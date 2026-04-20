package com.br.checkingnative.domain.model

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import java.time.Instant
import java.time.LocalDate
import java.time.OffsetDateTime

data class WebProjectRow(
    val id: Int,
    val name: String,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): WebProjectRow {
            return WebProjectRow(
                id = json.getIntOrNull("id") ?: 0,
                name = json.getStringOrNull("name").orEmpty(),
            )
        }
    }
}

data class WebPasswordStatusResponse(
    val found: Boolean,
    val chave: String,
    val hasPassword: Boolean,
    val authenticated: Boolean,
    val message: String,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): WebPasswordStatusResponse {
            return WebPasswordStatusResponse(
                found = json.getBooleanOrNull("found") ?: false,
                chave = json.getStringOrNull("chave").orEmpty(),
                hasPassword = json.getBooleanOrNull("has_password") ?: false,
                authenticated = json.getBooleanOrNull("authenticated") ?: false,
                message = json.getStringOrNull("message").orEmpty(),
            )
        }
    }
}

data class WebPasswordRegisterRequest(
    val chave: String,
    val projeto: String,
    val senha: String,
)

data class WebUserSelfRegistrationRequest(
    val chave: String,
    val nome: String,
    val projeto: String,
    val endRua: String,
    val zip: String,
    val email: String,
    val senha: String,
    val confirmarSenha: String,
)

data class WebPasswordLoginRequest(
    val chave: String,
    val senha: String,
)

data class WebPasswordChangeRequest(
    val chave: String,
    val senhaAntiga: String,
    val novaSenha: String,
)

data class WebPasswordActionResponse(
    val ok: Boolean,
    val authenticated: Boolean,
    val hasPassword: Boolean,
    val message: String,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): WebPasswordActionResponse {
            return WebPasswordActionResponse(
                ok = json.getBooleanOrNull("ok") ?: false,
                authenticated = json.getBooleanOrNull("authenticated") ?: false,
                hasPassword = json.getBooleanOrNull("has_password") ?: false,
                message = json.getStringOrNull("message").orEmpty(),
            )
        }
    }
}

data class WebProjectUpdateRequest(
    val chave: String,
    val projeto: String,
)

data class WebProjectUpdateResponse(
    val ok: Boolean,
    val message: String,
    val project: String,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): WebProjectUpdateResponse {
            return WebProjectUpdateResponse(
                ok = json.getBooleanOrNull("ok") ?: false,
                message = json.getStringOrNull("message").orEmpty(),
                project = json.getStringOrNull("project").orEmpty(),
            )
        }
    }
}

data class WebCheckHistoryResponse(
    val found: Boolean,
    val chave: String,
    val projeto: String?,
    val currentAction: String?,
    val currentLocal: String?,
    val hasCurrentDayCheckIn: Boolean,
    val lastCheckInAt: Instant?,
    val lastCheckOutAt: Instant?,
) {
    fun toMobileStateResponse(): MobileStateResponse {
        return MobileStateResponse(
            found = found,
            chave = chave,
            nome = null,
            projeto = projeto,
            currentAction = currentAction,
            currentEventTime = null,
            currentLocal = currentLocal,
            lastCheckInAt = lastCheckInAt,
            lastCheckOutAt = lastCheckOutAt,
        )
    }

    companion object {
        fun fromJsonObject(json: JsonObject): WebCheckHistoryResponse {
            return WebCheckHistoryResponse(
                found = json.getBooleanOrNull("found") ?: false,
                chave = json.getStringOrNull("chave").orEmpty(),
                projeto = json.getStringOrNull("projeto"),
                currentAction = json.getStringOrNull("current_action"),
                currentLocal = json.getStringOrNull("current_local"),
                hasCurrentDayCheckIn =
                    json.getBooleanOrNull("has_current_day_checkin") ?: false,
                lastCheckInAt = parseOptionalInstant(json.getStringOrNull("last_checkin_at")),
                lastCheckOutAt = parseOptionalInstant(json.getStringOrNull("last_checkout_at")),
            )
        }
    }
}

data class WebLocationOptionsResponse(
    val items: List<String>,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): WebLocationOptionsResponse {
            return WebLocationOptionsResponse(
                items = json.getArrayOrNull("items")
                    ?.mapNotNull { item ->
                        if (item.isJsonPrimitive) item.asString else null
                    }
                    ?: emptyList(),
            )
        }
    }
}

data class WebLocationMatchRequest(
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Double? = null,
)

data class WebLocationMatchResponse(
    val matched: Boolean,
    val resolvedLocal: String?,
    val label: String,
    val status: String,
    val message: String,
    val accuracyMeters: Double?,
    val accuracyThresholdMeters: Int,
    val nearestWorkplaceDistanceMeters: Double?,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): WebLocationMatchResponse {
            return WebLocationMatchResponse(
                matched = json.getBooleanOrNull("matched") ?: false,
                resolvedLocal = json.getStringOrNull("resolved_local"),
                label = json.getStringOrNull("label").orEmpty(),
                status = json.getStringOrNull("status").orEmpty(),
                message = json.getStringOrNull("message").orEmpty(),
                accuracyMeters = json.getDoubleOrNull("accuracy_meters"),
                accuracyThresholdMeters = json.getIntOrNull("accuracy_threshold_meters")
                    ?: CheckingLocationAccuracyDefaults.thresholdMeters,
                nearestWorkplaceDistanceMeters =
                    json.getDoubleOrNull("nearest_workplace_distance_meters"),
            )
        }
    }
}

data class WebCheckSubmitRequest(
    val chave: String,
    val projeto: String,
    val action: RegistroType,
    val informe: InformeType,
    val eventTime: Instant,
    val clientEventId: String,
    val local: String? = null,
)

data class WebCheckSubmitResponse(
    val ok: Boolean,
    val duplicate: Boolean,
    val queuedForms: Boolean,
    val message: String,
    val state: MobileStateResponse,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): WebCheckSubmitResponse {
            return WebCheckSubmitResponse(
                ok = json.getBooleanOrNull("ok") ?: false,
                duplicate = json.getBooleanOrNull("duplicate") ?: false,
                queuedForms = json.getBooleanOrNull("queued_forms") ?: true,
                message = json.getStringOrNull("message") ?: "Operacao processada.",
                state = json.getObjectOrNull("state")
                    ?.let(MobileStateResponse::fromJsonObject)
                    ?: MobileStateResponse.fromJsonObject(JsonObject()),
            )
        }
    }
}

data class WebTransportRequestItemResponse(
    val requestId: Int,
    val requestKind: String,
    val status: String,
    val isActive: Boolean,
    val serviceDate: LocalDate?,
    val requestedTime: String?,
    val selectedWeekdays: List<Int>,
    val routeKind: String?,
    val boardingTime: String?,
    val confirmationDeadlineTime: String?,
    val vehicleType: String?,
    val vehiclePlate: String?,
    val vehicleColor: String?,
    val toleranceMinutes: Int?,
    val awarenessRequired: Boolean,
    val awarenessConfirmed: Boolean,
    val responseMessage: String?,
    val createdAt: Instant?,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): WebTransportRequestItemResponse {
            return WebTransportRequestItemResponse(
                requestId = json.getIntOrNull("request_id") ?: 0,
                requestKind = json.getStringOrNull("request_kind").orEmpty(),
                status = json.getStringOrNull("status").orEmpty(),
                isActive = json.getBooleanOrNull("is_active") ?: false,
                serviceDate = parseOptionalLocalDate(json.getStringOrNull("service_date")),
                requestedTime = json.getStringOrNull("requested_time"),
                selectedWeekdays = json.getIntListOrEmpty("selected_weekdays"),
                routeKind = json.getStringOrNull("route_kind"),
                boardingTime = json.getStringOrNull("boarding_time"),
                confirmationDeadlineTime =
                    json.getStringOrNull("confirmation_deadline_time"),
                vehicleType = json.getStringOrNull("vehicle_type"),
                vehiclePlate = json.getStringOrNull("vehicle_plate"),
                vehicleColor = json.getStringOrNull("vehicle_color"),
                toleranceMinutes = json.getIntOrNull("tolerance_minutes"),
                awarenessRequired = json.getBooleanOrNull("awareness_required") ?: false,
                awarenessConfirmed = json.getBooleanOrNull("awareness_confirmed") ?: false,
                responseMessage = json.getStringOrNull("response_message"),
                createdAt = parseOptionalInstant(json.getStringOrNull("created_at")),
            )
        }
    }
}

data class WebTransportStateResponse(
    val chave: String,
    val endRua: String?,
    val zip: String?,
    val status: String,
    val requestId: Int?,
    val requestKind: String?,
    val routeKind: String?,
    val serviceDate: LocalDate?,
    val requestedTime: String?,
    val boardingTime: String?,
    val confirmationDeadlineTime: String?,
    val vehicleType: String?,
    val vehiclePlate: String?,
    val vehicleColor: String?,
    val toleranceMinutes: Int?,
    val awarenessRequired: Boolean,
    val awarenessConfirmed: Boolean,
    val requests: List<WebTransportRequestItemResponse>,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): WebTransportStateResponse {
            return WebTransportStateResponse(
                chave = json.getStringOrNull("chave").orEmpty(),
                endRua = json.getStringOrNull("end_rua"),
                zip = json.getStringOrNull("zip"),
                status = json.getStringOrNull("status") ?: "available",
                requestId = json.getIntOrNull("request_id"),
                requestKind = json.getStringOrNull("request_kind"),
                routeKind = json.getStringOrNull("route_kind"),
                serviceDate = parseOptionalLocalDate(json.getStringOrNull("service_date")),
                requestedTime = json.getStringOrNull("requested_time"),
                boardingTime = json.getStringOrNull("boarding_time"),
                confirmationDeadlineTime =
                    json.getStringOrNull("confirmation_deadline_time"),
                vehicleType = json.getStringOrNull("vehicle_type"),
                vehiclePlate = json.getStringOrNull("vehicle_plate"),
                vehicleColor = json.getStringOrNull("vehicle_color"),
                toleranceMinutes = json.getIntOrNull("tolerance_minutes"),
                awarenessRequired = json.getBooleanOrNull("awareness_required") ?: false,
                awarenessConfirmed = json.getBooleanOrNull("awareness_confirmed") ?: false,
                requests = json.getArrayOrNull("requests")
                    ?.mapNotNull { item ->
                        if (item.isJsonObject) {
                            WebTransportRequestItemResponse.fromJsonObject(item.asJsonObject)
                        } else {
                            null
                        }
                    }
                    ?: emptyList(),
            )
        }
    }
}

data class WebTransportActionResponse(
    val ok: Boolean,
    val message: String,
    val state: WebTransportStateResponse,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): WebTransportActionResponse {
            return WebTransportActionResponse(
                ok = json.getBooleanOrNull("ok") ?: false,
                message = json.getStringOrNull("message").orEmpty(),
                state = json.getObjectOrNull("state")
                    ?.let(WebTransportStateResponse::fromJsonObject)
                    ?: WebTransportStateResponse.fromJsonObject(JsonObject()),
            )
        }
    }
}

data class WebTransportAddressUpdateRequest(
    val chave: String,
    val endRua: String,
    val zip: String,
)

data class WebTransportRequestCreate(
    val chave: String,
    val requestKind: String,
    val requestedTime: String? = null,
    val requestedDate: LocalDate? = null,
    val selectedWeekdays: List<Int>? = null,
)

data class WebTransportRequestAction(
    val chave: String,
    val requestId: Int,
)

private object CheckingLocationAccuracyDefaults {
    const val thresholdMeters: Int = 30
}

private fun JsonObject.getStringOrNull(key: String): String? {
    val value = get(key) ?: return null
    if (value.isJsonNull || !value.isJsonPrimitive) {
        return null
    }
    return value.asString
}

private fun JsonObject.getIntOrNull(key: String): Int? {
    val value = get(key) ?: return null
    if (value.isJsonNull || !value.isJsonPrimitive) {
        return null
    }
    return runCatching { value.asInt }.getOrNull()
}

private fun JsonObject.getDoubleOrNull(key: String): Double? {
    val value = get(key) ?: return null
    if (value.isJsonNull || !value.isJsonPrimitive) {
        return null
    }
    return runCatching { value.asDouble }.getOrNull()
}

private fun JsonObject.getBooleanOrNull(key: String): Boolean? {
    val value = get(key) ?: return null
    if (value.isJsonNull || !value.isJsonPrimitive) {
        return null
    }
    return runCatching { value.asBoolean }.getOrNull()
}

private fun JsonObject.getObjectOrNull(key: String): JsonObject? {
    val value = get(key) ?: return null
    if (!value.isJsonObject) {
        return null
    }
    return value.asJsonObject
}

private fun JsonObject.getArrayOrNull(key: String): List<JsonElement>? {
    val value = get(key) ?: return null
    if (!value.isJsonArray) {
        return null
    }
    return value.asJsonArray.toList()
}

private fun JsonObject.getIntListOrEmpty(key: String): List<Int> {
    return getArrayOrNull(key)
        ?.mapNotNull { item ->
            if (item.isJsonPrimitive) {
                runCatching { item.asInt }.getOrNull()
            } else {
                null
            }
        }
        ?: emptyList()
}

private fun parseOptionalInstant(value: String?): Instant? {
    if (value.isNullOrBlank()) {
        return null
    }
    return runCatching { Instant.parse(value) }.getOrElse {
        runCatching { OffsetDateTime.parse(value).toInstant() }.getOrNull()
    }
}

private fun parseOptionalLocalDate(value: String?): LocalDate? {
    if (value.isNullOrBlank()) {
        return null
    }
    return runCatching { LocalDate.parse(value) }.getOrNull()
}
