package com.br.checkingnative.data.local.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey
import com.br.checkingnative.data.legacy.LegacyFlutterStorageContract
import com.br.checkingnative.domain.model.ManagedLocation
import com.br.checkingnative.domain.model.ManagedLocationCoordinate
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.time.Instant

@Entity(tableName = LegacyFlutterStorageContract.locationsTableName)
data class ManagedLocationEntity(
    @PrimaryKey
    val id: Int,
    val local: String,
    val latitude: Double,
    val longitude: Double,
    @ColumnInfo(name = "coordinates_json")
    val coordinatesJson: String? = null,
    @ColumnInfo(name = "tolerance_meters")
    val toleranceMeters: Int,
    @ColumnInfo(name = "updated_at")
    val updatedAt: String,
)

fun ManagedLocationEntity.toDomainModel(): ManagedLocation {
    return ManagedLocation(
        id = id,
        local = local.trim(),
        latitude = latitude,
        longitude = longitude,
        coordinates = parseCoordinates(
            raw = coordinatesJson,
            fallbackLatitude = latitude,
            fallbackLongitude = longitude,
        ),
        toleranceMeters = toleranceMeters,
        updatedAt = parseOptionalInstant(updatedAt) ?: Instant.EPOCH,
    )
}

fun ManagedLocation.toEntity(): ManagedLocationEntity {
    return ManagedLocationEntity(
        id = id,
        local = local,
        latitude = latitude,
        longitude = longitude,
        coordinatesJson = JsonArray().apply {
            coordinates.forEach { coordinate ->
                add(
                    JsonObject().apply {
                        addProperty("latitude", coordinate.latitude)
                        addProperty("longitude", coordinate.longitude)
                    },
                )
            }
        }.toString(),
        toleranceMeters = toleranceMeters,
        updatedAt = updatedAt.toString(),
    )
}

private fun parseCoordinates(
    raw: String?,
    fallbackLatitude: Double,
    fallbackLongitude: Double,
): List<ManagedLocationCoordinate> {
    val parsedCoordinates = runCatching {
        if (raw.isNullOrBlank()) {
            emptyList()
        } else {
            val payload = JsonParser.parseString(raw)
            if (!payload.isJsonArray) {
                emptyList()
            } else {
                payload.asJsonArray.mapNotNull { item ->
                    if (!item.isJsonObject) {
                        return@mapNotNull null
                    }
                    ManagedLocationCoordinate(
                        latitude = item.asJsonObject.getDoubleOrNull("latitude") ?: 0.0,
                        longitude = item.asJsonObject.getDoubleOrNull("longitude") ?: 0.0,
                    )
                }
            }
        }
    }.getOrDefault(emptyList())

    if (parsedCoordinates.isNotEmpty()) {
        return parsedCoordinates
    }

    return listOf(
        ManagedLocationCoordinate(
            latitude = fallbackLatitude,
            longitude = fallbackLongitude,
        ),
    )
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
