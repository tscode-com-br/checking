package com.br.checkingnative.data.preferences

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.br.checkingnative.core.config.CheckingPresetConfig
import com.br.checkingnative.data.migration.LegacyFlutterMigrationReport
import com.br.checkingnative.data.migration.LegacyFlutterMigrationStatus
import com.br.checkingnative.domain.model.CheckingState
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

@Singleton
class CheckingStateRepository @Inject constructor(
    private val dataStore: DataStore<Preferences>,
) : CheckingStateStore, WebSessionStore {
    private object Keys {
        val stateJson = stringPreferencesKey("checking_state_json")
        val apiSharedKey = stringPreferencesKey("checking_api_shared_key")
        val webSessionCookieHeader = stringPreferencesKey("checking_web_session_cookie_header")
        val initialAndroidSetupPrompted =
            booleanPreferencesKey("checking_initial_android_setup_prompted")
        val legacyMigrationStatus =
            stringPreferencesKey("checking_legacy_migration_status")
        val legacyMigrationMessage =
            stringPreferencesKey("checking_legacy_migration_message")
        val legacySourceInstalled =
            booleanPreferencesKey("checking_legacy_source_installed")
    }

    override val storageSnapshot: Flow<CheckingStateStorageSnapshot> =
        dataStore.data.map { preferences ->
            val resolvedSharedKey = preferences.resolvedSharedKey()
            val persistedState = preferences[Keys.stateJson]
            CheckingStateStorageSnapshot(
                state = CheckingState.fromPersistedJsonString(
                    raw = persistedState,
                    resolvedSharedKey = resolvedSharedKey,
                ),
                hasPersistedState = !persistedState.isNullOrBlank(),
                hasPromptedInitialAndroidSetup =
                    preferences[Keys.initialAndroidSetupPrompted] ?: false,
                legacyMigrationStatus = LegacyFlutterMigrationStatus.fromStorageValue(
                    preferences[Keys.legacyMigrationStatus],
                ),
                legacyMigrationMessage = preferences[Keys.legacyMigrationMessage]
                    ?: "A verificacao da migracao legada ainda nao foi executada.",
                legacySourceInstalled = preferences[Keys.legacySourceInstalled] ?: false,
            )
        }

    override val webSessionSnapshot: Flow<WebSessionSnapshot> =
        dataStore.data.map { preferences ->
            WebSessionSnapshot(
                cookieHeader = preferences[Keys.webSessionCookieHeader].orEmpty(),
            )
        }

    override suspend fun ensureSeededState() {
        dataStore.edit { preferences ->
            if (!preferences[Keys.stateJson].isNullOrBlank()) {
                return@edit
            }

            val resolvedSharedKey = preferences.resolvedSharedKey()
            val seededState = CheckingState.initial().copy(
                apiSharedKey = resolvedSharedKey,
                isLoading = false,
            )
            preferences[Keys.stateJson] = seededState.toPersistedJsonString()
            if (resolvedSharedKey.isNotBlank()) {
                preferences[Keys.apiSharedKey] = resolvedSharedKey
            }
        }
    }

    override suspend fun saveState(state: CheckingState) {
        dataStore.edit { preferences ->
            preferences[Keys.stateJson] = state.toPersistedJsonString()

            val secureValue = state.apiSharedKey.trim()
            if (secureValue.isBlank()) {
                preferences.remove(Keys.apiSharedKey)
            } else {
                preferences[Keys.apiSharedKey] = secureValue
            }
        }
    }

    override suspend fun markInitialAndroidSetupPrompted() {
        dataStore.edit { preferences ->
            preferences[Keys.initialAndroidSetupPrompted] = true
        }
    }

    override suspend fun saveWebSessionCookieHeader(cookieHeader: String) {
        dataStore.edit { preferences ->
            val normalized = cookieHeader.trim()
            if (normalized.isBlank()) {
                preferences.remove(Keys.webSessionCookieHeader)
            } else {
                preferences[Keys.webSessionCookieHeader] = normalized
            }
        }
    }

    override suspend fun clearWebSessionCookie() {
        dataStore.edit { preferences ->
            preferences.remove(Keys.webSessionCookieHeader)
        }
    }

    override suspend fun updateLegacyMigrationReport(report: LegacyFlutterMigrationReport) {
        dataStore.edit { preferences ->
            preferences[Keys.legacyMigrationStatus] = report.status.storageValue
            preferences[Keys.legacyMigrationMessage] = report.message
            preferences[Keys.legacySourceInstalled] = report.sourceAppInstalled
        }
    }

    private fun Preferences.resolvedSharedKey(): String {
        return this[Keys.apiSharedKey]
            ?.trim()
            ?.takeIf { value -> value.isNotEmpty() }
            ?: CheckingPresetConfig.apiSharedKey
    }
}
