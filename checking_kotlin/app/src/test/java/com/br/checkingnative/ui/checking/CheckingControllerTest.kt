package com.br.checkingnative.ui.checking

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import com.br.checkingnative.data.local.db.ManagedLocationDao
import com.br.checkingnative.data.local.db.ManagedLocationEntity
import com.br.checkingnative.data.local.db.toEntity
import com.br.checkingnative.data.local.repository.ManagedLocationCacheRepository
import com.br.checkingnative.data.local.repository.ManagedLocationRepository
import com.br.checkingnative.data.preferences.CheckingStateRepository
import com.br.checkingnative.data.remote.CheckingApiService
import com.br.checkingnative.data.remote.CheckingHttpRequest
import com.br.checkingnative.data.remote.CheckingHttpResponse
import com.br.checkingnative.data.remote.CheckingHttpTransport
import com.br.checkingnative.domain.model.CheckingState
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
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
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
        fixture.stateRepository.saveState(
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
    fun updateChave_normalizesValueAndClearsCurrentHistory() = runBlocking {
        val fixture = createFixture("controller_key.preferences_pb")
        fixture.stateRepository.saveState(
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
        fixture.stateRepository.saveState(
            CheckingState.initial().copy(
                chave = "AB12",
                checkInProjeto = ProjetoType.P80,
                isLoading = false,
            ),
        )
        fixture.controller.initialize()

        val message = fixture.controller.syncHistory()

        val state = fixture.controller.uiState.value.state
        assertEquals("Historico sincronizado com a API.", message)
        assertEquals("Historico sincronizado com a API.", state.statusMessage)
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
        fixture.stateRepository.saveState(
            CheckingState.initial().copy(
                chave = "AB12",
                registro = RegistroType.CHECK_IN,
                checkInInforme = InformeType.RETROATIVO,
                checkInProjeto = ProjetoType.P83,
                isLoading = false,
            ),
        )
        fixture.controller.initialize()

        val message = fixture.controller.submitCurrent()

        val request = fixture.transport.requests.single()
        val payload = JsonParser.parseString(request.body).asJsonObject
        assertEquals("POST", request.method)
        assertEquals("https://tscode.com.br/api/mobile/events/forms-submit", request.url)
        assertEquals("AB12", payload["chave"].asString)
        assertEquals("P83", payload["projeto"].asString)
        assertEquals("checkin", payload["action"].asString)
        assertEquals("retroativo", payload["informe"].asString)
        assertTrue(payload["client_event_id"].asString.startsWith("kotlin-"))
        assertEquals("Registro enviado.", message)

        val state = fixture.controller.uiState.value.state
        assertEquals("Registro enviado.", state.statusMessage)
        assertEquals(StatusTone.SUCCESS, state.statusTone)
        assertEquals(Instant.parse("2026-04-18T09:30:00Z"), state.lastCheckIn)
        assertEquals("Base Norte", state.lastCheckInLocation)
        assertEquals(RegistroType.CHECK_OUT, state.registro)
        assertFalse(state.isSubmitting)
    }

    @Test
    fun refreshLocationsCatalog_replacesCacheAndUpdatesAccuracyThreshold() = runBlocking {
        val fixture = createFixture("controller_catalog.preferences_pb")
        fixture.transport.enqueueResponse(
            statusCode = 200,
            body = """
                {
                  "synced_at": "2026-04-18T10:00:00Z",
                  "location_accuracy_threshold_meters": 45,
                  "items": [
                    {
                      "id": 7,
                      "local": "Base Catalogo",
                      "latitude": -22.9,
                      "longitude": -43.2,
                      "coordinates": [
                        {"latitude": -22.9, "longitude": -43.2}
                      ],
                      "tolerance_meters": 80,
                      "updated_at": "2026-04-18T09:00:00Z"
                    }
                  ]
                }
            """.trimIndent(),
        )
        fixture.stateRepository.saveState(
            CheckingState.initial().copy(
                chave = "AB12",
                isLoading = false,
            ),
        )
        fixture.controller.initialize()

        val count = fixture.controller.refreshLocationsCatalog()

        assertEquals(1, count)
        assertEquals(
            "https://tscode.com.br/api/mobile/locations",
            fixture.transport.requests.single().url,
        )
        assertEquals(45, fixture.controller.uiState.value.state.locationAccuracyThresholdMeters)
        assertEquals("Base Catalogo", fixture.controller.uiState.value.managedLocations.single().local)
        assertEquals(
            "Base Catalogo",
            fixture.locationRepository.loadLocations().single().local,
        )
    }

    private fun createFixture(fileName: String): ControllerFixture {
        val dataStore = createDataStore(fileName)
        val stateRepository = CheckingStateRepository(dataStore)
        val cacheRepository = ManagedLocationCacheRepository(dataStore)
        val dao = FakeManagedLocationDao()
        val locationRepository = ManagedLocationRepository(dao, cacheRepository)
        val transport = FakeCheckingHttpTransport()
        val apiService = CheckingApiService(transport)
        val controller = CheckingController(
            checkingStateRepository = stateRepository,
            apiService = apiService,
            locationRepository = locationRepository,
        )
        return ControllerFixture(
            controller = controller,
            stateRepository = stateRepository,
            locationRepository = locationRepository,
            dao = dao,
            transport = transport,
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
    val stateRepository: CheckingStateRepository,
    val locationRepository: ManagedLocationRepository,
    val dao: FakeManagedLocationDao,
    val transport: FakeCheckingHttpTransport,
)

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
    ) {
        queuedResults.addLast(Result.success(CheckingHttpResponse(statusCode, body)))
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
