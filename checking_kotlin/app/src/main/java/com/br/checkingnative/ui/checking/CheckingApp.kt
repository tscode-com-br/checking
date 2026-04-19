package com.br.checkingnative.ui.checking

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.VerticalDivider
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusManager
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.br.checkingnative.R
import com.br.checkingnative.domain.logic.CheckingLocationLogic
import com.br.checkingnative.domain.logic.CheckingRuntimeLogic
import com.br.checkingnative.domain.model.CheckingPermissionSettingsState
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.InformeType
import com.br.checkingnative.domain.model.LocationFetchEntry
import com.br.checkingnative.domain.model.ProjetoType
import com.br.checkingnative.domain.model.RegistroType
import com.br.checkingnative.domain.model.StatusTone
import com.br.checkingnative.ui.theme.CheckingBorder
import com.br.checkingnative.ui.theme.CheckingCard
import com.br.checkingnative.ui.theme.CheckingError
import com.br.checkingnative.ui.theme.CheckingMuted
import com.br.checkingnative.ui.theme.CheckingSuccess
import com.br.checkingnative.ui.theme.CheckingSurface
import com.br.checkingnative.ui.theme.CheckingText
import com.br.checkingnative.ui.theme.CheckingWarning
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlin.math.roundToInt
import kotlinx.coroutines.flow.Flow

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CheckingApp(
    uiState: CheckingUiState,
    messages: Flow<String>,
    onChaveChanged: (String) -> Unit,
    onRegistroChanged: (RegistroType) -> Unit,
    onInformeChanged: (InformeType) -> Unit,
    onProjetoChanged: (ProjetoType) -> Unit,
    onSubmit: () -> Unit,
    onSyncHistory: () -> Unit,
    onRefreshCatalog: () -> Unit,
    onLocationSharingChanged: (Boolean) -> Unit,
    onAutomaticCheckingChanged: (Boolean) -> Unit,
    onLocationUpdateIntervalChanged: (Int) -> Unit,
    onNightUpdatesChanged: (Boolean) -> Unit,
    onNightModeAfterCheckoutChanged: (Boolean) -> Unit,
    onNightStartChanged: (Int) -> Unit,
    onNightEndChanged: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val snackbarHostState = remember { SnackbarHostState() }
    var showLocationSheet by remember { mutableStateOf(false) }
    var showSettingsSheet by remember { mutableStateOf(false) }

    LaunchedEffect(messages) {
        messages.collect { message ->
            snackbarHostState.showSnackbar(message)
        }
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        contentWindowInsets = WindowInsets.safeDrawing,
        containerColor = CheckingSurface,
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) },
    ) { innerPadding ->
        CheckingMainContent(
            uiState = uiState,
            onOpenLocationSheet = { showLocationSheet = true },
            onOpenSettingsSheet = { showSettingsSheet = true },
            onChaveChanged = onChaveChanged,
            onRegistroChanged = onRegistroChanged,
            onInformeChanged = onInformeChanged,
            onProjetoChanged = onProjetoChanged,
            onSubmit = onSubmit,
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .imePadding(),
        )
    }

    if (showLocationSheet) {
        ModalBottomSheet(
            onDismissRequest = { showLocationSheet = false },
            containerColor = CheckingSurface,
        ) {
            LocationAutomationSheet(
                state = uiState.state,
                managedLocationCount = uiState.managedLocationCount,
                onAutomaticCheckingChanged = onAutomaticCheckingChanged,
                onClose = { showLocationSheet = false },
            )
        }
    }

    if (showSettingsSheet) {
        ModalBottomSheet(
            onDismissRequest = { showSettingsSheet = false },
            containerColor = CheckingSurface,
        ) {
            SettingsSheet(
                state = uiState.state,
                permissionSettings = uiState.permissionSettings,
                onLocationSharingChanged = onLocationSharingChanged,
                onSyncHistory = onSyncHistory,
                onRefreshCatalog = onRefreshCatalog,
                onLocationUpdateIntervalChanged = onLocationUpdateIntervalChanged,
                onNightUpdatesChanged = onNightUpdatesChanged,
                onNightModeAfterCheckoutChanged = onNightModeAfterCheckoutChanged,
                onNightStartChanged = onNightStartChanged,
                onNightEndChanged = onNightEndChanged,
                onClose = { showSettingsSheet = false },
            )
        }
    }
}

@Composable
private fun CheckingMainContent(
    uiState: CheckingUiState,
    onOpenLocationSheet: () -> Unit,
    onOpenSettingsSheet: () -> Unit,
    onChaveChanged: (String) -> Unit,
    onRegistroChanged: (RegistroType) -> Unit,
    onInformeChanged: (InformeType) -> Unit,
    onProjetoChanged: (ProjetoType) -> Unit,
    onSubmit: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val state = uiState.state

    Box(
        modifier = modifier.background(CheckingSurface),
        contentAlignment = Alignment.TopCenter,
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .widthIn(max = 560.dp)
                .padding(horizontal = 16.dp, vertical = 24.dp),
        ) {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                TopLogo()
                Header(
                    onOpenLocationSheet = onOpenLocationSheet,
                    onOpenSettingsSheet = onOpenSettingsSheet,
                )
                HistorySection(state = state)
                StatusLabel(state = state)
                ChaveInputField(
                    value = state.chave,
                    onValueChange = onChaveChanged,
                )
                SegmentedSelector(
                    value = state.registro,
                    options = RegistroType.entries,
                    label = RegistroType::label,
                    onValueChange = onRegistroChanged,
                )
                SegmentedSelector(
                    value = state.informe,
                    options = InformeType.entries,
                    label = InformeType::label,
                    onValueChange = onInformeChanged,
                )
                if (state.registro == RegistroType.CHECK_IN) {
                    SegmentedSelector(
                        value = state.projeto,
                        options = ProjetoType.entries,
                        label = ProjetoType::apiValue,
                        onValueChange = onProjetoChanged,
                    )
                }
                if (state.isSyncing || state.isLoading) {
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                }
            }

            Spacer(modifier = Modifier.height(20.dp))
            Button(
                onClick = onSubmit,
                enabled = CheckingController.isRegisterActionInteractive(state),
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
            ) {
                if (state.isSubmitting) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(22.dp),
                        strokeWidth = 2.2.dp,
                        color = MaterialTheme.colorScheme.onPrimary,
                    )
                } else {
                    Text(
                        text = "REGISTRAR",
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}

@Composable
private fun TopLogo() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(84.dp),
        contentAlignment = Alignment.Center,
    ) {
        Surface(
            color = CheckingCard,
            shape = RoundedCornerShape(8.dp),
            shadowElevation = 1.dp,
        ) {
            Image(
                painter = painterResource(id = R.drawable.ic_launcher_foreground),
                contentDescription = "Checking",
                contentScale = ContentScale.Fit,
                modifier = Modifier.size(76.dp),
            )
        }
    }
}

@Composable
private fun Header(
    onOpenLocationSheet: () -> Unit,
    onOpenSettingsSheet: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "Checking",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = "TBY - Autodeclaração de Presença.",
                style = MaterialTheme.typography.bodyMedium,
                color = CheckingMuted,
            )
        }
        HeaderIconButton(
            onClick = onOpenLocationSheet,
        ) {
            Icon(
                imageVector = Icons.Filled.LocationOn,
                contentDescription = "Automação por localização",
                tint = MaterialTheme.colorScheme.primary,
            )
        }
        HeaderIconButton(
            onClick = onOpenSettingsSheet,
        ) {
            Icon(
                imageVector = Icons.Filled.Settings,
                contentDescription = "Configurações do aplicativo",
                tint = CheckingText,
            )
        }
    }
}

@Composable
private fun HeaderIconButton(
    onClick: () -> Unit,
    content: @Composable () -> Unit,
) {
    Surface(
        shape = RoundedCornerShape(8.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, CheckingBorder),
        color = CheckingCard,
    ) {
        IconButton(
            onClick = onClick,
            modifier = Modifier.size(44.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                content()
            }
        }
    }
}

@Composable
private fun HistorySection(state: CheckingState) {
    GroupBox {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            HistoryItem(
                label = "Último Check-In",
                value = formatHistoryInstant(state.lastCheckIn),
                modifier = Modifier.weight(1f),
            )
            HistoryItem(
                label = "Último Check-Out",
                value = formatHistoryInstant(state.lastCheckOut),
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun HistoryItem(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.heightIn(min = 48.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = label.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = CheckingMuted,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            color = CheckingText,
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.Center,
            minLines = 2,
        )
    }
}

@Composable
private fun StatusLabel(state: CheckingState) {
    val message = state.statusMessage
    if (message.isBlank()) {
        Spacer(modifier = Modifier.height(4.dp))
        return
    }

    Text(
        text = message,
        style = MaterialTheme.typography.bodySmall,
        color = when (state.statusTone) {
            StatusTone.SUCCESS -> CheckingSuccess
            StatusTone.WARNING -> CheckingWarning
            StatusTone.ERROR -> CheckingError
            StatusTone.NEUTRAL -> CheckingMuted
        },
    )
}

@Composable
private fun ChaveInputField(
    value: String,
    onValueChange: (String) -> Unit,
) {
    val focusManager = LocalFocusManager.current
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = "Chave Petrobras",
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.SemiBold,
        )
        OutlinedTextField(
            value = value,
            onValueChange = { rawValue ->
                val normalized = normalizeKey(rawValue)
                onValueChange(normalized)
                if (normalized.length == 4) {
                    focusManager.clearFocus()
                }
            },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            placeholder = { Text("Digite sua chave aqui.") },
            keyboardOptions = KeyboardOptions(
                capitalization = KeyboardCapitalization.Characters,
                keyboardType = KeyboardType.Ascii,
            ),
            shape = RoundedCornerShape(8.dp),
        )
    }
}

@Composable
private fun <T> SegmentedSelector(
    value: T,
    options: List<T>,
    label: (T) -> String,
    onValueChange: (T) -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = CheckingCard,
        shape = RoundedCornerShape(8.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, CheckingBorder),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 50.dp),
        ) {
            options.forEachIndexed { index, option ->
                val selected = option == value
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .background(
                            if (selected) {
                                MaterialTheme.colorScheme.primary.copy(alpha = 0.10f)
                            } else {
                                Color.Transparent
                            },
                        )
                        .clickable { onValueChange(option) }
                        .padding(horizontal = 8.dp, vertical = 12.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = label(option),
                        color = if (selected) MaterialTheme.colorScheme.primary else CheckingText,
                        fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                        textAlign = TextAlign.Center,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                if (index != options.lastIndex) {
                    VerticalDivider(color = CheckingBorder)
                }
            }
        }
    }
}

@Composable
private fun LocationAutomationSheet(
    state: CheckingState,
    managedLocationCount: Int,
    onAutomaticCheckingChanged: (Boolean) -> Unit,
    onClose: () -> Unit,
) {
    var showHistoryDialog by remember { mutableStateOf(false) }

    SheetContent {
        SheetTitle("Automação por Localização")
        SwitchRow(
            label = "Check-in/Check-out automáticos:",
            value = CheckingRuntimeLogic.isAutomaticCheckingEnabledInUi(state),
            isBusy = state.isAutomaticCheckingUpdating,
            onCheckedChange = if (CheckingRuntimeLogic.isAutomaticCheckingToggleInteractive(state)) {
                onAutomaticCheckingChanged
            } else {
                null
            },
        )
        OutlinedButton(
            onClick = { showHistoryDialog = true },
            shape = RoundedCornerShape(8.dp),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Icon(imageVector = Icons.Filled.History, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Últimas Localizações")
        }
        DetailRow("Última Atualização", formatDetailedInstant(state.lastLocationUpdateAt))
        DetailRow(
            "Atualizações",
            CheckingLocationLogic.describeLocationUpdateInterval(
                configuredIntervalSeconds = state.locationUpdateIntervalSeconds,
            ),
        )
        DetailRow("Locais monitorados", managedLocationCount.toString())
        CapturedLocationBox(state.lastDetectedLocation)
        SheetCloseButton(onClose)
    }

    if (showHistoryDialog) {
        RecentLocationHistoryDialog(
            history = state.locationFetchHistory,
            onDismiss = { showHistoryDialog = false },
        )
    }
}

@Composable
private fun SettingsSheet(
    state: CheckingState,
    permissionSettings: CheckingPermissionSettingsState,
    onLocationSharingChanged: (Boolean) -> Unit,
    onSyncHistory: () -> Unit,
    onRefreshCatalog: () -> Unit,
    onLocationUpdateIntervalChanged: (Int) -> Unit,
    onNightUpdatesChanged: (Boolean) -> Unit,
    onNightModeAfterCheckoutChanged: (Boolean) -> Unit,
    onNightStartChanged: (Int) -> Unit,
    onNightEndChanged: (Int) -> Unit,
    onClose: () -> Unit,
) {
    SheetContent {
        SheetTitle("Configurações")
        SectionTitle("Permissões")
        GroupBox {
            SwitchRow(
                label = "Compartilhar Localização:",
                value = state.locationSharingEnabled,
                isBusy = state.isLocationUpdating,
                onCheckedChange = if (CheckingRuntimeLogic.isLocationSharingToggleInteractive(state)) {
                    onLocationSharingChanged
                } else {
                    null
                },
            )
            SwitchRow(
                label = "Acesso em 2º plano:",
                value = permissionSettings.backgroundAccessEnabled,
                isBusy = permissionSettings.isRefreshing,
                onCheckedChange = null,
            )
            SwitchRow(
                label = "Permitir notificações:",
                value = permissionSettings.notificationsEnabled,
                isBusy = permissionSettings.isRefreshing,
                onCheckedChange = null,
            )
            SwitchRow(
                label = "Sem restrições de bateria:",
                value = permissionSettings.batteryOptimizationIgnored,
                isBusy = permissionSettings.isRefreshing,
                onCheckedChange = null,
            )
        }
        SectionTitle("Sincronização")
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            OutlinedButton(
                onClick = onSyncHistory,
                enabled = !state.isSyncing,
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.weight(1f),
            ) {
                Icon(imageVector = Icons.Filled.Refresh, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Histórico")
            }
            OutlinedButton(
                onClick = onRefreshCatalog,
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.weight(1f),
            ) {
                Icon(imageVector = Icons.Filled.Refresh, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Catálogo")
            }
        }
        SectionTitle("Ajustes Gerais")
        GroupBox {
            IntervalSlider(
                intervalSeconds = state.locationUpdateIntervalSeconds,
                onChanged = onLocationUpdateIntervalChanged,
            )
            SwitchRow(
                label = "Modo noturno após check-out:",
                value = state.nightModeAfterCheckoutEnabled,
                onCheckedChange = onNightModeAfterCheckoutChanged,
            )
            if (!state.nightModeAfterCheckoutEnabled) {
                SwitchRow(
                    label = "Desativar atualização noturna:",
                    value = state.nightUpdatesDisabled,
                    onCheckedChange = onNightUpdatesChanged,
                )
                if (state.nightUpdatesDisabled) {
                    MinutesStepper(
                        label = "De",
                        value = state.nightPeriodStartMinutes,
                        onChanged = onNightStartChanged,
                    )
                    MinutesStepper(
                        label = "Até",
                        value = state.nightPeriodEndMinutes,
                        onChanged = onNightEndChanged,
                    )
                }
            }
        }
        SheetCloseButton(onClose)
    }
}

@Composable
private fun SheetContent(content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(max = 720.dp)
            .verticalScroll(rememberScrollState())
            .padding(start = 18.dp, end = 18.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
        content = content,
    )
}

@Composable
private fun SheetTitle(text: String) {
    Text(
        text = text,
        modifier = Modifier.fillMaxWidth(),
        textAlign = TextAlign.Center,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.Bold,
    )
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text = text,
        modifier = Modifier.fillMaxWidth(),
        textAlign = TextAlign.Center,
        style = MaterialTheme.typography.titleSmall,
        fontWeight = FontWeight.Bold,
    )
}

@Composable
private fun SwitchRow(
    label: String,
    value: Boolean,
    onCheckedChange: ((Boolean) -> Unit)?,
    isBusy: Boolean = false,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = label,
            modifier = Modifier.weight(1f),
            style = MaterialTheme.typography.bodyMedium,
            color = CheckingText,
        )
        if (isBusy) {
            CircularProgressIndicator(
                modifier = Modifier.size(28.dp),
                strokeWidth = 2.dp,
            )
        } else {
            Switch(
                checked = value,
                onCheckedChange = onCheckedChange,
            )
        }
    }
}

@Composable
private fun IntervalSlider(
    intervalSeconds: Int,
    onChanged: (Int) -> Unit,
) {
    var sliderValue by remember(intervalSeconds) {
        mutableFloatStateOf((intervalSeconds / 60f).coerceIn(15f, 60f))
    }

    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        DetailRow("Frequência de Atividades", "${sliderValue.roundToInt()} min")
        Slider(
            value = sliderValue,
            onValueChange = { value ->
                sliderValue = value
            },
            onValueChangeFinished = {
                onChanged(sliderValue.roundToInt())
            },
            valueRange = 15f..60f,
            steps = 2,
        )
        Text(
            text = "Aplicado imediatamente em primeiro e segundo plano.",
            style = MaterialTheme.typography.bodySmall,
            color = CheckingMuted,
        )
    }
}

@Composable
private fun MinutesStepper(
    label: String,
    value: Int,
    onChanged: (Int) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            text = label,
            modifier = Modifier.width(42.dp),
            fontWeight = FontWeight.SemiBold,
        )
        OutlinedButton(
            onClick = { onChanged(shiftMinutes(value, -30)) },
            shape = RoundedCornerShape(8.dp),
        ) {
            Text("-")
        }
        Text(
            text = formatMinutesOfDay(value),
            modifier = Modifier.weight(1f),
            textAlign = TextAlign.Center,
            fontWeight = FontWeight.Bold,
        )
        OutlinedButton(
            onClick = { onChanged(shiftMinutes(value, 30)) },
            shape = RoundedCornerShape(8.dp),
        ) {
            Text("+")
        }
    }
}

@Composable
private fun DetailRow(
    label: String,
    value: String,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            text = "$label:",
            modifier = Modifier.weight(0.9f),
            style = MaterialTheme.typography.bodyMedium,
            color = CheckingText,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text = value.ifBlank { "--" },
            modifier = Modifier.weight(1.1f),
            style = MaterialTheme.typography.bodyMedium,
            color = CheckingText,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun CapturedLocationBox(locationName: String?) {
    GroupBox {
        Text(
            text = "Local Capturado",
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Bold,
            color = CheckingText,
        )
        Text(
            text = locationName?.takeIf { it.isNotBlank() } ?: "--",
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center,
            style = MaterialTheme.typography.bodyLarge,
            color = if (locationName.isNullOrBlank()) CheckingMuted else CheckingSuccess,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun GroupBox(content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .border(1.dp, CheckingBorder, RoundedCornerShape(8.dp))
            .background(CheckingCard)
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        content = content,
    )
}

@Composable
private fun SheetCloseButton(onClose: () -> Unit) {
    Button(
        onClick = onClose,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
    ) {
        Icon(imageVector = Icons.Filled.Close, contentDescription = null)
        Spacer(modifier = Modifier.width(8.dp))
        Text("Fechar")
    }
}

@Composable
private fun RecentLocationHistoryDialog(
    history: List<LocationFetchEntry>,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Fechar")
            }
        },
        title = {
            Text(
                text = "Últimas Localizações",
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                HistoryTableHeader()
                HorizontalDivider(color = CheckingBorder)
                if (history.isEmpty()) {
                    HistoryTableRow("--", "--", "--\n--")
                } else {
                    history.forEach { entry ->
                        HistoryTableRow(
                            date = formatDate(entry.timestamp),
                            time = formatTime(entry.timestamp),
                            coordinate = formatCoordinatePair(entry),
                        )
                    }
                }
            }
        },
    )
}

@Composable
private fun HistoryTableHeader() {
    HistoryTableRow(
        date = "Data",
        time = "Hora",
        coordinate = "Coordenada",
        header = true,
    )
}

@Composable
private fun HistoryTableRow(
    date: String,
    time: String,
    coordinate: String,
    header: Boolean = false,
) {
    val weight = if (header) FontWeight.Bold else FontWeight.SemiBold
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = date,
            modifier = Modifier.weight(1f),
            textAlign = TextAlign.Center,
            fontWeight = weight,
            style = MaterialTheme.typography.bodySmall,
        )
        Text(
            text = time,
            modifier = Modifier.weight(1f),
            textAlign = TextAlign.Center,
            fontWeight = weight,
            style = MaterialTheme.typography.bodySmall,
        )
        Text(
            text = coordinate,
            modifier = Modifier.weight(2f),
            textAlign = TextAlign.Center,
            fontWeight = weight,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

private fun normalizeKey(value: String): String {
    return value.uppercase()
        .replace(Regex("[^A-Z0-9]"), "")
        .take(4)
}

private fun formatHistoryInstant(value: Instant?): String {
    if (value == null) {
        return ""
    }
    return "${formatDate(value)}\n${formatTime(value)}"
}

private fun formatDetailedInstant(value: Instant?): String {
    if (value == null) {
        return "--"
    }
    return detailedInstantFormatter.format(value)
}

private fun formatDate(value: Instant): String = dateFormatter.format(value)

private fun formatTime(value: Instant): String = timeFormatter.format(value)

private fun formatCoordinatePair(entry: LocationFetchEntry): String {
    val latitude = entry.latitude
    val longitude = entry.longitude
    return if (latitude == null || longitude == null) {
        "--\n--"
    } else {
        "${"%.6f".format(latitude)}\n${"%.6f".format(longitude)}"
    }
}

private fun formatMinutesOfDay(totalMinutes: Int): String {
    val safeMinutes = ((totalMinutes % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY
    val hours = safeMinutes / 60
    val minutes = safeMinutes % 60
    return "${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}"
}

private fun shiftMinutes(totalMinutes: Int, delta: Int): Int {
    return ((totalMinutes + delta) % MINUTES_PER_DAY + MINUTES_PER_DAY) % MINUTES_PER_DAY
}

private const val MINUTES_PER_DAY = 24 * 60

private val userZone: ZoneId = ZoneId.systemDefault()
private val dateFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("dd/MM/yyyy").withZone(userZone)
private val timeFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("HH:mm:ss").withZone(userZone)
private val detailedInstantFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("dd-MM-yyyy HH:mm:ss").withZone(userZone)
