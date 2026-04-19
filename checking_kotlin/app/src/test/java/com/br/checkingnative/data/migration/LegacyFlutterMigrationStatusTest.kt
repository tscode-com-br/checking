package com.br.checkingnative.data.migration

import org.junit.Assert.assertEquals
import org.junit.Test

class LegacyFlutterMigrationStatusTest {
    @Test
    fun fromStorageValue_mapsOldBlockedValueToManualOnboarding() {
        val restored = LegacyFlutterMigrationStatus.fromStorageValue(
            "automatic_import_blocked",
        )

        assertEquals(LegacyFlutterMigrationStatus.MANUAL_ONBOARDING_REQUIRED, restored)
    }
}
