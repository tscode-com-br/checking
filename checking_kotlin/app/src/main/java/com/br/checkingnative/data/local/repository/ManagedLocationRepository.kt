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
) {
    val locationCount: Flow<Int> = dao.observeLocationCount()

    val locations: Flow<List<ManagedLocation>> =
        dao.observeAll().map { items ->
            items.map(ManagedLocationEntity::toDomainModel)
        }

    suspend fun replaceAll(items: List<ManagedLocation>) {
        dao.clearAll()
        if (items.isNotEmpty()) {
            dao.upsertAll(items.map(ManagedLocation::toEntity))
        }
    }
}
