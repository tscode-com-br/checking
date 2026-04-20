package com.br.checkingnative

import android.Manifest
import android.annotation.SuppressLint
import android.location.Location
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
import android.os.Looper
import android.os.PowerManager
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.br.checkingnative.domain.model.CheckingLocationSample
import com.br.checkingnative.domain.model.CheckingOemBackgroundSetupResult
import com.br.checkingnative.domain.model.CheckingPermissionSnapshot
import com.br.checkingnative.ui.checking.CheckingApp
import com.br.checkingnative.ui.checking.CheckingViewModel
import com.br.checkingnative.ui.theme.CheckingKotlinTheme
import com.google.android.gms.location.CurrentLocationRequest
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import dagger.hilt.android.AndroidEntryPoint
import java.time.Instant
import java.util.Locale
import kotlin.math.max

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private val viewModel: CheckingViewModel by viewModels()
    private var initialResumeHandled = false
    private var pendingAfterSettings: (() -> Unit)? = null
    private var pendingAfterForegroundLocationPermission: (() -> Unit)? = null
    private var pendingAfterBackgroundLocationPermission: (() -> Unit)? = null
    private var pendingAfterNotificationPermission: (() -> Unit)? = null
    private val fusedLocationClient: FusedLocationProviderClient by lazy {
        LocationServices.getFusedLocationProviderClient(this)
    }
    private var foregroundLocationUpdatesStarted = false
    private var foregroundLocationIntervalMillis: Long? = null
    private var backgroundLocationServiceRequested = false

    private val foregroundLocationCallback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            result.locations.forEach(::handleNativeLocation)
        }
    }

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
            LaunchedEffect(
                uiState.state.locationSharingEnabled,
                uiState.state.autoCheckInEnabled,
                uiState.state.autoCheckOutEnabled,
                uiState.state.locationUpdateIntervalSeconds,
                uiState.state.locationAccuracyThresholdMeters,
                uiState.state.nightUpdatesDisabled,
                uiState.state.nightPeriodStartMinutes,
                uiState.state.nightPeriodEndMinutes,
                uiState.state.nightModeAfterCheckoutUntil,
            ) {
                syncLocationTracking(captureImmediately = uiState.state.locationSharingEnabled)
            }
            CheckingKotlinTheme {
                CheckingApp(
                    uiState = uiState,
                    messages = viewModel.messages,
                    onChaveChanged = viewModel::updateChave,
                    onRefreshWebAuthStatus = viewModel::refreshWebAuthStatus,
                    onLoginWebPassword = viewModel::loginWebPassword,
                    onRegisterWebPassword = viewModel::registerWebPassword,
                    onRegisterWebUser = viewModel::registerWebUser,
                    onLogoutWebSession = viewModel::logoutWebSession,
                    onRegistroChanged = viewModel::updateRegistro,
                    onInformeChanged = viewModel::updateInforme,
                    onProjetoChanged = viewModel::updateProjeto,
                    onSubmit = viewModel::submitCurrent,
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
                    onInitialMonitoringAccepted = {
                        viewModel.markInitialAndroidSetupPrompted()
                        requestLocationSharingChange(true)
                    },
                    onInitialMonitoringSkipped = viewModel::markInitialAndroidSetupPrompted,
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refreshAndroidPermissionState(updateStatus = false)
        syncLocationTracking(captureImmediately = false)
        if (initialResumeHandled) {
            viewModel.refreshAfterEnteringForeground()
        } else {
            initialResumeHandled = true
        }
    }

    override fun onPause() {
        stopForegroundLocationStream()
        super.onPause()
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
                    syncLocationTracking(captureImmediately = true)
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
            backgroundAccessRequiresSettings =
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.R &&
                    !hasBackgroundLocationPermission(),
            foregroundServiceStartRequiresVisibleApp =
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.S,
            foregroundServiceLocationRequiresRuntimePermission =
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE,
        )
    }

    private fun syncLocationTracking(captureImmediately: Boolean) {
        val shouldKeepBackgroundService = shouldKeepBackgroundLocationService()
        syncBackgroundLocationService(shouldKeepBackgroundService)
        if (shouldKeepBackgroundService) {
            stopForegroundLocationStream()
            return
        }

        syncForegroundLocationStream(
            captureImmediately = captureImmediately,
            backgroundServiceRunning = false,
        )
    }

    private fun shouldKeepBackgroundLocationService(): Boolean {
        val state = viewModel.uiState.value.state
        return state.locationSharingEnabled && state.hasAnyLocationAutomation
    }

    private fun syncBackgroundLocationService(shouldStart: Boolean) {
        if (shouldStart) {
            runCatching {
                ContextCompat.startForegroundService(
                    this,
                    Intent(this, CheckingLocationForegroundService::class.java).apply {
                        action = CheckingLocationForegroundService.ACTION_START
                    },
                )
            }.onSuccess {
                backgroundLocationServiceRequested = true
            }
            return
        }

        if (!backgroundLocationServiceRequested && !viewModel.uiState.value.initialized) {
            return
        }

        runCatching {
            startService(
                Intent(this, CheckingLocationForegroundService::class.java).apply {
                    action = CheckingLocationForegroundService.ACTION_STOP
                },
            )
        }
        backgroundLocationServiceRequested = false
    }

    @SuppressLint("MissingPermission")
    private fun syncForegroundLocationStream(
        captureImmediately: Boolean,
        backgroundServiceRunning: Boolean,
    ) {
        if (
            !viewModel.shouldRunForegroundLocationStream(backgroundServiceRunning) ||
            !isLocationServiceEnabled() ||
            !hasPreciseLocationPermission()
        ) {
            stopForegroundLocationStream()
            return
        }

        val intervalMillis = resolveForegroundLocationIntervalMillis()
        if (
            foregroundLocationUpdatesStarted &&
            foregroundLocationIntervalMillis == intervalMillis
        ) {
            if (captureImmediately) {
                captureCurrentLocationOnce()
            }
            return
        }

        stopForegroundLocationStream()
        val request = LocationRequest.Builder(
            Priority.PRIORITY_HIGH_ACCURACY,
            intervalMillis,
        )
            .setMinUpdateIntervalMillis(max(1_000L, intervalMillis / 2))
            .setMinUpdateDistanceMeters(0f)
            .setWaitForAccurateLocation(false)
            .build()

        foregroundLocationIntervalMillis = intervalMillis
        fusedLocationClient
            .requestLocationUpdates(request, foregroundLocationCallback, Looper.getMainLooper())
            .addOnSuccessListener {
                foregroundLocationUpdatesStarted = true
                if (captureImmediately) {
                    captureCurrentLocationOnce()
                }
            }
            .addOnFailureListener {
                foregroundLocationUpdatesStarted = false
                foregroundLocationIntervalMillis = null
            }
    }

    @SuppressLint("MissingPermission")
    private fun captureCurrentLocationOnce() {
        if (!isLocationServiceEnabled() || !hasPreciseLocationPermission()) {
            return
        }

        val request = CurrentLocationRequest.Builder()
            .setPriority(Priority.PRIORITY_HIGH_ACCURACY)
            .build()
        val cancellationToken = CancellationTokenSource()
        fusedLocationClient
            .getCurrentLocation(request, cancellationToken.token)
            .addOnSuccessListener { location ->
                if (location != null) {
                    handleNativeLocation(location)
                }
            }
    }

    private fun stopForegroundLocationStream() {
        if (!foregroundLocationUpdatesStarted) {
            foregroundLocationIntervalMillis = null
            return
        }

        fusedLocationClient.removeLocationUpdates(foregroundLocationCallback)
        foregroundLocationUpdatesStarted = false
        foregroundLocationIntervalMillis = null
    }

    private fun resolveForegroundLocationIntervalMillis(): Long {
        val seconds = viewModel.uiState.value.state.locationUpdateIntervalSeconds
        return max(1_000L, seconds * 1_000L)
    }

    private fun handleNativeLocation(location: Location) {
        viewModel.processForegroundLocationUpdate(
            CheckingLocationSample(
                timestamp = Instant.ofEpochMilli(
                    location.time.takeIf { value -> value > 0L } ?: System.currentTimeMillis(),
                ),
                latitude = location.latitude,
                longitude = location.longitude,
                accuracyMeters = if (location.hasAccuracy()) {
                    location.accuracy.toDouble()
                } else {
                    null
                },
            ),
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
