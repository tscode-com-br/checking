(function (root, factory) {
  const exported = factory();

  if (typeof module === 'object' && module.exports) {
    module.exports = exported;
  }

  root.CheckingWebAutomaticActivities = exported;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const AUTOMATIC_CHECKOUT_LOCATION = 'Fora do Local de Trabalho';
  const AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION = 'Localização não Cadastrada';
  const MIXED_ZONE_LOCATION = 'Zona Mista';

  function parseHistoryTimestamp(value) {
    if (!value) {
      return null;
    }

    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function normalizeLocationName(value) {
    return String(value || '')
      .trim()
      .replace(/\s+/g, ' ')
      .toLowerCase();
  }

  function isCheckoutZoneLocationName(value) {
    return normalizeLocationName(value) === 'zona de checkout';
  }

  function isMixedZoneLocationName(value) {
    return normalizeLocationName(value) === 'zona mista';
  }

  function resolveLastRecordedAction(state) {
    const lastCheckinAt = parseHistoryTimestamp(state && state.last_checkin_at);
    const lastCheckoutAt = parseHistoryTimestamp(state && state.last_checkout_at);
    if (!lastCheckinAt && !lastCheckoutAt) {
      return state && state.current_action ? state.current_action : null;
    }
    if (lastCheckinAt && !lastCheckoutAt) {
      return 'checkin';
    }
    if (!lastCheckinAt && lastCheckoutAt) {
      return 'checkout';
    }
    if (lastCheckinAt > lastCheckoutAt) {
      return 'checkin';
    }
    if (lastCheckoutAt > lastCheckinAt) {
      return 'checkout';
    }
    return state && state.current_action ? state.current_action : null;
  }

  function resolveRecordedCheckInLocation(state) {
    return state && state.current_action === 'checkin' ? state.current_local : null;
  }

  function resolveCurrentRecordedLocation(state) {
    return state ? state.current_local : null;
  }

  function resolveRecordedActionTimestamp(state, action) {
    if (action === 'checkin') {
      return parseHistoryTimestamp(state && state.last_checkin_at);
    }
    if (action === 'checkout') {
      return parseHistoryTimestamp(state && state.last_checkout_at);
    }
    return null;
  }

  function resolveLastRelevantMixedZoneActivity(state) {
    const currentRecordedLocation = resolveCurrentRecordedLocation(state);
    if (!isMixedZoneLocationName(currentRecordedLocation)) {
      return null;
    }

    const lastRecordedAction = resolveLastRecordedAction(state);
    if (lastRecordedAction !== 'checkin' && lastRecordedAction !== 'checkout') {
      return null;
    }

    const timestamp = resolveRecordedActionTimestamp(state, lastRecordedAction);
    if (!timestamp) {
      return null;
    }

    return {
      action: lastRecordedAction,
      local: currentRecordedLocation,
      timestamp,
    };
  }

  function isLastRelevantActivityInMixedZone(state) {
    return Boolean(resolveLastRelevantMixedZoneActivity(state));
  }

  function resolveMixedZoneCooldownMilliseconds(mixedZoneIntervalMinutes) {
    const normalizedIntervalMinutes = Number(mixedZoneIntervalMinutes);
    if (!Number.isFinite(normalizedIntervalMinutes) || normalizedIntervalMinutes < 1) {
      return 0;
    }
    return Math.trunc(normalizedIntervalMinutes) * 60 * 1000;
  }

  function resolveMixedZoneDecisionSettings(settings) {
    if (!settings || typeof settings !== 'object' || Array.isArray(settings)) {
      return {
        mixedZoneIntervalMinutes: settings,
        referenceTime: undefined,
      };
    }

    return {
      mixedZoneIntervalMinutes: settings.mixedZoneIntervalMinutes,
      referenceTime: settings.referenceTime,
    };
  }

  function resolveReferenceTimestamp(referenceTime) {
    if (referenceTime === undefined) {
      return new Date();
    }
    if (referenceTime instanceof Date) {
      return Number.isNaN(referenceTime.getTime()) ? null : referenceTime;
    }
    if (typeof referenceTime === 'number' && Number.isFinite(referenceTime)) {
      const parsedFromNumber = new Date(referenceTime);
      return Number.isNaN(parsedFromNumber.getTime()) ? null : parsedFromNumber;
    }
    return parseHistoryTimestamp(referenceTime);
  }

  function isMixedZoneCooldownActive(state, mixedZoneIntervalMinutes, referenceTime) {
    const lastMixedZoneActivity = resolveLastRelevantMixedZoneActivity(state);
    if (!lastMixedZoneActivity) {
      return false;
    }

    const cooldownMilliseconds = resolveMixedZoneCooldownMilliseconds(mixedZoneIntervalMinutes);
    if (!cooldownMilliseconds) {
      return false;
    }

    const resolvedReferenceTimestamp = resolveReferenceTimestamp(referenceTime);
    if (!resolvedReferenceTimestamp) {
      return false;
    }

    return resolvedReferenceTimestamp.getTime() - lastMixedZoneActivity.timestamp.getTime() < cooldownMilliseconds;
  }

  function resolveAutomaticCheckInLocation(locationPayload) {
    const resolvedLocal = String(locationPayload && locationPayload.resolved_local || '').trim();
    return resolvedLocal || null;
  }

  function isOperationalAutomaticCheckInLocation(locationPayload, automaticLocal) {
    const resolvedLocal = String(locationPayload && locationPayload.resolved_local || '').trim();
    const candidateLocal = String(automaticLocal || '').trim();
    return Boolean(resolvedLocal) && candidateLocal === resolvedLocal;
  }

  // ===========================================================================
  // SITUAÇÃO 8 (docs/regras_e_situacoes/regras_checkin_checkout_webapp.txt):
  // alternância automática check-in/check-out na 'Zona Mista', com o cooldown do
  // campo 'Intervalo de Tempo para Zona Mista'. Decide se uma leitura em 'Zona
  // Mista' deve gerar um novo evento automático, respeitando o cooldown apenas
  // entre leituras consecutivas realizadas dentro da própria 'Zona Mista'.
  // ===========================================================================
  function shouldAttemptAutomaticMixedZoneLocationEvent(locationPayload, remoteState, settings) {
    const resolvedLocal = locationPayload && locationPayload.resolved_local;
    if (!isMixedZoneLocationName(resolvedLocal)) {
      return false;
    }

    const lastRecordedAction = resolveLastRecordedAction(remoteState);
    const currentRecordedLocation = resolveCurrentRecordedLocation(remoteState);
    const lastCheckInLocation = resolveRecordedCheckInLocation(remoteState);
    const decisionSettings = resolveMixedZoneDecisionSettings(settings);
    const cooldownMilliseconds = resolveMixedZoneCooldownMilliseconds(decisionSettings.mixedZoneIntervalMinutes);

    if (
      normalizeLocationName(resolvedLocal)
      && normalizeLocationName(resolvedLocal) === normalizeLocationName(currentRecordedLocation)
    ) {
      if (!isLastRelevantActivityInMixedZone(remoteState) || cooldownMilliseconds <= 0) {
        return false;
      }

      return !isMixedZoneCooldownActive(
        remoteState,
        decisionSettings.mixedZoneIntervalMinutes,
        decisionSettings.referenceTime
      );
    }

    if (lastRecordedAction !== 'checkin') {
      return true;
    }

    return normalizeLocationName(resolvedLocal) !== normalizeLocationName(lastCheckInLocation);
  }

  // ===========================================================================
  // Roteador de decisão para uma posição que CORRESPONDE (matched) a uma área
  // cadastrada na API. Concentra as Situações 1, 2, 3, 4, 6, 7 e 8 do descritivo
  // (docs/regras_e_situacoes/regras_checkin_checkout_webapp.txt). Retornar true
  // significa "disparar um evento automático" (a ação — check-in ou check-out —
  // é resolvida depois em resolveAutomaticLocationAction, em app.js).
  // ===========================================================================
  function shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, settings) {
    const resolvedLocal = locationPayload && locationPayload.resolved_local;
    const lastRecordedAction = resolveLastRecordedAction(remoteState);

    // SITUAÇÃO 1 (variante 'Zona de CheckOut') + SITUAÇÃO 2 + 1ª etapa da SITUAÇÃO 7:
    // estando na 'Zona de CheckOut', dispara check-out apenas se a última atividade foi
    // um check-in (Situação 1). Se a última atividade já foi um check-out, retorna false
    // e nenhuma ação é tomada (Situação 2; e a etapa inicial da Situação 7, em que o
    // usuário permanece na 'Zona de CheckOut' logo após um check-out).
    if (isCheckoutZoneLocationName(resolvedLocal)) {
      return lastRecordedAction === 'checkin';
    }

    // SITUAÇÃO 8: posição corresponde à 'Zona Mista' — alternância automática e cooldown
    // ficam em shouldAttemptAutomaticMixedZoneLocationEvent (ver acima).
    if (isMixedZoneLocationName(resolvedLocal)) {
      return shouldAttemptAutomaticMixedZoneLocationEvent(locationPayload, remoteState, settings);
    }

    // SITUAÇÃO 3 + SITUAÇÃO 7 (variantes 7A/7B): após um check-out, qualquer local
    // cadastrado (≠ Zona de CheckOut) deve disparar o check-in — inclusive quando o local
    // atual coincide com o local em que o check-out foi registrado (ex.: check-out manual
    // no Escritório Principal). Esta verificação precisa vir ANTES do guard de "mesma
    // localização" abaixo, que se aplica apenas ao caso já-em-check-in (Situações 4/6).
    if (lastRecordedAction !== 'checkin') {
      return true;
    }

    // SITUAÇÕES 4 e 6: usuário já em check-in, em local cadastrado (≠ Zona de CheckOut e
    // ≠ Zona Mista, já tratados acima). Conforme o descritivo atualizado, um NOVO check-in
    // deve ser realizado SEMPRE — ao abrir/recarregar/trazer para primeiro plano
    // (Situação 4) ou ao pressionar 'Atualizar' (Situação 6) — INCLUSIVE quando o usuário
    // estiver no MESMO local do último check-in. Esse novo check-in registra/atualiza a
    // localização e o horário do usuário na API, no mesmo local em que ele se encontra.
    // (resolvedLocal sempre vem preenchido aqui, pois esta função só é chamada quando a
    // posição corresponde — matched — a uma área cadastrada; o Boolean evita, por
    // segurança, um disparo com local vazio.)
    return Boolean(normalizeLocationName(resolvedLocal));
  }

  // SITUAÇÃO 1 (variante "além da distância mínima de qualquer área cadastrada") +
  // SITUAÇÃO 2: posição NÃO corresponde a área cadastrada e está fora do raio de trabalho
  // (status 'outside_workplace'). Dispara check-out apenas se a última atividade foi um
  // check-in (Situação 1); se já foi um check-out, retorna false e nada é feito
  // (Situação 2 — o check-out não é repetido por mudança de localização).
  function shouldAttemptAutomaticOutOfRangeCheckout(locationPayload, remoteState) {
    if (!locationPayload || locationPayload.status !== 'outside_workplace') {
      return false;
    }
    return resolveLastRecordedAction(remoteState) === 'checkin';
  }

  // SITUAÇÃO 5: última atividade = check-in, usuário NÃO está em nenhuma área cadastrada,
  // porém ainda está próximo do trabalho (status 'not_in_known_location', dentro do raio).
  // Nenhum check-in/check-out automático deve ocorrer — apenas a exibição de 'Localização
  // não Cadastrada'. Por isso esta função sempre retorna false (não há alvo de check-in).
  function shouldAttemptAutomaticNearbyWorkplaceCheckIn(locationPayload, remoteState) {
    if (!locationPayload || locationPayload.matched || locationPayload.status !== 'not_in_known_location') {
      return false;
    }

    // `not_in_known_location` can still inform the UI, but it is never a valid
    // automatic check-in target.
    return false;
  }

  return {
    AUTOMATIC_CHECKOUT_LOCATION,
    AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION,
    MIXED_ZONE_LOCATION,
    normalizeLocationName,
    isCheckoutZoneLocationName,
    isMixedZoneLocationName,
    resolveLastRecordedAction,
    resolveRecordedCheckInLocation,
    resolveCurrentRecordedLocation,
    resolveRecordedActionTimestamp,
    resolveLastRelevantMixedZoneActivity,
    isLastRelevantActivityInMixedZone,
    isMixedZoneCooldownActive,
    resolveAutomaticCheckInLocation,
    isOperationalAutomaticCheckInLocation,
    resolveMixedZoneDecisionSettings,
    shouldAttemptAutomaticMixedZoneLocationEvent,
    shouldAttemptAutomaticLocationEvent,
    shouldAttemptAutomaticOutOfRangeCheckout,
    shouldAttemptAutomaticNearbyWorkplaceCheckIn,
  };
});
