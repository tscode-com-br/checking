package com.br.checkingnative.ui.checking

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.br.checkingnative.domain.model.InformeType
import com.br.checkingnative.domain.model.CheckingOemBackgroundSetupResult
import com.br.checkingnative.domain.model.CheckingPermissionSnapshot
import com.br.checkingnative.domain.model.ProjetoType
import com.br.checkingnative.domain.model.RegistroType
import com.br.checkingnative.data.remote.CheckingApiException
import com.br.checkingnative.domain.model.CheckingLocationSample
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch

@HiltViewModel
class CheckingViewModel @Inject constructor(
    private val controller: CheckingController,
) : ViewModel() {
    val uiState: StateFlow<CheckingUiState> = controller.uiState

    private val _messages = MutableSharedFlow<String>()
    val messages: SharedFlow<String> = _messages.asSharedFlow()

    init {
        viewModelScope.launch {
            controller.initialize()
            controller.refreshAfterEnteringForeground()
        }
    }

    fun updateChave(value: String) {
        viewModelScope.launch {
            controller.updateChave(value)
        }
    }

    fun updateInforme(value: InformeType) {
        viewModelScope.launch {
            controller.updateInforme(value)
        }
    }

    fun updateRegistro(value: RegistroType) {
        viewModelScope.launch {
            controller.updateRegistro(value)
        }
    }

    fun updateProjeto(value: ProjetoType) {
        viewModelScope.launch {
            controller.updateProjeto(value)
        }
    }

    fun syncHistory() {
        viewModelScope.launch {
            emitMessage(controller.syncHistory(silent = true, updateStatus = true))
        }
    }

    fun refreshLocationsCatalog() {
        viewModelScope.launch {
            val count = controller.refreshLocationsCatalog(silent = true, updateStatus = true)
            emitMessage("$count localizações atualizadas no aplicativo.")
        }
    }

    fun submitCurrent() {
        viewModelScope.launch {
            val result = runCatching {
                controller.submitCurrent()
            }
            if (result.isSuccess) {
                emitMessage(result.getOrThrow())
            } else {
                emitMessage(userMessage(result.exceptionOrNull() ?: return@launch))
            }
        }
    }

    fun setLocationSharingEnabled(value: Boolean) {
        viewModelScope.launch {
            controller.setLocationSharingEnabled(value)
        }
    }

    fun enableLocationSharingAfterPermissionFlow(snapshot: CheckingPermissionSnapshot) {
        viewModelScope.launch {
            controller.initialize()
            controller.enableLocationSharingAfterPermissionFlow(snapshot)
        }
    }

    fun refreshPermissionState(
        snapshot: CheckingPermissionSnapshot,
        updateStatus: Boolean = false,
    ) {
        viewModelScope.launch {
            controller.initialize()
            controller.refreshPermissionState(
                snapshot = snapshot,
                updateStatus = updateStatus,
            )
        }
    }

    fun setPermissionSettingsRefreshing(value: Boolean) {
        controller.setPermissionSettingsRefreshing(value)
    }

    fun setBackgroundAccessEnabled(
        value: Boolean,
        snapshot: CheckingPermissionSnapshot,
    ) {
        viewModelScope.launch {
            controller.initialize()
            controller.setBackgroundAccessEnabled(value, snapshot)
        }
    }

    fun setNotificationsEnabled(
        value: Boolean,
        snapshot: CheckingPermissionSnapshot,
    ) {
        viewModelScope.launch {
            controller.initialize()
            controller.setNotificationsEnabled(value, snapshot)
        }
    }

    fun setBatteryOptimizationIgnored(
        value: Boolean,
        snapshot: CheckingPermissionSnapshot,
    ) {
        viewModelScope.launch {
            controller.initialize()
            controller.setBatteryOptimizationIgnored(value, snapshot)
        }
    }

    fun setOemBackgroundSetupEnabled(
        value: Boolean,
        setupResult: CheckingOemBackgroundSetupResult = CheckingOemBackgroundSetupResult.empty,
    ) {
        viewModelScope.launch {
            controller.initialize()
            controller.setOemBackgroundSetupEnabled(value, setupResult)
        }
    }

    fun shouldRunForegroundLocationStream(backgroundServiceRunning: Boolean): Boolean {
        return controller.shouldRunForegroundLocationStream(
            backgroundServiceRunning = backgroundServiceRunning,
        )
    }

    fun processForegroundLocationUpdate(sample: CheckingLocationSample) {
        viewModelScope.launch {
            controller.initialize()
            controller.processForegroundLocationUpdate(sample)
        }
    }

    fun setAutomaticCheckInOutEnabled(value: Boolean) {
        viewModelScope.launch {
            controller.setAutomaticCheckInOutEnabled(value)
        }
    }

    fun setLocationUpdateIntervalMinutes(minutes: Int) {
        viewModelScope.launch {
            controller.setLocationUpdateIntervalMinutes(minutes)
        }
    }

    fun setNightUpdatesDisabled(value: Boolean) {
        viewModelScope.launch {
            controller.setNightUpdatesDisabled(value)
        }
    }

    fun setNightModeAfterCheckoutEnabled(value: Boolean) {
        viewModelScope.launch {
            controller.setNightModeAfterCheckoutEnabled(value)
        }
    }

    fun setNightPeriodStartMinutes(minutes: Int) {
        viewModelScope.launch {
            controller.setNightPeriodStartMinutes(minutes)
        }
    }

    fun setNightPeriodEndMinutes(minutes: Int) {
        viewModelScope.launch {
            controller.setNightPeriodEndMinutes(minutes)
        }
    }

    fun refreshAfterEnteringForeground() {
        viewModelScope.launch {
            controller.refreshAfterEnteringForeground()
        }
    }

    private suspend fun emitMessage(message: String) {
        if (message.isNotBlank()) {
            _messages.emit(message)
        }
    }

    private fun userMessage(error: Throwable): String {
        return if (error is CheckingApiException) {
            error.userMessage
        } else {
            error.message ?: "Falha ao executar a operação."
        }
    }
}
