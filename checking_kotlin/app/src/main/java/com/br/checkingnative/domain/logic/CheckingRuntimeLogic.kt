package com.br.checkingnative.domain.logic

import com.br.checkingnative.domain.model.CheckingPermissionSettingsState
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.ManagedLocation
import java.time.Instant

object CheckingRuntimeLogic {
    fun shouldRefreshLocationTrackingAfterSubmit(state: CheckingState): Boolean {
        return state.locationSharingEnabled &&
            (state.hasAnyLocationAutomation || state.nightModeAfterCheckoutEnabled)
    }

    fun isLocationSharingToggleInteractive(state: CheckingState): Boolean {
        return (state.locationSharingEnabled || state.canEnableLocationSharing) &&
            !state.isLocationUpdating &&
            !state.isAutomaticCheckingUpdating
    }

    fun shouldRunBackgroundLocationService(
        state: CheckingState,
        backgroundServiceSupported: Boolean,
        referenceTime: Instant? = null,
    ): Boolean {
        return backgroundServiceSupported &&
            state.locationSharingEnabled &&
            state.hasAnyLocationAutomation &&
            CheckingLocationLogic.shouldRunBackgroundActivityNow(
                state = state,
                referenceTime = referenceTime,
            )
    }

    fun shouldRunForegroundLocationStream(
        state: CheckingState,
        backgroundServiceSupported: Boolean,
        referenceTime: Instant? = null,
    ): Boolean {
        return state.locationSharingEnabled &&
            !shouldRunBackgroundLocationService(
                state = state,
                backgroundServiceSupported = backgroundServiceSupported,
                referenceTime = referenceTime,
            )
    }

    fun reconcilePermissionBackedSwitches(
        state: CheckingState,
        canEnableLocationSharing: Boolean,
    ): CheckingState {
        val locationSharingEnabled = if (canEnableLocationSharing) {
            state.locationSharingEnabled
        } else {
            false
        }
        val oemBackgroundSetupEnabled = if (canEnableLocationSharing) {
            state.oemBackgroundSetupEnabled
        } else {
            false
        }

        return state.copy(
            canEnableLocationSharing = canEnableLocationSharing,
            isLocationUpdating = false,
            locationSharingEnabled = locationSharingEnabled,
            oemBackgroundSetupEnabled = oemBackgroundSetupEnabled,
            lastMatchedLocation = if (locationSharingEnabled) state.lastMatchedLocation else null,
        )
    }

    fun isConfiguredToKeepRunningInBackground(
        state: CheckingState,
        permissionSettings: CheckingPermissionSettingsState,
        backgroundServiceSupported: Boolean,
        referenceTime: Instant? = null,
    ): Boolean {
        return permissionSettings.backgroundAccessEnabled &&
            permissionSettings.notificationsEnabled &&
            shouldRunBackgroundLocationService(
                state = state,
                backgroundServiceSupported = backgroundServiceSupported,
                referenceTime = referenceTime,
            )
    }

    fun resolveControlFlagAfterSnapshot(
        currentValue: Boolean,
        snapshotLocationSharingEnabled: Boolean,
    ): Boolean {
        return if (snapshotLocationSharingEnabled) currentValue else false
    }

    fun isAutomaticCheckingEnabledInUi(state: CheckingState): Boolean {
        return state.locationSharingEnabled && state.automaticCheckInOutEnabled
    }

    fun isAutomaticCheckingToggleInteractive(state: CheckingState): Boolean {
        return state.locationSharingEnabled &&
            !state.isLocationUpdating &&
            !state.isAutomaticCheckingUpdating
    }

    fun isNightModeAfterCheckoutActive(
        state: CheckingState,
        referenceTime: Instant? = null,
    ): Boolean {
        return CheckingLocationLogic.isNightModeAfterCheckoutActive(
            state = state,
            referenceTime = referenceTime,
        )
    }

    fun isRegisterActionInteractive(
        state: CheckingState,
        referenceTime: Instant? = null,
    ): Boolean {
        return !state.isSubmitting &&
            !CheckingLocationLogic.isNightModeAfterCheckoutActive(
                state = state,
                referenceTime = referenceTime,
            )
    }

    fun resolveManagedLocationForLastCapture(
        managedLocations: List<ManagedLocation>,
        lastMatchedLocation: String?,
        lastDetectedLocation: String?,
    ): ManagedLocation? {
        val normalizedDetectedLocation = normalizeLocationLookup(lastDetectedLocation)
        if (normalizedDetectedLocation != null) {
            for (location in managedLocations) {
                if (normalizeLocationLookup(location.local) == normalizedDetectedLocation) {
                    return location
                }
            }
        }

        val normalizedMatchedLocation = normalizeLocationLookup(lastMatchedLocation) ?: return null
        for (location in managedLocations) {
            if (
                normalizeLocationLookup(location.automationAreaLabel) == normalizedMatchedLocation ||
                normalizeLocationLookup(location.local) == normalizedMatchedLocation
            ) {
                return location
            }
        }

        return null
    }

    private fun normalizeLocationLookup(value: String?): String? {
        val normalized = value?.trim()?.lowercase()?.replace(Regex("\\s+"), " ")
        return normalized?.takeIf { item -> item.isNotEmpty() }
    }
}
