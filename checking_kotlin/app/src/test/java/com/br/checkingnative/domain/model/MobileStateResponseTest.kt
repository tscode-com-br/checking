package com.br.checkingnative.domain.model

import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MobileStateResponseTest {
    @Test
    fun fromJsonObject_parsesSubmitResponseAndNestedState() {
        val payload = JsonParser.parseString(
            """
                {
                  "ok": true,
                  "duplicate": false,
                  "queued_forms": true,
                  "message": "Operacao processada.",
                  "state": {
                    "found": true,
                    "chave": "AB12",
                    "nome": "Usuario Teste",
                    "projeto": "P80",
                    "current_action": "checkin",
                    "current_event_time": "2026-04-18T08:30:00Z",
                    "current_local": "Base Sul",
                    "last_checkin_at": "2026-04-18T08:30:00Z",
                    "last_checkout_at": "2026-04-18T17:00:00Z"
                  }
                }
            """.trimIndent(),
        ).asJsonObject

        val response = MobileSubmitResponse.fromJsonObject(payload)

        assertTrue(response.ok)
        assertEquals("Operacao processada.", response.message)
        assertTrue(response.state.found)
        assertEquals("AB12", response.state.chave)
        assertEquals("Base Sul", response.state.currentLocal)
        assertEquals("2026-04-18T08:30:00Z", response.state.currentEventTime.toString())
        assertEquals("2026-04-18T17:00:00Z", response.state.lastCheckOutAt.toString())
    }
}
