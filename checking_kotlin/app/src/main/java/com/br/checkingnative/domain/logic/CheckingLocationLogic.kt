package com.br.checkingnative.domain.logic

import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.LocationFetchEntry
import com.br.checkingnative.domain.model.ManagedLocation
import com.br.checkingnative.domain.model.ManagedLocationCoordinate
import com.br.checkingnative.domain.model.MobileStateResponse
import com.br.checkingnative.domain.model.ProjetoType
import com.br.checkingnative.domain.model.RegistroType
import com.br.checkingnative.domain.model.StatusTone
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.ZoneId
import java.time.ZoneOffset
import kotlin.math.PI
import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.pow
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

data class CheckingLocationMatchResult(
    val matchedLocation: ManagedLocation?,
    val nearestWorkplaceDistanceMeters: Double?,
)

object CheckingLocationLogic {
    const val outOfRangeCheckoutDistanceMeters: Double = 2000.0
    const val defaultLocationAccuracyThresholdMeters: Double = 30.0
    const val maxLocationFetchHistoryEntries: Int = LocationFetchEntry.maxStoredEntries
    const val minLocationUpdateIntervalMinutes: Int = 15
    const val maxLocationUpdateIntervalMinutes: Int = 60
    const val defaultLocationUpdateIntervalSeconds: Int = 15 * 60
    const val defaultNightPeriodStartMinutes: Int = 22 * 60
    const val defaultNightPeriodEndMinutes: Int = 6 * 60
    const val postCheckoutNightModeResumeMinutes: Int = 6 * 60
    const val automaticCheckoutLocation: String = "Fora do Local de Trabalho"
    const val outsideWorkplaceCapturedLocation: String = "Fora do Ambiente de Trabalho"
    const val checkoutZoneCapturedLocation: String = "Zona de Check-Out"
    const val uncatalogedCapturedLocation: String = "Localização não Cadastrada"
    const val postCheckoutNightModeStatusMessage: String =
        "Modo noturno após check-out ativo até 06:00 do dia seguinte, no horário de Singapura."

    private val singaporeOffset: ZoneOffset = ZoneOffset.ofHours(8)
    private val systemZone: ZoneId
        get() = ZoneId.systemDefault()

    fun resolveLocationUpdateIntervalSeconds(
        configuredIntervalSeconds: Int? = null,
        referenceTime: Instant? = null,
    ): Int {
        return normalizeLocationUpdateIntervalSeconds(
            configuredIntervalSeconds ?: defaultLocationUpdateIntervalSeconds,
        )
    }

    fun describeLocationUpdateInterval(
        configuredIntervalSeconds: Int? = null,
        referenceTime: Instant? = null,
    ): String {
        val intervalSeconds = resolveLocationUpdateIntervalSeconds(
            configuredIntervalSeconds = configuredIntervalSeconds,
            referenceTime = referenceTime,
        )
        return "${intervalSeconds / 60} min"
    }

    fun resolveLocationUpdateIntervalState(
        state: CheckingState,
        referenceTime: Instant? = null,
    ): CheckingState {
        val resolvedIntervalSeconds = resolveLocationUpdateIntervalSeconds(
            configuredIntervalSeconds = state.locationUpdateIntervalSeconds,
            referenceTime = referenceTime,
        )
        val normalizedNightPeriodStartMinutes = normalizeMinutesOfDay(
            state.nightPeriodStartMinutes,
            fallbackMinutes = defaultNightPeriodStartMinutes,
        )
        val normalizedNightPeriodEndMinutes = normalizeMinutesOfDay(
            state.nightPeriodEndMinutes,
            fallbackMinutes = defaultNightPeriodEndMinutes,
        )
        val normalizedNightModeAfterCheckoutUntil = normalizeNightModeAfterCheckoutUntil(
            state = state,
            referenceTime = referenceTime,
        )

        if (
            resolvedIntervalSeconds == state.locationUpdateIntervalSeconds &&
            normalizedNightPeriodStartMinutes == state.nightPeriodStartMinutes &&
            normalizedNightPeriodEndMinutes == state.nightPeriodEndMinutes &&
            normalizedNightModeAfterCheckoutUntil == state.nightModeAfterCheckoutUntil
        ) {
            return state
        }

        return state.copy(
            locationUpdateIntervalSeconds = resolvedIntervalSeconds,
            nightPeriodStartMinutes = normalizedNightPeriodStartMinutes,
            nightPeriodEndMinutes = normalizedNightPeriodEndMinutes,
            nightModeAfterCheckoutUntil = normalizedNightModeAfterCheckoutUntil,
        )
    }

    fun delayUntilNextLocationUpdateIntervalBoundary(
        state: CheckingState,
        referenceTime: Instant? = null,
    ): Duration {
        val normalizedNightModeAfterCheckoutUntil = normalizeNightModeAfterCheckoutUntil(
            state = state,
            referenceTime = referenceTime,
        )
        if (normalizedNightModeAfterCheckoutUntil != null) {
            val now = referenceTime ?: Instant.now()
            val delay = Duration.between(now, normalizedNightModeAfterCheckoutUntil)
            if (delay.isNegative || delay.isZero) {
                return Duration.ofMinutes(1)
            }
            return delay
        }

        if (state.nightModeAfterCheckoutEnabled) {
            return Duration.ofDays(1)
        }

        if (!state.nightUpdatesDisabled || state.nightPeriodStartMinutes == state.nightPeriodEndMinutes) {
            return Duration.ofDays(1)
        }

        val now = referenceTime ?: Instant.now()
        val nextBoundary = resolveNextNightPeriodBoundary(
            referenceTime = now,
            startMinutes = state.nightPeriodStartMinutes,
            endMinutes = state.nightPeriodEndMinutes,
        ) ?: return Duration.ofDays(1)

        val delay = Duration.between(now, nextBoundary)
        if (delay.isNegative || delay.isZero) {
            return Duration.ofMinutes(1)
        }
        return delay
    }

    fun normalizeLocationUpdateIntervalSeconds(seconds: Int): Int {
        val normalizedMinutes = (seconds / 60.0).roundToInt()
            .coerceIn(minLocationUpdateIntervalMinutes, maxLocationUpdateIntervalMinutes)
        return normalizedMinutes * 60
    }

    fun normalizeMinutesOfDay(
        minutes: Int,
        fallbackMinutes: Int,
    ): Int {
        val minutesPerDay = 24 * 60
        val normalized = minutes % minutesPerDay
        return if (normalized < 0) normalized + minutesPerDay else normalized
    }

    fun isNightPeriodActive(
        state: CheckingState,
        referenceTime: Instant? = null,
    ): Boolean {
        if (state.nightModeAfterCheckoutEnabled) {
            return false
        }

        if (!state.nightUpdatesDisabled || state.nightPeriodStartMinutes == state.nightPeriodEndMinutes) {
            return false
        }

        val now = (referenceTime ?: Instant.now()).atZone(systemZone).toLocalDateTime()
        val currentMinutes = now.hour * 60 + now.minute
        val startMinutes = normalizeMinutesOfDay(
            state.nightPeriodStartMinutes,
            fallbackMinutes = defaultNightPeriodStartMinutes,
        )
        val endMinutes = normalizeMinutesOfDay(
            state.nightPeriodEndMinutes,
            fallbackMinutes = defaultNightPeriodEndMinutes,
        )
        return if (startMinutes < endMinutes) {
            currentMinutes in startMinutes until endMinutes
        } else {
            currentMinutes >= startMinutes || currentMinutes < endMinutes
        }
    }

    fun resolveNextNightPeriodBoundary(
        referenceTime: Instant,
        startMinutes: Int,
        endMinutes: Int,
    ): Instant? {
        val normalizedStartMinutes = normalizeMinutesOfDay(
            startMinutes,
            fallbackMinutes = defaultNightPeriodStartMinutes,
        )
        val normalizedEndMinutes = normalizeMinutesOfDay(
            endMinutes,
            fallbackMinutes = defaultNightPeriodEndMinutes,
        )
        if (normalizedStartMinutes == normalizedEndMinutes) {
            return null
        }

        val referenceDateTime = referenceTime.atZone(systemZone).toLocalDateTime()
        val today = referenceDateTime.toLocalDate()
        val currentMinutes = referenceDateTime.hour * 60 + referenceDateTime.minute
        val startToday = localDateTimeToInstant(today, normalizedStartMinutes)
        val endToday = localDateTimeToInstant(today, normalizedEndMinutes)
        val spansMidnight = normalizedStartMinutes > normalizedEndMinutes
        if (!spansMidnight) {
            return when {
                currentMinutes < normalizedStartMinutes -> startToday
                currentMinutes < normalizedEndMinutes -> endToday
                else -> startToday.plus(Duration.ofDays(1))
            }
        }

        return when {
            currentMinutes >= normalizedStartMinutes -> endToday.plus(Duration.ofDays(1))
            currentMinutes < normalizedEndMinutes -> endToday
            else -> startToday
        }
    }

    fun shouldRunBackgroundActivityNow(
        state: CheckingState,
        referenceTime: Instant? = null,
    ): Boolean {
        if (isNightModeAfterCheckoutActive(state = state, referenceTime = referenceTime)) {
            return false
        }

        if (state.nightModeAfterCheckoutEnabled) {
            return true
        }

        return !isNightPeriodActive(state = state, referenceTime = referenceTime)
    }

    fun resolveNightModeAfterCheckoutUntil(checkoutTime: Instant): Instant {
        val checkoutTimeInSingapore = checkoutTime.atOffset(ZoneOffset.UTC)
            .withOffsetSameInstant(singaporeOffset)
        val nextDayAtSixInSingapore = checkoutTimeInSingapore.toLocalDate()
            .plusDays(1)
            .atTime(6, 0)
            .atOffset(singaporeOffset)
        return nextDayAtSixInSingapore.toInstant()
    }

    fun normalizeNightModeAfterCheckoutUntil(
        state: CheckingState,
        referenceTime: Instant? = null,
    ): Instant? {
        if (!state.nightModeAfterCheckoutEnabled) {
            return null
        }

        val nightModeAfterCheckoutUntil = state.nightModeAfterCheckoutUntil ?: return null
        val now = referenceTime ?: Instant.now()
        return if (nightModeAfterCheckoutUntil.isAfter(now)) {
            nightModeAfterCheckoutUntil
        } else {
            null
        }
    }

    fun isNightModeAfterCheckoutActive(
        state: CheckingState,
        referenceTime: Instant? = null,
    ): Boolean {
        return normalizeNightModeAfterCheckoutUntil(
            state = state,
            referenceTime = referenceTime,
        ) != null
    }

    fun resolveNightModeAfterCheckoutUntilForAction(
        currentState: CheckingState,
        effectiveLastAction: RegistroType?,
        lastCheckOut: Instant?,
        referenceTime: Instant? = null,
    ): Instant? {
        if (!currentState.nightModeAfterCheckoutEnabled) {
            return null
        }

        val now = referenceTime ?: Instant.now()
        if (effectiveLastAction == RegistroType.CHECK_OUT && lastCheckOut != null) {
            val nightModeAfterCheckoutUntil = resolveNightModeAfterCheckoutUntil(lastCheckOut)
            return nightModeAfterCheckoutUntil.takeIf { it.isAfter(now) }
        }

        if (effectiveLastAction == RegistroType.CHECK_IN) {
            return null
        }

        val existing = currentState.nightModeAfterCheckoutUntil
        return if (existing != null && existing.isAfter(now)) existing else null
    }

    fun resolveDistanceToLocation(
        location: ManagedLocation,
        latitude: Double,
        longitude: Double,
    ): Double {
        val coordinates = if (location.coordinates.isEmpty()) {
            listOf(
                ManagedLocationCoordinate(
                    latitude = location.latitude,
                    longitude = location.longitude,
                ),
            )
        } else {
            location.coordinates
        }
        return coordinates.minOf { coordinate ->
            distanceBetween(
                latitude,
                longitude,
                coordinate.latitude,
                coordinate.longitude,
            )
        }
    }

    fun resolveLocationMatch(
        managedLocations: List<ManagedLocation>,
        latitude: Double,
        longitude: Double,
    ): CheckingLocationMatchResult {
        var nearestRegularLocation: ManagedLocation? = null
        var nearestRegularDistanceMeters: Double? = null
        var nearestCheckoutLocation: ManagedLocation? = null
        var nearestCheckoutDistanceMeters: Double? = null
        var nearestWorkplaceDistanceMeters: Double? = null

        for (location in managedLocations) {
            val distanceMeters = resolveDistanceToLocation(
                location = location,
                latitude = latitude,
                longitude = longitude,
            )

            if (!location.isCheckoutZone && (
                    nearestWorkplaceDistanceMeters == null ||
                        distanceMeters < nearestWorkplaceDistanceMeters
                    )
            ) {
                nearestWorkplaceDistanceMeters = distanceMeters
            }

            if (distanceMeters > location.toleranceMeters) {
                continue
            }

            if (location.isCheckoutZone) {
                if (nearestCheckoutDistanceMeters == null || distanceMeters < nearestCheckoutDistanceMeters) {
                    nearestCheckoutLocation = location
                    nearestCheckoutDistanceMeters = distanceMeters
                }
                continue
            }

            if (nearestRegularDistanceMeters == null || distanceMeters < nearestRegularDistanceMeters) {
                nearestRegularLocation = location
                nearestRegularDistanceMeters = distanceMeters
            }
        }

        return CheckingLocationMatchResult(
            matchedLocation = nearestCheckoutLocation ?: nearestRegularLocation,
            nearestWorkplaceDistanceMeters = nearestWorkplaceDistanceMeters,
        )
    }

    fun resolveAutomaticActionForLocation(
        remoteState: MobileStateResponse,
        location: ManagedLocation,
        autoCheckInEnabled: Boolean,
        autoCheckOutEnabled: Boolean,
        lastCheckInLocation: String?,
    ): RegistroType? {
        val lastRecordedAction = resolveLastRecordedAction(remoteState)
        val recordedCheckInLocation = resolveRecordedCheckInLocation(
            remoteState = remoteState,
            fallbackLocation = lastCheckInLocation,
        )
        if (!shouldAttemptAutomaticLocationEvent(
                location = location,
                lastRecordedAction = lastRecordedAction,
                lastCheckInLocation = recordedCheckInLocation,
                autoCheckInEnabled = autoCheckInEnabled,
                autoCheckOutEnabled = autoCheckOutEnabled,
            )
        ) {
            return null
        }

        return if (location.isCheckoutZone) RegistroType.CHECK_OUT else RegistroType.CHECK_IN
    }

    fun shouldAttemptAutomaticLocationEvent(
        location: ManagedLocation,
        lastRecordedAction: RegistroType?,
        lastCheckInLocation: String?,
        autoCheckInEnabled: Boolean,
        autoCheckOutEnabled: Boolean,
    ): Boolean {
        if (location.isCheckoutZone) {
            return autoCheckOutEnabled && lastRecordedAction == RegistroType.CHECK_IN
        }

        if (!autoCheckInEnabled) {
            return false
        }
        if (lastRecordedAction != RegistroType.CHECK_IN) {
            return true
        }
        return !location.matchesLocationName(lastCheckInLocation)
    }

    fun resolveAutomaticActionOutOfRange(
        remoteState: MobileStateResponse,
        nearestDistanceMeters: Double?,
        autoCheckOutEnabled: Boolean,
    ): RegistroType? {
        return if (
            shouldAttemptAutomaticOutOfRangeCheckout(
                lastRecordedAction = resolveLastRecordedAction(remoteState),
                nearestDistanceMeters = nearestDistanceMeters,
                autoCheckOutEnabled = autoCheckOutEnabled,
            )
        ) {
            RegistroType.CHECK_OUT
        } else {
            null
        }
    }

    fun resolveAutomaticActionWithoutLocationMatch(
        remoteState: MobileStateResponse,
        nearestDistanceMeters: Double?,
        autoCheckInEnabled: Boolean,
        autoCheckOutEnabled: Boolean,
    ): RegistroType? {
        val outOfRangeAction = resolveAutomaticActionOutOfRange(
            remoteState = remoteState,
            nearestDistanceMeters = nearestDistanceMeters,
            autoCheckOutEnabled = autoCheckOutEnabled,
        )
        if (outOfRangeAction != null) {
            return outOfRangeAction
        }

        return if (
            shouldAttemptAutomaticNearbyWorkplaceCheckIn(
                lastRecordedAction = resolveLastRecordedAction(remoteState),
                nearestDistanceMeters = nearestDistanceMeters,
                autoCheckInEnabled = autoCheckInEnabled,
            )
        ) {
            RegistroType.CHECK_IN
        } else {
            null
        }
    }

    fun shouldAttemptAutomaticOutOfRangeCheckout(
        lastRecordedAction: RegistroType?,
        nearestDistanceMeters: Double?,
        autoCheckOutEnabled: Boolean,
    ): Boolean {
        if (
            !autoCheckOutEnabled ||
            nearestDistanceMeters == null ||
            nearestDistanceMeters <= outOfRangeCheckoutDistanceMeters
        ) {
            return false
        }
        return lastRecordedAction == RegistroType.CHECK_IN
    }

    fun shouldAttemptAutomaticNearbyWorkplaceCheckIn(
        lastRecordedAction: RegistroType?,
        nearestDistanceMeters: Double?,
        autoCheckInEnabled: Boolean,
    ): Boolean {
        if (
            !autoCheckInEnabled ||
            nearestDistanceMeters == null ||
            nearestDistanceMeters > outOfRangeCheckoutDistanceMeters
        ) {
            return false
        }
        return lastRecordedAction != RegistroType.CHECK_IN
    }

    fun resolveAutomaticEventLocal(
        action: RegistroType,
        location: ManagedLocation? = null,
    ): String {
        if (action == RegistroType.CHECK_OUT) {
            if (location != null && location.isCheckoutZone) {
                return location.automationAreaLabel
            }
            return automaticCheckoutLocation
        }

        return location?.local ?: uncatalogedCapturedLocation
    }

    fun resolveCapturedLocationLabel(
        location: ManagedLocation?,
        nearestWorkplaceDistanceMeters: Double? = null,
    ): String? {
        if (location == null) {
            if (nearestWorkplaceDistanceMeters == null) {
                return null
            }
            return if (nearestWorkplaceDistanceMeters > outOfRangeCheckoutDistanceMeters) {
                outsideWorkplaceCapturedLocation
            } else {
                uncatalogedCapturedLocation
            }
        }
        return if (location.isCheckoutZone) {
            checkoutZoneCapturedLocation
        } else {
            location.local
        }
    }

    fun recordLocationFetchHistory(
        history: List<LocationFetchEntry>,
        timestamp: Instant,
        latitude: Double,
        longitude: Double,
        maxEntries: Int = maxLocationFetchHistoryEntries,
    ): List<LocationFetchEntry> {
        val effectiveMaxEntries = max(1, maxEntries)
        return LocationFetchEntry.normalizeHistory(
            entries = listOf(
                LocationFetchEntry(
                    timestamp = timestamp,
                    latitude = latitude,
                    longitude = longitude,
                ),
            ) + history,
            maxEntries = effectiveMaxEntries,
        )
    }

    fun shouldSkipDuplicateLocationFetch(
        history: List<LocationFetchEntry>,
        timestamp: Instant,
        latitude: Double,
        longitude: Double,
    ): Boolean {
        if (history.isEmpty()) {
            return false
        }

        return LocationFetchEntry(
            timestamp = timestamp,
            latitude = latitude,
            longitude = longitude,
        ).isDuplicateOf(history.first())
    }

    fun isLocationAccuracyPreciseEnough(
        accuracyMeters: Double?,
        maxAccuracyMeters: Double = defaultLocationAccuracyThresholdMeters,
    ): Boolean {
        if (accuracyMeters == null || accuracyMeters.isNaN()) {
            return false
        }
        return accuracyMeters <= maxAccuracyMeters
    }

    fun resolveLastRecordedAction(remoteState: MobileStateResponse): RegistroType? {
        val lastCheckInAt = remoteState.lastCheckInAt
        val lastCheckOutAt = remoteState.lastCheckOutAt
        if (lastCheckInAt == null && lastCheckOutAt == null) {
            return parseRemoteAction(remoteState.currentAction)
        }
        if (lastCheckInAt != null && lastCheckOutAt == null) {
            return RegistroType.CHECK_IN
        }
        if (lastCheckInAt == null && lastCheckOutAt != null) {
            return RegistroType.CHECK_OUT
        }
        return when {
            lastCheckInAt!!.isAfter(lastCheckOutAt) -> RegistroType.CHECK_IN
            lastCheckOutAt!!.isAfter(lastCheckInAt) -> RegistroType.CHECK_OUT
            else -> parseRemoteAction(remoteState.currentAction)
        }
    }

    fun resolveRecordedCheckInLocation(
        remoteState: MobileStateResponse,
        fallbackLocation: String?,
    ): String? {
        if (parseRemoteAction(remoteState.currentAction) == RegistroType.CHECK_IN) {
            val currentLocal = normalizeOptionalLocationName(remoteState.currentLocal)
            if (currentLocal != null) {
                return currentLocal
            }
        }
        return normalizeOptionalLocationName(fallbackLocation)
    }

    fun applyRemoteState(
        currentState: CheckingState,
        response: MobileStateResponse,
        statusMessage: String,
        tone: StatusTone,
        updateStatus: Boolean = true,
        recentAction: RegistroType? = null,
        recentLocal: String? = null,
    ): CheckingState {
        val suggestedRegistro = CheckingState.inferSuggestedRegistro(
            lastCheckIn = response.lastCheckInAt,
            lastCheckOut = response.lastCheckOutAt,
            fallback = currentState.registro,
        )
        val remoteLastRecordedAction = resolveLastRecordedAction(response)
        var nextLastCheckInLocation = currentState.lastCheckInLocation
        when (recentAction) {
            RegistroType.CHECK_IN -> {
                nextLastCheckInLocation = normalizeOptionalLocationName(recentLocal)
            }
            RegistroType.CHECK_OUT -> {
                nextLastCheckInLocation = null
            }
            null -> {
                when (remoteLastRecordedAction) {
                    RegistroType.CHECK_IN -> {
                        nextLastCheckInLocation = resolveRecordedCheckInLocation(
                            remoteState = response,
                            fallbackLocation = currentState.lastCheckInLocation,
                        )
                    }
                    RegistroType.CHECK_OUT -> nextLastCheckInLocation = null
                    null -> Unit
                }
            }
        }
        val nextNightModeAfterCheckoutUntil = resolveNightModeAfterCheckoutUntilForAction(
            currentState = currentState,
            effectiveLastAction = recentAction ?: remoteLastRecordedAction,
            lastCheckOut = response.lastCheckOutAt,
        )

        return currentState.copy(
            lastCheckIn = response.lastCheckInAt,
            lastCheckOut = response.lastCheckOutAt,
            lastCheckInLocation = nextLastCheckInLocation,
            nightModeAfterCheckoutUntil = nextNightModeAfterCheckoutUntil,
            registro = suggestedRegistro,
            checkInProjeto = resolveProjeto(response.projeto) ?: currentState.projeto,
            statusMessage = if (updateStatus) statusMessage else currentState.statusMessage,
            statusTone = if (updateStatus) tone else currentState.statusTone,
        )
    }

    fun resolveProjeto(value: String?): ProjetoType? {
        return when (value?.trim()?.uppercase()) {
            "P80" -> ProjetoType.P80
            "P82" -> ProjetoType.P82
            "P83" -> ProjetoType.P83
            else -> null
        }
    }

    fun normalizeOptionalLocationName(value: String?): String? {
        val normalized = value?.trim()?.replace(Regex("\\s+"), " ")
        return normalized?.takeIf { item -> item.isNotEmpty() }
    }

    private fun parseRemoteAction(value: String?): RegistroType? {
        return when (value?.trim()?.lowercase()) {
            "checkin" -> RegistroType.CHECK_IN
            "checkout" -> RegistroType.CHECK_OUT
            else -> null
        }
    }

    private fun distanceBetween(
        startLatitude: Double,
        startLongitude: Double,
        endLatitude: Double,
        endLongitude: Double,
    ): Double {
        val earthRadiusMeters = 6_371_000.0
        val startLatitudeRadians = startLatitude.toRadians()
        val endLatitudeRadians = endLatitude.toRadians()
        val latitudeDeltaRadians = (endLatitude - startLatitude).toRadians()
        val longitudeDeltaRadians = (endLongitude - startLongitude).toRadians()

        val haversine = sin(latitudeDeltaRadians / 2).pow(2) +
            cos(startLatitudeRadians) *
            cos(endLatitudeRadians) *
            sin(longitudeDeltaRadians / 2).pow(2)

        return 2 * earthRadiusMeters * asin(sqrt(haversine))
    }

    private fun localDateTimeToInstant(date: LocalDate, minutes: Int): Instant {
        val localDateTime = LocalDateTime.of(
            date,
            LocalTime.of(minutes / 60, minutes % 60),
        )
        return localDateTime.atZone(systemZone).toInstant()
    }

    private fun Double.toRadians(): Double = this * PI / 180.0
}
