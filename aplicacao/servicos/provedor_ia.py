from datetime import datetime, timezone
from uuid import uuid4

from google import genai
from google.genai import types

from aplicacao.modelos.resumo import (
    StructuredAiOutput,
    SummaryRequest,
    SummaryResponse,
    TextMetrics,
)
from aplicacao.servicos.gerenciador_prompt import PromptBuilder


class AiProviderError(RuntimeError):
    """Raised when the external AI API cannot produce a valid summary."""


class GeminiSummarizerService:
    """Integrates with Google Gemini to produce structured JSON text summaries."""

    _WORDS_PER_MINUTE = 200.0

    def __init__(
        self,
        api_key: str,
        model_name: str,
        fallback_models: list[str] | None = None,
        prompt_builder: PromptBuilder | None = None,
        client: genai.Client | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._model_name = model_name.strip()
        self._fallback_models = [
            model.strip()
            for model in (fallback_models or [])
            if model.strip() and model.strip() != self._model_name
        ]
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._client = client

    def _get_client(self) -> genai.Client:
        if self._client is not None:
            return self._client
        if not self._api_key or self._api_key == "sua_chave_api_aqui":
            raise AiProviderError(
                "Chave GEMINI_API_KEY não configurada no arquivo .env."
            )
        self._client = genai.Client(
            api_key=self._api_key,
            http_options=types.HttpOptions(
                timeout=18000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        return self._client

    @classmethod
    def calculate_metrics(
        cls,
        original_text: str,
        analysis: StructuredAiOutput,
    ) -> TextMetrics:
        original_words = len(original_text.split())
        summary_words = len(analysis.executive_summary.split())

        if original_words == 0:
            reduction = 0.0
        else:
            reduction = max(
                0.0,
                round(((original_words - summary_words) / original_words) * 100, 1),
            )

        words_saved = max(0, original_words - summary_words)
        minutes_saved = round(words_saved / cls._WORDS_PER_MINUTE, 2)

        return TextMetrics(
            original_words=original_words,
            summary_words=summary_words,
            reduction_percent=reduction,
            estimated_minutes_saved=minutes_saved,
        )

    @staticmethod
    def build_preview(text: str, max_chars: int = 180) -> str:
        collapsed = " ".join(text.split())
        if len(collapsed) <= max_chars:
            return collapsed
        return f"{collapsed[: max_chars - 3].rstrip()}..."

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        message = str(exc).upper()
        return any(
            token in message
            for token in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "DEADLINE")
        )

    def summarize(self, request: SummaryRequest) -> SummaryResponse:
        client = self._get_client()
        system_instruction = self._prompt_builder.build_system_instruction()
        user_prompt = self._prompt_builder.build_user_prompt(request)

        candidates = [self._model_name, *self._fallback_models]
        response = None
        used_model = self._model_name
        last_error: Exception | None = None

        for idx, candidate_model in enumerate(candidates):
            try:
                response = client.models.generate_content(
                    model=candidate_model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=StructuredAiOutput,
                        temperature=0.2,
                    ),
                )
                used_model = candidate_model
                break
            except Exception as exc:
                last_error = exc
                has_next = idx < len(candidates) - 1
                if has_next and self._is_transient_error(exc):
                    continue
                raise AiProviderError(
                    f"Falha ao consultar o modelo '{candidate_model}': {exc}"
                ) from exc

        if response is None:
            raise AiProviderError(
                f"Nenhum modelo Gemini respondeu com sucesso: {last_error}"
            )

        parsed_output = getattr(response, "parsed", None)
        if isinstance(parsed_output, StructuredAiOutput):
            analysis = parsed_output
        elif isinstance(parsed_output, dict):
            analysis = StructuredAiOutput.model_validate(parsed_output)
        else:
            raw_text = (getattr(response, "text", None) or "").strip()
            if not raw_text:
                raise AiProviderError(
                    "O modelo retornou uma resposta vazia ao resumir o texto."
                )
            try:
                analysis = StructuredAiOutput.model_validate_json(raw_text)
            except Exception as exc:
                raise AiProviderError(
                    f"A resposta da IA não seguiu o JSON esperado: {exc}"
                ) from exc

        metrics = self.calculate_metrics(request.text, analysis)

        return SummaryResponse(
            id=uuid4().hex[:12],
            created_at=datetime.now(timezone.utc).isoformat(),
            source=request.source,
            requester=request.requester,
            detail_level=request.detail_level,
            model_used=used_model,
            text_preview=self.build_preview(request.text),
            metrics=metrics,
            analysis=analysis,
        )
