package com.br.checkingnative.ui.checking

import com.br.checkingnative.domain.model.CheckingPermissionSettingsState
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.CheckingWebAuthState
import com.br.checkingnative.domain.model.ManagedLocation

data class CheckingUiState(
    val state: CheckingState = CheckingState.initial(),
    val webAuth: CheckingWebAuthState = CheckingWebAuthState.initial(),
    val permissionSettings: CheckingPermissionSettingsState =
        CheckingPermissionSettingsState.initial(),
    val managedLocations: List<ManagedLocation> = emptyList(),
    val initialized: Boolean = false,
    val hasPromptedInitialAndroidSetup: Boolean = false,
    val hasHydratedHistoryForCurrentKey: Boolean = false,
    val foregroundRefreshInProgress: Boolean = false,
) {
    val managedLocationCount: Int
        get() = managedLocations.size
}
