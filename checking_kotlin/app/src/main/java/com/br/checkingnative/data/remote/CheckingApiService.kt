package com.br.checkingnative.data.remote

import com.br.checkingnative.core.config.CheckingPresetConfig
import com.br.checkingnative.domain.model.LocationCatalogResponse
import com.br.checkingnative.domain.model.MobileStateResponse
import com.br.checkingnative.domain.model.MobileSubmitResponse
import com.br.checkingnative.domain.model.SubmitCheckingEventRequest
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class CheckingApiException(
    val userMessage: String,
) : Exception(userMessage)

data class CheckingHttpRequest(
    val method: String,
    val url: String,
    val headers: Map<String, String>,
    val body: String? = null,
)

data class CheckingHttpResponse(
    val statusCode: Int,
    val body: String,
    val headers: Map<String, List<String>> = emptyMap(),
)

interface CheckingHttpTransport {
    suspend fun execute(request: CheckingHttpRequest): CheckingHttpResponse
}

class JdkCheckingHttpTransport @Inject constructor() : CheckingHttpTransport {
    override suspend fun execute(request: CheckingHttpRequest): CheckingHttpResponse {
        return withContext(Dispatchers.IO) {
            val connection = URL(request.url).openConnection() as HttpURLConnection
            try {
                connection.requestMethod = request.method
                connection.instanceFollowRedirects = false
                connection.connectTimeout = 15_000
                connection.readTimeout = 15_000
                request.headers.forEach { (name, value) ->
                    connection.setRequestProperty(name, value)
                }

                val body = request.body
                if (!body.isNullOrBlank()) {
                    connection.doOutput = true
                    OutputStreamWriter(connection.outputStream, Charsets.UTF_8).use { writer ->
                        writer.write(body)
                    }
                }

                val statusCode = connection.responseCode
                val stream = if (statusCode in 200..399) {
                    connection.inputStream
                } else {
                    connection.errorStream
                }
                val responseBody = stream?.bufferedReader()?.use { reader -> reader.readText() }.orEmpty()
                val responseHeaders = connection.headerFields
                    .filterKeys { name -> name != null }
                    .mapKeys { entry -> entry.key.orEmpty() }
                    .mapValues { entry -> entry.value.orEmpty() }
                CheckingHttpResponse(
                    statusCode = statusCode,
                    body = responseBody,
                    headers = responseHeaders,
                )
            } finally {
                connection.disconnect()
            }
        }
    }
}

@Singleton
class CheckingApiService @Inject constructor(
    private val transport: CheckingHttpTransport,
) {
    suspend fun fetchState(
        baseUrl: String,
        sharedKey: String,
        chave: String,
    ): MobileStateResponse {
        val candidates = candidateBaseUrls(baseUrl)
        var lastError: Throwable? = null

        for (candidate in candidates) {
            try {
                val response = transport.execute(
                    CheckingHttpRequest(
                        method = "GET",
                        url = "$candidate/api/mobile/state?chave=${encodeQuery(chave)}",
                        headers = headers(sharedKey),
                    ),
                )
                val payload = decode(response)
                if (response.statusCode !in 200..299) {
                    throw CheckingApiException(extractMessage(payload, response.statusCode))
                }
                return MobileStateResponse.fromJsonObject(payload)
            } catch (error: Throwable) {
                lastError = error
            }
        }

        throw fallbackException(lastError, "Falha ao consultar a API.")
    }

    suspend fun submitEvent(
        baseUrl: String,
        sharedKey: String,
        request: SubmitCheckingEventRequest,
    ): MobileSubmitResponse {
        val candidates = candidateBaseUrls(baseUrl)
        var lastError: Throwable? = null

        for (candidate in candidates) {
            try {
                val response = transport.execute(
                    CheckingHttpRequest(
                        method = "POST",
                        url = "$candidate/api/mobile/events/forms-submit",
                        headers = headers(sharedKey),
                        body = buildSubmitPayload(request).toString(),
                    ),
                )
                val payload = decode(response)
                if (response.statusCode !in 200..299) {
                    throw CheckingApiException(extractMessage(payload, response.statusCode))
                }
                return MobileSubmitResponse.fromJsonObject(payload)
            } catch (error: Throwable) {
                lastError = error
            }
        }

        throw fallbackException(lastError, "Falha ao enviar evento pela API.")
    }

    suspend fun fetchLocations(
        baseUrl: String,
        sharedKey: String,
    ): LocationCatalogResponse {
        val candidates = candidateBaseUrls(baseUrl)
        var lastError: Throwable? = null

        for (candidate in candidates) {
            try {
                val response = transport.execute(
                    CheckingHttpRequest(
                        method = "GET",
                        url = "$candidate/api/mobile/locations",
                        headers = headers(sharedKey),
                    ),
                )
                val payload = decode(response)
                if (response.statusCode !in 200..299) {
                    throw CheckingApiException(extractMessage(payload, response.statusCode))
                }
                return LocationCatalogResponse.fromJsonObject(payload)
            } catch (error: Throwable) {
                lastError = error
            }
        }

        throw fallbackException(lastError, "Falha ao atualizar as localizações do aplicativo.")
    }

    fun candidateBaseUrls(rawBaseUrl: String): List<String> {
        val primary = normalizeAndValidateBaseUrl(rawBaseUrl)
        val candidates = linkedSetOf(primary)
        for (fallback in CheckingPresetConfig.apiBaseUrlFallbacks) {
            val normalizedFallback = fallback.trim().replace(Regex("/+$"), "")
            if (normalizedFallback.isBlank()) {
                continue
            }
            val uri = runCatching { URL(normalizedFallback) }.getOrNull() ?: continue
            if (uri.protocol != "https") {
                continue
            }
            candidates += normalizedFallback
        }
        return candidates.toList()
    }

    private fun headers(sharedKey: String): Map<String, String> {
        return mapOf(
            "Content-Type" to "application/json",
            "x-mobile-shared-key" to sharedKey.trim(),
        )
    }

    private fun normalizeAndValidateBaseUrl(rawBaseUrl: String): String {
        val normalized = rawBaseUrl.trim().replace(Regex("/+$"), "")
        if (normalized.isBlank()) {
            throw CheckingApiException("Informe a URL base da API.")
        }

        val url = runCatching { URL(normalized) }.getOrNull()
            ?: throw CheckingApiException("A URL base da API é inválida.")
        if (url.protocol != "https") {
            throw CheckingApiException("A URL da API deve usar HTTPS.")
        }
        return normalized
    }

    private fun buildSubmitPayload(request: SubmitCheckingEventRequest): JsonObject {
        return JsonObject().apply {
            addProperty("chave", request.chave)
            addProperty("projeto", request.projeto.apiValue)
            addProperty("action", request.action.apiValue)
            addProperty("informe", request.informe.storageName)
            addProperty("client_event_id", request.clientEventId)
            addProperty("event_time", request.eventTime.toString())
            request.local
                ?.trim()
                ?.takeIf { it.isNotEmpty() }
                ?.let { addProperty("local", it) }
        }
    }

    private fun decode(response: CheckingHttpResponse): JsonObject {
        if (response.body.isBlank()) {
            return JsonObject()
        }

        return try {
            val decoded = JsonParser.parseString(response.body)
            if (decoded.isJsonObject) {
                decoded.asJsonObject
            } else {
                JsonObject().apply {
                    addProperty("message", decoded.toString())
                }
            }
        } catch (_: Exception) {
            JsonObject().apply {
                addProperty("message", fallbackHttpMessage(response.statusCode))
            }
        }
    }

    private fun extractMessage(payload: JsonObject, statusCode: Int): String {
        val detail = payload.getStringOrNull("detail")
        if (!detail.isNullOrBlank()) {
            return detail
        }

        val message = payload.getStringOrNull("message")
        if (!message.isNullOrBlank()) {
            return message
        }

        return fallbackHttpMessage(statusCode)
    }

    private fun fallbackHttpMessage(statusCode: Int): String {
        return when (statusCode) {
            502 -> "API indisponível no momento (502 Bad Gateway)."
            503 -> "API indisponível no momento (503 Service Unavailable)."
            504 -> "API não respondeu a tempo (504 Gateway Timeout)."
            else -> "Erro $statusCode ao acessar a API."
        }
    }

    private fun fallbackException(lastError: Throwable?, defaultMessage: String): CheckingApiException {
        return if (lastError is CheckingApiException) {
            lastError
        } else {
            CheckingApiException(defaultMessage)
        }
    }

    private fun encodeQuery(value: String): String {
        return java.net.URLEncoder.encode(value, Charsets.UTF_8.name())
    }
}

private fun JsonObject.getStringOrNull(key: String): String? {
    val value = get(key) ?: return null
    if (value.isJsonNull || !value.isJsonPrimitive) {
        return null
    }
    return value.asString
}
