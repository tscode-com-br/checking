#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");
const spaRoot = path.join(workspaceRoot, "sistema", "app", "static", "check");
const spaIndexPath = path.join(spaRoot, "index.html");
const outputRoot = path.join(workspaceRoot, "docs", "temp_006_homologation");
const screenshotRoot = path.join(outputRoot, "screenshots");
const manifestPath = path.join(outputRoot, "manifest.json");
const readmePath = path.join(outputRoot, "README.md");
const chromePath = findChrome();

const mobileUserAgent = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36";
const desktopUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

const scenarios = [
  {
    id: "01-portrait-mobile-main",
    title: "Retrato mobile com shell principal preenchida",
    viewport: { width: 412, height: 915 },
    layout: "mobile",
    scenario: "filled-main",
  },
  {
    id: "02-landscape-mobile-main",
    title: "Paisagem mobile com shell principal preenchida",
    viewport: { width: 915, height: 412 },
    layout: "mobile",
    scenario: "filled-main",
  },
  {
    id: "03-landscape-mobile-auth-focus-proxy-keyboard",
    title: "Paisagem mobile com foco em autenticacao e viewport reduzido como proxy de teclado aberto",
    viewport: { width: 915, height: 300 },
    layout: "mobile",
    scenario: "auth-focus-proxy-keyboard",
    note: "Proxy de teclado aberto: viewport reduzido em headless com foco no campo de senha.",
  },
  {
    id: "04-tablet-landscape-main",
    title: "Viewport intermediaria em paisagem",
    viewport: { width: 1024, height: 768 },
    layout: "mobile",
    scenario: "filled-main",
  },
  {
    id: "05-notebook-main",
    title: "Notebook comum com shell principal preenchida",
    viewport: { width: 1366, height: 768 },
    layout: "desktop",
    scenario: "filled-main",
  },
  {
    id: "06-desktop-wide-main",
    title: "Desktop amplo com shell principal preenchida",
    viewport: { width: 1600, height: 900 },
    layout: "desktop",
    scenario: "filled-main",
  },
  {
    id: "07-notebook-password-dialog",
    title: "Dialog de senha em notebook",
    viewport: { width: 1366, height: 768 },
    layout: "desktop",
    scenario: "password-dialog",
  },
  {
    id: "08-notebook-registration-dialog",
    title: "Dialog de cadastro em notebook",
    viewport: { width: 1366, height: 768 },
    layout: "desktop",
    scenario: "registration-dialog",
  },
  {
    id: "09-notebook-transport-screen",
    title: "Tela de transporte em notebook",
    viewport: { width: 1366, height: 768 },
    layout: "desktop",
    scenario: "transport-screen",
  },
  {
    id: "10-notebook-transport-detail",
    title: "Detalhe de solicitacao de transporte em notebook",
    viewport: { width: 1366, height: 768 },
    layout: "desktop",
    scenario: "transport-detail",
  },
];

function findChrome() {
  const configured = process.env.CHECKING_CHROME_PATH;
  const candidates = [
    configured,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);

  const found = candidates.find((candidate) => existsSync(candidate));
  if (!found) {
    throw new Error("Chrome or Edge was not found. Set CHECKING_CHROME_PATH to a Chromium executable.");
  }
  return found;
}

function contentTypeFor(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".html") return "text/html; charset=utf-8";
  if (ext === ".css") return "text/css; charset=utf-8";
  if (ext === ".js") return "text/javascript; charset=utf-8";
  if (ext === ".json") return "application/json; charset=utf-8";
  if (ext === ".png") return "image/png";
  if (ext === ".svg") return "image/svg+xml";
  if (ext === ".ico") return "image/x-icon";
  return "application/octet-stream";
}

async function serveStatic(requestPath, response) {
  const decodedPath = decodeURIComponent(requestPath.split("?")[0]);
  const relativePath = decodedPath.replace(/^\/+/, "");
  const candidatePath = path.normalize(path.join(workspaceRoot, relativePath));
  if (!candidatePath.startsWith(workspaceRoot) || !existsSync(candidatePath)) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Not found");
    return;
  }

  const data = await fs.readFile(candidatePath);
  response.writeHead(200, {
    "Content-Type": contentTypeFor(candidatePath),
    "Cache-Control": "no-store",
  });
  response.end(data);
}

async function buildScenarioHtml(scenarioId) {
  const originalHtml = await fs.readFile(spaIndexPath, "utf8");
  const htmlWithCaptureBase = originalHtml.replace(
    '<base href="./user/" />',
    '<base href="/sistema/app/static/check/" />',
  );
  const preScript = `<script>${buildPreloadScript(scenarioId)}</script>`;
  const postScript = `<script>${buildScenarioScript(scenarioId)}</script>`;
  return htmlWithCaptureBase.replace(
    '<script src="automatic-activities.js"></script>',
    `${preScript}\n    <script src="automatic-activities.js"></script>`,
  ).replace("</body>", `    ${postScript}\n  </body>`);
}

function buildPreloadScript(scenarioId) {
  return `
(() => {
  window.__CHECKING_TEMP006_SCENARIO__ = ${JSON.stringify(scenarioId)};
  try { window.localStorage.clear(); } catch (_error) {}

  const today = "2026-04-25";
  const projectRows = [{ name: "BRAVO" }, { name: "ALFA" }, { name: "CHARLIE" }];
  const locations = { items: ["Base Petrobras", "Oficina Central", "Zona de CheckOut"] };
  const history = {
    found: true,
    chave: "HR70",
    projeto: "BRAVO",
    current_action: "checkin",
    current_local: "Base Petrobras",
    has_current_day_checkin: true,
    last_checkin_at: "2026-04-25T08:12:00+08:00",
    last_checkout_at: "2026-04-24T17:44:00+08:00"
  };

  const transportState = {
    chave: "HR70",
    end_rua: "Blk 10 Tanjong Pagar Road, #05-01",
    zip: "088445",
    status: "confirmed",
    request_id: 902,
    request_kind: "regular",
    route_kind: "work_to_home",
    service_date: today,
    requested_time: "18:00",
    boarding_time: "18:20",
    confirmation_deadline_time: "17:40",
    vehicle_type: "van",
    vehicle_plate: "SGX-2048",
    vehicle_color: "Prata",
    tolerance_minutes: 10,
    awareness_required: false,
    awareness_confirmed: false,
    requests: [
      {
        request_id: 902,
        request_kind: "regular",
        status: "confirmed",
        is_active: true,
        service_date: today,
        requested_time: "18:00",
        selected_weekdays: [0, 1, 2, 3, 4],
        route_kind: "work_to_home",
        boarding_time: "18:20",
        confirmation_deadline_time: "17:40",
        vehicle_type: "van",
        vehicle_plate: "SGX-2048",
        vehicle_color: "Prata",
        tolerance_minutes: 10,
        awareness_required: false,
        awareness_confirmed: false,
        response_message: "",
        created_at: "2026-04-25T07:50:00+08:00"
      }
    ]
  };

  function json(payload, status = 200) {
    return new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" }
    });
  }

  window.fetch = async (input) => {
    const url = new URL(String(input), window.location.href);
    if (url.pathname === "/api/web/projects") return json(projectRows);
    if (url.pathname === "/api/web/check/locations") return json(locations);
    if (url.pathname === "/api/web/check/state") return json(history);
    if (url.pathname === "/api/web/check/location") {
      return json({
        matched: true,
        resolved_local: "Base Petrobras",
        label: "Base Petrobras",
        status: "matched",
        message: "Localização identificada em Base Petrobras.",
        accuracy_meters: 18,
        accuracy_threshold_meters: 50,
        minimum_checkout_distance_meters: 500,
        nearest_workplace_distance_meters: 0
      });
    }
    if (url.pathname === "/api/web/project") return json({ ok: true, project: "BRAVO", message: "Projeto atualizado com sucesso." });
    if (url.pathname === "/api/web/check") return json({ ok: true, message: "Check-In concluído.", state: history });
    if (url.pathname === "/api/web/transport/state") return json(transportState);
    if (url.pathname === "/api/web/transport/address") return json({ ok: true, message: "Endereço cadastrado.", state: transportState });
    if (url.pathname === "/api/web/transport/vehicle-request" || url.pathname === "/api/web/transport/request") {
      return json({ ok: true, message: "Solicitação registrada.", state: transportState });
    }
    if (url.pathname === "/api/web/transport/cancel") return json({ ok: true, message: "Solicitação de transporte cancelada.", state: transportState });
    if (url.pathname === "/api/web/transport/acknowledge") return json({ ok: true, message: "Ciência registrada com sucesso.", state: transportState });
    if (url.pathname === "/api/web/auth/logout") return json({ ok: true });
    if (url.pathname === "/api/web/auth/login") return json({ ok: true, authenticated: true, has_password: true, message: "Usuário autenticado." });
    if (url.pathname === "/api/web/auth/register-password") return json({ ok: true, authenticated: true, has_password: true, message: "Senha cadastrada." });
    if (url.pathname === "/api/web/auth/register-user") return json({ ok: true, authenticated: true, has_password: true, message: "Cadastro concluído com sucesso." });
    if (url.pathname === "/api/web/auth/change-password") return json({ ok: true, authenticated: true, has_password: true, message: "Senha alterada." });
    if (url.pathname === "/api/web/auth/status") {
      const chave = (url.searchParams.get("chave") || "").toUpperCase();
      if (chave === "NOPE") return json({ chave, found: false, has_password: false, authenticated: false, message: "Chave não encontrada. Solicite cadastro." });
      return json({ chave, found: true, has_password: true, authenticated: false, message: "Digite sua senha para iniciar." });
    }
    return json({});
  };

  window.EventSource = class {
    constructor() {}
    close() {}
  };

  navigator.permissions = {
    query: async () => ({ state: "granted", onchange: null })
  };
  navigator.geolocation = {
    getCurrentPosition: (success) => {
      window.setTimeout(() => {
        success({
          coords: {
            latitude: 1.2762,
            longitude: 103.8501,
            accuracy: 18
          },
          timestamp: Date.now()
        });
      }, 10);
    }
  };
})();
`;
}

function buildScenarioScript(scenarioId) {
  return `
(() => {
  const scenarioId = ${JSON.stringify(scenarioId)};

  function byId(id) {
    return document.getElementById(id);
  }

  function show(element) {
    if (!element) return;
    element.hidden = false;
    element.classList.remove("is-hidden");
    element.setAttribute("aria-hidden", "false");
  }

  function hide(element) {
    if (!element) return;
    element.hidden = true;
    element.classList.add("is-hidden");
    element.setAttribute("aria-hidden", "true");
  }

  function visibleField(element, visible) {
    if (!element) return;
    element.classList.toggle("is-hidden", !visible);
    element.setAttribute("aria-hidden", String(!visible));
  }

  function setOptions(selectId, values, selectedValue) {
    const select = byId(selectId);
    if (!select) return;
    select.replaceChildren();
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
    select.value = selectedValue || values[0] || "";
  }

  function setNotification(primary, secondary, tone) {
    [["notificationLinePrimary", primary], ["notificationLineSecondary", secondary]].forEach(([id, text]) => {
      const line = byId(id);
      if (!line) return;
      line.textContent = text || "";
      line.classList.remove("is-success", "is-error", "is-warning", "is-info", "is-neutral");
      if (tone) line.classList.add("is-" + tone);
    });
  }

  function setLocation(label, accuracy, tone) {
    const value = byId("locationValue");
    const accuracyElement = byId("locationAccuracy");
    if (value) {
      value.textContent = label;
      value.classList.remove("is-error", "is-success", "is-warning", "is-info", "is-muted");
      if (tone) value.classList.add("is-" + tone);
    }
    if (accuracyElement) accuracyElement.textContent = accuracy || "--";
  }

  function setHistory(checkin, checkout, latest) {
    function render(id, parts) {
      const element = byId(id);
      if (!element) return;
      element.replaceChildren();
      if (!parts) {
        element.textContent = "--";
        return;
      }
      [["history-weekday", parts[0]], ["history-date", parts[1]], ["history-time", parts[2]]].forEach(([className, text]) => {
        const span = document.createElement("span");
        span.className = className;
        span.textContent = text;
        element.appendChild(span);
      });
    }
    render("lastCheckinValue", checkin);
    render("lastCheckoutValue", checkout);
    const checkinItem = byId("lastCheckinValue")?.closest(".history-item");
    const checkoutItem = byId("lastCheckoutValue")?.closest(".history-item");
    checkinItem?.classList.toggle("is-latest-activity", latest === "checkin");
    checkoutItem?.classList.toggle("is-latest-activity", latest === "checkout");
  }

  function unlockMain(options = {}) {
    byId("chaveInput").value = options.chave || "HR70";
    byId("passwordInput").value = options.password || "1234";
    byId("passwordActionButton").textContent = "Alterar";
    byId("requestRegistrationButton").hidden = true;
    byId("requestRegistrationButton").setAttribute("aria-hidden", "true");
    document.querySelectorAll(".auth-field").forEach((field) => {
      field.classList.remove("auth-field-pending");
      field.classList.add("auth-field-authenticated");
    });
    document.querySelectorAll(".check-form input, .check-form select, .check-form button").forEach((control) => {
      control.disabled = false;
      control.removeAttribute("aria-disabled");
    });
    setOptions("projectSelect", ["BRAVO", "ALFA", "CHARLIE"], "BRAVO");
    setOptions("registrationProjectSelect", ["BRAVO", "ALFA", "CHARLIE"], "BRAVO");
    setOptions("manualLocationSelect", ["Base Petrobras", "Oficina Central", "Zona de CheckOut"], "Base Petrobras");
    setHistory(["sábado", "25/04/2026", "08:12:00"], ["sexta-feira", "24/04/2026", "17:44:00"], "checkin");
    setNotification("Aplicação atualizada com sucesso.", "Layout homologado localmente para a Fase 6.", "success");
    setLocation("Base Petrobras", "Precisão 18 m / Limite 50 m", "success");
    visibleField(byId("automaticActivitiesField"), options.showAutomatic !== false);
    byId("automaticActivitiesToggle").checked = Boolean(options.automaticEnabled);
    visibleField(byId("projectField"), options.projectVisible !== false);
    visibleField(byId("locationSelectField"), options.locationVisible !== false);
    visibleField(byId("informeField"), options.informeVisible !== false);
  }

  function setKeyStateNotFound() {
    byId("chaveInput").value = "NOPE";
    byId("passwordInput").value = "";
    byId("requestRegistrationButton").hidden = false;
    byId("requestRegistrationButton").setAttribute("aria-hidden", "false");
    document.querySelectorAll(".auth-field").forEach((field) => field.classList.remove("auth-field-authenticated", "auth-field-pending"));
    byId("passwordActionButton").textContent = "Chave?";
    byId("passwordActionButton").classList.add("is-attention");
    byId("chaveInput").closest(".auth-field")?.classList.add("auth-field-pending");
    setNotification("Chave não encontrada.", "Solicite cadastro.", "warning");
  }

  function showPasswordDialog() {
    unlockMain();
    show(byId("passwordDialogBackdrop"));
    show(byId("passwordDialog"));
    byId("passwordDialogTitle").textContent = "Alterar Senha";
    byId("oldPasswordInput").value = "1234";
    byId("newPasswordInput").value = "nova";
    byId("confirmPasswordInput").value = "nova";
  }

  function showRegistrationDialog() {
    setKeyStateNotFound();
    show(byId("registrationDialogBackdrop"));
    show(byId("registrationDialog"));
    byId("registrationChaveInput").value = "NOPE";
    byId("registrationNameInput").value = "Usuário Baseline";
    byId("registrationEmailInput").value = "usuario@example.com";
    byId("registrationPasswordInput").value = "1234";
    byId("registrationConfirmPasswordInput").value = "1234";
    setOptions("registrationProjectSelect", ["BRAVO", "ALFA", "CHARLIE"], "BRAVO");
  }

  function requestCard() {
    const card = document.createElement("div");
    card.className = "transport-request-card is-confirmed is-selected";
    card.dataset.requestId = "902";
    card.setAttribute("role", "button");
    card.setAttribute("aria-haspopup", "dialog");
    card.setAttribute("aria-controls", "transportRequestDetailWidget");
    card.setAttribute("aria-disabled", "false");
    card.setAttribute("aria-pressed", "true");
    card.tabIndex = 0;

    const header = document.createElement("span");
    header.className = "transport-request-card-header";
    const title = document.createElement("span");
    title.className = "transport-request-card-title";
    title.textContent = "Transporte Rotineiro";
    const statusLabel = document.createElement("span");
    statusLabel.className = "transport-request-card-status is-confirmed";
    statusLabel.textContent = "Confirmado";
    header.append(title, statusLabel);

    const meta = document.createElement("div");
    meta.className = "transport-request-card-meta";
    const dateTime = document.createElement("span");
    dateTime.className = "transport-request-card-date-time";
    dateTime.textContent = "25/04/2026 18:20";
    meta.appendChild(dateTime);

    const actionWrap = document.createElement("div");
    actionWrap.className = "transport-request-card-actions";
    const realized = document.createElement("button");
    realized.type = "button";
    realized.className = "transport-request-card-realized-button";
    realized.textContent = "Realizado";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "transport-request-card-cancel-button";
    cancel.textContent = "Cancelar";
    actionWrap.append(realized, cancel);
    meta.appendChild(actionWrap);

    card.append(header, meta);
    return card;
  }

  function showTransportBase() {
    unlockMain({ showAutomatic: true });
    show(byId("transportScreenBackdrop"));
    show(byId("transportScreen"));
    byId("transportAddressSummaryValue").textContent = "Blk 10 Tanjong Pagar Road, #05-01\\nZIP 088445";
    hide(byId("transportAddressEditor"));
    show(byId("transportOptionButtons"));
    hide(byId("transportRequestBuilderPanel"));
    hide(byId("transportRequestHistorySection"));
    hide(byId("transportAcknowledgementSection"));
    hide(byId("transportRequestDetailWidget"));
    byId("transportInlineStatus").textContent = "";
    byId("transportInlineStatus").className = "transport-inline-status";
  }

  function showTransportDetailWidget() {
    showTransportBase();
    hide(byId("transportOptionButtons"));
    show(byId("transportRequestHistorySection"));
    const list = byId("transportRequestHistoryList");
    list.replaceChildren(requestCard());
    show(byId("transportRequestDetailWidget"));
    byId("transportRequestDetailWidgetTitle").textContent = "Transporte Rotineiro";
    const content = byId("transportRequestDetailContent");
    content.replaceChildren();
    const copy = document.createElement("div");
    copy.className = "transport-request-detail-copy";
    const msg = document.createElement("p");
    msg.className = "transport-request-detail-message";
    msg.textContent = "Transporte confirmado.";
    const fields = document.createElement("div");
    fields.className = "transport-request-detail-fields";
    [["Tipo de Veículo", "Van"], ["Placa do Veículo", "SGX-2048"], ["Cor do Veículo", "Prata"], ["Data de Partida", "25/04/2026"], ["Hora de Partida", "18:20"]].forEach(([label, value]) => {
      const field = document.createElement("div");
      field.className = "transport-request-detail-field";
      const labelEl = document.createElement("span");
      labelEl.className = "transport-request-detail-field-label";
      labelEl.textContent = label;
      const valueEl = document.createElement("span");
      valueEl.className = "transport-request-detail-field-value";
      valueEl.textContent = value;
      field.append(labelEl, valueEl);
      fields.appendChild(field);
    });
    copy.append(msg, fields);
    content.appendChild(copy);
  }

  function applyScenario() {
    setOptions("projectSelect", ["BRAVO", "ALFA", "CHARLIE"], "BRAVO");
    setOptions("registrationProjectSelect", ["BRAVO", "ALFA", "CHARLIE"], "BRAVO");
    setOptions("manualLocationSelect", ["Base Petrobras", "Oficina Central", "Zona de CheckOut"], "Base Petrobras");

    if (scenarioId === "password-dialog") {
      showPasswordDialog();
    } else if (scenarioId === "registration-dialog") {
      showRegistrationDialog();
    } else if (scenarioId === "transport-screen") {
      showTransportBase();
    } else if (scenarioId === "transport-detail") {
      showTransportDetailWidget();
    } else {
      unlockMain({ showAutomatic: true, automaticEnabled: false, locationVisible: false });
      if (scenarioId === "auth-focus-proxy-keyboard") {
        const passwordInput = byId("passwordInput");
        if (passwordInput) {
          passwordInput.focus({ preventScroll: false });
          passwordInput.setSelectionRange(passwordInput.value.length, passwordInput.value.length);
          passwordInput.scrollIntoView({ block: "center", inline: "nearest" });
        }
        setNotification("Aplicação atualizada com sucesso.", "Viewport reduzido e foco na senha como proxy de teclado aberto.", "info");
      }
    }

    window.__CHECKING_TEMP006_READY__ = true;
  }

  if (document.readyState === "complete") {
    window.setTimeout(applyScenario, 350);
  } else {
    window.addEventListener("load", () => window.setTimeout(applyScenario, 350), { once: true });
  }
})();
`;
}

async function startServer() {
  const server = http.createServer(async (request, response) => {
    try {
      const requestUrl = new URL(request.url, "http://127.0.0.1");
      if (requestUrl.pathname.startsWith("/__temp006/")) {
        const scenarioId = requestUrl.pathname.split("/").pop();
        const html = await buildScenarioHtml(scenarioId);
        response.writeHead(200, {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "no-store",
        });
        response.end(html);
        return;
      }
      await serveStatic(requestUrl.pathname, response);
    } catch (error) {
      response.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
      response.end(error instanceof Error ? error.stack : String(error));
    }
  });

  await new Promise((resolve) => {
    server.listen(0, "127.0.0.1", resolve);
  });
  return server;
}

async function screenshotScenario(server, scenario) {
  const address = server.address();
  const url = `http://127.0.0.1:${address.port}/__temp006/${scenario.scenario}`;
  const outputPath = path.join(screenshotRoot, `${scenario.id}.png`);
  await captureWithChromeDevTools({
    url,
    outputPath,
    viewport: scenario.viewport,
    mobile: scenario.layout === "mobile",
    userAgent: scenario.layout === "mobile" ? mobileUserAgent : desktopUserAgent,
  });
  const buffer = await fs.readFile(outputPath);
  return {
    id: scenario.id,
    title: scenario.title,
    file: path.relative(workspaceRoot, outputPath).replaceAll("\\", "/"),
    viewport: scenario.viewport,
    layout: scenario.layout,
    note: scenario.note || null,
    sha256: crypto.createHash("sha256").update(buffer).digest("hex").toUpperCase(),
    bytes: buffer.length,
  };
}

class CdpClient {
  constructor(webSocketUrl) {
    this.webSocket = new WebSocket(webSocketUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.eventWaiters = new Map();
    this.opened = new Promise((resolve, reject) => {
      this.webSocket.addEventListener("open", resolve, { once: true });
      this.webSocket.addEventListener("error", reject, { once: true });
    });
    this.webSocket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) {
          reject(new Error(message.error.message || JSON.stringify(message.error)));
        } else {
          resolve(message.result || {});
        }
        return;
      }
      if (message.method && this.eventWaiters.has(message.method)) {
        const waiters = this.eventWaiters.get(message.method);
        this.eventWaiters.delete(message.method);
        waiters.forEach((resolve) => resolve(message.params || {}));
      }
    });
  }

  async send(method, params = {}) {
    await this.opened;
    const id = this.nextId++;
    const payload = JSON.stringify({ id, method, params });
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.webSocket.send(payload);
    });
  }

  waitForEvent(method, timeoutMs = 5000) {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        const waiters = this.eventWaiters.get(method) || [];
        this.eventWaiters.set(method, waiters.filter((waiter) => waiter !== resolve));
        reject(new Error(`Timed out waiting for ${method}`));
      }, timeoutMs);

      const wrappedResolve = (params) => {
        clearTimeout(timeoutId);
        resolve(params);
      };
      const waiters = this.eventWaiters.get(method) || [];
      waiters.push(wrappedResolve);
      this.eventWaiters.set(method, waiters);
    });
  }

  close() {
    this.webSocket.close();
  }
}

async function captureWithChromeDevTools({ url, outputPath, viewport, mobile, userAgent }) {
  const userDataDir = path.join(os.tmpdir(), `checking-temp006-${process.pid}-${Date.now()}`);
  await removeDirectory(userDataDir);
  await fs.mkdir(userDataDir, { recursive: true });

  const chrome = spawn(chromePath, [
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-sync",
    "--disable-extensions",
    "--hide-scrollbars",
    "--remote-debugging-port=0",
    `--user-data-dir=${userDataDir}`,
    "about:blank",
  ], {
    stdio: ["ignore", "ignore", "pipe"],
    windowsHide: true,
  });

  let pageClient = null;
  try {
    const devToolsUrl = await waitForDevToolsUrl(chrome);
    const remotePort = new URL(devToolsUrl).port;
    const targetResponse = await fetch(
      `http://127.0.0.1:${remotePort}/json/new?${encodeURIComponent("about:blank")}`,
      { method: "PUT" },
    );
    if (!targetResponse.ok) {
      throw new Error(`Unable to create Chrome target: HTTP ${targetResponse.status}`);
    }
    const target = await targetResponse.json();
    pageClient = new CdpClient(target.webSocketDebuggerUrl);
    await pageClient.send("Page.enable");
    await pageClient.send("Runtime.enable");
    await pageClient.send("Emulation.setDeviceMetricsOverride", {
      width: viewport.width,
      height: viewport.height,
      deviceScaleFactor: 1,
      mobile,
      screenWidth: viewport.width,
      screenHeight: viewport.height,
    });
    await pageClient.send("Emulation.setUserAgentOverride", { userAgent });

    const loadEvent = pageClient.waitForEvent("Page.loadEventFired", 8000);
    await pageClient.send("Page.navigate", { url });
    await loadEvent;
    await pageClient.send("Runtime.evaluate", {
      awaitPromise: true,
      expression: `
        new Promise((resolve) => {
          const startedAt = Date.now();
          const check = () => {
            if (window.__CHECKING_TEMP006_READY__ === true) {
              resolve(true);
              return;
            }
            if (Date.now() - startedAt > 5000) {
              resolve(false);
              return;
            }
            setTimeout(check, 50);
          };
          check();
        })
      `,
    });
    await pageClient.send("Runtime.evaluate", {
      awaitPromise: true,
      expression: "new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))",
    });
    const screenshot = await pageClient.send("Page.captureScreenshot", {
      format: "png",
      fromSurface: true,
      captureBeyondViewport: false,
    });
    await fs.writeFile(outputPath, Buffer.from(screenshot.data, "base64"));
  } finally {
    if (pageClient) {
      pageClient.close();
    }
    await terminateChrome(chrome);
    await removeDirectory(userDataDir);
  }
}

async function removeDirectory(directoryPath) {
  await fs.rm(directoryPath, {
    recursive: true,
    force: true,
    maxRetries: 8,
    retryDelay: 150,
  });
}

async function terminateChrome(chrome) {
  if (chrome.exitCode !== null || chrome.signalCode !== null) {
    return;
  }
  await new Promise((resolve) => {
    chrome.once("exit", resolve);
    chrome.kill();
    setTimeout(resolve, 2000);
  });
}

function waitForDevToolsUrl(chrome) {
  return new Promise((resolve, reject) => {
    let stderr = "";
    const timeoutId = setTimeout(() => {
      reject(new Error(`Timed out waiting for Chrome DevTools URL. stderr: ${stderr}`));
    }, 10000);

    chrome.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
      const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) {
        clearTimeout(timeoutId);
        resolve(match[1]);
      }
    });
    chrome.on("error", (error) => {
      clearTimeout(timeoutId);
      reject(error);
    });
    chrome.on("exit", (code) => {
      if (code !== null && code !== 0) {
        clearTimeout(timeoutId);
        reject(new Error(`Chrome exited before DevTools was available. code=${code} stderr=${stderr}`));
      }
    });
  });
}

async function writeReadme(entries) {
  const lines = [
    "# Homologacao Visual da Fase 6 de temp_006",
    "",
    "Data: 2026-04-25",
    "",
    "Este diretório reúne artefatos locais da homologação da Fase 6 de `docs/temp_006.md`, gerados a partir da própria SPA do workspace com dados mockados e viewports direcionados aos cenários pedidos.",
    "",
    "Observações importantes:",
    "",
    "- nenhuma captura desta pasta depende da URL pública nem de deploy;",
    "- os cenários usam HTML, CSS e JavaScript reais de `sistema/app/static/check`;",
    "- o cenário de teclado aberto em paisagem foi validado como proxy de viewport reduzido em headless com foco no campo de senha, porque o navegador headless não exibe o teclado virtual do sistema operacional.",
    "",
    "## Cenários capturados",
    "",
    "| Arquivo | Estado | Viewport | Observação |",
    "| --- | --- | --- | --- |",
    ...entries.map((entry) => `| \`${entry.file}\` | ${entry.title} | ${entry.viewport.width}x${entry.viewport.height} | ${entry.note || "-"} |`),
    "",
    "## Comando usado",
    "",
    "```powershell",
    "node scripts/capture_temp_006_homologation.mjs",
    "```",
    "",
  ];
  await fs.writeFile(readmePath, `${lines.join("\n")}\n`, "utf8");
}

async function main() {
  await fs.mkdir(screenshotRoot, { recursive: true });
  const server = await startServer();
  const entries = [];
  try {
    for (const scenario of scenarios) {
      const entry = await screenshotScenario(server, scenario);
      entries.push(entry);
      console.log(`captured ${entry.file}`);
    }
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }

  const manifest = {
    schema_version: 1,
    captured_at: new Date().toISOString(),
    source_of_truth: "sistema/app/static/check",
    artifact_set: "temp_006_homologation",
    browser: chromePath,
    entries,
  };

  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  await writeReadme(entries);
  console.log(`manifest ${path.relative(workspaceRoot, manifestPath).replaceAll("\\", "/")}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});