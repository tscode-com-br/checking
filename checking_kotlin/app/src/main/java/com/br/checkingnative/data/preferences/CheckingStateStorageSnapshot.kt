package com.br.checkingnative.data.preferences

import com.br.checkingnative.data.migration.LegacyFlutterMigrationStatus
import com.br.checkingnative.domain.model.CheckingState

data class CheckingStateStorageSnapshot(
    val state: CheckingState = CheckingState.initial().copy(isLoading = false),
    val hasPersistedState: Boolean = false,
    val hasPromptedInitialAndroidSetup: Boolean = false,
    val legacyMigrationStatus: LegacyFlutterMigrationStatus =
        LegacyFlutterMigrationStatus.NOT_STARTED,
    val legacyMigrationMessage: String =
        "A verificacao da migracao legada ainda nao foi executada.",
    val legacySourceInstalled: Boolean = false,
)
