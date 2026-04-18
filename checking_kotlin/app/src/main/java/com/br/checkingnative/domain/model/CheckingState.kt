package com.br.checkingnative.domain.model

import com.br.checkingnative.core.config.CheckingPresetConfig
import com.google.gson.JsonArray
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.time.Instant
import kotlin.math.abs

enum class RegistroType(
    val storageName: String,
    val label: String,
    val apiValue: String,
) {
    CHECK_IN(
        storageName = "checkIn",
        label = "Check-In",
        apiValue = "checkin",
    ),
    CHECK_OUT(
        storageName = "checkOut",
        label = "Check-Out",
        apiValue = "checkout",
    ),
    ;

    companion object {
        fun fromStorageName(value: String?): RegistroType {
            return entries.firstOrNull { type -> type.storageName == value } ?: CHECK_IN
        }
    }
}

enum class InformeType(
    val storageName: String,
    val label: String,
) {
    NORMAL(
        storageName = "normal",
        label = "Normal",
    ),
    RETROATIVO(
        storageName = "retroativo",
        label = "Retroativo",
    ),
    ;

    companion object {
        fun fromStorageName(value: String?): InformeType {
            return entries.firstOrNull { type -> type.storageName == value } ?: NORMAL
        }
    }
}

enum class ProjetoType(
    val storageName: String,
    val label: String,
    val apiValue: String,
) {
    P80(
        storageName = "p80",
        label = "P-80",
        apiValue = "P80",
    ),
    P82(
        storageName = "p82",
        label = "P-82",
        apiValue = "P82",
    ),
    P83(
        storageName = "p83",
        label = "P-83",
        apiValue = "P83",
    ),
    ;

    companion object {
        fun fromStorageName(value: String?): ProjetoType {
            return entries.firstOrNull { type -> type.storageName == value } ?: P80
        }
    }
}

enum class StatusTone(
    val storageName: String,
) {
    NEUTRAL("neutral"),
    SUCCESS("success"),
    WARNING("warning"),
    ERROR("error"),
    ;
}

data class LocationFetchEntry(
    val timestamp: Instant,
    val latitude: Double? = null,
    val longitude: Double? = null,
) {
    fun isDuplicateOf(
        other: LocationFetchEntry,
        maxTimestampDifferenceMillis: Long = DUPLICATE_WINDOW_MILLIS,
        coordinateTolerance: Double = DUPLICATE_COORDINATE_TOLERANCE,
    ): Boolean {
        val timestampDifferenceMillis =
            abs(timestamp.toEpochMilli() - other.timestamp.toEpochMilli())
        if (timestampDifferenceMillis > maxTimestampDifferenceMillis) {
            return false
        }

        val currentLatitude = latitude
        val currentLongitude = longitude
        val otherLatitude = other.latitude
        val otherLongitude = other.longitude
        if (
            currentLatitude == null ||
            currentLongitude == null ||
            otherLatitude == null ||
            otherLongitude == null
        ) {
            return currentLatitude == otherLatitude && currentLongitude == otherLongitude
        }

        return abs(currentLatitude - otherLatitude) <= coordinateTolerance &&
            abs(currentLongitude - otherLongitude) <= coordinateTolerance
    }

    fun toPersistedJson(): JsonObject {
        return JsonObject().apply {
            addProperty("timestamp", timestamp.toString())
            if (latitude != null) {
                addProperty("latitude", latitude)
            }
            if (longitude != null) {
                addProperty("longitude", longitude)
            }
        }
    }

    companion object {
        const val maxStoredEntries: Int = 10
        const val DUPLICATE_WINDOW_MILLIS: Long = 1_000
        const val DUPLICATE_COORDINATE_TOLERANCE: Double = 1e-6

        fun normalizeHistory(
            entries: Iterable<LocationFetchEntry>,
            maxEntries: Int? = null,
        ): List<LocationFetchEntry> {
            val effectiveMaxEntries = when {
                maxEntries == null -> null
                maxEntries < 1 -> 1
                else -> maxEntries
            }
            val normalized = mutableListOf<LocationFetchEntry>()

            for (entry in entries) {
                if (normalized.isNotEmpty() && entry.isDuplicateOf(normalized.last())) {
                    continue
                }

                normalized += entry
                if (effectiveMaxEntries != null && normalized.size >= effectiveMaxEntries) {
                    break
                }
            }

            return normalized.toList()
        }

        fun tryParse(value: JsonElement?): LocationFetchEntry? {
            if (value == null || value.isJsonNull) {
                return null
            }

            if (value.isJsonPrimitive && value.asJsonPrimitive.isString) {
                val timestamp = parseOptionalInstant(value.asString) ?: return null
                return LocationFetchEntry(timestamp = timestamp)
            }

            if (value.isJsonObject) {
                val payload = value.asJsonObject
                val rawTimestamp = payload.get("timestamp")
                val timestamp = when {
                    rawTimestamp == null || rawTimestamp.isJsonNull -> null
                    rawTimestamp.isJsonPrimitive && rawTimestamp.asJsonPrimitive.isString ->
                        parseOptionalInstant(rawTimestamp.asString)
                    rawTimestamp.isJsonPrimitive && rawTimestamp.asJsonPrimitive.isNumber ->
                        Instant.ofEpochMilli(rawTimestamp.asLong)
                    else -> null
                } ?: return null

                return LocationFetchEntry(
                    timestamp = timestamp,
                    latitude = payload.getDoubleOrNull("latitude"),
                    longitude = payload.getDoubleOrNull("longitude"),
                )
            }

            return null
        }
    }
}

data class CheckingState(
    val chave: String,
    val registro: RegistroType,
    val checkInInforme: InformeType,
    val checkOutInforme: InformeType,
    val checkInProjeto: ProjetoType,
    val apiBaseUrl: String,
    val apiSharedKey: String,
    val locationUpdateIntervalSeconds: Int,
    val nightUpdatesDisabled: Boolean,
    val nightPeriodStartMinutes: Int,
    val nightPeriodEndMinutes: Int,
    val nightModeAfterCheckoutEnabled: Boolean,
    val nightModeAfterCheckoutUntil: Instant?,
    val locationAccuracyThresholdMeters: Int,
    val locationSharingEnabled: Boolean,
    val canEnableLocationSharing: Boolean,
    val autoCheckInEnabled: Boolean,
    val autoCheckOutEnabled: Boolean,
    val oemBackgroundSetupEnabled: Boolean,
    val lastMatchedLocation: String?,
    val lastDetectedLocation: String?,
    val lastLocationUpdateAt: Instant?,
    val locationFetchHistory: List<LocationFetchEntry>,
    val lastCheckInLocation: String?,
    val lastCheckIn: Instant?,
    val lastCheckOut: Instant?,
    val statusMessage: String,
    val statusTone: StatusTone,
    val isLoading: Boolean,
    val isSubmitting: Boolean,
    val isSyncing: Boolean,
    val isLocationUpdating: Boolean,
    val isAutomaticCheckingUpdating: Boolean,
) {
    val informe: InformeType
        get() = informeFor(registro)

    val projeto: ProjetoType
        get() = checkInProjeto

    val hasValidChave: Boolean
        get() = chave.trim().length == 4

    val hasApiConfig: Boolean
        get() = apiBaseUrl.trim().isNotEmpty() && apiSharedKey.trim().isNotEmpty()

    val automaticCheckInOutEnabled: Boolean
        get() = autoCheckInEnabled || autoCheckOutEnabled

    val hasAnyLocationAutomation: Boolean
        get() = autoCheckInEnabled || autoCheckOutEnabled

    val lastRecordedAction: RegistroType?
        get() {
            val latestCheckIn = lastCheckIn
            val latestCheckOut = lastCheckOut
            if (latestCheckIn == null && latestCheckOut == null) {
                return null
            }
            if (latestCheckIn != null && latestCheckOut == null) {
                return RegistroType.CHECK_IN
            }
            if (latestCheckIn == null && latestCheckOut != null) {
                return RegistroType.CHECK_OUT
            }
            return when {
                latestCheckIn!!.isAfter(latestCheckOut) -> RegistroType.CHECK_IN
                latestCheckOut!!.isAfter(latestCheckIn) -> RegistroType.CHECK_OUT
                else -> null
            }
        }

    fun informeFor(action: RegistroType): InformeType {
        return if (action == RegistroType.CHECK_IN) checkInInforme else checkOutInforme
    }

    fun projetoFor(action: RegistroType): ProjetoType {
        return checkInProjeto
    }

    fun toPersistedJsonString(): String {
        return JsonObject().apply {
            addProperty("chave", chave)
            addProperty("registro", registro.storageName)
            addProperty("informe", informe.storageName)
            addProperty("projeto", checkInProjeto.storageName)
            addProperty("checkInInforme", checkInInforme.storageName)
            addProperty("checkOutInforme", checkOutInforme.storageName)
            addProperty("checkInProjeto", checkInProjeto.storageName)
            addProperty("apiBaseUrl", apiBaseUrl)
            addProperty("locationUpdateIntervalSeconds", locationUpdateIntervalSeconds)
            addProperty("nightUpdatesDisabled", nightUpdatesDisabled)
            addProperty("nightPeriodStartMinutes", nightPeriodStartMinutes)
            addProperty("nightPeriodEndMinutes", nightPeriodEndMinutes)
            addProperty("nightModeAfterCheckoutEnabled", nightModeAfterCheckoutEnabled)
            if (nightModeAfterCheckoutUntil != null) {
                addProperty("nightModeAfterCheckoutUntil", nightModeAfterCheckoutUntil.toString())
            }
            addProperty("locationAccuracyThresholdMeters", locationAccuracyThresholdMeters)
            addProperty("locationSharingEnabled", locationSharingEnabled)
            addProperty("autoCheckInEnabled", autoCheckInEnabled)
            addProperty("autoCheckOutEnabled", autoCheckOutEnabled)
            addProperty("oemBackgroundSetupEnabled", oemBackgroundSetupEnabled)
            if (lastMatchedLocation != null) {
                addProperty("lastMatchedLocation", lastMatchedLocation)
            }
            if (lastDetectedLocation != null) {
                addProperty("lastDetectedLocation", lastDetectedLocation)
            }
            if (lastLocationUpdateAt != null) {
                addProperty("lastLocationUpdateAt", lastLocationUpdateAt.toString())
            }
            add(
                "locationFetchHistory",
                JsonArray().apply {
                    locationFetchHistory.forEach { entry -> add(entry.toPersistedJson()) }
                },
            )
            if (lastCheckInLocation != null) {
                addProperty("lastCheckInLocation", lastCheckInLocation)
            }
        }.toString()
    }

    companion object {
        fun initial(): CheckingState {
            return CheckingState(
                chave = "",
                registro = RegistroType.CHECK_IN,
                checkInInforme = InformeType.NORMAL,
                checkOutInforme = InformeType.NORMAL,
                checkInProjeto = ProjetoType.P80,
                apiBaseUrl = CheckingPresetConfig.apiBaseUrl,
                apiSharedKey = CheckingPresetConfig.apiSharedKey,
                locationUpdateIntervalSeconds = 15 * 60,
                nightUpdatesDisabled = false,
                nightPeriodStartMinutes = 22 * 60,
                nightPeriodEndMinutes = 6 * 60,
                nightModeAfterCheckoutEnabled = false,
                nightModeAfterCheckoutUntil = null,
                locationAccuracyThresholdMeters = 30,
                locationSharingEnabled = false,
                canEnableLocationSharing = false,
                autoCheckInEnabled = false,
                autoCheckOutEnabled = false,
                oemBackgroundSetupEnabled = false,
                lastMatchedLocation = null,
                lastDetectedLocation = null,
                lastLocationUpdateAt = null,
                locationFetchHistory = emptyList(),
                lastCheckInLocation = null,
                lastCheckIn = null,
                lastCheckOut = null,
                statusMessage = "",
                statusTone = StatusTone.NEUTRAL,
                isLoading = true,
                isSubmitting = false,
                isSyncing = false,
                isLocationUpdating = false,
                isAutomaticCheckingUpdating = false,
            )
        }

        fun sanitizeChave(value: String): String {
            return value.trim().uppercase()
        }

        fun inferSuggestedRegistro(
            lastCheckIn: Instant?,
            lastCheckOut: Instant?,
            fallback: RegistroType = RegistroType.CHECK_IN,
        ): RegistroType {
            if (lastCheckIn == null && lastCheckOut == null) {
                return fallback
            }
            if (lastCheckIn != null && lastCheckOut == null) {
                return RegistroType.CHECK_OUT
            }
            if (lastCheckIn == null && lastCheckOut != null) {
                return RegistroType.CHECK_IN
            }
            return when {
                lastCheckIn!!.isAfter(lastCheckOut) -> RegistroType.CHECK_OUT
                lastCheckIn.isBefore(lastCheckOut!!) -> RegistroType.CHECK_IN
                else -> fallback
            }
        }

        fun fromPersistedJsonString(
            raw: String?,
            resolvedSharedKey: String = CheckingPresetConfig.apiSharedKey,
        ): CheckingState {
            if (raw.isNullOrBlank()) {
                return initial().copy(
                    apiSharedKey = resolvedSharedKey,
                    isLoading = false,
                )
            }

            return try {
                val payload = JsonParser.parseString(raw)
                if (!payload.isJsonObject) {
                    throw IllegalArgumentException("Persisted state must be a JSON object.")
                }
                fromPersistedJsonObject(
                    json = payload.asJsonObject,
                    resolvedSharedKey = resolvedSharedKey,
                )
            } catch (_: Exception) {
                initial().copy(
                    apiSharedKey = resolvedSharedKey,
                    isLoading = false,
                )
            }
        }

        private fun fromPersistedJsonObject(
            json: JsonObject,
            resolvedSharedKey: String,
        ): CheckingState {
            val locationSharingEnabled = json.getBooleanOrNull("locationSharingEnabled") ?: false
            val restoredAutoCheckInEnabled = if (json.has("autoCheckInEnabled")) {
                json.getBooleanOrNull("autoCheckInEnabled") ?: false
            } else {
                locationSharingEnabled
            }
            val restoredAutoCheckOutEnabled = if (json.has("autoCheckOutEnabled")) {
                json.getBooleanOrNull("autoCheckOutEnabled") ?: false
            } else {
                locationSharingEnabled
            }
            val autoCheckInEnabled = if (locationSharingEnabled) {
                restoredAutoCheckInEnabled
            } else {
                false
            }
            val autoCheckOutEnabled = if (locationSharingEnabled) {
                restoredAutoCheckOutEnabled
            } else {
                false
            }
            val storedRegistro = RegistroType.fromStorageName(json.getStringOrNull("registro"))
            val legacyInforme = InformeType.fromStorageName(json.getStringOrNull("informe"))

            return CheckingState(
                chave = sanitizeChave((json.getStringOrNull("chave") ?: "").uppercase()),
                registro = inferSuggestedRegistro(
                    lastCheckIn = null,
                    lastCheckOut = null,
                    fallback = storedRegistro,
                ),
                checkInInforme = json.getStringOrNull("checkInInforme")
                    ?.let(InformeType::fromStorageName)
                    ?: if (storedRegistro == RegistroType.CHECK_IN) legacyInforme else InformeType.NORMAL,
                checkOutInforme = json.getStringOrNull("checkOutInforme")
                    ?.let(InformeType::fromStorageName)
                    ?: if (storedRegistro == RegistroType.CHECK_OUT) legacyInforme else InformeType.NORMAL,
                checkInProjeto = ProjetoType.fromStorageName(
                    json.getStringOrNull("checkInProjeto") ?: json.getStringOrNull("projeto"),
                ),
                apiBaseUrl = json.getStringOrNull("apiBaseUrl")
                    ?.takeIf { value -> value.isNotBlank() }
                    ?: CheckingPresetConfig.apiBaseUrl,
                apiSharedKey = resolvedSharedKey,
                locationUpdateIntervalSeconds =
                    json.getIntOrNull("locationUpdateIntervalSeconds") ?: 15 * 60,
                nightUpdatesDisabled = json.getBooleanOrNull("nightUpdatesDisabled") ?: false,
                nightPeriodStartMinutes = json.getIntOrNull("nightPeriodStartMinutes") ?: 22 * 60,
                nightPeriodEndMinutes = json.getIntOrNull("nightPeriodEndMinutes") ?: 6 * 60,
                nightModeAfterCheckoutEnabled =
                    json.getBooleanOrNull("nightModeAfterCheckoutEnabled") ?: false,
                nightModeAfterCheckoutUntil =
                    parseOptionalInstant(json.getStringOrNull("nightModeAfterCheckoutUntil")),
                locationAccuracyThresholdMeters =
                    json.getIntOrNull("locationAccuracyThresholdMeters") ?: 30,
                locationSharingEnabled = locationSharingEnabled,
                canEnableLocationSharing = false,
                autoCheckInEnabled = autoCheckInEnabled,
                autoCheckOutEnabled = autoCheckOutEnabled,
                oemBackgroundSetupEnabled =
                    json.getBooleanOrNull("oemBackgroundSetupEnabled") ?: false,
                lastMatchedLocation =
                    normalizeOptionalText(json.getStringOrNull("lastMatchedLocation")),
                lastDetectedLocation =
                    normalizeOptionalText(json.getStringOrNull("lastDetectedLocation")),
                lastLocationUpdateAt =
                    parseOptionalInstant(json.getStringOrNull("lastLocationUpdateAt")),
                locationFetchHistory =
                    parseLocationFetchHistory(json.get("locationFetchHistory")),
                lastCheckInLocation =
                    normalizeOptionalText(json.getStringOrNull("lastCheckInLocation")),
                lastCheckIn = null,
                lastCheckOut = null,
                statusMessage = "",
                statusTone = StatusTone.NEUTRAL,
                isLoading = false,
                isSubmitting = false,
                isSyncing = false,
                isLocationUpdating = false,
                isAutomaticCheckingUpdating = false,
            )
        }

        private fun parseLocationFetchHistory(value: JsonElement?): List<LocationFetchEntry> {
            if (value == null || !value.isJsonArray) {
                return emptyList()
            }

            return LocationFetchEntry.normalizeHistory(
                entries = value.asJsonArray.mapNotNull(LocationFetchEntry::tryParse),
                maxEntries = LocationFetchEntry.maxStoredEntries,
            )
        }

        private fun normalizeOptionalText(value: String?): String? {
            val normalized = value?.trim()
            return normalized?.takeIf { item -> item.isNotEmpty() }
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

private fun JsonObject.getBooleanOrNull(key: String): Boolean? {
    val value = get(key) ?: return null
    if (value.isJsonNull || !value.isJsonPrimitive) {
        return null
    }
    return runCatching { value.asBoolean }.getOrNull()
}

private fun parseOptionalInstant(value: String?): Instant? {
    if (value.isNullOrBlank()) {
        return null
    }
    return runCatching { Instant.parse(value) }.getOrNull()
}
