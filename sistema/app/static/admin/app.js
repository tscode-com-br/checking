const statusLine = document.getElementById("statusLine");
const DEFAULT_ADMIN_KEY = "change-admin-key";

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
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
  document.querySelector(`.tabs button[data-tab=\"${tab}\"]`).classList.add("active");
  document.querySelectorAll(".tab").forEach((el) => el.classList.remove("active"));
  document.getElementById(`tab-${tab}`).classList.add("active");
}

async function fetchJson(url) {
  const res = await fetch(url, { headers: adminHeaders() });
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error("HTTP 401 - Admin Key ausente/invalida.");
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
      tr.innerHTML = `<td>${r.time}</td><td>${r.nome}</td><td>${r.chave}</td><td>${r.projeto}</td><td>${formatLocal(r.local)}</td><td>${r.rfid}</td>`;
    } else {
      tr.innerHTML = `<td>${r.time}</td><td>${r.nome}</td><td>${r.chave}</td><td>${r.projeto}</td><td>${r.rfid}</td>`;
    }
    body.appendChild(tr);
  });
  applyResponsiveLabels(targetId);
}

function formatLocal(local) {
  if (local === "main") {
    return "Escritorio Principal";
  }
  if (local === "co80") {
    return "Escritorio Avancado P80";
  }
  if (local === "un80") {
    return "A bordo da P80";
  }
  if (local === "co83") {
    return "Escritorio Avancado P83";
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

async function loadEvents() {
  const rows = await fetchJson("/api/admin/events");
  const body = document.getElementById("eventsBody");
  body.innerHTML = "";
  rows.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${r.id}</td><td>${r.event_time}</td><td>${r.source}</td><td>${formatAction(r.action)}</td><td>${r.status}</td><td>${r.device_id ?? "-"}</td><td>${formatLocal(r.local)}</td><td>${r.rfid ?? "-"}</td><td>${r.project ?? "-"}</td><td>${r.http_status ?? "-"}</td><td>${r.request_path ?? "-"}</td><td>${r.retry_count ?? 0}</td><td>${r.message}</td><td>${r.details ?? "-"}</td>`;
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
      setStatus("Admin Key ausente/invalida.", false);
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
      setStatus("Admin Key ausente/invalida.", false);
      return;
    }
    if (res.status === 404) {
      setStatus("Pendencia nao encontrada para remocao.", false);
      return;
    }
    setStatus(`Falha ao remover pendencia: HTTP ${res.status}`, false);
    return;
  }

  setStatus("Pendencia removida com sucesso", true);
  await loadPending();
}

function bindActions() {
  document.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  document.getElementById("refreshCheckin").addEventListener("click", () => loadCheckin().catch((e) => setStatus(e.message, false)));
  document.getElementById("refreshCheckout").addEventListener("click", () => loadCheckout().catch((e) => setStatus(e.message, false)));
  document.getElementById("refreshPending").addEventListener("click", () => loadPending().catch((e) => setStatus(e.message, false)));
  document.getElementById("refreshEvents").addEventListener("click", () => loadEvents().catch((e) => setStatus(e.message, false)));

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
}

async function bootstrap() {
  bindActions();
  try {
    await loadPending();
    await loadEvents();
    await loadCheckin();
    await loadCheckout();
    setStatus("Lista Completa", true);
  } catch (err) {
    setStatus(String(err), false);
  }
}

bootstrap();
