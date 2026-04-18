package com.br.checkingnative.data.remote

import com.br.checkingnative.domain.model.InformeType
import com.br.checkingnative.domain.model.ProjetoType
import com.br.checkingnative.domain.model.RegistroType
import com.br.checkingnative.domain.model.SubmitCheckingEventRequest
import com.google.gson.JsonParser
import java.io.IOException
import java.time.Instant
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CheckingApiServiceTest {
    @Test
    fun fetchState_usesExpectedUrlAndHeaders() = runBlocking {
        val transport = FakeCheckingHttpTransport().apply {
            enqueueResponse(
                statusCode = 200,
                body = """
                    {
                      "found": true,
                      "chave": "AB12",
                      "current_action": "checkin",
                      "last_checkin_at": "2026-04-18T08:00:00Z"
                    }
                """.trimIndent(),
            )
        }
        val service = CheckingApiService(transport)

        val response = service.fetchState(
            baseUrl = "https://tscode.com.br/",
            sharedKey = "mobile-key",
            chave = "AB12",
        )

        val request = transport.requests.single()
        assertEquals(
            "https://tscode.com.br/api/mobile/state?chave=AB12",
            request.url,
        )
        assertEquals("mobile-key", request.headers["x-mobile-shared-key"])
        assertTrue(response.found)
        assertEquals("AB12", response.chave)
    }

    @Test
    fun submitEvent_usesFallbackBaseUrlAfterPrimaryFailure() = runBlocking {
        val transport = FakeCheckingHttpTransport().apply {
            enqueueFailure(IOException("primary offline"))
            enqueueResponse(
                statusCode = 200,
                body = """
                    {
                      "ok": true,
                      "duplicate": false,
                      "queued_forms": true,
                      "message": "Operacao processada.",
                      "state": {
                        "found": true,
                        "chave": "AB12",
                        "current_action": "checkin"
                      }
                    }
                """.trimIndent(),
            )
        }
        val service = CheckingApiService(transport)

        val response = service.submitEvent(
            baseUrl = "https://tscode.com.br",
            sharedKey = "mobile-key",
            request = SubmitCheckingEventRequest(
                chave = "AB12",
                projeto = ProjetoType.P80,
                action = RegistroType.CHECK_IN,
                informe = InformeType.NORMAL,
                clientEventId = "evt-123",
                eventTime = Instant.parse("2026-04-18T08:30:00Z"),
                local = "Base Sul",
            ),
        )

        assertEquals(2, transport.requests.size)
        assertEquals(
            "https://tscode.com.br/api/mobile/events/forms-submit",
            transport.requests[0].url,
        )
        assertEquals(
            "https://www.tscode.com.br/api/mobile/events/forms-submit",
            transport.requests[1].url,
        )

        val payload = JsonParser.parseString(transport.requests[1].body).asJsonObject
        assertEquals("AB12", payload["chave"].asString)
        assertEquals("P80", payload["projeto"].asString)
        assertEquals("checkin", payload["action"].asString)
        assertEquals("normal", payload["informe"].asString)
        assertEquals("Base Sul", payload["local"].asString)
        assertTrue(response.ok)
    }

    @Test
    fun fetchLocations_surfacesFriendlyHttpErrorMessage() = runBlocking {
        val transport = FakeCheckingHttpTransport().apply {
            enqueueResponse(statusCode = 502, body = "")
            enqueueResponse(statusCode = 502, body = "")
        }
        val service = CheckingApiService(transport)

        try {
            service.fetchLocations(
                baseUrl = "https://tscode.com.br",
                sharedKey = "mobile-key",
            )
        } catch (error: CheckingApiException) {
            assertEquals(
                "API indisponivel no momento (502 Bad Gateway).",
                error.userMessage,
            )
            return@runBlocking
        }

        throw AssertionError("Expected CheckingApiException to be thrown.")
    }

    @Test
    fun candidateBaseUrls_rejectsNonHttpsBaseUrl() {
        val service = CheckingApiService(FakeCheckingHttpTransport())

        try {
            service.candidateBaseUrls("http://tscode.com.br")
        } catch (error: CheckingApiException) {
            assertEquals("A URL da API deve usar HTTPS.", error.userMessage)
            return
        }

        throw AssertionError("Expected CheckingApiException to be thrown.")
    }
}

private class FakeCheckingHttpTransport : CheckingHttpTransport {
    val requests = mutableListOf<CheckingHttpRequest>()
    private val queuedResults = ArrayDeque<Result<CheckingHttpResponse>>()

    override suspend fun execute(request: CheckingHttpRequest): CheckingHttpResponse {
        requests += request
        val nextResult = queuedResults.removeFirstOrNull()
            ?: throw IllegalStateException("No queued HTTP response for $request")
        return nextResult.getOrThrow()
    }

    fun enqueueResponse(
        statusCode: Int,
        body: String,
    ) {
        queuedResults.addLast(Result.success(CheckingHttpResponse(statusCode, body)))
    }

    fun enqueueFailure(error: Throwable) {
        queuedResults.addLast(Result.failure(error))
    }
}
