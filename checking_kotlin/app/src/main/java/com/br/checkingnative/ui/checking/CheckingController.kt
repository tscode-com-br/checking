package com.br.checkingnative.ui.checking

import com.br.checkingnative.data.background.CheckingBackgroundSnapshotRepository
import com.br.checkingnative.data.local.repository.ManagedLocationRepository
import com.br.checkingnative.data.preferences.CheckingStateStore
import com.br.checkingnative.data.preferences.WebSessionStore
import com.br.checkingnative.data.remote.CheckingApiException
import com.br.checkingnative.data.remote.WebCheckApiService
import com.br.checkingnative.domain.logic.CheckingLocationLogic
import com.br.checkingnative.domain.logic.CheckingRuntimeLogic
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.CheckingOemBackgroundSetupResult
import com.br.checkingnative.domain.model.CheckingLocationSample
import com.br.checkingnative.domain.model.CheckingPermissionSnapshot
import com.br.checkingnative.domain.model.CheckingWebAuthState
import com.br.checkingnative.domain.model.CheckingWebRegistrationInput
import com.br.checkingnative.domain.model.InformeType
import com.br.checkingnative.domain.model.ProjetoType
import com.br.checkingnative.domain.model.RegistroType
import com.br.checkingnative.domain.model.StatusTone
import com.br.checkingnative.domain.model.WebCheckSubmitRequest
import com.br.checkingnative.domain.model.WebPasswordLoginRequest
import com.br.checkingnative.domain.model.WebPasswordRegisterRequest
import com.br.checkingnative.domain.model.WebUserSelfRegistrationRequest
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
    private val webApiService: WebCheckApiService,
    private val webSessionStore: WebSessionStore,
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
            val hasStoredWebSession = webSessionStore.webSessionSnapshot
                .first()
                .cookieHeader
                .isNotBlank()
            val locations = locationRepository.loadLocations(preferCache = true)
            _uiState.update { current ->
                current.copy(
                    state = restoredState,
                    webAuth = initialWebAuthForState(
                        state = restoredState,
                        hasStoredWebSession = hasStoredWebSession,
                    ),
                    managedLocations = locations,
                    initialized = true,
                    hasPromptedInitialAndroidSetup = snapshot.hasPromptedInitialAndroidSetup,
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
                    hasPromptedInitialAndroidSetup = true,
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
            current.copy(
                webAuth = if (normalized.length == 4) {
                    CheckingWebAuthState.unauthenticated(
                        chave = normalized,
                        message = "Verifique o acesso web para esta chave.",
                        found = false,
                        hasPassword = false,
                    )
                } else {
                    CheckingWebAuthState.awaitingChave()
                },
                hasHydratedHistoryForCurrentKey = false,
            )
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

        if (!currentState.hasValidChave || !hasWebApiConfig(currentState)) {
            clearHistoryFields(updateStatus = false)
            return
        }

        if (syncAfterValidChange) {
            val webAuth = refreshWebAuthStatus(updateStatus = true, silent = true)
            if (webAuth.authenticated) {
                syncHistory(silent = true, updateStatus = true)
            }
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
        val normalized = value.trim()
        if (normalized == currentState.apiBaseUrl) {
            return
        }
        webSessionStore.clearWebSessionCookie()
        updateAndPersist(
            currentState.copy(
                apiBaseUrl = normalized,
                locationSharingEnabled = false,
                autoCheckInEnabled = false,
                autoCheckOutEnabled = false,
                isLocationUpdating = false,
            ),
        )
        setWebAuthOnly(
            CheckingWebAuthState.unauthenticated(
                chave = currentState.chave,
                message = "URL da API alterada. Entre novamente para liberar o segundo plano.",
                found = false,
                hasPassword = false,
            ),
        )
    }

    suspend fun updateApiSharedKey(value: String) {
        updateAndPersist(currentState.copy(apiSharedKey = value.trim()))
    }

    suspend fun refreshWebAuthStatus(
        updateStatus: Boolean = true,
        silent: Boolean = false,
    ): CheckingWebAuthState {
        val state = currentState
        if (!state.hasValidChave) {
            val nextAuth = CheckingWebAuthState.awaitingChave()
            setWebAuthOnly(nextAuth)
            if (updateStatus) {
                setStatus("Informe a chave do usuário para verificar o acesso web.", StatusTone.WARNING)
            }
            return nextAuth
        }
        if (!hasWebApiConfig(state)) {
            val nextAuth = CheckingWebAuthState.unauthenticated(
                chave = state.chave,
                message = "Informe a URL base da API para verificar o acesso web.",
                found = false,
                hasPassword = false,
            )
            setWebAuthOnly(nextAuth)
            if (updateStatus) {
                setStatus(nextAuth.message, StatusTone.WARNING)
            }
            return nextAuth
        }

        setWebAuthOnly(CheckingWebAuthState.checking(state.chave, _uiState.value.webAuth))
        return try {
            val response = webApiService.fetchAuthStatus(
                baseUrl = state.apiBaseUrl,
                chave = state.chave,
            )
            val nextAuth = CheckingWebAuthState.fromStatus(
                response = response,
                hasStoredSession = hasStoredWebSession(),
            )
            setWebAuthOnly(nextAuth)
            if (updateStatus) {
                setStatus(
                    nextAuth.message,
                    if (nextAuth.authenticated) StatusTone.SUCCESS else StatusTone.WARNING,
                )
            }
            nextAuth
        } catch (error: Throwable) {
            if (error is CancellationException) {
                throw error
            }
            val message = userMessage(error, "Falha ao verificar o acesso web.")
            val nextAuth = CheckingWebAuthState.unauthenticated(
                chave = state.chave,
                message = message,
                found = _uiState.value.webAuth.found,
                hasPassword = _uiState.value.webAuth.hasPassword,
            )
            setWebAuthOnly(nextAuth)
            if (updateStatus) {
                setStatus(message, StatusTone.ERROR)
            }
            if (!silent) {
                throw error
            }
            nextAuth
        }
    }

    suspend fun loginWebPassword(password: String): String {
        val senha = password.trim()
        validateWebAuthBasics()
        if (senha.isBlank()) {
            throw CheckingApiException("Informe a senha para entrar.")
        }

        setWebAuthOnly(CheckingWebAuthState.authenticating(_uiState.value.webAuth))
        try {
            val response = webApiService.login(
                baseUrl = currentState.apiBaseUrl,
                request = WebPasswordLoginRequest(
                    chave = currentState.chave,
                    senha = senha,
                ),
            )
            val nextAuth = CheckingWebAuthState.fromAction(
                chave = currentState.chave,
                response = response,
                hasStoredSession = hasStoredWebSession(),
            )
            setWebAuthOnly(nextAuth)
            setStatus(response.message, if (response.authenticated) StatusTone.SUCCESS else StatusTone.WARNING)
            if (response.authenticated) {
                syncHistory(silent = true, updateStatus = false)
            }
            return response.message
        } catch (error: Throwable) {
            if (error is CancellationException) {
                throw error
            }
            val message = userMessage(error, "Falha ao entrar com a senha.")
            setWebAuthOnly(
                CheckingWebAuthState.unauthenticated(
                    chave = currentState.chave,
                    message = message,
                ),
            )
            setStatus(message, StatusTone.ERROR)
            throw error
        }
    }

    suspend fun registerWebPassword(password: String): String {
        val senha = password.trim()
        validateWebAuthBasics()
        if (senha.length < MIN_PASSWORD_LENGTH) {
            throw CheckingApiException("A senha deve ter pelo menos $MIN_PASSWORD_LENGTH caracteres.")
        }

        setWebAuthOnly(CheckingWebAuthState.authenticating(_uiState.value.webAuth))
        try {
            val response = webApiService.registerPassword(
                baseUrl = currentState.apiBaseUrl,
                request = WebPasswordRegisterRequest(
                    chave = currentState.chave,
                    projeto = currentState.projeto.apiValue,
                    senha = senha,
                ),
            )
            val nextAuth = CheckingWebAuthState.fromAction(
                chave = currentState.chave,
                response = response,
                hasStoredSession = hasStoredWebSession(),
            )
            setWebAuthOnly(nextAuth)
            setStatus(response.message, if (response.authenticated) StatusTone.SUCCESS else StatusTone.WARNING)
            if (response.authenticated) {
                syncHistory(silent = true, updateStatus = false)
            }
            return response.message
        } catch (error: Throwable) {
            if (error is CancellationException) {
                throw error
            }
            val message = userMessage(error, "Falha ao cadastrar a senha.")
            setWebAuthOnly(
                CheckingWebAuthState.unauthenticated(
                    chave = currentState.chave,
                    message = message,
                    found = true,
                    hasPassword = false,
                ),
            )
            setStatus(message, StatusTone.ERROR)
            throw error
        }
    }

    suspend fun registerWebUser(input: CheckingWebRegistrationInput): String {
        validateWebAuthBasics()
        validateWebRegistrationInput(input)

        setWebAuthOnly(CheckingWebAuthState.authenticating(_uiState.value.webAuth))
        try {
            val response = webApiService.registerUser(
                baseUrl = currentState.apiBaseUrl,
                request = WebUserSelfRegistrationRequest(
                    chave = currentState.chave,
                    nome = input.nome.trim(),
                    projeto = input.projeto.apiValue,
                    endRua = input.endRua.trim(),
                    zip = input.zip.trim(),
                    email = input.email.trim(),
                    senha = input.senha.trim(),
                    confirmarSenha = input.confirmarSenha.trim(),
                ),
            )
            updateAndPersist(currentState.copy(checkInProjeto = input.projeto))
            val nextAuth = CheckingWebAuthState.fromAction(
                chave = currentState.chave,
                response = response,
                hasStoredSession = hasStoredWebSession(),
            )
            setWebAuthOnly(nextAuth)
            setStatus(response.message, if (response.authenticated) StatusTone.SUCCESS else StatusTone.WARNING)
            if (response.authenticated) {
                syncHistory(silent = true, updateStatus = false)
            }
            return response.message
        } catch (error: Throwable) {
            if (error is CancellationException) {
                throw error
            }
            val message = userMessage(error, "Falha ao cadastrar usuário.")
            setWebAuthOnly(
                CheckingWebAuthState.unauthenticated(
                    chave = currentState.chave,
                    message = message,
                    found = false,
                    hasPassword = false,
                ),
            )
            setStatus(message, StatusTone.ERROR)
            throw error
        }
    }

    suspend fun logoutWebSession(): String {
        val state = currentState
        val message = try {
            if (hasWebApiConfig(state)) {
                webApiService.logout(baseUrl = state.apiBaseUrl).message
            } else {
                "Sessão encerrada."
            }
        } catch (error: Throwable) {
            if (error is CancellationException) {
                throw error
            }
            userMessage(error, "Sessão local encerrada.")
        } finally {
            webSessionStore.clearWebSessionCookie()
        }

        setWebAuthOnly(
            CheckingWebAuthState.unauthenticated(
                chave = state.chave,
                message = message,
                found = _uiState.value.webAuth.found,
                hasPassword = _uiState.value.webAuth.hasPassword,
            ),
        )
        updateAndPersist(
            currentState.copy(
                locationSharingEnabled = false,
                autoCheckInEnabled = false,
                autoCheckOutEnabled = false,
                isLocationUpdating = false,
                statusMessage = message,
                statusTone = StatusTone.WARNING,
            ),
        )
        return message
    }

    suspend fun markInitialAndroidSetupPrompted() {
        checkingStateStore.markInitialAndroidSetupPrompted()
        _uiState.update { current ->
            current.copy(hasPromptedInitialAndroidSetup = true)
        }
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
        if (value && !_uiState.value.webAuth.authenticated) {
            setStatus(
                "Entre com sua senha para liberar a automação em segundo plano.",
                StatusTone.ERROR,
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
        if (value && !_uiState.value.webAuth.authenticated) {
            setStatus(
                "Entre com sua senha para liberar o monitoramento em segundo plano.",
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

            if (!currentState.hasValidChave || !hasWebApiConfig(currentState)) {
                clearHistoryFields(updateStatus = true)
                return
            }

            val webAuth = refreshWebAuthStatus(updateStatus = false, silent = true)
            if (!webAuth.authenticated) {
                setStatus(
                    webAuth.message.ifBlank { "Entre com sua senha para sincronizar o histórico." },
                    StatusTone.WARNING,
                )
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
        if (!hasWebApiConfig(currentState)) {
            if (updateStatus) {
                setStatus(
                    "Informe a URL base da API para sincronizar o histórico.",
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
            val response = webApiService.fetchCheckState(
                baseUrl = currentState.apiBaseUrl,
                chave = currentState.chave,
            ).toMobileStateResponse()
            setWebAuthAuthenticatedAfterApiSuccess()
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
            setWebAuthOnly(
                CheckingWebAuthState.unauthenticated(
                    chave = currentState.chave,
                    message = message,
                    found = _uiState.value.webAuth.found,
                    hasPassword = _uiState.value.webAuth.hasPassword,
                ),
            )
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
        if (!hasWebApiConfig(currentState)) {
            if (updateStatus) {
                setStatus(
                    "Informe a URL base da API para consultar localizações.",
                    StatusTone.WARNING,
                )
            }
            return _uiState.value.managedLocationCount
        }

        try {
            val response = webApiService.fetchLocationOptions(
                baseUrl = currentState.apiBaseUrl,
            )
            setWebAuthAuthenticatedAfterApiSuccess()
            if (updateStatus) {
                setStatus(
                    "${response.items.size} localizações disponíveis na API web.",
                    StatusTone.SUCCESS,
                )
            }
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
        if (!hasWebApiConfig(currentState)) {
            throw CheckingApiException(
                "Informe a URL base da API para enviar o registro.",
            )
        }
        if (!_uiState.value.webAuth.authenticated) {
            throw CheckingApiException("Entre com sua senha para enviar o registro.")
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
            val response = webApiService.submitCheck(
                baseUrl = state.apiBaseUrl,
                request = WebCheckSubmitRequest(
                    chave = state.chave,
                    projeto = state.projetoFor(action).apiValue,
                    action = action,
                    informe = informe,
                    clientEventId = buildClientEventId(
                        prefix = if (source == SOURCE_LOCATION_AUTOMATION) {
                            "web-check-android-auto"
                        } else {
                            "web-check-android"
                        },
                    ),
                    eventTime = Instant.now(),
                    local = local,
                ),
            )
            setWebAuthAuthenticatedAfterApiSuccess()
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
            setWebAuthOnly(
                CheckingWebAuthState.unauthenticated(
                    chave = currentState.chave,
                    message = message,
                    found = _uiState.value.webAuth.found,
                    hasPassword = _uiState.value.webAuth.hasPassword,
                ),
            )
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

    private fun setWebAuthOnly(nextAuth: CheckingWebAuthState) {
        _uiState.update { current ->
            current.copy(webAuth = nextAuth)
        }
    }

    private fun initialWebAuthForState(
        state: CheckingState,
        hasStoredWebSession: Boolean,
    ): CheckingWebAuthState {
        if (!state.hasValidChave) {
            return CheckingWebAuthState.awaitingChave()
        }
        return CheckingWebAuthState(
            chave = state.chave,
            hasStoredSession = hasStoredWebSession,
            message = if (hasStoredWebSession) {
                "Sessão web salva. Verifique o acesso para liberar o segundo plano."
            } else {
                "Verifique o acesso web para liberar o segundo plano."
            },
        )
    }

    private suspend fun setWebAuthAuthenticatedAfterApiSuccess() {
        val currentAuth = _uiState.value.webAuth
        setWebAuthOnly(
            currentAuth.copy(
                chave = currentState.chave,
                found = true,
                hasPassword = true,
                authenticated = true,
                hasStoredSession = hasStoredWebSession(),
                isChecking = false,
                isAuthenticating = false,
                message = "Aplicacao liberada.",
            ),
        )
    }

    private suspend fun hasStoredWebSession(): Boolean {
        return webSessionStore.webSessionSnapshot.first().cookieHeader.isNotBlank()
    }

    private fun validateWebAuthBasics() {
        if (!currentState.hasValidChave) {
            throw CheckingApiException("Informe uma chave Petrobras com 4 caracteres.")
        }
        if (!hasWebApiConfig(currentState)) {
            throw CheckingApiException("Informe a URL base da API.")
        }
    }

    private fun validateWebRegistrationInput(input: CheckingWebRegistrationInput) {
        when {
            input.nome.isBlank() -> throw CheckingApiException("Informe seu nome.")
            input.endRua.isBlank() -> throw CheckingApiException("Informe seu endereço.")
            input.zip.isBlank() -> throw CheckingApiException("Informe seu ZIP/código postal.")
            input.email.isBlank() -> throw CheckingApiException("Informe seu e-mail.")
            input.senha.trim().length < MIN_PASSWORD_LENGTH ->
                throw CheckingApiException("A senha deve ter pelo menos $MIN_PASSWORD_LENGTH caracteres.")
            input.senha.trim() != input.confirmarSenha.trim() ->
                throw CheckingApiException("A confirmação da senha não confere.")
        }
    }

    private fun hasWebApiConfig(state: CheckingState): Boolean {
        return state.apiBaseUrl.trim().isNotEmpty()
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
        const val MIN_PASSWORD_LENGTH: Int = 4

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
