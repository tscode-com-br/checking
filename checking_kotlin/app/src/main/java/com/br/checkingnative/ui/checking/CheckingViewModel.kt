package com.br.checkingnative.ui.checking

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.br.checkingnative.domain.model.InformeType
import com.br.checkingnative.domain.model.ProjetoType
import com.br.checkingnative.domain.model.RegistroType
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

@HiltViewModel
class CheckingViewModel @Inject constructor(
    private val controller: CheckingController,
) : ViewModel() {
    val uiState: StateFlow<CheckingUiState> = controller.uiState

    init {
        viewModelScope.launch {
            controller.initialize()
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
            controller.syncHistory(silent = true, updateStatus = true)
        }
    }

    fun refreshLocationsCatalog() {
        viewModelScope.launch {
            controller.refreshLocationsCatalog(silent = true, updateStatus = true)
        }
    }

    fun submitCurrent() {
        viewModelScope.launch {
            controller.submitCurrent()
        }
    }

    fun refreshAfterEnteringForeground() {
        viewModelScope.launch {
            controller.refreshAfterEnteringForeground()
        }
    }
}
