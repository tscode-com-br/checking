package com.br.checkingnative.domain.model

import java.time.Instant

data class CheckingLocationSample(
    val timestamp: Instant,
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Double?,
)
