class SampleTextCatalog {
  static getSamples() {
    return {
      relatorio: {
        requester: "Coordenação Comercial",
        source: "relatorio",
        detail_level: "medio",
        text: [
          "Relatório Operacional de Outubro — Unidade Sudeste.",
          "Durante o mês de outubro, a equipe de atendimento registrou 1.482 chamados no canal principal, um aumento de 19% em relação a setembro.",
          "Esse crescimento foi puxado principalmente por dúvidas sobre a nova política de faturamento parcelado e por instabilidades intermitentes na emissão de notas fiscais entre os dias 12 e 16.",
          "O tempo médio de primeira resposta subiu de 22 minutos para 38 minutos, impactando o SLA de contas corporativas.",
          "Como ação imediata, o time de Engenharia aplicou uma correção no módulo fiscal no dia 17, reduzindo os erros de emissão em 94% na segunda quinzena.",
          "Para novembro, solicitamos a aprovação de contratação temporária de dois analistas de suporte e a atualização da central de ajuda com um guia passo a passo sobre o novo faturamento até o dia 05/11."
        ].join(" ")
      },
      solicitacao: {
        requester: "Marina Alves — Financeiro",
        source: "solicitacao",
        detail_level: "medio",
        text: [
          "Olá equipe de Tecnologia, precisamos priorizar com urgência a revisão da rotina de conciliação bancária do ERP.",
          "Desde a última atualização de sexta-feira, os arquivos OFX importados pelo setor financeiro estão duplicando lançamentos referentes a tarifas de cartão quando o lote possui mais de 300 registros.",
          "Como o fechamento contábil da competência vence nesta quinta-feira às 17h, a analista responsável precisou conferir manualmente mais de 600 linhas hoje pela manhã.",
          "Pedimos que verifiquem o parser de importação ainda hoje, liberem uma correção em homologação até amanhã às 11h e confirmem se os lançamentos duplicados dos dias 21 e 22 podem ser revertidos automaticamente via script."
        ].join(" ")
      },
      ata: {
        requester: "Gestão de Produto",
        source: "email",
        detail_level: "detalhado",
        text: [
          "Ata resumida da reunião de alinhamento — Portal do Cliente v2.4 (24/11).",
          "Participantes: Lucas (Produto), Camila (UX), Rafael (Back-end) e Fernanda (Suporte).",
          "Decisões tomadas: o lançamento da nova tela de acompanhamento de pedidos será mantido para 02/12, porém o módulo de exportação em PDF ficará para a sprint seguinte devido a ajustes de performance nas consultas.",
          "Camila entregará os protótipos finais das mensagens de erro até quarta-feira às 14h.",
          "Rafael ficou responsável por validar a fila de webhooks com o n8n e garantir que os alertas de falha cheguem ao canal de monitoramento.",
          "Fernanda preparará o comunicado para os clientes-piloto e consolidará o feedback da primeira semana de uso."
        ].join(" ")
      }
    };
  }
}
