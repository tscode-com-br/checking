package com.br.checkingnative.domain.model

import com.google.gson.JsonObject
import java.time.Instant

data class MobileStateResponse(
    val found: Boolean,
    val chave: String,
    val nome: String?,
    val projeto: String?,
    val currentAction: String?,
    val currentEventTime: Instant?,
    val currentLocal: String?,
    val lastCheckInAt: Instant?,
    val lastCheckOutAt: Instant?,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): MobileStateResponse {
            return MobileStateResponse(
                found = json.getBooleanOrNull("found") ?: false,
                chave = json.getStringOrNull("chave") ?: "",
                nome = json.getStringOrNull("nome"),
                projeto = json.getStringOrNull("projeto"),
                currentAction = json.getStringOrNull("current_action"),
                currentEventTime = parseOptionalInstant(json.getStringOrNull("current_event_time")),
                currentLocal = json.getStringOrNull("current_local"),
                lastCheckInAt = parseOptionalInstant(json.getStringOrNull("last_checkin_at")),
                lastCheckOutAt = parseOptionalInstant(json.getStringOrNull("last_checkout_at")),
            )
        }
    }
}

data class MobileSubmitResponse(
    val ok: Boolean,
    val duplicate: Boolean,
    val queuedForms: Boolean,
    val message: String,
    val state: MobileStateResponse,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): MobileSubmitResponse {
            return MobileSubmitResponse(
                ok = json.getBooleanOrNull("ok") ?: false,
                duplicate = json.getBooleanOrNull("duplicate") ?: false,
                queuedForms = json.getBooleanOrNull("queued_forms") ?: true,
                message = json.getStringOrNull("message") ?: "Operação processada.",
                state = json.getObjectOrNull("state")
                    ?.let(MobileStateResponse::fromJsonObject)
                    ?: MobileStateResponse.fromJsonObject(JsonObject()),
            )
        }
    }
}

private fun JsonObject.getStringOrNull(key: String): String? {
    val value = get(key) ?: return null
    if (value.isJsonNull || !value.isJsonPrimitive) {
        return null
    }
    return value.asString
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

private fun parseOptionalInstant(value: String?): Instant? {
    if (value.isNullOrBlank()) {
        return null
    }
    return runCatching { Instant.parse(value) }.getOrNull()
}
