package com.br.checkingnative

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.br.checkingnative.data.legacy.LegacyFlutterStorageContract
import com.br.checkingnative.data.local.db.CheckingDatabase
import com.br.checkingnative.data.local.db.ManagedLocationEntity
import java.time.Instant
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CheckingDatabaseInstrumentedTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()
    private val openedDatabases = mutableListOf<CheckingDatabase>()
    private val databaseNames = mutableListOf<String>()

    @After
    fun tearDown() {
        openedDatabases.forEach { database -> database.close() }
        databaseNames.forEach { name -> context.deleteDatabase(name) }
    }

    @Test
    fun dao_replaceAllAndLoadSnapshot_usesRealRoomDatabase() = runBlocking {
        val database = Room.inMemoryDatabaseBuilder(
            context,
            CheckingDatabase::class.java,
        )
            .allowMainThreadQueries()
            .build()
            .also(openedDatabases::add)

        database.managedLocationDao().replaceAll(
            listOf(
                ManagedLocationEntity(
                    id = 2,
                    local = "Base B",
                    latitude = 1.0,
                    longitude = 2.0,
                    coordinatesJson = """[{"latitude":1.0,"longitude":2.0}]""",
                    toleranceMeters = 150,
                    updatedAt = "2026-04-19T08:00:00Z",
                ),
                ManagedLocationEntity(
                    id = 1,
                    local = "Base A",
                    latitude = 3.0,
                    longitude = 4.0,
                    coordinatesJson = null,
                    toleranceMeters = 200,
                    updatedAt = "2026-04-19T09:00:00Z",
                ),
            ),
        )

        val loaded = database.managedLocationDao().loadAllSnapshot()

        assertEquals(listOf("Base A", "Base B"), loaded.map { item -> item.local })
        assertEquals(2, loaded.size)
    }

    @Test
    fun migration1To2_addsCoordinatesColumnAndPreservesLegacyRows() = runBlocking {
        val databaseName = "legacy_locations_${System.nanoTime()}.db"
        databaseNames += databaseName
        context.deleteDatabase(databaseName)
        context.openOrCreateDatabase(databaseName, Context.MODE_PRIVATE, null).use { database ->
            database.execSQL(
                """
                    CREATE TABLE ${LegacyFlutterStorageContract.locationsTableName} (
                        id INTEGER NOT NULL PRIMARY KEY,
                        local TEXT NOT NULL,
                        latitude REAL NOT NULL,
                        longitude REAL NOT NULL,
                        tolerance_meters INTEGER NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """.trimIndent(),
            )
            database.execSQL(
                """
                    INSERT INTO ${LegacyFlutterStorageContract.locationsTableName}
                    (id, local, latitude, longitude, tolerance_meters, updated_at)
                    VALUES (7, 'Base Legada', 1.249494, 103.614345, 150, '2026-04-15T07:00:00Z')
                """.trimIndent(),
            )
            database.version = 1
        }

        val roomDatabase = Room.databaseBuilder(
            context,
            CheckingDatabase::class.java,
            databaseName,
        )
            .addMigrations(CheckingDatabase.MIGRATION_1_2)
            .allowMainThreadQueries()
            .build()
            .also(openedDatabases::add)

        val loaded = roomDatabase.managedLocationDao().loadAllSnapshot()
        val tableInfo = roomDatabase.openHelper.readableDatabase
            .query("PRAGMA table_info(${LegacyFlutterStorageContract.locationsTableName})")
            .use { cursor ->
                val nameIndex = cursor.getColumnIndex("name")
                generateSequence {
                    if (cursor.moveToNext()) cursor.getString(nameIndex) else null
                }.toList()
            }

        assertTrue(tableInfo.contains("coordinates_json"))
        assertEquals(1, loaded.size)
        assertEquals("Base Legada", loaded.single().local)
        assertEquals(Instant.parse("2026-04-15T07:00:00Z").toString(), loaded.single().updatedAt)
        assertTrue(roomDatabase.isOpen)
    }
}
