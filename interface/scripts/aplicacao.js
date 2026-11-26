class SummaryApiClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
  }

  async checkHealth() {
    const response = await fetch(`${this.baseUrl}/api/v1/health`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  }

  async createSummary(payload) {
    const response = await fetch(`${this.baseUrl}/api/v1/resumos`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof data.detail === "string"
        ? data.detail
        : "Não foi possível gerar o resumo.";
      throw new Error(detail);
    }
    return data;
  }

  async listHistory(limit = 12) {
    const response = await fetch(`${this.baseUrl}/api/v1/resumos?limit=${limit}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  }

  async deleteSummary(summaryId) {
    const response = await fetch(`${this.baseUrl}/api/v1/resumos/${encodeURIComponent(summaryId)}`, {
      method: "DELETE"
    });
    if (!response.ok && response.status !== 204) {
      throw new Error(`Erro ao remover item (${response.status})`);
    }
  }
}

class SummaryResultView {
  constructor() {
    this.emptyState = document.getElementById("empty-result-state");
    this.resultContent = document.getElementById("result-content");
    this.formattedView = document.getElementById("formatted-view");
    this.jsonView = document.getElementById("json-view");
    this.jsonOutput = document.getElementById("res-json-output");
    this.titleEl = document.getElementById("res-title");
    this.categoryEl = document.getElementById("res-category");
    this.urgencyEl = document.getElementById("res-urgency");
    this.routingEl = document.getElementById("res-routing");
    this.metricOriginal = document.getElementById("metric-original");
    this.metricSummary = document.getElementById("metric-summary");
    this.metricReduction = document.getElementById("metric-reduction");
    this.metricTime = document.getElementById("metric-time");
    this.n8nStatusBox = document.getElementById("n8n-status-box");
    this.summaryEl = document.getElementById("res-summary");
    this.keyPointsEl = document.getElementById("res-key-points");
    this.actionsEl = document.getElementById("res-actions");
    this.entitiesEl = document.getElementById("res-entities");
    this.timestampEl = document.getElementById("res-timestamp");
    this.copyBtn = document.getElementById("copy-result-btn");
    this.tabButtons = document.querySelectorAll(".tab-btn");

    this.currentResult = null;
    this.activeTab = "formatted";
    this._bindTabs();
  }

  _bindTabs() {
    this.tabButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const view = button.dataset.view;
        this.switchView(view);
      });
    });
  }

  switchView(view) {
    this.activeTab = view === "json" ? "json" : "formatted";
    this.tabButtons.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.view === this.activeTab);
    });

    this.formattedView.classList.toggle("hidden", this.activeTab !== "formatted");
    this.jsonView.classList.toggle("hidden", this.activeTab !== "json");
    this.copyBtn.textContent = this.activeTab === "json" ? "Copiar JSON" : "Copiar resumo";
  }

  static formatCategory(category) {
    const labels = {
      relatorio: "Relatório",
      solicitacao: "Solicitação",
      email: "E-mail",
      ata_reuniao: "Ata de reunião",
      contrato: "Contrato",
      artigo: "Artigo",
      outro: "Outro"
    };
    return labels[category] || category;
  }

  static formatUrgency(urgency) {
    const labels = {
      baixa: "Urgência baixa",
      media: "Urgência média",
      alta: "Urgência alta",
      critica: "Urgência crítica"
    };
    return labels[urgency] || urgency;
  }

  render(result) {
    this.currentResult = result;
    const { analysis, metrics } = result;

    this.emptyState.classList.add("hidden");
    this.resultContent.classList.remove("hidden");

    this.titleEl.textContent = analysis.title;
    this.categoryEl.textContent = SummaryResultView.formatCategory(analysis.category);
    this.urgencyEl.textContent = SummaryResultView.formatUrgency(analysis.urgency);
    this.urgencyEl.className = `meta-badge badge-urgency ${analysis.urgency}`;
    this.routingEl.textContent = `Encaminhar: ${analysis.routing_suggestion}`;

    this.metricOriginal.textContent = `${metrics.original_words} palavras`;
    this.metricSummary.textContent = `${metrics.summary_words} palavras`;
    this.metricReduction.textContent = `${metrics.reduction_percent}%`;
    this.metricTime.textContent = `${metrics.estimated_minutes_saved} min`;

    if (result.automation_status) {
      this.n8nStatusBox.classList.remove("hidden", "dispatched", "failed");
      this.n8nStatusBox.classList.add(result.automation_dispatched ? "dispatched" : "failed");
      this.n8nStatusBox.textContent = `n8n: ${result.automation_status}`;
    } else {
      this.n8nStatusBox.classList.add("hidden");
    }

    this.summaryEl.textContent = analysis.executive_summary;

    this._renderList(this.keyPointsEl, analysis.key_points, "Nenhum ponto listado.");
    this._renderList(
      this.actionsEl,
      analysis.action_items,
      "Nenhuma ação explícita identificada."
    );
    this._renderChips(this.entitiesEl, analysis.mentioned_entities);

    this.jsonOutput.textContent = JSON.stringify(result, null, 2);

    const formattedDate = new Date(result.created_at).toLocaleString("pt-BR");
    this.timestampEl.textContent = `ID ${result.id} · Modelo ${result.model_used} · ${formattedDate}`;
  }

  _renderList(container, items, emptyMessage) {
    container.innerHTML = "";
    if (!items || items.length === 0) {
      const emptyItem = document.createElement("li");
      emptyItem.className = "muted-note";
      emptyItem.textContent = emptyMessage;
      container.appendChild(emptyItem);
      return;
    }

    items.forEach((text) => {
      const li = document.createElement("li");
      li.textContent = text;
      container.appendChild(li);
    });
  }

  _renderChips(container, entities) {
    container.innerHTML = "";
    if (!entities || entities.length === 0) {
      const note = document.createElement("p");
      note.className = "muted-note";
      note.textContent = "Nenhuma entidade destacada.";
      container.appendChild(note);
      return;
    }

    entities.forEach((entity) => {
      const chip = document.createElement("span");
      chip.className = "entity-chip";
      chip.textContent = entity;
      container.appendChild(chip);
    });
  }

  getCopyableText() {
    if (!this.currentResult) {
      return "";
    }
    if (this.activeTab === "json") {
      return JSON.stringify(this.currentResult, null, 2);
    }

    const { analysis } = this.currentResult;
    const points = analysis.key_points.map((item) => `- ${item}`).join("\n");
    const actions = analysis.action_items.length
      ? analysis.action_items.map((item) => `- ${item}`).join("\n")
      : "- Nenhuma ação explícita";

    return [
      analysis.title,
      `Categoria: ${SummaryResultView.formatCategory(analysis.category)} | ${SummaryResultView.formatUrgency(analysis.urgency)}`,
      "",
      "Resumo executivo:",
      analysis.executive_summary,
      "",
      "Principais pontos:",
      points,
      "",
      "Ações identificadas:",
      actions
    ].join("\n");
  }
}

class HistoryListView {
  constructor(onSelect, onDelete) {
    this.container = document.getElementById("history-list");
    this.emptyNotice = document.getElementById("history-empty");
    this.onSelect = onSelect;
    this.onDelete = onDelete;
  }

  render(items) {
    this.container.innerHTML = "";
    if (!items || items.length === 0) {
      this.emptyNotice.classList.remove("hidden");
      return;
    }

    this.emptyNotice.classList.add("hidden");
    items.forEach((item) => {
      const card = document.createElement("article");
      card.className = "history-card";

      const topBlock = document.createElement("div");

      const title = document.createElement("h3");
      title.className = "history-card-title";
      title.textContent = item.analysis.title;

      const preview = document.createElement("p");
      preview.className = "history-card-preview";
      preview.textContent = item.analysis.executive_summary;

      topBlock.appendChild(title);
      topBlock.appendChild(preview);

      const footer = document.createElement("div");
      footer.className = "history-card-footer";

      const badge = document.createElement("span");
      badge.className = `meta-badge badge-urgency ${item.analysis.urgency}`;
      badge.textContent = `${SummaryResultView.formatCategory(item.analysis.category)} · ${item.source}`;

      const actions = document.createElement("div");
      actions.className = "history-actions";

      const openBtn = document.createElement("button");
      openBtn.type = "button";
      openBtn.className = "link-btn";
      openBtn.textContent = "Abrir";
      openBtn.addEventListener("click", () => this.onSelect(item));

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "link-btn delete";
      deleteBtn.textContent = "Excluir";
      deleteBtn.addEventListener("click", () => this.onDelete(item.id));

      actions.appendChild(openBtn);
      actions.appendChild(deleteBtn);

      footer.appendChild(badge);
      footer.appendChild(actions);

      card.appendChild(topBlock);
      card.appendChild(footer);
      this.container.appendChild(card);
    });
  }
}

class SummarizerApp {
  constructor() {
    this.api = new SummaryApiClient();
    this.resultView = new SummaryResultView();
    this.historyView = new HistoryListView(
      (item) => this._handleSelectHistory(item),
      (id) => this._handleDeleteHistory(id)
    );

    this.form = document.getElementById("summary-form");
    this.textInput = document.getElementById("input-text");
    this.requesterInput = document.getElementById("input-requester");
    this.sourceSelect = document.getElementById("input-source");
    this.detailSelect = document.getElementById("input-detail");
    this.dispatchCheckbox = document.getElementById("input-dispatch-n8n");
    this.counterEl = document.getElementById("text-counter");
    this.feedbackEl = document.getElementById("form-feedback");
    this.submitBtn = document.getElementById("submit-btn");
    this.submitSpinner = document.getElementById("submit-spinner");
    this.submitLabel = document.getElementById("submit-label");
    this.clearBtn = document.getElementById("clear-btn");
    this.refreshHistoryBtn = document.getElementById("refresh-history-btn");
    this.statusDot = document.getElementById("api-status-dot");
    this.statusText = document.getElementById("api-status-text");
  }

  init() {
    this._bindEvents();
    this._updateCounter();
    this._loadHealth();
    this._loadHistory();
  }

  _bindEvents() {
    this.textInput.addEventListener("input", () => this._updateCounter());

    document.querySelectorAll(".sample-btn").forEach((button) => {
      button.addEventListener("click", () => {
        const samples = SampleTextCatalog.getSamples();
        const chosen = samples[button.dataset.sample];
        if (!chosen) {
          return;
        }
        this.textInput.value = chosen.text;
        this.requesterInput.value = chosen.requester;
        this.sourceSelect.value = chosen.source;
        this.detailSelect.value = chosen.detail_level;
        this._updateCounter();
        this._hideFeedback();
      });
    });

    this.clearBtn.addEventListener("click", () => {
      this.form.reset();
      this._updateCounter();
      this._hideFeedback();
    });

    this.form.addEventListener("submit", (event) => {
      event.preventDefault();
      this._handleSubmit();
    });

    this.resultView.copyBtn.addEventListener("click", () => this._handleCopy());
    this.refreshHistoryBtn.addEventListener("click", () => this._loadHistory());
  }

  _updateCounter() {
    const raw = this.textInput.value.trim();
    const words = raw ? raw.split(/\s+/).length : 0;
    const chars = raw.length;
    this.counterEl.textContent = `${words} palavras · ${chars} caracteres`;
  }

  _showFeedback(message, type = "error") {
    this.feedbackEl.textContent = message;
    this.feedbackEl.className = `feedback-banner ${type}`;
  }

  _hideFeedback() {
    this.feedbackEl.className = "feedback-banner hidden";
    this.feedbackEl.textContent = "";
  }

  _setSubmitting(isLoading) {
    this.submitBtn.disabled = isLoading;
    this.submitSpinner.classList.toggle("hidden", !isLoading);
    this.submitLabel.textContent = isLoading ? "Resumindo..." : "Gerar resumo";
  }

  async _loadHealth() {
    try {
      const health = await this.api.checkHealth();
      this.statusDot.classList.remove("online", "warning", "offline");
      if (health.gemini_configured) {
        this.statusDot.classList.add("online");
        this.statusText.textContent = `API online · ${health.model}`;
      } else {
        this.statusDot.classList.add("warning");
        this.statusText.textContent = "API online · falta chave Gemini";
      }
    } catch (_error) {
      this.statusDot.classList.remove("online", "warning");
      this.statusDot.classList.add("offline");
      this.statusText.textContent = "API offline";
    }
  }

  async _loadHistory() {
    try {
      const data = await this.api.listHistory(12);
      this.historyView.render(data.items);
    } catch (_error) {
      this.historyView.render([]);
    }
  }

  async _handleSubmit() {
    this._hideFeedback();
    const cleanedText = this.textInput.value.trim();

    if (cleanedText.length < 30) {
      this._showFeedback("Digite ou cole um texto com pelo menos 30 caracteres.", "error");
      this.textInput.focus();
      return;
    }

    const payload = {
      text: cleanedText,
      source: this.sourceSelect.value,
      detail_level: this.detailSelect.value,
      requester: this.requesterInput.value.trim() || null,
      dispatch_to_n8n: this.dispatchCheckbox.checked
    };

    this._setSubmitting(true);
    try {
      const result = await this.api.createSummary(payload);
      this.resultView.render(result);
      await this._loadHistory();
    } catch (error) {
      this._showFeedback(error.message || "Erro ao se comunicar com a API.", "error");
    } finally {
      this._setSubmitting(false);
    }
  }

  _handleSelectHistory(item) {
    this.resultView.render(item);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async _handleDeleteHistory(summaryId) {
    try {
      await this.api.deleteSummary(summaryId);
      await this._loadHistory();
    } catch (error) {
      this._showFeedback(error.message, "error");
    }
  }

  async _handleCopy() {
    const content = this.resultView.getCopyableText();
    if (!content) {
      return;
    }
    try {
      await navigator.clipboard.writeText(content);
      const originalLabel = this.resultView.copyBtn.textContent;
      this.resultView.copyBtn.textContent = "Copiado!";
      setTimeout(() => {
        this.resultView.copyBtn.textContent = originalLabel;
      }, 1500);
    } catch (_error) {
      this._showFeedback("Não foi possível acessar a área de transferência.", "error");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const app = new SummarizerApp();
  app.init();
});
