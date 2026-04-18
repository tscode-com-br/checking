package com.br.checkingnative.domain.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
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
