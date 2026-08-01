(() => {
  const TOKEN_KEY = "local-ai-agent-api-token";
  const CHAT_KEY = "local-ai-agent-admin-chat";
  const RESTART_KEY = "local-ai-agent-restart-banner";

  const state = {
    view: "overview",
    stackTab: "models",
    status: null,
    metrics: null,
    ready: null,
    health: null,
    tasks: [],
    selectedTaskId: null,
    memory: [],
    settings: null,
    chatBusy: false,
    tokenRequired: false,
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  function toast(message) {
    const el = $("#toast");
    el.textContent = message;
    el.classList.remove("hidden");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add("hidden"), 3200);
  }

  function getApiToken() {
    const rail = $("#api-token");
    const chat = $("#chat-api-token");
    return (rail?.value || chat?.value || "").trim();
  }

  function setApiToken(value, { persist = true } = {}) {
    const cleaned = (value || "").trim();
    const rail = $("#api-token");
    const chat = $("#chat-api-token");
    if (rail) rail.value = cleaned;
    if (chat) chat.value = cleaned;
    if (persist) {
      if (cleaned) localStorage.setItem(TOKEN_KEY, cleaned);
      else localStorage.removeItem(TOKEN_KEY);
    }
    updateTokenUi();
  }

  function updateTokenUi() {
    const hasToken = Boolean(getApiToken());
    const need = state.tokenRequired && !hasToken;
    $("#token-required-badge")?.classList.toggle("hidden", !state.tokenRequired);
    $("#token-hint")?.classList.toggle("hidden", !need);
    $("#chat-token-bar")?.classList.toggle("hidden", !need);
    if (need && $("#chat-api-token") && !$("#chat-api-token").value) {
      $("#chat-api-token").value = localStorage.getItem(TOKEN_KEY) || "";
    }
  }

  async function refreshTokenRequirement() {
    try {
      const ready = await fetchJson("/ready", { skipAuthRetry: true });
      state.ready = ready;
      state.tokenRequired = Boolean(ready.api_token_required);
    } catch {
      state.tokenRequired = true;
    }
    updateTokenUi();
  }

  function authHeaders(extra = {}) {
    const headers = { ...extra };
    const token = getApiToken();
    if (token) headers["X-API-Token"] = token;
    return headers;
  }

  async function fetchJson(url, options = {}) {
    const opts = { ...options };
    const skipAuthRetry = Boolean(opts.skipAuthRetry);
    delete opts.skipAuthRetry;
    opts.headers = authHeaders(opts.headers || {});
    const response = await fetch(url, opts);
    const text = await response.text();
    let payload = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      payload = { detail: text };
    }
    if (!response.ok) {
      const detail = payload && payload.detail ? payload.detail : `HTTP ${response.status}`;
      const message = typeof detail === "string" ? detail : JSON.stringify(detail);
      if (response.status === 401 && !skipAuthRetry) {
        state.tokenRequired = true;
        updateTokenUi();
        if (isChatDialogOpen()) {
          $("#chat-token-bar")?.classList.remove("hidden");
          $("#chat-api-token")?.focus();
        }
        throw new Error(
          "Нужен API token. Вставьте LOCAL_AI_AGENT_API_TOKEN из .env в поле выше или слева в меню, затем повторите.",
        );
      }
      throw new Error(message);
    }
    return payload;
  }

  function showRestartBanner(show) {
    const banner = $("#restart-banner");
    if (show) {
      banner.classList.remove("hidden");
      sessionStorage.setItem(RESTART_KEY, "1");
    } else {
      banner.classList.add("hidden");
      sessionStorage.removeItem(RESTART_KEY);
    }
  }

  function setView(name) {
    state.view = name;
    $$(".nav-item").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.view === name);
    });
    $$(".view").forEach((view) => {
      view.classList.toggle("active", view.id === `view-${name}`);
    });
    if (name === "overview") refreshOverview();
    if (name === "tasks") refreshTasks();
    if (name === "memory") refreshMemory();
    if (name === "stack") refreshStack();
    if (name === "settings") refreshSettings();
  }

  async function openChatDialog() {
    const root = $("#chat-dialog-root");
    root.classList.remove("hidden");
    root.setAttribute("aria-hidden", "false");
    await refreshTokenRequirement();
    const chatToken = $("#chat-api-token");
    if (chatToken) chatToken.value = getApiToken();
    updateTokenUi();
    renderChat();
    const focusEl = state.tokenRequired && !getApiToken()
      ? $("#chat-api-token")
      : $("#chat-input");
    if (focusEl) setTimeout(() => focusEl.focus(), 40);
  }

  function closeChatDialog() {
    const root = $("#chat-dialog-root");
    root.classList.add("hidden");
    root.setAttribute("aria-hidden", "true");
  }

  function isChatDialogOpen() {
    return !$("#chat-dialog-root").classList.contains("hidden");
  }

  function openModal({ title, bodyHtml, footHtml }) {
    $("#modal-title").textContent = title;
    $("#modal-body").innerHTML = bodyHtml;
    $("#modal-foot").innerHTML = footHtml || "";
    const root = $("#modal-root");
    root.classList.remove("hidden");
    root.setAttribute("aria-hidden", "false");
  }

  function closeModal() {
    const root = $("#modal-root");
    root.classList.add("hidden");
    root.setAttribute("aria-hidden", "true");
    $("#modal-body").innerHTML = "";
    $("#modal-foot").innerHTML = "";
  }

  function kpi(label, value, tone = "") {
    return `<div class="kpi ${tone}"><div class="label">${label}</div><div class="value">${value}</div></div>`;
  }

  function yesNo(ok) {
    return ok ? "онлайн" : "нет";
  }

  function toneBool(ok) {
    return ok ? "ok" : "bad";
  }

  async function refreshOverview() {
    const grid = $("#kpi-grid");
    const detail = $("#overview-detail");
    grid.innerHTML = "<p class='muted'>Загрузка…</p>";
    try {
      const [health, ready, status, metrics] = await Promise.all([
        fetchJson("/health"),
        fetchJson("/ready"),
        fetchJson("/status"),
        fetchJson("/metrics"),
      ]);
      state.health = health;
      state.ready = ready;
      state.status = status;
      state.metrics = metrics;
      grid.innerHTML = [
        kpi("Health", health.status || "?", health.status === "ok" ? "ok" : "bad"),
        kpi("Ready", ready.status === "ready" ? "ready" : "waiting", ready.status === "ready" ? "ok" : "warn"),
        kpi("Uptime", `${Math.round(metrics.uptime_seconds || 0)}s`),
        kpi("Ollama", yesNo(status.ollama_online), toneBool(status.ollama_online)),
        kpi("Memory", status.memory_backend || "—"),
        kpi("Tasks", metrics.task_count ?? "—"),
        kpi("Telegram", status.telegram?.available ? "ready" : "off", status.telegram?.available ? "ok" : "warn"),
        kpi("FS Watch", status.fs_watch?.available ? "available" : "n/a", status.fs_watch?.available ? "ok" : "warn"),
      ].join("");
      const models = status.models_resolved || status.models || {};
      detail.innerHTML = `
        <h2>Сводка</h2>
        <p class="muted">Env: <code>${health.env || "—"}</code> · Version: <code>${health.version || "—"}</code></p>
        <p>Models: primary <code>${models.primary || status.models?.primary || "—"}</code>,
          router <code>${models.router || status.models?.router || "—"}</code>,
          vision <code>${models.vision || status.models?.vision || "—"}</code>,
          embed <code>${models.embed || status.models?.embed || "—"}</code></p>
        <p>Quality mode: <code>${status.quality_mode || "—"}</code></p>
      `;
    } catch (error) {
      grid.innerHTML = `<p class="muted">${escapeHtml(String(error))}</p>`;
      detail.innerHTML = "";
    }
  }

  function loadChat() {
    try {
      return JSON.parse(sessionStorage.getItem(CHAT_KEY) || "[]");
    } catch {
      return [];
    }
  }

  function saveChat(messages) {
    sessionStorage.setItem(CHAT_KEY, JSON.stringify(messages));
  }

  function renderChat() {
    const stream = $("#chat-stream");
    const messages = loadChat();
    if (!messages.length) {
      stream.innerHTML = `
        <div class="chat-empty">
          <img class="brand-hero" src="/admin/static/brand.png" width="88" height="88" alt="Local AI Agent" />
          <h2>Local AI Agent</h2>
          <p class="muted">Ваш локальный ИИ — спросите что угодно. Запрос уйдёт в orchestrator как Task.</p>
          <div class="suggestions">
            <button type="button" class="chip" data-prompt="Кто ты и что умеешь?">Кто ты?</button>
            <button type="button" class="chip" data-prompt="Проверь статус Ollama и моделей">Статус Ollama</button>
            <button type="button" class="chip" data-prompt="Кратко объясни, как устроен Memory store">Про Memory</button>
          </div>
        </div>`;
      $$(".chip", stream).forEach((chip) => {
        chip.addEventListener("click", () => {
          $("#chat-input").value = chip.dataset.prompt;
          $("#chat-input").focus();
        });
      });
      return;
    }
    stream.innerHTML = messages
      .map((msg) => {
        if (msg.role === "meta") {
          return `<div class="msg-meta">${msg.html}</div>`;
        }
        const cls = msg.role === "user" ? "user" : msg.thinking ? "assistant thinking" : "assistant";
        return `<div class="bubble ${cls}">${escapeHtml(msg.text)}</div>`;
      })
      .join("");
    stream.scrollTop = stream.scrollHeight;
    $$("[data-approve]", stream).forEach((btn) => {
      btn.addEventListener("click", () => approveTask(btn.dataset.approve, true));
    });
    $$("[data-reject]", stream).forEach((btn) => {
      btn.addEventListener("click", () => approveTask(btn.dataset.reject, false));
    });
    $$("[data-open-task]", stream).forEach((btn) => {
      btn.addEventListener("click", () => {
        state.selectedTaskId = btn.dataset.openTask;
        closeChatDialog();
        setView("tasks");
      });
    });
  }

  async function sendChat(event) {
    event.preventDefault();
    if (state.chatBusy) return;
    if (state.tokenRequired && !getApiToken()) {
      updateTokenUi();
      $("#chat-token-bar")?.classList.remove("hidden");
      toast("Сначала вставьте API token из .env");
      $("#chat-api-token")?.focus();
      return;
    }
    const input = $("#chat-input");
    const goal = input.value.trim();
    if (!goal) return;
    const messages = loadChat();
    messages.push({ role: "user", text: goal });
    messages.push({ role: "assistant", text: "Агент думает…", thinking: true });
    saveChat(messages);
    input.value = "";
    state.chatBusy = true;
    $("#chat-send").disabled = true;
    renderChat();
    try {
      const result = await fetchJson("/tasks/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "admin-chat", goal }),
      });
      const next = loadChat().filter((m) => !m.thinking);
      const reply = result.message || "(пустой ответ)";
      next.push({ role: "assistant", text: reply });
      const action = result.action?.name || "—";
      const verdict = result.policy_decision?.verdict || "—";
      const success = result.success ? "ok" : "fail";
      const taskId = result.observations?.find((o) => o.details?.task_id)?.details?.task_id
        || result.artifacts?.find((a) => a.metadata?.task_id)?.metadata?.task_id
        || "";
      let meta = `<span class="badge ${result.success ? "ok" : "bad"}">${success}</span>
        <span>action: <code>${escapeHtml(action)}</code></span>
        <span>policy: <code>${escapeHtml(verdict)}</code></span>`;
      if (taskId) {
        meta += ` <button type="button" class="linkish" data-open-task="${escapeAttr(taskId)}">Открыть Task</button>`;
      }
      if (verdict === "require-approval" || (!result.success && verdict === "deny")) {
        /* approval uses task store; try recent lookup after run */
      }
      next.push({ role: "meta", html: meta });
      saveChat(next);
      await maybeAttachApprovalForLatest(next);
      renderChat();
    } catch (error) {
      const next = loadChat().filter((m) => !m.thinking);
      next.push({ role: "assistant", text: `Ошибка: ${error.message || error}` });
      saveChat(next);
      renderChat();
    } finally {
      state.chatBusy = false;
      $("#chat-send").disabled = false;
    }
  }

  async function maybeAttachApprovalForLatest(messages) {
    try {
      const recent = await fetchJson("/tasks/recent?limit=5");
      const pending = (recent || []).find((t) => t.state === "awaiting_approval");
      if (!pending) return;
      messages.push({
        role: "meta",
        html: `Task <code>${escapeHtml(pending.id)}</code> ждёт approval.
          <button type="button" class="btn primary" data-approve="${escapeAttr(pending.id)}">Approve</button>
          <button type="button" class="btn danger" data-reject="${escapeAttr(pending.id)}">Reject</button>`,
      });
      saveChat(messages);
    } catch {
      /* ignore */
    }
  }

  async function approveTask(taskId, approved) {
    try {
      await fetchJson(`/tasks/${encodeURIComponent(taskId)}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved, reviewer: "admin-ui" }),
      });
      toast(approved ? "Task approved" : "Task rejected");
      if (state.view === "tasks") refreshTasks();
      if (isChatDialogOpen()) {
        const messages = loadChat();
        messages.push({
          role: "assistant",
          text: approved ? `Task ${taskId} одобрен.` : `Task ${taskId} отклонён.`,
        });
        saveChat(messages);
        renderChat();
      }
    } catch (error) {
      toast(String(error));
    }
  }

  async function refreshTasks() {
    const list = $("#tasks-list");
    list.innerHTML = "<p class='muted'>Загрузка…</p>";
    try {
      state.tasks = await fetchJson("/tasks/recent?limit=30");
      if (!state.tasks.length) {
        list.innerHTML = "<p class='muted'>Задач пока нет.</p>";
        return;
      }
      list.innerHTML = state.tasks
        .map((task) => {
          const active = task.id === state.selectedTaskId ? "active" : "";
          return `<button type="button" class="list-item ${active}" data-task-id="${escapeAttr(task.id)}">
            <strong>${escapeHtml(task.title || "untitled")}</strong>
            <div class="muted">${escapeHtml(task.state || "")} · ${escapeHtml((task.goal || "").slice(0, 80))}</div>
          </button>`;
        })
        .join("");
      $$("[data-task-id]", list).forEach((btn) => {
        btn.addEventListener("click", () => {
          state.selectedTaskId = btn.dataset.taskId;
          renderTaskDetail();
          refreshTasks();
        });
      });
      if (state.selectedTaskId) renderTaskDetail();
    } catch (error) {
      list.innerHTML = `<p class="muted">${escapeHtml(String(error))}</p>`;
    }
  }

  async function renderTaskDetail() {
    const box = $("#task-detail");
    if (!state.selectedTaskId) {
      box.innerHTML = "<p class='muted'>Выберите задачу.</p>";
      return;
    }
    box.innerHTML = "<p class='muted'>Загрузка…</p>";
    try {
      const payload = await fetchJson(`/tasks/${encodeURIComponent(state.selectedTaskId)}`);
      if (!payload.found) {
        box.innerHTML = "<p class='muted'>Task не найден.</p>";
        return;
      }
      const task = payload.task;
      const needsApproval = task.state === "awaiting_approval";
      box.innerHTML = `
        <h2>${escapeHtml(task.title || "Task")}</h2>
        <p><span class="badge ${task.state === "succeeded" ? "ok" : task.state === "failed" ? "bad" : "warn"}">${escapeHtml(task.state)}</span></p>
        <p class="muted"><code>${escapeHtml(task.id)}</code></p>
        <p><strong>Goal</strong></p>
        <pre class="raw">${escapeHtml(task.goal || "")}</pre>
        ${needsApproval ? `
          <div class="row" style="margin-top:12px">
            <button type="button" class="btn primary" id="task-approve">Approve</button>
            <button type="button" class="btn danger" id="task-reject">Reject</button>
          </div>` : ""}
        <details style="margin-top:12px"><summary>JSON</summary><pre class="raw">${escapeHtml(JSON.stringify(task, null, 2))}</pre></details>
      `;
      const approveBtn = $("#task-approve");
      const rejectBtn = $("#task-reject");
      if (approveBtn) approveBtn.addEventListener("click", () => approveTask(task.id, true).then(refreshTasks));
      if (rejectBtn) rejectBtn.addEventListener("click", () => approveTask(task.id, false).then(refreshTasks));
    } catch (error) {
      box.innerHTML = `<p class="muted">${escapeHtml(String(error))}</p>`;
    }
  }

  async function refreshMemory() {
    const list = $("#memory-list");
    list.innerHTML = "<p class='muted'>Загрузка…</p>";
    const q = $("#memory-q").value.trim();
    const kind = $("#memory-kind").value;
    const params = new URLSearchParams({ limit: "50" });
    if (q) params.set("q", q);
    if (kind) params.set("kind", kind);
    try {
      const payload = await fetchJson(`/memory?${params}`);
      state.memory = payload.items || [];
      if (!state.memory.length) {
        list.innerHTML = "<p class='muted'>Пусто.</p>";
        return;
      }
      list.innerHTML = state.memory
        .map((item) => `
          <div class="list-item" style="cursor:default">
            <div class="row" style="justify-content:space-between">
              <strong>${escapeHtml(item.key)}</strong>
              <span class="badge">${escapeHtml(item.kind)}</span>
            </div>
            <div class="muted">${escapeHtml(String(item.value || "").slice(0, 160))}</div>
            <div class="row" style="margin-top:8px">
              <button type="button" class="btn ghost" data-mem-edit="${escapeAttr(item.id)}">Изменить</button>
              <button type="button" class="btn danger" data-mem-del="${escapeAttr(item.id)}">Удалить</button>
            </div>
          </div>`)
        .join("");
      $$("[data-mem-edit]", list).forEach((btn) => {
        btn.addEventListener("click", () => openMemoryEditor(state.memory.find((m) => m.id === btn.dataset.memEdit)));
      });
      $$("[data-mem-del]", list).forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!confirm("Удалить memory item?")) return;
          await fetchJson(`/memory/${encodeURIComponent(btn.dataset.memDel)}`, { method: "DELETE" });
          toast("Удалено");
          refreshMemory();
        });
      });
    } catch (error) {
      list.innerHTML = `<p class="muted">${escapeHtml(String(error))}</p>`;
    }
  }

  function openMemoryEditor(item) {
    const isNew = !item;
    openModal({
      title: isNew ? "Новая Memory" : "Изменить Memory",
      bodyHtml: `
        <div class="form-grid">
          <label>Kind
            <select id="mem-kind">
              ${["preference", "rule", "habit", "fact", "episode"]
                .map((k) => `<option value="${k}" ${item?.kind === k ? "selected" : ""}>${k}</option>`)
                .join("")}
            </select>
          </label>
          <label>Key <input id="mem-key" value="${escapeAttr(item?.key || "")}" /></label>
          <label>Value <textarea id="mem-value" rows="4">${escapeHtml(item?.value || "")}</textarea></label>
          <label>Tags (csv) <input id="mem-tags" value="${escapeAttr((item?.tags || []).join(", "))}" /></label>
        </div>`,
      footHtml: `<button type="button" class="btn ghost" data-close-modal>Отмена</button>
        <button type="button" class="btn primary" id="mem-save">Сохранить</button>`,
    });
    $("#mem-save").addEventListener("click", async () => {
      const body = {
        kind: $("#mem-kind").value,
        key: $("#mem-key").value.trim(),
        value: $("#mem-value").value,
        tags: $("#mem-tags").value.split(",").map((t) => t.trim()).filter(Boolean),
      };
      if (!body.key) {
        toast("Key обязателен");
        return;
      }
      if (isNew) {
        await fetchJson("/memory", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      } else {
        await fetchJson(`/memory/${encodeURIComponent(item.id)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      }
      closeModal();
      toast("Memory сохранена");
      refreshMemory();
    });
  }

  async function refreshStack() {
    const body = $("#stack-body");
    body.innerHTML = "<p class='muted'>Загрузка…</p>";
    try {
      state.status = await fetchJson("/status");
      renderStackTab();
    } catch (error) {
      body.innerHTML = `<p class="muted">${escapeHtml(String(error))}</p>`;
    }
  }

  function renderStackTab() {
    const s = state.status || {};
    const body = $("#stack-body");
    const tab = state.stackTab;
    if (tab === "models") {
      body.innerHTML = `
        <h2>Ollama / Models</h2>
        <p>URL: <code>${escapeHtml(s.ollama_url || "—")}</code> ·
          <span class="badge ${s.ollama_online ? "ok" : "bad"}">${s.ollama_online ? "online" : "offline"}</span></p>
        <pre class="raw">${escapeHtml(JSON.stringify({
          configured: s.models,
          resolved: s.models_resolved,
        }, null, 2))}</pre>`;
    } else if (tab === "perception") {
      body.innerHTML = `<h2>Perception</h2><pre class="raw">${escapeHtml(JSON.stringify(s.perception || {}, null, 2))}</pre>`;
    } else if (tab === "coding") {
      body.innerHTML = `<h2>Coding Agents</h2><pre class="raw">${escapeHtml(JSON.stringify(s.coding_agents || {}, null, 2))}</pre>`;
    } else if (tab === "sandbox") {
      body.innerHTML = `
        <h2>Sandbox &amp; FS</h2>
        <p>Sandbox prefer Docker: <code>${escapeHtml(String(s.sandbox_prefer_docker))}</code></p>
        <p>FS Watch path: <code>${escapeHtml(s.fs_watch?.path || "—")}</code> ·
          available: <code>${escapeHtml(String(s.fs_watch?.available))}</code></p>
        <p>Web search: <code>${escapeHtml(s.web_search?.provider || "—")}</code></p>`;
    } else {
      body.innerHTML = `
        <h2>Telegram</h2>
        <p>Configured: <code>${escapeHtml(String(s.telegram?.configured))}</code></p>
        <p>Available: <code>${escapeHtml(String(s.telegram?.available))}</code></p>`;
    }
  }

  const SETTINGS_CARDS = [
    { id: "general", title: "Общие", desc: "APP_NAME, ENV, LOG_LEVEL, ADMIN_UI_TITLE" },
    { id: "models", title: "Models & Ollama", desc: "Слоты моделей и Ollama URL" },
    { id: "memory", title: "Memory & Qdrant", desc: "Qdrant, embeddings, collection" },
    { id: "paths", title: "Paths", desc: "Logs, audit, tasks, backups, Downloads" },
    { id: "sandbox", title: "Sandbox & Coding Agents", desc: "Docker sandbox и coding CLIs" },
    { id: "voice", title: "Voice / STT", desc: "Язык распознавания речи" },
    { id: "security", title: "API & Security", desc: "Bind, token, trusted hosts" },
    { id: "policy", title: "Policy", desc: "Allow / deny execute actions" },
    { id: "telegram", title: "Telegram", desc: "Bot token и admin chat id" },
    { id: "ops", title: "Операции", desc: "Approve, FS Watch, Voice Transcribe" },
  ];

  async function refreshSettings() {
    const grid = $("#settings-grid");
    grid.innerHTML = SETTINGS_CARDS.map((card) => `
      <button type="button" class="settings-card" data-settings="${card.id}">
        <h3>${card.title}</h3>
        <p>${card.desc}</p>
      </button>`).join("");
    $$("[data-settings]", grid).forEach((btn) => {
      btn.addEventListener("click", () => openSettingsDialog(btn.dataset.settings));
    });
    try {
      state.settings = await fetchJson("/settings");
    } catch (error) {
      toast(`Settings: ${error.message || error}`);
    }
  }

  function field(label, id, value, opts = {}) {
    const type = opts.type || "text";
    if (type === "textarea") {
      return `<label>${label}<textarea id="${id}" rows="${opts.rows || 3}">${escapeHtml(value ?? "")}</textarea></label>`;
    }
    if (type === "checkbox") {
      return `<label class="checks"><input type="checkbox" id="${id}" ${value ? "checked" : ""} /> ${label}</label>`;
    }
    return `<label>${label}<input id="${id}" type="${type}" value="${escapeAttr(value ?? "")}" ${opts.placeholder ? `placeholder="${escapeAttr(opts.placeholder)}"` : ""} /></label>`;
  }

  function s() {
    return (state.settings && state.settings.values) || {};
  }

  function secrets() {
    return (state.settings && state.settings.secrets) || {};
  }

  async function openSettingsDialog(id) {
    if (id === "ops") {
      openOpsDialog();
      return;
    }
    if (!state.settings) {
      try {
        state.settings = await fetchJson("/settings");
      } catch (error) {
        toast(String(error));
        return;
      }
    }
    const v = s();
    const sec = secrets();
    let title = "";
    let body = "";
    if (id === "general") {
      title = "Общие";
      body = `<div class="form-grid">
        ${field("APP_NAME", "f-app_name", v.app_name)}
        ${field("ENV", "f-env", v.env)}
        ${field("LOG_LEVEL", "f-log_level", v.log_level)}
        ${field("ADMIN_UI_TITLE", "f-admin_ui_title", v.admin_ui_title)}
      </div>`;
    } else if (id === "models") {
      title = "Models & Ollama";
      body = `<div class="form-grid">
        ${field("MODEL_PRIMARY", "f-model_primary", v.model_primary)}
        ${field("MODEL_ROUTER", "f-model_router", v.model_router)}
        ${field("MODEL_VISION", "f-model_vision", v.model_vision)}
        ${field("MODEL_EMBED", "f-model_embed", v.model_embed)}
        ${field("OLLAMA_URL", "f-ollama_url", v.ollama_url)}
        <p class="hint">В Docker Compose OLLAMA_URL может переопределяться environment.</p>
      </div>`;
    } else if (id === "memory") {
      title = "Memory & Qdrant";
      body = `<div class="form-grid">
        ${field("QDRANT_URL", "f-qdrant_url", v.qdrant_url)}
        ${field("QDRANT_COLLECTION", "f-qdrant_collection", v.qdrant_collection)}
        ${field("EMBEDDING_DIMENSIONS", "f-embedding_dimensions", v.embedding_dimensions ?? "", { placeholder: "пусто = native" })}
        ${field("Prefer native embedding dims", "f-embedding_prefer_native", v.embedding_prefer_native, { type: "checkbox" })}
        <p class="hint">В Docker Compose QDRANT_URL может переопределяться environment.</p>
      </div>`;
    } else if (id === "paths") {
      title = "Paths";
      body = `<div class="form-grid">
        ${field("RUNTIME_LOG_PATH", "f-runtime_log_path", v.runtime_log_path)}
        ${field("AUDIT_LOG_PATH", "f-audit_log_path", v.audit_log_path)}
        ${field("TASK_STORE_PATH", "f-task_store_path", v.task_store_path)}
        ${field("MEMORY_STORE_PATH", "f-memory_store_path", v.memory_store_path)}
        ${field("BACKUP_DIR", "f-backup_dir", v.backup_dir)}
        ${field("DOWNLOADS_WATCH_PATH", "f-downloads_watch_path", v.downloads_watch_path)}
      </div>`;
    } else if (id === "sandbox") {
      title = "Sandbox & Coding Agents";
      body = `<div class="form-grid">
        ${field("Prefer Docker sandbox", "f-sandbox_prefer_docker", v.sandbox_prefer_docker, { type: "checkbox" })}
        ${field("Coding agents enabled", "f-coding_agents_enabled", v.coding_agents_enabled, { type: "checkbox" })}
        ${field("CODING_AGENT_DEFAULT", "f-coding_agent_default", v.coding_agent_default)}
        ${field("CODING_AGENT_TIMEOUT_SECONDS", "f-coding_agent_timeout_seconds", v.coding_agent_timeout_seconds)}
        ${field("CODING_AGENT_MODEL", "f-coding_agent_model", v.coding_agent_model || "", { placeholder: "пусто = primary" })}
      </div>`;
    } else if (id === "voice") {
      title = "Voice / STT";
      body = `<div class="form-grid">
        ${field("STT_LANGUAGE", "f-stt_language", v.stt_language || "", { placeholder: "пусто / auto = автодетект" })}
      </div>`;
    } else if (id === "security") {
      title = "API & Security";
      body = `<div class="form-grid">
        ${field("API_BIND_HOST", "f-api_bind_host", v.api_bind_host)}
        ${field("TRUSTED_HOSTS", "f-trusted_hosts_raw", v.trusted_hosts_raw)}
        ${field("Require API token", "f-require_api_token", v.require_api_token, { type: "checkbox" })}
        ${field("API_TOKEN", "f-api_token", "", { type: "password", placeholder: sec.api_token?.configured ? "задан · введите новый чтобы заменить" : "не задан" })}
        <label class="checks"><input type="checkbox" id="f-api_token_clear" /> Очистить API token</label>
      </div>`;
    } else if (id === "policy") {
      title = "Policy";
      body = `<div class="form-grid">
        ${field("ALLOWED_EXECUTE_ACTIONS", "f-allowed_execute_actions_raw", v.allowed_execute_actions_raw, { type: "textarea", rows: 4 })}
        ${field("DENIED_EXECUTE_ACTIONS", "f-denied_execute_actions_raw", v.denied_execute_actions_raw, { type: "textarea", rows: 3 })}
      </div>`;
    } else if (id === "telegram") {
      title = "Telegram";
      body = `<div class="form-grid">
        ${field("TELEGRAM_BOT_TOKEN", "f-telegram_bot_token", "", { type: "password", placeholder: sec.telegram_bot_token?.configured ? "задан · введите новый чтобы заменить" : "не задан" })}
        <label class="checks"><input type="checkbox" id="f-telegram_bot_token_clear" /> Очистить bot token</label>
        ${field("TELEGRAM_ADMIN_CHAT_ID", "f-telegram_admin_chat_id", v.telegram_admin_chat_id || "")}
      </div>`;
    }
    openModal({
      title,
      bodyHtml: body,
      footHtml: `<button type="button" class="btn ghost" data-close-modal>Отмена</button>
        <button type="button" class="btn primary" id="settings-save">Сохранить в .env</button>`,
    });
    $("#settings-save").addEventListener("click", () => saveSettingsCategory(id));
  }

  function readCheckbox(id) {
    const el = document.getElementById(id);
    return el ? el.checked : false;
  }

  function readVal(id) {
    const el = document.getElementById(id);
    return el ? el.value : "";
  }

  async function saveSettingsCategory(id) {
    const updates = {};
    const clear_secrets = [];
    if (id === "general") {
      updates.app_name = readVal("f-app_name");
      updates.env = readVal("f-env");
      updates.log_level = readVal("f-log_level");
      updates.admin_ui_title = readVal("f-admin_ui_title");
    } else if (id === "models") {
      updates.model_primary = readVal("f-model_primary");
      updates.model_router = readVal("f-model_router");
      updates.model_vision = readVal("f-model_vision");
      updates.model_embed = readVal("f-model_embed");
      updates.ollama_url = readVal("f-ollama_url");
    } else if (id === "memory") {
      updates.qdrant_url = readVal("f-qdrant_url");
      updates.qdrant_collection = readVal("f-qdrant_collection");
      const dims = readVal("f-embedding_dimensions").trim();
      updates.embedding_dimensions = dims === "" ? null : Number(dims);
      updates.embedding_prefer_native = readCheckbox("f-embedding_prefer_native");
    } else if (id === "paths") {
      updates.runtime_log_path = readVal("f-runtime_log_path");
      updates.audit_log_path = readVal("f-audit_log_path");
      updates.task_store_path = readVal("f-task_store_path");
      updates.memory_store_path = readVal("f-memory_store_path");
      updates.backup_dir = readVal("f-backup_dir");
      updates.downloads_watch_path = readVal("f-downloads_watch_path");
    } else if (id === "sandbox") {
      updates.sandbox_prefer_docker = readCheckbox("f-sandbox_prefer_docker");
      updates.coding_agents_enabled = readCheckbox("f-coding_agents_enabled");
      updates.coding_agent_default = readVal("f-coding_agent_default");
      updates.coding_agent_timeout_seconds = Number(readVal("f-coding_agent_timeout_seconds") || "300");
      updates.coding_agent_model = readVal("f-coding_agent_model");
    } else if (id === "voice") {
      updates.stt_language = readVal("f-stt_language");
    } else if (id === "security") {
      updates.api_bind_host = readVal("f-api_bind_host");
      updates.trusted_hosts_raw = readVal("f-trusted_hosts_raw");
      updates.require_api_token = readCheckbox("f-require_api_token");
      const token = readVal("f-api_token").trim();
      if (token) updates.api_token = token;
      if (readCheckbox("f-api_token_clear")) clear_secrets.push("api_token");
    } else if (id === "policy") {
      updates.allowed_execute_actions_raw = readVal("f-allowed_execute_actions_raw");
      updates.denied_execute_actions_raw = readVal("f-denied_execute_actions_raw");
    } else if (id === "telegram") {
      const token = readVal("f-telegram_bot_token").trim();
      if (token) updates.telegram_bot_token = token;
      if (readCheckbox("f-telegram_bot_token_clear")) clear_secrets.push("telegram_bot_token");
      updates.telegram_admin_chat_id = readVal("f-telegram_admin_chat_id");
    }
    try {
      const result = await fetchJson("/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ updates, clear_secrets }),
      });
      closeModal();
      toast("Сохранено в .env");
      if (result.restart_required) showRestartBanner(true);
      state.settings = await fetchJson("/settings");
    } catch (error) {
      toast(String(error));
    }
  }

  function openOpsDialog() {
    openModal({
      title: "Операции",
      bodyHtml: `
        <div class="form-grid">
          <h3 style="margin:0;font-family:var(--serif)">Approve Task</h3>
          <label>Task ID <input id="ops-task-id" placeholder="uuid" /></label>
          <label>Reviewer <input id="ops-reviewer" value="operator" /></label>
          <div class="row">
            <button type="button" class="btn primary" id="ops-approve">Approve</button>
            <button type="button" class="btn danger" id="ops-reject">Reject</button>
          </div>
          <h3 style="margin:12px 0 0;font-family:var(--serif)">Filesystem Watch</h3>
          <div class="row">
            <button type="button" class="btn primary" id="ops-fs-start">Start</button>
            <button type="button" class="btn ghost" id="ops-fs-events">Events</button>
            <button type="button" class="btn ghost" id="ops-fs-stop">Stop</button>
          </div>
          <h3 style="margin:12px 0 0;font-family:var(--serif)">Voice Transcribe</h3>
          <label>Local audio path <input id="ops-voice-path" placeholder="C:/path/to/audio.ogg" /></label>
          <button type="button" class="btn primary" id="ops-voice">Transcribe</button>
          <pre class="raw" id="ops-out">Idle</pre>
        </div>`,
      footHtml: `<button type="button" class="btn ghost" data-close-modal>Закрыть</button>`,
    });
    const out = () => $("#ops-out");
    $("#ops-approve").addEventListener("click", async () => {
      const taskId = $("#ops-task-id").value.trim();
      const reviewer = $("#ops-reviewer").value.trim() || "operator";
      out().textContent = "Working…";
      try {
        const payload = await fetchJson(`/tasks/${encodeURIComponent(taskId)}/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ approved: true, reviewer }),
        });
        out().textContent = JSON.stringify(payload, null, 2);
      } catch (error) {
        out().textContent = String(error);
      }
    });
    $("#ops-reject").addEventListener("click", async () => {
      const taskId = $("#ops-task-id").value.trim();
      const reviewer = $("#ops-reviewer").value.trim() || "operator";
      out().textContent = "Working…";
      try {
        const payload = await fetchJson(`/tasks/${encodeURIComponent(taskId)}/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ approved: false, reviewer }),
        });
        out().textContent = JSON.stringify(payload, null, 2);
      } catch (error) {
        out().textContent = String(error);
      }
    });
    $("#ops-fs-start").addEventListener("click", async () => {
      out().textContent = "Working…";
      try {
        out().textContent = JSON.stringify(
          await fetchJson("/fs/watch/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ seconds: 0 }),
          }),
          null,
          2,
        );
      } catch (error) {
        out().textContent = String(error);
      }
    });
    $("#ops-fs-events").addEventListener("click", async () => {
      out().textContent = "Working…";
      try {
        out().textContent = JSON.stringify(await fetchJson("/fs/watch/events"), null, 2);
      } catch (error) {
        out().textContent = String(error);
      }
    });
    $("#ops-fs-stop").addEventListener("click", async () => {
      out().textContent = "Working…";
      try {
        out().textContent = JSON.stringify(await fetchJson("/fs/watch/stop", { method: "POST" }), null, 2);
      } catch (error) {
        out().textContent = String(error);
      }
    });
    $("#ops-voice").addEventListener("click", async () => {
      const path = $("#ops-voice-path").value.trim();
      out().textContent = "Working…";
      try {
        out().textContent = JSON.stringify(
          await fetchJson(`/voice/transcribe?channel=admin&audio_path=${encodeURIComponent(path)}`, {
            method: "POST",
          }),
          null,
          2,
        );
      } catch (error) {
        out().textContent = String(error);
      }
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/'/g, "&#39;");
  }

  function bindUi() {
    $$(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        const view = btn.dataset.view;
        if (view === "chat") {
          setView("chat");
          openChatDialog();
          return;
        }
        setView(view);
      });
    });
    $("#btn-refresh-overview").addEventListener("click", refreshOverview);
    $("#btn-overview-chat").addEventListener("click", openChatDialog);
    $("#btn-refresh-tasks").addEventListener("click", refreshTasks);
    $("#btn-refresh-memory").addEventListener("click", refreshMemory);
    $("#btn-refresh-stack").addEventListener("click", refreshStack);
    $("#btn-refresh-settings").addEventListener("click", refreshSettings);
    $("#btn-memory-create").addEventListener("click", () => openMemoryEditor(null));
    $("#memory-q").addEventListener("keydown", (e) => {
      if (e.key === "Enter") refreshMemory();
    });
    $("#memory-kind").addEventListener("change", refreshMemory);
    $("#chat-form").addEventListener("submit", sendChat);
    $("#chat-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        $("#chat-form").requestSubmit();
      }
    });
    const clearHistory = () => {
      saveChat([]);
      if (isChatDialogOpen()) renderChat();
      toast("История чата очищена");
    };
    $("#btn-clear-chat").addEventListener("click", clearHistory);
    $("#btn-clear-chat-dialog").addEventListener("click", clearHistory);
    $("#btn-open-chat-page").addEventListener("click", openChatDialog);
    $("#btn-rail-chat").addEventListener("click", openChatDialog);
    $("#btn-chat-fab").addEventListener("click", openChatDialog);
    $("#chat-dialog-root").addEventListener("click", (e) => {
      if (e.target.matches("[data-close-chat-dialog]")) closeChatDialog();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && isChatDialogOpen()) {
        closeChatDialog();
      }
    });
    $$("#stack-tabs .tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        state.stackTab = tab.dataset.tab;
        $$("#stack-tabs .tab").forEach((t) => t.classList.toggle("active", t === tab));
        renderStackTab();
      });
    });
    $$("[data-close-modal]").forEach((el) => {
      el.addEventListener("click", closeModal);
    });
    $("#modal-root").addEventListener("click", (e) => {
      if (e.target.matches("[data-close-modal]")) closeModal();
    });
    $("#dismiss-banner").addEventListener("click", () => showRestartBanner(false));
    const savedToken = localStorage.getItem(TOKEN_KEY) || "";
    setApiToken(savedToken, { persist: false });
    $("#api-token").addEventListener("change", () => {
      setApiToken($("#api-token").value);
      toast("API token сохранён в браузере");
    });
    $("#api-token").addEventListener("input", () => {
      const chat = $("#chat-api-token");
      if (chat) chat.value = $("#api-token").value;
      updateTokenUi();
    });
    $("#btn-save-chat-token").addEventListener("click", () => {
      setApiToken($("#chat-api-token").value);
      toast(getApiToken() ? "Token сохранён — можно писать агенту" : "Token очищен");
      if (getApiToken()) $("#chat-input")?.focus();
    });
    $("#chat-api-token").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        $("#btn-save-chat-token").click();
      }
    });
    if (sessionStorage.getItem(RESTART_KEY)) showRestartBanner(true);
    refreshTokenRequirement();
  }

  bindUi();
  setView("overview");
})();
