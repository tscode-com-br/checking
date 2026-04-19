package com.br.checkingnative.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.br.checkingnative.data.migration.LegacyFlutterMigrationCoordinator
import com.br.checkingnative.data.local.repository.ManagedLocationRepository
import com.br.checkingnative.data.preferences.CheckingStateRepository
import com.br.checkingnative.ui.checking.CheckingController
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@HiltViewModel
class BootstrapViewModel @Inject constructor(
    checkingStateRepository: CheckingStateRepository,
    migrationCoordinator: LegacyFlutterMigrationCoordinator,
    locationRepository: ManagedLocationRepository,
    checkingController: CheckingController,
) : ViewModel() {
    val uiState: StateFlow<BootstrapUiState> = combine(
        checkingStateRepository.storageSnapshot,
        locationRepository.locationCount,
        checkingController.uiState,
    ) { snapshot, locationCount, checkingUiState ->
        val activeState = if (checkingUiState.initialized) {
            checkingUiState.state
        } else {
            snapshot.state
        }
        BootstrapUiState(
            phaseLabel = "Fase 4 - controller funcional",
            coexistenceMode = "Modo 2: app Kotlin coexistindo com o Flutter",
            dataStoreReady = true,
            roomReady = true,
            stateRepositoryReady = true,
            legacySchemaReady = true,
            apiClientReady = true,
            domainLogicReady = true,
            controllerReady = checkingUiState.initialized,
            manualHistorySyncReady = checkingUiState.initialized,
            manualSubmitReady = checkingUiState.initialized,
            catalogSyncReady = checkingUiState.initialized,
            managedLocationCount = if (checkingUiState.initialized) {
                checkingUiState.managedLocationCount
            } else {
                locationCount
            },
            hasPersistedState = snapshot.hasPersistedState,
            chavePreview = activeState.chave.ifBlank { "Nao definida" },
            registroLabel = activeState.registro.label,
            locationIntervalSeconds = activeState.locationUpdateIntervalSeconds,
            locationSharingEnabled = activeState.locationSharingEnabled,
            automaticCheckInOutEnabled = activeState.automaticCheckInOutEnabled,
            currentStatusMessage = activeState.statusMessage,
            isSubmitting = activeState.isSubmitting,
            isSyncing = activeState.isSyncing,
            legacyMigrationStatus = snapshot.legacyMigrationStatus.label,
            legacyMigrationMessage = snapshot.legacyMigrationMessage,
            legacySourceInstalled = snapshot.legacySourceInstalled,
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = BootstrapUiState(),
    )

    init {
        viewModelScope.launch {
            checkingController.initialize()
            migrationCoordinator.assessAutomaticMigrationAvailability()
        }
    }
}
