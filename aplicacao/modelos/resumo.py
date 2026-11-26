from enum import Enum
from pydantic import BaseModel, Field, field_validator


class TextCategory(str, Enum):
    RELATORIO = "relatorio"
    SOLICITACAO = "solicitacao"
    EMAIL = "email"
    ATA_REUNIAO = "ata_reuniao"
    CONTRATO = "contrato"
    ARTIGO = "artigo"
    OUTRO = "outro"


class UrgencyLevel(str, Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class SummaryDetailLevel(str, Enum):
    CURTO = "curto"
    MEDIO = "medio"
    DETALHADO = "detalhado"


class SummaryRequest(BaseModel):
    """Input payload accepted by the summarization endpoint."""

    text: str = Field(
        ...,
        min_length=30,
        max_length=30000,
        description="Texto completo que precisa ser analisado e resumido.",
    )
    source: str = Field(
        default="manual",
        max_length=60,
        description="Origem do texto (ex.: interface_web, n8n_webhook, email, slack).",
    )
    detail_level: SummaryDetailLevel = Field(
        default=SummaryDetailLevel.MEDIO,
        description="Profundidade desejada para o resumo.",
    )
    requester: str | None = Field(
        default=None,
        max_length=120,
        description="Nome da pessoa ou equipe que enviou o texto.",
    )
    dispatch_to_n8n: bool = Field(
        default=False,
        description="Quando verdadeiro, encaminha o resultado para o webhook do n8n.",
    )

    @field_validator("text")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 30:
            raise ValueError(
                "O texto precisa ter pelo menos 30 caracteres úteis após remover espaços."
            )
        return cleaned

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        cleaned = value.strip().lower()
        return cleaned or "manual"

    @field_validator("requester")
    @classmethod
    def clean_requester(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None


class StructuredAiOutput(BaseModel):
    """Schema enforced on the AI model response to guarantee predictable JSON."""

    title: str = Field(
        ...,
        description="Título curto e descritivo do conteúdo analisado (máximo 12 palavras).",
    )
    category: TextCategory = Field(
        ...,
        description="Classificação predominante do documento ou mensagem.",
    )
    urgency: UrgencyLevel = Field(
        ...,
        description="Nível de urgência percebido no texto.",
    )
    executive_summary: str = Field(
        ...,
        description="Resumo claro e direto com a ideia central e o contexto.",
    )
    key_points: list[str] = Field(
        ...,
        min_length=2,
        max_length=7,
        description="Lista objetiva dos principais pontos destacados do texto.",
    )
    action_items: list[str] = Field(
        default_factory=list,
        description="Ações, pedidos ou próximos passos explícitos encontrados no texto.",
    )
    mentioned_entities: list[str] = Field(
        default_factory=list,
        description="Pessoas, setores, sistemas, clientes ou prazos relevantes citados.",
    )
    routing_suggestion: str = Field(
        ...,
        description="Área ou equipe mais indicada para lidar com esse conteúdo.",
    )


class TextMetrics(BaseModel):
    """Quantitative reading metrics comparing original text and summary."""

    original_words: int
    summary_words: int
    reduction_percent: float
    estimated_minutes_saved: float


class SummaryResponse(BaseModel):
    """Full response returned to API clients, frontend and n8n workflows."""

    id: str
    created_at: str
    source: str
    requester: str | None = None
    detail_level: SummaryDetailLevel
    model_used: str
    text_preview: str
    metrics: TextMetrics
    analysis: StructuredAiOutput
    automation_dispatched: bool = False
    automation_status: str | None = None


class HistoryListResponse(BaseModel):
    """Collection of recent summaries stored locally."""

    total: int
    items: list[SummaryResponse]


class HealthCheckResponse(BaseModel):
    """Operational readiness check exposed by the API."""

    status: str
    environment: str
    gemini_configured: bool
    model: str
    n8n_webhook_configured: bool
