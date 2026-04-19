package com.br.checkingnative.data.local.repository

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.br.checkingnative.data.legacy.LegacyFlutterStorageContract
import com.br.checkingnative.data.local.db.ManagedLocationEntity
import com.br.checkingnative.data.local.db.toDomainModel
import com.br.checkingnative.data.local.db.toEntity
import com.br.checkingnative.domain.model.ManagedLocation
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.first

@Singleton
class ManagedLocationCacheRepository @Inject constructor(
    private val dataStore: DataStore<Preferences>,
) {
    private object Keys {
        val locationsJson = stringPreferencesKey(
            LegacyFlutterStorageContract.locationsCachePrefsKey,
        )
    }

    suspend fun readLocations(): List<ManagedLocation> {
        val preferences = dataStore.data.first()
        return decodeLocations(preferences[Keys.locationsJson])
    }

    suspend fun saveLocations(items: List<ManagedLocation>) {
        dataStore.edit { preferences ->
            if (items.isEmpty()) {
                preferences.remove(Keys.locationsJson)
            } else {
                preferences[Keys.locationsJson] = encodeLocations(items)
            }
        }
    }

    private fun encodeLocations(items: List<ManagedLocation>): String {
        return JsonArray().apply {
            items.map(ManagedLocation::toEntity).forEach { entity ->
                add(entity.toCacheJson())
            }
        }.toString()
    }

    private fun decodeLocations(raw: String?): List<ManagedLocation> {
        if (raw.isNullOrBlank()) {
            return emptyList()
        }

        return runCatching {
            val parsed = JsonParser.parseString(raw)
            if (!parsed.isJsonArray) {
                return@runCatching emptyList()
            }

            parsed.asJsonArray.mapNotNull { item ->
                if (item.isJsonObject) {
                    item.asJsonObject.toManagedLocationEntity()?.toDomainModel()
                } else {
                    null
                }
            }
        }.getOrDefault(emptyList())
    }
}

private fun ManagedLocationEntity.toCacheJson(): JsonObject {
    return JsonObject().apply {
        addProperty("id", id)
        addProperty("local", local)
        addProperty("latitude", latitude)
        addProperty("longitude", longitude)
        if (!coordinatesJson.isNullOrBlank()) {
            addProperty("coordinates_json", coordinatesJson)
        }
        addProperty("tolerance_meters", toleranceMeters)
        addProperty("updated_at", updatedAt)
    }
}

private fun JsonObject.toManagedLocationEntity(): ManagedLocationEntity? {
    val id = getIntOrNull("id") ?: return null
    val local = getStringOrNull("local") ?: return null
    val latitude = getDoubleOrNull("latitude") ?: return null
    val longitude = getDoubleOrNull("longitude") ?: return null
    val toleranceMeters = getIntOrNull("tolerance_meters") ?: return null
    val updatedAt = getStringOrNull("updated_at") ?: return null

    return ManagedLocationEntity(
        id = id,
        local = local,
        latitude = latitude,
        longitude = longitude,
        coordinatesJson = getStringOrNull("coordinates_json"),
        toleranceMeters = toleranceMeters,
        updatedAt = updatedAt,
    )
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
