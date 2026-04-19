package com.br.checkingnative.data.preferences

import com.br.checkingnative.data.migration.LegacyFlutterMigrationReport
import com.br.checkingnative.domain.model.CheckingState
import kotlinx.coroutines.flow.Flow

interface CheckingStateStore {
    val storageSnapshot: Flow<CheckingStateStorageSnapshot>

    suspend fun ensureSeededState()

    suspend fun saveState(state: CheckingState)

    suspend fun markInitialAndroidSetupPrompted()

    suspend fun updateLegacyMigrationReport(report: LegacyFlutterMigrationReport)
}
