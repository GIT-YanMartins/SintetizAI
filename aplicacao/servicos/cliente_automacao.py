import httpx
from aplicacao.modelos.resumo import SummaryRequest, SummaryResponse


class AutomationWebhookError(RuntimeError):
    """Raised when the n8n automation webhook fails to process a request."""


class AutomationWebhookClient:
    """Dispatches texts to the n8n workflow webhook and parses the returned summary."""

    def __init__(self, webhook_url: str, timeout_seconds: float = 65.0) -> None:
        self._webhook_url = webhook_url.strip()
        self._timeout = timeout_seconds

    async def process_via_workflow(self, request: SummaryRequest) -> SummaryResponse:
        if not self._webhook_url:
            raise AutomationWebhookError("AUTOMATION_WEBHOOK_URL não configurada no .env.")

        payload = {
            "texto": request.text,
            "origem": request.source,
            "nivel_detalhe": request.detail_level.value,
            "solicitante": request.requester,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._webhook_url, json=payload)
        except httpx.RequestError as exc:
            raise AutomationWebhookError(
                f"Não foi possível conectar ao webhook do n8n ({self._webhook_url}): {exc}"
            ) from exc

        if not (200 <= response.status_code < 300):
            raise AutomationWebhookError(
                f"Fluxo do n8n retornou HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise AutomationWebhookError(
                "O webhook do n8n não retornou um JSON válido."
            ) from exc

        raw_summary = data.get("resumo_completo") if isinstance(data, dict) else None
        if not isinstance(raw_summary, dict):
            raise AutomationWebhookError(
                "Resposta do fluxo n8n não contém o bloco 'resumo_completo' esperado."
            )

        summary = SummaryResponse.model_validate(raw_summary)
        fila = data.get("fila_destino") or "Fluxo n8n"
        summary.automation_dispatched = True
        summary.automation_status = f"Processado pelo n8n · {fila}"
        return summary
