package com.br.checkingnative.domain.logic

import com.br.checkingnative.domain.model.CheckingPermissionSettingsState
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.ManagedLocation
import java.time.Instant

data class CheckingAndroidLimitationGuidance(
    val title: String,
    val message: String,
    val blocking: Boolean,
)

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
            CheckingLocationLogic.shouldRunBackgroundActivityNow(
                state = state,
                referenceTime = referenceTime,
            ) &&
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

    fun resolveAndroidLimitationGuidance(
        state: CheckingState,
        permissionSettings: CheckingPermissionSettingsState,
    ): CheckingAndroidLimitationGuidance {
        return when {
            !permissionSettings.locationServiceEnabled -> CheckingAndroidLimitationGuidance(
                title = "Localização do Android",
                message = "Ative o serviço de localização do aparelho antes de iniciar o monitoramento.",
                blocking = true,
            )
            !permissionSettings.preciseLocationGranted -> CheckingAndroidLimitationGuidance(
                title = "Localização precisa",
                message = "Permita localização precisa; coordenadas aproximadas não são suficientes para validar os locais cadastrados.",
                blocking = true,
            )
            !permissionSettings.backgroundAccessEnabled &&
                permissionSettings.backgroundAccessRequiresSettings ->
                CheckingAndroidLimitationGuidance(
                    title = "Permitir o tempo todo",
                    message = "Neste Android, a permissão de localização em segundo plano precisa ser liberada na tela de configurações do app.",
                    blocking = true,
                )
            !permissionSettings.backgroundAccessEnabled -> CheckingAndroidLimitationGuidance(
                title = "Localização em segundo plano",
                message = "Permita acesso à localização em segundo plano para que o app continue capturando coordenadas fechado.",
                blocking = true,
            )
            !permissionSettings.notificationsEnabled -> CheckingAndroidLimitationGuidance(
                title = "Notificação persistente",
                message = "Permita notificações; o serviço de localização em segundo plano depende de uma notificação fixa.",
                blocking = true,
            )
            !state.locationSharingEnabled -> CheckingAndroidLimitationGuidance(
                title = "Monitoramento desligado",
                message = "Ative a busca por coordenadas para iniciar o serviço nativo enquanto o app está aberto.",
                blocking = true,
            )
            !state.hasAnyLocationAutomation -> CheckingAndroidLimitationGuidance(
                title = "Automação desligada",
                message = "Ative check-in/check-out automático para que o serviço envie eventos sem trazer o app para primeiro plano.",
                blocking = true,
            )
            permissionSettings.foregroundServiceStartRequiresVisibleApp ->
                CheckingAndroidLimitationGuidance(
                    title = "Ativação pelo app aberto",
                    message = "Neste Android, o serviço deve ser iniciado enquanto o app está aberto; depois a notificação persistente mantém o monitoramento.",
                    blocking = false,
                )
            permissionSettings.foregroundServiceLocationRequiresRuntimePermission ->
                CheckingAndroidLimitationGuidance(
                    title = "Foreground service de localização",
                    message = "Neste Android, o serviço só inicia com as permissões de localização já concedidas.",
                    blocking = false,
                )
            else -> CheckingAndroidLimitationGuidance(
                title = "Pronto para segundo plano",
                message = "Permissões essenciais liberadas. Mantenha a bateria sem restrição para reduzir pausas do fabricante.",
                blocking = false,
            )
        }
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
