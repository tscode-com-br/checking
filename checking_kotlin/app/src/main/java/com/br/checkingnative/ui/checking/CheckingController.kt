package com.br.checkingnative.ui.checking

import com.br.checkingnative.data.background.CheckingBackgroundSnapshotRepository
import com.br.checkingnative.data.local.repository.ManagedLocationRepository
import com.br.checkingnative.data.preferences.CheckingStateStore
import com.br.checkingnative.data.remote.CheckingApiException
import com.br.checkingnative.data.remote.CheckingApiService
import com.br.checkingnative.domain.logic.CheckingLocationLogic
import com.br.checkingnative.domain.logic.CheckingRuntimeLogic
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.CheckingOemBackgroundSetupResult
import com.br.checkingnative.domain.model.CheckingLocationSample
import com.br.checkingnative.domain.model.CheckingPermissionSnapshot
import com.br.checkingnative.domain.model.InformeType
import com.br.checkingnative.domain.model.ProjetoType
import com.br.checkingnative.domain.model.RegistroType
import com.br.checkingnative.domain.model.StatusTone
import com.br.checkingnative.domain.model.SubmitCheckingEventRequest
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.min
import kotlin.random.Random
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@Singleton
class CheckingController @Inject constructor(
    private val checkingStateStore: CheckingStateStore,
    private val apiService: CheckingApiService,
    private val locationRepository: ManagedLocationRepository,
    private val backgroundSnapshotRepository: CheckingBackgroundSnapshotRepository =
        CheckingBackgroundSnapshotRepository(),
) {
    private val random = Random.Default
    private val controllerScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val _uiState = MutableStateFlow(CheckingUiState())
    private var backgroundSnapshotObserver: Job? = null
    private var processingForegroundLocationUpdate = false

    val uiState: StateFlow<CheckingUiState> = _uiState.asStateFlow()

    suspend fun initialize() {
        if (_uiState.value.initialized) {
            return
        }

        try {
            checkingStateStore.ensureSeededState()
            val snapshot = checkingStateStore.storageSnapshot.first()
            val restoredState = CheckingLocationLogic.resolveLocationUpdateIntervalState(
                state = snapshot.state,
            ).copy(
                lastCheckIn = null,
                lastCheckOut = null,
                isLoading = false,
                isSubmitting = false,
                isSyncing = false,
                isLocationUpdating = false,
                isAutomaticCheckingUpdating = false,
            )
            val locations = locationRepository.loadLocations(preferCache = true)
            _uiState.update { current ->
                current.copy(
                    state = restoredState,
                    managedLocations = locations,
                    initialized = true,
                    hasHydratedHistoryForCurrentKey = false,
                )
            }
        } catch (error: CancellationException) {
            throw error
        } catch (_: Exception) {
            _uiState.update { current ->
                current.copy(
                    state = CheckingState.initial().copy(
                        isLoading = false,
                        statusMessage = "Falha ao carregar dados locais do aplicativo.",
                        statusTone = StatusTone.ERROR,
                    ),
                    initialized = true,
                )
            }
        }

        startBackgroundSnapshotObserver()
    }

    suspend fun updateChave(
        value: String,
        syncAfterValidChange: Boolean = true,
    ) {
        val normalized = normalizeKey(value)
        if (normalized == currentState.chave) {
            return
        }

        _uiState.update { current ->
            current.copy(hasHydratedHistoryForCurrentKey = false)
        }

        updateAndPersist(
            currentState.copy(
                chave = normalized,
                lastMatchedLocation = null,
                lastDetectedLocation = null,
                lastLocationUpdateAt = null,
                lastCheckInLocation = null,
                lastCheckIn = null,
                lastCheckOut = null,
            ),
        )

        if (!currentState.hasValidChave || !currentState.hasApiConfig) {
            clearHistoryFields(updateStatus = false)
            return
        }

        if (syncAfterValidChange) {
            syncHistory(silent = true, updateStatus = true)
        }
    }

    suspend fun updateInforme(value: InformeType) {
        val state = currentState
        updateAndPersist(
            if (state.registro == RegistroType.CHECK_IN) {
                state.copy(checkInInforme = value)
            } else {
                state.copy(checkOutInforme = value)
            },
        )
    }

    suspend fun updateRegistro(value: RegistroType) {
        updateAndPersist(currentState.copy(registro = value))
    }

    suspend fun updateProjeto(value: ProjetoType) {
        updateAndPersist(currentState.copy(checkInProjeto = value))
    }

    suspend fun updateApiBaseUrl(value: String) {
        updateAndPersist(currentState.copy(apiBaseUrl = value.trim()))
    }

    suspend fun updateApiSharedKey(value: String) {
        updateAndPersist(currentState.copy(apiSharedKey = value.trim()))
    }

    suspend fun setLocationUpdateIntervalMinutes(minutes: Int) {
        val nextIntervalSeconds = CheckingLocationLogic.normalizeLocationUpdateIntervalSeconds(
            seconds = minutes * 60,
        )
        if (nextIntervalSeconds == currentState.locationUpdateIntervalSeconds) {
            return
        }

        applySettingsState(
            currentState.copy(locationUpdateIntervalSeconds = nextIntervalSeconds),
        )
    }

    suspend fun setNightUpdatesDisabled(value: Boolean) {
        if (value == currentState.nightUpdatesDisabled) {
            return
        }

        applySettingsState(currentState.copy(nightUpdatesDisabled = value))
    }

    suspend fun setNightModeAfterCheckoutEnabled(value: Boolean) {
        if (value == currentState.nightModeAfterCheckoutEnabled) {
            return
        }

        val baseState = currentState.copy(nightModeAfterCheckoutEnabled = value)
        val nextState = baseState.copy(
            nightModeAfterCheckoutUntil =
                CheckingLocationLogic.resolveNightModeAfterCheckoutUntilForAction(
                    currentState = baseState,
                    effectiveLastAction = baseState.lastRecordedAction,
                    lastCheckOut = baseState.lastCheckOut,
                ),
        )
        applySettingsState(nextState)

        if (CheckingLocationLogic.isNightModeAfterCheckoutActive(state = currentState)) {
            setStatus(
                CheckingLocationLogic.postCheckoutNightModeStatusMessage,
                StatusTone.WARNING,
            )
            return
        }

        setStatus(
            if (value) {
                "Modo noturno após check-out ativado."
            } else {
                "Modo noturno após check-out desativado."
            },
            if (value) StatusTone.SUCCESS else StatusTone.WARNING,
        )
    }

    suspend fun setNightPeriodStartMinutes(minutes: Int) {
        val normalizedMinutes = CheckingLocationLogic.normalizeMinutesOfDay(
            minutes = minutes,
            fallbackMinutes = CheckingLocationLogic.defaultNightPeriodStartMinutes,
        )
        if (normalizedMinutes == currentState.nightPeriodStartMinutes) {
            return
        }

        applySettingsState(currentState.copy(nightPeriodStartMinutes = normalizedMinutes))
    }

    suspend fun setNightPeriodEndMinutes(minutes: Int) {
        val normalizedMinutes = CheckingLocationLogic.normalizeMinutesOfDay(
            minutes = minutes,
            fallbackMinutes = CheckingLocationLogic.defaultNightPeriodEndMinutes,
        )
        if (normalizedMinutes == currentState.nightPeriodEndMinutes) {
            return
        }

        applySettingsState(currentState.copy(nightPeriodEndMinutes = normalizedMinutes))
    }

    suspend fun setAutomaticCheckInOutEnabled(value: Boolean) {
        val state = currentState
        if (state.isAutomaticCheckingUpdating || state.isLocationUpdating) {
            return
        }
        if (state.automaticCheckInOutEnabled == value) {
            return
        }

        if (!state.locationSharingEnabled) {
            updateAndPersist(
                state.copy(
                    autoCheckInEnabled = false,
                    autoCheckOutEnabled = false,
                ),
            )
            setStatus(
                "Ative a busca por localização para habilitar o check-in/check-out automático.",
                StatusTone.WARNING,
            )
            return
        }

        setStateOnly(state.copy(isAutomaticCheckingUpdating = true))
        try {
            updateAndPersist(
                currentState.copy(
                    autoCheckInEnabled = value,
                    autoCheckOutEnabled = value,
                    isAutomaticCheckingUpdating = true,
                ),
            )
            setStatus(
                if (value) {
                    "Check-in/Check-out automáticos ativados."
                } else {
                    "Check-in/Check-out automáticos desativados."
                },
                if (value) StatusTone.SUCCESS else StatusTone.WARNING,
            )
        } finally {
            setStateOnly(currentState.copy(isAutomaticCheckingUpdating = false))
        }
    }

    suspend fun setLocationSharingEnabled(value: Boolean) {
        val state = currentState
        if (state.isLocationUpdating || state.isAutomaticCheckingUpdating) {
            return
        }

        if (value && !state.canEnableLocationSharing) {
            setStatus(
                "Permita localização precisa, localização em segundo plano e notificações para habilitar a busca por localização.",
                StatusTone.ERROR,
            )
            return
        }

        if (!value) {
            updateAndPersist(
                state.copy(
                    locationSharingEnabled = false,
                    autoCheckInEnabled = false,
                    autoCheckOutEnabled = false,
                    lastMatchedLocation = null,
                ),
            )
            setStatus("Busca por localização desativada.", StatusTone.WARNING)
            return
        }

        updateAndPersist(
            state.copy(
                locationSharingEnabled = true,
                isLocationUpdating = false,
            ),
        )
        setStatus("Busca por localização ativada.", StatusTone.SUCCESS)
    }

    suspend fun enableLocationSharingAfterPermissionFlow(snapshot: CheckingPermissionSnapshot) {
        refreshPermissionState(
            snapshot = snapshot,
            updateStatus = true,
        )
        if (snapshot.canEnableLocationSharing) {
            setLocationSharingEnabled(true)
        }
    }

    suspend fun refreshPermissionState(
        snapshot: CheckingPermissionSnapshot,
        updateStatus: Boolean = false,
    ) {
        val previousState = currentState
        val reconciledState = CheckingRuntimeLogic.reconcilePermissionBackedSwitches(
            state = previousState,
            canEnableLocationSharing = snapshot.canEnableLocationSharing,
        )
        val status = if (updateStatus) permissionStatus(snapshot) else null
        val nextState = if (status != null) {
            reconciledState.copy(
                statusMessage = status.message,
                statusTone = status.tone,
            )
        } else {
            reconciledState
        }

        _uiState.update { current ->
            current.copy(
                state = nextState,
                permissionSettings = snapshot.toSettingsState(isRefreshing = false),
            )
        }

        if (nextState != previousState) {
            checkingStateStore.saveState(nextState)
        }
    }

    fun setPermissionSettingsRefreshing(value: Boolean) {
        _uiState.update { current ->
            current.copy(
                permissionSettings = current.permissionSettings.copy(isRefreshing = value),
            )
        }
    }

    suspend fun setBackgroundAccessEnabled(
        value: Boolean,
        snapshot: CheckingPermissionSnapshot,
    ) {
        refreshPermissionState(snapshot = snapshot, updateStatus = false)
        if (!value) {
            setStatus(
                "Revise o acesso à localização em 2º plano nas configurações do Android.",
                StatusTone.WARNING,
            )
            return
        }
        if (!snapshot.backgroundAccessEnabled) {
            setStatus(
                "Permita o acesso à localização em segundo plano para concluir a ativação.",
                StatusTone.ERROR,
            )
            return
        }
        setStatus(
            "Acesso à localização em 2º plano liberado. O monitoramento contínuo em segundo plano será usado quando a busca por localização e a automação estiverem ativas.",
            StatusTone.SUCCESS,
        )
    }

    suspend fun setNotificationsEnabled(
        value: Boolean,
        snapshot: CheckingPermissionSnapshot,
    ) {
        refreshPermissionState(snapshot = snapshot, updateStatus = false)
        if (!value) {
            setStatus(
                "Revise as notificações do aplicativo nas configurações do Android.",
                StatusTone.WARNING,
            )
            return
        }
        if (!snapshot.notificationsEnabled) {
            setStatus(
                "Permita as notificações do aplicativo para manter o monitoramento em segundo plano.",
                StatusTone.ERROR,
            )
            return
        }
        setStatus("Notificações do aplicativo liberadas.", StatusTone.SUCCESS)
    }

    suspend fun setBatteryOptimizationIgnored(
        value: Boolean,
        snapshot: CheckingPermissionSnapshot,
    ) {
        refreshPermissionState(snapshot = snapshot, updateStatus = false)
        if (!value) {
            setStatus(
                "Revise a otimização de bateria nas configurações do Android.",
                StatusTone.WARNING,
            )
            return
        }
        if (!snapshot.batteryOptimizationIgnored) {
            setStatus(
                "Permita ignorar a otimização de bateria para maior confiabilidade em segundo plano.",
                StatusTone.WARNING,
            )
            return
        }
        setStatus(
            "Otimização de bateria ajustada para o monitoramento em segundo plano.",
            StatusTone.SUCCESS,
        )
    }

    suspend fun setOemBackgroundSetupEnabled(
        value: Boolean,
        setupResult: CheckingOemBackgroundSetupResult = CheckingOemBackgroundSetupResult.empty,
    ) {
        if (value && !currentState.canEnableLocationSharing) {
            setStatus(
                "Permita localização precisa, acesso em 2º plano e notificações antes de ativar o Auto-Start.",
                StatusTone.WARNING,
            )
            return
        }

        if (!value) {
            updateAndPersist(
                currentState.copy(
                    oemBackgroundSetupEnabled = false,
                    statusMessage = "Auto-start desativado.",
                    statusTone = StatusTone.WARNING,
                ),
            )
            return
        }

        val message = setupResult.message.ifBlank {
            "Configuração OEM aberta para ajustes de auto-start."
        }
        updateAndPersist(
            currentState.copy(
                oemBackgroundSetupEnabled = true,
                statusMessage = message,
                statusTone = if (setupResult.message.isBlank()) {
                    StatusTone.SUCCESS
                } else {
                    StatusTone.WARNING
                },
            ),
        )
    }

    fun shouldRunForegroundLocationStream(backgroundServiceRunning: Boolean = false): Boolean {
        return CheckingRuntimeLogic.shouldRunForegroundLocationStream(
            state = currentState,
            backgroundServiceSupported = backgroundServiceRunning,
        ) && !backgroundServiceRunning
    }

    suspend fun processForegroundLocationUpdate(sample: CheckingLocationSample): Boolean {
        if (
            processingForegroundLocationUpdate ||
            !currentState.locationSharingEnabled ||
            CheckingLocationLogic.isNightModeAfterCheckoutActive(state = currentState)
        ) {
            return false
        }

        if (
            !CheckingLocationLogic.isLocationAccuracyPreciseEnough(
                accuracyMeters = sample.accuracyMeters,
                maxAccuracyMeters = currentState.locationAccuracyThresholdMeters.toDouble(),
            )
        ) {
            return false
        }

        if (
            CheckingLocationLogic.shouldSkipDuplicateLocationFetch(
                history = currentState.locationFetchHistory,
                timestamp = sample.timestamp,
                latitude = sample.latitude,
                longitude = sample.longitude,
            )
        ) {
            return false
        }

        processingForegroundLocationUpdate = true
        return try {
            val matchResult = CheckingLocationLogic.resolveLocationMatch(
                managedLocations = _uiState.value.managedLocations,
                latitude = sample.latitude,
                longitude = sample.longitude,
            )
            val matchedLocation = matchResult.matchedLocation
            val capturedLocationLabel = CheckingLocationLogic.resolveCapturedLocationLabel(
                location = matchedLocation,
                nearestWorkplaceDistanceMeters = matchResult.nearestWorkplaceDistanceMeters,
            )
            val locationFetchHistory = CheckingLocationLogic.recordLocationFetchHistory(
                history = currentState.locationFetchHistory,
                timestamp = sample.timestamp,
                latitude = sample.latitude,
                longitude = sample.longitude,
            )
            updateAndPersist(
                currentState.copy(
                    lastMatchedLocation = matchedLocation?.automationAreaLabel,
                    lastDetectedLocation = capturedLocationLabel,
                    lastLocationUpdateAt = sample.timestamp,
                    locationFetchHistory = locationFetchHistory,
                ),
            )
            true
        } finally {
            processingForegroundLocationUpdate = false
        }
    }

    suspend fun refreshAfterEnteringForeground() {
        if (_uiState.value.foregroundRefreshInProgress) {
            return
        }

        _uiState.update { current ->
            current.copy(foregroundRefreshInProgress = true)
        }

        try {
            val resolvedState = CheckingLocationLogic.resolveLocationUpdateIntervalState(
                state = currentState,
            )
            if (resolvedState != currentState) {
                updateAndPersist(resolvedState)
            }

            if (CheckingLocationLogic.isNightModeAfterCheckoutActive(state = currentState)) {
                setStatus(
                    CheckingLocationLogic.postCheckoutNightModeStatusMessage,
                    StatusTone.WARNING,
                )
                return
            }

            _uiState.update { current ->
                current.copy(hasHydratedHistoryForCurrentKey = false)
            }
            setStateOnly(
                currentState.copy(
                    lastMatchedLocation = null,
                    lastDetectedLocation = null,
                    lastLocationUpdateAt = null,
                    lastCheckInLocation = null,
                    lastCheckIn = null,
                    lastCheckOut = null,
                    statusMessage = "Atualização em andamento. Aguarde.",
                    statusTone = StatusTone.WARNING,
                    isLoading = false,
                ),
            )

            if (!currentState.hasValidChave || !currentState.hasApiConfig) {
                clearHistoryFields(updateStatus = true)
                return
            }

            try {
                syncHistory(silent = false, updateStatus = false)
            } catch (error: Throwable) {
                if (error is CancellationException) {
                    throw error
                }
                setStatus(
                    userMessage(error, "Falha ao consultar a API."),
                    StatusTone.ERROR,
                )
                return
            }

            if (currentState.locationSharingEnabled) {
                refreshLocationsCatalog(silent = true, updateStatus = false)
                setStatus("Atividades e localizações atualizadas.", StatusTone.SUCCESS)
            } else {
                setStateOnly(
                    currentState.copy(
                        lastMatchedLocation = null,
                        lastDetectedLocation = null,
                        lastLocationUpdateAt = null,
                    ),
                )
                setStatus("Atividades atualizadas.", StatusTone.SUCCESS)
            }
        } finally {
            _uiState.update { current ->
                current.copy(foregroundRefreshInProgress = false)
            }
        }
    }

    suspend fun syncHistory(
        silent: Boolean = false,
        updateStatus: Boolean = true,
    ): String {
        if (CheckingLocationLogic.isNightModeAfterCheckoutActive(state = currentState)) {
            if (updateStatus) {
                setStatus(
                    CheckingLocationLogic.postCheckoutNightModeStatusMessage,
                    StatusTone.WARNING,
                )
            }
            return CheckingLocationLogic.postCheckoutNightModeStatusMessage
        }

        if (!currentState.hasValidChave) {
            clearHistoryFields(updateStatus = updateStatus)
            return currentState.statusMessage
        }
        if (!currentState.hasApiConfig) {
            if (updateStatus) {
                setStatus(
                    "A configuração interna da API do aplicativo está incompleta.",
                    StatusTone.WARNING,
                )
            }
            return currentState.statusMessage
        }
        if (currentState.isSyncing) {
            return currentState.statusMessage
        }

        setStateOnly(currentState.copy(isSyncing = true))
        try {
            val response = apiService.fetchState(
                baseUrl = currentState.apiBaseUrl,
                sharedKey = currentState.apiSharedKey,
                chave = currentState.chave,
            )
            _uiState.update { current ->
                current.copy(hasHydratedHistoryForCurrentKey = true)
            }
            applyRemoteState(
                response = response,
                statusMessage = if (response.found) {
                    "Histórico sincronizado com a API."
                } else {
                    "Nenhum histórico encontrado para a chave informada."
                },
                tone = if (response.found) StatusTone.SUCCESS else StatusTone.WARNING,
                updateStatus = updateStatus,
            )
            return currentState.statusMessage
        } catch (error: Throwable) {
            if (error is CancellationException) {
                throw error
            }
            val message = userMessage(error, "Falha ao consultar a API.")
            if (updateStatus) {
                setStatus(message, StatusTone.ERROR)
            }
            if (!silent) {
                throw error
            }
            return message
        } finally {
            setStateOnly(currentState.copy(isSyncing = false))
        }
    }

    suspend fun refreshLocationsCatalog(
        silent: Boolean = false,
        updateStatus: Boolean = true,
    ): Int {
        if (!currentState.hasApiConfig) {
            if (updateStatus) {
                setStatus(
                    "A configuração interna da API do aplicativo está incompleta.",
                    StatusTone.WARNING,
                )
            }
            return _uiState.value.managedLocationCount
        }

        try {
            val response = apiService.fetchLocations(
                baseUrl = currentState.apiBaseUrl,
                sharedKey = currentState.apiSharedKey,
            )
            locationRepository.replaceAll(response.items)
            val nextState = CheckingLocationLogic.resolveLocationUpdateIntervalState(
                state = currentState.copy(
                    locationAccuracyThresholdMeters =
                        response.locationAccuracyThresholdMeters,
                ),
            ).let { resolvedState ->
                if (updateStatus) {
                    resolvedState.copy(
                        statusMessage =
                            "${response.items.size} localizações atualizadas no aplicativo.",
                        statusTone = StatusTone.SUCCESS,
                    )
                } else {
                    resolvedState
                }
            }

            _uiState.update { current ->
                current.copy(managedLocations = response.items)
            }
            updateAndPersist(nextState)
            return response.items.size
        } catch (error: Throwable) {
            if (error is CancellationException) {
                throw error
            }
            val message = userMessage(
                error,
                "Falha ao atualizar as localizações do aplicativo.",
            )
            if (updateStatus) {
                setStatus(message, StatusTone.ERROR)
            }
            if (!silent) {
                throw error
            }
            return _uiState.value.managedLocationCount
        }
    }

    suspend fun submitCurrent(): String {
        return submit(
            forcedAction = null,
            source = SOURCE_MANUAL,
            local = null,
        )
    }

    suspend fun submit(
        forcedAction: RegistroType?,
        source: String,
        local: String? = null,
    ): String {
        if (CheckingLocationLogic.isNightModeAfterCheckoutActive(state = currentState)) {
            setStatus(
                CheckingLocationLogic.postCheckoutNightModeStatusMessage,
                StatusTone.WARNING,
            )
            throw CheckingApiException(CheckingLocationLogic.postCheckoutNightModeStatusMessage)
        }
        if (!currentState.hasValidChave) {
            throw CheckingApiException("Informe uma chave Petrobras com 4 caracteres.")
        }
        if (!currentState.hasApiConfig) {
            throw CheckingApiException(
                "A configuração interna da API do aplicativo está incompleta.",
            )
        }

        setStateOnly(currentState.copy(isSubmitting = true))
        try {
            val state = currentState
            val action = forcedAction ?: state.registro
            val informe = resolveInformeForSubmission(
                state = state,
                action = action,
                source = source,
            )
            val response = apiService.submitEvent(
                baseUrl = state.apiBaseUrl,
                sharedKey = state.apiSharedKey,
                request = SubmitCheckingEventRequest(
                    chave = state.chave,
                    projeto = state.projetoFor(action),
                    action = action,
                    informe = informe,
                    clientEventId = buildClientEventId(
                        prefix = if (source == SOURCE_LOCATION_AUTOMATION) {
                            "kotlin-auto"
                        } else {
                            "kotlin"
                        },
                    ),
                    eventTime = Instant.now(),
                    local = local,
                ),
            )
            applyRemoteState(
                response = response.state,
                statusMessage = response.message,
                tone = StatusTone.SUCCESS,
                recentAction = action,
                recentLocal = local,
            )

            if (CheckingLocationLogic.isNightModeAfterCheckoutActive(state = currentState)) {
                setStatus(
                    CheckingLocationLogic.postCheckoutNightModeStatusMessage,
                    StatusTone.WARNING,
                )
            }
            return response.message
        } catch (error: Throwable) {
            if (error is CancellationException) {
                throw error
            }
            val message = userMessage(error, "Falha ao enviar evento pela API.")
            setStatus(
                "$message (${if (source == SOURCE_MANUAL) "manual" else "automático"})",
                StatusTone.ERROR,
            )
            throw error
        } finally {
            setStateOnly(currentState.copy(isSubmitting = false))
        }
    }

    private val currentState: CheckingState
        get() = _uiState.value.state

    private suspend fun applySettingsState(nextState: CheckingState) {
        updateAndPersist(
            CheckingLocationLogic.resolveLocationUpdateIntervalState(state = nextState),
        )
    }

    private suspend fun applyRemoteState(
        response: com.br.checkingnative.domain.model.MobileStateResponse,
        statusMessage: String,
        tone: StatusTone,
        updateStatus: Boolean = true,
        recentAction: RegistroType? = null,
        recentLocal: String? = null,
    ) {
        updateAndPersist(
            CheckingLocationLogic.applyRemoteState(
                currentState = currentState,
                response = response,
                statusMessage = statusMessage,
                tone = tone,
                updateStatus = updateStatus,
                recentAction = recentAction,
                recentLocal = recentLocal,
            ),
        )
    }

    private suspend fun clearHistoryFields(updateStatus: Boolean) {
        _uiState.update { current ->
            current.copy(hasHydratedHistoryForCurrentKey = false)
        }
        updateAndPersist(
            currentState.copy(
                lastMatchedLocation = null,
                lastDetectedLocation = null,
                lastLocationUpdateAt = null,
                lastCheckInLocation = null,
                lastCheckIn = null,
                lastCheckOut = null,
                statusMessage = if (updateStatus) {
                    "Informe a chave do usuário para sincronizar o histórico."
                } else {
                    currentState.statusMessage
                },
                statusTone = if (updateStatus) StatusTone.WARNING else currentState.statusTone,
            ),
        )
    }

    private suspend fun setStatus(message: String, tone: StatusTone) {
        updateAndPersist(
            currentState.copy(
                statusMessage = message,
                statusTone = tone,
                isLoading = false,
            ),
        )
    }

    private suspend fun updateAndPersist(nextState: CheckingState) {
        val resolvedState = nextState.copy(isLoading = false)
        setStateOnly(resolvedState)
        checkingStateStore.saveState(resolvedState)
    }

    private fun setStateOnly(nextState: CheckingState) {
        _uiState.update { current ->
            current.copy(state = nextState)
        }
    }

    private fun startBackgroundSnapshotObserver() {
        if (backgroundSnapshotObserver != null) {
            return
        }

        backgroundSnapshotObserver = controllerScope.launch {
            backgroundSnapshotRepository.snapshots.collect { snapshot ->
                _uiState.update { current ->
                    current.copy(
                        state = mergeBackgroundSnapshot(
                            currentState = current.state,
                            snapshot = snapshot,
                        ),
                    )
                }
            }
        }
    }

    private fun mergeBackgroundSnapshot(
        currentState: CheckingState,
        snapshot: CheckingState,
    ): CheckingState {
        return snapshot.copy(
            canEnableLocationSharing = currentState.canEnableLocationSharing,
            isLoading = false,
            isSubmitting = currentState.isSubmitting,
            isSyncing = currentState.isSyncing,
            isLocationUpdating = currentState.isLocationUpdating,
            isAutomaticCheckingUpdating = currentState.isAutomaticCheckingUpdating,
        )
    }

    private fun normalizeKey(value: String): String {
        val normalized = value.uppercase().replace(Regex("[^A-Z0-9]"), "")
        return normalized.substring(0, min(4, normalized.length))
    }

    private fun buildClientEventId(prefix: String): String {
        val now = Instant.now()
        val micros = (now.epochSecond * 1_000_000L) + (now.nano / 1_000L)
        val randomPart = random.nextInt(0xFFFFFF).toString(16).padStart(6, '0')
        return "$prefix-$micros-$randomPart"
    }

    private fun userMessage(error: Throwable, fallback: String): String {
        return if (error is CheckingApiException) {
            error.userMessage
        } else {
            fallback
        }
    }

    private fun permissionStatus(snapshot: CheckingPermissionSnapshot): PermissionStatusMessage {
        return when {
            !snapshot.locationServiceEnabled -> PermissionStatusMessage(
                message = "Ative o serviço de localização do Android para continuar.",
                tone = StatusTone.ERROR,
            )
            !snapshot.preciseLocationGranted -> PermissionStatusMessage(
                message = "Permita a localização precisa do aplicativo para ativar o monitoramento.",
                tone = StatusTone.ERROR,
            )
            !snapshot.backgroundAccessEnabled -> PermissionStatusMessage(
                message = "Permita o acesso à localização em segundo plano para concluir a ativação.",
                tone = StatusTone.ERROR,
            )
            !snapshot.notificationsEnabled -> PermissionStatusMessage(
                message = "Permita as notificações do aplicativo para manter o monitoramento em segundo plano.",
                tone = StatusTone.ERROR,
            )
            !snapshot.batteryOptimizationIgnored -> PermissionStatusMessage(
                message = "Busca por localização ativada. Para máxima confiabilidade com a tela bloqueada, permita ignorar a otimização de bateria do Android.",
                tone = StatusTone.WARNING,
            )
            else -> PermissionStatusMessage(
                message = "Configuração inicial do Android concluída.",
                tone = StatusTone.SUCCESS,
            )
        }
    }

    companion object {
        const val SOURCE_MANUAL: String = "manual"
        const val SOURCE_LOCATION_AUTOMATION: String = "location-automation"

        fun resolveInformeForSubmission(
            state: CheckingState,
            action: RegistroType,
            source: String,
        ): InformeType {
            return if (source == SOURCE_LOCATION_AUTOMATION) {
                InformeType.NORMAL
            } else {
                state.informeFor(action)
            }
        }

        fun isRegisterActionInteractive(state: CheckingState): Boolean {
            return CheckingRuntimeLogic.isRegisterActionInteractive(state = state)
        }
    }
}

private data class PermissionStatusMessage(
    val message: String,
    val tone: StatusTone,
)
