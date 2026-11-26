from pathlib import Path
from types import SimpleNamespace
from fastapi.testclient import TestClient

from aplicacao.configuracao import AppSettings, get_settings
from aplicacao.modelos.resumo import (
    StructuredAiOutput,
    SummaryDetailLevel,
    SummaryRequest,
    TextCategory,
    UrgencyLevel,
)
from aplicacao.principal import ApplicationFactory
from aplicacao.rotas.resumos import provide_repository, provide_summarizer
from aplicacao.servicos.gerenciador_prompt import PromptBuilder
from aplicacao.servicos.provedor_ia import GeminiSummarizerService
from aplicacao.servicos.repositorio_historico import SummaryHistoryRepository


class FakeModelsEndpoint:
    """Stubs Google GenAI models.generate_content for deterministic unit tests."""

    def generate_content(self, **_kwargs):
        output = StructuredAiOutput(
            title="Relatório de atendimentos de outubro",
            category=TextCategory.RELATORIO,
            urgency=UrgencyLevel.MEDIA,
            executive_summary=(
                "Os chamados aumentaram 19% em outubro devido a dúvidas sobre faturamento "
                "e instabilidades fiscais corrigidas no dia 17."
            ),
            key_points=[
                "Alta de 19% no volume de chamados (1.482 no total).",
                "Correção no módulo fiscal reduziu erros em 94%.",
                "Solicitada contratação temporária de dois analistas.",
            ],
            action_items=[
                "Aprovar dois analistas temporários para novembro.",
                "Atualizar a central de ajuda até 05/11.",
            ],
            mentioned_entities=["Engenharia", "05/11", "Sudeste"],
            routing_suggestion="Operações e Suporte",
        )
        return SimpleNamespace(parsed=output, text=output.model_dump_json())


class FakeGenAiClient:
    """Stubs the top-level google.genai.Client interface."""

    def __init__(self) -> None:
        self.models = FakeModelsEndpoint()


class TestPromptAndMetrics:
    def test_prompt_builder_includes_context_and_text(self) -> None:
        builder = PromptBuilder()
        request = SummaryRequest(
            text="Texto longo de exemplo para validar o prompt com mais de trinta caracteres.",
            source="email",
            detail_level=SummaryDetailLevel.DETALHADO,
            requester="Time Comercial",
        )
        system_msg = builder.build_system_instruction()
        user_msg = builder.build_user_prompt(request)

        assert "nunca invente" in system_msg.lower()
        assert "Origem: email" in user_msg
        assert "Time Comercial" in user_msg
        assert "5 e 7 key_points" in user_msg

    def test_summarizer_metrics_and_structured_output(self) -> None:
        service = GeminiSummarizerService(
            api_key="fake-key",
            model_name="gemini-3.6-flash",
            client=FakeGenAiClient(),
        )
        long_text = " ".join(["Relatório operacional detalhado sobre vendas e suporte."] * 15)
        result = service.summarize(SummaryRequest(text=long_text, source="n8n_webhook"))

        assert result.analysis.category == TextCategory.RELATORIO
        assert result.metrics.original_words > result.metrics.summary_words
        assert result.metrics.reduction_percent > 0

    def test_summarizer_falls_back_on_transient_503(self) -> None:
        class FlakyModelsEndpoint(FakeModelsEndpoint):
            def __init__(self) -> None:
                self.calls = []

            def generate_content(self, **kwargs):
                model = kwargs["model"]
                self.calls.append(model)
                if model == "gemini-3.8-flash":
                    raise RuntimeError("503 UNAVAILABLE")
                return super().generate_content(**kwargs)

        flaky_client = SimpleNamespace(models=FlakyModelsEndpoint())
        service = GeminiSummarizerService(
            api_key="fake-key",
            model_name="gemini-3.8-flash",
            fallback_models=["gemini-3.6-flash"],
            client=flaky_client,
        )
        result = service.summarize(
            SummaryRequest(text="Texto suficientemente longo para testar o fallback de modelos Gemini.")
        )
        assert result.model_used == "gemini-3.6-flash"
        assert flaky_client.models.calls == ["gemini-3.8-flash", "gemini-3.6-flash"]


class TestSummaryApiEndpoints:
    def test_health_and_summary_lifecycle(self, tmp_path: Path) -> None:
        app = ApplicationFactory.create()
        history_path = tmp_path / "historico.json"

        test_settings = AppSettings(
            gemini_api_key="test-key",
            gemini_model="gemini-2.5-flash",
            history_file_path=history_path,
        )
        fake_summarizer = GeminiSummarizerService(
            api_key="test-key",
            model_name="gemini-2.5-flash",
            client=FakeGenAiClient(),
        )
        repo = SummaryHistoryRepository(file_path=history_path)

        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[provide_summarizer] = lambda: fake_summarizer
        app.dependency_overrides[provide_repository] = lambda: repo

        client = TestClient(app)

        health_res = client.get("/api/v1/health")
        assert health_res.status_code == 200
        assert health_res.json()["gemini_configured"] is True

        create_res = client.post(
            "/api/v1/resumos",
            json={
                "text": "Precisamos avaliar o aumento de chamados e corrigir a rotina de faturamento até sexta-feira.",
                "source": "n8n_webhook",
                "detail_level": "medio",
                "requester": "Atendimento",
            },
        )
        assert create_res.status_code == 201
        created = create_res.json()
        summary_id = created["id"]
        assert created["analysis"]["title"] == "Relatório de atendimentos de outubro"

        list_res = client.get("/api/v1/resumos")
        assert list_res.status_code == 200
        assert list_res.json()["total"] == 1

        delete_res = client.delete(f"/api/v1/resumos/{summary_id}")
        assert delete_res.status_code == 204
        assert client.get("/api/v1/resumos").json()["total"] == 0

    def test_repository_replaces_existing_id_on_upsert(self, tmp_path: Path) -> None:
        history_path = tmp_path / "historico.json"
        repo = SummaryHistoryRepository(file_path=history_path)
        service = GeminiSummarizerService(
            api_key="test-key",
            model_name="gemini-3.6-flash",
            client=FakeGenAiClient(),
        )
        entry = service.summarize(
            SummaryRequest(text="Texto suficientemente longo para testar atualização no histórico.")
        )
        repo.add(entry)
        entry.automation_dispatched = True
        entry.automation_status = "Processado pelo n8n · Atendimento Prioritário"
        repo.add(entry)

        items = repo.list_recent()
        assert len(items) == 1
        assert items[0].automation_dispatched is True
        assert items[0].automation_status == "Processado pelo n8n · Atendimento Prioritário"
