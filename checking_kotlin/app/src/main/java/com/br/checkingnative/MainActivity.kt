package com.br.checkingnative

import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.br.checkingnative.ui.checking.CheckingApp
import com.br.checkingnative.ui.checking.CheckingViewModel
import com.br.checkingnative.ui.theme.CheckingKotlinTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private val viewModel: CheckingViewModel by viewModels()
    private var initialResumeHandled = false

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
                    onLocationSharingChanged = viewModel::setLocationSharingEnabled,
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
}
