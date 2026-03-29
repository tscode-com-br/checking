const statusLine = document.getElementById("statusLine");
const DEFAULT_ADMIN_KEY = "change-admin-key";
const AUTO_REFRESH_MS = 5000;
const REALTIME_DEBOUNCE_MS = 250;
const ARCHIVE_PAGE_SIZE = 8;

let activeTab = "checkin";
let autoRefreshHandle = null;
let realtimeConnected = false;
let refreshAllTimer = null;
let registeredUsersTotal = 0;
let inactiveUsersTotal = 0;
let eventArchives = [];
let eventArchivesFilterQuery = "";
let eventArchivesPage = 1;
let eventArchivesTotal = 0;
let eventArchivesTotalPages = 0;
let eventArchivesTotalSizeBytes = 0;

function adminHeaders() {
  return { "x-admin-key": DEFAULT_ADMIN_KEY };
}

function setStatus(message, ok = true) {
  statusLine.textContent = message;
  statusLine.className = ok ? "status-ok" : "status-err";
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

function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
  document.querySelector(`.tabs button[data-tab=\"${tab}\"]`).classList.add("active");
  document.querySelectorAll(".tab").forEach((el) => el.classList.remove("active"));
  document.getElementById(`tab-${tab}`).classList.add("active");

  refreshActiveTab().catch((e) => setStatus(e.message, false));
}

function hasPendingEditInProgress() {
  return Array.from(document.querySelectorAll("#pendingBody input, #pendingBody select, #usersBody input, #usersBody select")).some((field) => !field.disabled);
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
  if (activeTab === "inativos") {
    await loadInactive();
    return;
  }
  if (activeTab === "cadastro") {
    if (!hasPendingEditInProgress()) {
      await Promise.all([loadPending(), loadRegisteredUsers()]);
    }
    return;
  }
  await loadEvents();
}

async function refreshAllTables() {
  const jobs = [loadCheckin(), loadCheckout(), loadInactive(), loadEvents()];
  if (!hasPendingEditInProgress()) {
    jobs.push(loadPending());
    jobs.push(loadRegisteredUsers());
  }
  await Promise.all(jobs);
}

function startAutoRefresh() {
  if (autoRefreshHandle !== null) {
    clearInterval(autoRefreshHandle);
  }

  autoRefreshHandle = window.setInterval(() => {
    if (document.hidden || realtimeConnected) {
      return;
    }

    refreshAllTables().catch((e) => setStatus(e.message, false));
  }, AUTO_REFRESH_MS);
}

function requestRefreshAllTables() {
  if (refreshAllTimer !== null) {
    window.clearTimeout(refreshAllTimer);
  }

  refreshAllTimer = window.setTimeout(() => {
    refreshAllTables().catch((e) => setStatus(e.message, false));
    refreshAllTimer = null;
  }, REALTIME_DEBOUNCE_MS);
}

function startRealtimeUpdates() {
  const streamUrl = `/api/admin/stream?admin_key=${encodeURIComponent(DEFAULT_ADMIN_KEY)}`;
  const stream = new EventSource(streamUrl);

  stream.onopen = () => {
    realtimeConnected = true;
  };

  stream.onmessage = () => {
    realtimeConnected = true;
    requestRefreshAllTables();
  };

  stream.onerror = () => {
    realtimeConnected = false;
  };

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      requestRefreshAllTables();
    }
  });
}

async function fetchJson(url) {
  const res = await fetch(url, { headers: adminHeaders() });
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error("HTTP 401 - Admin Key ausente/inválida.");
    }
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

function renderUsers(targetId, rows) {
  const body = document.getElementById(targetId);
  const includeLocal = targetId === "checkinBody" || targetId === "checkoutBody";
  body.innerHTML = "";
  rows.forEach((r) => {
    const tr = document.createElement("tr");
    if (includeLocal) {
      tr.innerHTML = `<td>${formatDateTime(r.time)}</td><td>${r.nome}</td><td>${r.chave}</td><td>${r.projeto}</td><td>${formatLocal(r.local)}</td>`;
    } else {
      tr.innerHTML = `<td>${formatDateTime(r.time)}</td><td>${r.nome}</td><td>${r.chave}</td><td>${r.projeto}</td><td>${r.rfid}</td>`;
    }
    body.appendChild(tr);
  });
  applyResponsiveLabels(targetId);
  updateUserTitle(targetId, rows.length, registeredUsersTotal);
}

function updateUserTitle(targetId, totalRows, totalRegistered) {
  if (targetId === "checkinBody") {
    document.getElementById("checkinTitle").textContent = `Usuários em Check-In (${totalRows}/${totalRegistered})`;
    return;
  }

  if (targetId === "checkoutBody") {
    document.getElementById("checkoutTitle").textContent = `Usuários em Check-Out (${totalRows}/${totalRegistered})`;
    return;
  }

  if (targetId === "inactiveBody") {
    document.getElementById("inactiveTitle").textContent = `Inatividade (${totalRows}/${totalRegistered})`;
  }
}

function syncUserTitles() {
  updateUserTitle("checkinBody", document.querySelectorAll("#checkinBody tr").length, registeredUsersTotal);
  updateUserTitle("checkoutBody", document.querySelectorAll("#checkoutBody tr").length, registeredUsersTotal);
  updateUserTitle("inactiveBody", document.querySelectorAll("#inactiveBody tr").length, registeredUsersTotal);
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

function escapeHtml(value) {
  return String(value ?? "-")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function makeEventCell(value) {
  const safeValue = escapeHtml(value ?? "-");
  return `<span class="event-cell">${safeValue}</span>`;
}

function makeEventDetailsButton() {
  return '<button type="button" class="event-details-button">Detalhes</button>';
}

function openEventDetails(details) {
  const modal = document.getElementById("eventDetailsModal");
  const textArea = document.getElementById("eventDetailsText");
  textArea.value = details || "-";
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
  const res = await fetch(url, { headers: adminHeaders() });
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error("HTTP 401 - Admin Key ausente/inválida.");
    }
    if (res.status === 404) {
      throw new Error("Arquivo solicitado não encontrado.");
    }
    throw new Error(`HTTP ${res.status}`);
  }

  const blob = await res.blob();
  return {
    blob,
    fileName: parseDownloadFileName(res.headers.get("Content-Disposition"), fallbackName),
  };
}

async function deleteJson(url) {
  const res = await fetch(url, { method: "DELETE", headers: adminHeaders() });
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error("HTTP 401 - Admin Key ausente/inválida.");
    }
    if (res.status === 404) {
      throw new Error("Arquivo solicitado não encontrado.");
    }
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
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
  if (eventArchivesFilterQuery.trim()) {
    summary.textContent = `${eventArchives.length} de ${eventArchivesTotal} logs`;
  } else {
    summary.textContent = `${eventArchivesTotal} logs`;
  }

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

  const res = await fetch("/api/admin/events/archive", {
    method: "POST",
    headers: adminHeaders(),
  });

  if (!res.ok) {
    if (res.status === 401) {
      throw new Error("HTTP 401 - Admin Key ausente/inválida.");
    }
    throw new Error(`HTTP ${res.status}`);
  }

  const payload = await res.json();
  eventArchivesPage = 1;
  renderEventArchives(payload.archives || []);
  openEventArchivesModal();
  await loadEvents();

  if (payload.created && payload.archive) {
    setStatus(`Eventos salvos em ${payload.archive.period} e limpos (${payload.cleared_count} registros).`, true);
    return;
  }

  setStatus("Não havia eventos novos para salvar. Logs já salvos exibidos na janela.", true);
}

function makePendingRow(r) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${r.rfid}</td>
    <td><input class=\"inline\" id=\"nome-${r.id}\" disabled /></td>
    <td><input class=\"inline\" id=\"chave-${r.id}\" maxlength=\"4\" disabled /></td>
    <td>
      <select class=\"inline\" id=\"projeto-${r.id}\" disabled>
        <option value=\"P80\">P80</option>
        <option value=\"P83\">P83</option>
      </select>
    </td>
    <td class=\"pending-actions\">
      <button data-edit=\"${r.id}\">Editar</button>
      <button data-remove=\"${r.id}\">Remover</button>
      <button data-save=\"${r.id}\" data-rfid=\"${r.rfid}\" disabled>Salvar</button>
    </td>
  `;
  return tr;
}

function makeRegisteredUserRow(user) {
  const tr = document.createElement("tr");
  tr.dataset.rfid = user.rfid;
  tr.innerHTML = `
    <td>${escapeHtml(user.rfid)}</td>
    <td><input class="inline user-nome" value="${user.nome}" disabled /></td>
    <td><input class="inline user-chave" maxlength="4" value="${user.chave}" disabled /></td>
    <td>
      <select class="inline user-projeto" disabled>
        <option value="P80">P80</option>
        <option value="P83">P83</option>
      </select>
    </td>
    <td class="pending-actions">
      <button data-user-edit="${user.rfid}">Editar</button>
      <button data-user-save="${user.rfid}" disabled>Salvar</button>
      <button data-user-remove="${user.rfid}">Remover</button>
    </td>
  `;
  tr.querySelector(".user-projeto").value = user.projeto;
  return tr;
}

function formatInactivity(days) {
  const value = Number(days || 0);
  return value === 1 ? "1 dia" : `${value} dias`;
}

function makeInactiveUserRow(user) {
  const tr = document.createElement("tr");
  tr.dataset.rfid = user.rfid;
  tr.innerHTML = `
    <td>${escapeHtml(user.nome)}</td>
    <td>${escapeHtml(user.chave)}</td>
    <td>${escapeHtml(user.projeto)}</td>
    <td>${escapeHtml(formatInactivity(user.inactivity_days))}</td>
    <td class="pending-actions"><button type="button" data-inactive-remove="${escapeHtml(user.rfid)}">Remover</button></td>
  `;
  return tr;
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

function setRegisteredUserEditingState(rfid, editing) {
  const row = document.querySelector(`#usersBody tr[data-rfid="${CSS.escape(rfid)}"]`);
  if (!row) {
    return;
  }

  const nome = row.querySelector(".user-nome");
  const chave = row.querySelector(".user-chave");
  const projeto = row.querySelector(".user-projeto");
  const saveButton = row.querySelector(`[data-user-save="${rfid}"]`);
  const editButton = row.querySelector(`[data-user-edit="${rfid}"]`);

  nome.disabled = !editing;
  chave.disabled = !editing;
  projeto.disabled = !editing;
  saveButton.disabled = !editing;
  editButton.disabled = editing;

  if (editing) {
    nome.focus();
  }
}

async function loadCheckin() {
  const rows = await fetchJson("/api/admin/checkin");
  renderUsers("checkinBody", rows);
  setStatus("Lista Completa", true);
}

async function loadCheckout() {
  const rows = await fetchJson("/api/admin/checkout");
  renderUsers("checkoutBody", rows);
  setStatus("Lista Completa", true);
}

async function loadPending() {
  const rows = await fetchJson("/api/admin/pending");
  const body = document.getElementById("pendingBody");
  body.innerHTML = "";
  rows.forEach((r) => body.appendChild(makePendingRow(r)));
  applyResponsiveLabels("pendingBody");
  setStatus("Lista Completa", true);
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

async function loadInactive() {
  const rows = await fetchJson("/api/admin/inactive");
  inactiveUsersTotal = rows.length;
  const body = document.getElementById("inactiveBody");
  body.innerHTML = "";
  rows.forEach((user) => body.appendChild(makeInactiveUserRow(user)));
  applyResponsiveLabels("inactiveBody");
  updateUserTitle("inactiveBody", inactiveUsersTotal, registeredUsersTotal);
}

async function loadEvents() {
  const rows = await fetchJson("/api/admin/events");
  const body = document.getElementById("eventsBody");
  body.innerHTML = "";
  rows.forEach((r) => {
    const tr = document.createElement("tr");
    const formattedDetails = formatEventDetails(r.details);
    tr.innerHTML = `<td>${makeEventCell(r.id)}</td><td>${makeEventCell(formatDateTime(r.event_time))}</td><td>${makeEventCell(r.source)}</td><td>${makeEventCell(formatAction(r.action))}</td><td>${makeEventCell(r.status)}</td><td>${makeEventCell(r.device_id ?? "-")}</td><td>${makeEventCell(formatLocal(r.local))}</td><td>${makeEventCell(r.rfid ?? "-")}</td><td>${makeEventCell(r.project ?? "-")}</td><td>${makeEventCell(r.http_status ?? "-")}</td><td>${makeEventCell(r.request_path ?? "-")}</td><td>${makeEventCell(r.retry_count ?? 0)}</td><td>${makeEventCell(r.message)}</td><td>${makeEventDetailsButton()}</td>`;
    const detailsButton = tr.querySelector(".event-details-button");
    detailsButton.addEventListener("click", () => openEventDetails(formattedDetails));
    body.appendChild(tr);
  });
  applyResponsiveLabels("eventsBody");
}

async function savePending(id, rfid) {
  const nome = document.getElementById(`nome-${id}`).value.trim();
  const chave = document.getElementById(`chave-${id}`).value.trim().toUpperCase();
  const projeto = document.getElementById(`projeto-${id}`).value;

  if (!nome || chave.length !== 4) {
    setStatus("Preencha nome e chave de 4 caracteres", false);
    return;
  }

  const res = await fetch("/api/admin/users", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...adminHeaders(),
    },
    body: JSON.stringify({ rfid, nome, chave, projeto }),
  });

  if (!res.ok) {
    if (res.status === 401) {
      setStatus("Admin Key ausente/inválida.", false);
      return;
    }
    setStatus(`Falha ao salvar cadastro: HTTP ${res.status}`, false);
    return;
  }

  setStatus("Cadastro salvo com sucesso", true);
  await loadPending();
}

async function removePending(id) {
  const res = await fetch(`/api/admin/pending/${id}`, {
    method: "DELETE",
    headers: adminHeaders(),
  });

  if (!res.ok) {
    if (res.status === 401) {
      setStatus("Admin Key ausente/inválida.", false);
      return;
    }
    if (res.status === 404) {
      setStatus("Pendência não encontrada para remoção.", false);
      return;
    }
    setStatus(`Falha ao remover pendência: HTTP ${res.status}`, false);
    return;
  }

  setStatus("Pendência removida com sucesso", true);
  await loadPending();
}

async function saveRegisteredUser(rfid) {
  const row = document.querySelector(`#usersBody tr[data-rfid="${CSS.escape(rfid)}"]`);
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

  const res = await fetch("/api/admin/users", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...adminHeaders(),
    },
    body: JSON.stringify({ rfid, nome, chave, projeto }),
  });

  if (!res.ok) {
    if (res.status === 401) {
      setStatus("Admin Key ausente/inválida.", false);
      return;
    }
    setStatus(`Falha ao salvar usuário: HTTP ${res.status}`, false);
    return;
  }

  setStatus("Usuário salvo com sucesso", true);
  await loadRegisteredUsers();
}

async function removeRegisteredUser(rfid) {
  const res = await fetch(`/api/admin/users/${encodeURIComponent(rfid)}`, {
    method: "DELETE",
    headers: adminHeaders(),
  });

  if (!res.ok) {
    if (res.status === 401) {
      setStatus("Admin Key ausente/inválida.", false);
      return;
    }
    if (res.status === 404) {
      setStatus("Usuário não encontrado para remoção.", false);
      return;
    }
    setStatus(`Falha ao remover usuário: HTTP ${res.status}`, false);
    return;
  }

  setStatus("Usuário removido com sucesso", true);
  await loadRegisteredUsers();
}

function bindActions() {
  document.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  document.getElementById("clearEvents").addEventListener("click", () => {
    archiveAndClearEvents().catch((e) => setStatus(e.message, false));
  });
  document.getElementById("closeEventDetails").addEventListener("click", closeEventDetails);
  document.getElementById("closeEventArchives").addEventListener("click", closeEventArchivesModal);
  document.getElementById("closeEventArchivesFooter").addEventListener("click", closeEventArchivesModal);
  document.getElementById("downloadAllEventArchives").addEventListener("click", () => {
    downloadAllEventArchives().catch((e) => setStatus(e.message, false));
  });
  document.getElementById("eventArchivesFilter").addEventListener("input", (ev) => {
    eventArchivesFilterQuery = ev.target.value || "";
    eventArchivesPage = 1;
    loadEventArchives().catch((e) => setStatus(e.message, false));
  });
  document.getElementById("eventArchivesPrev").addEventListener("click", () => {
    if (eventArchivesPage > 1) {
      eventArchivesPage -= 1;
      loadEventArchives().catch((e) => setStatus(e.message, false));
    }
  });
  document.getElementById("eventArchivesNext").addEventListener("click", () => {
    if (eventArchivesPage < eventArchivesTotalPages) {
      eventArchivesPage += 1;
      loadEventArchives().catch((e) => setStatus(e.message, false));
    }
  });
  document.getElementById("eventDetailsModal").addEventListener("click", (ev) => {
    if (ev.target.id === "eventDetailsModal") {
      closeEventDetails();
    }
  });
  document.getElementById("eventArchivesModal").addEventListener("click", (ev) => {
    if (ev.target.id === "eventArchivesModal") {
      closeEventArchivesModal();
    }
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") {
      closeEventDetails();
      closeEventArchivesModal();
    }
  });
  document.getElementById("eventArchivesBody").addEventListener("click", (ev) => {
    const target = ev.target;
    if (target.tagName === "BUTTON" && target.dataset.archiveDownload) {
      downloadEventArchive(target.dataset.archiveDownload).catch((e) => setStatus(e.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.archiveDelete) {
      const fileName = target.dataset.archiveDelete;
      const confirmed = window.confirm(`Deseja excluir permanentemente o arquivo ${fileName}?`);
      if (!confirmed) {
        return;
      }
      deleteEventArchive(fileName).catch((e) => setStatus(e.message, false));
    }
  });

  document.getElementById("pendingBody").addEventListener("click", (ev) => {
    const t = ev.target;
    if (t.tagName === "BUTTON" && t.dataset.edit) {
      setPendingEditingState(t.dataset.edit, true);
      return;
    }
    if (t.tagName === "BUTTON" && t.dataset.remove) {
      removePending(t.dataset.remove).catch((e) => setStatus(e.message, false));
      return;
    }
    if (t.tagName === "BUTTON" && t.dataset.save) {
      savePending(t.dataset.save, t.dataset.rfid).catch((e) => setStatus(e.message, false));
    }
  });

  document.getElementById("usersBody").addEventListener("click", (ev) => {
    const t = ev.target;
    if (t.tagName === "BUTTON" && t.dataset.userEdit) {
      setRegisteredUserEditingState(t.dataset.userEdit, true);
      return;
    }
    if (t.tagName === "BUTTON" && t.dataset.userSave) {
      saveRegisteredUser(t.dataset.userSave).catch((e) => setStatus(e.message, false));
      return;
    }
    if (t.tagName === "BUTTON" && t.dataset.userRemove) {
      removeRegisteredUser(t.dataset.userRemove).catch((e) => setStatus(e.message, false));
    }
  });

  document.getElementById("inactiveBody").addEventListener("click", (ev) => {
    const t = ev.target;
    if (t.tagName === "BUTTON" && t.dataset.inactiveRemove) {
      removeRegisteredUser(t.dataset.inactiveRemove).catch((e) => setStatus(e.message, false));
    }
  });
}

async function bootstrap() {
  bindActions();
  startAutoRefresh();
  startRealtimeUpdates();
  try {
    await refreshAllTables();
    setStatus("Lista Completa", true);
  } catch (err) {
    setStatus(String(err), false);
  }
}

bootstrap();
