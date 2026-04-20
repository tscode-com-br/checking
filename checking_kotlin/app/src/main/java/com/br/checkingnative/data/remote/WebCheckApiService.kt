package com.br.checkingnative.data.remote

import com.br.checkingnative.core.config.CheckingPresetConfig
import com.br.checkingnative.data.preferences.WebSessionStore
import com.br.checkingnative.domain.model.WebCheckHistoryResponse
import com.br.checkingnative.domain.model.WebCheckSubmitRequest
import com.br.checkingnative.domain.model.WebCheckSubmitResponse
import com.br.checkingnative.domain.model.WebLocationMatchRequest
import com.br.checkingnative.domain.model.WebLocationMatchResponse
import com.br.checkingnative.domain.model.WebLocationOptionsResponse
import com.br.checkingnative.domain.model.WebPasswordActionResponse
import com.br.checkingnative.domain.model.WebPasswordChangeRequest
import com.br.checkingnative.domain.model.WebPasswordLoginRequest
import com.br.checkingnative.domain.model.WebPasswordRegisterRequest
import com.br.checkingnative.domain.model.WebPasswordStatusResponse
import com.br.checkingnative.domain.model.WebProjectRow
import com.br.checkingnative.domain.model.WebProjectUpdateRequest
import com.br.checkingnative.domain.model.WebProjectUpdateResponse
import com.br.checkingnative.domain.model.WebTransportActionResponse
import com.br.checkingnative.domain.model.WebTransportAddressUpdateRequest
import com.br.checkingnative.domain.model.WebTransportRequestAction
import com.br.checkingnative.domain.model.WebTransportRequestCreate
import com.br.checkingnative.domain.model.WebTransportStateResponse
import com.br.checkingnative.domain.model.WebUserSelfRegistrationRequest
import com.google.gson.JsonArray
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.net.URL
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.first

@Singleton
class WebCheckApiService @Inject constructor(
    private val transport: CheckingHttpTransport,
    private val sessionStore: WebSessionStore,
) {
    suspend fun fetchAuthStatus(
        baseUrl: String,
        chave: String,
    ): WebPasswordStatusResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "GET",
            path = "/api/web/auth/status?chave=${encodeQuery(chave)}",
        )
        return WebPasswordStatusResponse.fromJsonObject(payload)
    }

    suspend fun registerPassword(
        baseUrl: String,
        request: WebPasswordRegisterRequest,
    ): WebPasswordActionResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "POST",
            path = "/api/web/auth/register-password",
            body = buildPasswordRegisterPayload(request),
        )
        return WebPasswordActionResponse.fromJsonObject(payload)
    }

    suspend fun registerUser(
        baseUrl: String,
        request: WebUserSelfRegistrationRequest,
    ): WebPasswordActionResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "POST",
            path = "/api/web/auth/register-user",
            body = buildUserRegistrationPayload(request),
        )
        return WebPasswordActionResponse.fromJsonObject(payload)
    }

    suspend fun login(
        baseUrl: String,
        request: WebPasswordLoginRequest,
    ): WebPasswordActionResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "POST",
            path = "/api/web/auth/login",
            body = buildPasswordLoginPayload(request),
        )
        return WebPasswordActionResponse.fromJsonObject(payload)
    }

    suspend fun logout(baseUrl: String): WebPasswordActionResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "POST",
            path = "/api/web/auth/logout",
        )
        return WebPasswordActionResponse.fromJsonObject(payload)
    }

    suspend fun changePassword(
        baseUrl: String,
        request: WebPasswordChangeRequest,
    ): WebPasswordActionResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "POST",
            path = "/api/web/auth/change-password",
            body = buildPasswordChangePayload(request),
        )
        return WebPasswordActionResponse.fromJsonObject(payload)
    }

    suspend fun fetchProjects(baseUrl: String): List<WebProjectRow> {
        val payload = executeElement(
            baseUrl = baseUrl,
            method = "GET",
            path = "/api/web/projects",
        )
        if (!payload.isJsonArray) {
            return emptyList()
        }
        return payload.asJsonArray.mapNotNull { item ->
            if (item.isJsonObject) WebProjectRow.fromJsonObject(item.asJsonObject) else null
        }
    }

    suspend fun updateProject(
        baseUrl: String,
        request: WebProjectUpdateRequest,
    ): WebProjectUpdateResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "PUT",
            path = "/api/web/project",
            body = buildProjectUpdatePayload(request),
        )
        return WebProjectUpdateResponse.fromJsonObject(payload)
    }

    suspend fun fetchTransportState(
        baseUrl: String,
        chave: String,
    ): WebTransportStateResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "GET",
            path = "/api/web/transport/state?chave=${encodeQuery(chave)}",
        )
        return WebTransportStateResponse.fromJsonObject(payload)
    }

    suspend fun updateTransportAddress(
        baseUrl: String,
        request: WebTransportAddressUpdateRequest,
    ): WebTransportActionResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "POST",
            path = "/api/web/transport/address",
            body = buildTransportAddressPayload(request),
        )
        return WebTransportActionResponse.fromJsonObject(payload)
    }

    suspend fun createTransportVehicleRequest(
        baseUrl: String,
        request: WebTransportRequestCreate,
    ): WebTransportActionResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "POST",
            path = "/api/web/transport/vehicle-request",
            body = buildTransportRequestPayload(request),
        )
        return WebTransportActionResponse.fromJsonObject(payload)
    }

    suspend fun cancelTransportRequest(
        baseUrl: String,
        request: WebTransportRequestAction,
    ): WebTransportActionResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "POST",
            path = "/api/web/transport/cancel",
            body = buildTransportActionPayload(request),
        )
        return WebTransportActionResponse.fromJsonObject(payload)
    }

    suspend fun acknowledgeTransportRequest(
        baseUrl: String,
        request: WebTransportRequestAction,
    ): WebTransportActionResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "POST",
            path = "/api/web/transport/acknowledge",
            body = buildTransportActionPayload(request),
        )
        return WebTransportActionResponse.fromJsonObject(payload)
    }

    suspend fun fetchCheckState(
        baseUrl: String,
        chave: String,
    ): WebCheckHistoryResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "GET",
            path = "/api/web/check/state?chave=${encodeQuery(chave)}",
        )
        return WebCheckHistoryResponse.fromJsonObject(payload)
    }

    suspend fun fetchLocationOptions(baseUrl: String): WebLocationOptionsResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "GET",
            path = "/api/web/check/locations",
        )
        return WebLocationOptionsResponse.fromJsonObject(payload)
    }

    suspend fun matchLocation(
        baseUrl: String,
        request: WebLocationMatchRequest,
    ): WebLocationMatchResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "POST",
            path = "/api/web/check/location",
            body = buildLocationMatchPayload(request),
        )
        return WebLocationMatchResponse.fromJsonObject(payload)
    }

    suspend fun submitCheck(
        baseUrl: String,
        request: WebCheckSubmitRequest,
    ): WebCheckSubmitResponse {
        val payload = executeObject(
            baseUrl = baseUrl,
            method = "POST",
            path = "/api/web/check",
            body = buildCheckSubmitPayload(request),
        )
        return WebCheckSubmitResponse.fromJsonObject(payload)
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

    private suspend fun executeObject(
        baseUrl: String,
        method: String,
        path: String,
        body: JsonObject? = null,
    ): JsonObject {
        val payload = executeElement(
            baseUrl = baseUrl,
            method = method,
            path = path,
            body = body,
        )
        return if (payload.isJsonObject) {
            payload.asJsonObject
        } else {
            JsonObject().apply {
                addProperty("message", payload.toString())
            }
        }
    }

    private suspend fun executeElement(
        baseUrl: String,
        method: String,
        path: String,
        body: JsonObject? = null,
    ): JsonElement {
        val candidates = candidateBaseUrls(baseUrl)
        var lastError: Throwable? = null

        for (candidate in candidates) {
            var nonRetryableHttpError = false
            try {
                val response = transport.execute(
                    CheckingHttpRequest(
                        method = method,
                        url = "$candidate$path",
                        headers = buildHeaders(hasBody = body != null),
                        body = body?.toString(),
                    ),
                )
                applySessionCookies(response)
                val payload = decode(response)
                if (response.statusCode !in 200..299) {
                    if (response.statusCode == 401 || response.statusCode == 403) {
                        sessionStore.clearWebSessionCookie()
                    }
                    nonRetryableHttpError = response.statusCode in 400..499
                    throw CheckingApiException(extractMessage(payload, response.statusCode))
                }
                return payload
            } catch (error: Throwable) {
                if (nonRetryableHttpError && error is CheckingApiException) {
                    throw error
                }
                lastError = error
            }
        }

        throw fallbackException(lastError, "Falha ao acessar a API web.")
    }

    private suspend fun buildHeaders(hasBody: Boolean): Map<String, String> {
        val headers = mutableMapOf("Accept" to "application/json")
        if (hasBody) {
            headers["Content-Type"] = "application/json"
        }

        val cookieHeader = sessionStore.webSessionSnapshot.first().cookieHeader.trim()
        if (cookieHeader.isNotBlank()) {
            headers["Cookie"] = cookieHeader
        }
        return headers
    }

    private suspend fun applySessionCookies(response: CheckingHttpResponse) {
        val setCookieHeaders = response.headers
            .filterKeys { key -> key.equals("Set-Cookie", ignoreCase = true) }
            .values
            .flatten()
        for (rawHeader in setCookieHeaders) {
            val cookiePair = rawHeader.substringBefore(";").trim()
            val cookieName = cookiePair.substringBefore("=", "").trim()
            val cookieValue = cookiePair.substringAfter("=", "").trim()
            if (!cookieName.equals(WEB_SESSION_COOKIE_NAME, ignoreCase = true)) {
                continue
            }
            val lowerHeader = rawHeader.lowercase()
            if (
                cookieValue.isBlank() ||
                lowerHeader.contains("max-age=0") ||
                lowerHeader.contains("expires=thu, 01 jan 1970")
            ) {
                sessionStore.clearWebSessionCookie()
                continue
            }
            sessionStore.saveWebSessionCookieHeader(cookiePair)
        }
    }

    private fun buildPasswordRegisterPayload(request: WebPasswordRegisterRequest): JsonObject {
        return JsonObject().apply {
            addProperty("chave", request.chave)
            addProperty("projeto", request.projeto)
            addProperty("senha", request.senha)
        }
    }

    private fun buildUserRegistrationPayload(request: WebUserSelfRegistrationRequest): JsonObject {
        return JsonObject().apply {
            addProperty("chave", request.chave)
            addProperty("nome", request.nome)
            addProperty("projeto", request.projeto)
            addProperty("end_rua", request.endRua)
            addProperty("zip", request.zip)
            addProperty("email", request.email)
            addProperty("senha", request.senha)
            addProperty("confirmar_senha", request.confirmarSenha)
        }
    }

    private fun buildPasswordLoginPayload(request: WebPasswordLoginRequest): JsonObject {
        return JsonObject().apply {
            addProperty("chave", request.chave)
            addProperty("senha", request.senha)
        }
    }

    private fun buildPasswordChangePayload(request: WebPasswordChangeRequest): JsonObject {
        return JsonObject().apply {
            addProperty("chave", request.chave)
            addProperty("senha_antiga", request.senhaAntiga)
            addProperty("nova_senha", request.novaSenha)
        }
    }

    private fun buildProjectUpdatePayload(request: WebProjectUpdateRequest): JsonObject {
        return JsonObject().apply {
            addProperty("chave", request.chave)
            addProperty("projeto", request.projeto)
        }
    }

    private fun buildTransportAddressPayload(
        request: WebTransportAddressUpdateRequest,
    ): JsonObject {
        return JsonObject().apply {
            addProperty("chave", request.chave)
            addProperty("end_rua", request.endRua)
            addProperty("zip", request.zip)
        }
    }

    private fun buildTransportRequestPayload(request: WebTransportRequestCreate): JsonObject {
        return JsonObject().apply {
            addProperty("chave", request.chave)
            addProperty("request_kind", request.requestKind)
            request.requestedTime?.let { value -> addProperty("requested_time", value) }
            request.requestedDate?.let { value -> addProperty("requested_date", value.toString()) }
            request.selectedWeekdays?.let { weekdays ->
                add(
                    "selected_weekdays",
                    JsonArray().apply {
                        weekdays.forEach { weekday -> add(weekday) }
                    },
                )
            }
        }
    }

    private fun buildTransportActionPayload(request: WebTransportRequestAction): JsonObject {
        return JsonObject().apply {
            addProperty("chave", request.chave)
            addProperty("request_id", request.requestId)
        }
    }

    private fun buildLocationMatchPayload(request: WebLocationMatchRequest): JsonObject {
        return JsonObject().apply {
            addProperty("latitude", request.latitude)
            addProperty("longitude", request.longitude)
            request.accuracyMeters?.let { value -> addProperty("accuracy_meters", value) }
        }
    }

    private fun buildCheckSubmitPayload(request: WebCheckSubmitRequest): JsonObject {
        return JsonObject().apply {
            addProperty("chave", request.chave)
            addProperty("projeto", request.projeto)
            addProperty("action", request.action.apiValue)
            addProperty("informe", request.informe.storageName)
            addProperty("event_time", request.eventTime.toString())
            addProperty("client_event_id", request.clientEventId)
            request.local
                ?.trim()
                ?.takeIf { value -> value.isNotEmpty() }
                ?.let { value -> addProperty("local", value) }
        }
    }

    private fun decode(response: CheckingHttpResponse): JsonElement {
        if (response.body.isBlank()) {
            return JsonObject()
        }

        return try {
            JsonParser.parseString(response.body)
        } catch (_: Exception) {
            JsonObject().apply {
                addProperty("message", fallbackHttpMessage(response.statusCode))
            }
        }
    }

    private fun extractMessage(payload: JsonElement, statusCode: Int): String {
        if (payload.isJsonObject) {
            val json = payload.asJsonObject
            val detail = json.getStringOrNull("detail")
            if (!detail.isNullOrBlank()) {
                return detail
            }

            val message = json.getStringOrNull("message")
            if (!message.isNullOrBlank()) {
                return message
            }
        }

        return fallbackHttpMessage(statusCode)
    }

    private fun fallbackHttpMessage(statusCode: Int): String {
        return when (statusCode) {
            401 -> "Sessao expirada ou credenciais invalidas."
            403 -> "Sessao nao autorizada para esta operacao."
            502 -> "API indisponivel no momento (502 Bad Gateway)."
            503 -> "API indisponivel no momento (503 Service Unavailable)."
            504 -> "API nao respondeu a tempo (504 Gateway Timeout)."
            else -> "Erro $statusCode ao acessar a API web."
        }
    }

    private fun fallbackException(lastError: Throwable?, defaultMessage: String): CheckingApiException {
        return if (lastError is CheckingApiException) {
            lastError
        } else {
            CheckingApiException(defaultMessage)
        }
    }

    private fun normalizeAndValidateBaseUrl(rawBaseUrl: String): String {
        val normalized = rawBaseUrl.trim().replace(Regex("/+$"), "")
        if (normalized.isBlank()) {
            throw CheckingApiException("Informe a URL base da API.")
        }

        val url = runCatching { URL(normalized) }.getOrNull()
            ?: throw CheckingApiException("A URL base da API e invalida.")
        if (url.protocol != "https") {
            throw CheckingApiException("A URL da API deve usar HTTPS.")
        }
        return normalized
    }

    private fun encodeQuery(value: String): String {
        return java.net.URLEncoder.encode(value, Charsets.UTF_8.name())
    }

    companion object {
        const val WEB_SESSION_COOKIE_NAME: String = "session"
    }
}

private fun JsonObject.getStringOrNull(key: String): String? {
    val value = get(key) ?: return null
    if (value.isJsonNull || !value.isJsonPrimitive) {
        return null
    }
    return value.asString
}
