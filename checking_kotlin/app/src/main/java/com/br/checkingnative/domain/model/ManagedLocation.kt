package com.br.checkingnative.domain.model

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import java.time.Instant

private fun normalizeLocationKey(value: String): String {
    return value.trim().lowercase().replace(Regex("\\s+"), " ")
}

data class ManagedLocationCoordinate(
    val latitude: Double,
    val longitude: Double,
)

data class ManagedLocation(
    val id: Int,
    val local: String,
    val latitude: Double,
    val longitude: Double,
    val coordinates: List<ManagedLocationCoordinate>,
    val toleranceMeters: Int,
    val updatedAt: Instant,
) {
    val isCheckoutZone: Boolean
        get() = CHECKOUT_ZONE_NAME_PATTERN.matches(normalizeLocationKey(local))

    val automationAreaLabel: String
        get() = if (isCheckoutZone) CHECKOUT_ZONE_LABEL else local

    fun matchesLocationName(value: String?): Boolean {
        if (value.isNullOrBlank()) {
            return false
        }
        return normalizeLocationKey(local) == normalizeLocationKey(value)
    }

    companion object {
        const val CHECKOUT_ZONE_LABEL: String = "Zona de CheckOut"
        private val CHECKOUT_ZONE_NAME_PATTERN = Regex("^zona de checkout(?: \\d+)?$")

        fun fromApiJson(json: JsonObject): ManagedLocation {
            val fallbackLatitude = json.getDoubleOrNull("latitude") ?: 0.0
            val fallbackLongitude = json.getDoubleOrNull("longitude") ?: 0.0
            return ManagedLocation(
                id = json.getIntOrNull("id") ?: 0,
                local = (json.getStringOrNull("local") ?: "").trim(),
                latitude = fallbackLatitude,
                longitude = fallbackLongitude,
                coordinates = parseCoordinates(
                    value = json.get("coordinates"),
                    fallbackLatitude = fallbackLatitude,
                    fallbackLongitude = fallbackLongitude,
                ),
                toleranceMeters = json.getIntOrNull("tolerance_meters") ?: 0,
                updatedAt = parseOptionalInstant(json.getStringOrNull("updated_at"))
                    ?: Instant.EPOCH,
            )
        }

        fun parseCoordinates(
            value: JsonElement?,
            fallbackLatitude: Double,
            fallbackLongitude: Double,
        ): List<ManagedLocationCoordinate> {
            if (value != null && value.isJsonArray) {
                val parsedCoordinates = value.asJsonArray.mapNotNull { entry ->
                    if (!entry.isJsonObject) {
                        return@mapNotNull null
                    }
                    ManagedLocationCoordinate(
                        latitude = entry.asJsonObject.getDoubleOrNull("latitude") ?: 0.0,
                        longitude = entry.asJsonObject.getDoubleOrNull("longitude") ?: 0.0,
                    )
                }
                if (parsedCoordinates.isNotEmpty()) {
                    return parsedCoordinates
                }
            }

            return listOf(
                ManagedLocationCoordinate(
                    latitude = fallbackLatitude,
                    longitude = fallbackLongitude,
                ),
            )
        }
    }
}

data class LocationCatalogResponse(
    val items: List<ManagedLocation>,
    val syncedAt: Instant,
    val locationAccuracyThresholdMeters: Int,
) {
    companion object {
        fun fromJsonObject(json: JsonObject): LocationCatalogResponse {
            val items = json.get("items")
                ?.takeIf { value -> value.isJsonArray }
                ?.asJsonArray
                ?.mapNotNull { item ->
                    if (item.isJsonObject) {
                        ManagedLocation.fromApiJson(item.asJsonObject)
                    } else {
                        null
                    }
                }
                ?: emptyList()

            return LocationCatalogResponse(
                items = items,
                syncedAt = parseOptionalInstant(json.getStringOrNull("synced_at")) ?: Instant.now(),
                locationAccuracyThresholdMeters =
                    json.getIntOrNull("location_accuracy_threshold_meters") ?: 30,
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

private fun parseOptionalInstant(value: String?): Instant? {
    if (value.isNullOrBlank()) {
        return null
    }
    return runCatching { Instant.parse(value) }.getOrNull()
}
