(function () {
  "use strict";

  let state = { is_active: false, accident: null, current_user_report: null };
  let eventSource = null;
  let pollingHandle = null;
  let refreshDebounce = null;
  let wizardData = {};

  // ---------------------------------------------------------------------------
  // State refresh
  // ---------------------------------------------------------------------------

  async function refreshState() {
    const chave = getCurrentChave();
    if (!chave) return;
    try {
      const resp = await fetch(
        "/api/web/check/accident/state?chave=" + encodeURIComponent(chave),
        { credentials: "include" }
      );
      if (!resp.ok) return;
      state = await resp.json();
      applyTheme(state.is_active);
      renderBanner(state);
      renderInquiryCard(state);
      updateReportButton(state);
    } catch (_) {}
  }

  // ---------------------------------------------------------------------------
  // Theme
  // ---------------------------------------------------------------------------

  function applyTheme(isActive) {
    document.documentElement.classList.toggle("accident-mode", !!isActive);
  }

  // ---------------------------------------------------------------------------
  // Banner
  // ---------------------------------------------------------------------------

  function renderBanner(s) {
    const line = document.getElementById("notificationLinePrimary");
    if (!line) return;
    if (s.is_active) {
      line.textContent = "Acidente Reportado no projeto " + s.project_name + "!";
    } else {
      if (line.textContent.startsWith("Acidente Reportado")) line.textContent = "";
    }
  }

  // ---------------------------------------------------------------------------
  // Inquiry card
  // ---------------------------------------------------------------------------

  function renderInquiryCard(s) {
    const card = document.getElementById("accidentInquiryCard");
    const history = document.querySelector(".history-card:not(.accident-inquiry-card)");
    if (!card) return;
    if (s.is_active) {
      card.hidden = false;
      card.classList.remove("is-hidden");
      resetInquiryCard();
      if (history) history.hidden = s.current_user_report ? false : true;
    } else {
      card.hidden = true;
      card.classList.add("is-hidden");
      if (history) history.hidden = false;
    }
  }

  function resetInquiryCard() {
    const title = document.getElementById("accidentInquiryTitle");
    const safetyBtn = document.getElementById("accidentZoneSafetyButton");
    const accidentBtn = document.getElementById("accidentZoneAccidentButton");
    if (title) title.textContent = "Estou em:";
    if (safetyBtn) { safetyBtn.textContent = "Zona de Segurança"; safetyBtn.onclick = null; }
    if (accidentBtn) { accidentBtn.textContent = "Zona de Acidente"; accidentBtn.onclick = null; }
  }

  // ---------------------------------------------------------------------------
  // Report button
  // ---------------------------------------------------------------------------

  function updateReportButton(s) {
    const btn = document.getElementById("accidentReportButton");
    if (!btn) return;
    btn.hidden = false;
    btn.setAttribute("aria-pressed", s.is_active ? "true" : "false");
    const label = btn.querySelector(".accident-report-button-label");
    if (label) label.textContent = s.is_active ? "Acidente Reportado" : "Reportar Acidente";
  }

  // ---------------------------------------------------------------------------
  // SSE
  // ---------------------------------------------------------------------------

  function startEventSource() {
    stopEventSource();
    const chave = getCurrentChave();
    if (!chave) return;
    eventSource = new EventSource(
      "/api/web/check/stream?chave=" + encodeURIComponent(chave)
    );
    eventSource.onmessage = function (event) {
      try {
        const data = JSON.parse(event.data);
        if (data.reason && data.reason.startsWith("accident_")) {
          scheduleRefresh();
        }
      } catch (_) {}
    };
    eventSource.onerror = function () { /* keep open; polling covers */ };
  }

  function stopEventSource() {
    if (eventSource) { eventSource.close(); eventSource = null; }
  }

  function scheduleRefresh() {
    if (refreshDebounce !== null) clearTimeout(refreshDebounce);
    refreshDebounce = setTimeout(function () {
      refreshDebounce = null;
      refreshState();
    }, 250);
  }

  // ---------------------------------------------------------------------------
  // Polling
  // ---------------------------------------------------------------------------

  function startPolling() {
    stopPolling();
    pollingHandle = setInterval(refreshState, 30000);
  }

  function stopPolling() {
    if (pollingHandle) { clearInterval(pollingHandle); pollingHandle = null; }
  }

  // ---------------------------------------------------------------------------
  // Shared confirm dialog
  // ---------------------------------------------------------------------------

  function askConfirm(zone, status) {
    const dialog = document.getElementById("accidentReportConfirmDialog");
    const backdrop = document.getElementById("accidentReportConfirmBackdrop");
    const textEl = document.getElementById("accidentReportConfirmText");
    const errorEl = document.getElementById("accidentReportConfirmError");
    if (!dialog || !textEl) return;
    const textMap = {
      "safety/ok": "Você confirma que está fora de perigo?",
      "accident/ok": "Você confirma que está na zona do acidente e que está fora de perigo?",
      "accident/help": "Você confirma que está na zona do acidente e que precisa de ajuda?",
    };
    textEl.textContent = textMap[zone + "/" + status] || "";
    if (errorEl) errorEl.textContent = "";
    showDialog(dialog, backdrop);

    document.getElementById("accidentReportConfirmCancel").onclick = function () {
      hideDialog(dialog, backdrop);
      // Restore the inquiry card to its initial state ("Zona de Seguranca" /
      // "Zona de Acidente"). Without this, after going through
      // "Zona de Acidente" -> "Estou bem." -> Cancel, the buttons stay in the
      // intermediate "Estou bem." / "Preciso de Ajuda!" state.
      resetInquiryCard();
    };
    document.getElementById("accidentReportConfirmSubmit").onclick = async function () {
      hideDialog(dialog, backdrop);
      try {
        await fetch("/api/web/check/accident/report", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ chave: getCurrentChave(), zone: zone, status: status }),
        });
      } catch (_) {}
      refreshState();
    };
  }

  // ---------------------------------------------------------------------------
  // Wizard — openAccidentWizard
  // ---------------------------------------------------------------------------

  async function openAccidentWizard() {
    const chave = getCurrentChave();
    if (!chave) return;
    wizardData = { projectId: null, projectName: "", locationId: null, locationName: "", locationRegistered: false, zone: null, status: null };

    const projDialog = document.getElementById("accidentReportProjectDialog");
    const projBackdrop = document.getElementById("accidentReportProjectBackdrop");
    const projOptions = document.getElementById("accidentReportProjectOptions");
    const projError = document.getElementById("accidentReportProjectError");
    const projAdvance = document.getElementById("accidentReportProjectAdvance");
    const projCancel = document.getElementById("accidentReportProjectCancel");
    if (!projDialog) return;

    projOptions.innerHTML = "";
    if (projError) projError.textContent = "";
    projAdvance.disabled = true;
    showDialog(projDialog, projBackdrop);
    projCancel.onclick = function () { hideDialog(projDialog, projBackdrop); };

    let projects = [];
    try {
      const resp = await fetch(
        "/api/web/check/accident/wizard/projects?chave=" + encodeURIComponent(chave),
        { credentials: "include" }
      );
      if (resp.ok) projects = await resp.json();
    } catch (_) {}

    if (!projects.length) {
      projOptions.innerHTML = "<p>Nenhum projeto disponível.</p>";
    } else {
      renderProjectRadios(projects, projAdvance);
    }

    projAdvance.onclick = function () { advanceWizardToLocations(projDialog, projBackdrop, chave); };
  }

  function renderProjectRadios(projects, advanceBtn) {
    const projOptions = document.getElementById("accidentReportProjectOptions");
    projOptions.innerHTML = "";
    projects.forEach(function (p) {
      const label = document.createElement("label");
      const inp = document.createElement("input");
      inp.type = "radio";
      inp.name = "accidentProjectChoice";
      inp.value = String(p.id);
      inp.addEventListener("change", function () {
        wizardData.projectId = parseInt(inp.value, 10);
        wizardData.projectName = p.name;
        if (advanceBtn) advanceBtn.disabled = false;
      });
      const span = document.createElement("span");
      span.textContent = p.name;
      label.appendChild(inp);
      label.appendChild(span);
      projOptions.appendChild(label);
    });
  }

  async function advanceWizardToLocations(prevDialog, prevBackdrop, chave) {
    if (!wizardData.projectId) return;
    hideDialog(prevDialog, prevBackdrop);

    const locDialog = document.getElementById("accidentReportLocationDialog");
    const locBackdrop = document.getElementById("accidentReportLocationBackdrop");
    const locOptions = document.getElementById("accidentReportLocationOptions");
    const locError = document.getElementById("accidentReportLocationError");
    const locAdvance = document.getElementById("accidentReportLocationAdvance");
    const locCancel = document.getElementById("accidentReportLocationCancel");
    const customInput = document.getElementById("accidentReportCustomLocation");
    if (!locDialog) return;

    locOptions.innerHTML = "";
    if (locError) locError.textContent = "";
    locAdvance.disabled = true;
    if (customInput) { customInput.disabled = true; customInput.value = ""; }
    showDialog(locDialog, locBackdrop);
    locCancel.onclick = function () { hideDialog(locDialog, locBackdrop); };

    let locations = [];
    try {
      const resp = await fetch(
        "/api/web/check/accident/wizard/locations?chave=" + encodeURIComponent(chave) + "&project_id=" + wizardData.projectId,
        { credentials: "include" }
      );
      if (resp.ok) locations = await resp.json();
    } catch (_) {}

    renderLocationRadios(locations, locAdvance, customInput);

    const customRadio = document.querySelector('input[name="accidentLocationChoice"][value="__custom__"]');
    if (customRadio && customInput) {
      customRadio.addEventListener("change", function () {
        customInput.disabled = false;
        wizardData.locationId = null;
        wizardData.locationName = customInput.value;
        wizardData.locationRegistered = false;
        locAdvance.disabled = !customInput.value.trim();
        customInput.oninput = function () {
          wizardData.locationName = customInput.value;
          locAdvance.disabled = !customInput.value.trim();
        };
      });
    }

    locAdvance.onclick = function () { advanceWizardToSituation(locDialog, locBackdrop); };
  }

  function renderLocationRadios(locations, advanceBtn, customInput) {
    const locOptions = document.getElementById("accidentReportLocationOptions");
    locOptions.innerHTML = "";
    locations.forEach(function (loc) {
      const label = document.createElement("label");
      const inp = document.createElement("input");
      inp.type = "radio";
      inp.name = "accidentLocationChoice";
      inp.value = String(loc.id);
      inp.addEventListener("change", function () {
        wizardData.locationId = parseInt(inp.value, 10);
        wizardData.locationName = loc.name;
        wizardData.locationRegistered = loc.registered !== false;
        if (customInput) { customInput.disabled = true; customInput.value = ""; }
        if (advanceBtn) advanceBtn.disabled = false;
      });
      const span = document.createElement("span");
      span.textContent = loc.name;
      label.appendChild(inp);
      label.appendChild(span);
      locOptions.appendChild(label);
    });
  }

  function advanceWizardToSituation(prevDialog, prevBackdrop) {
    hideDialog(prevDialog, prevBackdrop);
    const sitDialog = document.getElementById("accidentReportSituationDialog");
    const sitBackdrop = document.getElementById("accidentReportSituationBackdrop");
    const sitError = document.getElementById("accidentReportSituationError");
    const sitAdvance = document.getElementById("accidentReportSituationAdvance");
    const sitCancel = document.getElementById("accidentReportSituationCancel");
    if (!sitDialog) return;

    document.querySelectorAll('input[name="accidentSituationChoice"]').forEach(function (r) {
      r.checked = false;
    });
    if (sitError) sitError.textContent = "";
    sitAdvance.disabled = true;
    showDialog(sitDialog, sitBackdrop);
    sitCancel.onclick = function () { hideDialog(sitDialog, sitBackdrop); };

    document.querySelectorAll('input[name="accidentSituationChoice"]').forEach(function (r) {
      r.addEventListener("change", function () { sitAdvance.disabled = false; });
    });

    sitAdvance.onclick = function () { advanceWizardToConfirm(sitDialog, sitBackdrop); };
  }

  function advanceWizardToConfirm(prevDialog, prevBackdrop) {
    const selectedSituation = document.querySelector('input[name="accidentSituationChoice"]:checked');
    if (!selectedSituation) return;
    const value = selectedSituation.value;
    if (value === "safety-ok") { wizardData.zone = "safety"; wizardData.status = "ok"; }
    else if (value === "accident-ok") { wizardData.zone = "accident"; wizardData.status = "ok"; }
    else if (value === "accident-help") { wizardData.zone = "accident"; wizardData.status = "help"; }

    hideDialog(prevDialog, prevBackdrop);
    const confirmDialog = document.getElementById("accidentReportConfirmDialog");
    const confirmBackdrop = document.getElementById("accidentReportConfirmBackdrop");
    const textEl = document.getElementById("accidentReportConfirmText");
    const errorEl = document.getElementById("accidentReportConfirmError");
    if (!confirmDialog || !textEl) return;

    textEl.textContent = 'Confirmar acidente no projeto "' + wizardData.projectName + '" em "' + wizardData.locationName + '"?';
    if (errorEl) errorEl.textContent = "";
    showDialog(confirmDialog, confirmBackdrop);

    document.getElementById("accidentReportConfirmCancel").onclick = function () {
      hideDialog(confirmDialog, confirmBackdrop);
    };
    document.getElementById("accidentReportConfirmSubmit").onclick = async function () {
      if (errorEl) errorEl.textContent = "";
      try {
        const resp = await fetch("/api/web/check/accident/open", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            chave: getCurrentChave(),
            project_id: wizardData.projectId,
            location_id: wizardData.locationId,
            custom_location_name: wizardData.locationId ? null : wizardData.locationName,
            zone: wizardData.zone,
            status: wizardData.status,
          }),
        });
        if (!resp.ok) {
          const err = await resp.json().catch(function () { return {}; });
          if (errorEl) errorEl.textContent = err.detail || "Erro ao reportar acidente.";
          return;
        }
      } catch (_) {
        if (errorEl) errorEl.textContent = "Erro ao reportar acidente.";
        return;
      }
      hideDialog(confirmDialog, confirmBackdrop);
      refreshState();
    };
  }

  // ---------------------------------------------------------------------------
  // Actions dialog (when accident is already active)
  // ---------------------------------------------------------------------------

  function openAccidentActionsDialog() {
    const dialog = document.getElementById("accidentActionsDialog");
    const backdrop = document.getElementById("accidentActionsBackdrop");
    if (!dialog) return;
    showDialog(dialog, backdrop);

    document.getElementById("accidentActionsClose").onclick = function () {
      hideDialog(dialog, backdrop);
    };
    const videoBtn = document.getElementById("accidentActionsVideoButton");
    if (videoBtn) {
      videoBtn.onclick = function () {
        hideDialog(dialog, backdrop);
        if (window.AccidentCamera) {
          window.AccidentCamera.startRecording(getCurrentChave());
        }
      };
    }
  }

  // ---------------------------------------------------------------------------
  // Event listeners
  // ---------------------------------------------------------------------------

  const reportBtn = document.getElementById("accidentReportButton");
  if (reportBtn) {
    reportBtn.addEventListener("click", function () {
      if (state.is_active) openAccidentActionsDialog();
      else openAccidentWizard();
    });
  }

  const zoneSafetyBtn = document.getElementById("accidentZoneSafetyButton");
  if (zoneSafetyBtn) {
    zoneSafetyBtn.addEventListener("click", function () {
      askConfirm("safety", "ok");
    });
  }

  const zoneAccidentBtn = document.getElementById("accidentZoneAccidentButton");
  if (zoneAccidentBtn) {
    zoneAccidentBtn.addEventListener("click", function () {
      const title = document.getElementById("accidentInquiryTitle");
      if (title) title.textContent = "Sua Situação";
      if (zoneSafetyBtn) {
        zoneSafetyBtn.textContent = "Estou bem.";
        zoneSafetyBtn.onclick = function () { askConfirm("accident", "ok"); };
      }
      zoneAccidentBtn.textContent = "Preciso de Ajuda!";
      zoneAccidentBtn.onclick = function () { askConfirm("accident", "help"); };
    });
  }

  const audioVideoBtn = document.getElementById("settingsAudioVideoPermissionButton");
  if (audioVideoBtn) {
    audioVideoBtn.addEventListener("click", async function () {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        stream.getTracks().forEach(function (t) { t.stop(); });
        audioVideoBtn.textContent = "Audio & Video permitido";
        audioVideoBtn.disabled = true;
      } catch (_) {
        alert("Permissão negada.");
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function getCurrentChave() {
    const inp = document.getElementById("chaveInput");
    return (inp && inp.value && inp.value.length === 4) ? inp.value : null;
  }

  function showDialog(el, backdrop) {
    if (el) { el.hidden = false; el.classList.remove("is-hidden"); }
    if (backdrop) { backdrop.hidden = false; backdrop.classList.remove("is-hidden"); }
  }

  function hideDialog(el, backdrop) {
    if (el) { el.hidden = true; el.classList.add("is-hidden"); }
    if (backdrop) { backdrop.hidden = true; backdrop.classList.add("is-hidden"); }
  }

  // ---------------------------------------------------------------------------
  // Bootstrap — called from app.js after login / logout
  // ---------------------------------------------------------------------------

  window.AccidentMode = {
    onLogin: function () { refreshState(); startEventSource(); startPolling(); },
    onLogout: function () {
      stopEventSource();
      stopPolling();
      applyTheme(false);
      state = { is_active: false, accident: null, current_user_report: null };
    },
  };
})();
