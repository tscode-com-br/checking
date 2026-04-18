package com.br.checkingnative.domain.model

import com.br.checkingnative.data.local.db.ManagedLocationEntity
import com.br.checkingnative.data.local.db.toDomainModel
import com.br.checkingnative.data.local.db.toEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ManagedLocationTest {
    @Test
    fun entityRoundTrip_preservesLegacySchemaAndCheckoutZoneBehavior() {
        val entity = ManagedLocationEntity(
            id = 7,
            local = "Zona de CheckOut 2",
            latitude = -22.9,
            longitude = -43.1,
            coordinatesJson = """
                [
                  {"latitude": -22.9, "longitude": -43.1},
                  {"latitude": -22.91, "longitude": -43.11}
                ]
            """.trimIndent(),
            toleranceMeters = 35,
            updatedAt = "2026-04-18T00:00:00Z",
        )

        val location = entity.toDomainModel()
        val encodedEntity = location.toEntity()

        assertTrue(location.isCheckoutZone)
        assertEquals("Zona de CheckOut", location.automationAreaLabel)
        assertTrue(location.matchesLocationName("  zona   de checkout   2 "))
        assertEquals(2, location.coordinates.size)
        assertEquals(entity.id, encodedEntity.id)
        assertEquals(entity.local, encodedEntity.local)
        assertEquals(entity.toleranceMeters, encodedEntity.toleranceMeters)
    }
}
