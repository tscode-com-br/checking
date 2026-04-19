package com.br.checkingnative

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CheckingManifestParityTest {
    private val context = ApplicationProvider.getApplicationContext<android.content.Context>()
    private val packageManager = context.packageManager

    @Test
    fun manifest_declaresFlutterParityPermissions() {
        val requestedPermissions = packageInfo().requestedPermissions.orEmpty().toSet()

        assertTrue(requestedPermissions.contains(Manifest.permission.INTERNET))
        assertTrue(requestedPermissions.contains(Manifest.permission.ACCESS_NETWORK_STATE))
        assertTrue(requestedPermissions.contains(Manifest.permission.ACCESS_FINE_LOCATION))
        assertTrue(requestedPermissions.contains(Manifest.permission.ACCESS_COARSE_LOCATION))
        assertTrue(requestedPermissions.contains(Manifest.permission.ACCESS_BACKGROUND_LOCATION))
        assertTrue(requestedPermissions.contains(Manifest.permission.POST_NOTIFICATIONS))
        assertTrue(requestedPermissions.contains(Manifest.permission.FOREGROUND_SERVICE))
        assertTrue(requestedPermissions.contains(Manifest.permission.FOREGROUND_SERVICE_LOCATION))
        assertTrue(requestedPermissions.contains(Manifest.permission.WAKE_LOCK))
        assertTrue(requestedPermissions.contains(Manifest.permission.RECEIVE_BOOT_COMPLETED))
        assertTrue(
            requestedPermissions.contains(
                Manifest.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
            ),
        )
    }

    @Test
    fun foregroundLocationService_keepsTaskAliveAndDeclaresLocationType() {
        val service = packageInfo().services.orEmpty().first {
            it.name == CheckingLocationForegroundService::class.java.name
        }

        assertFalse((service.flags and ServiceInfo.FLAG_STOP_WITH_TASK) != 0)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            assertTrue(
                (service.foregroundServiceType and
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION) != 0,
            )
        }
    }

    @Test
    fun bootReceiver_handlesBootAndPackageReplaceActions() {
        assertReceiverHandles(Intent.ACTION_BOOT_COMPLETED)
        assertReceiverHandles(Intent.ACTION_LOCKED_BOOT_COMPLETED)
        assertReceiverHandles(Intent.ACTION_MY_PACKAGE_REPLACED)
    }

    private fun assertReceiverHandles(action: String) {
        val intent = Intent(action).setPackage(context.packageName)
        val receivers = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            packageManager.queryBroadcastReceivers(
                intent,
                PackageManager.ResolveInfoFlags.of(0),
            )
        } else {
            @Suppress("DEPRECATION")
            packageManager.queryBroadcastReceivers(intent, 0)
        }

        assertTrue(
            receivers.any { item ->
                item.activityInfo?.name == BootCompletedReceiver::class.java.name
            },
        )
    }

    private fun packageInfo(): android.content.pm.PackageInfo {
        val flags = PackageManager.GET_PERMISSIONS or
            PackageManager.GET_SERVICES or
            PackageManager.GET_RECEIVERS
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            packageManager.getPackageInfo(
                context.packageName,
                PackageManager.PackageInfoFlags.of(flags.toLong()),
            )
        } else {
            @Suppress("DEPRECATION")
            packageManager.getPackageInfo(context.packageName, flags)
        }
    }
}
