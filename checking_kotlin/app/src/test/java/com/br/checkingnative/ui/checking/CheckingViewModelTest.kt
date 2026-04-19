package com.br.checkingnative.ui.checking

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import com.br.checkingnative.data.background.CheckingBackgroundSnapshotRepository
import com.br.checkingnative.data.local.db.ManagedLocationDao
import com.br.checkingnative.data.local.db.ManagedLocationEntity
import com.br.checkingnative.data.local.repository.ManagedLocationCacheRepository
import com.br.checkingnative.data.local.repository.ManagedLocationRepository
import com.br.checkingnative.data.migration.LegacyFlutterMigrationReport
import com.br.checkingnative.data.preferences.CheckingStateStorageSnapshot
import com.br.checkingnative.data.preferences.CheckingStateStore
import com.br.checkingnative.data.remote.CheckingApiService
import com.br.checkingnative.data.remote.CheckingHttpRequest
import com.br.checkingnative.data.remote.CheckingHttpResponse
import com.br.checkingnative.data.remote.CheckingHttpTransport
import com.br.checkingnative.domain.model.CheckingPermissionSnapshot
import com.br.checkingnative.domain.model.CheckingState
import com.br.checkingnative.domain.model.StatusTone
import com.google.gson.JsonParser
import java.io.File
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import org.junit.rules.TestWatcher
import org.junit.runner.Description

@OptIn(ExperimentalCoroutinesApi::class)
class CheckingViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    @get:Rule
    val temporaryFolder: TemporaryFolder = TemporaryFolder()

    @Test
    fun init_initializesControllerState() = runTest {
        val fixture = createFixture("viewmodel_init.preferences_pb")

        advanceUntilIdle()

        assertTrue(fixture.viewModel.uiState.value.initialized)
        assertFalse(fixture.viewModel.uiState.value.state.isLoading)
    }

    @Test
    fun updateChave_normalizesAndSyncsWhenKeyBecomesValid() = runTest {
        val fixture = createFixture("viewmodel_key.preferences_pb")
        advanceUntilIdle()
        fixture.transport.enqueueResponse(
            statusCode = 200,
            body = """
                {
                  "found": false,
                  "chave": "HR70"
                }
            """.trimIndent(),
        )

        fixture.viewModel.updateChave("h r-70x")
        advanceUntilIdle()

        assertEquals("HR70", fixture.viewModel.uiState.value.state.chave)
        assertEquals(
            "https://tscode.com.br/api/mobile/state?chave=HR70",
            fixture.transport.requests.single().url,
        )
    }

    @Test
    fun submitCurrent_emitsSuccessMessageFromApi() = runTest {
        val fixture = createFixture("viewmodel_submit.preferences_pb")
        advanceUntilIdle()
        fixture.transport.enqueueResponse(
            statusCode = 200,
            body = """
                {
                  "found": false,
                  "chave": "AB12"
                }
            """.trimIndent(),
        )
        fixture.viewModel.updateChave("ab12")
        advanceUntilIdle()
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
                    "projeto": "P80",
                    "current_action": "checkin",
                    "last_checkin_at": "2026-04-19T08:00:00Z"
                  }
                }
            """.trimIndent(),
        )
        val messages = mutableListOf<String>()
        val collector = launch {
            fixture.viewModel.messages.take(1).toList(messages)
        }

        fixture.viewModel.submitCurrent()
        advanceUntilIdle()

        assertEquals(listOf("Registro enviado."), messages)
        val submitPayload = JsonParser.parseString(
            fixture.transport.requests.last().body,
        ).asJsonObject
        assertEquals("AB12", submitPayload["chave"].asString)
        assertEquals("normal", submitPayload["informe"].asString)
        collector.cancel()
    }

    @Test
    fun refreshPermissionState_turnsOffLocationSharingWhenPermissionIsRevoked() = runTest {
        val fixture = createFixture(
            fileName = "viewmodel_permissions.preferences_pb",
            initialState = CheckingState.initial().copy(
                canEnableLocationSharing = true,
                locationSharingEnabled = true,
                oemBackgroundSetupEnabled = true,
                isLoading = false,
            ),
        )
        advanceUntilIdle()

        fixture.viewModel.refreshPermissionState(
            snapshot = CheckingPermissionSnapshot(
                locationServiceEnabled = true,
                preciseLocationGranted = true,
                backgroundAccessEnabled = false,
                notificationsEnabled = true,
                batteryOptimizationIgnored = true,
            ),
            updateStatus = true,
        )
        advanceUntilIdle()

        val state = fixture.viewModel.uiState.value.state
        assertFalse(state.canEnableLocationSharing)
        assertFalse(state.locationSharingEnabled)
        assertFalse(state.oemBackgroundSetupEnabled)
        assertEquals(StatusTone.ERROR, state.statusTone)
    }

    private fun createFixture(
        fileName: String,
        initialState: CheckingState = CheckingState.initial().copy(isLoading = false),
    ): ViewModelFixture {
        val stateStore = ViewModelFakeCheckingStateStore(initialState)
        val cacheRepository = ManagedLocationCacheRepository(createDataStore("cache_$fileName"))
        val locationRepository = ManagedLocationRepository(
            dao = ViewModelFakeManagedLocationDao(),
            cacheRepository = cacheRepository,
        )
        val transport = ViewModelFakeCheckingHttpTransport()
        val controller = CheckingController(
            checkingStateStore = stateStore,
            apiService = CheckingApiService(transport),
            locationRepository = locationRepository,
            backgroundSnapshotRepository = CheckingBackgroundSnapshotRepository(),
        )
        return ViewModelFixture(
            viewModel = CheckingViewModel(controller),
            stateStore = stateStore,
            transport = transport,
        )
    }

    private fun createDataStore(fileName: String): DataStore<Preferences> {
        val file = File(temporaryFolder.root, fileName)
        return PreferenceDataStoreFactory.create(
            scope = kotlinx.coroutines.CoroutineScope(
                kotlinx.coroutines.SupervisorJob() + Dispatchers.IO,
            ),
            produceFile = { file },
        )
    }
}

private data class ViewModelFixture(
    val viewModel: CheckingViewModel,
    val stateStore: ViewModelFakeCheckingStateStore,
    val transport: ViewModelFakeCheckingHttpTransport,
)

@OptIn(ExperimentalCoroutinesApi::class)
private class MainDispatcherRule(
    private val dispatcher: TestDispatcher = StandardTestDispatcher(),
) : TestWatcher() {
    override fun starting(description: Description) {
        Dispatchers.setMain(dispatcher)
    }

    override fun finished(description: Description) {
        Dispatchers.resetMain()
    }
}

private class ViewModelFakeCheckingStateStore(
    initialState: CheckingState,
) : CheckingStateStore {
    private val snapshot = MutableStateFlow(
        CheckingStateStorageSnapshot(
            state = initialState,
            hasPersistedState = true,
        ),
    )

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

private class ViewModelFakeManagedLocationDao : ManagedLocationDao {
    private val storedItems = MutableStateFlow<List<ManagedLocationEntity>>(emptyList())

    override fun observeLocationCount(): Flow<Int> {
        return storedItems.map { items -> items.size }
    }

    override fun observeAll(): Flow<List<ManagedLocationEntity>> = storedItems

    override suspend fun loadAllSnapshot(): List<ManagedLocationEntity> = storedItems.value

    override suspend fun upsertAll(items: List<ManagedLocationEntity>) {
        storedItems.value = items
    }

    override suspend fun clearAll() {
        storedItems.value = emptyList()
    }

    override suspend fun replaceAll(items: List<ManagedLocationEntity>) {
        storedItems.value = items
    }
}

private class ViewModelFakeCheckingHttpTransport : CheckingHttpTransport {
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
    ) {
        queuedResults.addLast(Result.success(CheckingHttpResponse(statusCode, body)))
    }
}
