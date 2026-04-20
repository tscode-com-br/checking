package com.br.checkingnative

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.CheckingPermissionSettingsState
import com.br.checkingnative.domain.model.CheckingWebAuthState
import com.br.checkingnative.domain.model.LocationFetchEntry
import com.br.checkingnative.domain.model.StatusTone
import com.br.checkingnative.ui.checking.CheckingApp
import com.br.checkingnative.ui.checking.CheckingUiState
import com.br.checkingnative.ui.theme.CheckingKotlinTheme
import java.time.Instant
import kotlinx.coroutines.flow.emptyFlow
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CheckingComposeBaselineTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun presentationMainScreenAndSheetsExposeFlutterParityLabels() {
        composeRule.mainClock.autoAdvance = false
        composeRule.setContent {
            CheckingKotlinTheme {
                CheckingApp(
                    uiState = CheckingUiState(
                        state = CheckingState.initial().copy(
                            chave = "HR70",
                            canEnableLocationSharing = true,
                            locationSharingEnabled = true,
                            autoCheckInEnabled = true,
                            autoCheckOutEnabled = true,
                            lastCheckIn = Instant.parse("2026-04-19T08:00:00Z"),
                            lastCheckOut = Instant.parse("2026-04-19T18:00:00Z"),
                            lastDetectedLocation = "Escritorio Principal",
                            lastLocationUpdateAt = Instant.parse("2026-04-19T08:15:00Z"),
                            locationFetchHistory = listOf(
                                LocationFetchEntry(
                                    timestamp = Instant.parse("2026-04-19T08:15:00Z"),
                                    latitude = 1.249494,
                                    longitude = 103.614345,
                                ),
                            ),
                            statusMessage = "Atividades atualizadas.",
                            statusTone = StatusTone.SUCCESS,
                            isLoading = false,
                        ),
                        webAuth = CheckingWebAuthState(
                            chave = "HR70",
                            found = true,
                            hasPassword = true,
                            authenticated = true,
                            hasStoredSession = true,
                            message = "Aplicacao liberada.",
                        ),
                        permissionSettings = CheckingPermissionSettingsState(
                            backgroundAccessEnabled = true,
                            notificationsEnabled = true,
                            batteryOptimizationIgnored = true,
                            isRefreshing = false,
                            locationServiceEnabled = true,
                            preciseLocationGranted = true,
                            backgroundServiceSupported = true,
                            foregroundServiceStartRequiresVisibleApp = true,
                        ),
                        hasPromptedInitialAndroidSetup = true,
                        hasHydratedHistoryForCurrentKey = true,
                    ),
                    messages = emptyFlow(),
                    onChaveChanged = {},
                    onRefreshWebAuthStatus = {},
                    onLoginWebPassword = {},
                    onRegisterWebPassword = {},
                    onRegisterWebUser = {},
                    onLogoutWebSession = {},
                    onRegistroChanged = {},
                    onInformeChanged = {},
                    onProjetoChanged = {},
                    onSubmit = {},
                    onLocationSharingChanged = {},
                    onBackgroundAccessChanged = {},
                    onNotificationsChanged = {},
                    onBatteryOptimizationChanged = {},
                    onOemBackgroundSetupChanged = {},
                    onAutomaticCheckingChanged = {},
                    onLocationUpdateIntervalChanged = {},
                    onNightUpdatesChanged = {},
                    onNightModeAfterCheckoutChanged = {},
                    onNightStartChanged = {},
                    onNightEndChanged = {},
                    onInitialMonitoringAccepted = {},
                    onInitialMonitoringSkipped = {},
                )
            }
        }

        composeRule.onNodeWithText("Dilnei Schmidt (CYMQ)").assertIsDisplayed()
        composeRule.mainClock.advanceTimeBy(2_200L)
        composeRule.waitForIdle()

        composeRule.onNodeWithText("Chave Petrobras").assertIsDisplayed()
        composeRule.onNodeWithText("REGISTRAR").assertIsDisplayed()
        composeRule.onNodeWithText("ÚLTIMO CHECK-IN").assertIsDisplayed()
        composeRule.onNodeWithText("Atividades atualizadas.").assertIsDisplayed()

        composeRule.onNodeWithContentDescription("Monitoramento em segundo plano").performClick()
        composeRule.mainClock.autoAdvance = true
        composeRule.waitForIdle()
        composeRule.onNodeWithText("Monitoramento").assertIsDisplayed()
        composeRule.onNodeWithText("Ativação pelo app aberto").assertIsDisplayed()
        composeRule.onNodeWithText("As permissões são solicitadas em etapas; o Android não libera tudo em um único pedido.").assertIsDisplayed()
        composeRule.onNodeWithText("Permitir o tempo todo").assertIsDisplayed()
        composeRule.onNodeWithText("Última coordenada").assertIsDisplayed()
        composeRule.onNodeWithText("Fechar").performClick()
        composeRule.waitForIdle()

        composeRule.onNodeWithContentDescription("Automação por localização").performClick()
        composeRule.waitForIdle()
        composeRule.onNodeWithText("Automação por Localização").assertIsDisplayed()
        composeRule.onNodeWithText("Últimas Localizações").assertIsDisplayed()
        composeRule.onNodeWithText("Local Capturado").assertIsDisplayed()
    }

    @Test
    fun firstRunShowsInitialMonitoringPrompt() {
        var skipped = false
        composeRule.mainClock.autoAdvance = false
        composeRule.setContent {
            CheckingKotlinTheme {
                CheckingApp(
                    uiState = CheckingUiState(
                        state = CheckingState.initial().copy(isLoading = false),
                        initialized = true,
                        hasPromptedInitialAndroidSetup = false,
                    ),
                    messages = emptyFlow(),
                    onChaveChanged = {},
                    onRefreshWebAuthStatus = {},
                    onLoginWebPassword = {},
                    onRegisterWebPassword = {},
                    onRegisterWebUser = {},
                    onLogoutWebSession = {},
                    onRegistroChanged = {},
                    onInformeChanged = {},
                    onProjetoChanged = {},
                    onSubmit = {},
                    onLocationSharingChanged = {},
                    onBackgroundAccessChanged = {},
                    onNotificationsChanged = {},
                    onBatteryOptimizationChanged = {},
                    onOemBackgroundSetupChanged = {},
                    onAutomaticCheckingChanged = {},
                    onLocationUpdateIntervalChanged = {},
                    onNightUpdatesChanged = {},
                    onNightModeAfterCheckoutChanged = {},
                    onNightStartChanged = {},
                    onNightEndChanged = {},
                    onInitialMonitoringAccepted = {},
                    onInitialMonitoringSkipped = { skipped = true },
                )
            }
        }

        composeRule.mainClock.advanceTimeBy(2_200L)
        composeRule.waitForIdle()

        composeRule.onNodeWithText("Monitoramento automático").assertIsDisplayed()
        composeRule.onNodeWithText("Ativar monitoramento automático").assertIsDisplayed()
        composeRule.onNodeWithText("Agora não").performClick()
        composeRule.waitForIdle()

        assertTrue(skipped)
    }
}
