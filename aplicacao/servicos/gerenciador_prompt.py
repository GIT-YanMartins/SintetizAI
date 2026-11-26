from aplicacao.modelos.resumo import SummaryDetailLevel, SummaryRequest


class PromptBuilder:
    """Constructs structured prompts for the text summarization model."""

    _DETAIL_GUIDELINES: dict[SummaryDetailLevel, str] = {
        SummaryDetailLevel.CURTO: (
            "Produza um executive_summary bem enxuto (2 frases diretas) e entre "
            "2 e 3 key_points essenciais."
        ),
        SummaryDetailLevel.MEDIO: (
            "Produza um executive_summary equilibrado (3 a 4 frases) e entre "
            "3 e 5 key_points que cubram fatos, decisões e pedidos."
        ),
        SummaryDetailLevel.DETALHADO: (
            "Produza um executive_summary completo (4 a 6 frases) e entre "
            "5 e 7 key_points preservando números, datas, riscos e nuances."
        ),
    }

    def build_system_instruction(self) -> str:
        return (
            "Você é um analista operacional especialista em síntese de documentos, "
            "relatórios internos e solicitações corporativas. "
            "Sua tarefa é ler textos extensos enviados por equipes e transformá-los "
            "em um resumo estruturado em português do Brasil.\n\n"
            "Regras obrigatórias:\n"
            "1. Baseie-se exclusivamente no texto fornecido; nunca invente datas, nomes, "
            "valores ou conclusões que não estejam explícitos.\n"
            "2. Preserve números, prazos, percentuais e responsáveis citados no original.\n"
            "3. Se o texto não tiver ações explícitas, retorne action_items como lista vazia.\n"
            "4. Avalie a urgência com bom senso: use 'critica' apenas para incidentes "
            "graves, prazos vencendo hoje ou bloqueios severos.\n"
            "5. Seja sempre mais conciso que o texto original: sintetize sem repetir "
            "frases inteiras palavra por palavra.\n"
            "6. Responda estritamente no formato JSON definido pelo schema."
        )

    def build_user_prompt(self, request: SummaryRequest) -> str:
        detail_rule = self._DETAIL_GUIDELINES[request.detail_level]
        requester_label = request.requester or "Não informado"

        return (
            f"Contexto do envio:\n"
            f"- Origem: {request.source}\n"
            f"- Solicitante: {requester_label}\n"
            f"- Nível de detalhe: {request.detail_level.value}\n\n"
            f"Instrução de profundidade: {detail_rule}\n\n"
            f"Analise o texto abaixo e retorne o JSON estruturado:\n"
            f"--- INÍCIO DO TEXTO ---\n"
            f"{request.text}\n"
            f"--- FIM DO TEXTO ---"
        )
