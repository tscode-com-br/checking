package com.br.checkingnative.data.local.repository

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import com.br.checkingnative.data.local.db.ManagedLocationDao
import com.br.checkingnative.data.local.db.ManagedLocationEntity
import com.br.checkingnative.data.local.db.toDomainModel
import com.br.checkingnative.data.local.db.toEntity
import com.br.checkingnative.domain.model.ManagedLocation
import com.br.checkingnative.domain.model.ManagedLocationCoordinate
import java.io.File
import java.time.Instant
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class ManagedLocationRepositoryTest {
    @get:Rule
    val temporaryFolder: TemporaryFolder = TemporaryFolder()

    @Test
    fun loadLocations_refreshesCacheFromDatabase() = runBlocking {
        val dao = FakeManagedLocationDao()
        val cacheRepository = createCacheRepository("repository_refresh.preferences_pb")
        val repository = ManagedLocationRepository(dao, cacheRepository)
        dao.replaceAll(listOf(buildRepositoryLocation(id = 1).toEntity()))

        val loaded = repository.loadLocations()

        assertEquals(1, loaded.size)
        assertEquals("Base 1", loaded.first().local)
        assertEquals(loaded, cacheRepository.readLocations())
    }

    @Test
    fun loadLocations_fallsBackToCacheWhenDatabaseFails() = runBlocking {
        val dao = FakeManagedLocationDao()
        val cacheRepository = createCacheRepository("repository_fallback.preferences_pb")
        val repository = ManagedLocationRepository(dao, cacheRepository)
        val cachedLocation = buildRepositoryLocation(id = 2)
        cacheRepository.saveLocations(listOf(cachedLocation))
        dao.loadFailure = IllegalStateException("database unavailable")

        val loaded = repository.loadLocations()

        assertEquals(listOf(cachedLocation), loaded)
    }

    @Test
    fun replaceAll_keepsCacheWhenDatabaseReplaceFails() = runBlocking {
        val dao = FakeManagedLocationDao()
        val cacheRepository = createCacheRepository("repository_replace.preferences_pb")
        val repository = ManagedLocationRepository(dao, cacheRepository)
        val location = buildRepositoryLocation(id = 3)
        dao.replaceFailure = IllegalStateException("database write failed")

        repository.replaceAll(listOf(location))

        assertEquals(listOf(location), cacheRepository.readLocations())
        assertTrue(dao.loadAllSnapshot().isEmpty())
    }

    private fun createCacheRepository(fileName: String): ManagedLocationCacheRepository {
        return ManagedLocationCacheRepository(createDataStore(fileName))
    }

    private fun createDataStore(fileName: String): DataStore<Preferences> {
        val file = File(temporaryFolder.root, fileName)
        return PreferenceDataStoreFactory.create(
            scope = CoroutineScope(SupervisorJob() + Dispatchers.IO),
            produceFile = { file },
        )
    }
}

private class FakeManagedLocationDao : ManagedLocationDao {
    private val storedItems = MutableStateFlow<List<ManagedLocationEntity>>(emptyList())

    var loadFailure: RuntimeException? = null
    var replaceFailure: RuntimeException? = null

    override fun observeLocationCount(): Flow<Int> {
        return storedItems.map { items -> items.size }
    }

    override fun observeAll(): Flow<List<ManagedLocationEntity>> = storedItems

    override suspend fun loadAllSnapshot(): List<ManagedLocationEntity> {
        loadFailure?.let { error -> throw error }
        return sortEntities(storedItems.value)
    }

    override suspend fun upsertAll(items: List<ManagedLocationEntity>) {
        val byId = storedItems.value.associateBy { item -> item.id }.toMutableMap()
        items.forEach { item -> byId[item.id] = item }
        storedItems.value = sortEntities(byId.values.toList())
    }

    override suspend fun clearAll() {
        storedItems.value = emptyList()
    }

    override suspend fun replaceAll(items: List<ManagedLocationEntity>) {
        replaceFailure?.let { error -> throw error }
        storedItems.value = sortEntities(items)
    }

    private fun sortEntities(items: List<ManagedLocationEntity>): List<ManagedLocationEntity> {
        return items.sortedWith(
            compareBy<ManagedLocationEntity> { item -> item.local.lowercase() }
                .thenBy { item -> item.id },
        )
    }
}

private fun buildRepositoryLocation(id: Int): ManagedLocation {
    return ManagedLocation(
        id = id,
        local = "Base $id",
        latitude = -22.0 - id,
        longitude = -43.0 - id,
        coordinates = listOf(
            ManagedLocationCoordinate(latitude = -22.0 - id, longitude = -43.0 - id),
        ),
        toleranceMeters = 30 + id,
        updatedAt = Instant.parse("2026-04-18T00:00:00Z"),
    )
}
