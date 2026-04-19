package com.br.checkingnative.domain.model

data class CheckingPermissionSnapshot(
    val locationServiceEnabled: Boolean,
    val preciseLocationGranted: Boolean,
    val backgroundAccessEnabled: Boolean,
    val notificationsEnabled: Boolean,
    val batteryOptimizationIgnored: Boolean,
    val backgroundServiceSupported: Boolean = true,
) {
    val canEnableLocationSharing: Boolean
        get() = locationServiceEnabled &&
            preciseLocationGranted &&
            backgroundAccessEnabled &&
            notificationsEnabled &&
            backgroundServiceSupported

    fun toSettingsState(isRefreshing: Boolean = false): CheckingPermissionSettingsState {
        return CheckingPermissionSettingsState(
            backgroundAccessEnabled = backgroundAccessEnabled,
            notificationsEnabled = notificationsEnabled,
            batteryOptimizationIgnored = batteryOptimizationIgnored,
            isRefreshing = isRefreshing,
        )
    }

    companion object {
        fun unsupported(): CheckingPermissionSnapshot {
            return CheckingPermissionSnapshot(
                locationServiceEnabled = true,
                preciseLocationGranted = true,
                backgroundAccessEnabled = true,
                notificationsEnabled = true,
                batteryOptimizationIgnored = true,
                backgroundServiceSupported = false,
            )
        }
    }
}
