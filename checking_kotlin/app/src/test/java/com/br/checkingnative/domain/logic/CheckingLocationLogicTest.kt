package com.br.checkingnative.domain.logic

import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.LocationFetchEntry
import com.br.checkingnative.domain.model.ManagedLocation
import com.br.checkingnative.domain.model.ManagedLocationCoordinate
import com.br.checkingnative.domain.model.MobileStateResponse
import com.br.checkingnative.domain.model.RegistroType
import com.br.checkingnative.domain.model.StatusTone
import java.time.Instant
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CheckingLocationLogicTest {
    @Test
    fun resolveNightModeAfterCheckoutUntil_computesNextSingaporeMorning() {
        val resumeAt = CheckingLocationLogic.resolveNightModeAfterCheckoutUntil(
            checkoutTime = Instant.parse("2026-04-17T11:30:00Z"),
        )

        assertEquals("2026-04-17T22:00:00Z", resumeAt.toString())
    }

    @Test
    fun shouldRunBackgroundActivityNow_respectsConfiguredNightWindow() {
        val state = CheckingState.initial().copy(
            nightUpdatesDisabled = true,
            nightPeriodStartMinutes = 22 * 60,
            nightPeriodEndMinutes = 6 * 60,
        )

        assertFalse(
            CheckingLocationLogic.shouldRunBackgroundActivityNow(
                state = state,
                referenceTime = Instant.parse("2026-04-20T15:30:00Z"),
            ),
        )
        assertTrue(
            CheckingLocationLogic.shouldRunBackgroundActivityNow(
                state = state,
                referenceTime = Instant.parse("2026-04-20T01:00:00Z"),
            ),
        )
    }

    @Test
    fun resolveLocationMatch_prioritizesCheckoutZoneAndTracksNearestWorkplace() {
        val result = CheckingLocationLogic.resolveLocationMatch(
            managedLocations = buildScenarioLocations(),
            latitude = 1.266058,
            longitude = 103.614415,
        )

        assertTrue(result.matchedLocation?.isCheckoutZone == true)
        assertTrue(result.nearestWorkplaceDistanceMeters != null)
    }

    @Test
    fun resolveAutomaticActionForLocation_returnsCheckoutInCheckoutZoneAfterCheckIn() {
        val matchedLocation = buildScenarioLocations().last()

        val action = CheckingLocationLogic.resolveAutomaticActionForLocation(
            remoteState = buildScenarioRemoteState(
                lastAction = RegistroType.CHECK_IN,
                currentLocal = "Escritorio Principal",
            ),
            location = matchedLocation,
            autoCheckInEnabled = true,
            autoCheckOutEnabled = true,
            lastCheckInLocation = "Escritorio Principal",
        )

        assertEquals(RegistroType.CHECK_OUT, action)
        assertEquals(
            "Zona de CheckOut",
            CheckingLocationLogic.resolveAutomaticEventLocal(
                action = RegistroType.CHECK_OUT,
                location = matchedLocation,
            ),
        )
    }

    @Test
    fun resolveAutomaticActionWithoutLocationMatch_checksInNearWorkplaceAfterCheckout() {
        val action = CheckingLocationLogic.resolveAutomaticActionWithoutLocationMatch(
            remoteState = buildScenarioRemoteState(lastAction = RegistroType.CHECK_OUT),
            nearestDistanceMeters = 1500.0,
            autoCheckInEnabled = true,
            autoCheckOutEnabled = true,
        )

        assertEquals(RegistroType.CHECK_IN, action)
        assertEquals(
            CheckingLocationLogic.uncatalogedCapturedLocation,
            CheckingLocationLogic.resolveCapturedLocationLabel(
                location = null,
                nearestWorkplaceDistanceMeters = 1500.0,
            ),
        )
    }

    @Test
    fun recordLocationFetchHistory_deduplicatesConsecutiveCoordinates() {
        var history = emptyList<LocationFetchEntry>()
        history = CheckingLocationLogic.recordLocationFetchHistory(
            history = history,
            timestamp = Instant.parse("2026-04-18T08:00:00Z"),
            latitude = 1.249494,
            longitude = 103.614345,
        )
        history = CheckingLocationLogic.recordLocationFetchHistory(
            history = history,
            timestamp = Instant.parse("2026-04-18T08:00:00.500Z"),
            latitude = 1.249494,
            longitude = 103.614345,
        )

        assertEquals(1, history.size)
        assertTrue(
            CheckingLocationLogic.shouldSkipDuplicateLocationFetch(
                history = history,
                timestamp = Instant.parse("2026-04-18T08:00:00.700Z"),
                latitude = 1.249494,
                longitude = 103.614345,
            ),
        )
    }

    @Test
    fun applyRemoteState_updatesSuggestionAndLastCheckInLocation() {
        val nextState = CheckingLocationLogic.applyRemoteState(
            currentState = CheckingState.initial().copy(
                registro = RegistroType.CHECK_IN,
            ),
            response = buildScenarioRemoteState(
                lastAction = RegistroType.CHECK_IN,
                currentLocal = "Base P80",
            ),
            statusMessage = "Sincronizado",
            tone = StatusTone.SUCCESS,
            updateStatus = true,
        )

        assertEquals(RegistroType.CHECK_OUT, nextState.registro)
        assertEquals("Base P80", nextState.lastCheckInLocation)
        assertEquals(StatusTone.SUCCESS, nextState.statusTone)
        assertEquals("Sincronizado", nextState.statusMessage)
    }
}

private fun buildScenarioLocations(): List<ManagedLocation> {
    val updatedAt = Instant.parse("2026-04-15T07:00:00Z")
    return listOf(
        ManagedLocation(
            id = 200,
            local = "Escritorio Principal",
            latitude = 1.249494,
            longitude = 103.614345,
            coordinates = listOf(
                ManagedLocationCoordinate(1.249494, 103.614345),
            ),
            toleranceMeters = 150,
            updatedAt = updatedAt,
        ),
        ManagedLocation(
            id = 201,
            local = "Em Deslocamento",
            latitude = 1.25129,
            longitude = 103.613386,
            coordinates = listOf(
                ManagedLocationCoordinate(1.25129, 103.613386),
            ),
            toleranceMeters = 150,
            updatedAt = updatedAt,
        ),
        ManagedLocation(
            id = 202,
            local = "Zona de CheckOut",
            latitude = 1.266058,
            longitude = 103.614415,
            coordinates = listOf(
                ManagedLocationCoordinate(1.266058, 103.614415),
            ),
            toleranceMeters = 150,
            updatedAt = updatedAt,
        ),
    )
}

private fun buildScenarioRemoteState(
    lastAction: RegistroType,
    currentLocal: String? = null,
): MobileStateResponse {
    return when (lastAction) {
        RegistroType.CHECK_IN -> MobileStateResponse(
            found = true,
            chave = "HR70",
            nome = "Usuario Teste",
            projeto = "P80",
            currentAction = "checkin",
            currentEventTime = Instant.parse("2026-04-14T18:00:00Z"),
            currentLocal = currentLocal,
            lastCheckInAt = Instant.parse("2026-04-14T18:00:00Z"),
            lastCheckOutAt = Instant.parse("2026-04-13T18:00:00Z"),
        )
        RegistroType.CHECK_OUT -> MobileStateResponse(
            found = true,
            chave = "HR70",
            nome = "Usuario Teste",
            projeto = "P80",
            currentAction = "checkout",
            currentEventTime = Instant.parse("2026-04-14T18:00:00Z"),
            currentLocal = currentLocal,
            lastCheckInAt = Instant.parse("2026-04-14T07:00:00Z"),
            lastCheckOutAt = Instant.parse("2026-04-14T18:00:00Z"),
        )
    }
}
