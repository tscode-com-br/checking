package com.br.checkingnative.data.local.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.br.checkingnative.data.legacy.LegacyFlutterStorageContract
import kotlinx.coroutines.flow.Flow

@Dao
interface ManagedLocationDao {
    @Query("SELECT COUNT(*) FROM ${LegacyFlutterStorageContract.locationsTableName}")
    fun observeLocationCount(): Flow<Int>

    @Query(
        "SELECT * FROM ${LegacyFlutterStorageContract.locationsTableName} " +
            "ORDER BY local COLLATE NOCASE ASC, id ASC",
    )
    fun observeAll(): Flow<List<ManagedLocationEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(items: List<ManagedLocationEntity>)

    @Query("DELETE FROM ${LegacyFlutterStorageContract.locationsTableName}")
    suspend fun clearAll()
}
