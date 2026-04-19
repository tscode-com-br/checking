package com.br.checkingnative.data.preferences

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.stringPreferencesKey
import com.br.checkingnative.data.migration.LegacyFlutterMigrationReport
import com.br.checkingnative.data.migration.LegacyFlutterMigrationStatus
import com.br.checkingnative.domain.model.CheckingState
import java.io.File
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class CheckingStateRepositoryTest {
    @get:Rule
    val temporaryFolder: TemporaryFolder = TemporaryFolder()

    @Test
    fun ensureSeededState_createsInitialSnapshotWithoutLoadingFlag() = runBlocking {
        val repository = CheckingStateRepository(createDataStore("state_seed.preferences_pb"))

        repository.ensureSeededState()

        val snapshot = repository.storageSnapshot.first()
        assertTrue(snapshot.hasPersistedState)
        assertFalse(snapshot.state.isLoading)
        assertEquals(CheckingState.initial().apiBaseUrl, snapshot.state.apiBaseUrl)
    }

    @Test
    fun saveState_keepsSharedKeyOutsidePersistedStateJson() = runBlocking {
        val dataStore = createDataStore("state_secret.preferences_pb")
        val repository = CheckingStateRepository(dataStore)

        repository.saveState(
            CheckingState.initial().copy(
                chave = "AB12",
                apiSharedKey = "mobile-secret",
                isLoading = false,
            ),
        )

        val preferences = dataStore.data.first()
        val stateJson = preferences[stringPreferencesKey("checking_state_json")].orEmpty()
        val snapshot = repository.storageSnapshot.first()

        assertTrue(stateJson.contains("\"chave\":\"AB12\""))
        assertFalse(stateJson.contains("mobile-secret"))
        assertEquals("mobile-secret", snapshot.state.apiSharedKey)
    }

    @Test
    fun updateLegacyMigrationReport_persistsManualOnboardingStatus() = runBlocking {
        val repository = CheckingStateRepository(createDataStore("migration.preferences_pb"))

        repository.updateLegacyMigrationReport(
            LegacyFlutterMigrationReport(
                status = LegacyFlutterMigrationStatus.MANUAL_ONBOARDING_REQUIRED,
                message = "Onboarding manual registrado.",
                sourceAppInstalled = true,
            ),
        )

        val snapshot = repository.storageSnapshot.first()
        assertEquals(
            LegacyFlutterMigrationStatus.MANUAL_ONBOARDING_REQUIRED,
            snapshot.legacyMigrationStatus,
        )
        assertEquals("Onboarding manual registrado.", snapshot.legacyMigrationMessage)
        assertTrue(snapshot.legacySourceInstalled)
    }

    private fun createDataStore(fileName: String): DataStore<Preferences> {
        val file = File(temporaryFolder.root, fileName)
        return PreferenceDataStoreFactory.create(
            scope = CoroutineScope(SupervisorJob() + Dispatchers.IO),
            produceFile = { file },
        )
    }
}
