package com.br.checkingnative.domain.model

data class CheckingPermissionSettingsState(
    val backgroundAccessEnabled: Boolean,
    val notificationsEnabled: Boolean,
    val batteryOptimizationIgnored: Boolean,
    val isRefreshing: Boolean,
    val locationServiceEnabled: Boolean = false,
    val preciseLocationGranted: Boolean = false,
    val backgroundServiceSupported: Boolean = true,
    val backgroundAccessRequiresSettings: Boolean = false,
    val foregroundServiceStartRequiresVisibleApp: Boolean = false,
    val foregroundServiceLocationRequiresRuntimePermission: Boolean = false,
) {
    companion object {
        fun initial(): CheckingPermissionSettingsState {
            return CheckingPermissionSettingsState(
                backgroundAccessEnabled = false,
                notificationsEnabled = false,
                batteryOptimizationIgnored = false,
                isRefreshing = false,
                locationServiceEnabled = false,
                preciseLocationGranted = false,
                backgroundServiceSupported = true,
                backgroundAccessRequiresSettings = false,
                foregroundServiceStartRequiresVisibleApp = false,
                foregroundServiceLocationRequiresRuntimePermission = false,
            )
        }
    }
}
