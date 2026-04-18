package com.br.checkingnative.domain.logic

import com.br.checkingnative.domain.model.CheckingPermissionSettingsState
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.ManagedLocation
import com.br.checkingnative.domain.model.ManagedLocationCoordinate
import java.time.Instant
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CheckingRuntimeLogicTest {
    @Test
    fun resolveManagedLocationForLastCapture_prefersDetectedLocation() {
        val checkoutLocation = ManagedLocation(
            id = 7,
            local = "Zona de CheckOut 3",
            latitude = 1.0,
            longitude = 1.0,
            coordinates = listOf(ManagedLocationCoordinate(1.0, 1.0)),
            toleranceMeters = 200,
            updatedAt = Instant.parse("2026-04-15T00:00:00Z"),
        )
        val regularLocation = ManagedLocation(
            id = 8,
            local = "Base P80",
            latitude = 1.0,
            longitude = 1.0,
            coordinates = listOf(ManagedLocationCoordinate(1.0, 1.0)),
            toleranceMeters = 200,
            updatedAt = Instant.parse("2026-04-15T00:00:00Z"),
        )

        val resolved = CheckingRuntimeLogic.resolveManagedLocationForLastCapture(
            managedLocations = listOf(regularLocation, checkoutLocation),
            lastMatchedLocation = "Zona de CheckOut",
            lastDetectedLocation = "Zona de CheckOut 3",
        )

        assertEquals(checkoutLocation, resolved)
    }

    @Test
    fun reconcilePermissionBackedSwitches_turnsOffLocationSharingAndClearsMatchedLocation() {
        val reconciledState = CheckingRuntimeLogic.reconcilePermissionBackedSwitches(
            state = CheckingState.initial().copy(
                canEnableLocationSharing = true,
                locationSharingEnabled = true,
                autoCheckInEnabled = true,
                autoCheckOutEnabled = true,
                oemBackgroundSetupEnabled = true,
                lastMatchedLocation = "Base P80",
            ),
            canEnableLocationSharing = false,
        )

        assertFalse(reconciledState.canEnableLocationSharing)
        assertFalse(reconciledState.locationSharingEnabled)
        assertFalse(reconciledState.oemBackgroundSetupEnabled)
        assertEquals(null, reconciledState.lastMatchedLocation)
        assertTrue(reconciledState.autoCheckInEnabled)
        assertTrue(reconciledState.autoCheckOutEnabled)
    }

    @Test
    fun backgroundDecisions_considerAutomationAndPermissions() {
        val automaticState = CheckingState.initial().copy(
            locationSharingEnabled = true,
            autoCheckInEnabled = true,
            autoCheckOutEnabled = true,
        )
        val permissionSettings = CheckingPermissionSettingsState(
            backgroundAccessEnabled = true,
            notificationsEnabled = true,
            batteryOptimizationIgnored = false,
            isRefreshing = false,
        )

        assertTrue(
            CheckingRuntimeLogic.shouldRunBackgroundLocationService(
                state = automaticState,
                backgroundServiceSupported = true,
                referenceTime = Instant.parse("2026-04-20T01:00:00Z"),
            ),
        )
        assertFalse(
            CheckingRuntimeLogic.shouldRunForegroundLocationStream(
                state = automaticState,
                backgroundServiceSupported = true,
                referenceTime = Instant.parse("2026-04-20T01:00:00Z"),
            ),
        )
        assertTrue(
            CheckingRuntimeLogic.isConfiguredToKeepRunningInBackground(
                state = automaticState,
                permissionSettings = permissionSettings,
                backgroundServiceSupported = true,
                referenceTime = Instant.parse("2026-04-20T01:00:00Z"),
            ),
        )
    }

    @Test
    fun resolveControlFlagAfterSnapshot_neverReEnablesDisabledToggle() {
        assertFalse(
            CheckingRuntimeLogic.resolveControlFlagAfterSnapshot(
                currentValue = false,
                snapshotLocationSharingEnabled = true,
            ),
        )
        assertFalse(
            CheckingRuntimeLogic.resolveControlFlagAfterSnapshot(
                currentValue = true,
                snapshotLocationSharingEnabled = false,
            ),
        )
    }
}
