package com.br.checkingnative.ui.checking

import androidx.compose.animation.Crossfade
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.PressInteraction
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.GpsFixed
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.RadioButton
import androidx.compose.material3.RadioButtonDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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
import com.br.checkingnative.ui.theme.CheckingError
import com.br.checkingnative.ui.theme.CheckingInputFill
import com.br.checkingnative.ui.theme.CheckingMuted
import com.br.checkingnative.ui.theme.CheckingPrimarySoft
import com.br.checkingnative.ui.theme.CheckingSuccess
import com.br.checkingnative.ui.theme.CheckingSurface
import com.br.checkingnative.ui.theme.CheckingText
import com.br.checkingnative.ui.theme.CheckingWarning
import com.br.checkingnative.ui.theme.CheckingWheelSurface
import com.br.checkingnative.ui.theme.CheckingBlue
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlin.math.max
import kotlinx.coroutines.delay
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
    onLocationSharingChanged: (Boolean) -> Unit,
    onBackgroundAccessChanged: (Boolean) -> Unit,
    onNotificationsChanged: (Boolean) -> Unit,
    onBatteryOptimizationChanged: (Boolean) -> Unit,
    onOemBackgroundSetupChanged: (Boolean) -> Unit,
    onAutomaticCheckingChanged: (Boolean) -> Unit,
    onLocationUpdateIntervalChanged: (Int) -> Unit,
    onNightUpdatesChanged: (Boolean) -> Unit,
    onNightModeAfterCheckoutChanged: (Boolean) -> Unit,
    onNightStartChanged: (Int) -> Unit,
    onNightEndChanged: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    var showPresentation by rememberSaveable { mutableStateOf(true) }
    val snackbarHostState = remember { SnackbarHostState() }
    var showLocationSheet by remember { mutableStateOf(false) }
    var showSettingsSheet by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        delay(PRESENTATION_DURATION_MILLIS)
        showPresentation = false
    }

    LaunchedEffect(messages) {
        messages.collect { message ->
            snackbarHostState.showSnackbar(message)
        }
    }

    Crossfade(
        targetState = showPresentation,
        label = "checking-presentation",
        modifier = modifier.fillMaxSize(),
    ) { showingPresentation ->
        if (showingPresentation) {
            PresentationScreen()
            return@Crossfade
        }

        Scaffold(
            modifier = Modifier.fillMaxSize(),
            contentWindowInsets = WindowInsets.safeDrawing,
            containerColor = CheckingSurface,
            snackbarHost = {
                SnackbarHost(hostState = snackbarHostState) { data ->
                    Snackbar(
                        snackbarData = data,
                        containerColor = Color.Black.copy(alpha = 0.82f),
                        contentColor = Color.White,
                        shape = RoundedCornerShape(16.dp),
                    )
                }
            },
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
    }

    if (showLocationSheet) {
        ModalBottomSheet(
            onDismissRequest = { showLocationSheet = false },
            containerColor = CheckingSurface,
            shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
            dragHandle = { SheetHandle() },
        ) {
            LocationAutomationSheet(
                state = uiState.state,
                onAutomaticCheckingChanged = onAutomaticCheckingChanged,
                onClose = { showLocationSheet = false },
            )
        }
    }

    if (showSettingsSheet) {
        ModalBottomSheet(
            onDismissRequest = { showSettingsSheet = false },
            containerColor = CheckingSurface,
            shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
            dragHandle = { SheetHandle() },
        ) {
            SettingsSheet(
                state = uiState.state,
                permissionSettings = uiState.permissionSettings,
                onLocationSharingChanged = onLocationSharingChanged,
                onBackgroundAccessChanged = onBackgroundAccessChanged,
                onNotificationsChanged = onNotificationsChanged,
                onBatteryOptimizationChanged = onBatteryOptimizationChanged,
                onOemBackgroundSetupChanged = onOemBackgroundSetupChanged,
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
private fun PresentationScreen() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .padding(horizontal = 24.dp),
    ) {
        BoxWithConstraints(
            modifier = Modifier
                .align(Alignment.Center)
                .offset(y = (-160).dp),
            contentAlignment = Alignment.Center,
        ) {
            val logoWidth = maxWidth * 0.5f
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Image(
                    painter = painterResource(id = R.drawable.app_icon_3x),
                    contentDescription = "Checking",
                    contentScale = ContentScale.Fit,
                    modifier = Modifier.width(logoWidth),
                )
                Spacer(modifier = Modifier.height(24.dp))
                Text(
                    text = "Checking",
                    color = CheckingBlue,
                    fontSize = 40.sp,
                    fontWeight = FontWeight.ExtraBold,
                    textAlign = TextAlign.Center,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.width(logoWidth),
                )
            }
        }
        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 50.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = "Dilnei Schmidt (CYMQ)",
                color = Color.Black,
                fontSize = 20.sp,
                fontWeight = FontWeight.Light,
                textAlign = TextAlign.Center,
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Tamer Salmem (HR70)",
                color = Color.Black,
                fontSize = 20.sp,
                fontWeight = FontWeight.Light,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
private fun SheetHandle() {
    Box(
        modifier = Modifier
            .padding(top = 12.dp, bottom = 6.dp)
            .size(width = 44.dp, height = 4.dp)
            .clip(RoundedCornerShape(999.dp))
            .background(CheckingBorder),
    )
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
                .padding(start = 16.dp, top = 24.dp, end = 16.dp, bottom = 36.dp),
        ) {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState()),
            ) {
                TopLogo()
                Spacer(modifier = Modifier.height(20.dp))
                Header(
                    onOpenLocationSheet = onOpenLocationSheet,
                    onOpenSettingsSheet = onOpenSettingsSheet,
                )
                HistorySection(state = state)
                Spacer(modifier = Modifier.height(8.dp))
                StatusLabel(state = state)
                Spacer(modifier = Modifier.height(20.dp))
                ChaveInputField(
                    value = state.chave,
                    onValueChange = onChaveChanged,
                )
                Spacer(modifier = Modifier.height(12.dp))
                RadioGroupSelector(
                    value = state.registro,
                    options = RegistroType.entries,
                    label = RegistroType::label,
                    onValueChange = onRegistroChanged,
                )
                Spacer(modifier = Modifier.height(12.dp))
                RadioGroupSelector(
                    value = state.informe,
                    options = InformeType.entries,
                    label = InformeType::label,
                    onValueChange = onInformeChanged,
                )
                if (state.registro == RegistroType.CHECK_IN) {
                    Spacer(modifier = Modifier.height(12.dp))
                    RadioGroupSelector(
                        value = state.projeto,
                        options = ProjetoType.entries,
                        label = ProjetoType::apiValue,
                        onValueChange = onProjetoChanged,
                    )
                }
                if (state.isSyncing || state.isLoading) {
                    Spacer(modifier = Modifier.height(12.dp))
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                }
            }

            Spacer(modifier = Modifier.height(24.dp))
            Button(
                onClick = onSubmit,
                enabled = CheckingController.isRegisterActionInteractive(state),
                shape = RoundedCornerShape(14.dp),
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
    BoxWithConstraints(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .width(maxWidth * 0.82f)
                .heightIn(max = 90.dp),
            contentAlignment = Alignment.Center,
        ) {
            Image(
                painter = painterResource(id = R.drawable.app_icon),
                contentDescription = "Checking",
                contentScale = ContentScale.Fit,
                modifier = Modifier.heightIn(max = 90.dp),
            )
        }
    }
}

@Composable
private fun Header(
    onOpenLocationSheet: () -> Unit,
    onOpenSettingsSheet: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 20.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "Checking",
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.weight(1f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                HeaderIconButton(
                    onClick = onOpenLocationSheet,
                ) {
                    Icon(
                        imageVector = Icons.Rounded.GpsFixed,
                        contentDescription = "Automação por localização",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(22.dp),
                    )
                }
                HeaderIconButton(
                    onClick = onOpenSettingsSheet,
                ) {
                    Icon(
                        imageVector = Icons.Rounded.Settings,
                        contentDescription = "Configurações do aplicativo",
                        tint = CheckingText,
                        modifier = Modifier.size(22.dp),
                    )
                }
            }
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "TBY - Autodeclaração de Presença.",
            style = MaterialTheme.typography.bodyMedium,
            color = CheckingMuted,
        )
    }
}

@Composable
private fun HeaderIconButton(
    onClick: () -> Unit,
    content: @Composable () -> Unit,
) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, CheckingBorder),
        color = CheckingSurface,
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
    val keyboardController = LocalSoftwareKeyboardController.current
    val interactionSource = remember { MutableInteractionSource() }

    LaunchedEffect(interactionSource, value) {
        interactionSource.interactions.collect { interaction ->
            if (interaction is PressInteraction.Press && value.isNotEmpty()) {
                onValueChange("")
            }
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = "Chave Petrobras",
            style = MaterialTheme.typography.titleSmall,
        )
        TextField(
            value = value,
            onValueChange = { rawValue ->
                val normalized = normalizeKey(rawValue)
                onValueChange(normalized)
                if (normalized.length == 4) {
                    focusManager.clearFocus()
                    keyboardController?.hide()
                }
            },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            placeholder = { Text("Digite sua chave aqui.") },
            keyboardOptions = KeyboardOptions(
                capitalization = KeyboardCapitalization.Characters,
                keyboardType = KeyboardType.Ascii,
            ),
            interactionSource = interactionSource,
            shape = RoundedCornerShape(12.dp),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = CheckingInputFill,
                unfocusedContainerColor = CheckingInputFill,
                disabledContainerColor = CheckingInputFill,
                cursorColor = MaterialTheme.colorScheme.primary,
                focusedIndicatorColor = MaterialTheme.colorScheme.primary,
                unfocusedIndicatorColor = Color.Transparent,
                disabledIndicatorColor = Color.Transparent,
            ),
        )
    }
}

@Composable
private fun <T> RadioGroupSelector(
    value: T,
    options: List<T>,
    label: (T) -> String,
    onValueChange: (T) -> Unit,
) {
    GroupBox(
        modifier = Modifier.fillMaxWidth(),
        contentPadding = PaddingValues(8.dp),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 46.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            options.forEach { option ->
                RadioOptionTile(
                    selected = option == value,
                    label = label(option),
                    onTap = { onValueChange(option) },
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxHeight(),
                )
            }
        }
    }
}

@Composable
private fun RadioOptionTile(
    selected: Boolean,
    label: String,
    onTap: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .border(
                width = 1.dp,
                color = if (selected) MaterialTheme.colorScheme.primary else CheckingBorder,
                shape = RoundedCornerShape(12.dp),
            )
            .background(if (selected) CheckingPrimarySoft else CheckingSurface)
            .clickable(onClick = onTap)
            .padding(horizontal = 8.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        RadioButton(
            selected = selected,
            onClick = onTap,
            colors = RadioButtonDefaults.colors(
                selectedColor = MaterialTheme.colorScheme.primary,
                unselectedColor = CheckingMuted,
            ),
        )
        Spacer(modifier = Modifier.width(2.dp))
        Text(
            text = label,
            color = if (selected) MaterialTheme.colorScheme.primary else CheckingText,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Medium,
            textAlign = TextAlign.Center,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun LocationAutomationSheet(
    state: CheckingState,
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
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Icon(imageVector = Icons.Rounded.History, contentDescription = null)
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
        CapturedLocationBox(state.lastDetectedLocation)
        DangerCloseButton(onClose)
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
    onBackgroundAccessChanged: (Boolean) -> Unit,
    onNotificationsChanged: (Boolean) -> Unit,
    onBatteryOptimizationChanged: (Boolean) -> Unit,
    onOemBackgroundSetupChanged: (Boolean) -> Unit,
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
                label = "Acesso em 2º Plano:",
                value = permissionSettings.backgroundAccessEnabled,
                isBusy = permissionSettings.isRefreshing,
                onCheckedChange = onBackgroundAccessChanged,
            )
            SwitchRow(
                label = "Permitir Notificações:",
                value = permissionSettings.notificationsEnabled,
                isBusy = permissionSettings.isRefreshing,
                onCheckedChange = onNotificationsChanged,
            )
            SwitchRow(
                label = "Sem Restrições de Bateria:",
                value = permissionSettings.batteryOptimizationIgnored,
                isBusy = permissionSettings.isRefreshing,
                onCheckedChange = onBatteryOptimizationChanged,
            )
            SwitchRow(
                label = "Ativar Auto-Start:",
                value = state.oemBackgroundSetupEnabled,
                isBusy = permissionSettings.isRefreshing,
                onCheckedChange = if (state.canEnableLocationSharing) {
                    onOemBackgroundSetupChanged
                } else {
                    null
                },
            )
        }
        SectionTitle("Ajustes Gerais")
        GroupBox {
            Text(
                text = "Frequência de Atividades",
                style = MaterialTheme.typography.titleSmall,
            )
            FrequencyWheelSelector(
                selectedMinutes = state.locationUpdateIntervalSeconds / 60,
                onChanged = onLocationUpdateIntervalChanged,
            )
            Text(
                text = "Aplicado imediatamente em primeiro e segundo plano.",
                style = MaterialTheme.typography.bodySmall,
                color = CheckingMuted,
            )
            SwitchRow(
                label = "Modo Noturno Após Check-out:",
                value = state.nightModeAfterCheckoutEnabled,
                onCheckedChange = onNightModeAfterCheckoutChanged,
            )
            if (!state.nightModeAfterCheckoutEnabled) {
                SwitchRow(
                    label = "Desativar Atualização Noturna:",
                    value = state.nightUpdatesDisabled,
                    onCheckedChange = onNightUpdatesChanged,
                )
                if (state.nightUpdatesDisabled) {
                    MinutesOfDayWheelField(
                        label = "De",
                        value = state.nightPeriodStartMinutes,
                        onChanged = onNightStartChanged,
                    )
                    MinutesOfDayWheelField(
                        label = "Até",
                        value = state.nightPeriodEndMinutes,
                        onChanged = onNightEndChanged,
                    )
                }
            }
        }
        DangerCloseButton(onClose)
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
                colors = SwitchDefaults.colors(
                    checkedThumbColor = MaterialTheme.colorScheme.primary,
                    checkedTrackColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.32f),
                    uncheckedThumbColor = CheckingMuted,
                    uncheckedTrackColor = CheckingBorder,
                    disabledCheckedThumbColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.42f),
                    disabledUncheckedThumbColor = CheckingMuted.copy(alpha = 0.42f),
                ),
            )
        }
    }
}

@Composable
private fun FrequencyWheelSelector(
    selectedMinutes: Int,
    onChanged: (Int) -> Unit,
) {
    val safeMinutes = selectedMinutes.coerceIn(
        CheckingLocationLogic.minLocationUpdateIntervalMinutes,
        CheckingLocationLogic.maxLocationUpdateIntervalMinutes,
    )
    val values = (
        CheckingLocationLogic.minLocationUpdateIntervalMinutes..
            CheckingLocationLogic.maxLocationUpdateIntervalMinutes
        ).toList()

    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = Alignment.Center,
    ) {
        WheelSelector(
            itemCount = values.size,
            selectedIndex = safeMinutes - CheckingLocationLogic.minLocationUpdateIntervalMinutes,
            itemLabel = { index -> "${values[index]} min" },
            onSelectedIndex = { index -> onChanged(values[index]) },
            modifier = Modifier.width(136.dp),
        )
    }
}

@Composable
private fun MinutesOfDayWheelField(
    label: String,
    value: Int,
    onChanged: (Int) -> Unit,
) {
    val safeValue = normalizeMinutesOfDay(value)
    val selectedHour = safeValue / 60
    val selectedMinute = safeValue % 60

    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.titleSmall,
        )
        Row(
            modifier = Modifier
                .align(Alignment.CenterHorizontally)
                .width(164.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(CheckingWheelSurface)
                .padding(horizontal = 10.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            WheelSelector(
                itemCount = 24,
                selectedIndex = selectedHour,
                itemLabel = { index -> index.toString().padStart(2, '0') },
                onSelectedIndex = { hour -> onChanged((hour * 60) + selectedMinute) },
                modifier = Modifier.width(68.dp),
            )
            WheelSelector(
                itemCount = 60,
                selectedIndex = selectedMinute,
                itemLabel = { index -> index.toString().padStart(2, '0') },
                onSelectedIndex = { minute -> onChanged((selectedHour * 60) + minute) },
                modifier = Modifier.width(68.dp),
            )
        }
        Text(
            text = formatMinutesOfDay(safeValue),
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.End,
            style = MaterialTheme.typography.bodySmall,
            color = CheckingMuted,
        )
    }
}

@Composable
private fun WheelSelector(
    itemCount: Int,
    selectedIndex: Int,
    itemLabel: (Int) -> String,
    onSelectedIndex: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val safeSelectedIndex = selectedIndex.coerceIn(0, max(0, itemCount - 1))
    val listState = rememberLazyListState(initialFirstVisibleItemIndex = safeSelectedIndex)

    LaunchedEffect(safeSelectedIndex) {
        if (listState.firstVisibleItemIndex != safeSelectedIndex) {
            listState.animateScrollToItem(safeSelectedIndex)
        }
    }

    LazyColumn(
        state = listState,
        modifier = modifier
            .height(150.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(CheckingWheelSurface),
        horizontalAlignment = Alignment.CenterHorizontally,
        contentPadding = PaddingValues(vertical = 18.dp),
    ) {
        items(itemCount) { index ->
            val selected = index == safeSelectedIndex
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(38.dp)
                    .clickable { onSelectedIndex(index) },
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = itemLabel(index),
                    fontSize = if (selected) 20.sp else 16.sp,
                    fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                    color = if (selected) MaterialTheme.colorScheme.primary else CheckingMuted,
                    textAlign = TextAlign.Center,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
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
            text = locationName?.takeIf { it.isNotBlank() } ?: "",
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center,
            style = MaterialTheme.typography.bodyLarge,
            color = if (locationName.isNullOrBlank()) CheckingMuted else CheckingSuccess,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun GroupBox(
    modifier: Modifier = Modifier,
    contentPadding: PaddingValues = PaddingValues(12.dp),
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .border(1.dp, CheckingBorder, RoundedCornerShape(12.dp))
            .background(CheckingSurface)
            .padding(contentPadding),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        content = content,
    )
}

@Composable
private fun DangerCloseButton(onClose: () -> Unit) {
    Button(
        onClick = onClose,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = CheckingError,
            contentColor = Color.White,
            disabledContainerColor = CheckingError.copy(alpha = 0.42f),
            disabledContentColor = Color.White.copy(alpha = 0.72f),
        ),
    ) {
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
    val safeMinutes = normalizeMinutesOfDay(totalMinutes)
    val hours = safeMinutes / 60
    val minutes = safeMinutes % 60
    return "${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}"
}

private fun normalizeMinutesOfDay(totalMinutes: Int): Int {
    return ((totalMinutes % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY
}

private const val MINUTES_PER_DAY = 24 * 60
private const val PRESENTATION_DURATION_MILLIS = 2_000L

private val userZone: ZoneId = ZoneId.systemDefault()
private val dateFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("dd/MM/yyyy").withZone(userZone)
private val timeFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("HH:mm:ss").withZone(userZone)
private val detailedInstantFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("dd-MM-yyyy HH:mm:ss").withZone(userZone)
