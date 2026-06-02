(function () {
  "use strict";

  let state = { is_active: false, accident: null, current_user_report: null, active_accidents: [] };
  let eventSource = null;
  let pollingHandle = null;
  let refreshDebounce = null;
  let wizardData = {};
  // Set of accident ids whose ack dialog has already been displayed in this
  // session. Used together with _ackDialogQueue to avoid re-showing dialogs
  // on every refreshState() invocation while still permitting a fresh dialog
  // for genuinely new accidents.
  const _ackShownForAccidentIds = new Set();
  const _ackDialogQueue = [];
  let _ackDialogShowing = false;
  let _canReportAccident = false;
  // Latest /api/web/check/state snapshot pushed in by app.js — needed to
  // compare the user's current check-in status (and current projeto) against
  // the active accident's project.
  let _latestWebCheckState = null;
  // Tracks which accidents we have already attempted an auto check-in for in
  // this session. Prevents the retry loop from re-firing on every refresh.
  // Possible values per id:
  //   'pending'  → retries in flight
  //   'success'  → check-in landed, nothing else to do
  //   'failed'   → 3 attempts exhausted, fall back to manual check-in message
  const _autoCheckinAttemptStatus = new Map();

  // ---------------------------------------------------------------------------
  // i18n helper — usa window.CheckingWebI18n.t quando disponivel; cai no
  // fallback portugues caso o modulo ainda nao tenha carregado.
  // ---------------------------------------------------------------------------

  function tt(key, fallback) {
    const i18n = window.CheckingWebI18n;
    if (i18n && typeof i18n.t === "function") {
      try {
        const result = i18n.t(key);
        if (typeof result === "string" && result && result !== key) {
          return result;
        }
      } catch (_) {
        // fallthrough to fallback
      }
    }
    return fallback;
  }

  function applyReportButtonLabel() {
    const btn = document.getElementById("accidentReportButton");
    if (!btn) return;
    const label = btn.querySelector(".accident-report-button-label");
    if (!label) return;
    label.textContent = state.is_active
      ? tt("accident.button.reported", "Acidente Reportado")
      : tt("accident.button.report", "Reportar Acidente");
  }

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
      if (!Array.isArray(state.active_accidents)) state.active_accidents = [];

      // Prune the "already shown" tracker so dialogs reappear if the same
      // accident_id ever resurfaces after being closed and reopened. We keep
      // only ids still present in active_accidents.
      const liveIds = new Set(state.active_accidents.map(function (a) { return a.accident_id; }));
      Array.from(_ackShownForAccidentIds).forEach(function (id) {
        if (!liveIds.has(id)) _ackShownForAccidentIds.delete(id);
      });

      applyTheme(state.is_active);
      renderBanner(state);
      renderInquiryCard(state);
      updateReportButton(state);

      // State-based gate (NOT transition-based): enqueue an ack dialog for
      // every active accident the user has not acknowledged yet AND has not
      // already been queued in this session. Resilient to many refreshes
      // (SSE + polling + bootstrap) — the Set guarantees idempotency.
      state.active_accidents.forEach(function (item) {
        if (!item || !item.accident_id) return;
        if (item.awareness_status === "acknowledged") return;
        if (_ackShownForAccidentIds.has(item.accident_id)) return;
        if (_ackDialogQueue.some(function (q) { return q.accident_id === item.accident_id; })) return;
        _ackShownForAccidentIds.add(item.accident_id);
        _ackDialogQueue.push(item);
      });
      _processAckQueue();
    } catch (_) {}
  }

  function _processAckQueue() {
    if (_ackDialogShowing) return;
    const next = _ackDialogQueue.shift();
    if (!next) return;
    _ackDialogShowing = true;
    showAccidentAckDialog(next);
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

  // A user is considered to have reported when the backend has a non-null
  // reported_at on their AccidentUserReport. open_accident seeds a 'waiting'
  // report for every project member, so checking only `current_user_report`
  // would wrongly flag users who have not interacted yet.
  function _userHasReported(report) {
    return !!(report && report.reported_at);
  }

  // The accident project matches the user's currently checked-in project.
  // Compare by name (state.project_name vs webState.projeto) — both refer to
  // the project's `name` field. Returns false when either side is missing.
  function _userCheckedInAtAccidentProject(s, webState) {
    if (!webState || webState.current_action !== "checkin") return false;
    // If the backend already seeded a report for this user in this accident,
    // they are confirmed members of the accident's project — show the card
    // without relying on project-name string comparison (which can fail when
    // webState comes from MobileSyncStateResponse instead of
    // WebCheckHistoryResponse, or when the project catalog hasn't been
    // resolved yet on the client).
    if (s && s.current_user_report != null) return true;
    const userProject = (webState.projeto || "").trim();
    const accidentProject = (s && s.project_name ? String(s.project_name) : "").trim();
    return !!userProject && userProject === accidentProject;
  }

  function _userInCheckout(webState) {
    return !!(webState && webState.current_action === "checkout");
  }

  function renderInquiryCard(s) {
    const card = document.getElementById("accidentInquiryCard");
    const history = document.querySelector(".history-card:not(.accident-inquiry-card)");
    if (!card) return;
    if (!s.is_active) {
      _showInquiryCard(card, false);
      if (history) history.hidden = false;
      _hidePostReportState();
      _hideManualCheckinMessage();
      return;
    }

    // Accident is active. Decide between the four scenarios from item 4.1:
    //  (1) user is checked-in at the accident's project  → normal card (zone buttons / post-report)
    //  (2) user is checked-in at ANOTHER project          → hide the card, keep theme on
    //  (3) user is in check-out:
    //      3a) atividades automáticas ON + not yet tried  → try auto check-in (3x)
    //      3b) atividades automáticas ON + tried & failed → show manual check-in message
    //      3c) atividades automáticas OFF                 → hide the card
    const webState = _latestWebCheckState;
    const accidentId = s.accident_id || null;

    if (_userCheckedInAtAccidentProject(s, webState)) {
      // Scenario (1): normal flow.
      _showInquiryCard(card, true);
      _hideManualCheckinMessage();
      const hasReported = _userHasReported(s.current_user_report);
      if (history) history.hidden = hasReported ? false : true;
      if (hasReported) {
        _showPostReportState();
      } else {
        resetInquiryCard();
      }
      return;
    }

    // Scenarios (2)/(3): user is not checked-in at the accident's project.
    if (history) history.hidden = false;

    if (_userInCheckout(webState)) {
      const autoEnabled = _isAutomaticActivitiesEnabledNow();
      const status = accidentId ? _autoCheckinAttemptStatus.get(accidentId) : undefined;
      if (autoEnabled && status === undefined) {
        // Scenario (3a): kick off the retry loop. Hide the card while it runs.
        _showInquiryCard(card, false);
        _hidePostReportState();
        _hideManualCheckinMessage();
        _runAutoCheckinForAccident(accidentId);
        return;
      }
      if (autoEnabled && status === "pending") {
        _showInquiryCard(card, false);
        _hidePostReportState();
        _hideManualCheckinMessage();
        return;
      }
      if (status === "failed") {
        // Scenario (3b): retries exhausted — surface the manual check-in copy.
        _showInquiryCard(card, true);
        _hidePostReportState();
        _showManualCheckinMessage();
        return;
      }
      if (status === "success") {
        // Auto check-in succeeded but _latestWebCheckState is still stale (says
        // "checkout") because app.js hasn't delivered a fresh /check/state yet.
        // Show the zone buttons now and keep scheduling refreshes until
        // onCheckWebState receives the updated state (from there the normal
        // scenario-1 path takes over and the stale branch is never reached again).
        _showInquiryCard(card, true);
        _hidePostReportState();
        _hideManualCheckinMessage();
        resetInquiryCard();
        scheduleRefresh();
        return;
      }
      // Scenario (3c): no auto activities, no retries → keep the theme only.
      _showInquiryCard(card, false);
      _hidePostReportState();
      _hideManualCheckinMessage();
      return;
    }

    // Scenario (2): user is checked-in somewhere else (or has never checked
    // in today). Keep the theme on, hide the inquiry card.
    _showInquiryCard(card, false);
    _hidePostReportState();
    _hideManualCheckinMessage();
  }

  function _showInquiryCard(card, visible) {
    if (!card) return;
    if (visible) {
      card.hidden = false;
      card.classList.remove("is-hidden");
    } else {
      card.hidden = true;
      card.classList.add("is-hidden");
    }
  }

  function _isAutomaticActivitiesEnabledNow() {
    const toggle = document.getElementById("automaticActivitiesToggle");
    return !!(toggle && toggle.checked);
  }

  function _runAutoCheckinForAccident(accidentId) {
    if (!accidentId) return;
    if (_autoCheckinAttemptStatus.get(accidentId)) return;
    _autoCheckinAttemptStatus.set(accidentId, "pending");

    const helper = window.AccidentMode && window.AccidentMode.requestAutoCheckinWithRetries;
    if (typeof helper !== "function") {
      // No retry helper available — treat as failed so the manual message shows.
      _autoCheckinAttemptStatus.set(accidentId, "failed");
      scheduleRefresh();
      return;
    }

    Promise.resolve(helper(3)).then(function (success) {
      if (success) {
        _autoCheckinAttemptStatus.set(accidentId, "success");
      } else {
        _autoCheckinAttemptStatus.set(accidentId, "failed");
        // If the user had auto activities on and we exhausted retries, the
        // item 4.1 spec asks us to disable it so subsequent activity goes via
        // explicit user action. Guard against unchecking when the user is
        // somehow now in check-in (shouldn't happen, but defensive).
        const toggle = document.getElementById("automaticActivitiesToggle");
        const webState = _latestWebCheckState;
        if (toggle && toggle.checked && _userInCheckout(webState)) {
          toggle.checked = false;
          try { toggle.dispatchEvent(new Event("change", { bubbles: true })); } catch (_) {}
        }
      }
      scheduleRefresh();
    }).catch(function () {
      _autoCheckinAttemptStatus.set(accidentId, "failed");
      scheduleRefresh();
    });
  }

  function _showManualCheckinMessage() {
    const card = document.getElementById("accidentInquiryCard");
    if (!card) return;
    const safetyBtn = document.getElementById("accidentZoneSafetyButton");
    const accidentBtn = document.getElementById("accidentZoneAccidentButton");
    if (safetyBtn) { safetyBtn.hidden = true; safetyBtn.classList.add("is-hidden"); }
    if (accidentBtn) { accidentBtn.hidden = true; accidentBtn.classList.add("is-hidden"); }
    let msgEl = document.getElementById("accidentManualCheckinMessage");
    if (!msgEl) {
      msgEl = document.createElement("p");
      msgEl.id = "accidentManualCheckinMessage";
      msgEl.className = "notification-line accident-manual-checkin-message";
      msgEl.style.color = "#c8222a";
      msgEl.style.fontWeight = "700";
      const titleEl = document.getElementById("accidentInquiryTitle");
      if (titleEl && titleEl.parentNode === card) {
        card.insertBefore(msgEl, titleEl.nextSibling);
      } else {
        card.appendChild(msgEl);
      }
    }
    msgEl.textContent = tt(
      "accident.fallback.manualCheckin",
      "Situação de Acidente. Realize o check-in manual IMEDIATAMENTE."
    );
    msgEl.hidden = false;
    msgEl.classList.remove("is-hidden");
  }

  function _hideManualCheckinMessage() {
    const msgEl = document.getElementById("accidentManualCheckinMessage");
    if (!msgEl) return;
    msgEl.hidden = true;
    msgEl.classList.add("is-hidden");
  }

  function _showPostReportState() {
    const safetyBtn = document.getElementById("accidentZoneSafetyButton");
    const accidentBtn = document.getElementById("accidentZoneAccidentButton");
    const msg = document.getElementById("accidentSituationSentMsg");
    const btn = document.getElementById("accidentTriggerEmergencyButton");
    if (safetyBtn) { safetyBtn.hidden = true; safetyBtn.classList.add("is-hidden"); }
    if (accidentBtn) { accidentBtn.hidden = true; accidentBtn.classList.add("is-hidden"); }
    if (msg) { msg.textContent = "Situação atual enviada."; msg.hidden = false; msg.classList.remove("is-hidden"); }
    if (btn) { btn.hidden = false; btn.classList.remove("is-hidden"); }
  }

  function _hidePostReportState() {
    const safetyBtn = document.getElementById("accidentZoneSafetyButton");
    const accidentBtn = document.getElementById("accidentZoneAccidentButton");
    const msg = document.getElementById("accidentSituationSentMsg");
    const btn = document.getElementById("accidentTriggerEmergencyButton");
    if (safetyBtn) { safetyBtn.hidden = false; safetyBtn.classList.remove("is-hidden"); }
    if (accidentBtn) { accidentBtn.hidden = false; accidentBtn.classList.remove("is-hidden"); }
    if (msg) { msg.hidden = true; msg.classList.add("is-hidden"); }
    if (btn) { btn.hidden = true; btn.classList.add("is-hidden"); }
  }

  function resetInquiryCard() {
    const title = document.getElementById("accidentInquiryTitle");
    const safetyBtn = document.getElementById("accidentZoneSafetyButton");
    const accidentBtn = document.getElementById("accidentZoneAccidentButton");
    const msg = document.getElementById("accidentSituationSentMsg");
    const btn = document.getElementById("accidentTriggerEmergencyButton");
    if (title) title.textContent = "Estou em:";
    if (safetyBtn) { safetyBtn.textContent = "Zona de Segurança"; safetyBtn.onclick = null; safetyBtn.hidden = false; safetyBtn.classList.remove("is-hidden"); }
    if (accidentBtn) { accidentBtn.textContent = "Zona de Acidente"; accidentBtn.onclick = null; accidentBtn.hidden = false; accidentBtn.classList.remove("is-hidden"); }
    if (msg) { msg.hidden = true; msg.classList.add("is-hidden"); }
    if (btn) { btn.hidden = true; btn.classList.add("is-hidden"); }
  }

  // ---------------------------------------------------------------------------
  // Report button
  // ---------------------------------------------------------------------------

  function updateReportButton(s) {
    const btn = document.getElementById("accidentReportButton");
    if (!btn) return;
    btn.setAttribute("aria-pressed", s.is_active ? "true" : "false");
    applyReportButtonLabel();
    _applyReportButtonVisibility();
  }

  function _applyReportButtonVisibility() {
    const btn = document.getElementById("accidentReportButton");
    if (!btn) return;
    // During an active accident always show the button; otherwise respect check-in state
    btn.hidden = !state.is_active && !_canReportAccident;
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
      _showPostReportState();
      refreshState();
      // Auto-trigger emergency call when user reports "help"
      if (zone === "accident" && status === "help") {
        _autoTriggerEmergencyCall();
      }
    };
  }

  // ---------------------------------------------------------------------------
  // Wizard — openAccidentWizard
  // ---------------------------------------------------------------------------

  async function openAccidentWizard() {
    const chave = getCurrentChave();
    if (!chave) return;
    wizardData = { projectId: null, projectName: "", locationId: null, locationName: "", locationRegistered: false, zone: null, status: null, description: "" };

    // Defensive reset of every wizard button. The accidentReportConfirmDialog
    // is shared between askConfirm (post-report flow) and the wizard's final
    // step (open a new accident). Without this reset a stale `disabled` from
    // a previous interaction could prevent the admin from confirming a new
    // accident during an active one — exactly the bug reported in item 5.3.
    const confirmSubmit = document.getElementById("accidentReportConfirmSubmit");
    if (confirmSubmit) confirmSubmit.disabled = false;
    const locationAdvance = document.getElementById("accidentReportLocationAdvance");
    if (locationAdvance) locationAdvance.disabled = true;
    const situationAdvance = document.getElementById("accidentReportSituationAdvance");
    if (situationAdvance) situationAdvance.disabled = true;
    const descriptionAdvance = document.getElementById("accidentReportDescriptionAdvance");
    if (descriptionAdvance) descriptionAdvance.disabled = false;

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

    locAdvance.onclick = function () { advanceWizardToDescription(locDialog, locBackdrop); };
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

  function advanceWizardToDescription(prevDialog, prevBackdrop) {
    hideDialog(prevDialog, prevBackdrop);
    const descDialog = document.getElementById("accidentReportDescriptionDialog");
    const descBackdrop = document.getElementById("accidentReportDescriptionBackdrop");
    const descText = document.getElementById("accidentReportDescriptionText");
    const descError = document.getElementById("accidentReportDescriptionError");
    const descAdvance = document.getElementById("accidentReportDescriptionAdvance");
    const descCancel = document.getElementById("accidentReportDescriptionCancel");

    // FAILHARD: the description step is a hard requirement of item 4.6 — never
    // skip it silently. If the markup or any control is missing, surface a
    // console error so misconfigured front deploys are caught in the dev tools
    // instead of leading users straight to "Sua Situação".
    if (!descDialog || !descAdvance || !descCancel || !descText) {
      console.error(
        "[accident wizard] accidentReportDescriptionDialog markup is incomplete; " +
        "the Descrição Detalhada step cannot be displayed. Check check/index.html."
      );
      return;
    }

    descText.value = wizardData.description || "";
    if (descError) descError.textContent = "";
    // Avançar is always enabled — description is optional, but the user must
    // pass through the step (no silent skipping per item 4.6).
    descAdvance.disabled = false;
    showDialog(descDialog, descBackdrop);

    descCancel.onclick = function () {
      hideDialog(descDialog, descBackdrop);
    };
    descAdvance.onclick = function () {
      // Capture the (possibly empty) description and persist it through to
      // POST /api/web/check/accident/open. Trim trailing whitespace; an empty
      // string is a valid value (description is optional).
      wizardData.description = (descText.value || "").trim();
      advanceWizardToSituation(descDialog, descBackdrop);
    };
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
    const submitBtn = document.getElementById("accidentReportConfirmSubmit");
    submitBtn.onclick = async function () {
      if (errorEl) errorEl.textContent = "";
      submitBtn.disabled = true;
      let success = false;
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
            description: wizardData.description || "",
          }),
        });
        if (!resp.ok) {
          const err = await resp.json().catch(function () { return {}; });
          if (errorEl) errorEl.textContent = err.detail || "Erro ao reportar acidente.";
          return;
        }
        success = true;
      } catch (_) {
        if (errorEl) errorEl.textContent = "Erro ao reportar acidente.";
      } finally {
        // Always re-enable the button before returning so the next time the
        // wizard opens (e.g. opening a second accident in another project)
        // Confirmar starts in the enabled state.
        submitBtn.disabled = false;
      }
      if (success) {
        hideDialog(confirmDialog, confirmBackdrop);
        refreshState();
      }
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
    const newBtn = document.getElementById("accidentActionsNewButton");
    if (newBtn) {
      newBtn.onclick = function () {
        hideDialog(dialog, backdrop);
        openAccidentWizard();
      };
    }
  }

  // ---------------------------------------------------------------------------
  // Accident acknowledged dialog
  // ---------------------------------------------------------------------------

  function showAccidentAckDialog(item) {
    const dialog = document.getElementById("accidentAckDialog");
    const backdrop = document.getElementById("accidentAckBackdrop");
    if (!dialog) {
      _ackDialogShowing = false;
      _processAckQueue();
      return;
    }

    const projEl = document.getElementById("accidentAckProject");
    const locEl = document.getElementById("accidentAckLocation");
    const detEl = document.getElementById("accidentAckDetails");
    if (projEl) projEl.textContent = item.project_name || "";
    if (locEl) locEl.textContent = item.location_name || "";
    if (detEl) detEl.textContent = item.description || "";
    showDialog(dialog, backdrop);

    document.getElementById("accidentAckButton").onclick = async function () {
      hideDialog(dialog, backdrop);
      try {
        await fetch("/api/web/check/accident/acknowledge", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            chave: getCurrentChave(),
            accident_id: item.accident_id || null,
          }),
        });
      } catch (_) {}
      if (window.AccidentMode && window.AccidentMode.requestAutoCheckin) {
        window.AccidentMode.requestAutoCheckin();
      }
      _ackDialogShowing = false;
      // Continue to next queued dialog (if any). Drain synchronously so the
      // user sees them in immediate succession.
      _processAckQueue();
    };
  }

  // ---------------------------------------------------------------------------
  // Emergency call
  // ---------------------------------------------------------------------------

  async function _triggerEmergencyCall() {
    const chave = getCurrentChave();
    if (!chave) return;
    const notifEl = document.getElementById("notificationLineSecondary");
    if (notifEl) notifEl.textContent = "Acionando serviço de emergência…";
    try {
      const resp = await fetch("/api/web/check/accident/emergency-call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ chave: chave }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (notifEl) notifEl.textContent = "✅ Ligação de emergência N.º " + (data.call_number_label || data.call_number) + " iniciada.";
      } else if (resp.status === 409) {
        if (notifEl) notifEl.textContent = "Ligação de emergência já foi realizada neste acidente.";
      } else {
        if (notifEl) notifEl.textContent = "Erro ao acionar serviço de emergência.";
      }
    } catch (_) {
      if (notifEl) notifEl.textContent = "Erro de conexão ao acionar emergência.";
    }
  }

  function _autoTriggerEmergencyCall() {
    _triggerEmergencyCall().catch(function () {});
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

  const emergencyTriggerBtn = document.getElementById("accidentTriggerEmergencyButton");
  if (emergencyTriggerBtn) {
    emergencyTriggerBtn.addEventListener("click", function () { _triggerEmergencyCall(); });
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
      state = { is_active: false, accident: null, current_user_report: null, active_accidents: [] };
      _canReportAccident = false;
      _ackShownForAccidentIds.clear();
      _ackDialogQueue.length = 0;
      _ackDialogShowing = false;
      _latestWebCheckState = null;
      _autoCheckinAttemptStatus.clear();
    },
    // Re-aplica os labels do botao 'Reportar Acidente' / 'Acidente Reportado'
    // sem alterar visibilidade. Chamado por app.js apos mudanca de idioma.
    refreshLabels: function () { applyReportButtonLabel(); },
    // Called by app.js after each fetch of /check/state to update button visibility
    // and to provide the latest user activity context (current_action, projeto)
    // used by renderInquiryCard to decide between the 4 scenarios of item 4.1.
    onCheckWebState: function (webState) {
      const prevAction = _latestWebCheckState && _latestWebCheckState.current_action;
      _latestWebCheckState = webState || null;
      _canReportAccident = !!(
        webState && webState.has_current_day_checkin && webState.current_action === "checkin"
      );
      _applyReportButtonVisibility();
      // Re-render so a fresh /check/state can flip the inquiry card visibility
      // (e.g. user transitioned from check-out to check-in while modo acidente
      // was active — the auto check-in retry resolved successfully).
      renderInquiryCard(state);
      // When the user transitions from check-out to check-in while the accident
      // is active, trigger a fresh /check/accident/state fetch so that
      // current_user_report is up-to-date and the inquiry card shows reliably.
      if (state.is_active && prevAction === "checkout" && webState && webState.current_action === "checkin") {
        scheduleRefresh();
      }
    },
    // Exposed by app.js after login; triggers a lifecycle update cycle (auto check-in if GPS available)
    requestAutoCheckin: null,
  };
})();
