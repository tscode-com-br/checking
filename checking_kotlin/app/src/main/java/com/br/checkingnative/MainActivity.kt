package com.br.checkingnative

import android.Manifest
import android.app.NotificationManager
import android.content.ActivityNotFoundException
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.LocationManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.br.checkingnative.domain.model.CheckingOemBackgroundSetupResult
import com.br.checkingnative.domain.model.CheckingPermissionSnapshot
import com.br.checkingnative.ui.checking.CheckingApp
import com.br.checkingnative.ui.checking.CheckingViewModel
import com.br.checkingnative.ui.theme.CheckingKotlinTheme
import dagger.hilt.android.AndroidEntryPoint
import java.util.Locale

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private val viewModel: CheckingViewModel by viewModels()
    private var initialResumeHandled = false
    private var pendingAfterSettings: (() -> Unit)? = null
    private var pendingAfterForegroundLocationPermission: (() -> Unit)? = null
    private var pendingAfterBackgroundLocationPermission: (() -> Unit)? = null
    private var pendingAfterNotificationPermission: (() -> Unit)? = null

    private val foregroundLocationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
            val callback = pendingAfterForegroundLocationPermission
            pendingAfterForegroundLocationPermission = null
            callback?.invoke()
        }

    private val backgroundLocationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) {
            val callback = pendingAfterBackgroundLocationPermission
            pendingAfterBackgroundLocationPermission = null
            callback?.invoke()
        }

    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) {
            val callback = pendingAfterNotificationPermission
            pendingAfterNotificationPermission = null
            callback?.invoke()
        }

    private val settingsLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) {
            val callback = pendingAfterSettings
            pendingAfterSettings = null
            if (callback != null) {
                callback()
            } else {
                refreshAndroidPermissionState(updateStatus = false)
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleGeoActionIntent(intent)
        setContent {
            val uiState by viewModel.uiState.collectAsStateWithLifecycle()
            CheckingKotlinTheme {
                CheckingApp(
                    uiState = uiState,
                    messages = viewModel.messages,
                    onChaveChanged = viewModel::updateChave,
                    onRegistroChanged = viewModel::updateRegistro,
                    onInformeChanged = viewModel::updateInforme,
                    onProjetoChanged = viewModel::updateProjeto,
                    onSubmit = viewModel::submitCurrent,
                    onSyncHistory = viewModel::syncHistory,
                    onRefreshCatalog = viewModel::refreshLocationsCatalog,
                    onLocationSharingChanged = ::requestLocationSharingChange,
                    onBackgroundAccessChanged = ::requestBackgroundAccessChange,
                    onNotificationsChanged = ::requestNotificationsChange,
                    onBatteryOptimizationChanged = ::requestBatteryOptimizationChange,
                    onOemBackgroundSetupChanged = ::requestOemBackgroundSetupChange,
                    onAutomaticCheckingChanged = viewModel::setAutomaticCheckInOutEnabled,
                    onLocationUpdateIntervalChanged = viewModel::setLocationUpdateIntervalMinutes,
                    onNightUpdatesChanged = viewModel::setNightUpdatesDisabled,
                    onNightModeAfterCheckoutChanged = viewModel::setNightModeAfterCheckoutEnabled,
                    onNightStartChanged = viewModel::setNightPeriodStartMinutes,
                    onNightEndChanged = viewModel::setNightPeriodEndMinutes,
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refreshAndroidPermissionState(updateStatus = false)
        if (initialResumeHandled) {
            viewModel.refreshAfterEnteringForeground()
        } else {
            initialResumeHandled = true
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleGeoActionIntent(intent)
    }

    private fun handleGeoActionIntent(intent: Intent?) {
        if (GeoActionContract.readAction(intent) == null) {
            return
        }

        val notificationId = GeoActionContract.readNotificationId(intent)
        if (notificationId == 0) {
            return
        }

        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.cancel(notificationId)
    }

    private fun requestLocationSharingChange(value: Boolean) {
        if (!value) {
            viewModel.setLocationSharingEnabled(false)
            return
        }

        viewModel.setPermissionSettingsRefreshing(true)
        requestLocationPrerequisites {
            requestNotificationPermissionIfNeeded {
                requestIgnoreBatteryOptimizationIfNeeded {
                    viewModel.enableLocationSharingAfterPermissionFlow(readPermissionSnapshot())
                }
            }
        }
    }

    private fun requestBackgroundAccessChange(value: Boolean) {
        viewModel.setPermissionSettingsRefreshing(true)
        if (!value) {
            openApplicationDetailsSettings {
                viewModel.setBackgroundAccessEnabled(
                    value = false,
                    snapshot = readPermissionSnapshot(),
                )
            }
            return
        }

        requestLocationPrerequisites {
            viewModel.setBackgroundAccessEnabled(
                value = true,
                snapshot = readPermissionSnapshot(),
            )
        }
    }

    private fun requestNotificationsChange(value: Boolean) {
        viewModel.setPermissionSettingsRefreshing(true)
        if (!value) {
            openNotificationSettings {
                viewModel.setNotificationsEnabled(
                    value = false,
                    snapshot = readPermissionSnapshot(),
                )
            }
            return
        }

        requestNotificationPermissionIfNeeded {
            viewModel.setNotificationsEnabled(
                value = true,
                snapshot = readPermissionSnapshot(),
            )
        }
    }

    private fun requestBatteryOptimizationChange(value: Boolean) {
        viewModel.setPermissionSettingsRefreshing(true)
        if (!value) {
            openBatteryOptimizationSettings {
                viewModel.setBatteryOptimizationIgnored(
                    value = false,
                    snapshot = readPermissionSnapshot(),
                )
            }
            return
        }

        requestIgnoreBatteryOptimizationIfNeeded {
            viewModel.setBatteryOptimizationIgnored(
                value = true,
                snapshot = readPermissionSnapshot(),
            )
        }
    }

    private fun requestOemBackgroundSetupChange(value: Boolean) {
        if (!value) {
            viewModel.setOemBackgroundSetupEnabled(false)
            return
        }

        val setup = buildOemBackgroundSetupLaunch()
        val intent = setup.intent
        if (intent == null) {
            viewModel.setOemBackgroundSetupEnabled(true, setup.result)
            return
        }

        openSettingsIntent(intent) {
            viewModel.setOemBackgroundSetupEnabled(true, setup.result)
        }
    }

    private fun requestLocationPrerequisites(
        allowOpenLocationSettings: Boolean = true,
        allowRequestForeground: Boolean = true,
        allowRequestBackground: Boolean = true,
        onFinished: () -> Unit,
    ) {
        if (!isLocationServiceEnabled()) {
            if (allowOpenLocationSettings) {
                openSettingsIntent(Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS)) {
                    requestLocationPrerequisites(
                        allowOpenLocationSettings = false,
                        allowRequestForeground = allowRequestForeground,
                        allowRequestBackground = allowRequestBackground,
                        onFinished = onFinished,
                    )
                }
            } else {
                onFinished()
            }
            return
        }

        if (!hasPreciseLocationPermission()) {
            if (allowRequestForeground) {
                pendingAfterForegroundLocationPermission = {
                    requestLocationPrerequisites(
                        allowOpenLocationSettings = false,
                        allowRequestForeground = false,
                        allowRequestBackground = allowRequestBackground,
                        onFinished = onFinished,
                    )
                }
                foregroundLocationPermissionLauncher.launch(
                    arrayOf(
                        Manifest.permission.ACCESS_FINE_LOCATION,
                        Manifest.permission.ACCESS_COARSE_LOCATION,
                    ),
                )
            } else {
                onFinished()
            }
            return
        }

        if (!hasBackgroundLocationPermission()) {
            if (allowRequestBackground) {
                requestBackgroundLocationPermission {
                    requestLocationPrerequisites(
                        allowOpenLocationSettings = false,
                        allowRequestForeground = false,
                        allowRequestBackground = false,
                        onFinished = onFinished,
                    )
                }
            } else {
                onFinished()
            }
            return
        }

        onFinished()
    }

    private fun requestBackgroundLocationPermission(onFinished: () -> Unit) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            onFinished()
            return
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            openApplicationDetailsSettings(onFinished)
            return
        }

        pendingAfterBackgroundLocationPermission = onFinished
        backgroundLocationPermissionLauncher.launch(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
    }

    private fun requestNotificationPermissionIfNeeded(onFinished: () -> Unit) {
        if (areNotificationsEnabled()) {
            onFinished()
            return
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            pendingAfterNotificationPermission = onFinished
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            return
        }

        openNotificationSettings(onFinished)
    }

    private fun requestIgnoreBatteryOptimizationIfNeeded(onFinished: () -> Unit) {
        if (isIgnoringBatteryOptimizations()) {
            onFinished()
            return
        }

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            onFinished()
            return
        }

        val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
            data = Uri.parse("package:$packageName")
        }
        openSettingsIntent(intent, onFinished)
    }

    private fun refreshAndroidPermissionState(updateStatus: Boolean) {
        viewModel.refreshPermissionState(
            snapshot = readPermissionSnapshot(),
            updateStatus = updateStatus,
        )
    }

    private fun readPermissionSnapshot(): CheckingPermissionSnapshot {
        return CheckingPermissionSnapshot(
            locationServiceEnabled = isLocationServiceEnabled(),
            preciseLocationGranted = hasPreciseLocationPermission(),
            backgroundAccessEnabled = hasBackgroundLocationPermission(),
            notificationsEnabled = areNotificationsEnabled(),
            batteryOptimizationIgnored = isIgnoringBatteryOptimizations(),
            backgroundServiceSupported = true,
        )
    }

    private fun hasPreciseLocationPermission(): Boolean {
        return hasPermission(Manifest.permission.ACCESS_FINE_LOCATION)
    }

    private fun hasBackgroundLocationPermission(): Boolean {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.Q ||
            hasPermission(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
    }

    private fun hasPermission(permission: String): Boolean {
        return ContextCompat.checkSelfPermission(this, permission) ==
            PackageManager.PERMISSION_GRANTED
    }

    @Suppress("DEPRECATION")
    private fun isLocationServiceEnabled(): Boolean {
        val manager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            manager.isLocationEnabled
        } else {
            manager.isProviderEnabled(LocationManager.GPS_PROVIDER) ||
                manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
        }
    }

    private fun areNotificationsEnabled(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            hasPermission(Manifest.permission.POST_NOTIFICATIONS)
        } else {
            NotificationManagerCompat.from(this).areNotificationsEnabled()
        }
    }

    private fun isIgnoringBatteryOptimizations(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return true
        }
        val manager = getSystemService(Context.POWER_SERVICE) as PowerManager
        return manager.isIgnoringBatteryOptimizations(packageName)
    }

    private fun openApplicationDetailsSettings(onReturn: () -> Unit) {
        openSettingsIntent(
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.fromParts("package", packageName, null)
            },
            onReturn,
        )
    }

    private fun openNotificationSettings(onReturn: () -> Unit) {
        val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).apply {
                putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
            }
        } else {
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.fromParts("package", packageName, null)
            }
        }
        openSettingsIntent(intent, onReturn)
    }

    private fun openBatteryOptimizationSettings(onReturn: () -> Unit) {
        val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
        } else {
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.fromParts("package", packageName, null)
            }
        }
        openSettingsIntent(intent, onReturn)
    }

    private fun openSettingsIntent(intent: Intent, onReturn: () -> Unit) {
        pendingAfterSettings = onReturn
        try {
            settingsLauncher.launch(intent)
        } catch (_: ActivityNotFoundException) {
            pendingAfterSettings = null
            onReturn()
        } catch (_: SecurityException) {
            pendingAfterSettings = null
            onReturn()
        } catch (_: IllegalArgumentException) {
            pendingAfterSettings = null
            onReturn()
        }
    }

    private fun buildOemBackgroundSetupLaunch(): OemSetupLaunch {
        val manufacturer = listOfNotNull(Build.MANUFACTURER, Build.BRAND)
            .joinToString(" ")
            .lowercase(Locale.ROOT)

        return when {
            manufacturer.contains("xiaomi") ||
                manufacturer.contains("redmi") ||
                manufacturer.contains("poco") -> {
                val intent = firstResolvableIntent(xiaomiBackgroundSettingsIntents())
                OemSetupLaunch(
                    intent = intent,
                    result = CheckingOemBackgroundSetupResult(
                        openedSettings = intent != null,
                        message = if (intent != null) {
                            "No Xiaomi/HyperOS, revise a tela de Autostart aberta e mantenha a bateria do app em Sem restrições."
                        } else {
                            "No Xiaomi/HyperOS, habilite Autostart/Background autostart e defina a bateria do app como Sem restrições."
                        },
                    ),
                )
            }
            manufacturer.contains("samsung") -> OemSetupLaunch(
                intent = null,
                result = CheckingOemBackgroundSetupResult(
                    openedSettings = false,
                    message = "Em Samsung, se houver pausas, remova o app de Apps em suspensão/Deep sleeping e, se existir, adicione em Never sleeping apps.",
                ),
            )
            manufacturer.contains("motorola") ||
                manufacturer.contains("moto") -> OemSetupLaunch(
                intent = null,
                result = CheckingOemBackgroundSetupResult(
                    openedSettings = false,
                    message = "Em Motorola, se houver pausas, abra Uso de bateria do app e marque Unrestricted; se existir, permita Managing background apps.",
                ),
            )
            else -> OemSetupLaunch(
                intent = null,
                result = CheckingOemBackgroundSetupResult.empty,
            )
        }
    }

    private fun xiaomiBackgroundSettingsIntents(): List<Intent> {
        return listOf(
            Intent().apply {
                component = ComponentName(
                    "com.miui.securitycenter",
                    "com.miui.permcenter.autostart.AutoStartManagementActivity",
                )
            },
            Intent("miui.intent.action.OP_AUTO_START"),
            Intent().apply {
                component = ComponentName(
                    "com.miui.securitycenter",
                    "com.miui.appmanager.ApplicationsDetailsActivity",
                )
                putExtra("package_name", packageName)
                putExtra("miui.intent.extra.PACKAGE_NAME", packageName)
                putExtra("extra_pkgname", packageName)
            },
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.fromParts("package", packageName, null)
            },
        )
    }

    private fun firstResolvableIntent(intents: List<Intent>): Intent? {
        return intents.firstOrNull { intent ->
            intent.resolveActivity(packageManager) != null
        }
    }

    private data class OemSetupLaunch(
        val intent: Intent?,
        val result: CheckingOemBackgroundSetupResult,
    )
}
