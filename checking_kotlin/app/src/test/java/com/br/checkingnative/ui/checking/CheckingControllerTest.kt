package com.br.checkingnative.ui.checking

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import com.br.checkingnative.data.background.CheckingBackgroundSnapshotRepository
import com.br.checkingnative.data.local.db.ManagedLocationDao
import com.br.checkingnative.data.local.db.ManagedLocationEntity
import com.br.checkingnative.data.local.db.toEntity
import com.br.checkingnative.data.local.repository.ManagedLocationCacheRepository
import com.br.checkingnative.data.local.repository.ManagedLocationRepository
import com.br.checkingnative.data.migration.LegacyFlutterMigrationReport
import com.br.checkingnative.data.preferences.CheckingStateStorageSnapshot
import com.br.checkingnative.data.preferences.CheckingStateStore
import com.br.checkingnative.data.preferences.WebSessionSnapshot
import com.br.checkingnative.data.preferences.WebSessionStore
import com.br.checkingnative.data.remote.WebCheckApiService
import com.br.checkingnative.data.remote.CheckingHttpRequest
import com.br.checkingnative.data.remote.CheckingHttpResponse
import com.br.checkingnative.data.remote.CheckingHttpTransport
import com.br.checkingnative.domain.model.CheckingLocationSample
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.CheckingOemBackgroundSetupResult
import com.br.checkingnative.domain.model.CheckingPermissionSnapshot
import com.br.checkingnative.domain.model.InformeType
import com.br.checkingnative.domain.model.ManagedLocation
import com.br.checkingnative.domain.model.ManagedLocationCoordinate
import com.br.checkingnative.domain.model.ProjetoType
import com.br.checkingnative.domain.model.RegistroType
import com.br.checkingnative.domain.model.StatusTone
import com.google.gson.JsonParser
import java.io.File
import java.io.IOException
import java.time.Instant
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class CheckingControllerTest {
    @get:Rule
    val temporaryFolder: TemporaryFolder = TemporaryFolder()

    @Test
    fun initialize_loadsPersistedStateAndLocations() = runBlocking {
        val fixture = createFixture("controller_init.preferences_pb")
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                chave = "AB12",
                isLoading = false,
            ),
        )
        fixture.dao.replaceAll(listOf(buildControllerLocation(id = 1).toEntity()))

        fixture.controller.initialize()

        val uiState = fixture.controller.uiState.value
        assertTrue(uiState.initialized)
        assertFalse(uiState.state.isLoading)
        assertEquals("AB12", uiState.state.chave)
        assertEquals(1, uiState.managedLocationCount)
        assertEquals("Base 1", uiState.managedLocations.single().local)
    }

    @Test
    fun markInitialAndroidSetupPrompted_updatesUiAndStorageFlag() = runBlocking {
        val fixture = createFixture("controller_initial_setup.preferences_pb")
        fixture.controller.initialize()

        assertFalse(fixture.controller.uiState.value.hasPromptedInitialAndroidSetup)

        fixture.controller.markInitialAndroidSetupPrompted()

        assertTrue(fixture.controller.uiState.value.hasPromptedInitialAndroidSetup)
        assertTrue(
            fixture.stateStore.storageSnapshot.first().hasPromptedInitialAndroidSetup,
        )
    }

    @Test
    fun updateChave_normalizesValueAndClearsCurrentHistory() = runBlocking {
        val fixture = createFixture("controller_key.preferences_pb")
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                chave = "ZZ99",
                lastCheckIn = Instant.parse("2026-04-18T08:00:00Z"),
                lastCheckOut = Instant.parse("2026-04-18T17:00:00Z"),
                lastCheckInLocation = "Base Sul",
                lastMatchedLocation = "Base Sul",
                lastDetectedLocation = "Base Sul",
                lastLocationUpdateAt = Instant.parse("2026-04-18T17:01:00Z"),
                isLoading = false,
            ),
        )
        fixture.controller.initialize()

        fixture.controller.updateChave(
            value = "a b-12x",
            syncAfterValidChange = false,
        )

        val state = fixture.controller.uiState.value.state
        assertEquals("AB12", state.chave)
        assertNull(state.lastCheckIn)
        assertNull(state.lastCheckOut)
        assertNull(state.lastCheckInLocation)
        assertNull(state.lastMatchedLocation)
        assertNull(state.lastDetectedLocation)
        assertNull(state.lastLocationUpdateAt)
        assertFalse(fixture.controller.uiState.value.hasHydratedHistoryForCurrentKey)
    }

    @Test
    fun loginWebPassword_persistsWebSessionAndHydratesHistoryForBackground() = runBlocking {
        val fixture = createFixture("controller_web_login.preferences_pb")
        fixture.transport.enqueueResponse(
            statusCode = 200,
            body = """
                {
                  "ok": true,
                  "authenticated": true,
                  "has_password": true,
                  "message": "Autenticacao concluida."
                }
            """.trimIndent(),
            headers = mapOf("Set-Cookie" to listOf("session=login-cookie; path=/; httponly")),
        )
        fixture.transport.enqueueResponse(
            statusCode = 200,
            body = """
                {
                  "found": true,
                  "chave": "AB12",
                  "projeto": "P80",
                  "current_action": "checkout",
                  "current_local": "Fora do Local de Trabalho",
                  "has_current_day_checkin": true,
                  "last_checkout_at": "2026-04-18T18:00:00Z"
                }
            """.trimIndent(),
        )
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                chave = "AB12",
                isLoading = false,
            ),
        )
        fixture.controller.initialize()

        val message = fixture.controller.loginWebPassword("1234")

        assertEquals("Autenticacao concluida.", message)
        assertEquals("session=login-cookie", fixture.webSessionStore.webSessionSnapshot.value.cookieHeader)
        assertEquals("https://tscode.com.br/api/web/auth/login", fixture.transport.requests[0].url)
        assertEquals("https://tscode.com.br/api/web/check/state?chave=AB12", fixture.transport.requests[1].url)
        assertEquals("session=login-cookie", fixture.transport.requests[1].headers["Cookie"])
        assertTrue(fixture.controller.uiState.value.webAuth.authenticated)
        assertTrue(fixture.controller.uiState.value.webAuth.hasStoredSession)
        assertEquals(Instant.parse("2026-04-18T18:00:00Z"), fixture.controller.uiState.value.state.lastCheckOut)
    }

    @Test
    fun logoutWebSession_clearsCookieAndStopsBackgroundAutomation() = runBlocking {
        val fixture = createFixture("controller_web_logout.preferences_pb")
        fixture.webSessionStore.saveWebSessionCookieHeader("session=old")
        fixture.transport.enqueueResponse(
            statusCode = 200,
            body = """
                {
                  "ok": true,
                  "authenticated": false,
                  "has_password": true,
                  "message": "Sessao encerrada."
                }
            """.trimIndent(),
            headers = mapOf(
                "Set-Cookie" to listOf(
                    "session=null; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0",
                ),
            ),
        )
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                chave = "AB12",
                canEnableLocationSharing = true,
                locationSharingEnabled = true,
                autoCheckInEnabled = true,
                autoCheckOutEnabled = true,
                isLoading = false,
            ),
        )
        fixture.controller.initialize()

        fixture.controller.logoutWebSession()

        val state = fixture.controller.uiState.value.state
        assertEquals("", fixture.webSessionStore.webSessionSnapshot.value.cookieHeader)
        assertFalse(fixture.controller.uiState.value.webAuth.authenticated)
        assertFalse(state.locationSharingEnabled)
        assertFalse(state.autoCheckInEnabled)
        assertFalse(state.autoCheckOutEnabled)
    }

    @Test
    fun syncHistory_appliesRemoteStateAndSuggestedNextAction() = runBlocking {
        val fixture = createFixture("controller_history.preferences_pb")
        fixture.transport.enqueueResponse(
            statusCode = 200,
            body = """
                {
                  "found": true,
                  "chave": "AB12",
                  "nome": "Usuario Teste",
                  "projeto": "P82",
                  "current_action": "checkin",
                  "current_local": "Base Sul",
                  "last_checkin_at": "2026-04-18T08:00:00Z"
                }
            """.trimIndent(),
        )
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                chave = "AB12",
                checkInProjeto = ProjetoType.P80,
                isLoading = false,
            ),
        )
        fixture.controller.initialize()

        val message = fixture.controller.syncHistory()

        val state = fixture.controller.uiState.value.state
        assertEquals("Histórico sincronizado com a API.", message)
        assertEquals("Histórico sincronizado com a API.", state.statusMessage)
        assertEquals(StatusTone.SUCCESS, state.statusTone)
        assertEquals(Instant.parse("2026-04-18T08:00:00Z"), state.lastCheckIn)
        assertNull(state.lastCheckOut)
        assertEquals("Base Sul", state.lastCheckInLocation)
        assertEquals(RegistroType.CHECK_OUT, state.registro)
        assertEquals(ProjetoType.P82, state.checkInProjeto)
        assertFalse(state.isSyncing)
        assertTrue(fixture.controller.uiState.value.hasHydratedHistoryForCurrentKey)
    }

    @Test
    fun submitCurrent_sendsManualPayloadAndAppliesRemoteState() = runBlocking {
        val fixture = createFixture("controller_submit.preferences_pb")
        fixture.transport.enqueueResponse(
            statusCode = 200,
            body = """
                {
                  "found": true,
                  "chave": "AB12",
                  "has_password": true,
                  "authenticated": true,
                  "message": "Aplicacao liberada."
                }
            """.trimIndent(),
            headers = mapOf("Set-Cookie" to listOf("session=submit; path=/; httponly")),
        )
        fixture.transport.enqueueResponse(
            statusCode = 200,
            body = """
                {
                  "ok": true,
                  "duplicate": false,
                  "queued_forms": true,
                  "message": "Registro enviado.",
                  "state": {
                    "found": true,
                    "chave": "AB12",
                    "projeto": "P83",
                    "current_action": "checkin",
                    "current_local": "Base Norte",
                    "last_checkin_at": "2026-04-18T09:30:00Z"
                  }
                }
            """.trimIndent(),
        )
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                chave = "AB12",
                registro = RegistroType.CHECK_IN,
                checkInInforme = InformeType.RETROATIVO,
                checkInProjeto = ProjetoType.P83,
                isLoading = false,
            ),
        )
        fixture.controller.initialize()
        fixture.controller.refreshWebAuthStatus(updateStatus = false, silent = true)

        val message = fixture.controller.submitCurrent()

        val request = fixture.transport.requests.last()
        val payload = JsonParser.parseString(request.body).asJsonObject
        assertEquals("POST", request.method)
        assertEquals("https://tscode.com.br/api/web/check", request.url)
        assertEquals("AB12", payload["chave"].asString)
        assertEquals("P83", payload["projeto"].asString)
        assertEquals("checkin", payload["action"].asString)
        assertEquals("retroativo", payload["informe"].asString)
        assertTrue(payload["client_event_id"].asString.startsWith("web-check-android-"))
        assertEquals("Registro enviado.", message)

        val state = fixture.controller.uiState.value.state
        assertEquals("Registro enviado.", state.statusMessage)
        assertEquals(StatusTone.SUCCESS, state.statusTone)
        assertEquals(Instant.parse("2026-04-18T09:30:00Z"), state.lastCheckIn)
        assertNull(state.lastCheckInLocation)
        assertEquals(RegistroType.CHECK_OUT, state.registro)
        assertFalse(state.isSubmitting)
    }

    @Test
    fun resolveInformeForSubmission_manualUsesSelectedAndAutomationUsesNormal() {
        val state = CheckingState.initial().copy(
            registro = RegistroType.CHECK_IN,
            checkInInforme = InformeType.RETROATIVO,
        )

        assertEquals(
            InformeType.RETROATIVO,
            CheckingController.resolveInformeForSubmission(
                state = state,
                action = RegistroType.CHECK_IN,
                source = CheckingController.SOURCE_MANUAL,
            ),
        )
        assertEquals(
            InformeType.NORMAL,
            CheckingController.resolveInformeForSubmission(
                state = state,
                action = RegistroType.CHECK_IN,
                source = CheckingController.SOURCE_LOCATION_AUTOMATION,
            ),
        )
    }

    @Test
    fun refreshLocationsCatalog_usesWebEndpointAndKeepsSessionAuthenticated() = runBlocking {
        val fixture = createFixture("controller_catalog.preferences_pb")
        fixture.transport.enqueueResponse(
            statusCode = 200,
            body = """
                {
                  "items": ["Base Catalogo", "Zona de CheckOut"]
                }
            """.trimIndent(),
        )
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                chave = "AB12",
                isLoading = false,
            ),
        )
        fixture.controller.initialize()

        val count = fixture.controller.refreshLocationsCatalog()

        assertEquals(2, count)
        assertEquals(
            "https://tscode.com.br/api/web/check/locations",
            fixture.transport.requests.single().url,
        )
        assertEquals("2 localizações disponíveis na API web.", fixture.controller.uiState.value.state.statusMessage)
        assertTrue(fixture.controller.uiState.value.webAuth.authenticated)
    }

    @Test
    fun processForegroundLocationUpdate_updatesDetectedMatchAndHistory() = runBlocking {
        val fixture = createFixture("controller_foreground_location.preferences_pb")
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                locationSharingEnabled = true,
                locationAccuracyThresholdMeters = 30,
                isLoading = false,
            ),
        )
        fixture.dao.replaceAll(listOf(buildControllerLocation(id = 1).toEntity()))
        fixture.controller.initialize()

        val processed = fixture.controller.processForegroundLocationUpdate(
            CheckingLocationSample(
                timestamp = Instant.parse("2026-04-19T10:00:00Z"),
                latitude = -23.0,
                longitude = -44.0,
                accuracyMeters = 12.0,
            ),
        )

        val state = fixture.controller.uiState.value.state
        assertTrue(processed)
        assertEquals("Base 1", state.lastDetectedLocation)
        assertEquals("Base 1", state.lastMatchedLocation)
        assertEquals(Instant.parse("2026-04-19T10:00:00Z"), state.lastLocationUpdateAt)
        assertEquals(1, state.locationFetchHistory.size)
    }

    @Test
    fun processForegroundLocationUpdate_rejectsPoorAccuracyAndDuplicates() = runBlocking {
        val fixture = createFixture("controller_location_filters.preferences_pb")
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                locationSharingEnabled = true,
                locationAccuracyThresholdMeters = 30,
                isLoading = false,
            ),
        )
        fixture.dao.replaceAll(listOf(buildControllerLocation(id = 1).toEntity()))
        fixture.controller.initialize()

        val poorAccuracyProcessed = fixture.controller.processForegroundLocationUpdate(
            CheckingLocationSample(
                timestamp = Instant.parse("2026-04-19T10:00:00Z"),
                latitude = -23.0,
                longitude = -44.0,
                accuracyMeters = 80.0,
            ),
        )
        val firstProcessed = fixture.controller.processForegroundLocationUpdate(
            CheckingLocationSample(
                timestamp = Instant.parse("2026-04-19T10:00:01Z"),
                latitude = -23.0,
                longitude = -44.0,
                accuracyMeters = 12.0,
            ),
        )
        val duplicateProcessed = fixture.controller.processForegroundLocationUpdate(
            CheckingLocationSample(
                timestamp = Instant.parse("2026-04-19T10:00:01.500Z"),
                latitude = -23.0,
                longitude = -44.0,
                accuracyMeters = 12.0,
            ),
        )

        assertFalse(poorAccuracyProcessed)
        assertTrue(firstProcessed)
        assertFalse(duplicateProcessed)
        assertEquals(1, fixture.controller.uiState.value.state.locationFetchHistory.size)
    }

    @Test
    fun refreshPermissionState_turnsOffPermissionBackedSwitchesWhenRevoked() = runBlocking {
        val fixture = createFixture("controller_permissions.preferences_pb")
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                canEnableLocationSharing = true,
                locationSharingEnabled = true,
                oemBackgroundSetupEnabled = true,
                lastMatchedLocation = "Base Sul",
                isLoading = false,
            ),
        )
        fixture.controller.initialize()

        fixture.controller.refreshPermissionState(
            snapshot = permissionSnapshot(backgroundAccessEnabled = false),
            updateStatus = true,
        )

        val uiState = fixture.controller.uiState.value
        assertFalse(uiState.state.canEnableLocationSharing)
        assertFalse(uiState.state.locationSharingEnabled)
        assertFalse(uiState.state.oemBackgroundSetupEnabled)
        assertNull(uiState.state.lastMatchedLocation)
        assertFalse(uiState.permissionSettings.backgroundAccessEnabled)
        assertEquals(
            "Permita o acesso à localização em segundo plano para concluir a ativação.",
            uiState.state.statusMessage,
        )
        assertEquals(StatusTone.ERROR, uiState.state.statusTone)
    }

    @Test
    fun setOemBackgroundSetupEnabled_persistsFlagAndShowsVendorWarning() = runBlocking {
        val fixture = createFixture("controller_oem.preferences_pb")
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                canEnableLocationSharing = true,
                isLoading = false,
            ),
        )
        fixture.controller.initialize()

        fixture.controller.setOemBackgroundSetupEnabled(
            value = true,
            setupResult = CheckingOemBackgroundSetupResult(
                openedSettings = false,
                message = "Em Samsung, revise Apps em suspensão.",
            ),
        )

        val state = fixture.controller.uiState.value.state
        assertTrue(state.oemBackgroundSetupEnabled)
        assertEquals("Em Samsung, revise Apps em suspensão.", state.statusMessage)
        assertEquals(StatusTone.WARNING, state.statusTone)
    }

    @Test
    fun backgroundSnapshot_updatesUiAndKeepsPermissionDerivedFlags() = runBlocking {
        val fixture = createFixture("controller_background_snapshot.preferences_pb")
        fixture.stateStore.saveState(
            CheckingState.initial().copy(
                canEnableLocationSharing = true,
                locationSharingEnabled = true,
                isLoading = false,
            ),
        )
        fixture.controller.initialize()

        fixture.backgroundSnapshotRepository.publish(
            CheckingState.initial().copy(
                chave = "AB12",
                locationSharingEnabled = true,
                canEnableLocationSharing = false,
                lastCheckIn = Instant.parse("2026-04-19T08:00:00Z"),
                statusMessage = "Check-In automático enviado para Base 1.",
                statusTone = StatusTone.SUCCESS,
                isLocationUpdating = true,
            ),
        )

        withTimeout(1_000L) {
            while (fixture.controller.uiState.value.state.lastCheckIn == null) {
                delay(10L)
            }
        }

        val state = fixture.controller.uiState.value.state
        assertEquals("AB12", state.chave)
        assertEquals(Instant.parse("2026-04-19T08:00:00Z"), state.lastCheckIn)
        assertEquals("Check-In automático enviado para Base 1.", state.statusMessage)
        assertTrue(state.canEnableLocationSharing)
        assertFalse(state.isLocationUpdating)
    }

    private fun createFixture(fileName: String): ControllerFixture {
        val cacheDataStore = createDataStore("cache_$fileName")
        val stateStore = FakeCheckingStateStore()
        val cacheRepository = ManagedLocationCacheRepository(cacheDataStore)
        val dao = FakeManagedLocationDao()
        val locationRepository = ManagedLocationRepository(dao, cacheRepository)
        val transport = FakeCheckingHttpTransport()
        val webSessionStore = FakeWebSessionStore()
        val webApiService = WebCheckApiService(transport, webSessionStore)
        val backgroundSnapshotRepository = CheckingBackgroundSnapshotRepository()
        val controller = CheckingController(
            checkingStateStore = stateStore,
            webApiService = webApiService,
            webSessionStore = webSessionStore,
            locationRepository = locationRepository,
            backgroundSnapshotRepository = backgroundSnapshotRepository,
        )
        return ControllerFixture(
            controller = controller,
            stateStore = stateStore,
            locationRepository = locationRepository,
            dao = dao,
            transport = transport,
            webSessionStore = webSessionStore,
            backgroundSnapshotRepository = backgroundSnapshotRepository,
        )
    }

    private fun createDataStore(fileName: String): DataStore<Preferences> {
        val file = File(temporaryFolder.root, fileName)
        return PreferenceDataStoreFactory.create(
            scope = CoroutineScope(SupervisorJob() + Dispatchers.IO),
            produceFile = { file },
        )
    }
}

private data class ControllerFixture(
    val controller: CheckingController,
    val stateStore: FakeCheckingStateStore,
    val locationRepository: ManagedLocationRepository,
    val dao: FakeManagedLocationDao,
    val transport: FakeCheckingHttpTransport,
    val webSessionStore: FakeWebSessionStore,
    val backgroundSnapshotRepository: CheckingBackgroundSnapshotRepository,
)

private class FakeCheckingStateStore : CheckingStateStore {
    private val snapshot = MutableStateFlow(CheckingStateStorageSnapshot())

    override val storageSnapshot: Flow<CheckingStateStorageSnapshot> = snapshot

    override suspend fun ensureSeededState() {
        if (!snapshot.value.hasPersistedState) {
            saveState(CheckingState.initial().copy(isLoading = false))
        }
    }

    override suspend fun saveState(state: CheckingState) {
        snapshot.value = snapshot.value.copy(
            state = state,
            hasPersistedState = true,
        )
    }

    override suspend fun markInitialAndroidSetupPrompted() {
        snapshot.value = snapshot.value.copy(hasPromptedInitialAndroidSetup = true)
    }

    override suspend fun updateLegacyMigrationReport(report: LegacyFlutterMigrationReport) {
        snapshot.value = snapshot.value.copy(
            legacyMigrationStatus = report.status,
            legacyMigrationMessage = report.message,
            legacySourceInstalled = report.sourceAppInstalled,
        )
    }
}

private class FakeManagedLocationDao : ManagedLocationDao {
    private val storedItems = MutableStateFlow<List<ManagedLocationEntity>>(emptyList())

    override fun observeLocationCount(): Flow<Int> {
        return storedItems.map { items -> items.size }
    }

    override fun observeAll(): Flow<List<ManagedLocationEntity>> = storedItems

    override suspend fun loadAllSnapshot(): List<ManagedLocationEntity> {
        return sortEntities(storedItems.value)
    }

    override suspend fun upsertAll(items: List<ManagedLocationEntity>) {
        val byId = storedItems.value.associateBy { item -> item.id }.toMutableMap()
        items.forEach { item -> byId[item.id] = item }
        storedItems.value = sortEntities(byId.values.toList())
    }

    override suspend fun clearAll() {
        storedItems.value = emptyList()
    }

    override suspend fun replaceAll(items: List<ManagedLocationEntity>) {
        storedItems.value = sortEntities(items)
    }

    private fun sortEntities(items: List<ManagedLocationEntity>): List<ManagedLocationEntity> {
        return items.sortedWith(
            compareBy<ManagedLocationEntity> { item -> item.local.lowercase() }
                .thenBy { item -> item.id },
        )
    }
}

private class FakeCheckingHttpTransport : CheckingHttpTransport {
    val requests = mutableListOf<CheckingHttpRequest>()
    private val queuedResults = ArrayDeque<Result<CheckingHttpResponse>>()

    override suspend fun execute(request: CheckingHttpRequest): CheckingHttpResponse {
        requests += request
        val nextResult = queuedResults.removeFirstOrNull()
            ?: throw IOException("No queued HTTP response for ${request.url}")
        return nextResult.getOrThrow()
    }

    fun enqueueResponse(
        statusCode: Int,
        body: String,
        headers: Map<String, List<String>> = emptyMap(),
    ) {
        queuedResults.addLast(Result.success(CheckingHttpResponse(statusCode, body, headers)))
    }
}

private class FakeWebSessionStore(
    initialCookieHeader: String = "",
) : WebSessionStore {
    private val snapshot = MutableStateFlow(WebSessionSnapshot(initialCookieHeader))

    override val webSessionSnapshot: MutableStateFlow<WebSessionSnapshot> = snapshot

    override suspend fun saveWebSessionCookieHeader(cookieHeader: String) {
        snapshot.value = WebSessionSnapshot(cookieHeader.trim())
    }

    override suspend fun clearWebSessionCookie() {
        snapshot.value = WebSessionSnapshot()
    }
}

private fun buildControllerLocation(id: Int): ManagedLocation {
    return ManagedLocation(
        id = id,
        local = "Base $id",
        latitude = -22.0 - id,
        longitude = -43.0 - id,
        coordinates = listOf(
            ManagedLocationCoordinate(
                latitude = -22.0 - id,
                longitude = -43.0 - id,
            ),
        ),
        toleranceMeters = 30 + id,
        updatedAt = Instant.parse("2026-04-18T00:00:00Z"),
    )
}

private fun permissionSnapshot(
    locationServiceEnabled: Boolean = true,
    preciseLocationGranted: Boolean = true,
    backgroundAccessEnabled: Boolean = true,
    notificationsEnabled: Boolean = true,
    batteryOptimizationIgnored: Boolean = true,
): CheckingPermissionSnapshot {
    return CheckingPermissionSnapshot(
        locationServiceEnabled = locationServiceEnabled,
        preciseLocationGranted = preciseLocationGranted,
        backgroundAccessEnabled = backgroundAccessEnabled,
        notificationsEnabled = notificationsEnabled,
        batteryOptimizationIgnored = batteryOptimizationIgnored,
    )
}
