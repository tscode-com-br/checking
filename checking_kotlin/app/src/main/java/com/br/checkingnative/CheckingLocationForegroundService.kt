package com.br.checkingnative

import android.Manifest
import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.br.checkingnative.data.background.CheckingBackgroundSnapshotRepository
import com.br.checkingnative.data.preferences.CheckingStateStore
import com.br.checkingnative.data.remote.CheckingApiException
import com.br.checkingnative.data.remote.WebCheckApiService
import com.br.checkingnative.domain.logic.CheckingLocationLogic
import com.br.checkingnative.domain.logic.WebAutomaticActivityDecision
import com.br.checkingnative.domain.logic.WebAutomaticActivityReason
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.InformeType
import com.br.checkingnative.domain.model.MobileStateResponse
import com.br.checkingnative.domain.model.RegistroType
import com.br.checkingnative.domain.model.StatusTone
import com.br.checkingnative.domain.model.WebCheckSubmitRequest
import com.br.checkingnative.domain.model.WebLocationMatchRequest
import com.br.checkingnative.domain.model.WebLocationMatchResponse
import com.google.android.gms.location.CurrentLocationRequest
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import dagger.hilt.android.AndroidEntryPoint
import java.time.Duration
import java.time.Instant
import javax.inject.Inject
import kotlin.math.max
import kotlin.random.Random
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@AndroidEntryPoint
class CheckingLocationForegroundService : Service() {
    @Inject lateinit var checkingStateStore: CheckingStateStore
    @Inject lateinit var webApiService: WebCheckApiService
    @Inject lateinit var backgroundSnapshotRepository: CheckingBackgroundSnapshotRepository

    private val random = Random.Default
    private val serviceJob = SupervisorJob()
    private val serviceScope = CoroutineScope(serviceJob + Dispatchers.Main.immediate)
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private var wakeLock: PowerManager.WakeLock? = null
    private var locationUpdatesStarted = false
    private var currentIntervalSeconds: Int? = null
    private var scheduleBoundaryJob: Job? = null
    private var locationCaptureJob: Job? = null
    private var processingLocationUpdate = false
    private var lastRuntimeState: CheckingState? = null
    private var automationRetryAfter: Instant? = null
    private var automationRetryDelayMillis: Long = INITIAL_AUTOMATION_RETRY_DELAY_MILLIS

    private val locationCallback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            result.locations.forEach { location ->
                serviceScope.launch {
                    runGuarded { handleLocationUpdate(location) }
                }
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        createNotificationChannel()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopServiceInstance()
            return START_NOT_STICKY
        }

        return try {
            startForegroundCompat(buildNotification())
            acquireWakeLock()
            serviceScope.launch {
                runGuarded { reloadTrackingState(forceRestart = true) }
            }
            START_STICKY
        } catch (_: SecurityException) {
            stopSelf(startId)
            START_NOT_STICKY
        } catch (_: IllegalStateException) {
            stopSelf(startId)
            START_NOT_STICKY
        }
    }

    override fun onDestroy() {
        cancelTracking(keepScheduleBoundaryTimer = false)
        releaseWakeLock()
        lastRuntimeState?.let { state ->
            backgroundSnapshotRepository.tryPublish(
                state.copy(isLocationUpdating = false),
            )
        }
        serviceScope.cancel()
        super.onDestroy()
    }

    private suspend fun reloadTrackingState(forceRestart: Boolean) {
        val state = loadTrackingState()
        if (!shouldKeepServiceForState(state)) {
            cancelTracking(keepScheduleBoundaryTimer = false)
            currentIntervalSeconds = null
            stopServiceInstance()
            return
        }

        if (!CheckingLocationLogic.shouldRunBackgroundActivityNow(state = state)) {
            val pausedState = state.copy(
                statusMessage = if (
                    CheckingLocationLogic.isNightModeAfterCheckoutActive(state = state)
                ) {
                    CheckingLocationLogic.postCheckoutNightModeStatusMessage
                } else {
                    "Atualizações em segundo plano pausadas no período noturno configurado."
                },
                statusTone = StatusTone.WARNING,
                isLocationUpdating = false,
            )
            saveAndPublish(pausedState)
            cancelTracking(keepScheduleBoundaryTimer = false)
            currentIntervalSeconds = null
            restartScheduleBoundaryTimer(pausedState)
            updateNotification(pausedState.statusMessage)
            return
        }

        val blockedMessage = locationPrerequisiteBlockingMessage()
        if (blockedMessage != null) {
            val blockedState = state.copy(
                statusMessage = blockedMessage,
                statusTone = StatusTone.WARNING,
                isLocationUpdating = false,
            )
            saveAndPublish(blockedState)
            cancelTracking(keepScheduleBoundaryTimer = true)
            currentIntervalSeconds = null
            scheduleTrackingRetry()
            updateNotification(blockedMessage)
            return
        }

        restartScheduleBoundaryTimer(state)
        if (
            forceRestart ||
            !locationUpdatesStarted ||
            currentIntervalSeconds != state.locationUpdateIntervalSeconds
        ) {
            restartTracking(state)
        }
    }

    @SuppressLint("MissingPermission")
    private fun restartTracking(state: CheckingState) {
        cancelTracking(keepScheduleBoundaryTimer = true)
        currentIntervalSeconds = state.locationUpdateIntervalSeconds

        val intervalMillis = max(1_000L, state.locationUpdateIntervalSeconds * 1_000L)
        val request = LocationRequest.Builder(
            Priority.PRIORITY_HIGH_ACCURACY,
            intervalMillis,
        )
            .setMinUpdateIntervalMillis(max(1_000L, intervalMillis / 2))
            .setMinUpdateDistanceMeters(0f)
            .setWaitForAccurateLocation(false)
            .build()

        val updatingState = state.copy(isLocationUpdating = true)
        serviceScope.launch {
            saveAndPublish(updatingState)
        }
        updateNotification()

        fusedLocationClient
            .requestLocationUpdates(request, locationCallback, Looper.getMainLooper())
            .addOnSuccessListener {
                locationUpdatesStarted = true
                restartLocationCaptureJob(intervalMillis)
                captureCurrentLocationNow()
            }
            .addOnFailureListener { error ->
                locationUpdatesStarted = false
                currentIntervalSeconds = null
                serviceScope.launch {
                    runGuarded {
                        handleTrackingFailure(
                            state = state,
                            error = error,
                            fallbackMessage =
                                "Falha ao atualizar a localização do aparelho.",
                        )
                    }
                }
            }
    }

    private fun restartLocationCaptureJob(intervalMillis: Long) {
        locationCaptureJob?.cancel()
        locationCaptureJob = serviceScope.launch {
            while (isActive) {
                delay(intervalMillis)
                captureCurrentLocationNow()
            }
        }
    }

    @SuppressLint("MissingPermission")
    private fun captureCurrentLocationNow() {
        if (locationPrerequisiteBlockingMessage() != null) {
            serviceScope.launch {
                runGuarded { reloadTrackingState(forceRestart = false) }
            }
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
                    serviceScope.launch {
                        runGuarded { handleLocationUpdate(location) }
                    }
                }
            }
    }

    private suspend fun handleLocationUpdate(location: Location) {
        if (processingLocationUpdate) {
            return
        }

        val baseState = loadTrackingState()
        if (!shouldKeepServiceForState(baseState)) {
            reloadTrackingState(forceRestart = false)
            return
        }
        if (!CheckingLocationLogic.shouldRunBackgroundActivityNow(state = baseState)) {
            reloadTrackingState(forceRestart = true)
            return
        }

        val shouldRestartTracking =
            currentIntervalSeconds != baseState.locationUpdateIntervalSeconds
        if (
            !CheckingLocationLogic.isLocationAccuracyPreciseEnough(
                accuracyMeters = if (location.hasAccuracy()) {
                    location.accuracy.toDouble()
                } else {
                    null
                },
                maxAccuracyMeters = baseState.locationAccuracyThresholdMeters.toDouble(),
            )
        ) {
            if (shouldRestartTracking) {
                restartTracking(baseState)
            }
            return
        }

        val positionTimestamp = Instant.ofEpochMilli(
            location.time.takeIf { value -> value > 0L } ?: System.currentTimeMillis(),
        )
        if (
            CheckingLocationLogic.shouldSkipDuplicateLocationFetch(
                history = baseState.locationFetchHistory,
                timestamp = positionTimestamp,
                latitude = location.latitude,
                longitude = location.longitude,
            )
        ) {
            if (shouldRestartTracking) {
                restartTracking(baseState)
            }
            return
        }

        processingLocationUpdate = true
        try {
            val locationFetchHistory = CheckingLocationLogic.recordLocationFetchHistory(
                history = baseState.locationFetchHistory,
                timestamp = positionTimestamp,
                latitude = location.latitude,
                longitude = location.longitude,
            )
            val capturedState = baseState.copy(
                lastLocationUpdateAt = positionTimestamp,
                locationFetchHistory = locationFetchHistory,
                isLocationUpdating = true,
            )

            if (!capturedState.hasValidChave || !hasWebApiConfig(capturedState)) {
                saveAndPublish(
                    capturedState.copy(
                        lastDetectedLocation = "Coordenada capturada",
                        statusMessage =
                            "Monitoramento ativo. Informe chave e URL da API para executar a automação web.",
                        statusTone = StatusTone.WARNING,
                    ),
                )
                return
            }

            val coordinateCapturedState = capturedState.copy(
                lastDetectedLocation = "Coordenada capturada",
            )
            saveAndPublish(coordinateCapturedState)

            val locationPayload = try {
                withContext(Dispatchers.IO) {
                    webApiService.matchLocation(
                        baseUrl = capturedState.apiBaseUrl,
                        request = WebLocationMatchRequest(
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
            } catch (error: Throwable) {
                if (error is CancellationException) {
                    throw error
                }
                recordAutomationFailure()
                publishAutomationError(
                    state = coordinateCapturedState,
                    error = error,
                )
                return
            }

            val nextState = capturedState.copy(
                lastMatchedLocation = locationPayload.resolvedLocal,
                lastDetectedLocation =
                    CheckingLocationLogic.resolveCapturedLocationLabel(locationPayload),
            )
            saveAndPublish(nextState)

            if (CheckingLocationLogic.isNightModeAfterCheckoutActive(state = nextState)) {
                reloadTrackingState(forceRestart = true)
                return
            }
            if (
                !nextState.hasAnyLocationAutomation ||
                !nextState.hasValidChave ||
                !hasWebApiConfig(nextState)
            ) {
                return
            }

            if (isAutomationRetryDeferred()) {
                return
            }

            submitAutomaticWebLocationEvent(
                state = nextState,
                locationPayload = locationPayload,
            )
        } finally {
            processingLocationUpdate = false
            if (shouldRestartTracking) {
                restartTracking(baseState)
            }
        }
    }

    private suspend fun submitAutomaticWebLocationEvent(
        state: CheckingState,
        locationPayload: WebLocationMatchResponse,
    ) {
        try {
            val remoteState = withContext(Dispatchers.IO) {
                webApiService.fetchCheckState(
                    baseUrl = state.apiBaseUrl,
                    chave = state.chave,
                ).toMobileStateResponse()
            }
            resetAutomationBackoff()

            val decision = CheckingLocationLogic.resolveAutomaticActionForWebLocation(
                remoteState = remoteState,
                locationPayload = locationPayload,
                autoCheckInEnabled = state.autoCheckInEnabled,
                autoCheckOutEnabled = state.autoCheckOutEnabled,
            ) ?: return

            val response = withContext(Dispatchers.IO) {
                webApiService.submitCheck(
                    baseUrl = state.apiBaseUrl,
                    request = buildWebSubmitRequest(
                        state = state,
                        decision = decision,
                        projeto = remoteState.projeto
                            ?.trim()
                            ?.takeIf { value -> value.isNotEmpty() }
                            ?: state.projeto.apiValue,
                    ),
                )
            }
            resetAutomationBackoff()

            val nextState = applyAutomaticResponseState(
                state = state,
                remoteState = response.state,
                statusMessage = resolveAutomaticSuccessMessage(decision),
                action = decision.action,
                local = decision.local,
            )
            saveAndPublish(nextState)
            if (CheckingLocationLogic.isNightModeAfterCheckoutActive(state = nextState)) {
                reloadTrackingState(forceRestart = true)
            }
        } catch (error: Throwable) {
            if (error is CancellationException) {
                throw error
            }
            recordAutomationFailure()
            publishAutomationError(state, error)
        }
    }

    private fun applyAutomaticResponseState(
        state: CheckingState,
        remoteState: MobileStateResponse,
        statusMessage: String,
        action: RegistroType,
        local: String,
    ): CheckingState {
        val nextState = CheckingLocationLogic.applyRemoteState(
            currentState = state,
            response = remoteState,
            statusMessage = statusMessage,
            tone = StatusTone.SUCCESS,
            recentAction = action,
            recentLocal = local,
        )
        return if (CheckingLocationLogic.isNightModeAfterCheckoutActive(state = nextState)) {
            nextState.copy(
                statusMessage = CheckingLocationLogic.postCheckoutNightModeStatusMessage,
                statusTone = StatusTone.WARNING,
            )
        } else {
            nextState
        }
    }

    private suspend fun handleTrackingFailure(
        state: CheckingState,
        error: Throwable,
        fallbackMessage: String,
    ) {
        val statusMessage = resolveTrackingFailureMessage(
            error = error,
            fallbackMessage = fallbackMessage,
        )
        val warningState = state.copy(
            statusMessage = statusMessage,
            statusTone = StatusTone.WARNING,
            isLocationUpdating = false,
        )
        saveAndPublish(warningState)
        cancelTracking(keepScheduleBoundaryTimer = true)
        currentIntervalSeconds = null
        scheduleTrackingRetry()
        updateNotification(statusMessage)
    }

    private suspend fun handleUnexpectedBackgroundFailure() {
        val state = runCatching { loadTrackingState() }.getOrNull() ?: return
        val errorState = state.copy(
            statusMessage =
                "Falha ao manter o monitoramento em segundo plano. Abra o aplicativo para retomar a automação.",
            statusTone = StatusTone.ERROR,
            isLocationUpdating = false,
        )
        saveAndPublish(errorState)
        updateNotification(errorState.statusMessage)
    }

    private fun cancelTracking(keepScheduleBoundaryTimer: Boolean) {
        if (locationUpdatesStarted) {
            fusedLocationClient.removeLocationUpdates(locationCallback)
            locationUpdatesStarted = false
        }
        locationCaptureJob?.cancel()
        locationCaptureJob = null
        if (!keepScheduleBoundaryTimer) {
            scheduleBoundaryJob?.cancel()
            scheduleBoundaryJob = null
        }
    }

    private fun restartScheduleBoundaryTimer(state: CheckingState) {
        scheduleBoundaryJob?.cancel()
        val delayMillis = CheckingLocationLogic
            .delayUntilNextLocationUpdateIntervalBoundary(state = state)
            .toClampedMillis()
        scheduleBoundaryJob = serviceScope.launch {
            delay(delayMillis)
            runGuarded { reloadTrackingState(forceRestart = true) }
        }
    }

    private fun scheduleTrackingRetry() {
        scheduleBoundaryJob?.cancel()
        scheduleBoundaryJob = serviceScope.launch {
            delay(RETRY_DELAY_MILLIS)
            runGuarded { reloadTrackingState(forceRestart = true) }
        }
    }

    private suspend fun loadTrackingState(): CheckingState {
        val storedState = withContext(Dispatchers.IO) {
            checkingStateStore.storageSnapshot.first().state
        }
        val resolvedStoredState = CheckingLocationLogic.resolveLocationUpdateIntervalState(
            state = storedState,
        )
        val runtimeState = lastRuntimeState
        val mergedState = if (
            runtimeState != null &&
            runtimeState.chave == resolvedStoredState.chave &&
            runtimeState.apiBaseUrl == resolvedStoredState.apiBaseUrl
        ) {
            resolvedStoredState.copy(
                canEnableLocationSharing = runtimeState.canEnableLocationSharing,
                lastCheckIn = runtimeState.lastCheckIn,
                lastCheckOut = runtimeState.lastCheckOut,
                statusMessage = runtimeState.statusMessage,
                statusTone = runtimeState.statusTone,
                isLocationUpdating = runtimeState.isLocationUpdating,
            )
        } else {
            resolvedStoredState
        }

        if (resolvedStoredState != storedState) {
            saveAndPublish(mergedState)
        }
        return mergedState
    }

    private suspend fun saveAndPublish(state: CheckingState) {
        val resolvedState = state.copy(
            isLoading = false,
            isSubmitting = false,
            isSyncing = false,
            isAutomaticCheckingUpdating = false,
        )
        lastRuntimeState = resolvedState
        withContext(Dispatchers.IO) {
            checkingStateStore.saveState(resolvedState)
        }
        backgroundSnapshotRepository.publish(resolvedState)
    }

    private suspend fun publishAutomationError(state: CheckingState, error: Throwable) {
        val message = if (error is CheckingApiException) {
            error.userMessage
        } else {
            "Falha ao executar a automação por localização."
        }
        saveAndPublish(
            state.copy(
                statusMessage = message,
                statusTone = StatusTone.ERROR,
                isLocationUpdating = locationUpdatesStarted,
            ),
        )
    }

    private fun resolveAutomaticSuccessMessage(
        decision: WebAutomaticActivityDecision,
    ): String {
        return when (decision.reason) {
            WebAutomaticActivityReason.OUT_OF_RANGE_CHECKOUT ->
                "Check-Out automático enviado por afastamento das áreas monitoradas."
            else -> "${decision.action.label} automático enviado para ${decision.local}."
        }
    }

    private fun buildWebSubmitRequest(
        state: CheckingState,
        decision: WebAutomaticActivityDecision,
        projeto: String,
    ): WebCheckSubmitRequest {
        return WebCheckSubmitRequest(
            chave = state.chave,
            projeto = projeto,
            action = decision.action,
            informe = InformeType.NORMAL,
            clientEventId = buildClientEventId(),
            eventTime = Instant.now(),
            local = decision.local,
        )
    }

    private fun buildClientEventId(): String {
        val now = Instant.now()
        val micros = (now.epochSecond * 1_000_000L) + (now.nano / 1_000L)
        val randomPart = random.nextInt(0xFFFFFF).toString(16).padStart(6, '0')
        return "web-check-android-auto-$micros-$randomPart"
    }

    private fun hasWebApiConfig(state: CheckingState): Boolean {
        return state.apiBaseUrl.trim().isNotEmpty()
    }

    private fun isAutomationRetryDeferred(referenceTime: Instant = Instant.now()): Boolean {
        val retryAfter = automationRetryAfter ?: return false
        return retryAfter.isAfter(referenceTime)
    }

    private fun recordAutomationFailure(referenceTime: Instant = Instant.now()) {
        automationRetryAfter = referenceTime.plusMillis(automationRetryDelayMillis)
        automationRetryDelayMillis = (automationRetryDelayMillis * 2)
            .coerceAtMost(MAX_AUTOMATION_RETRY_DELAY_MILLIS)
    }

    private fun resetAutomationBackoff() {
        automationRetryAfter = null
        automationRetryDelayMillis = INITIAL_AUTOMATION_RETRY_DELAY_MILLIS
    }

    private suspend fun runGuarded(operation: suspend () -> Unit) {
        try {
            operation()
        } catch (error: Throwable) {
            if (error is CancellationException) {
                throw error
            }
            handleUnexpectedBackgroundFailure()
        }
    }

    private fun stopServiceInstance() {
        cancelTracking(keepScheduleBoundaryTimer = false)
        releaseWakeLock()
        stopForegroundCompat()
        stopSelf()
    }

    private fun shouldKeepServiceForState(state: CheckingState): Boolean {
        return state.locationSharingEnabled && state.hasAnyLocationAutomation
    }

    private fun locationPrerequisiteBlockingMessage(): String? {
        return when {
            !isLocationServiceEnabled() ->
                "Ative o serviço de localização do Android para retomar o monitoramento."
            !hasPreciseLocationPermission() || !hasBackgroundLocationPermission() ->
                "Permita a localização em segundo plano para retomar o monitoramento."
            else -> null
        }
    }

    private fun hasPreciseLocationPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_FINE_LOCATION,
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun hasBackgroundLocationPermission(): Boolean {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.Q ||
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_BACKGROUND_LOCATION,
            ) == PackageManager.PERMISSION_GRANTED
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

    private fun resolveTrackingFailureMessage(
        error: Throwable,
        fallbackMessage: String,
    ): String {
        val normalizedMessage = error.toString().trim().lowercase()
        return when {
            normalizedMessage.contains("permission") ||
                normalizedMessage.contains("denied") ->
                "Permita a localização em segundo plano para retomar o monitoramento."
            normalizedMessage.contains("location service") ||
                normalizedMessage.contains("service disabled") ->
                "Ative o serviço de localização do Android para retomar o monitoramento."
            else -> fallbackMessage
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return
        }

        val channel = NotificationChannel(
            CHANNEL_ID,
            CHANNEL_NAME,
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description =
                "Mantém o monitoramento de localização ativo para a automação de presença."
            setShowBadge(false)
        }
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(channel)
    }

    private fun buildNotification(
        contentText: String = DEFAULT_NOTIFICATION_TEXT,
    ): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_monochrome)
            .setContentTitle(NOTIFICATION_TITLE)
            .setContentText(contentText)
            .setStyle(NotificationCompat.BigTextStyle().bigText(contentText))
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun startForegroundCompat(notification: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION,
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    @SuppressLint("MissingPermission")
    private fun updateNotification(contentText: String = DEFAULT_NOTIFICATION_TEXT) {
        runCatching {
            NotificationManagerCompat.from(this).notify(
                NOTIFICATION_ID,
                buildNotification(contentText),
            )
        }
    }

    @Suppress("DEPRECATION")
    private fun stopForegroundCompat() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            stopForeground(true)
        }
    }

    @SuppressLint("WakelockTimeout")
    private fun acquireWakeLock() {
        val currentWakeLock = wakeLock
        if (currentWakeLock?.isHeld == true) {
            return
        }

        val manager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = manager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "$packageName:checking-location",
        ).apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    private fun releaseWakeLock() {
        val currentWakeLock = wakeLock
        if (currentWakeLock?.isHeld == true) {
            currentWakeLock.release()
        }
        wakeLock = null
    }

    private fun Duration.toClampedMillis(): Long {
        return toMillis().coerceIn(MIN_BOUNDARY_DELAY_MILLIS, MAX_BOUNDARY_DELAY_MILLIS)
    }

    companion object {
        const val ACTION_START: String = "com.br.checkingnative.location.START"
        const val ACTION_STOP: String = "com.br.checkingnative.location.STOP"
        const val CHANNEL_ID: String = "checking_location_tracking"
        const val CHANNEL_NAME: String = "Checking em segundo plano"
        const val NOTIFICATION_ID: Int = 4012
        private const val NOTIFICATION_TITLE: String = "Checking ativo"
        private const val DEFAULT_NOTIFICATION_TEXT: String =
            "Monitoramento de localização em segundo plano em execução."
        private const val RETRY_DELAY_MILLIS: Long = 60_000L
        private const val INITIAL_AUTOMATION_RETRY_DELAY_MILLIS: Long = 30_000L
        private const val MAX_AUTOMATION_RETRY_DELAY_MILLIS: Long = 10 * 60_000L
        private const val MIN_BOUNDARY_DELAY_MILLIS: Long = 60_000L
        private const val MAX_BOUNDARY_DELAY_MILLIS: Long = 24 * 60 * 60 * 1_000L
    }
}
