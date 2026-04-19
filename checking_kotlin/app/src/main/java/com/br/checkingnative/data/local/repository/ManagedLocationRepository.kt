package com.br.checkingnative.data.local.repository

import com.br.checkingnative.data.local.db.ManagedLocationDao
import com.br.checkingnative.data.local.db.ManagedLocationEntity
import com.br.checkingnative.data.local.db.toDomainModel
import com.br.checkingnative.data.local.db.toEntity
import com.br.checkingnative.domain.model.ManagedLocation
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ManagedLocationRepository @Inject constructor(
    private val dao: ManagedLocationDao,
    private val cacheRepository: ManagedLocationCacheRepository,
) {
    val locationCount: Flow<Int> = dao.observeLocationCount()

    val locations: Flow<List<ManagedLocation>> =
        dao.observeAll().map { items ->
            items.map(ManagedLocationEntity::toDomainModel)
        }

    suspend fun loadLocations(preferCache: Boolean = false): List<ManagedLocation> {
        val preferredCache = if (preferCache) {
            cacheRepository.readLocations()
        } else {
            emptyList()
        }
        if (preferredCache.isNotEmpty()) {
            return preferredCache
        }

        return try {
            val loadedLocations = dao.loadAllSnapshot().map(ManagedLocationEntity::toDomainModel)
            cacheRepository.saveLocations(loadedLocations)
            loadedLocations
        } catch (_: Exception) {
            cacheRepository.readLocations()
        }
    }

    suspend fun replaceAll(items: List<ManagedLocation>) {
        val cacheResult = runCatching {
            cacheRepository.saveLocations(items)
        }
        val databaseResult = runCatching {
            dao.replaceAll(items.map(ManagedLocation::toEntity))
        }

        if (cacheResult.isFailure && databaseResult.isFailure) {
            throw databaseResult.exceptionOrNull()
                ?: cacheResult.exceptionOrNull()
                ?: IllegalStateException("Falha ao atualizar o catalogo local.")
        }
    }
}
