(function (root, factory) {
  const exported = factory();

  if (typeof module === 'object' && module.exports) {
    module.exports = exported;
  }

  root.CheckingWebAutomaticActivities = exported;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const AUTOMATIC_CHECKOUT_DISTANCE_METERS = 2000;
  const AUTOMATIC_CHECKOUT_LOCATION = 'Fora do Local de Trabalho';
  const AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION = 'Localização não Cadastrada';

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

  function resolveAutomaticCheckInLocation(locationPayload) {
    const resolvedLocal = String(locationPayload && locationPayload.resolved_local || '').trim();
    if (resolvedLocal) {
      return resolvedLocal;
    }

    const fallbackLabel = String(locationPayload && locationPayload.label || '').trim();
    if (fallbackLabel) {
      return fallbackLabel;
    }

    return AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION;
  }

  function shouldAttemptAutomaticLocationEvent(locationPayload, remoteState) {
    const resolvedLocal = locationPayload && locationPayload.resolved_local;
    const lastRecordedAction = resolveLastRecordedAction(remoteState);
    const currentRecordedLocation = resolveCurrentRecordedLocation(remoteState);
    const lastCheckInLocation = resolveRecordedCheckInLocation(remoteState);

    if (isCheckoutZoneLocationName(resolvedLocal)) {
      return lastRecordedAction === 'checkin';
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
    const nearestDistanceMeters = Number(locationPayload && locationPayload.nearest_workplace_distance_meters);
    if (!Number.isFinite(nearestDistanceMeters) || nearestDistanceMeters <= AUTOMATIC_CHECKOUT_DISTANCE_METERS) {
      return false;
    }
    return resolveLastRecordedAction(remoteState) === 'checkin';
  }

  function shouldAttemptAutomaticNearbyWorkplaceCheckIn(locationPayload, remoteState) {
    if (!locationPayload || locationPayload.matched || locationPayload.status !== 'not_in_known_location') {
      return false;
    }

    if (resolveLastRecordedAction(remoteState) !== 'checkout') {
      return false;
    }

    return normalizeLocationName(resolveAutomaticCheckInLocation(locationPayload))
      !== normalizeLocationName(resolveCurrentRecordedLocation(remoteState));
  }

  return {
    AUTOMATIC_CHECKOUT_DISTANCE_METERS,
    AUTOMATIC_CHECKOUT_LOCATION,
    AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION,
    normalizeLocationName,
    isCheckoutZoneLocationName,
    resolveLastRecordedAction,
    resolveRecordedCheckInLocation,
    resolveAutomaticCheckInLocation,
    shouldAttemptAutomaticLocationEvent,
    shouldAttemptAutomaticOutOfRangeCheckout,
    shouldAttemptAutomaticNearbyWorkplaceCheckIn,
  };
});