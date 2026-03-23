const statusLine = document.getElementById("statusLine");
const adminKeyInput = document.getElementById("adminKey");
const DEFAULT_ADMIN_KEY = "change-admin-key";

function resolveAdminKey() {
  const typed = (adminKeyInput.value || "").trim();
  if (typed) {
    return typed;
  }
  const saved = (localStorage.getItem("checking_admin_key") || "").trim();
  if (saved) {
    return saved;
  }
  return DEFAULT_ADMIN_KEY;
}

function adminHeaders() {
  return { "x-admin-key": resolveAdminKey() };
}

function setStatus(message, ok = true) {
  statusLine.textContent = message;
  statusLine.className = ok ? "status-ok" : "status-err";
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
      throw new Error("HTTP 401 - Admin Key ausente/invalida. Preencha a chave e clique em Salvar Chave.");
    }
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

function renderUsers(targetId, rows) {
  const body = document.getElementById(targetId);
  body.innerHTML = "";
  rows.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${r.time}</td><td>${r.nome}</td><td>${r.chave}</td><td>${r.projeto}</td><td>${r.rfid}</td>`;
    body.appendChild(tr);
  });
}

function makePendingRow(r) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${r.rfid}</td>
    <td><input class=\"inline\" id=\"nome-${r.id}\" /></td>
    <td><input class=\"inline\" id=\"chave-${r.id}\" maxlength=\"4\" /></td>
    <td>
      <select class=\"inline\" id=\"projeto-${r.id}\">
        <option value=\"P80\">P80</option>
        <option value=\"P82\">P82</option>
        <option value=\"P83\">P83</option>
      </select>
    </td>
    <td><button data-save=\"${r.id}\" data-rfid=\"${r.rfid}\">Salvar</button></td>
  `;
  return tr;
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
  setStatus("Lista Completa", true);
}

async function loadEvents() {
  const rows = await fetchJson("/api/admin/events");
  const body = document.getElementById("eventsBody");
  body.innerHTML = "";
  rows.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${r.id}</td><td>${r.rfid ?? "-"}</td><td>${r.action}</td><td>${r.status}</td><td>${r.message}</td><td>${r.event_time}</td>`;
    body.appendChild(tr);
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
      setStatus("Admin Key ausente/invalida. Clique em Salvar Chave e tente novamente.", false);
      return;
    }
    setStatus(`Falha ao salvar cadastro: HTTP ${res.status}`, false);
    return;
  }

  setStatus("Cadastro salvo com sucesso", true);
  await loadPending();
}

function bindActions() {
  document.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  document.getElementById("saveKey").addEventListener("click", () => {
    localStorage.setItem("checking_admin_key", adminKeyInput.value.trim());
    setStatus("Admin key salva no navegador", true);
  });

  document.getElementById("refreshCheckin").addEventListener("click", () => loadCheckin().catch((e) => setStatus(e.message, false)));
  document.getElementById("refreshCheckout").addEventListener("click", () => loadCheckout().catch((e) => setStatus(e.message, false)));
  document.getElementById("refreshPending").addEventListener("click", () => loadPending().catch((e) => setStatus(e.message, false)));
  document.getElementById("refreshEvents").addEventListener("click", () => loadEvents().catch((e) => setStatus(e.message, false)));

  document.getElementById("pendingBody").addEventListener("click", (ev) => {
    const t = ev.target;
    if (t.tagName === "BUTTON" && t.dataset.save) {
      savePending(t.dataset.save, t.dataset.rfid).catch((e) => setStatus(e.message, false));
    }
  });
}

async function bootstrap() {
  const bootKey = resolveAdminKey();
  adminKeyInput.value = bootKey;
  localStorage.setItem("checking_admin_key", bootKey);
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
