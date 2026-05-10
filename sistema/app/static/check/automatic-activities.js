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

  function shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, settings) {
    const resolvedLocal = locationPayload && locationPayload.resolved_local;
    const lastRecordedAction = resolveLastRecordedAction(remoteState);
    const currentRecordedLocation = resolveCurrentRecordedLocation(remoteState);
    const lastCheckInLocation = resolveRecordedCheckInLocation(remoteState);

    if (isCheckoutZoneLocationName(resolvedLocal)) {
      return lastRecordedAction === 'checkin';
    }

    if (isMixedZoneLocationName(resolvedLocal)) {
      return shouldAttemptAutomaticMixedZoneLocationEvent(locationPayload, remoteState, settings);
    }

    if (
      normalizeLocationName(resolvedLocal)
      && normalizeLocationName(resolvedLocal) === normalizeLocationName(currentRecordedLocation)
    ) {
      return false;
    }

    if (lastRecordedAction !== 'checkin') {
      return true;
    }

    return normalizeLocationName(resolvedLocal) !== normalizeLocationName(lastCheckInLocation);
  }

  function shouldAttemptAutomaticOutOfRangeCheckout(locationPayload, remoteState) {
    if (!locationPayload || locationPayload.status !== 'outside_workplace') {
      return false;
    }
    return resolveLastRecordedAction(remoteState) === 'checkin';
  }

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
