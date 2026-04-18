package com.br.checkingnative.ui

data class BootstrapUiState(
    val applicationId: String = "com.br.checkingnative",
    val namespace: String = "com.br.checkingnative",
    val phaseLabel: String = "Fase 3 - API e dominio puro",
    val coexistenceMode: String = "App Kotlin separado do Flutter",
    val dataStoreReady: Boolean = false,
    val roomReady: Boolean = false,
    val stateRepositoryReady: Boolean = false,
    val legacySchemaReady: Boolean = false,
    val apiClientReady: Boolean = false,
    val domainLogicReady: Boolean = false,
    val managedLocationCount: Int = 0,
    val hasPersistedState: Boolean = false,
    val chavePreview: String = "Nao definida",
    val registroLabel: String = "Check-In",
    val locationIntervalSeconds: Int = 15 * 60,
    val locationSharingEnabled: Boolean = false,
    val automaticCheckInOutEnabled: Boolean = false,
    val legacyMigrationStatus: String = "Nao verificada",
    val legacyMigrationMessage: String =
        "A verificacao da migracao legada ainda nao foi executada.",
    val legacySourceInstalled: Boolean = false,
    val nextSteps: List<String> = listOf(
        "Implementar localizacao e background Android em Kotlin.",
        "Ligar a automacao nativa ao cliente de API e ao dominio puro.",
        "Substituir a UI de bootstrap pela tela funcional em Compose.",
    ),
)
