package com.br.checkingnative

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.LocationFetchEntry
import com.br.checkingnative.domain.model.StatusTone
import com.br.checkingnative.ui.checking.CheckingApp
import com.br.checkingnative.ui.checking.CheckingUiState
import com.br.checkingnative.ui.theme.CheckingKotlinTheme
import java.time.Instant
import kotlinx.coroutines.flow.emptyFlow
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
                    ),
                    messages = emptyFlow(),
                    onChaveChanged = {},
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

        composeRule.onNodeWithContentDescription("Automação por localização").performClick()
        composeRule.mainClock.autoAdvance = true
        composeRule.waitForIdle()
        composeRule.onNodeWithText("Automação por Localização").assertIsDisplayed()
        composeRule.onNodeWithText("Últimas Localizações").assertIsDisplayed()
        composeRule.onNodeWithText("Local Capturado").assertIsDisplayed()
    }
}
