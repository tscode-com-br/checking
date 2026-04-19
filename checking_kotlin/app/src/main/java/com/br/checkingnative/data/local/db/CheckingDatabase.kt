package com.br.checkingnative.data.local.db

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.br.checkingnative.data.legacy.LegacyFlutterStorageContract

@Database(
    entities = [ManagedLocationEntity::class],
    version = 2,
    exportSchema = false,
)
abstract class CheckingDatabase : RoomDatabase() {
    abstract fun managedLocationDao(): ManagedLocationDao

    companion object {
        val MIGRATION_1_2: Migration = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                val tableName = LegacyFlutterStorageContract.locationsTableName
                val hasCoordinatesColumn = db.query("PRAGMA table_info($tableName)").use { cursor ->
                    val nameIndex = cursor.getColumnIndex("name")
                    if (nameIndex < 0) {
                        return@use false
                    }

                    var found = false
                    while (cursor.moveToNext()) {
                        if (cursor.getString(nameIndex) == "coordinates_json") {
                            found = true
                            break
                        }
                    }
                    found
                }

                if (!hasCoordinatesColumn) {
                    db.execSQL("ALTER TABLE $tableName ADD COLUMN coordinates_json TEXT")
                }
            }
        }
    }
}
