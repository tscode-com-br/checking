package com.br.checkingnative.data.local.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [ManagedLocationEntity::class],
    version = 1,
    exportSchema = false,
)
abstract class CheckingDatabase : RoomDatabase() {
    abstract fun managedLocationDao(): ManagedLocationDao
}

