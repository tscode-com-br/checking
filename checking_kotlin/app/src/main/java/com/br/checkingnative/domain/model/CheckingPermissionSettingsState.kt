package com.br.checkingnative.domain.model

data class CheckingPermissionSettingsState(
    val backgroundAccessEnabled: Boolean,
    val notificationsEnabled: Boolean,
    val batteryOptimizationIgnored: Boolean,
    val isRefreshing: Boolean,
) {
    companion object {
        fun initial(): CheckingPermissionSettingsState {
            return CheckingPermissionSettingsState(
                backgroundAccessEnabled = false,
                notificationsEnabled = false,
                batteryOptimizationIgnored = false,
                isRefreshing = false,
            )
        }
    }
}
