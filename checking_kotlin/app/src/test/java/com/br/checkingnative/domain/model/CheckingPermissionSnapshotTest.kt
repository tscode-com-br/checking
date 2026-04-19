package com.br.checkingnative.domain.model

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CheckingPermissionSnapshotTest {
    @Test
    fun canEnableLocationSharing_requiresLocationBackgroundAndNotifications() {
        assertTrue(
            permissionSnapshot().canEnableLocationSharing,
        )
        assertTrue(
            permissionSnapshot(batteryOptimizationIgnored = false).canEnableLocationSharing,
        )
        assertFalse(
            permissionSnapshot(preciseLocationGranted = false).canEnableLocationSharing,
        )
        assertFalse(
            permissionSnapshot(backgroundAccessEnabled = false).canEnableLocationSharing,
        )
        assertFalse(
            permissionSnapshot(notificationsEnabled = false).canEnableLocationSharing,
        )
    }

    private fun permissionSnapshot(
        locationServiceEnabled: Boolean = true,
        preciseLocationGranted: Boolean = true,
        backgroundAccessEnabled: Boolean = true,
        notificationsEnabled: Boolean = true,
        batteryOptimizationIgnored: Boolean = true,
    ): CheckingPermissionSnapshot {
        return CheckingPermissionSnapshot(
            locationServiceEnabled = locationServiceEnabled,
            preciseLocationGranted = preciseLocationGranted,
            backgroundAccessEnabled = backgroundAccessEnabled,
            notificationsEnabled = notificationsEnabled,
            batteryOptimizationIgnored = batteryOptimizationIgnored,
        )
    }
}
