package com.br.checkingnative.domain.model

import java.time.Instant
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CheckingStateTest {
    @Test
    fun fromPersistedJsonString_restoresLegacyStateAndSanitizesFields() {
        val raw = """
            {
              "chave": " ab12 ",
              "registro": "checkOut",
              "informe": "retroativo",
              "projeto": "p82",
              "locationSharingEnabled": true,
              "nightModeAfterCheckoutEnabled": true,
              "nightModeAfterCheckoutUntil": "2026-04-18T00:00:00Z",
              "locationFetchHistory": [
                {
                  "timestamp": "2026-04-18T10:00:00Z",
                  "latitude": -22.9,
                  "longitude": -43.1
                },
                {
                  "timestamp": "2026-04-18T10:00:00.500Z",
                  "latitude": -22.9,
                  "longitude": -43.1
                }
              ]
            }
        """.trimIndent()

        val state = CheckingState.fromPersistedJsonString(
            raw = raw,
            resolvedSharedKey = "secret-key",
        )

        assertEquals("AB12", state.chave)
        assertEquals(RegistroType.CHECK_OUT, state.registro)
        assertEquals(InformeType.NORMAL, state.checkInInforme)
        assertEquals(InformeType.RETROATIVO, state.checkOutInforme)
        assertEquals(ProjetoType.P82, state.checkInProjeto)
        assertTrue(state.locationSharingEnabled)
        assertTrue(state.autoCheckInEnabled)
        assertTrue(state.autoCheckOutEnabled)
        assertEquals(1, state.locationFetchHistory.size)
        assertEquals("secret-key", state.apiSharedKey)
        assertFalse(state.isLoading)
    }

    @Test
    fun fromPersistedJsonString_restoresScheduleSettingsAndOemFlag() {
        val state = CheckingState.fromPersistedJsonString(
            raw = """
                {
                  "locationUpdateIntervalSeconds": 2700,
                  "nightUpdatesDisabled": true,
                  "nightPeriodStartMinutes": 1380,
                  "nightPeriodEndMinutes": 300,
                  "nightModeAfterCheckoutEnabled": true,
                  "nightModeAfterCheckoutUntil": "2026-04-17T22:00:00Z",
                  "oemBackgroundSetupEnabled": true
                }
            """.trimIndent(),
        )

        assertEquals(45 * 60, state.locationUpdateIntervalSeconds)
        assertTrue(state.nightUpdatesDisabled)
        assertEquals(23 * 60, state.nightPeriodStartMinutes)
        assertEquals(5 * 60, state.nightPeriodEndMinutes)
        assertTrue(state.nightModeAfterCheckoutEnabled)
        assertEquals(
            Instant.parse("2026-04-17T22:00:00Z"),
            state.nightModeAfterCheckoutUntil,
        )
        assertTrue(state.oemBackgroundSetupEnabled)
    }

    @Test
    fun fromPersistedJsonString_keepsLegacyAutomationFlagsAndTurnsThemOffWithLocationSharing() {
        val legacyEnabled = CheckingState.fromPersistedJsonString(
            raw = """
                {
                  "locationSharingEnabled": true
                }
            """.trimIndent(),
        )
        val explicitlyDisabled = CheckingState.fromPersistedJsonString(
            raw = """
                {
                  "locationSharingEnabled": true,
                  "autoCheckInEnabled": false,
                  "autoCheckOutEnabled": false
                }
            """.trimIndent(),
        )
        val locationSharingOff = CheckingState.fromPersistedJsonString(
            raw = """
                {
                  "locationSharingEnabled": false,
                  "autoCheckInEnabled": true,
                  "autoCheckOutEnabled": true
                }
            """.trimIndent(),
        )

        assertTrue(legacyEnabled.autoCheckInEnabled)
        assertTrue(legacyEnabled.autoCheckOutEnabled)
        assertFalse(explicitlyDisabled.automaticCheckInOutEnabled)
        assertFalse(locationSharingOff.autoCheckInEnabled)
        assertFalse(locationSharingOff.autoCheckOutEnabled)
    }

    @Test
    fun fromPersistedJsonString_restoresLegacyLocationFetchHistoryWithoutCoordinates() {
        val state = CheckingState.fromPersistedJsonString(
            raw = """
                {
                  "locationFetchHistory": ["2026-04-10T07:45:30Z"]
                }
            """.trimIndent(),
        )

        assertEquals(1, state.locationFetchHistory.size)
        assertEquals(
            Instant.parse("2026-04-10T07:45:30Z"),
            state.locationFetchHistory.first().timestamp,
        )
        assertNull(state.locationFetchHistory.first().latitude)
        assertNull(state.locationFetchHistory.first().longitude)
    }

    @Test
    fun fromPersistedJsonString_ignoresPersistedRemoteHistoryTimestamps() {
        val state = CheckingState.fromPersistedJsonString(
            raw = """
                {
                  "chave": "AB12",
                  "lastCheckIn": "2026-04-09T08:00:00Z",
                  "lastCheckOut": "2026-04-09T18:00:00Z"
                }
            """.trimIndent(),
        )

        assertNull(state.lastCheckIn)
        assertNull(state.lastCheckOut)
    }

    @Test
    fun lastRecordedAction_usesTheLatestRemoteTimestamp() {
        val checkedInState = CheckingState.initial().copy(
            lastCheckIn = Instant.parse("2026-04-10T08:00:00Z"),
            lastCheckOut = Instant.parse("2026-04-09T18:00:00Z"),
        )
        val checkedOutState = CheckingState.initial().copy(
            lastCheckIn = Instant.parse("2026-04-09T08:00:00Z"),
            lastCheckOut = Instant.parse("2026-04-10T18:00:00Z"),
        )

        assertEquals(RegistroType.CHECK_IN, checkedInState.lastRecordedAction)
        assertEquals(RegistroType.CHECK_OUT, checkedOutState.lastRecordedAction)
    }

    @Test
    fun toPersistedJsonString_omitsSecretAndTransientFields() {
        val state = CheckingState.initial().copy(
            chave = "AB12",
            apiSharedKey = "hidden-key",
        )

        val encoded = state.toPersistedJsonString()

        assertTrue(encoded.contains("\"chave\":\"AB12\""))
        assertFalse(encoded.contains("hidden-key"))
        assertFalse(encoded.contains("apiSharedKey"))
        assertFalse(encoded.contains("lastCheckIn"))
        assertFalse(encoded.contains("lastCheckOut"))
    }
}
