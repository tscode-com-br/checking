package com.br.checkingnative.data.migration

enum class LegacyFlutterMigrationStatus(
    val storageValue: String,
    val label: String,
) {
    NOT_STARTED(
        storageValue = "not_started",
        label = "Nao verificada",
    ),
    SOURCE_APP_NOT_INSTALLED(
        storageValue = "source_app_not_installed",
        label = "App Flutter nao detectado",
    ),
    AUTOMATIC_IMPORT_BLOCKED(
        storageValue = "automatic_import_blocked",
        label = "Migracao automatica bloqueada",
    ),
    COMPLETED(
        storageValue = "completed",
        label = "Migracao concluida",
    ),
    ;

    companion object {
        fun fromStorageValue(value: String?): LegacyFlutterMigrationStatus {
            return entries.firstOrNull { status -> status.storageValue == value } ?: NOT_STARTED
        }
    }
}

data class LegacyFlutterMigrationReport(
    val status: LegacyFlutterMigrationStatus,
    val message: String,
    val sourceAppInstalled: Boolean,
)
