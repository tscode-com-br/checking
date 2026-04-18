package com.br.checkingnative.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.br.checkingnative.data.migration.LegacyFlutterMigrationCoordinator
import com.br.checkingnative.data.local.repository.ManagedLocationRepository
import com.br.checkingnative.data.preferences.CheckingStateRepository
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
) : ViewModel() {
    val uiState: StateFlow<BootstrapUiState> = combine(
        checkingStateRepository.storageSnapshot,
        locationRepository.locationCount,
    ) { snapshot, locationCount ->
        BootstrapUiState(
            phaseLabel = "Fase 3 - API e dominio puro",
            coexistenceMode = "Modo 2: app Kotlin coexistindo com o Flutter",
            dataStoreReady = true,
            roomReady = true,
            stateRepositoryReady = true,
            legacySchemaReady = true,
            apiClientReady = true,
            domainLogicReady = true,
            managedLocationCount = locationCount,
            hasPersistedState = snapshot.hasPersistedState,
            chavePreview = snapshot.state.chave.ifBlank { "Nao definida" },
            registroLabel = snapshot.state.registro.label,
            locationIntervalSeconds = snapshot.state.locationUpdateIntervalSeconds,
            locationSharingEnabled = snapshot.state.locationSharingEnabled,
            automaticCheckInOutEnabled = snapshot.state.automaticCheckInOutEnabled,
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
            checkingStateRepository.ensureSeededState()
            migrationCoordinator.assessAutomaticMigrationAvailability()
        }
    }
}
