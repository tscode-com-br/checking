const authShell = document.getElementById("authShell");
const adminShell = document.getElementById("adminShell");
const statusLine = document.getElementById("statusLine");
const authStatus = document.getElementById("authStatus");
const sessionBar = document.getElementById("sessionBar");
const sessionUserLabel = document.getElementById("sessionUserLabel");

const AUTO_REFRESH_MS = 5000;
const REALTIME_DEBOUNCE_MS = 250;
const ARCHIVE_PAGE_SIZE = 8;

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

const PRESENCE_TABLE_CONFIGS = {
  checkin: {
    bodyId: "checkinBody",
    filterColumns: ["time", "nome", "chave", "projeto", "assiduidade", "local"],
    defaultSortKey: "time",
    defaultSortDirection: "desc",
    renderOptions: { highlightMissingCheckout: true, includeElapsedDays: true },
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

function setStatus(message, ok = true) {
  statusLine.textContent = message;
  statusLine.className = ok ? "status-ok" : "status-err";
}

function clearStatus() {
  statusLine.textContent = "";
  statusLine.className = "";
}

function showAuthShell(message = "", kind = "info") {
  isAuthenticated = false;
  locationSettingsDirty = false;
  authShell.classList.remove("hidden");
  adminShell.classList.add("hidden");
  sessionBar.classList.add("hidden");
  stopRealtimeUpdates();
  stopAutoRefresh();
  setAuthStatus(message, kind);
  clearStatus();
}

function showAdminShell(admin) {
  isAuthenticated = true;
  authShell.classList.add("hidden");
  adminShell.classList.remove("hidden");
  sessionBar.classList.remove("hidden");
  sessionUserLabel.textContent = `${admin.nome_completo} (${admin.chave})`;
  setAuthStatus("");
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
  const headers = Array.from(table.querySelectorAll("thead th")).map((th) => th.textContent.trim());
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

function openRequestAdminModal() {
  const modal = document.getElementById("requestAdminModal");
  document.getElementById("requestAdminStatus").textContent = "";
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

function closeRequestAdminModal() {
  const modal = document.getElementById("requestAdminModal");
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
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
    const tokens = rawFilterValue
      .toLocaleLowerCase()
      .split(/\s+/)
      .filter(Boolean);
    const searchableValue = String(getPresenceRowDisplayValue(tableKey, row, key) || "").toLocaleLowerCase();
    return tokens.every((token) => searchableValue.includes(token));
  }));
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

  container.querySelectorAll("[data-presence-filter]").forEach((input) => {
    const key = input.dataset.presenceFilter;
    input.value = state.filters[key] || "";
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
    tolerance: "",
    isEditing: false,
    ...overrides,
  };
  row.coordinates = normalizeLocationCoordinateEntries(overrides.coordinates);
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

function makeLocationCoordinateLines(row) {
  return row.coordinates.map((coordinate, index) => `
    <div class="location-coordinate-line">
      <input
        class="inline location-coordinate-input"
        data-coordinate-id="${escapeHtml(String(coordinate.id))}"
        maxlength="40"
        placeholder="1.255936, 103.611066"
        value="${escapeHtml(coordinate.value)}"
        ${row.isEditing ? "" : "disabled"}
      />
      ${row.isEditing && index > 0 ? `<button type="button" class="secondary-button location-coordinate-remove-button" data-location-coordinate-remove="${row.id}" data-coordinate-id="${escapeHtml(String(coordinate.id))}">Remover</button>` : ""}
    </div>
  `).join("");
}

function makeLocationRow(row) {
  const tr = document.createElement("tr");
  tr.className = "location-row";
  tr.dataset.locationId = String(row.id);
  tr.innerHTML = `
    <td class="location-cell">
      <div class="location-cell-stack">
        <input class="inline location-name" maxlength="100" value="${escapeHtml(row.local)}" ${row.isEditing ? "" : "disabled"} />
      </div>
    </td>
    <td class="location-cell location-coordinates-cell">
      <div class="location-coordinates-stack">${makeLocationCoordinateLines(row)}</div>
    </td>
    <td class="location-cell">
      <div class="location-cell-stack">
        <input class="inline location-tolerance" type="number" min="1" max="9999" inputmode="numeric" value="${escapeHtml(row.tolerance)}" ${row.isEditing ? "" : "disabled"} />
      </div>
    </td>
    <td class="pending-actions location-actions">
      <button type="button" data-location-edit="${row.id}">${row.isEditing ? "Salvar" : "Editar"}</button>
      <button type="button" class="secondary-button" data-location-add-coordinate="${row.id}">Adicionar Coordenadas</button>
      <button type="button" data-location-remove="${row.id}">Remover</button>
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
  const normalizedCoordinates = row.coordinates
    .map((coordinate) => String(coordinate.value || "").trim())
    .filter((value) => value)
    .map((value) => normalizeCoordinates(value));
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
      tolerance: String(row.tolerance_meters),
      isEditing: false,
    })
  );
  renderLocations();
  renderLocationSettings();
}

function makePendingRow(row) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${escapeHtml(row.rfid)}</td>
    <td><input class="inline" id="nome-${row.id}" disabled /></td>
    <td><input class="inline" id="chave-${row.id}" maxlength="4" disabled /></td>
    <td>
      <select class="inline" id="projeto-${row.id}" disabled>
        <option value="P80">P80</option>
        <option value="P82">P82</option>
        <option value="P83">P83</option>
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
  tr.dataset.userId = String(user.id);
  tr.innerHTML = `
    <td>${escapeHtml(user.rfid ?? "-")}</td>
    <td><input class="inline user-nome" value="${escapeHtml(user.nome)}" disabled /></td>
    <td><input class="inline user-chave" maxlength="4" value="${escapeHtml(user.chave)}" disabled /></td>
    <td>
      <select class="inline user-projeto" disabled>
        <option value="P80">P80</option>
        <option value="P82">P82</option>
        <option value="P83">P83</option>
      </select>
    </td>
    <td class="pending-actions">
      <button data-user-edit="${user.id}">Editar</button>
      <button data-user-save="${user.id}" disabled>Salvar</button>
      <button data-user-remove="${user.id}">Remover</button>
    </td>
  `;
  tr.querySelector(".user-projeto").value = user.projeto;
  return tr;
}

function makeAdministratorRow(row) {
  const tr = document.createElement("tr");
  const actions = [];
  if (row.can_revoke) {
    actions.push(`<button type="button" data-admin-revoke="${row.id}">Revogar</button>`);
  }
  if (row.can_approve) {
    actions.push(`<button type="button" data-admin-approve="${row.id}">Aprovar</button>`);
  }
  if (row.can_reject) {
    actions.push(`<button type="button" data-admin-reject="${row.id}">Rejeitar</button>`);
  }
  if (row.can_set_password) {
    actions.push(`<button type="button" data-admin-show-password="${row.id}">Cadastrar Senha</button>`);
  }

  tr.innerHTML = `
    <td>${escapeHtml(row.chave)}</td>
    <td>${escapeHtml(row.nome)}</td>
    <td>${escapeHtml(row.status_label)}</td>
    <td>
      <div class="pending-actions">${actions.join("") || "-"}</div>
      <div class="admin-password-editor" id="admin-password-editor-${row.id}">
        <span class="admin-password-label">Nova Senha</span>
        <input class="admin-password-input" id="admin-password-input-${row.id}" type="password" minlength="3" maxlength="20" />
        <button type="button" data-admin-save-password="${row.id}">Salvar</button>
        <button type="button" class="secondary-button" data-admin-cancel-password="${row.id}">Cancelar</button>
      </div>
    </td>
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

  const nome = row.querySelector(".user-nome");
  const chave = row.querySelector(".user-chave");
  const projeto = row.querySelector(".user-projeto");
  const saveButton = row.querySelector(`[data-user-save="${userId}"]`);
  const editButton = row.querySelector(`[data-user-edit="${userId}"]`);

  nome.disabled = !editing;
  chave.disabled = !editing;
  projeto.disabled = !editing;
  saveButton.disabled = !editing;
  editButton.disabled = editing;
  if (editing) {
    nome.focus();
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

async function loadCheckin() {
  const rows = await fetchJson("/api/admin/checkin");
  presenceTableStates.checkin.rawRows = Array.isArray(rows) ? rows : [];
  applyPresenceTableState("checkin");
}

async function loadCheckout() {
  const [rows, missingCheckoutRows] = await Promise.all([
    fetchJson("/api/admin/checkout"),
    fetchJson("/api/admin/missing-checkout"),
  ]);
  presenceTableStates.checkout.rawRows = Array.isArray(rows) ? rows : [];
  presenceTableStates.missingCheckout.rawRows = Array.isArray(missingCheckoutRows) ? missingCheckoutRows : [];
  applyPresenceTableState("checkout");
  applyPresenceTableState("missingCheckout");
}

async function loadInactive() {
  const rows = await fetchJson("/api/admin/inactive");
  presenceTableStates.inactive.rawRows = Array.isArray(rows) ? rows : [];
  applyPresenceTableState("inactive");
}

async function loadPending() {
  const rows = await fetchJson("/api/admin/pending");
  const body = document.getElementById("pendingBody");
  body.innerHTML = "";
  rows.forEach((row) => body.appendChild(makePendingRow(row)));
  applyResponsiveLabels("pendingBody");
}

async function loadAdministrators() {
  const rows = await fetchJson("/api/admin/administrators");
  const body = document.getElementById("administratorsBody");
  body.innerHTML = "";
  rows.forEach((row) => body.appendChild(makeAdministratorRow(row)));
  applyResponsiveLabels("administratorsBody");
}

async function loadRegisteredUsers() {
  const rows = await fetchJson("/api/admin/users");
  registeredUsersTotal = rows.length;
  const body = document.getElementById("usersBody");
  body.innerHTML = "";
  rows.forEach((user) => body.appendChild(makeRegisteredUserRow(user)));
  applyResponsiveLabels("usersBody");
  syncUserTitles();
}

async function loadEvents() {
  const rows = await fetchJson("/api/admin/events");
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
}

async function refreshActiveTab() {
  if (activeTab === "checkin") {
    await loadCheckin();
    return;
  }
  if (activeTab === "checkout") {
    await loadCheckout();
    return;
  }
  if (activeTab === "inactive") {
    await loadInactive();
    return;
  }
  if (activeTab === "cadastro") {
    if (!hasPendingEditInProgress()) {
      await Promise.all([loadPending(), loadAdministrators(), loadRegisteredUsers(), loadLocations()]);
    }
    return;
  }
  await loadEvents();
}

async function refreshAllTables() {
  const jobs = [loadCheckin(), loadCheckout(), loadInactive(), loadEvents(), loadAdministrators()];
  if (!hasPendingEditInProgress()) {
    jobs.push(loadPending());
    jobs.push(loadRegisteredUsers());
    jobs.push(loadLocations());
  }
  await Promise.all(jobs);
}

function startAutoRefresh() {
  stopAutoRefresh();
  autoRefreshHandle = window.setInterval(() => {
    if (document.hidden || realtimeConnected || !isAuthenticated) {
      return;
    }
    refreshAllTables().catch((error) => setStatus(error.message, false));
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
    refreshAllTables().catch((error) => setStatus(error.message, false));
    refreshAllTimer = null;
  }, REALTIME_DEBOUNCE_MS);
}

function startRealtimeUpdates() {
  stopRealtimeUpdates();
  eventStream = new EventSource("/api/admin/stream");
  eventStream.onopen = () => {
    realtimeConnected = true;
  };
  eventStream.onmessage = () => {
    realtimeConnected = true;
    requestRefreshAllTables();
  };
  eventStream.onerror = () => {
    realtimeConnected = false;
  };
}

function stopRealtimeUpdates() {
  if (eventStream) {
    eventStream.close();
    eventStream = null;
  }
  realtimeConnected = false;
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

  if (payload.created && payload.archive) {
    setStatus(`Eventos salvos em ${payload.archive.period} e limpos (${payload.cleared_count} registros).`, true);
    return;
  }
  setStatus("Não havia eventos novos para salvar. Logs já salvos exibidos na janela.", true);
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
  const nome = row.querySelector(".user-nome").value.trim();
  const chave = row.querySelector(".user-chave").value.trim().toUpperCase();
  const projeto = row.querySelector(".user-projeto").value;
  if (!nome || chave.length !== 4) {
    setStatus("Preencha nome e chave de 4 caracteres", false);
    return;
  }
  await postJson("/api/admin/users", { user_id: Number(normalizedUserId), nome, chave, projeto });
  setStatus("Usuário salvo com sucesso", true);
  await loadRegisteredUsers();
}

async function removeRegisteredUser(userId) {
  const normalizedUserId = requireIntegerId(userId, "Usuário");
  await deleteJson(`/api/admin/users/${normalizedUserId}`);
  setStatus("Usuário removido com sucesso", true);
  await Promise.all([loadRegisteredUsers(), loadCheckin(), loadCheckout(), loadInactive()]);
}

async function approveAdministrator(id) {
  const payload = await postJson(`/api/admin/administrators/requests/${id}/approve`);
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
  const chave = document.getElementById("loginChave").value.trim().toUpperCase();
  const senha = document.getElementById("loginSenha").value;
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
  document.getElementById("loginSenha").value = "";
  await bootstrapAdmin();
}

async function submitRequestAdmin() {
  const chave = document.getElementById("requestAdminChave").value.trim().toUpperCase();
  const nomeCompleto = document.getElementById("requestAdminNome").value.trim();
  const senha = document.getElementById("requestAdminSenha").value;
  if (chave.length !== 4 || !/^[A-Z0-9]{4}$/i.test(chave)) {
    document.getElementById("requestAdminStatus").textContent = "A chave deve ter 4 caracteres alfanuméricos.";
    return;
  }
  if (nomeCompleto.length < 3) {
    document.getElementById("requestAdminStatus").textContent = "Informe o nome completo.";
    return;
  }
  if (senha.length < 3 || senha.length > 20) {
    document.getElementById("requestAdminStatus").textContent = "A senha deve ter entre 3 e 20 caracteres.";
    return;
  }

  const payload = await postJson("/api/admin/auth/request-access", {
    chave,
    nome_completo: nomeCompleto,
    senha,
  });
  document.getElementById("requestAdminStatus").textContent = payload.message;
  setAuthStatus(payload.message, "success");
  window.setTimeout(() => {
    closeRequestAdminModal();
    document.getElementById("requestAdminChave").value = "";
    document.getElementById("requestAdminNome").value = "";
    document.getElementById("requestAdminSenha").value = "";
  }, 700);
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

    container.addEventListener("input", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement) || !target.dataset.presenceFilter) {
        return;
      }
      const state = getPresenceTableState(tableKey);
      if (!state) {
        return;
      }
      state.filters[target.dataset.presenceFilter] = target.value;
      applyPresenceTableState(tableKey);
    });

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

  document.querySelector("main").addEventListener("click", (event) => {
    const target = event.target;
    const sortButton = target instanceof Element ? target.closest(".sortable-header") : null;
    if (!sortButton) {
      return;
    }

    const tableKey = sortButton.dataset.sortTable;
    const sortKey = sortButton.dataset.sortKey;
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
  document.getElementById("loginSenha").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      submitLogin().catch((error) => setAuthStatus(error.message, "error"));
    }
  });
  document.getElementById("requestAdminButton").addEventListener("click", openRequestAdminModal);
  document.getElementById("resetPasswordButton").addEventListener("click", () => {
    submitPasswordReset().catch((error) => setAuthStatus(error.message, "error"));
  });
  document.getElementById("logoutButton").addEventListener("click", () => {
    logout().catch((error) => setAuthStatus(error.message, "error"));
  });

  document.getElementById("closeRequestAdmin").addEventListener("click", closeRequestAdminModal);
  document.getElementById("submitRequestAdmin").addEventListener("click", () => {
    submitRequestAdmin().catch((error) => {
      document.getElementById("requestAdminStatus").textContent = error.message;
    });
  });
  document.getElementById("requestAdminModal").addEventListener("click", (event) => {
    if (event.target.id === "requestAdminModal") {
      closeRequestAdminModal();
    }
  });

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
      closeRequestAdminModal();
    }
  });

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
    if (target.tagName === "BUTTON" && target.dataset.userRemove) {
      removeRegisteredUser(target.dataset.userRemove).catch((error) => setStatus(error.message, false));
    }
  });

  document.getElementById("inactiveBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName === "BUTTON" && target.dataset.userRemove) {
      removeRegisteredUser(target.dataset.userRemove).catch((error) => setStatus(error.message, false));
    }
  });

  document.getElementById("missingCheckoutBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName === "BUTTON" && target.dataset.userRemove) {
      removeRegisteredUser(target.dataset.userRemove).catch((error) => setStatus(error.message, false));
    }
  });

  document.getElementById("administratorsBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName !== "BUTTON") {
      return;
    }
    if (target.dataset.adminApprove) {
      approveAdministrator(target.dataset.adminApprove).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.dataset.adminReject) {
      rejectAdministrator(target.dataset.adminReject).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.dataset.adminRevoke) {
      revokeAdministrator(target.dataset.adminRevoke).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.dataset.adminShowPassword) {
      toggleAdminPasswordEditor(target.dataset.adminShowPassword, true);
      return;
    }
    if (target.dataset.adminCancelPassword) {
      toggleAdminPasswordEditor(target.dataset.adminCancelPassword, false);
      return;
    }
    if (target.dataset.adminSavePassword) {
      saveAdministratorPassword(target.dataset.adminSavePassword).catch((error) => setStatus(error.message, false));
    }
  });

  Object.keys(presenceTableStates).forEach((tableKey) => {
    syncPresenceControls(tableKey);
    syncPresenceSortHeaders(tableKey);
  });
}

async function bootstrap() {
  bindActions();
  try {
    await bootstrapAdmin();
  } catch (error) {
    showAuthShell(error.message, "error");
  }
}

bootstrap();
