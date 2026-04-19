package com.br.checkingnative.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BootstrapApp(
    uiState: BootstrapUiState,
    modifier: Modifier = Modifier,
) {
    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = {
                    Text(text = "Checking Kotlin")
                },
            )
        },
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
                .padding(innerPadding)
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item {
                HeaderSection(uiState = uiState)
            }
            item {
                EnvironmentCard(uiState = uiState)
            }
            item {
                ReadinessCard(uiState = uiState)
            }
            item {
                PersistedStateCard(uiState = uiState)
            }
            item {
                LegacyMigrationCard(uiState = uiState)
            }
            item {
                NextStepsCard(nextSteps = uiState.nextSteps)
            }
        }
    }
}

@Composable
private fun HeaderSection(uiState: BootstrapUiState) {
    Card(
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer,
        ),
        shape = RoundedCornerShape(28.dp),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.14f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = "K",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                )
            }

            Text(
                text = "Controller funcional portado para Kotlin",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )

            Text(
                text = "${uiState.phaseLabel}. O app Kotlin agora hidrata estado local, sincroniza historico, atualiza catalogo e envia registros manuais pela API nativa.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun EnvironmentCard(uiState: BootstrapUiState) {
    InfoCard(title = "Decisoes da Fase 0") {
        DetailRow(label = "Application ID", value = uiState.applicationId)
        DetailRow(label = "Namespace", value = uiState.namespace)
        DetailRow(label = "Modo", value = uiState.coexistenceMode)
    }
}

@Composable
private fun ReadinessCard(uiState: BootstrapUiState) {
    InfoCard(title = "Estado da Fase 4") {
        StatusRow(
            label = "Compose e Activity",
            value = "Configurados",
            success = true,
        )
        StatusRow(
            label = "Hilt",
            value = if (uiState.dataStoreReady) "Conectado" else "Pendente",
            success = uiState.dataStoreReady,
        )
        StatusRow(
            label = "DataStore",
            value = if (uiState.dataStoreReady) "Pronto" else "Pendente",
            success = uiState.dataStoreReady,
        )
        StatusRow(
            label = "Repositorio de estado",
            value = if (uiState.stateRepositoryReady) "Pronto" else "Pendente",
            success = uiState.stateRepositoryReady,
        )
        StatusRow(
            label = "Room",
            value = if (uiState.roomReady) "Pronto" else "Pendente",
            success = uiState.roomReady,
        )
        StatusRow(
            label = "Schema legado",
            value = if (uiState.legacySchemaReady) "Alinhado ao Flutter" else "Pendente",
            success = uiState.legacySchemaReady,
        )
        StatusRow(
            label = "Cliente de API",
            value = if (uiState.apiClientReady) "Portado" else "Pendente",
            success = uiState.apiClientReady,
        )
        StatusRow(
            label = "Regras de dominio",
            value = if (uiState.domainLogicReady) "Portadas" else "Pendente",
            success = uiState.domainLogicReady,
        )
        StatusRow(
            label = "Controller Kotlin",
            value = if (uiState.controllerReady) "Inicializado" else "Carregando",
            success = uiState.controllerReady,
        )
        StatusRow(
            label = "Sync de historico",
            value = if (uiState.manualHistorySyncReady) "Conectado a API" else "Pendente",
            success = uiState.manualHistorySyncReady,
        )
        StatusRow(
            label = "Envio manual",
            value = if (uiState.manualSubmitReady) "Conectado a API" else "Pendente",
            success = uiState.manualSubmitReady,
        )
        StatusRow(
            label = "Catalogo de locais",
            value = if (uiState.catalogSyncReady) "Conectado a API e cache" else "Pendente",
            success = uiState.catalogSyncReady,
        )
    }
}

@Composable
private fun PersistedStateCard(uiState: BootstrapUiState) {
    InfoCard(title = "Estado persistido") {
        DetailRow(
            label = "Snapshot salvo",
            value = if (uiState.hasPersistedState) "Sim" else "Nao",
        )
        DetailRow(label = "Chave", value = uiState.chavePreview)
        DetailRow(label = "Registro sugerido", value = uiState.registroLabel)
        DetailRow(
            label = "Intervalo de localizacao",
            value = "${uiState.locationIntervalSeconds}s",
        )
        DetailRow(
            label = "Compartilhamento",
            value = if (uiState.locationSharingEnabled) "Ativo" else "Inativo",
        )
        DetailRow(
            label = "Automacao local",
            value = if (uiState.automaticCheckInOutEnabled) "Ativa" else "Inativa",
        )
        DetailRow(
            label = "Locais no banco",
            value = uiState.managedLocationCount.toString(),
        )
        DetailRow(
            label = "Sync ativo",
            value = if (uiState.isSyncing) "Sim" else "Nao",
        )
        DetailRow(
            label = "Envio ativo",
            value = if (uiState.isSubmitting) "Sim" else "Nao",
        )
        if (uiState.currentStatusMessage.isNotBlank()) {
            Text(
                text = uiState.currentStatusMessage,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun LegacyMigrationCard(uiState: BootstrapUiState) {
    InfoCard(title = "Migracao legada") {
        DetailRow(
            label = "App Flutter detectado",
            value = if (uiState.legacySourceInstalled) "Sim" else "Nao",
        )
        DetailRow(label = "Status", value = uiState.legacyMigrationStatus)
        Text(
            text = uiState.legacyMigrationMessage,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun NextStepsCard(nextSteps: List<String>) {
    InfoCard(title = "Proximas entregas") {
        nextSteps.forEachIndexed { index, step ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.Top,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text(
                    text = "${index + 1}.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = step,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (index != nextSteps.lastIndex) {
                Spacer(modifier = Modifier.height(10.dp))
            }
        }
    }
}

@Composable
private fun InfoCard(
    title: String,
    content: @Composable () -> Unit,
) {
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
            )
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
            content()
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
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium,
        )
    }
}

@Composable
private fun StatusRow(
    label: String,
    value: String,
    success: Boolean,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Surface(
            shape = CircleShape,
            color = if (success) {
                Color(0xFFDAF5E4)
            } else {
                Color(0xFFFCE7E7)
            },
        ) {
            Text(
                modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp),
                text = if (success) "OK" else "AL",
                style = MaterialTheme.typography.labelSmall,
                color = if (success) Color(0xFF1F7A3E) else Color(0xFFC0392B),
            )
        }

        Column(
            verticalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium,
            )
            Text(
                text = value,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
