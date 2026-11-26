from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool

from aplicacao.configuracao import AppSettings, get_settings
from aplicacao.modelos.resumo import (
    HealthCheckResponse,
    HistoryListResponse,
    SummaryRequest,
    SummaryResponse,
)
from aplicacao.servicos.cliente_automacao import (
    AutomationWebhookClient,
    AutomationWebhookError,
)
from aplicacao.servicos.provedor_ia import AiProviderError, GeminiSummarizerService
from aplicacao.servicos.repositorio_historico import SummaryHistoryRepository


def provide_summarizer(
    settings: AppSettings = Depends(get_settings),
) -> GeminiSummarizerService:
    return GeminiSummarizerService(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
        fallback_models=settings.fallback_model_list,
    )


def provide_repository(
    settings: AppSettings = Depends(get_settings),
) -> SummaryHistoryRepository:
    return SummaryHistoryRepository(
        file_path=settings.resolved_history_path,
        max_items=settings.max_history_items,
    )


def provide_automation_client(
    settings: AppSettings = Depends(get_settings),
) -> AutomationWebhookClient:
    return AutomationWebhookClient(webhook_url=settings.n8n_webhook_url)


class SummaryController:
    """Groups API endpoints for health status, text summarization and history."""

    def __init__(self) -> None:
        self.router = APIRouter(prefix="/api/v1", tags=["Resumos"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "/health",
            self.health_check,
            methods=["GET"],
            response_model=HealthCheckResponse,
            summary="Verifica o status da API e das integrações configuradas",
        )
        self.router.add_api_route(
            "/resumos",
            self.create_summary,
            methods=["POST"],
            response_model=SummaryResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Gera um resumo estruturado em JSON a partir de um texto",
        )
        self.router.add_api_route(
            "/resumos",
            self.list_summaries,
            methods=["GET"],
            response_model=HistoryListResponse,
            summary="Lista os resumos gerados recentemente",
        )
        self.router.add_api_route(
            "/resumos/{summary_id}",
            self.get_summary,
            methods=["GET"],
            response_model=SummaryResponse,
            summary="Consulta um resumo específico pelo ID",
        )
        self.router.add_api_route(
            "/resumos/{summary_id}",
            self.delete_summary,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Remove um item do histórico local",
        )

    async def health_check(
        self,
        settings: AppSettings = Depends(get_settings),
    ) -> HealthCheckResponse:
        key_ok = bool(
            settings.gemini_api_key.strip()
            and settings.gemini_api_key.strip() != "sua_chave_api_aqui"
        )
        return HealthCheckResponse(
            status="ok",
            environment=settings.app_env,
            gemini_configured=key_ok,
            model=settings.gemini_model,
            n8n_webhook_configured=bool(settings.n8n_webhook_url.strip()),
        )

    async def create_summary(
        self,
        payload: SummaryRequest,
        summarizer: GeminiSummarizerService = Depends(provide_summarizer),
        repository: SummaryHistoryRepository = Depends(provide_repository),
        automation_client: AutomationWebhookClient = Depends(provide_automation_client),
    ) -> SummaryResponse:
        if payload.dispatch_to_n8n:
            try:
                workflow_result = await automation_client.process_via_workflow(payload)
                repository.add(workflow_result)
                return workflow_result
            except AutomationWebhookError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=str(exc),
                ) from exc

        try:
            result = await run_in_threadpool(summarizer.summarize, payload)
        except AiProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        repository.add(result)
        return result

    async def list_summaries(
        self,
        limit: int = Query(default=20, ge=1, le=50),
        repository: SummaryHistoryRepository = Depends(provide_repository),
    ) -> HistoryListResponse:
        items = repository.list_recent(limit=limit)
        return HistoryListResponse(total=len(items), items=items)

    async def get_summary(
        self,
        summary_id: str,
        repository: SummaryHistoryRepository = Depends(provide_repository),
    ) -> SummaryResponse:
        found = repository.get_by_id(summary_id)
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resumo '{summary_id}' não encontrado.",
            )
        return found

    async def delete_summary(
        self,
        summary_id: str,
        repository: SummaryHistoryRepository = Depends(provide_repository),
    ) -> None:
        removed = repository.delete_by_id(summary_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resumo '{summary_id}' não encontrado.",
            )
