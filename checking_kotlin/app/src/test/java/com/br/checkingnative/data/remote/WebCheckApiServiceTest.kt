package com.br.checkingnative.data.remote

import com.br.checkingnative.data.preferences.WebSessionSnapshot
import com.br.checkingnative.data.preferences.WebSessionStore
import com.br.checkingnative.domain.model.InformeType
import com.br.checkingnative.domain.model.RegistroType
import com.br.checkingnative.domain.model.WebCheckSubmitRequest
import com.br.checkingnative.domain.model.WebLocationMatchRequest
import com.br.checkingnative.domain.model.WebPasswordLoginRequest
import com.br.checkingnative.domain.model.WebTransportRequestCreate
import com.google.gson.JsonParser
import java.io.IOException
import java.time.Instant
import java.time.LocalDate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class WebCheckApiServiceTest {
    @Test
    fun login_savesSessionCookieAndAuthenticatedRequestsSendCookie() = runBlocking {
        val transport = FakeWebCheckingHttpTransport().apply {
            enqueueResponse(
                statusCode = 200,
                body = """
                    {
                      "ok": true,
                      "authenticated": true,
                      "has_password": true,
                      "message": "Autenticacao concluida."
                    }
                """.trimIndent(),
                headers = mapOf(
                    "Set-Cookie" to listOf(
                        "session=abc123; path=/; httponly; samesite=lax",
                    ),
                ),
            )
            enqueueResponse(
                statusCode = 200,
                body = """
                    {
                      "found": true,
                      "chave": "AB12",
                      "projeto": "P80",
                      "current_action": "checkin",
                      "current_local": "Base Sul",
                      "has_current_day_checkin": true,
                      "last_checkin_at": "2026-04-20T01:00:00Z"
                    }
                """.trimIndent(),
            )
        }
        val sessionStore = FakeWebSessionStore()
        val service = WebCheckApiService(transport, sessionStore)

        val login = service.login(
            baseUrl = "https://tscode.com.br",
            request = WebPasswordLoginRequest(
                chave = "AB12",
                senha = "123",
            ),
        )
        val history = service.fetchCheckState(
            baseUrl = "https://tscode.com.br",
            chave = "AB12",
        )

        assertTrue(login.authenticated)
        assertEquals("session=abc123", sessionStore.webSessionSnapshot.value.cookieHeader)
        assertEquals("POST", transport.requests[0].method)
        assertEquals("https://tscode.com.br/api/web/auth/login", transport.requests[0].url)
        assertEquals(
            "https://tscode.com.br/api/web/check/state?chave=AB12",
            transport.requests[1].url,
        )
        assertEquals("session=abc123", transport.requests[1].headers["Cookie"])
        assertTrue(history.found)
        assertEquals("Base Sul", history.currentLocal)
    }

    @Test
    fun submitCheck_usesWebEndpointAndPayloadShape() = runBlocking {
        val transport = FakeWebCheckingHttpTransport().apply {
            enqueueResponse(
                statusCode = 200,
                body = """
                    {
                      "ok": true,
                      "duplicate": false,
                      "queued_forms": true,
                      "message": "Check-In concluido.",
                      "state": {
                        "found": true,
                        "chave": "AB12",
                        "projeto": "P82",
                        "current_action": "checkin",
                        "current_local": "Base Norte",
                        "last_checkin_at": "2026-04-20T02:00:00Z"
                      }
                    }
                """.trimIndent(),
            )
        }
        val service = WebCheckApiService(transport, FakeWebSessionStore("session=abc123"))

        val response = service.submitCheck(
            baseUrl = "https://tscode.com.br/",
            request = WebCheckSubmitRequest(
                chave = "AB12",
                projeto = "P82",
                action = RegistroType.CHECK_IN,
                informe = InformeType.RETROATIVO,
                eventTime = Instant.parse("2026-04-20T02:00:00Z"),
                clientEventId = "web-check-12345678",
                local = "Base Norte",
            ),
        )

        val request = transport.requests.single()
        val payload = JsonParser.parseString(request.body).asJsonObject
        assertEquals("POST", request.method)
        assertEquals("https://tscode.com.br/api/web/check", request.url)
        assertEquals("session=abc123", request.headers["Cookie"])
        assertEquals("AB12", payload["chave"].asString)
        assertEquals("P82", payload["projeto"].asString)
        assertEquals("checkin", payload["action"].asString)
        assertEquals("retroativo", payload["informe"].asString)
        assertEquals("Base Norte", payload["local"].asString)
        assertEquals("web-check-12345678", payload["client_event_id"].asString)
        assertTrue(response.ok)
        assertEquals("P82", response.state.projeto)
    }

    @Test
    fun locationAndTransport_useWebEndpointsAndParseResponses() = runBlocking {
        val transport = FakeWebCheckingHttpTransport().apply {
            enqueueResponse(
                statusCode = 200,
                body = """
                    {
                      "matched": true,
                      "resolved_local": "Zona de CheckOut",
                      "label": "Zona de Check-Out",
                      "status": "matched",
                      "message": "Localizacao identificada em Zona de Check-Out.",
                      "accuracy_meters": 12.5,
                      "accuracy_threshold_meters": 30,
                      "nearest_workplace_distance_meters": 90.0
                    }
                """.trimIndent(),
            )
            enqueueResponse(
                statusCode = 200,
                body = """
                    {
                      "ok": true,
                      "message": "Solicitacao de transporte registrada.",
                      "state": {
                        "chave": "AB12",
                        "end_rua": "Rua Um",
                        "zip": "123456",
                        "status": "pending",
                        "request_id": 7,
                        "request_kind": "extra",
                        "service_date": "2026-04-21",
                        "requested_time": "18:00",
                        "requests": [
                          {
                            "request_id": 7,
                            "request_kind": "extra",
                            "status": "pending",
                            "is_active": true,
                            "service_date": "2026-04-21",
                            "requested_time": "18:00",
                            "selected_weekdays": [],
                            "created_at": "2026-04-20T03:00:00Z"
                          }
                        ]
                      }
                    }
                """.trimIndent(),
            )
        }
        val service = WebCheckApiService(transport, FakeWebSessionStore("session=abc123"))

        val location = service.matchLocation(
            baseUrl = "https://tscode.com.br",
            request = WebLocationMatchRequest(
                latitude = -22.9,
                longitude = -43.2,
                accuracyMeters = 12.5,
            ),
        )
        val transportResponse = service.createTransportVehicleRequest(
            baseUrl = "https://tscode.com.br",
            request = WebTransportRequestCreate(
                chave = "AB12",
                requestKind = "extra",
                requestedDate = LocalDate.parse("2026-04-21"),
                requestedTime = "18:00",
            ),
        )

        assertEquals("https://tscode.com.br/api/web/check/location", transport.requests[0].url)
        assertEquals("Zona de CheckOut", location.resolvedLocal)
        assertEquals(
            "https://tscode.com.br/api/web/transport/vehicle-request",
            transport.requests[1].url,
        )
        val transportPayload = JsonParser.parseString(transport.requests[1].body).asJsonObject
        assertEquals("extra", transportPayload["request_kind"].asString)
        assertEquals("2026-04-21", transportPayload["requested_date"].asString)
        assertEquals(7, transportResponse.state.requestId)
        assertEquals(1, transportResponse.state.requests.size)
        assertTrue(transportResponse.state.requests.single().isActive)
    }

    @Test
    fun unauthorizedResponseClearsPersistedSessionAndSurfacesDetail() = runBlocking {
        val transport = FakeWebCheckingHttpTransport().apply {
            enqueueResponse(
                statusCode = 401,
                body = """{"detail":"Chave ou senha invalida"}""",
                headers = mapOf(
                    "Set-Cookie" to listOf(
                        "session=null; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0",
                    ),
                ),
            )
            enqueueFailure(IOException("fallback should not matter"))
        }
        val sessionStore = FakeWebSessionStore("session=old")
        val service = WebCheckApiService(transport, sessionStore)

        try {
            service.fetchCheckState(
                baseUrl = "https://tscode.com.br",
                chave = "AB12",
            )
        } catch (error: CheckingApiException) {
            assertEquals("Chave ou senha invalida", error.userMessage)
            assertEquals("", sessionStore.webSessionSnapshot.value.cookieHeader)
            return@runBlocking
        }

        throw AssertionError("Expected CheckingApiException to be thrown.")
    }

    @Test
    fun logoutClearsSessionWhenServerClearsCookie() = runBlocking {
        val transport = FakeWebCheckingHttpTransport().apply {
            enqueueResponse(
                statusCode = 200,
                body = """
                    {
                      "ok": true,
                      "authenticated": false,
                      "has_password": false,
                      "message": "Sessao encerrada."
                    }
                """.trimIndent(),
                headers = mapOf(
                    "Set-Cookie" to listOf(
                        "session=null; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0",
                    ),
                ),
            )
        }
        val sessionStore = FakeWebSessionStore("session=old")
        val service = WebCheckApiService(transport, sessionStore)

        val response = service.logout("https://tscode.com.br")

        assertFalse(response.authenticated)
        assertEquals("", sessionStore.webSessionSnapshot.value.cookieHeader)
        assertNull(transport.requests.single().body)
    }
}

private class FakeWebCheckingHttpTransport : CheckingHttpTransport {
    val requests = mutableListOf<CheckingHttpRequest>()
    private val queuedResults = ArrayDeque<Result<CheckingHttpResponse>>()

    override suspend fun execute(request: CheckingHttpRequest): CheckingHttpResponse {
        requests += request
        val nextResult = queuedResults.removeFirstOrNull()
            ?: throw IOException("No queued HTTP response for ${request.url}")
        return nextResult.getOrThrow()
    }

    fun enqueueResponse(
        statusCode: Int,
        body: String,
        headers: Map<String, List<String>> = emptyMap(),
    ) {
        queuedResults.addLast(Result.success(CheckingHttpResponse(statusCode, body, headers)))
    }

    fun enqueueFailure(error: Throwable) {
        queuedResults.addLast(Result.failure(error))
    }
}

private class FakeWebSessionStore(
    initialCookieHeader: String = "",
) : WebSessionStore {
    private val snapshot = MutableStateFlow(WebSessionSnapshot(initialCookieHeader))

    override val webSessionSnapshot: MutableStateFlow<WebSessionSnapshot> = snapshot

    override suspend fun saveWebSessionCookieHeader(cookieHeader: String) {
        snapshot.value = WebSessionSnapshot(cookieHeader.trim())
    }

    override suspend fun clearWebSessionCookie() {
        snapshot.value = WebSessionSnapshot()
    }
}
