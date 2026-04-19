package com.br.checkingnative.data.local.repository

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.br.checkingnative.data.legacy.LegacyFlutterStorageContract
import com.br.checkingnative.domain.model.ManagedLocation
import com.br.checkingnative.domain.model.ManagedLocationCoordinate
import java.io.File
import java.time.Instant
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class ManagedLocationCacheRepositoryTest {
    @get:Rule
    val temporaryFolder: TemporaryFolder = TemporaryFolder()

    @Test
    fun saveAndReadLocations_preservesLegacyCacheShape() = runBlocking {
        val repository = ManagedLocationCacheRepository(
            createDataStore("locations_cache.preferences_pb"),
        )

        repository.saveLocations(listOf(buildLocation()))

        val restored = repository.readLocations()
        assertEquals(1, restored.size)
        assertEquals("Base P80", restored.first().local)
        assertEquals(2, restored.first().coordinates.size)
        assertEquals(45, restored.first().toleranceMeters)
    }

    @Test
    fun readLocations_returnsEmptyListForMalformedCache() = runBlocking {
        val dataStore = createDataStore("locations_malformed.preferences_pb")
        dataStore.edit { preferences ->
            preferences[stringPreferencesKey(LegacyFlutterStorageContract.locationsCachePrefsKey)] =
                "{invalid-json"
        }
        val repository = ManagedLocationCacheRepository(dataStore)

        assertTrue(repository.readLocations().isEmpty())
    }

    private fun createDataStore(fileName: String): DataStore<Preferences> {
        val file = File(temporaryFolder.root, fileName)
        return PreferenceDataStoreFactory.create(
            scope = CoroutineScope(SupervisorJob() + Dispatchers.IO),
            produceFile = { file },
        )
    }
}

private fun buildLocation(): ManagedLocation {
    return ManagedLocation(
        id = 10,
        local = "Base P80",
        latitude = -22.9,
        longitude = -43.1,
        coordinates = listOf(
            ManagedLocationCoordinate(latitude = -22.9, longitude = -43.1),
            ManagedLocationCoordinate(latitude = -22.91, longitude = -43.11),
        ),
        toleranceMeters = 45,
        updatedAt = Instant.parse("2026-04-18T00:00:00Z"),
    )
}
