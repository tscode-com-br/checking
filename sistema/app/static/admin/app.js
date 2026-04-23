const authShell = document.getElementById("authShell");
const adminShell = document.getElementById("adminShell");
const statusLine = document.getElementById("statusLine");
const authStatus = document.getElementById("authStatus");
const sessionBar = document.getElementById("sessionBar");
const sessionUserLabel = document.getElementById("sessionUserLabel");
const loginChaveInput = document.getElementById("loginChave");
const loginSenhaInput = document.getElementById("loginSenha");
const changePasswordModal = document.getElementById("changePasswordModal");
const changePasswordForm = document.getElementById("changePasswordForm");
const changePasswordCurrentInput = document.getElementById("changePasswordCurrent");
const changePasswordNewInput = document.getElementById("changePasswordNew");
const changePasswordConfirmInput = document.getElementById("changePasswordConfirm");
const changePasswordBackButton = document.getElementById("changePasswordBackButton");
const changePasswordSaveButton = document.getElementById("changePasswordSaveButton");
const changePasswordStatus = document.getElementById("changePasswordStatus");
const requestAdminButton = document.getElementById("requestAdminButton");
const requestAdminModal = document.getElementById("requestAdminModal");
const requestAdminChaveInput = document.getElementById("requestAdminChave");
const requestAdminStatus = document.getElementById("requestAdminStatus");
const requestAdminBackButton = document.getElementById("requestAdminBackButton");
const requestAdminRegistrationModal = document.getElementById("requestAdminRegistrationModal");
const requestAdminRegistrationForm = document.getElementById("requestAdminRegistrationForm");
const requestAdminRegistrationChaveInput = document.getElementById("requestAdminRegistrationChave");
const requestAdminRegistrationNomeInput = document.getElementById("requestAdminRegistrationNome");
const requestAdminRegistrationProjetoSelect = document.getElementById("requestAdminRegistrationProjeto");
const requestAdminRegistrationSenhaInput = document.getElementById("requestAdminRegistrationSenha");
const requestAdminRegistrationConfirmInput = document.getElementById("requestAdminRegistrationConfirm");
const requestAdminRegistrationBackButton = document.getElementById("requestAdminRegistrationBackButton");
const requestAdminRegistrationSaveButton = document.getElementById("requestAdminRegistrationSaveButton");
const requestAdminRegistrationStatus = document.getElementById("requestAdminRegistrationStatus");

const AUTO_REFRESH_MS = 5000;
const REALTIME_DEBOUNCE_MS = 250;
const ARCHIVE_PAGE_SIZE = 8;
const DATABASE_EVENTS_PAGE_SIZE = 50;
const DATABASE_EVENT_DEFAULT_SORT_KEY = "event_time";
const DATABASE_EVENT_DEFAULT_SORT_DIRECTION = "desc";
const ADMIN_SELF_PASSWORD_VERIFY_DEBOUNCE_MS = 260;
const ADMIN_REQUEST_LOOKUP_DEBOUNCE_MS = 260;

let activeTab = "checkin";
let autoRefreshHandle = null;
let realtimeConnected = false;
let refreshAllTimer = null;
let eventStream = null;
let isAuthenticated = false;
let registeredUsersTotal = 0;
let eventArchives = [];
let eventArchivesFilterQuery = "";
let eventArchivesPage = 1;
let eventArchivesTotal = 0;
let eventArchivesTotalPages = 0;
let eventArchivesTotalSizeBytes = 0;
let nextLocationDraftId = 1;
let nextLocationCoordinateDraftId = 1;
let locationRows = [];
let locationAccuracyThresholdMeters = 30;
let locationSettingsDirty = false;
let pendingUsersTotal = 0;
let administratorsTotal = 0;
let eventsTotal = 0;
let formsTotal = 0;
let lastDashboardRefreshAt = null;
let userTextareaRefreshFrame = null;
let databaseEventsLoaded = false;
let databaseEventsRefreshTimer = null;
let projectCatalog = [];
let changePasswordVerifyTimeout = null;
let changePasswordVerifyRequestToken = 0;
let changePasswordCurrentPasswordValid = false;
let changePasswordCurrentPasswordChecking = false;
let changePasswordSaveInProgress = false;
let requestAdminLookupTimeout = null;
let requestAdminLookupRequestToken = 0;
let requestAdminSelfServiceInProgress = false;
let requestAdminRegistrationSaveInProgress = false;

function createDefaultDatabaseEventFilters() {
  return {
    search: "",
    chave: "",
    rfid: "",
    action: "",
    project: "",
    source: "",
    status: "",
    fromDate: "",
    toDate: "",
  };
}

const databaseEventsState = {
  page: 1,
  pageSize: DATABASE_EVENTS_PAGE_SIZE,
  total: 0,
  totalPages: 1,
  filters: createDefaultDatabaseEventFilters(),
  sortKey: DATABASE_EVENT_DEFAULT_SORT_KEY,
  sortDirection: DATABASE_EVENT_DEFAULT_SORT_DIRECTION,
  filterOptions: {
    action: [],
    chave: [],
    rfid: [],
    project: [],
    source: [],
    status: [],
  },
};

function getProjectCatalogNames() {
  return projectCatalog.map((row) => row.name).filter(Boolean);
}

function getProjectOptions(selectedValue, options = {}) {
  const optionValues = getProjectCatalogNames();
  const normalizedSelectedValue = String(selectedValue ?? "").trim();
  if (options.includeDetachedValue && normalizedSelectedValue && !optionValues.includes(normalizedSelectedValue)) {
    return [normalizedSelectedValue, ...optionValues];
  }
  return optionValues;
}

function normalizeProjectNames(values) {
  return Array.from(new Set(
    Array.from(values || [])
      .map((value) => String(value ?? "").trim())
      .filter(Boolean)
  ));
}

function getLocationProjectOptions(selectedValues = []) {
  const selectedProjectNames = normalizeProjectNames(selectedValues);
  const catalogProjectNames = getProjectCatalogNames();
  const detachedProjectNames = selectedProjectNames.filter((projectName) => !catalogProjectNames.includes(projectName));
  return [...detachedProjectNames, ...catalogProjectNames];
}

function syncSelectOptions(selectElement, optionValues, selectedValue) {
  if (!(selectElement instanceof HTMLSelectElement)) {
    return;
  }

  const nextSelectedValue = String(selectedValue ?? "").trim();
  const fragment = document.createDocumentFragment();
  optionValues.forEach((optionValue) => {
    const option = document.createElement("option");
    option.value = optionValue;
    option.textContent = optionValue;
    fragment.appendChild(option);
  });
  selectElement.replaceChildren(fragment);
  if (optionValues.includes(nextSelectedValue)) {
    selectElement.value = nextSelectedValue;
    return;
  }
  selectElement.value = optionValues[0] || "";
}

function buildProjectOptionsHtml(selectedValue, options = {}) {
  return getProjectOptions(selectedValue, options)
    .map((projectName) => `<option value="${escapeHtml(projectName)}">${escapeHtml(projectName)}</option>`)
    .join("");
}

function setProjectCatalog(rows) {
  projectCatalog = Array.isArray(rows)
    ? rows
      .filter((row) => row && typeof row.name === "string" && row.name.trim())
      .map((row) => ({ id: row.id, name: row.name.trim() }))
    : [];
}

const PRESENCE_TABLE_CONFIGS = {
  checkin: {
    bodyId: "checkinBody",
    filterColumns: ["time", "nome", "chave", "projeto", "assiduidade", "local"],
    defaultSortKey: "time",
    defaultSortDirection: "desc",
    renderOptions: { includeElapsedDays: true },
  },
  checkout: {
    bodyId: "checkoutBody",
    filterColumns: ["time", "nome", "chave", "projeto", "assiduidade", "local"],
    defaultSortKey: "time",
    defaultSortDirection: "desc",
    renderOptions: {},
  },
  inactive: {
    bodyId: "inactiveBody",
    filterColumns: ["nome", "chave", "projeto", "latest_time", "inactivity_days"],
    defaultSortKey: "inactivity_days",
    defaultSortDirection: "desc",
    renderOptions: {},
  },
  missingCheckout: {
    bodyId: "missingCheckoutBody",
    filterColumns: ["nome", "chave", "time"],
    defaultSortKey: "time",
    defaultSortDirection: "desc",
    renderOptions: {},
  },
};
const presenceTableStates = Object.fromEntries(
  Object.entries(PRESENCE_TABLE_CONFIGS).map(([tableKey, config]) => [
    tableKey,
    createPresenceTableState(tableKey, config),
  ]),
);
const TAB_LABELS = {
  checkin: "Check-In",
  checkout: "Check-Out",
  forms: "Forms",
  inactive: "Inativos",
  cadastro: "Cadastro",
  eventos: "Eventos",
  "banco-dados": "Banco de Dados",
};

function createPresenceFilterState(filterColumns) {
  return Object.fromEntries(filterColumns.map((key) => [key, ""]));
}

function createPresenceTableState(tableKey, config) {
  return {
    tableKey,
    bodyId: config.bodyId,
    renderOptions: config.renderOptions || {},
    filterColumns: config.filterColumns || [],
    defaultSortKey: config.defaultSortKey,
    defaultSortDirection: config.defaultSortDirection,
    rawRows: [],
    filters: createPresenceFilterState(config.filterColumns || []),
    sortKey: config.defaultSortKey,
    sortDirection: config.defaultSortDirection,
  };
}

function setAuthStatus(message, kind = "info") {
  authStatus.textContent = message || "";
  authStatus.className = `auth-status ${kind === "error" ? "status-err" : kind === "success" ? "status-ok" : ""}`;
}

function setChangePasswordStatus(message, kind = "info") {
  if (!changePasswordStatus) {
    return;
  }

  changePasswordStatus.textContent = message || "";
  changePasswordStatus.className = `auth-status ${kind === "error" ? "status-err" : kind === "success" ? "status-ok" : ""}`;
}

function normalizeAdminChave(value) {
  return String(value || "")
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, 4);
}

function isAdminCurrentPasswordInputValid(value) {
  const password = String(value || "");
  return password.length >= 3 && password.length <= 20 && password.trim().length > 0;
}

function isAdminNewPasswordInputValid(value) {
  const password = String(value || "");
  return password.length >= 3 && password.length <= 10 && password.trim().length > 0;
}

function isChangePasswordModalOpen() {
  return Boolean(changePasswordModal && !changePasswordModal.classList.contains("hidden"));
}

function clearChangePasswordVerificationTimer() {
  if (changePasswordVerifyTimeout !== null) {
    window.clearTimeout(changePasswordVerifyTimeout);
    changePasswordVerifyTimeout = null;
  }
  changePasswordVerifyRequestToken += 1;
}

function syncChangePasswordFormState() {
  if (!changePasswordSaveButton) {
    return;
  }

  const chave = normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "");
  const currentPassword = String(changePasswordCurrentInput ? changePasswordCurrentInput.value : "");
  const newPassword = String(changePasswordNewInput ? changePasswordNewInput.value : "");
  const confirmPassword = String(changePasswordConfirmInput ? changePasswordConfirmInput.value : "");
  const canSave = chave.length === 4
    && changePasswordCurrentPasswordValid
    && isAdminNewPasswordInputValid(newPassword)
    && newPassword !== currentPassword
    && confirmPassword === newPassword
    && !changePasswordCurrentPasswordChecking
    && !changePasswordSaveInProgress;

  changePasswordSaveButton.disabled = !canSave;
  changePasswordSaveButton.textContent = changePasswordSaveInProgress ? "Salvando..." : "Salvar";

  [changePasswordCurrentInput, changePasswordNewInput, changePasswordConfirmInput, changePasswordBackButton]
    .filter(Boolean)
    .forEach((element) => {
      element.disabled = changePasswordSaveInProgress;
    });
}

function resetChangePasswordVerificationState() {
  clearChangePasswordVerificationTimer();
  changePasswordCurrentPasswordValid = false;
  changePasswordCurrentPasswordChecking = false;
}

function openChangePasswordModal() {
  const normalizedChave = normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "");
  if (loginChaveInput && normalizedChave !== loginChaveInput.value) {
    loginChaveInput.value = normalizedChave;
  }

  if (normalizedChave.length !== 4) {
    setAuthStatus("Informe sua chave antes de alterar a senha.", "error");
    if (loginChaveInput) {
      loginChaveInput.focus();
    }
    return;
  }

  if (!changePasswordModal || !changePasswordForm) {
    return;
  }

  changePasswordForm.reset();
  changePasswordSaveInProgress = false;
  resetChangePasswordVerificationState();
  setChangePasswordStatus("");
  changePasswordModal.classList.remove("hidden");
  changePasswordModal.setAttribute("aria-hidden", "false");
  syncChangePasswordFormState();
  if (changePasswordCurrentInput) {
    changePasswordCurrentInput.focus();
  }
}

function closeChangePasswordModal() {
  if (!changePasswordModal) {
    return;
  }

  if (changePasswordForm) {
    changePasswordForm.reset();
  }
  changePasswordSaveInProgress = false;
  resetChangePasswordVerificationState();
  setChangePasswordStatus("");
  changePasswordModal.classList.add("hidden");
  changePasswordModal.setAttribute("aria-hidden", "true");
  syncChangePasswordFormState();
}

function isStaleChangePasswordVerification(chave, currentPassword, requestToken) {
  return requestToken !== changePasswordVerifyRequestToken
    || !isChangePasswordModalOpen()
    || normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "") !== chave
    || String(changePasswordCurrentInput ? changePasswordCurrentInput.value : "") !== currentPassword;
}

async function verifyCurrentAdminPassword(chave, currentPassword, requestToken) {
  try {
    const payload = await postJson("/api/admin/auth/verify-current-password", {
      chave,
      senha_atual: currentPassword,
    });

    if (isStaleChangePasswordVerification(chave, currentPassword, requestToken)) {
      return;
    }

    changePasswordCurrentPasswordValid = Boolean(payload.valid);
    setChangePasswordStatus(payload.valid ? "Senha atual confirmada." : payload.message, payload.valid ? "success" : "error");
  } catch (error) {
    if (isStaleChangePasswordVerification(chave, currentPassword, requestToken)) {
      return;
    }

    changePasswordCurrentPasswordValid = false;
    setChangePasswordStatus(error.message, "error");
  } finally {
    if (isStaleChangePasswordVerification(chave, currentPassword, requestToken)) {
      return;
    }

    changePasswordCurrentPasswordChecking = false;
    syncChangePasswordFormState();
  }
}

function scheduleChangePasswordVerification() {
  if (!isChangePasswordModalOpen()) {
    return;
  }

  const chave = normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "");
  const currentPassword = String(changePasswordCurrentInput ? changePasswordCurrentInput.value : "");

  resetChangePasswordVerificationState();
  if (!chave || !isAdminCurrentPasswordInputValid(currentPassword)) {
    if (!currentPassword) {
      setChangePasswordStatus("");
    }
    syncChangePasswordFormState();
    return;
  }

  const requestToken = changePasswordVerifyRequestToken;
  changePasswordCurrentPasswordChecking = true;
  setChangePasswordStatus("Verificando senha atual...", "info");
  syncChangePasswordFormState();
  changePasswordVerifyTimeout = window.setTimeout(() => {
    void verifyCurrentAdminPassword(chave, currentPassword, requestToken);
  }, ADMIN_SELF_PASSWORD_VERIFY_DEBOUNCE_MS);
}

async function submitChangePassword() {
  const chave = normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "");
  const currentPassword = String(changePasswordCurrentInput ? changePasswordCurrentInput.value : "");
  const newPassword = String(changePasswordNewInput ? changePasswordNewInput.value : "");
  const confirmPassword = String(changePasswordConfirmInput ? changePasswordConfirmInput.value : "");

  if (chave.length !== 4) {
    setChangePasswordStatus("Informe sua chave antes de alterar a senha.", "error");
    if (loginChaveInput) {
      loginChaveInput.focus();
    }
    return;
  }
  if (!isAdminCurrentPasswordInputValid(currentPassword)) {
    setChangePasswordStatus("A senha atual deve ter entre 3 e 20 caracteres.", "error");
    if (changePasswordCurrentInput) {
      changePasswordCurrentInput.focus();
    }
    return;
  }
  if (!changePasswordCurrentPasswordValid) {
    setChangePasswordStatus("A senha atual nao confere.", "error");
    if (changePasswordCurrentInput) {
      changePasswordCurrentInput.focus();
    }
    return;
  }
  if (!isAdminNewPasswordInputValid(newPassword)) {
    setChangePasswordStatus("A nova senha deve ter entre 3 e 10 caracteres.", "error");
    if (changePasswordNewInput) {
      changePasswordNewInput.focus();
    }
    return;
  }
  if (newPassword === currentPassword) {
    setChangePasswordStatus("A nova senha deve ser diferente da senha atual.", "error");
    if (changePasswordNewInput) {
      changePasswordNewInput.focus();
    }
    return;
  }
  if (confirmPassword !== newPassword) {
    setChangePasswordStatus("A confirmação da senha deve ser idêntica à nova senha.", "error");
    if (changePasswordConfirmInput) {
      changePasswordConfirmInput.focus();
    }
    return;
  }

  changePasswordSaveInProgress = true;
  syncChangePasswordFormState();
  setChangePasswordStatus("Salvando nova senha...", "info");

  try {
    const payload = await postJson("/api/admin/auth/change-password", {
      chave,
      senha_atual: currentPassword,
      nova_senha: newPassword,
      confirmar_senha: confirmPassword,
    });
    if (loginSenhaInput) {
      loginSenhaInput.value = newPassword;
    }
    closeChangePasswordModal();
    setAuthStatus(payload.message, "success");
  } catch (error) {
    setChangePasswordStatus(error.message, "error");
  } finally {
    changePasswordSaveInProgress = false;
    syncChangePasswordFormState();
  }
}

function setStatus(message, ok = true) {
  statusLine.textContent = message;
  statusLine.className = ok ? "status-ok" : "status-err";
}

function clearStatus() {
  statusLine.textContent = "";
  statusLine.className = "";
}

function setTextContentIfPresent(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function formatDashboardRefreshTime(value) {
  if (!(value instanceof Date) || Number.isNaN(value.getTime())) {
    return "Sem atualização";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(value);
}

function updateOperationalChrome() {
  const currentTabLabel = TAB_LABELS[activeTab] || "Painel";
  let realtimeLabel = "Aguardando sessão";
  let realtimeTone = "waiting";
  let connectionSummary = "Aguardando autenticação";

  if (isAuthenticated && realtimeConnected) {
    realtimeLabel = "Tempo real ativo";
    realtimeTone = "live";
    connectionSummary = "Sincronização em tempo real";
  } else if (isAuthenticated) {
    realtimeLabel = "Atualização periódica";
    realtimeTone = "polling";
    connectionSummary = "Fallback por polling a cada 5 s";
  }

  const realtimeBadge = document.getElementById("realtimeStatusBadge");
  if (realtimeBadge) {
    realtimeBadge.textContent = realtimeLabel;
    realtimeBadge.className = `topbar-pill topbar-pill-live is-${realtimeTone}`;
  }

  const lastRefreshLabel = lastDashboardRefreshAt
    ? `Atualizado às ${formatDashboardRefreshTime(lastDashboardRefreshAt)}`
    : "Sem atualização";

  setTextContentIfPresent("lastRefreshBadge", lastRefreshLabel);
  setTextContentIfPresent("activeTabBadge", `Aba atual: ${currentTabLabel}`);
  setTextContentIfPresent("heroMetricConnection", connectionSummary);
  setTextContentIfPresent("heroMetricRefresh", lastRefreshLabel);
  setTextContentIfPresent("heroMetricCurrentTab", currentTabLabel);
  setTextContentIfPresent(
    "heroMetricCoverage",
    registeredUsersTotal === 1 ? "1 usuário monitorado" : `${registeredUsersTotal} usuários monitorados`,
  );
}

function updateDashboardSummary() {
  const counts = {
    checkin: presenceTableStates.checkin.rawRows.length,
    checkout: presenceTableStates.checkout.rawRows.length,
    forms: formsTotal,
    inactive: presenceTableStates.inactive.rawRows.length,
    pending: pendingUsersTotal,
    users: registeredUsersTotal,
    events: eventsTotal,
    missingCheckout: presenceTableStates.missingCheckout.rawRows.length,
    cadastro: registeredUsersTotal,
    eventos: eventsTotal,
    "banco-dados": databaseEventsState.total,
  };

  Object.entries(counts).forEach(([key, value]) => {
    document.querySelectorAll(`[data-dashboard-stat-value="${key}"]`).forEach((element) => {
      element.textContent = String(value);
    });
    document.querySelectorAll(`[data-tab-count-for="${key}"]`).forEach((element) => {
      element.textContent = String(value);
    });
  });

  const criticalPendingLabel = counts.missingCheckout === 0
    ? "Nenhuma pendência crítica"
    : counts.missingCheckout === 1
      ? "1 check-out pendente"
      : `${counts.missingCheckout} check-outs pendentes`;

  const adminCoverageLabel = administratorsTotal === 0
    ? "Sem administradores visíveis"
    : administratorsTotal === 1
      ? "1 administrador visível"
      : `${administratorsTotal} administradores visíveis`;

  setTextContentIfPresent("heroMetricPending", criticalPendingLabel);
  setTextContentIfPresent("heroMetricAdminCoverage", adminCoverageLabel);
  updateOperationalChrome();
}

function markDashboardRefreshed() {
  lastDashboardRefreshAt = new Date();
  updateOperationalChrome();
}

function showAuthShell(message = "", kind = "info") {
  isAuthenticated = false;
  locationSettingsDirty = false;
  lastDashboardRefreshAt = null;
  closeChangePasswordModal();
  formsTotal = 0;
  databaseEventsLoaded = false;
  if (databaseEventsRefreshTimer !== null) {
    window.clearTimeout(databaseEventsRefreshTimer);
    databaseEventsRefreshTimer = null;
  }
  databaseEventsState.page = 1;
  databaseEventsState.total = 0;
  databaseEventsState.totalPages = 1;
  databaseEventsState.pageSize = DATABASE_EVENTS_PAGE_SIZE;
  databaseEventsState.filters = createDefaultDatabaseEventFilters();
  databaseEventsState.sortKey = DATABASE_EVENT_DEFAULT_SORT_KEY;
  databaseEventsState.sortDirection = DATABASE_EVENT_DEFAULT_SORT_DIRECTION;
  databaseEventsState.filterOptions = {
    action: [],
    chave: [],
    rfid: [],
    project: [],
    source: [],
    status: [],
  };
  syncDatabaseEventFilterOptions();
  syncDatabaseEventFilterInputs();
  syncDatabaseEventSortHeaders();
  authShell.classList.remove("hidden");
  adminShell.classList.add("hidden");
  sessionBar.classList.add("hidden");
  stopRealtimeUpdates();
  stopAutoRefresh();
  setAuthStatus(message, kind);
  clearStatus();
  updateOperationalChrome();
}

function showAdminShell(admin) {
  isAuthenticated = true;
  authShell.classList.add("hidden");
  adminShell.classList.remove("hidden");
  sessionBar.classList.remove("hidden");
  sessionUserLabel.textContent = `${admin.nome_completo} (${admin.chave})`;
  setAuthStatus("");
  updateOperationalChrome();
}

function applyResponsiveLabels(tbodyId) {
  const body = document.getElementById(tbodyId);
  if (!body) {
    return;
  }
  const table = body.closest("table");
  if (!table) {
    return;
  }
  const headers = Array.from(table.querySelectorAll("thead th")).map((th) => {
    const sortableLabel = th.querySelector(".sortable-header span")?.textContent?.trim();
    return sortableLabel || th.textContent.trim();
  });
  body.querySelectorAll("tr").forEach((tr) => {
    Array.from(tr.children).forEach((cell, idx) => {
      if (cell.tagName === "TD") {
        cell.setAttribute("data-label", headers[idx] || "Campo");
      }
    });
  });
}

function escapeHtml(value) {
  return String(value ?? "-")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function updateAdaptiveInputWidth(input, minimumCharacters = 4) {
  if (!(input instanceof HTMLInputElement)) {
    return;
  }
  const characterCount = Math.max(minimumCharacters, String(input.value || "").trim().length || 0);
  input.style.width = `${characterCount + 1}ch`;
}

function bindAdaptiveInputWidth(input, minimumCharacters = 4) {
  if (!(input instanceof HTMLInputElement)) {
    return;
  }
  updateAdaptiveInputWidth(input, minimumCharacters);
  input.addEventListener("input", () => updateAdaptiveInputWidth(input, minimumCharacters));
}

function updateAutoTextareaHeight(textarea) {
  if (!(textarea instanceof HTMLTextAreaElement)) {
    return;
  }

  const minimumHeightPx = Number(textarea.dataset.minHeightPx || 0);
  textarea.style.height = "auto";
  textarea.style.height = `${Math.max(textarea.scrollHeight, minimumHeightPx)}px`;
}

function bindAutoTextareaHeight(textarea) {
  if (!(textarea instanceof HTMLTextAreaElement)) {
    return;
  }

  if (!textarea.dataset.minHeightPx) {
    textarea.style.height = "auto";
    textarea.dataset.minHeightPx = String(textarea.scrollHeight);
  }
  updateAutoTextareaHeight(textarea);
  textarea.addEventListener("input", () => updateAutoTextareaHeight(textarea));
}

function refreshUserFieldTextareaHeights() {
  document.querySelectorAll(".user-field-textarea").forEach((textarea) => {
    updateAutoTextareaHeight(textarea);
  });
}

function scheduleUserFieldTextareaRefresh() {
  if (userTextareaRefreshFrame !== null) {
    window.cancelAnimationFrame(userTextareaRefreshFrame);
  }

  userTextareaRefreshFrame = window.requestAnimationFrame(() => {
    userTextareaRefreshFrame = null;
    refreshUserFieldTextareaHeights();
  });
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).replace("T", " ").replace(/\.\d+Z?$/, "").replace(/Z$/, "");
  }

  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Singapore",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function formatDateTimeLines(value) {
  const formatted = formatDateTime(value);
  if (formatted === "-") {
    return { date: "-", time: "" };
  }

  const [datePart, timePart, ...rest] = String(formatted).split(" ");
  return {
    date: datePart || formatted,
    time: [timePart, ...rest].filter(Boolean).join(" "),
  };
}

function getSingaporeDayKey(value) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Singapore",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);

  const year = parts.find((part) => part.type === "year")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  const day = parts.find((part) => part.type === "day")?.value;
  if (!year || !month || !day) {
    return null;
  }

  return `${year}-${month}-${day}`;
}

function formatLocal(local) {
  if (local === "main") {
    return "Escritório Principal";
  }
  if (local === "co80") {
    return "Escritório Avançado P80";
  }
  if (local === "un80") {
    return "A bordo da P80";
  }
  if (local === "co83") {
    return "Escritório Avançado P83";
  }
  if (local === "un83") {
    return "A bordo da P83";
  }
  return local || "-";
}

function formatAction(action) {
  if (action === "checkin") {
    return "Check-In";
  }
  if (action === "checkout") {
    return "Check-Out";
  }
  if (action === "register") {
    return "Cadastro";
  }
  if (action === "admin_request") {
    return "Solicitação Admin";
  }
  if (action === "admin_access") {
    return "Admin";
  }
  if (action === "password") {
    return "Senha";
  }
  if (action === "location") {
    return "Localização";
  }
  if (action === "location_config" || action === "location_setting") {
    return "Configuração de Localização";
  }
  if (action === "event_archive") {
    return "Arquivo Eventos";
  }
  return action;
}

function formatEventDetails(details) {
  if (!details) {
    return "-";
  }

  const cleanedParts = String(details)
    .split(";")
    .map((part) => part.trim())
    .filter((part) => part && !part.startsWith("final_url="));

  return cleanedParts.length > 0 ? cleanedParts.join("; ") : "-";
}

function makeEventCell(value, extraClass = "") {
  const className = extraClass ? `event-cell ${extraClass}` : "event-cell";
  return `<span class="${className}">${escapeHtml(value ?? "-")}</span>`;
}

function makeEventDateTimeCell(value) {
  const { date, time } = formatDateTimeLines(value);
  return `
    <span class="event-cell event-datetime-cell">
      <span class="event-datetime-line">${escapeHtml(date)}</span>
      ${time ? `<span class="event-datetime-line">${escapeHtml(time)}</span>` : ""}
    </span>
  `;
}

function makeEventDetailsButton() {
  return '<button type="button" class="event-details-button">Detalhes</button>';
}

function buildDatabaseEventsQueryParams() {
  const params = new URLSearchParams();
  params.set("page", String(databaseEventsState.page));
  params.set("page_size", String(databaseEventsState.pageSize));
  params.set("sort_by", databaseEventsState.sortKey);
  params.set("sort_direction", databaseEventsState.sortDirection);

  const normalizedKey = databaseEventsState.filters.chave.trim().toUpperCase();
  const normalizedRfid = databaseEventsState.filters.rfid.trim();
  const normalizedSearch = databaseEventsState.filters.search.trim();
  const normalizedSource = databaseEventsState.filters.source.trim().toLowerCase();
  const normalizedStatus = databaseEventsState.filters.status.trim().toLowerCase();
  const normalizedAction = databaseEventsState.filters.action.trim().toLowerCase();
  const normalizedProject = databaseEventsState.filters.project.trim().toUpperCase();

  if (normalizedSearch) {
    params.set("search", normalizedSearch);
  }
  if (normalizedKey) {
    params.set("chave", normalizedKey);
  }
  if (normalizedRfid) {
    params.set("rfid", normalizedRfid);
  }
  if (normalizedAction) {
    params.set("action", normalizedAction);
  }
  if (normalizedProject) {
    params.set("project", normalizedProject);
  }
  if (normalizedSource) {
    params.set("source", normalizedSource);
  }
  if (normalizedStatus) {
    params.set("status", normalizedStatus);
  }
  if (databaseEventsState.filters.fromDate) {
    params.set("from_date", databaseEventsState.filters.fromDate);
  }
  if (databaseEventsState.filters.toDate) {
    params.set("to_date", databaseEventsState.filters.toDate);
  }

  return params;
}

function syncDatabaseEventFilterInputs() {
  const textInputIds = {
    search: "databaseEventsSearch",
    fromDate: "databaseEventsFromDate",
    toDate: "databaseEventsToDate",
  };

  Object.entries(textInputIds).forEach(([filterKey, elementId]) => {
    const element = document.getElementById(elementId);
    if (element) {
      element.value = databaseEventsState.filters[filterKey] ?? "";
    }
  });

  const selectFilterIds = {
    chave: "databaseEventsKey",
    rfid: "databaseEventsRfid",
    action: "databaseEventsAction",
    project: "databaseEventsProject",
    source: "databaseEventsSource",
    status: "databaseEventsStatus",
  };

  Object.entries(selectFilterIds).forEach(([filterKey, elementId]) => {
    const selectElement = document.getElementById(elementId);
    if (selectElement instanceof HTMLSelectElement) {
      selectElement.value = databaseEventsState.filters[filterKey] ?? "";
    }
  });
}

function syncDatabaseEventFilterOptions() {
  const filterSelects = {
    chave: "databaseEventsKey",
    rfid: "databaseEventsRfid",
    action: "databaseEventsAction",
    project: "databaseEventsProject",
    source: "databaseEventsSource",
    status: "databaseEventsStatus",
  };

  Object.entries(filterSelects).forEach(([filterKey, elementId]) => {
    const selectElement = document.getElementById(elementId);
    if (!(selectElement instanceof HTMLSelectElement)) {
      return;
    }

    const optionValues = Array.isArray(databaseEventsState.filterOptions[filterKey])
      ? databaseEventsState.filterOptions[filterKey]
      : [];
    const currentValue = String(databaseEventsState.filters[filterKey] || "").trim();
    const values = currentValue && !optionValues.includes(currentValue)
      ? [currentValue, ...optionValues]
      : optionValues;
    const fragment = document.createDocumentFragment();
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "Todos";
    fragment.appendChild(defaultOption);
    values.forEach((optionValue) => {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionValue;
      fragment.appendChild(option);
    });
    selectElement.replaceChildren(fragment);
    selectElement.value = values.includes(currentValue) ? currentValue : "";
    if (!values.includes(currentValue)) {
      databaseEventsState.filters[filterKey] = "";
    }
  });
}

function getDatabaseEventDefaultSortDirection(sortKey) {
  if (["id", "event_time", "http_status"].includes(sortKey)) {
    return "desc";
  }
  return "asc";
}

function syncDatabaseEventSortHeaders() {
  document.querySelectorAll('.sortable-header[data-sort-table="databaseEvents"]').forEach((button) => {
    const isActive = button.dataset.sortKey === databaseEventsState.sortKey;
    button.classList.toggle("is-active", isActive);
    const indicator = button.querySelector(".sort-indicator");
    if (indicator) {
      indicator.textContent = isActive ? (databaseEventsState.sortDirection === "asc" ? "↑" : "↓") : "↕";
    }
    const parentHeader = button.closest("th");
    if (parentHeader) {
      parentHeader.setAttribute(
        "aria-sort",
        isActive ? (databaseEventsState.sortDirection === "asc" ? "ascending" : "descending") : "none",
      );
    }
  });
}

function applyDatabaseEventSort(sortKey) {
  if (!sortKey) {
    return;
  }

  if (databaseEventsState.sortKey === sortKey) {
    databaseEventsState.sortDirection = databaseEventsState.sortDirection === "asc" ? "desc" : "asc";
  } else {
    databaseEventsState.sortKey = sortKey;
    databaseEventsState.sortDirection = getDatabaseEventDefaultSortDirection(sortKey);
  }

  databaseEventsState.page = 1;
  syncDatabaseEventSortHeaders();
}

function updateDatabaseEventsInsights(rows) {
  const visibleCount = rows.length;
  const visibleCheckins = rows.filter((row) => row.action === "checkin").length;
  const visibleCheckouts = rows.filter((row) => row.action === "checkout").length;
  const total = databaseEventsState.total;
  const page = databaseEventsState.page;
  const totalPages = databaseEventsState.totalPages;
  const startRow = total === 0 ? 0 : (page - 1) * databaseEventsState.pageSize + 1;
  const endRow = total === 0 ? 0 : startRow + visibleCount - 1;

  setTextContentIfPresent("databaseEventsTotalCount", String(total));
  setTextContentIfPresent("databaseEventsVisibleCount", String(visibleCount));
  setTextContentIfPresent("databaseEventsCheckinCount", String(visibleCheckins));
  setTextContentIfPresent("databaseEventsCheckoutCount", String(visibleCheckouts));
  setTextContentIfPresent(
    "databaseEventsResultSummary",
    total === 1 ? "1 evento encontrado" : `${total} eventos encontrados`,
  );
  setTextContentIfPresent("databaseEventsPageInfo", `Página ${page} de ${totalPages}`);
  setTextContentIfPresent(
    "databaseEventsPaginationSummary",
    total === 0 ? "Nenhum evento corresponde aos filtros atuais." : `Mostrando ${startRow}-${endRow} de ${total} eventos.`,
  );

  const previousButton = document.getElementById("databaseEventsPrev");
  if (previousButton) {
    previousButton.disabled = page <= 1 || total === 0;
  }
  const nextButton = document.getElementById("databaseEventsNext");
  if (nextButton) {
    nextButton.disabled = page >= totalPages || total === 0;
  }
}

function renderDatabaseEvents(rows) {
  const body = document.getElementById("databaseEventsBody");
  if (!body) {
    return;
  }

  body.innerHTML = "";
  if (!rows.length) {
    renderEmptyStateRow("databaseEventsBody", 13, "Nenhum evento encontrado para os filtros informados.");
    updateDatabaseEventsInsights([]);
    return;
  }

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    const eventDetails = {
      message: row.message ?? "-",
      details: formatEventDetails(row.details),
    };
    tr.innerHTML = `<td>${makeEventCell(row.id)}</td><td>${makeEventDateTimeCell(row.event_time)}</td><td>${makeEventCell(formatAction(row.action))}</td><td>${makeEventCell(row.chave ?? "-")}</td><td>${makeEventCell(row.rfid ?? "-")}</td><td>${makeEventCell(row.project ?? "-")}</td><td>${makeEventCell(formatLocal(row.local), "event-cell-left")}</td><td>${makeEventCell(row.source ?? "-")}</td><td>${makeEventCell(row.status ?? "-")}</td><td>${makeEventCell(row.http_status ?? "-")}</td><td>${makeEventCell(row.device_id ?? "-", "event-cell-left")}</td><td>${makeEventCell(row.message ?? "-", "event-cell-left")}</td><td>${makeEventDetailsButton()}</td>`;
    tr.querySelector(".event-details-button").addEventListener("click", () => openEventDetails(eventDetails));
    body.appendChild(tr);
  });

  applyResponsiveLabels("databaseEventsBody");
  updateDatabaseEventsInsights(rows);
}

function scheduleDatabaseEventsRefresh(delayMs = REALTIME_DEBOUNCE_MS) {
  if (!isAuthenticated || !document.getElementById("databaseEventsBody")) {
    return;
  }

  if (databaseEventsRefreshTimer !== null) {
    window.clearTimeout(databaseEventsRefreshTimer);
  }

  databaseEventsRefreshTimer = window.setTimeout(() => {
    loadDatabaseEvents().catch((error) => setStatus(error.message, false));
    databaseEventsRefreshTimer = null;
  }, delayMs);
}

function resetDatabaseEventFilters() {
  databaseEventsState.page = 1;
  databaseEventsState.total = 0;
  databaseEventsState.totalPages = 1;
  databaseEventsState.filters = createDefaultDatabaseEventFilters();
  syncDatabaseEventFilterInputs();
}

async function loadDatabaseEvents() {
  if (!document.getElementById("databaseEventsBody")) {
    return;
  }

  const { fromDate, toDate } = databaseEventsState.filters;
  if (fromDate && toDate && fromDate > toDate) {
    throw new Error("O período informado é inválido. Ajuste as datas de início e fim.");
  }

  const params = buildDatabaseEventsQueryParams();
  const payload = await fetchJson(`/api/admin/database-events?${params.toString()}`);
  const rows = Array.isArray(payload?.items) ? payload.items : [];

  databaseEventsLoaded = true;
  databaseEventsState.total = Number(payload?.total) || 0;
  databaseEventsState.page = Number(payload?.page) || 1;
  databaseEventsState.pageSize = Number(payload?.page_size) || DATABASE_EVENTS_PAGE_SIZE;
  databaseEventsState.totalPages = Math.max(1, Number(payload?.total_pages) || 1);
  databaseEventsState.filterOptions = {
    action: Array.isArray(payload?.filter_options?.action) ? payload.filter_options.action : [],
    chave: Array.isArray(payload?.filter_options?.chave) ? payload.filter_options.chave : [],
    rfid: Array.isArray(payload?.filter_options?.rfid) ? payload.filter_options.rfid : [],
    project: Array.isArray(payload?.filter_options?.project) ? payload.filter_options.project : [],
    source: Array.isArray(payload?.filter_options?.source) ? payload.filter_options.source : [],
    status: Array.isArray(payload?.filter_options?.status) ? payload.filter_options.status : [],
  };

  syncDatabaseEventFilterOptions();
  syncDatabaseEventFilterInputs();
  syncDatabaseEventSortHeaders();
  renderDatabaseEvents(rows);
  updateDashboardSummary();
}

function formatOntime(value) {
  if (value === true) return "Sim";
  if (value === false) return "Não";
  return "-";
}

function parseErrorPayload(payload, fallback) {
  if (!payload) {
    return fallback;
  }
  if (typeof payload.detail === "string") {
    return payload.detail;
  }
  if (Array.isArray(payload.detail) && payload.detail.length > 0) {
    return payload.detail.map((item) => item.msg || item.message || "Erro de validação").join("; ");
  }
  return fallback;
}

async function parseErrorResponse(res) {
  let payload = null;
  try {
    payload = await res.json();
  } catch {
    payload = null;
  }

  if (res.status === 401) {
    return parseErrorPayload(payload, "Sua sessão expirou. Faça login novamente.");
  }
  return parseErrorPayload(payload, `HTTP ${res.status}`);
}

async function handleUnauthorized(message) {
  if (!isAuthenticated) {
    setAuthStatus(message, "error");
    return;
  }

  showAuthShell(message || "Sua sessão expirou. Faça login novamente.", "error");
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const message = await parseErrorResponse(res);
    if (res.status === 401) {
      await handleUnauthorized(message);
    }
    throw new Error(message);
  }

  if (res.status === 204) {
    return null;
  }

  return res.json();
}

async function postJson(url, body) {
  const options = {
    method: "POST",
    headers: {},
  };
  if (body !== null && body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  return fetchJson(url, options);
}

async function deleteJson(url) {
  return fetchJson(url, { method: "DELETE" });
}

function requireIntegerId(value, label) {
  const normalized = String(value ?? "").trim();
  if (!/^\d+$/.test(normalized)) {
    throw new Error(`${label} inválido para esta ação.`);
  }
  return normalized;
}

function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll(".tabs button").forEach((button) => button.classList.remove("active"));
  document.querySelector(`.tabs button[data-tab="${tab}"]`).classList.add("active");
  document.querySelectorAll(".tab").forEach((el) => el.classList.remove("active"));
  document.getElementById(`tab-${tab}`).classList.add("active");
  updateOperationalChrome();
  refreshActiveTab().catch((error) => setStatus(error.message, false));
}

function openEventDetails({ message, details }) {
  const modal = document.getElementById("eventDetailsModal");
  document.getElementById("eventMessageText").value = message || "-";
  document.getElementById("eventDetailsText").value = details || "-";
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

function closeEventDetails() {
  const modal = document.getElementById("eventDetailsModal");
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
}

function openEventArchivesModal() {
  const modal = document.getElementById("eventArchivesModal");
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

function closeEventArchivesModal() {
  const modal = document.getElementById("eventArchivesModal");
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
}

function setRequestAdminStatus(message, kind = "info") {
  if (!requestAdminStatus) {
    return;
  }

  requestAdminStatus.textContent = message || "";
  requestAdminStatus.className = `auth-status ${kind === "error" ? "status-err" : kind === "success" ? "status-ok" : ""}`;
}

function setRequestAdminRegistrationStatus(message, kind = "info") {
  if (!requestAdminRegistrationStatus) {
    return;
  }

  requestAdminRegistrationStatus.textContent = message || "";
  requestAdminRegistrationStatus.className = `auth-status ${kind === "error" ? "status-err" : kind === "success" ? "status-ok" : ""}`;
}

function cancelRequestAdminLookup() {
  if (requestAdminLookupTimeout) {
    window.clearTimeout(requestAdminLookupTimeout);
    requestAdminLookupTimeout = null;
  }
  requestAdminLookupRequestToken += 1;
}

function isAdminRequestKeyValid(chave) {
  return /^[A-Z0-9]{4}$/.test(String(chave || ""));
}

function isAdminRequestPasswordValid(value) {
  return value.length >= 3 && value.length <= 10 && value.trim().length > 0;
}

function syncRequestAdminRegistrationFormState() {
  if (!requestAdminRegistrationSaveButton) {
    return;
  }

  const nome = requestAdminRegistrationNomeInput ? requestAdminRegistrationNomeInput.value.trim() : "";
  const projeto = requestAdminRegistrationProjetoSelect ? requestAdminRegistrationProjetoSelect.value.trim() : "";
  const senha = requestAdminRegistrationSenhaInput ? requestAdminRegistrationSenhaInput.value : "";
  const confirmarSenha = requestAdminRegistrationConfirmInput ? requestAdminRegistrationConfirmInput.value : "";
  const canSave = nome.length >= 3
    && projeto.length >= 2
    && isAdminRequestPasswordValid(senha)
    && senha === confirmarSenha
    && !requestAdminRegistrationSaveInProgress;
  requestAdminRegistrationSaveButton.disabled = !canSave;
}

async function loadRequestAdminProjects(selectedValue = "") {
  const rows = projectCatalog.length > 0 ? projectCatalog : await fetchJson("/api/web/projects");
  setProjectCatalog(rows);
  const optionValues = getProjectOptions(selectedValue, { includeDetachedValue: true });
  syncSelectOptions(requestAdminRegistrationProjetoSelect, optionValues, selectedValue || optionValues[0] || "");
}

function resetRequestAdminRegistrationState(options = {}) {
  const preserveKey = options.preserveKey === true;
  if (requestAdminRegistrationChaveInput && !preserveKey) {
    requestAdminRegistrationChaveInput.value = "";
  }
  if (requestAdminRegistrationNomeInput) {
    requestAdminRegistrationNomeInput.value = "";
  }
  if (requestAdminRegistrationSenhaInput) {
    requestAdminRegistrationSenhaInput.value = "";
  }
  if (requestAdminRegistrationConfirmInput) {
    requestAdminRegistrationConfirmInput.value = "";
  }
  setRequestAdminRegistrationStatus("");
  syncRequestAdminRegistrationFormState();
}

function openRequestAdminModal() {
  cancelRequestAdminLookup();
  if (requestAdminRegistrationModal) {
    requestAdminRegistrationModal.classList.add("hidden");
    requestAdminRegistrationModal.setAttribute("aria-hidden", "true");
  }
  resetRequestAdminRegistrationState();
  setRequestAdminStatus("");
  if (requestAdminChaveInput) {
    requestAdminChaveInput.value = "";
  }
  if (!requestAdminModal) {
    return;
  }
  requestAdminModal.classList.remove("hidden");
  requestAdminModal.setAttribute("aria-hidden", "false");
  if (requestAdminChaveInput) {
    requestAdminChaveInput.focus();
  }
}

function closeRequestAdminModal() {
  cancelRequestAdminLookup();
  if (requestAdminModal) {
    requestAdminModal.classList.add("hidden");
    requestAdminModal.setAttribute("aria-hidden", "true");
  }
  if (requestAdminChaveInput) {
    requestAdminChaveInput.value = "";
  }
  setRequestAdminStatus("");
}

function closeRequestAdminRegistrationModal() {
  if (!requestAdminRegistrationModal) {
    return;
  }
  requestAdminRegistrationModal.classList.add("hidden");
  requestAdminRegistrationModal.setAttribute("aria-hidden", "true");
  resetRequestAdminRegistrationState();
}

async function openRequestAdminRegistrationModal(chave) {
  if (!requestAdminRegistrationModal || !requestAdminRegistrationChaveInput) {
    return;
  }

  requestAdminRegistrationChaveInput.value = chave;
  await loadRequestAdminProjects();
  resetRequestAdminRegistrationState({ preserveKey: true });
  if (requestAdminModal) {
    requestAdminModal.classList.add("hidden");
    requestAdminModal.setAttribute("aria-hidden", "true");
  }
  requestAdminRegistrationModal.classList.remove("hidden");
  requestAdminRegistrationModal.setAttribute("aria-hidden", "false");
  syncRequestAdminRegistrationFormState();
  if (requestAdminRegistrationNomeInput) {
    requestAdminRegistrationNomeInput.focus();
  }
}

function returnToRequestAdminLookupModal() {
  const chave = requestAdminRegistrationChaveInput ? requestAdminRegistrationChaveInput.value : "";
  closeRequestAdminRegistrationModal();
  if (!requestAdminModal) {
    return;
  }
  requestAdminModal.classList.remove("hidden");
  requestAdminModal.setAttribute("aria-hidden", "false");
  if (requestAdminChaveInput) {
    requestAdminChaveInput.value = chave;
    requestAdminChaveInput.focus();
    if (typeof requestAdminChaveInput.select === "function") {
      requestAdminChaveInput.select();
    }
  }
  setRequestAdminStatus("Corrija a chave ou informe outra para continuar.");
}

async function submitRequestAdminKnownUser(chave, requestToken) {
  if (requestAdminSelfServiceInProgress) {
    return;
  }

  requestAdminSelfServiceInProgress = true;
  try {
    const payload = await postJson("/api/admin/auth/request-access/self-service", { chave });
    if (requestToken !== requestAdminLookupRequestToken || !requestAdminModal || requestAdminModal.classList.contains("hidden")) {
      return;
    }

    setRequestAdminStatus(payload.message, "success");
    setAuthStatus(payload.message, "success");
    window.setTimeout(() => {
      if (requestToken !== requestAdminLookupRequestToken) {
        return;
      }
      closeRequestAdminModal();
    }, 700);
  } finally {
    requestAdminSelfServiceInProgress = false;
  }
}

async function lookupRequestAdminChave(chave, requestToken) {
  if (requestToken !== requestAdminLookupRequestToken || !requestAdminModal || requestAdminModal.classList.contains("hidden")) {
    return;
  }

  setRequestAdminStatus("Verificando chave...");
  const payload = await fetchJson(`/api/admin/auth/request-access/status?chave=${encodeURIComponent(chave)}`);
  if (requestToken !== requestAdminLookupRequestToken || !requestAdminModal || requestAdminModal.classList.contains("hidden")) {
    return;
  }

  if (!payload.found) {
    await openRequestAdminRegistrationModal(chave);
    setRequestAdminRegistrationStatus(payload.message);
    return;
  }

  if (payload.is_admin || payload.has_pending_request || !payload.has_password) {
    const kind = payload.has_pending_request ? "info" : "error";
    setRequestAdminStatus(payload.message, kind);
    return;
  }

  setRequestAdminStatus("Chave cadastrada. Enviando solicitacao...");
  await submitRequestAdminKnownUser(chave, requestToken);
}

function scheduleRequestAdminLookup() {
  if (!requestAdminChaveInput) {
    return;
  }

  const chave = normalizeAdminChave(requestAdminChaveInput.value);
  if (requestAdminChaveInput.value !== chave) {
    requestAdminChaveInput.value = chave;
  }

  if (requestAdminLookupTimeout) {
    window.clearTimeout(requestAdminLookupTimeout);
    requestAdminLookupTimeout = null;
  }

  setRequestAdminStatus("");
  if (!chave) {
    return;
  }
  if (!/^[A-Z0-9]{0,4}$/.test(chave)) {
    setRequestAdminStatus("A chave deve ter 4 caracteres alfanumericos.", "error");
    return;
  }
  if (!isAdminRequestKeyValid(chave)) {
    setRequestAdminStatus("Digite os 4 caracteres da chave para continuar.");
    return;
  }

  const requestToken = ++requestAdminLookupRequestToken;
  requestAdminLookupTimeout = window.setTimeout(() => {
    lookupRequestAdminChave(chave, requestToken).catch((error) => {
      if (requestToken !== requestAdminLookupRequestToken) {
        return;
      }
      setRequestAdminStatus(error.message, "error");
    });
  }, ADMIN_REQUEST_LOOKUP_DEBOUNCE_MS);
}

function updateUserTitle(targetId, totalRows, totalRegistered) {
  if (targetId === "checkinBody") {
    document.getElementById("checkinTitle").textContent = `Usuários em Check-In (${totalRows}/${totalRegistered})`;
    return;
  }
  if (targetId === "checkoutBody") {
    document.getElementById("checkoutTitle").textContent = `Usuários em Check-Out (${totalRows}/${totalRegistered})`;
  }
}

function updateInactiveTitle(totalRows) {
  document.getElementById("inactiveTitle").textContent = `Usuários Inativos (${totalRows})`;
}

function updateMissingCheckoutTitle(totalRows) {
  document.getElementById("missingCheckoutTitle").textContent = `Usuários com Check-in e sem Check-Out (${totalRows})`;
}

function countRenderedDataRows(bodyId) {
  return document.querySelectorAll(`#${bodyId} tr:not(.empty-state-row)`).length;
}

function syncUserTitles() {
  updateUserTitle("checkinBody", countRenderedDataRows("checkinBody"), registeredUsersTotal);
  updateUserTitle("checkoutBody", countRenderedDataRows("checkoutBody"), registeredUsersTotal);
  updateDashboardSummary();
}

function getSingaporeCalendarDayDiff(value) {
  const eventDayKey = getSingaporeDayKey(value);
  const todayKey = getSingaporeDayKey();
  if (!eventDayKey || !todayKey) {
    return 0;
  }

  const eventMidnightUtcMs = Date.parse(`${eventDayKey}T00:00:00Z`);
  const todayMidnightUtcMs = Date.parse(`${todayKey}T00:00:00Z`);
  if (Number.isNaN(eventMidnightUtcMs) || Number.isNaN(todayMidnightUtcMs)) {
    return 0;
  }

  const diffDays = Math.floor((todayMidnightUtcMs - eventMidnightUtcMs) / (24 * 60 * 60 * 1000));
  return Math.max(0, diffDays);
}

function formatElapsedDays(days) {
  return days === 1 ? "há 1 dia" : `há ${days} dias`;
}

function formatUserTableTime(value) {
  const formatted = formatDateTime(value);
  const calendarDayDiff = getSingaporeCalendarDayDiff(value);
  if (!calendarDayDiff) {
    return { formatted, elapsedDays: 0, isStale: false };
  }

  return {
    formatted: `${formatted} (${formatElapsedDays(calendarDayDiff)})`,
    elapsedDays: calendarDayDiff,
    isStale: true,
  };
}

function buildPresenceRow(row, options = {}) {
  const { highlightMissingCheckout = false, includeElapsedDays = false } = options;
  const tr = document.createElement("tr");
  tr.dataset.userId = String(row.id);
  const timeDisplay = includeElapsedDays ? formatUserTableTime(row.time) : { formatted: formatDateTime(row.time), isStale: false };
  const staleCheckin = getSingaporeCalendarDayDiff(row.time) > 0;
  if (highlightMissingCheckout && staleCheckin) {
    tr.classList.add("attention-user-row");
  }

  tr.innerHTML = `<td>${escapeHtml(includeElapsedDays ? timeDisplay.formatted : formatDateTime(row.time))}</td><td>${escapeHtml(row.nome)}</td><td>${escapeHtml(row.chave)}</td><td>${escapeHtml(row.projeto)}</td><td>${escapeHtml(row.assiduidade ?? "Normal")}</td><td>${escapeHtml(formatLocal(row.local))}</td>`;
  return tr;
}

function renderEmptyStateRow(bodyId, columnCount, message) {
  const body = document.getElementById(bodyId);
  body.innerHTML = "";
  const emptyRow = document.createElement("tr");
  emptyRow.className = "empty-state-row";
  emptyRow.innerHTML = `<td colspan="${columnCount}" class="empty-state-cell">${escapeHtml(message || "Nenhum registro encontrado.")}</td>`;
  body.appendChild(emptyRow);
  applyResponsiveLabels(bodyId);
}

function getPresenceTableState(tableKey) {
  return presenceTableStates[tableKey] || null;
}

function getPresenceDefaultSortDirection(sortKey) {
  if (["time", "latest_time", "inactivity_days"].includes(sortKey)) {
    return "desc";
  }
  return "asc";
}

function getPresenceRowDisplayValue(tableKey, row, key) {
  if (tableKey === "inactive") {
    if (key === "nome") {
      return row.nome || "";
    }
    if (key === "chave") {
      return row.chave || "";
    }
    if (key === "projeto") {
      return row.projeto || "";
    }
    if (key === "latest_time") {
      return `${formatAction(row.latest_action)} - ${formatDateTime(row.latest_time)}`;
    }
    if (key === "inactivity_days") {
      return formatInactivityDays(row.inactivity_days);
    }
    return "";
  }

  if (tableKey === "missingCheckout") {
    if (key === "time") {
      return formatUserTableTime(row.time).formatted;
    }
    if (key === "nome") {
      return row.nome || "";
    }
    if (key === "chave") {
      return row.chave || "";
    }
    return "";
  }

  if (key === "time") {
    return formatDateTime(row.time);
  }
  if (key === "nome") {
    return row.nome || "";
  }
  if (key === "chave") {
    return row.chave || "";
  }
  if (key === "projeto") {
    return row.projeto || "";
  }
  if (key === "assiduidade") {
    return row.assiduidade || "Normal";
  }
  if (key === "local") {
    return formatLocal(row.local);
  }
  return "";
}

function getPresenceRowSortValue(tableKey, row, key) {
  if (tableKey === "inactive") {
    if (key === "latest_time") {
      const parsedTime = Date.parse(row.latest_time || "");
      return Number.isNaN(parsedTime) ? 0 : parsedTime;
    }
    if (key === "inactivity_days") {
      return Number(row.inactivity_days || 0);
    }
    return getPresenceRowDisplayValue(tableKey, row, key);
  }

  if (key === "time") {
    const parsedTime = Date.parse(row.time || "");
    return Number.isNaN(parsedTime) ? 0 : parsedTime;
  }
  return getPresenceRowDisplayValue(tableKey, row, key);
}

function hasActivePresenceFilters(tableKey) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return false;
  }
  return Object.values(state.filters).some((value) => String(value || "").trim());
}

function getPresenceEmptyMessage(tableKey) {
  if (hasActivePresenceFilters(tableKey)) {
    return "Nenhum registro encontrado com os filtros atuais.";
  }
  if (tableKey === "inactive") {
    return "Nenhum usuário inativo no momento.";
  }
  if (tableKey === "missingCheckout") {
    return "Nenhum usuário com check-in pendente de check-out no momento.";
  }
  return tableKey === "checkin"
    ? "Nenhum usuário em check-in no momento."
    : "Nenhum usuário em check-out no momento.";
}

function filterPresenceRows(tableKey, rows, filters) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return rows;
  }
  return rows.filter((row) => state.filterColumns.every((key) => {
    const rawFilterValue = String(filters[key] || "").trim();
    if (!rawFilterValue) {
      return true;
    }
    const searchableValue = String(getPresenceRowDisplayValue(tableKey, row, key) || "").toLocaleLowerCase();
    return searchableValue === rawFilterValue.toLocaleLowerCase();
  }));
}

function getPresenceFilterOptions(tableKey, key, rows) {
  const sortedRows = sortPresenceRows(tableKey, rows, key, getPresenceDefaultSortDirection(key));
  const uniqueOptions = new Map();
  sortedRows.forEach((row) => {
    const displayValue = String(getPresenceRowDisplayValue(tableKey, row, key) || "").trim();
    if (!displayValue || uniqueOptions.has(displayValue)) {
      return;
    }
    uniqueOptions.set(displayValue, displayValue);
  });
  return [...uniqueOptions.values()];
}

function refreshPresenceFilterOptions(tableKey) {
  const state = getPresenceTableState(tableKey);
  const container = document.querySelector(`.presence-controls[data-presence-table="${tableKey}"]`);
  if (!state || !container) {
    return;
  }

  container.querySelectorAll("[data-presence-filter]").forEach((control) => {
    const key = control.dataset.presenceFilter;
    const options = getPresenceFilterOptions(tableKey, key, state.rawRows);
    const currentValue = String(state.filters[key] || "");
    const fragment = document.createDocumentFragment();
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "Todos";
    fragment.appendChild(defaultOption);
    options.forEach((optionValue) => {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionValue;
      fragment.appendChild(option);
    });
    control.replaceChildren(fragment);
    if (options.includes(currentValue)) {
      control.value = currentValue;
      return;
    }
    state.filters[key] = "";
    control.value = "";
  });
}

function sortPresenceRows(tableKey, rows, sortKey, sortDirection) {
  const direction = sortDirection === "asc" ? 1 : -1;
  return [...rows].sort((rowA, rowB) => {
    if (["time", "latest_time", "inactivity_days"].includes(sortKey)) {
      const timeDifference = getPresenceRowSortValue(tableKey, rowA, sortKey) - getPresenceRowSortValue(tableKey, rowB, sortKey);
      if (timeDifference !== 0) {
        return timeDifference * direction;
      }
      return String(rowA.nome || "").localeCompare(String(rowB.nome || ""), "pt-BR", {
        sensitivity: "base",
        numeric: true,
      }) * direction;
    }

    return String(getPresenceRowSortValue(tableKey, rowA, sortKey)).localeCompare(
      String(getPresenceRowSortValue(tableKey, rowB, sortKey)),
      "pt-BR",
      { sensitivity: "base", numeric: true },
    ) * direction;
  });
}

function syncPresenceControls(tableKey) {
  const state = getPresenceTableState(tableKey);
  const container = document.querySelector(`.presence-controls[data-presence-table="${tableKey}"]`);
  if (!state || !container) {
    return;
  }

  container.querySelectorAll("[data-presence-filter]").forEach((control) => {
    const key = control.dataset.presenceFilter;
    control.value = state.filters[key] || "";
  });
}

function syncPresenceSortHeaders(tableKey) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return;
  }

  document.querySelectorAll(`.sortable-header[data-sort-table="${tableKey}"]`).forEach((button) => {
    const isActive = button.dataset.sortKey === state.sortKey;
    button.classList.toggle("is-active", isActive);
    const indicator = button.querySelector(".sort-indicator");
    if (indicator) {
      indicator.textContent = isActive ? (state.sortDirection === "asc" ? "↑" : "↓") : "↕";
    }
    const parentHeader = button.closest("th");
    if (parentHeader) {
      parentHeader.setAttribute("aria-sort", isActive ? (state.sortDirection === "asc" ? "ascending" : "descending") : "none");
    }
  });
}

function resetPresenceControls(tableKey) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return;
  }
  state.filters = createPresenceFilterState(state.filterColumns);
  state.sortKey = state.defaultSortKey;
  state.sortDirection = state.defaultSortDirection;
  syncPresenceControls(tableKey);
  syncPresenceSortHeaders(tableKey);
}

function applyPresenceTableState(tableKey) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return;
  }

  refreshPresenceFilterOptions(tableKey);
  const filteredRows = filterPresenceRows(tableKey, state.rawRows, state.filters);
  const sortedRows = sortPresenceRows(tableKey, filteredRows, state.sortKey, state.sortDirection);
  if (tableKey === "inactive") {
    renderInactiveTable(sortedRows, { emptyMessage: getPresenceEmptyMessage(tableKey) });
  } else if (tableKey === "missingCheckout") {
    renderMissingCheckoutTable(sortedRows, { emptyMessage: getPresenceEmptyMessage(tableKey) });
  } else {
    renderPresenceTable(state.bodyId, sortedRows, {
      ...state.renderOptions,
      emptyMessage: getPresenceEmptyMessage(tableKey),
    });
  }
  syncPresenceSortHeaders(tableKey);
}

function renderPresenceTable(bodyId, rows, options = {}) {
  if (!rows.length) {
    renderEmptyStateRow(bodyId, 6, options.emptyMessage || "Nenhum registro encontrado.");
    updateUserTitle(bodyId, 0, registeredUsersTotal);
    return;
  }
  const body = document.getElementById(bodyId);
  body.innerHTML = "";
  rows.forEach((row) => body.appendChild(buildPresenceRow(row, options)));
  applyResponsiveLabels(bodyId);
  updateUserTitle(bodyId, rows.length, registeredUsersTotal);
}

function formatInactivityDays(days) {
  return days === 1 ? "1 dia" : `${days} dias`;
}

function buildInactiveRow(row) {
  const tr = document.createElement("tr");
  tr.dataset.userId = String(row.id);
  tr.classList.add("inactive-user-row");
  tr.innerHTML = `
    <td>${escapeHtml(row.nome)}</td>
    <td>${escapeHtml(row.chave)}</td>
    <td>${escapeHtml(row.projeto)}</td>
    <td>${escapeHtml(`${formatAction(row.latest_action)} - ${formatDateTime(row.latest_time)}`)}</td>
    <td>${escapeHtml(formatInactivityDays(row.inactivity_days))}</td>
    <td class="user-table-actions"><button type="button" data-user-remove="${escapeHtml(row.id)}">Remover</button></td>
  `;
  return tr;
}

function renderInactiveTable(rows, options = {}) {
  if (!rows.length) {
    renderEmptyStateRow("inactiveBody", 6, options.emptyMessage || "Nenhum registro encontrado.");
    updateInactiveTitle(0);
    return;
  }

  const body = document.getElementById("inactiveBody");
  body.innerHTML = "";
  rows.forEach((row) => body.appendChild(buildInactiveRow(row)));
  applyResponsiveLabels("inactiveBody");
  updateInactiveTitle(rows.length);
}

function buildMissingCheckoutRow(row) {
  const tr = document.createElement("tr");
  tr.dataset.userId = String(row.id);
  const timeDisplay = formatUserTableTime(row.time);
  tr.innerHTML = `
    <td>${escapeHtml(row.nome)}</td>
    <td>${escapeHtml(row.chave)}</td>
    <td>${escapeHtml(timeDisplay.formatted)}</td>
    <td class="user-table-actions"><button type="button" data-user-remove="${escapeHtml(row.id)}">Remover</button></td>
  `;
  return tr;
}

function renderMissingCheckoutTable(rows, options = {}) {
  if (!rows.length) {
    renderEmptyStateRow("missingCheckoutBody", 4, options.emptyMessage || "Nenhum registro encontrado.");
    updateMissingCheckoutTitle(0);
    return;
  }

  const body = document.getElementById("missingCheckoutBody");
  body.innerHTML = "";
  rows.forEach((row) => body.appendChild(buildMissingCheckoutRow(row)));
  applyResponsiveLabels("missingCheckoutBody");
  updateMissingCheckoutTitle(rows.length);
}

function createLocationCoordinateEntry(value = "", overrides = {}) {
  return {
    id: overrides.id ?? `coord-${nextLocationCoordinateDraftId++}`,
    value: String(value ?? ""),
  };
}

function normalizeLocationCoordinateEntries(entries) {
  if (!Array.isArray(entries) || !entries.length) {
    return [createLocationCoordinateEntry("")];
  }

  return entries.map((entry) => {
    if (typeof entry === "string") {
      return createLocationCoordinateEntry(entry);
    }

    return createLocationCoordinateEntry(entry?.value ?? "", { id: entry?.id });
  });
}

function createLocationRow(overrides = {}) {
  const row = {
    id: overrides.id ?? `draft-${nextLocationDraftId++}`,
    local: "",
    coordinates: [createLocationCoordinateEntry("")],
    projects: [],
    projectPickerOpen: false,
    tolerance: "",
    isEditing: false,
    ...overrides,
  };
  row.coordinates = normalizeLocationCoordinateEntries(overrides.coordinates);
  row.projects = normalizeProjectNames(overrides.projects);
  return row;
}

function isPersistedLocationRowId(rowId) {
  return /^\d+$/.test(String(rowId ?? "").trim());
}

function getLocationRowById(rowId) {
  return locationRows.find((row) => String(row.id) === String(rowId));
}

function getLocationRowElement(rowId) {
  return document.querySelector(`#locationsBody tr[data-location-id="${CSS.escape(String(rowId))}"]`);
}

function captureLocationRowDraft(rowId) {
  const row = getLocationRowById(rowId);
  const rowElement = getLocationRowElement(rowId);
  if (!row || !rowElement) {
    return row;
  }

  row.local = rowElement.querySelector(".location-name")?.value ?? row.local;
  row.tolerance = rowElement.querySelector(".location-tolerance")?.value ?? row.tolerance;
  const coordinateInputs = Array.from(rowElement.querySelectorAll(".location-coordinate-input"));
  row.coordinates = coordinateInputs.length
    ? coordinateInputs.map((input, index) =>
        createLocationCoordinateEntry(input.value, {
          id: input.dataset.coordinateId || row.coordinates[index]?.id,
        })
      )
    : [createLocationCoordinateEntry("")];
  const projectInputs = Array.from(rowElement.querySelectorAll("input[data-location-project-option]"));
  if (projectInputs.length) {
    row.projects = normalizeProjectNames(
      projectInputs.filter((input) => input.checked).map((input) => input.value)
    );
  }
  return row;
}

function isBlankLocationRow(row) {
  return !String(row.local || "").trim()
    && !(row.coordinates || []).some((coordinate) => String(coordinate.value || "").trim())
    && !String(row.tolerance || "").trim();
}

function hasBlankLocationRow() {
  return locationRows.some((row) => isBlankLocationRow(row));
}

function getLocationAccuracyThresholdInput() {
  return document.getElementById("locationAccuracyThresholdMeters");
}

function getLocationSettingsSaveButton() {
  return document.getElementById("saveLocationSettingsButton");
}

function normalizeLocationAccuracyThreshold(value) {
  const normalized = String(value ?? "").trim();
  if (!/^\d+$/.test(normalized)) {
    throw new Error("O erro máximo para considerar a coordenada do usuário deve ser um inteiro em metros.");
  }

  const meters = Number(normalized);
  if (!Number.isInteger(meters) || meters < 1 || meters > 9999) {
    throw new Error("O erro máximo para considerar a coordenada do usuário deve ser um inteiro entre 1 e 9999 metros.");
  }
  return String(meters);
}

function normalizeLocationName(value) {
  const normalized = String(value || "").trim().replace(/\s+/g, " ");
  if (!normalized) {
    throw new Error("Informe a descrição do local.");
  }
  if (normalized.length > 40) {
    throw new Error("O local deve ter no máximo 40 caracteres.");
  }
  if (!/^[\p{L}\p{N} ]+$/u.test(normalized)) {
    throw new Error("O local deve conter apenas letras, números e espaços.");
  }
  return normalized;
}

function normalizeCoordinates(value) {
  const normalized = String(value || "").trim().replace(/\s+/g, " ");
  const match = /^(-?\d{1,3}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)$/.exec(normalized);
  if (!match) {
    throw new Error("As coordenadas devem estar no formato latitude, longitude.");
  }

  const latitude = Number(match[1]);
  const longitude = Number(match[2]);
  if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
    throw new Error("A latitude deve estar entre -90 e 90.");
  }
  if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
    throw new Error("A longitude deve estar entre -180 e 180.");
  }

  return `${latitude}, ${longitude}`;
}

function normalizeTolerance(value) {
  const normalized = String(value ?? "").trim();
  if (!/^\d{1,4}$/.test(normalized)) {
    throw new Error("A tolerância deve ter de 1 a 4 algarismos inteiros.");
  }

  const tolerance = Number(normalized);
  if (!Number.isInteger(tolerance) || tolerance < 1 || tolerance > 9999) {
    throw new Error("A tolerância deve ser um inteiro entre 1 e 9999 metros.");
  }
  return String(tolerance);
}

function getLocationCoordinateValues(row) {
  if (!Array.isArray(row?.coordinates)) {
    return [];
  }

  return row.coordinates
    .map((coordinate) => String(coordinate?.value ?? coordinate ?? "").trim())
    .filter((value) => value);
}

function formatLocationCoordinateCount(count) {
  return count === 1 ? "1 coordenada" : `${count} coordenadas`;
}

function makeLocationCoordinateSummary(row) {
  const coordinates = getLocationCoordinateValues(row);
  if (!coordinates.length) {
    return '<span class="location-empty-copy">Sem coordenadas</span>';
  }

  const primaryCoordinate = coordinates[0];
  const extraCoordinates = Math.max(0, coordinates.length - 1);
  const tooltip = coordinates.join(" | ");

  return `
    <div class="location-coordinate-summary" title="${escapeHtml(tooltip)}">
      <span class="location-coordinate-pill-index">1</span>
      <span class="location-coordinate-summary-primary">${escapeHtml(primaryCoordinate)}</span>
      ${extraCoordinates > 0 ? `<span class="location-coordinate-summary-count">+${extraCoordinates}</span>` : ""}
    </div>
  `;
}

function makeLocationCoordinateLines(row) {
  return row.coordinates.map((coordinate, index) => `
    <div class="location-coordinate-line">
      <span class="location-coordinate-index">${index + 1}</span>
      <input
        class="inline location-coordinate-input"
        data-coordinate-id="${escapeHtml(String(coordinate.id))}"
        maxlength="40"
        placeholder="Latitude, longitude"
        value="${escapeHtml(coordinate.value)}"
        ${row.isEditing ? "" : "disabled"}
      />
      ${row.isEditing && index > 0 ? `<button type="button" class="secondary-button location-coordinate-remove-button" data-location-coordinate-remove="${row.id}" data-coordinate-id="${escapeHtml(String(coordinate.id))}">Remover</button>` : ""}
    </div>
  `).join("");
}

function formatLocationProjectSummary(row) {
  const projectNames = normalizeProjectNames(row?.projects);
  if (!projectNames.length) {
    return "Nenhum projeto selecionado";
  }
  return projectNames.join(", ");
}

function makeLocationProjectOptions(row) {
  const selectedProjectNames = normalizeProjectNames(row.projects);
  const selectedProjectSet = new Set(selectedProjectNames);
  return getLocationProjectOptions(selectedProjectNames)
    .map((projectName) => `
      <label class="location-project-option">
        <input
          type="checkbox"
          data-location-project-option="${row.id}"
          value="${escapeHtml(projectName)}"
          ${selectedProjectSet.has(projectName) ? "checked" : ""}
        />
        <span>${escapeHtml(projectName)}</span>
      </label>
    `)
    .join("");
}

function focusLocationProjectPicker(rowId) {
  const row = getLocationRowElement(rowId);
  if (!row) {
    return;
  }
  row.querySelector("input[data-location-project-option]")?.focus();
}

function makeLocationRow(row) {
  const tr = document.createElement("tr");
  tr.className = row.isEditing ? "location-row location-row-editing" : "location-row";
  tr.dataset.locationId = String(row.id);

  const toleranceValue = String(row.tolerance ?? "").trim();
  const coordinateValues = getLocationCoordinateValues(row);
  const coordinateCountLabel = formatLocationCoordinateCount(coordinateValues.length || 0);
  const projectOptionsMarkup = makeLocationProjectOptions(row);
  const projectsCell = `
    <div class="location-cell-stack location-projects-cell">
      <button
        type="button"
        class="secondary-button location-projects-button"
        data-location-projects-toggle="${row.id}"
        aria-expanded="${row.projectPickerOpen ? "true" : "false"}"
      >Projetos</button>
      <span class="location-projects-summary">${escapeHtml(formatLocationProjectSummary(row))}</span>
      ${row.projectPickerOpen ? `
        <div class="location-projects-panel">
          ${projectOptionsMarkup || '<span class="location-empty-copy">Nenhum projeto cadastrado.</span>'}
        </div>
      ` : ""}
    </div>
  `;
  const locationCell = row.isEditing
    ? `
      <div class="location-cell-stack">
        <input class="inline location-name" maxlength="100" value="${escapeHtml(row.local)}" />
      </div>
    `
    : `
      <div class="location-cell-stack">
        <span class="location-static-value">${escapeHtml(row.local || "-")}</span>
        <span class="location-static-meta">${escapeHtml(coordinateCountLabel)}</span>
      </div>
    `;

  const coordinatesCell = row.isEditing
    ? `<div class="location-coordinates-stack">${makeLocationCoordinateLines(row)}</div>`
    : `<div class="location-coordinates-stack">${makeLocationCoordinateSummary(row)}</div>`;

  const toleranceCell = row.isEditing
    ? `
      <div class="location-cell-stack">
        <input class="inline location-tolerance" type="number" min="1" max="9999" inputmode="numeric" value="${escapeHtml(row.tolerance)}" />
      </div>
    `
    : `
      <div class="location-cell-stack">
        <span class="location-tolerance-badge">${escapeHtml(toleranceValue ? `${toleranceValue} m` : "-")}</span>
      </div>
    `;

  const actionsCell = row.isEditing
    ? `
      <button type="button" class="location-action-primary" data-location-edit="${row.id}">Salvar</button>
      <button type="button" class="secondary-button location-action-secondary" data-location-add-coordinate="${row.id}">+ Coord.</button>
      <button type="button" class="location-action-danger" data-location-remove="${row.id}">Remover</button>
    `
    : `
      <button type="button" class="location-action-primary" data-location-edit="${row.id}">Editar</button>
      <button type="button" class="secondary-button location-action-secondary" data-location-remove="${row.id}">Remover</button>
    `;

  tr.innerHTML = `
    <td class="location-cell">
        ${projectsCell}
      </td>
      <td class="location-cell">
      ${locationCell}
    </td>
    <td class="location-cell location-coordinates-cell">
      ${coordinatesCell}
    </td>
    <td class="location-cell">
      ${toleranceCell}
    </td>
    <td class="location-actions">
      ${actionsCell}
    </td>
  `;
  return tr;
}

function renderLocations() {
  const body = document.getElementById("locationsBody");
  const addButton = document.getElementById("addLocationButton");
  body.innerHTML = "";
  locationRows.forEach((row) => body.appendChild(makeLocationRow(row)));
  applyResponsiveLabels("locationsBody");
  addButton.disabled = hasBlankLocationRow();
}
function renderLocationSettings() {
  const accuracyInput = getLocationAccuracyThresholdInput();
  if (accuracyInput) {
    const normalizedAccuracy = String(locationAccuracyThresholdMeters);
    accuracyInput.value = normalizedAccuracy;
    accuracyInput.dataset.persistedValue = normalizedAccuracy;
  }
  locationSettingsDirty = false;
  updateLocationSettingsSaveButton();
}

function updateLocationSettingsSaveButton() {
  const saveButton = getLocationSettingsSaveButton();
  if (saveButton) {
    saveButton.disabled = !locationSettingsDirty;
  }
}

function haveLocationSettingsChanged() {
  const accuracyInput = getLocationAccuracyThresholdInput();
  if (!accuracyInput) {
    return false;
  }

  const persistedAccuracy = accuracyInput.dataset.persistedValue ?? String(locationAccuracyThresholdMeters);

  try {
    return normalizeLocationAccuracyThreshold(accuracyInput.value) !== persistedAccuracy;
  } catch {
    return String(accuracyInput.value ?? "").trim() !== persistedAccuracy;
  }
}

function refreshLocationSettingsDirtyState() {
  locationSettingsDirty = haveLocationSettingsChanged();
  updateLocationSettingsSaveButton();
}

function handleLocationSettingsInputChange() {
  refreshLocationSettingsDirtyState();
  if (locationSettingsDirty) {
    setStatus("Alterações pendentes nas configurações de localização. Clique em Salvar para registrar.", true);
  }
}

function discardLocationSettingsDraft() {
  renderLocationSettings();
  setStatus("Alterações nas configurações de localização descartadas.", true);
}

function focusLocationRow(rowId, coordinateId = null) {
  const row = getLocationRowElement(rowId);
  if (!row) {
    return;
  }

  if (coordinateId !== null) {
    row.querySelector(`[data-coordinate-id="${CSS.escape(String(coordinateId))}"]`)?.focus();
    return;
  }

  row.querySelector(".location-name")?.focus();
}

function setLocationEditingState(rowId, editing) {
  const row = getLocationRowById(rowId);
  if (!row) {
    return;
  }

  if (row.isEditing) {
    captureLocationRowDraft(rowId);
  }
  row.isEditing = editing;
  if (!editing) {
    row.projectPickerOpen = false;
  }
  renderLocations();
  if (editing) {
    focusLocationRow(rowId);
  }
}

function addLocationRow() {
  if (hasBlankLocationRow()) {
    setStatus("Finalize ou remova a linha em branco antes de adicionar outra localização.", false);
    renderLocations();
    return;
  }

  const row = createLocationRow({ isEditing: true });
  locationRows.push(row);
  renderLocations();
  focusLocationRow(row.id);
  setStatus("Nova localização pronta para preenchimento.", true);
}

function addLocationCoordinate(rowId) {
  const row = getLocationRowById(rowId);
  if (!row) {
    return;
  }

  captureLocationRowDraft(rowId);
  if (!row.isEditing) {
    row.isEditing = true;
  }
  const coordinate = createLocationCoordinateEntry("");
  row.coordinates.push(coordinate);
  renderLocations();
  focusLocationRow(rowId, coordinate.id);
}

function removeLocationCoordinate(rowId, coordinateId) {
  const row = getLocationRowById(rowId);
  if (!row) {
    return;
  }

  captureLocationRowDraft(rowId);
  if (row.coordinates.length <= 1) {
    return;
  }

  row.coordinates = row.coordinates.filter((coordinate) => String(coordinate.id) !== String(coordinateId));
  if (!row.coordinates.length) {
    row.coordinates = [createLocationCoordinateEntry("")];
  }

  renderLocations();
  focusLocationRow(rowId, row.coordinates[Math.max(0, row.coordinates.length - 1)]?.id ?? null);
}

async function saveLocationRow(rowId) {
  const row = captureLocationRowDraft(rowId);
  if (!row) {
    return;
  }

  const local = normalizeLocationName(row.local);
  const tolerance = normalizeTolerance(row.tolerance);
  const projects = normalizeProjectNames(row.projects);
  const normalizedCoordinates = row.coordinates
    .map((coordinate) => String(coordinate.value || "").trim())
    .filter((value) => value)
    .map((value) => normalizeCoordinates(value));
  if (!projects.length) {
    throw new Error("Selecione ao menos um projeto para a localização.");
  }
  if (!normalizedCoordinates.length) {
    throw new Error("Informe ao menos uma coordenada para o local.");
  }

  const coordinatesPayload = normalizedCoordinates.map((value) => {
    const [latitude, longitude] = value.split(",").map((part) => Number(part.trim()));
    return { latitude, longitude };
  });
  const primaryCoordinate = coordinatesPayload[0];
  const payload = {
    local,
    latitude: primaryCoordinate.latitude,
    longitude: primaryCoordinate.longitude,
    coordinates: coordinatesPayload,
    projects,
    tolerance_meters: Number(tolerance),
  };
  if (isPersistedLocationRowId(rowId)) {
    payload.location_id = Number(rowId);
  }

  const response = await postJson("/api/admin/locations", payload);
  await loadLocations();
  setStatus(response.message, true);
}

async function removeLocationRow(rowId) {
  const row = getLocationRowById(rowId);
  if (!row) {
    return;
  }

  captureLocationRowDraft(rowId);

  if (!isPersistedLocationRowId(rowId)) {
    locationRows = locationRows.filter((item) => String(item.id) !== String(rowId));
    renderLocations();
    setStatus(`Localização ${row.local || "em branco"} removida.`, true);
    return;
  }

  const confirmed = window.confirm(`Deseja remover a localização ${row.local}?`);
  if (!confirmed) {
    return;
  }

  const response = await deleteJson(`/api/admin/locations/${rowId}`);
  await loadLocations();
  setStatus(response.message, true);
}

async function saveLocationSettings() {
  const accuracyInput = getLocationAccuracyThresholdInput();
  const saveButton = getLocationSettingsSaveButton();
  if (!accuracyInput) {
    locationSettingsDirty = false;
    updateLocationSettingsSaveButton();
    return;
  }

  const normalizedAccuracy = normalizeLocationAccuracyThreshold(accuracyInput.value);
  accuracyInput.value = normalizedAccuracy;
  if (normalizedAccuracy === String(locationAccuracyThresholdMeters)) {
    locationSettingsDirty = false;
    updateLocationSettingsSaveButton();
    return;
  }

  accuracyInput.disabled = true;
  if (saveButton) {
    saveButton.disabled = true;
  }
  try {
    const response = await postJson("/api/admin/locations/settings", {
      location_accuracy_threshold_meters: Number(normalizedAccuracy),
    });
    locationAccuracyThresholdMeters = response.location_accuracy_threshold_meters;
    renderLocationSettings();
    setStatus(response.message, true);
  } catch (error) {
    refreshLocationSettingsDirtyState();
    throw error;
  } finally {
    accuracyInput.disabled = false;
    updateLocationSettingsSaveButton();
  }
}

async function loadLocations() {
  const response = await fetchJson("/api/admin/locations");
  locationAccuracyThresholdMeters = response.location_accuracy_threshold_meters;
  locationRows = response.items.map((row) =>
    createLocationRow({
      id: row.id,
      local: row.local,
      coordinates: (Array.isArray(row.coordinates) && row.coordinates.length
        ? row.coordinates
        : [{ latitude: row.latitude, longitude: row.longitude }]
      ).map((coordinate) => `${coordinate.latitude}, ${coordinate.longitude}`),
      projects: Array.isArray(row.projects) ? row.projects : [],
      tolerance: String(row.tolerance_meters),
      isEditing: false,
    })
  );
  renderLocations();
  renderLocationSettings();
  updateDashboardSummary();
}

function makePendingRow(row) {
  const defaultProjectValue = getProjectOptions("", {}).at(0) || "";
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${escapeHtml(row.rfid)}</td>
    <td><input class="inline" id="nome-${row.id}" disabled /></td>
    <td><input class="inline" id="chave-${row.id}" maxlength="4" disabled /></td>
    <td>
      <select class="inline" id="projeto-${row.id}" disabled>
        ${buildProjectOptionsHtml(defaultProjectValue)}
      </select>
    </td>
    <td class="pending-actions">
      <button data-edit="${row.id}">Editar</button>
      <button data-remove="${row.id}">Remover</button>
      <button data-save="${row.id}" data-rfid="${escapeHtml(row.rfid)}" disabled>Salvar</button>
    </td>
  `;
  return tr;
}

function makeRegisteredUserRow(user) {
  const tr = document.createElement("tr");
  tr.className = "user-row";
  tr.dataset.userId = String(user.id);
  tr.innerHTML = `
    <td><input class="inline user-rfid" maxlength="64" value="${escapeHtml(user.rfid ?? "")}" title="${escapeHtml(user.rfid ?? "")}" disabled /></td>
    <td><input class="inline user-nome" maxlength="180" value="${escapeHtml(user.nome)}" title="${escapeHtml(user.nome)}" disabled /></td>
    <td><input class="inline user-chave" maxlength="4" value="${escapeHtml(user.chave)}" title="${escapeHtml(user.chave)}" disabled /></td>
    <td><input class="inline user-perfil" type="number" min="0" max="999" value="${escapeHtml(user.perfil ?? 0)}" title="${escapeHtml(user.perfil ?? 0)}" disabled /></td>
    <td>
      <select class="inline user-projeto" title="${escapeHtml(user.projeto ?? "")}" disabled>
        ${buildProjectOptionsHtml(user.projeto, { includeDetachedValue: true })}
      </select>
    </td>
    <td><input class="inline user-end-rua" maxlength="255" value="${escapeHtml(user.end_rua ?? "")}" title="${escapeHtml(user.end_rua ?? "")}" disabled /></td>
    <td><input class="inline user-zip" maxlength="10" value="${escapeHtml(user.zip ?? "")}" title="${escapeHtml(user.zip ?? "")}" disabled /></td>
    <td><input class="inline user-cargo" maxlength="255" value="${escapeHtml(user.cargo ?? "")}" title="${escapeHtml(user.cargo ?? "")}" disabled /></td>
    <td><input class="inline user-email" type="email" maxlength="255" value="${escapeHtml(user.email ?? "")}" title="${escapeHtml(user.email ?? "")}" spellcheck="false" disabled /></td>
    <td class="pending-actions user-actions">
      <button data-user-edit="${user.id}">Editar</button>
      <button data-user-save="${user.id}" disabled>Salvar</button>
      <button type="button" class="secondary-button" data-user-password-reset="${user.id}" title="Remove a senha atual para que o usuario cadastre uma nova.">Senha</button>
      <button data-user-remove="${user.id}">Remover</button>
    </td>
  `;
  tr.querySelector(".user-projeto").value = user.projeto;
  return tr;
}

function makeProjectRow(project) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${escapeHtml(project.name)}</td>
    <td class="pending-actions user-actions">
      <button type="button" class="secondary-button" data-project-remove="${project.id}">Remover</button>
    </td>
  `;
  return tr;
}

function makeAdministratorRow(row) {
  const tr = document.createElement("tr");
  const isRequestRow = row.row_type === "request";
  const profileValue = Number.parseInt(row.perfil, 10);
  const normalizedProfileValue = Number.isFinite(profileValue) ? profileValue : 0;
  const actionButtons = isRequestRow
    ? `
      ${row.can_approve ? `<button data-admin-approve="${row.id}">Aprovar</button>` : ""}
      ${row.can_reject ? `<button type="button" class="secondary-button" data-admin-reject="${row.id}">Rejeitar</button>` : ""}
    `
    : `
      <button data-admin-profile-save="${row.id}">Salvar Perfil</button>
      ${row.can_revoke ? `<button type="button" class="secondary-button" data-admin-revoke="${row.id}">Revogar</button>` : ""}
    `;
  tr.classList.toggle("admin-row-pending", isRequestRow);
  tr.innerHTML = `
    <td>${escapeHtml(row.chave)}</td>
    <td>${escapeHtml(row.nome)}</td>
    <td>
      <input
        class="inline admin-profile-input"
        data-admin-profile-input="${row.id}"
        type="number"
        min="0"
        max="999"
        inputmode="numeric"
        value="${escapeHtml(normalizedProfileValue)}"
      />
    </td>
    <td><span class="admin-status-badge${isRequestRow ? " is-pending" : ""}">${escapeHtml(row.status_label)}</span></td>
    <td class="pending-actions user-actions">${actionButtons}</td>
  `;
  return tr;
}

function hasPendingEditInProgress() {
  return locationRows.some((row) => row.isEditing)
    || locationSettingsDirty
    || Array.from(document.querySelectorAll("#pendingBody input, #pendingBody select, #usersBody input, #usersBody select")).some((field) => !field.disabled);
}

function setPendingEditingState(id, editing) {
  const nome = document.getElementById(`nome-${id}`);
  const chave = document.getElementById(`chave-${id}`);
  const projeto = document.getElementById(`projeto-${id}`);
  const saveButton = document.querySelector(`button[data-save="${id}"]`);
  const editButton = document.querySelector(`button[data-edit="${id}"]`);

  if (!nome || !chave || !projeto || !saveButton || !editButton) {
    return;
  }

  nome.disabled = !editing;
  chave.disabled = !editing;
  projeto.disabled = !editing;
  saveButton.disabled = !editing;
  editButton.disabled = editing;
  if (editing) {
    nome.focus();
  }
}

function setRegisteredUserEditingState(userId, editing) {
  const row = document.querySelector(`#usersBody tr[data-user-id="${CSS.escape(String(userId))}"]`);
  if (!row) {
    return;
  }

  row.classList.toggle("user-row-editing", editing);

  const rfid = row.querySelector(".user-rfid");
  const nome = row.querySelector(".user-nome");
  const chave = row.querySelector(".user-chave");
  const perfil = row.querySelector(".user-perfil");
  const projeto = row.querySelector(".user-projeto");
  const endRua = row.querySelector(".user-end-rua");
  const zip = row.querySelector(".user-zip");
  const cargo = row.querySelector(".user-cargo");
  const email = row.querySelector(".user-email");
  const saveButton = row.querySelector(`[data-user-save="${userId}"]`);
  const editButton = row.querySelector(`[data-user-edit="${userId}"]`);
  const passwordButton = row.querySelector(`[data-user-password-reset="${userId}"]`);

  rfid.disabled = !editing;
  nome.disabled = !editing;
  chave.disabled = !editing;
  perfil.disabled = !editing;
  projeto.disabled = !editing;
  endRua.disabled = !editing;
  zip.disabled = !editing;
  cargo.disabled = !editing;
  email.disabled = !editing;
  saveButton.disabled = !editing;
  editButton.disabled = editing;
  if (passwordButton) {
    passwordButton.disabled = editing;
  }
  scheduleUserFieldTextareaRefresh();
  if (editing) {
    nome.focus();
    if (typeof nome.select === "function") {
      nome.select();
    }
  }
}

function toggleAdminPasswordEditor(id, active) {
  const editor = document.getElementById(`admin-password-editor-${id}`);
  if (!editor) {
    return;
  }
  editor.classList.toggle("active", active);
  const input = document.getElementById(`admin-password-input-${id}`);
  if (!input) {
    return;
  }
  if (active) {
    input.focus();
  } else {
    input.value = "";
  }
}

function readAdministratorProfileValue(id) {
  const input = document.querySelector(`[data-admin-profile-input="${CSS.escape(String(id))}"]`);
  if (!(input instanceof HTMLInputElement)) {
    throw new Error("Perfil do administrador nao encontrado.");
  }

  const normalized = String(input.value || "").trim();
  if (!/^\d{1,3}$/.test(normalized)) {
    throw new Error("Informe um perfil numerico entre 0 e 999.");
  }
  return Number.parseInt(normalized, 10);
}

async function loadCheckin() {
  const rows = await fetchJson("/api/admin/checkin");
  presenceTableStates.checkin.rawRows = Array.isArray(rows) ? rows : [];
  applyPresenceTableState("checkin");
  updateDashboardSummary();
}

async function loadCheckout() {
  const rows = await fetchJson("/api/admin/checkout");
  presenceTableStates.checkout.rawRows = Array.isArray(rows) ? rows : [];
  if (presenceTableStates.missingCheckout) {
    presenceTableStates.missingCheckout.rawRows = [];
  }
  applyPresenceTableState("checkout");
  updateDashboardSummary();
}

async function loadInactive() {
  const rows = await fetchJson("/api/admin/inactive");
  presenceTableStates.inactive.rawRows = Array.isArray(rows) ? rows : [];
  applyPresenceTableState("inactive");
  updateDashboardSummary();
}

async function loadPending() {
  const rows = await fetchJson("/api/admin/pending");
  pendingUsersTotal = Array.isArray(rows) ? rows.length : 0;
  const body = document.getElementById("pendingBody");
  body.innerHTML = "";
  rows.forEach((row) => body.appendChild(makePendingRow(row)));
  applyResponsiveLabels("pendingBody");
  updateDashboardSummary();
}

async function loadAdministrators() {
  const rows = await fetchJson("/api/admin/administrators");
  const normalizedRows = Array.isArray(rows) ? rows : [];
  const adminRows = normalizedRows.filter((row) => row.row_type === "admin");
  administratorsTotal = adminRows.length;
  const body = document.getElementById("administratorsBody");
  body.innerHTML = "";
  if (normalizedRows.length === 0) {
    renderEmptyStateRow("administratorsBody", 5, "Nenhum administrador ou solicitacao pendente encontrada.");
  } else {
    normalizedRows.forEach((row) => body.appendChild(makeAdministratorRow(row)));
  }
  applyResponsiveLabels("administratorsBody");
  updateDashboardSummary();
}

async function loadProjects() {
  const rows = await fetchJson("/api/admin/projects");
  setProjectCatalog(rows);
  if (locationRows.length > 0) {
    renderLocations();
  }

  const body = document.getElementById("projectsBody");
  if (!body) {
    return rows;
  }

  body.innerHTML = "";
  if (!rows.length) {
    renderEmptyStateRow("projectsBody", 2, "Nenhum projeto cadastrado.");
    return rows;
  }

  rows.forEach((project) => body.appendChild(makeProjectRow(project)));
  applyResponsiveLabels("projectsBody");
  return rows;
}

async function loadRegisteredUsers() {
  const rows = await fetchJson("/api/admin/users");
  registeredUsersTotal = rows.length;
  const body = document.getElementById("usersBody");
  body.innerHTML = "";
  rows.forEach((user) => body.appendChild(makeRegisteredUserRow(user)));
  applyResponsiveLabels("usersBody");
  syncUserTitles();
  updateDashboardSummary();
  scheduleUserFieldTextareaRefresh();
}

async function createProject() {
  if (hasPendingEditInProgress()) {
    setStatus("Salve ou cancele as edições pendentes antes de alterar os projetos.", false);
    return;
  }

  const projectName = window.prompt("Informe o nome do projeto.");
  if (projectName === null) {
    return;
  }

  if (!projectName.trim()) {
    setStatus("Informe o nome do projeto.", false);
    return;
  }

  await postJson("/api/admin/projects", { name: projectName });
  setStatus("Projeto adicionado com sucesso", true);
  await Promise.all([loadProjects(), loadPending(), loadRegisteredUsers()]);
}

async function removeProject(projectId) {
  if (hasPendingEditInProgress()) {
    setStatus("Salve ou cancele as edições pendentes antes de alterar os projetos.", false);
    return;
  }

  const normalizedProjectId = requireIntegerId(projectId, "Projeto");
  const confirmed = window.confirm("Deseja remover este projeto?");
  if (!confirmed) {
    return;
  }

  await deleteJson(`/api/admin/projects/${normalizedProjectId}`);
  setStatus("Projeto removido com sucesso", true);
  await Promise.all([loadProjects(), loadPending(), loadRegisteredUsers()]);
}

async function loadEvents() {
  const rows = await fetchJson("/api/admin/events");
  eventsTotal = Array.isArray(rows) ? rows.length : 0;
  const body = document.getElementById("eventsBody");
  body.innerHTML = "";
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    const eventDetails = {
      message: row.message ?? "-",
      details: formatEventDetails(row.details),
    };
    tr.innerHTML = `<td>${makeEventCell(row.id)}</td><td>${makeEventDateTimeCell(row.event_time)}</td><td>${makeEventCell(row.source)}</td><td>${makeEventCell(formatAction(row.action))}</td><td>${makeEventCell(row.status)}</td><td>${makeEventCell(row.device_id ?? "-")}</td><td>${makeEventCell(formatLocal(row.local))}</td><td>${makeEventCell(row.rfid ?? "-")}</td><td>${makeEventCell(row.chave ?? "-")}</td><td>${makeEventCell(row.project ?? "-")}</td><td>${makeEventCell(formatOntime(row.ontime))}</td><td>${makeEventCell(row.http_status ?? "-")}</td><td>${makeEventCell(row.retry_count ?? 0)}</td><td>${makeEventDetailsButton()}</td>`;
    tr.querySelector(".event-details-button").addEventListener("click", () => openEventDetails(eventDetails));
    body.appendChild(tr);
  });
  applyResponsiveLabels("eventsBody");
  updateDashboardSummary();
}

async function loadForms() {
  const body = document.getElementById("formsBody");
  if (!body) {
    formsTotal = 0;
    updateFormsClearButtonState();
    updateDashboardSummary();
    return;
  }

  const rows = await fetchJson("/api/admin/forms");
  formsTotal = Array.isArray(rows) ? rows.length : 0;
  setTextContentIfPresent("formsTitle", `Forms (${formsTotal})`);
  updateFormsClearButtonState();
  body.innerHTML = "";
  if (formsTotal === 0) {
    renderEmptyStateRow("formsBody", 8, "Nenhum registro recebido do endpoint updaterecords.");
    updateDashboardSummary();
    return;
  }

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${makeEventDateTimeCell(row.recebimento)}</td><td>${makeEventCell(row.chave ?? "-")}</td><td>${makeEventCell(row.nome ?? "-", "event-cell-left")}</td><td>${makeEventCell(row.projeto ?? "-")}</td><td>${makeEventCell(row.atividade ?? "-")}</td><td>${makeEventCell(row.informe ?? "-")}</td><td>${makeEventCell(row.data ?? "-")}</td><td>${makeEventCell(row.hora ?? "-")}</td>`;
    body.appendChild(tr);
  });
  applyResponsiveLabels("formsBody");
  updateDashboardSummary();
}

function updateFormsClearButtonState() {
  const clearButton = document.getElementById("clearFormsButton");
  if (!clearButton) {
    return;
  }
  clearButton.disabled = formsTotal === 0;
}

async function clearForms() {
  const confirmed = window.confirm("Deseja remover todos os registros da aba Forms?");
  if (!confirmed) {
    return;
  }

  const clearButton = document.getElementById("clearFormsButton");
  if (clearButton) {
    clearButton.disabled = true;
  }

  try {
    const payload = await deleteJson("/api/admin/forms");
    await loadForms();
    requestRefreshAllTables();
    setStatus(payload?.message || "Registros de Forms removidos com sucesso.", true);
  } finally {
    updateFormsClearButtonState();
  }
}

async function refreshActiveTab() {
  if (activeTab === "checkin") {
    await loadCheckin();
    markDashboardRefreshed();
    return;
  }
  if (activeTab === "checkout") {
    await loadCheckout();
    markDashboardRefreshed();
    return;
  }
  if (activeTab === "forms") {
    return;
  }
  if (activeTab === "inactive") {
    return;
  }
  if (activeTab === "cadastro") {
    if (!hasPendingEditInProgress()) {
      await loadProjects();
      await Promise.all([loadPending(), loadLocations()]);
      markDashboardRefreshed();
    }
    return;
  }
  if (activeTab === "banco-dados") {
    await loadDatabaseEvents();
    markDashboardRefreshed();
    return;
  }
}

async function refreshAllTables() {
  const jobs = [loadCheckin(), loadCheckout(), loadForms(), loadInactive(), loadEvents(), loadAdministrators()];
  if (databaseEventsLoaded) {
    jobs.push(loadDatabaseEvents());
  }
  if (!hasPendingEditInProgress()) {
    await loadProjects();
    jobs.push(loadPending());
    jobs.push(loadRegisteredUsers());
    jobs.push(loadLocations());
  }
  await Promise.all(jobs);
  markDashboardRefreshed();
}

async function refreshAutomaticTables() {
  const jobs = [loadCheckin(), loadCheckout()];
  if (databaseEventsLoaded) {
    jobs.push(loadDatabaseEvents());
  }
  if (!hasPendingEditInProgress()) {
    await loadProjects();
    jobs.push(loadPending());
    jobs.push(loadLocations());
  }
  await Promise.all(jobs);
  markDashboardRefreshed();
}

function startAutoRefresh() {
  stopAutoRefresh();
  autoRefreshHandle = window.setInterval(() => {
    if (document.hidden || realtimeConnected || !isAuthenticated) {
      return;
    }
    refreshAutomaticTables().catch((error) => setStatus(error.message, false));
  }, AUTO_REFRESH_MS);
}

function stopAutoRefresh() {
  if (autoRefreshHandle !== null) {
    window.clearInterval(autoRefreshHandle);
    autoRefreshHandle = null;
  }
}

function requestRefreshAllTables() {
  if (refreshAllTimer !== null) {
    window.clearTimeout(refreshAllTimer);
  }
  refreshAllTimer = window.setTimeout(() => {
    refreshAutomaticTables().catch((error) => setStatus(error.message, false));
    refreshAllTimer = null;
  }, REALTIME_DEBOUNCE_MS);
}

function startRealtimeUpdates() {
  stopRealtimeUpdates();
  eventStream = new EventSource("/api/admin/stream");
  eventStream.onopen = () => {
    realtimeConnected = true;
    updateOperationalChrome();
  };
  eventStream.onmessage = () => {
    realtimeConnected = true;
    updateOperationalChrome();
    requestRefreshAllTables();
  };
  eventStream.onerror = () => {
    realtimeConnected = false;
    updateOperationalChrome();
  };
}

function stopRealtimeUpdates() {
  if (eventStream) {
    eventStream.close();
    eventStream = null;
  }
  realtimeConnected = false;
  updateOperationalChrome();
}

function parseDownloadFileName(contentDisposition, fallbackName) {
  const match = /filename="?([^";]+)"?/i.exec(contentDisposition || "");
  return match ? match[1] : fallbackName;
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  const decimals = unitIndex === 0 ? 0 : size >= 10 ? 1 : 2;
  return `${size.toFixed(decimals)} ${units[unitIndex]}`;
}

function downloadBlob(blob, fileName) {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

async function fetchBlob(url, fallbackName) {
  const res = await fetch(url, { credentials: "same-origin" });
  if (!res.ok) {
    const message = await parseErrorResponse(res);
    if (res.status === 401) {
      await handleUnauthorized(message);
    }
    throw new Error(message);
  }
  const blob = await res.blob();
  return {
    blob,
    fileName: parseDownloadFileName(res.headers.get("Content-Disposition"), fallbackName),
  };
}

async function loadEventArchives() {
  const params = new URLSearchParams({
    page: String(eventArchivesPage),
    page_size: String(ARCHIVE_PAGE_SIZE),
  });
  if (eventArchivesFilterQuery.trim()) {
    params.set("q", eventArchivesFilterQuery.trim());
  }
  const payload = await fetchJson(`/api/admin/events/archives?${params.toString()}`);
  renderEventArchives(payload);
  return payload;
}

function updateArchivePagination() {
  const prevButton = document.getElementById("eventArchivesPrev");
  const nextButton = document.getElementById("eventArchivesNext");
  const pageInfo = document.getElementById("eventArchivesPageInfo");
  prevButton.disabled = eventArchivesPage <= 1 || eventArchivesTotal === 0;
  nextButton.disabled = eventArchivesPage >= eventArchivesTotalPages || eventArchivesTotal === 0;
  pageInfo.textContent = `Página ${eventArchivesTotal === 0 ? 0 : eventArchivesPage} de ${eventArchivesTotal === 0 ? 0 : eventArchivesTotalPages}`;
}

function updateArchiveSummary() {
  const summary = document.getElementById("eventArchivesSummary");
  const storageSummary = document.getElementById("eventArchivesStorage");
  summary.textContent = eventArchivesFilterQuery.trim() ? `${eventArchives.length} de ${eventArchivesTotal} logs` : `${eventArchivesTotal} logs`;
  storageSummary.textContent = `Espaço total usado: ${formatBytes(eventArchivesTotalSizeBytes)}`;
}

function renderEventArchives(payload) {
  eventArchives = payload.items || [];
  eventArchivesTotal = payload.total || 0;
  eventArchivesTotalSizeBytes = payload.total_size_bytes || 0;
  eventArchivesPage = payload.page || 1;
  eventArchivesTotalPages = payload.total_pages || 0;
  const body = document.getElementById("eventArchivesBody");
  const emptyState = document.getElementById("eventArchivesEmpty");
  const downloadAllButton = document.getElementById("downloadAllEventArchives");
  body.innerHTML = "";
  updateArchiveSummary();
  updateArchivePagination();
  if (!eventArchives.length) {
    emptyState.classList.remove("hidden");
    downloadAllButton.disabled = true;
    return;
  }

  emptyState.classList.add("hidden");
  downloadAllButton.disabled = false;
  eventArchives.forEach((archive) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><span class="archive-period">${escapeHtml(archive.period)}</span></td>
      <td><span class="archive-record-count">${escapeHtml(archive.record_count)}</span></td>
      <td><span class="archive-size">${escapeHtml(formatBytes(archive.size_bytes))}</span></td>
      <td>
        <div class="archive-actions">
          <button type="button" class="archive-download-button" data-archive-download="${escapeHtml(archive.file_name)}">Baixar</button>
          <button type="button" class="archive-delete-button" data-archive-delete="${escapeHtml(archive.file_name)}">Excluir</button>
        </div>
      </td>
    `;
    body.appendChild(row);
  });
}

async function downloadEventArchive(fileName) {
  const { blob, fileName: resolvedName } = await fetchBlob(`/api/admin/events/archives/${encodeURIComponent(fileName)}`, fileName);
  downloadBlob(blob, resolvedName);
}

async function downloadAllEventArchives() {
  const { blob, fileName } = await fetchBlob("/api/admin/events/archives/download-all", "eventos-archives.zip");
  downloadBlob(blob, fileName);
}

async function deleteEventArchive(fileName) {
  await deleteJson(`/api/admin/events/archives/${encodeURIComponent(fileName)}`);
  const archives = await loadEventArchives();
  setStatus(`Arquivo ${fileName} excluído com sucesso.`, true);
  if (!archives.total) {
    setStatus("Todos os logs salvos foram excluídos.", true);
  }
}

async function archiveAndClearEvents() {
  const confirmed = window.confirm("Deseja salvar os eventos atuais em CSV e limpar a lista de eventos?\n\nOs arquivos antigos continuarão disponíveis para download.");
  if (!confirmed) {
    return;
  }

  const payload = await postJson("/api/admin/events/archive");
  eventArchivesPage = 1;
  renderEventArchives(payload.archives || {});
  openEventArchivesModal();
  await loadEvents();
  if (databaseEventsLoaded) {
    await loadDatabaseEvents();
  }

  if (payload.created && payload.archive) {
    setStatus(`Eventos salvos em ${payload.archive.period} e limpos (${payload.cleared_count} registros).`, true);
    return;
  }
  setStatus("Não havia eventos novos para salvar. Logs já salvos exibidos na janela.", true);
}

async function refreshManualTable(loader) {
  await loader();
  markDashboardRefreshed();
}

async function runManualRefresh(button, loader) {
  if (!(button instanceof HTMLButtonElement) || button.disabled) {
    return;
  }

  const idleLabel = String(button.dataset.idleLabel || button.textContent || "Atualizar").trim() || "Atualizar";
  button.dataset.idleLabel = idleLabel;
  button.disabled = true;
  button.classList.add("is-loading");
  button.setAttribute("aria-busy", "true");
  button.textContent = "Atualizando...";

  try {
    await refreshManualTable(loader);
  } finally {
    button.disabled = false;
    button.classList.remove("is-loading");
    button.setAttribute("aria-busy", "false");
    button.textContent = idleLabel;
  }
}

function bindManualRefreshButton(button, loader) {
  if (!(button instanceof HTMLButtonElement)) {
    return;
  }

  button.dataset.idleLabel = String(button.textContent || "Atualizar").trim() || "Atualizar";
  button.addEventListener("click", () => {
    runManualRefresh(button, loader).catch((error) => setStatus(error.message, false));
  });
}

async function savePending(id, rfid) {
  const nome = document.getElementById(`nome-${id}`).value.trim();
  const chave = document.getElementById(`chave-${id}`).value.trim().toUpperCase();
  const projeto = document.getElementById(`projeto-${id}`).value;
  if (!nome || chave.length !== 4) {
    setStatus("Preencha nome e chave de 4 caracteres", false);
    return;
  }
  const payload = await postJson("/api/admin/users", { rfid, nome, chave, projeto });
  if (payload?.linked_existing_user) {
    setStatus("Cadastro salvo com sucesso e RFID vinculado ao usuário já existente pela chave.", true);
  } else {
    setStatus("Cadastro salvo com sucesso", true);
  }
  await Promise.all([loadPending(), loadRegisteredUsers()]);
}

async function removePending(id) {
  await deleteJson(`/api/admin/pending/${id}`);
  setStatus("Pendência removida com sucesso", true);
  await loadPending();
}

async function saveRegisteredUser(userId) {
  const normalizedUserId = requireIntegerId(userId, "Usuário");
  const row = document.querySelector(`#usersBody tr[data-user-id="${CSS.escape(normalizedUserId)}"]`);
  if (!row) {
    return;
  }
  const rfidValue = row.querySelector(".user-rfid").value.trim();
  const nome = row.querySelector(".user-nome").value.trim();
  const chave = row.querySelector(".user-chave").value.trim().toUpperCase();
  const perfilValue = row.querySelector(".user-perfil").value.trim();
  const projeto = row.querySelector(".user-projeto").value;
  const endRua = row.querySelector(".user-end-rua").value.trim();
  const zip = row.querySelector(".user-zip").value.trim();
  const cargo = row.querySelector(".user-cargo").value.trim();
  const email = row.querySelector(".user-email").value.trim().toLowerCase();
  if (!nome || chave.length !== 4) {
    setStatus("Preencha nome e chave de 4 caracteres", false);
    return;
  }
  if (!/^\d{1,3}$/.test(perfilValue)) {
    setStatus("Informe um perfil numérico entre 0 e 999.", false);
    return;
  }
  await postJson("/api/admin/users", {
    user_id: Number(normalizedUserId),
    rfid: rfidValue || null,
    nome,
    chave,
    perfil: Number(perfilValue),
    projeto,
    end_rua: endRua || null,
    zip: zip || null,
    cargo: cargo || null,
    email: email || null,
  });
  setStatus("Usuário salvo com sucesso", true);
  await loadRegisteredUsers();
}

async function removeRegisteredUser(userId) {
  const normalizedUserId = requireIntegerId(userId, "Usuário");
  await deleteJson(`/api/admin/users/${normalizedUserId}`);
  setStatus("Usuário removido com sucesso", true);
  await Promise.all([loadRegisteredUsers(), loadCheckin(), loadCheckout(), loadInactive()]);
}

async function resetRegisteredUserPassword(userId) {
  const normalizedUserId = requireIntegerId(userId, "Usuário");
  const confirmed = window.confirm(
    "Deseja remover a senha deste usuário?\n\nDepois disso, ele precisará cadastrar uma nova senha para voltar a acessar a área web.",
  );
  if (!confirmed) {
    return;
  }

  const payload = await postJson(`/api/admin/users/${normalizedUserId}/reset-password`);
  setStatus(payload.message, true);
  await loadRegisteredUsers();
}

async function approveAdministrator(id) {
  const profile = readAdministratorProfileValue(id);
  const payload = await postJson(`/api/admin/administrators/requests/${id}/approve`, { perfil: profile });
  setStatus(payload.message, true);
  await loadAdministrators();
}

async function rejectAdministrator(id) {
  const payload = await postJson(`/api/admin/administrators/requests/${id}/reject`);
  setStatus(payload.message, true);
  await loadAdministrators();
}

async function revokeAdministrator(id) {
  const confirmed = window.confirm("Deseja revogar o acesso deste administrador?");
  if (!confirmed) {
    return;
  }
  const payload = await postJson(`/api/admin/administrators/${id}/revoke`);
  setStatus(payload.message, true);
  await loadAdministrators();
}

async function saveAdministratorProfile(id) {
  const profile = readAdministratorProfileValue(id);
  const payload = await postJson(`/api/admin/administrators/${id}/profile`, { perfil: profile });
  setStatus(payload.message, true);
  await loadAdministrators();
}

async function saveAdministratorPassword(id) {
  const input = document.getElementById(`admin-password-input-${id}`);
  const novaSenha = input.value;
  if (novaSenha.length < 3 || novaSenha.length > 20) {
    setStatus("A nova senha deve ter entre 3 e 20 caracteres.", false);
    return;
  }
  const payload = await postJson(`/api/admin/administrators/${id}/set-password`, { nova_senha: novaSenha });
  toggleAdminPasswordEditor(id, false);
  setStatus(payload.message, true);
  await loadAdministrators();
}

async function submitLogin() {
  const chave = normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "");
  const senha = loginSenhaInput ? loginSenhaInput.value : "";
  if (loginChaveInput) {
    loginChaveInput.value = chave;
  }
  if (chave.length !== 4 || !/^[A-Z0-9]{4}$/i.test(chave)) {
    setAuthStatus("A chave deve ter 4 caracteres alfanuméricos.", "error");
    return;
  }
  if (senha.length < 3 || senha.length > 20) {
    setAuthStatus("A senha deve ter entre 3 e 20 caracteres.", "error");
    return;
  }

  const payload = await postJson("/api/admin/auth/login", { chave, senha });
  setAuthStatus(payload.message, "success");
  if (loginSenhaInput) {
    loginSenhaInput.value = "";
  }
  await bootstrapAdmin();
}

async function submitRequestAdminRegistration() {
  const chave = normalizeAdminChave(requestAdminRegistrationChaveInput ? requestAdminRegistrationChaveInput.value : "");
  const nomeCompleto = requestAdminRegistrationNomeInput ? requestAdminRegistrationNomeInput.value.trim() : "";
  const projeto = requestAdminRegistrationProjetoSelect ? requestAdminRegistrationProjetoSelect.value.trim() : "";
  const senha = requestAdminRegistrationSenhaInput ? requestAdminRegistrationSenhaInput.value : "";
  const confirmarSenha = requestAdminRegistrationConfirmInput ? requestAdminRegistrationConfirmInput.value : "";

  if (!isAdminRequestKeyValid(chave)) {
    setRequestAdminRegistrationStatus("A chave deve ter 4 caracteres alfanumericos.", "error");
    return;
  }
  if (nomeCompleto.length < 3) {
    setRequestAdminRegistrationStatus("Informe o nome completo.", "error");
    return;
  }
  if (projeto.length < 2) {
    setRequestAdminRegistrationStatus("Selecione o projeto do usuario.", "error");
    return;
  }
  if (!isAdminRequestPasswordValid(senha)) {
    setRequestAdminRegistrationStatus("A senha deve ter entre 3 e 10 caracteres.", "error");
    return;
  }
  if (senha !== confirmarSenha) {
    setRequestAdminRegistrationStatus("A confirmacao de senha nao confere.", "error");
    return;
  }

  requestAdminRegistrationSaveInProgress = true;
  syncRequestAdminRegistrationFormState();
  try {
    const payload = await postJson("/api/admin/auth/request-access/self-service", {
      chave,
      nome_completo: nomeCompleto,
      projeto,
      senha,
      confirmar_senha: confirmarSenha,
    });
    setRequestAdminRegistrationStatus(payload.message, "success");
    setAuthStatus(payload.message, "success");
    window.setTimeout(() => {
      closeRequestAdminRegistrationModal();
      closeRequestAdminModal();
    }, 700);
  } finally {
    requestAdminRegistrationSaveInProgress = false;
    syncRequestAdminRegistrationFormState();
  }
}

async function submitPasswordReset() {
  const chave = document.getElementById("loginChave").value.trim().toUpperCase();
  if (!chave) {
    setAuthStatus("Informe sua chave antes de solicitar o recadastro da senha.", "error");
    return;
  }
  if (chave.length !== 4 || !/^[A-Z0-9]{4}$/i.test(chave)) {
    setAuthStatus("A chave deve ter 4 caracteres alfanuméricos.", "error");
    return;
  }

  const payload = await postJson("/api/admin/auth/request-password-reset", { chave });
  document.getElementById("loginSenha").value = "";
  setAuthStatus(payload.message, "success");
}

async function logout() {
  await postJson("/api/admin/auth/logout");
  showAuthShell("Sessão encerrada com sucesso.", "success");
}

async function bootstrapAdmin() {
  const session = await fetchJson("/api/admin/auth/session");
  if (!session.authenticated || !session.admin) {
    showAuthShell("", "info");
    return;
  }

  showAdminShell(session.admin);
  startAutoRefresh();
  startRealtimeUpdates();
  await refreshAllTables();
  setStatus("Painel administrativo carregado.", true);
}

function bindLocationSettingsInput(inputId) {
  const input = document.getElementById(inputId);
  if (!input) {
    return;
  }

  input.addEventListener("input", handleLocationSettingsInputChange);
  input.addEventListener("change", handleLocationSettingsInputChange);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      discardLocationSettingsDraft();
      event.currentTarget.blur();
    }
  });
}

function bindActions() {
  document.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  document.querySelectorAll(".presence-controls").forEach((container) => {
    const tableKey = container.dataset.presenceTable;

    const handlePresenceFilterChange = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement) || !target.dataset.presenceFilter) {
        return;
      }
      const state = getPresenceTableState(tableKey);
      if (!state) {
        return;
      }
      state.filters[target.dataset.presenceFilter] = target.value;
      applyPresenceTableState(tableKey);
    };

    container.addEventListener("input", handlePresenceFilterChange);
    container.addEventListener("change", handlePresenceFilterChange);

    container.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLButtonElement) || target.dataset.presenceClear === undefined) {
        return;
      }
      resetPresenceControls(tableKey);
      applyPresenceTableState(tableKey);
      setStatus("Filtros limpos com sucesso.", true);
    });
  });

  const databaseTab = document.getElementById("tab-banco-dados");
  if (databaseTab) {
    const handleDatabaseFilterChange = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement) || !target.dataset.databaseEventFilter) {
        return;
      }

      const filterKey = target.dataset.databaseEventFilter;
      let nextValue = target.value;

      if (filterKey === "chave") {
        nextValue = nextValue.replace(/\s+/g, "").toUpperCase().slice(0, 4);
        target.value = nextValue;
      } else if (filterKey === "project") {
        nextValue = nextValue.toUpperCase();
      } else if (["action", "source", "status"].includes(filterKey)) {
        nextValue = nextValue.toLowerCase();
      }

      databaseEventsState.filters[filterKey] = nextValue;
      databaseEventsState.page = 1;

      const shouldDebounce = event.type === "input" && (target.type === "search" || target.type === "text");
      scheduleDatabaseEventsRefresh(shouldDebounce ? REALTIME_DEBOUNCE_MS : 0);
    };

    databaseTab.addEventListener("input", handleDatabaseFilterChange);
    databaseTab.addEventListener("change", handleDatabaseFilterChange);

    const clearDatabaseFiltersButton = document.getElementById("databaseEventsClearFilters");
    if (clearDatabaseFiltersButton) {
      clearDatabaseFiltersButton.addEventListener("click", () => {
        resetDatabaseEventFilters();
        scheduleDatabaseEventsRefresh(0);
        setStatus("Filtros do banco de dados limpos com sucesso.", true);
      });
    }

    const previousButton = document.getElementById("databaseEventsPrev");
    if (previousButton) {
      previousButton.addEventListener("click", () => {
        if (databaseEventsState.page <= 1) {
          return;
        }
        databaseEventsState.page -= 1;
        loadDatabaseEvents().catch((error) => setStatus(error.message, false));
      });
    }

    const nextButton = document.getElementById("databaseEventsNext");
    if (nextButton) {
      nextButton.addEventListener("click", () => {
        if (databaseEventsState.page >= databaseEventsState.totalPages) {
          return;
        }
        databaseEventsState.page += 1;
        loadDatabaseEvents().catch((error) => setStatus(error.message, false));
      });
    }
  }

  document.querySelector("main").addEventListener("click", (event) => {
    const target = event.target;
    const sortButton = target instanceof Element ? target.closest(".sortable-header") : null;
    if (!sortButton) {
      return;
    }

    const tableKey = sortButton.dataset.sortTable;
    const sortKey = sortButton.dataset.sortKey;
    if (tableKey === "databaseEvents") {
      applyDatabaseEventSort(sortKey);
      loadDatabaseEvents().catch((error) => setStatus(error.message, false));
      return;
    }
    const state = getPresenceTableState(tableKey);
    if (!state || !sortKey) {
      return;
    }

    if (state.sortKey === sortKey) {
      state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
    } else {
      state.sortKey = sortKey;
      state.sortDirection = getPresenceDefaultSortDirection(sortKey);
    }

    applyPresenceTableState(tableKey);
  });

  document.getElementById("loginButton").addEventListener("click", () => {
    submitLogin().catch((error) => setAuthStatus(error.message, "error"));
  });
  if (loginChaveInput) {
    loginChaveInput.addEventListener("input", () => {
      const normalized = normalizeAdminChave(loginChaveInput.value);
      if (normalized !== loginChaveInput.value) {
        loginChaveInput.value = normalized;
      }
      if (isChangePasswordModalOpen()) {
        scheduleChangePasswordVerification();
        syncChangePasswordFormState();
      }
    });
  }
  document.getElementById("loginSenha").addEventListener("keydown", (event) => {
        setChangePasswordStatus("");
  });
  document.getElementById("logoutButton").addEventListener("click", () => {
    logout().catch((error) => setAuthStatus(error.message, "error"));
  });

  const clearFormsButton = document.getElementById("clearFormsButton");
  if (clearFormsButton) {
    clearFormsButton.addEventListener("click", () => {
      clearForms().catch((error) => setStatus(error.message, false));
    });
  }

  const changePasswordButton = document.getElementById("changePasswordButton");
  const refreshFormsButton = document.getElementById("refreshFormsButton");
  const refreshInactiveButton = document.getElementById("refreshInactiveButton");
  const refreshAdministratorsButton = document.getElementById("refreshAdministratorsButton");
  const refreshUsersButton = document.getElementById("refreshUsersButton");
  const refreshEventsButton = document.getElementById("refreshEventsButton");
  if (changePasswordButton) {
    changePasswordButton.addEventListener("click", openChangePasswordModal);
  }
  bindManualRefreshButton(refreshFormsButton, loadForms);
  bindManualRefreshButton(refreshInactiveButton, loadInactive);
  bindManualRefreshButton(refreshAdministratorsButton, loadAdministrators);
  bindManualRefreshButton(refreshUsersButton, loadRegisteredUsers);
  bindManualRefreshButton(refreshEventsButton, loadEvents);
  if (changePasswordForm) {
    changePasswordForm.addEventListener("submit", (event) => {
      event.preventDefault();
      submitChangePassword().catch((error) => setChangePasswordStatus(error.message, "error"));
    });
  }
  [changePasswordCurrentInput, changePasswordNewInput, changePasswordConfirmInput].filter(Boolean).forEach((input) => {
    input.addEventListener("input", () => {
      if (input === changePasswordCurrentInput) {
        scheduleChangePasswordVerification();
      } else {
        syncChangePasswordFormState();
      }
    });
  });
  if (changePasswordBackButton) {
    changePasswordBackButton.addEventListener("click", closeChangePasswordModal);
  }
  if (changePasswordModal) {
    changePasswordModal.addEventListener("click", (event) => {
      if (event.target.id === "changePasswordModal") {
        closeChangePasswordModal();
      }
    });
  }
  if (requestAdminModal) {
    requestAdminModal.addEventListener("click", (event) => {
      if (event.target.id === "requestAdminModal") {
        closeRequestAdminModal();
      }
    });
  }
  if (requestAdminButton) {
    requestAdminButton.addEventListener("click", openRequestAdminModal);
  }
  if (requestAdminBackButton) {
    requestAdminBackButton.addEventListener("click", closeRequestAdminModal);
  }
  if (requestAdminChaveInput) {
    requestAdminChaveInput.addEventListener("input", scheduleRequestAdminLookup);
  }
  if (requestAdminRegistrationForm) {
    requestAdminRegistrationForm.addEventListener("submit", (event) => {
      event.preventDefault();
      submitRequestAdminRegistration().catch((error) => {
        setRequestAdminRegistrationStatus(error.message, "error");
      });
    });
  }
  [
    requestAdminRegistrationNomeInput,
    requestAdminRegistrationProjetoSelect,
    requestAdminRegistrationSenhaInput,
    requestAdminRegistrationConfirmInput,
  ].filter(Boolean).forEach((input) => {
    input.addEventListener("input", syncRequestAdminRegistrationFormState);
    input.addEventListener("change", syncRequestAdminRegistrationFormState);
  });
  if (requestAdminRegistrationBackButton) {
    requestAdminRegistrationBackButton.addEventListener("click", returnToRequestAdminLookupModal);
  }
  if (requestAdminRegistrationModal) {
    requestAdminRegistrationModal.addEventListener("click", (event) => {
      if (event.target.id === "requestAdminRegistrationModal") {
        returnToRequestAdminLookupModal();
      }
    });
  }

  document.getElementById("clearEvents").addEventListener("click", () => {
    archiveAndClearEvents().catch((error) => setStatus(error.message, false));
  });
  document.getElementById("closeEventDetails").addEventListener("click", closeEventDetails);
  document.getElementById("closeEventArchives").addEventListener("click", closeEventArchivesModal);
  document.getElementById("closeEventArchivesFooter").addEventListener("click", closeEventArchivesModal);
  document.getElementById("downloadAllEventArchives").addEventListener("click", () => {
    downloadAllEventArchives().catch((error) => setStatus(error.message, false));
  });
  document.getElementById("eventArchivesFilter").addEventListener("input", (event) => {
    eventArchivesFilterQuery = event.target.value || "";
    eventArchivesPage = 1;
    loadEventArchives().catch((error) => setStatus(error.message, false));
  });
  document.getElementById("eventArchivesPrev").addEventListener("click", () => {
    if (eventArchivesPage > 1) {
      eventArchivesPage -= 1;
      loadEventArchives().catch((error) => setStatus(error.message, false));
    }
  });
  document.getElementById("eventArchivesNext").addEventListener("click", () => {
    if (eventArchivesPage < eventArchivesTotalPages) {
      eventArchivesPage += 1;
      loadEventArchives().catch((error) => setStatus(error.message, false));
    }
  });
  document.getElementById("eventDetailsModal").addEventListener("click", (event) => {
    if (event.target.id === "eventDetailsModal") {
      closeEventDetails();
    }
  });
  document.getElementById("eventArchivesModal").addEventListener("click", (event) => {
    if (event.target.id === "eventArchivesModal") {
      closeEventArchivesModal();
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && isAuthenticated) {
      requestRefreshAllTables();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeEventDetails();
      closeEventArchivesModal();
      closeChangePasswordModal();
      const requestAdminRegistrationOpen = requestAdminRegistrationModal && !requestAdminRegistrationModal.classList.contains("hidden");
      if (requestAdminRegistrationOpen) {
        returnToRequestAdminLookupModal();
        return;
      }
      if (requestAdminModal && !requestAdminModal.classList.contains("hidden")) {
        closeRequestAdminModal();
      }
    }
  });
  window.addEventListener("resize", scheduleUserFieldTextareaRefresh);

  document.getElementById("eventArchivesBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName === "BUTTON" && target.dataset.archiveDownload) {
      downloadEventArchive(target.dataset.archiveDownload).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.archiveDelete) {
      const fileName = target.dataset.archiveDelete;
      const confirmed = window.confirm(`Deseja excluir permanentemente o arquivo ${fileName}?`);
      if (!confirmed) {
        return;
      }
      deleteEventArchive(fileName).catch((error) => setStatus(error.message, false));
    }
  });

  document.getElementById("pendingBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName === "BUTTON" && target.dataset.edit) {
      setPendingEditingState(target.dataset.edit, true);
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.remove) {
      removePending(target.dataset.remove).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.save) {
      savePending(target.dataset.save, target.dataset.rfid).catch((error) => setStatus(error.message, false));
    }
  });

  document.getElementById("addLocationButton").addEventListener("click", addLocationRow);
  document.getElementById("saveLocationSettingsButton").addEventListener("click", () => {
    saveLocationSettings().catch((error) => setStatus(error.message, false));
  });
  bindLocationSettingsInput("locationAccuracyThresholdMeters");

  document.getElementById("locationsBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName !== "BUTTON") {
      return;
    }
    if (target.dataset.locationProjectsToggle) {
      const row = getLocationRowById(target.dataset.locationProjectsToggle);
      if (!row) {
        return;
      }

      if (row.projectPickerOpen) {
        saveLocationRow(row.id).catch((error) => setStatus(error.message, false));
        return;
      }

      captureLocationRowDraft(row.id);
      if (!row.isEditing) {
        row.isEditing = true;
      }
      row.projectPickerOpen = true;
      renderLocations();
      if (row.projectPickerOpen) {
        focusLocationProjectPicker(row.id);
      }
      return;
    }
    if (target.dataset.locationEdit) {
      const row = getLocationRowById(target.dataset.locationEdit);
      if (!row) {
        return;
      }
      if (row.isEditing) {
        saveLocationRow(target.dataset.locationEdit).catch((error) => setStatus(error.message, false));
        return;
      }
      setLocationEditingState(target.dataset.locationEdit, true);
      return;
    }
    if (target.dataset.locationAddCoordinate) {
      addLocationCoordinate(target.dataset.locationAddCoordinate);
      return;
    }
    if (target.dataset.locationCoordinateRemove) {
      removeLocationCoordinate(
        target.dataset.locationCoordinateRemove,
        target.dataset.coordinateId,
      );
      return;
    }
    if (target.dataset.locationRemove) {
      removeLocationRow(target.dataset.locationRemove).catch((error) => setStatus(error.message, false));
    }
  });

  document.getElementById("usersBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName === "BUTTON" && target.dataset.userEdit) {
      setRegisteredUserEditingState(target.dataset.userEdit, true);
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.userSave) {
      saveRegisteredUser(target.dataset.userSave).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.userPasswordReset) {
      resetRegisteredUserPassword(target.dataset.userPasswordReset).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.userRemove) {
      removeRegisteredUser(target.dataset.userRemove).catch((error) => setStatus(error.message, false));
    }
  });

  const addProjectButton = document.getElementById("addProjectButton");
  if (addProjectButton) {
    addProjectButton.addEventListener("click", () => {
      createProject().catch((error) => setStatus(error.message, false));
    });
  }

  const projectsBody = document.getElementById("projectsBody");
  if (projectsBody) {
    projectsBody.addEventListener("click", (event) => {
      const target = event.target;
      if (target.tagName === "BUTTON" && target.dataset.projectRemove) {
        removeProject(target.dataset.projectRemove).catch((error) => setStatus(error.message, false));
      }
    });
  }

  document.getElementById("inactiveBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName === "BUTTON" && target.dataset.userRemove) {
      removeRegisteredUser(target.dataset.userRemove).catch((error) => setStatus(error.message, false));
    }
  });

  const missingCheckoutBody = document.getElementById("missingCheckoutBody");
  if (missingCheckoutBody) {
    missingCheckoutBody.addEventListener("click", (event) => {
      const target = event.target;
      if (target.tagName === "BUTTON" && target.dataset.userRemove) {
        removeRegisteredUser(target.dataset.userRemove).catch((error) => setStatus(error.message, false));
      }
    });
  }

  document.getElementById("administratorsBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName === "BUTTON" && target.dataset.adminApprove) {
      approveAdministrator(target.dataset.adminApprove).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.adminReject) {
      rejectAdministrator(target.dataset.adminReject).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.adminProfileSave) {
      saveAdministratorProfile(target.dataset.adminProfileSave).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.adminRevoke) {
      revokeAdministrator(target.dataset.adminRevoke).catch((error) => setStatus(error.message, false));
    }
  });

  Object.keys(presenceTableStates).forEach((tableKey) => {
    syncPresenceControls(tableKey);
    syncPresenceSortHeaders(tableKey);
  });
}

async function bootstrap() {
  bindActions();
  updateOperationalChrome();
  updateDashboardSummary();
  try {
    await bootstrapAdmin();
  } catch (error) {
    showAuthShell(error.message, "error");
  }
}

bootstrap();
