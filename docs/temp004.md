# Checking — Execution Playbook for `plan004.md` (agent prompts) + verification suite

> **Audience:** an AI coding agent that executes `docs/plans/plan004.md` end to end, one prompt at a time.
> **Prime directive:** the app is **in production and working very well**. The ONLY new behaviors are
> (1) the check-in/out history dialog showing data + a real error state, and (2) a new, read-only,
> persisted **"Activities"** debug log. **Everything else — check-in/check-out, the situation engine, the
> background orchestrator's decisions, geofencing, the FGS, sync, offline replay, transport, accident mode,
> auth, every existing screen — must stay byte-for-byte intact.** In particular, the new activity logger
> must be **fire-and-forget and can NEVER throw into a check-in / FGS / receiver path.** `plan004.md` is the
> canonical spec (the *what*/*why*); this file (`temp004.md`) is the *how*: ordered, self-contained prompts
> + verification. When a prompt says "apply plan004 §X", open `plan004.md`, read that section in full, and
> implement it exactly.

Modeled on `docs/temp003.md`. Execute prompts **strictly in order**. Do not start a prompt until the
previous one compiles, its tests pass, and its **Verify** block is satisfied. **Never start a change phase
on a red baseline.**

This work spans **two surfaces**, in two git repos:
- **Kotlin app** — `checking_kotlin/` (own git repo `checking-kotlin`). All of Problem 2 and the client
  half of Problem 1 live here. Distributes via Play Store **AAB**; no auto-deploy.
- **Backend monolith** — `sistema/app/` (root repo `checking`). Problem 1's *data* requires the un-deployed
  "change D" bundle (migration `0078` + the `local` write + `GET /check/history`). Pushing root `main`
  deploys **PRODUCTION**; the migration must run there. **Human-gated.** No new backend code is written by
  this playbook — only verification + one guarded e2e test + the deploy gate.

> **Decisions are LOCKED (plan004 §3.2):** (1) the Activities log is **persisted** (Room); (2) retain
> **30 days OR 5,000 entries**, whichever is smaller, pruned on write, **rendered in pages of 30**;
> (3) a **new dedicated store** (`EvaluationLog` left untouched); (4) log the **complete background suite**
> — everything relevant while the app runs, including in the background with the phone locked. The
> Activities **table content is ENGLISH-ONLY**; only the Settings *row label* is localized.

---

## 0. Global context (every prompt assumes you have read this section)

### 0.1 Repos, build, run
- Repo root: `c:\dev\projetos\checkcheck`. Kotlin app: `c:\dev\projetos\checkcheck\checking_kotlin`.
- **Kotlin build/test recipe** (from `checking_kotlin/`):
  `./gradlew compileDebugKotlin compileDebugAndroidTestKotlin testDebugUnitTest`. Unit-test counts come
  from `app/build/test-results/testDebugUnitTest/*.xml`. **Never** run `connectedAndroidTest` (the
  `BootReceiver` crashes it). Instrumented (`androidTest`) tests: **compile** them as a gate; run on a
  connected device via `am instrument` **twice**, else mark **"device verification pending"**.
- **Backend tests** (only for Problem 1's deploy verification): from repo root,
  `python -m pytest -q --ignore=tests/test_api_flow.py` (SQLite, offline). Prod-touching tests are guarded
  (`@pytest.mark.prod_e2e` + `CHECKING_E2E_PROD=1`), per `tests/conftest.py`.

### 0.2 The change set (full detail in `plan004.md`)
- **Problem 1 (history empty):** the client path is already correct; the data is missing because the
  "change D" bundle is **not deployed** (HEAD has `/check/state` but NOT `/check/history`; migration `0078`
  that adds `CheckingHistory.local` is also not in HEAD). Fix = (A) deploy the bundle [human-gated],
  (B) client: surface a real error/retry state (today a load failure is silently shown as "empty"),
  (C) client: add an **Atividade** column (keep the existing **Local** column — location needs no client
  change). plan004 §2.
- **Problem 2 (Activities log):** a new **Room-backed**, persisted, paged (30/block), 30-day/5,000-entry
  activity log; a `ActivityLogger` crash-proof façade instrumented across the **complete background suite**;
  a Settings "Atividades/Activities" row → a day-grouped, color-coded, **English-only** dialog. plan004 §3.

### 0.3 Key Kotlin files — Problem 1 (history). Re-locate symbols by name; line numbers drift.
- `presentation/components/HistoryCard.kt` — the "ÚLTIMO CHECK-IN/CHECK-OUT" cells → `vm::openCheckinHistory`
  / `openCheckoutHistory` (summary from `HistoryState.lastCheckinAt/lastCheckoutAt` — already works).
- `presentation/components/CheckHistoryDialog.kt` — table **Data | Hora | Local** from `entries`; empty →
  `history.empty`. **No error param today.** Renders `entry.local ?: "-"`. ← add `isError`/`onRetry` +
  **Atividade** column.
- `presentation/check/CheckUiState.kt` — `historyDialogEntries`, `isHistoryDialogLoading`,
  **`historyDialogError`** (set, but not consumed by the dialog); `historyDialogAction`; `CheckDialog` enum.
- `presentation/check/CheckViewModel.kt` — `openCheckHistoryDialog(action)` (~L681–708):
  `checkRepository.getHistory(chave)` → `historyDialogEntries = r.data.filter { it.action == action }`;
  failure → `historyDialogError = true`. ← add `retryHistoryDialog()`.
- `presentation/check/CheckScreen.kt` — HistoryCard wiring (~L233–239), History dialog wiring (~L503–510).
- `data/repository/CheckRepositoryImpl.kt` — `getHistory` → `CheckApi.getHistory`; `toDomain()` (~L151–157,
  preserves `local`). `data/api/CheckApi.kt` — `@GET("check/history")`. `data/dto/CheckDtos.kt` —
  `WebCheckHistoryItemDto(action, projeto, local, time, informe)`; enums `@SerialName("checkin"/"checkout")`,
  `@SerialName("normal"/"retroativo")` (serialization is correct — do not change).
- `domain/model/CheckModels.kt` — `CheckHistoryEntry(action, projeto, local, time, informe)`,
  `HistoryState(... lastCheckinAt, lastCheckoutAt ...)`, `enum CheckAction { CHECKIN, CHECKOUT }`.
- Tests: `androidTest/.../ui/CheckHistoryDialogSmokeTest.kt`, `test/.../data/repository/CheckHistoryMapperTest.kt`.
- i18n dicts (6): `i18n/dictionaries/{Pt,En,Zh,Ms,Id,Tl}.kt` (the `history` namespace).

### 0.4 Key Kotlin files — Problem 2 (Activities log) + the complete background suite
- **Reuse reference (do NOT modify):** `platform/background/diagnostics/EvaluationLog.kt` +
  `EvaluationEntry`/`EvaluationOutcome`; `presentation/settings/diagnostics/EvaluationLogDialog.kt`
  (ring-buffer + dialog patterns to copy stylistically).
- **New files (additive):** `domain/model/ActivityLogEntry.kt` (enums `ActivityActor`/`ActivityKind`/
  `ActivitySeverity` + data class); `data/local/activitylog/{ActivityLogRow.kt, ActivityLogDao.kt,
  CheckingActivityDatabase.kt}`; `data/.../activitylog/ActivityLog.kt` (store);
  `platform/activitylog/ActivityLogger.kt` (façade); a Hilt `@Module` providing the DB/DAO/store;
  `presentation/settings/activitylog/ActivityLogDialog.kt`.
- **Instrumentation sites (add one `ActivityLogger` call each; no logic change)** — see plan004 §3.4:
  `presentation/check/CheckViewModel.kt` (`onSubmit` ~L979–1126 manual; `attemptLogin` ~L277–324;
  `onLocationPermissionStateChanged` ~L540; `captureLocation` ~L472–503; `onAutomaticActivitiesToggled`
  ~L1256); `domain/usecase/RunAutomaticActivitiesUseCase.kt` (~L37–99); `domain/usecase/CaptureLocationUseCase.kt`;
  `platform/background/BackgroundCheckOrchestrator.kt` (`runOnceLocked` ~L148–271, `attemptSilentRelogin`
  ~L414–436); `platform/background/AutoActivityForegroundService.kt` (onCreate/onDestroy ~L38/L77);
  `platform/background/AutoActivityController.kt` (~L31/L50); `platform/background/AutoActivityWatchdogWorker.kt`;
  `platform/background/BootReceiver.kt` (**goAsync**); `platform/background/GeofenceBroadcastReceiver.kt`
  (**goAsync**); `platform/background/GeofenceManager.kt`; `platform/background/offline/{OfflineCheckQueue.kt,
  PendingCheckReplayer.kt, SyncPendingChecksWorker.kt}`; `permissions/PermissionLadder.kt`; the
  `@HiltAndroidApp` Application class (app start).
- **UI:** `presentation/components/SettingsDialog.kt` (+ row + `onActivitiesClick` param);
  `presentation/check/CheckScreen.kt` (wire + render); `presentation/check/CheckUiState.kt`
  (`CheckDialog.Activities` + paged state); `presentation/check/CheckViewModel.kt`
  (`openActivitiesDialog`/`loadMoreActivities`); `presentation/theme/Color.kt` (+ orange + dark-blue tokens).
- **Build:** `app/build.gradle.kts` + `gradle/libs.versions.toml` (add Room runtime+ktx + Room KSP compiler;
  KSP is already used for Hilt). minSdk 24 supports Room.

### 0.5 The Activities contract (English-only; full detail in plan004 §3.1–§3.3)
- **Model:** `ActivityLogEntry(at: Instant, actor: USER|SYS, kind, severity, description: String,
  location: String?)`. `ActivityKind ∈ {check-in, check-out, active, inactive, error}` (required) **+
  {trigger, location, sync, auth, system}** (background suite). `ActivitySeverity ∈ {SUCCESS, FAILURE,
  WARNING, INFO}` → **color only**: SUCCESS=green (`CheckingSuccess`), FAILURE=red (`CheckingErrorVivid`),
  WARNING=orange (new token), INFO=dark blue (new token).
- **Columns:** **Time** (`HH:mm:ss`, device zone) · **Who** (`user`/`sys`) · **Activity** (the `kind` text)
  · **Description** (English). Grouped by **local day** (date header per day), newest day & row first.
- **Required descriptions (exact):** `Check-in at <location>.` · `Check-out at <location>.` ·
  `Check-in failed at <location>.` · `Check-out failed at <location>.` · `Checking is now active.` ·
  `Checking is now inactive.` Extras follow the same style (plan004 §3.1/§3.4).
- **Persistence:** Room `activity_log` (id, atEpochMs[indexed], actor, kind, severity, description,
  location?), pruned to **30 days OR 5,000 rows** on write; paged `pageNewestFirst(limit=30, offset)`.
- **Crash-proof:** every `ActivityLogger` helper is `runCatching`-wrapped + off-thread; receivers use
  `goAsync()` so locked-phone events persist.

### 0.6 Backend "change D" bundle (Problem 1 data — already in the working tree, NOT in HEAD)
- Migration `alembic/versions/0078_add_local_to_checkinghistory.py` (adds `CheckingHistory.local`).
- `services/checking_history.py:25 record_checking_history(... local=local)` (persists location on write).
- `routers/web_check.py:892 get_web_check_history` + `services/checking_history.py:68 list_checking_history`.
- `schemas.py:4186 WebCheckHistoryItem` (has `local`) / `:4196 WebCheckHistoryListResponse`.
- **All four must deploy together + migration `0078` must run in prod** (plan004 §2.1). Old pre-deploy rows
  have null `local` ("-"); new ones carry location.

### 0.7 Safety
- **Default everything to LOCAL/offline.** The only prod-touching test is the guarded `/check/history`
  read (reuse the `prod_e2e` marker + `CHECKING_E2E_PROD=1`). Never loop prod calls.
- **Do NOT `git commit`/`push`/branch, deploy, or publish an AAB** unless the human asks. Pushing root
  `main` deploys backend PRODUCTION (and must run migration `0078`). The AAB is a separate human-gated step.

---

## 1. Golden rules (apply to EVERY prompt)
1. **Existing flows are sacred.** Only the two new behaviors change. Do not alter any decision, result, or
   control flow of check-in/out, the engine, orchestrator, geofencing, FGS, sync, offline replay, auth,
   transport, accident, or any existing screen. Instrumentation calls are **side-effect-only additions**.
2. **The activity logger can NEVER break a flow.** Every `ActivityLogger.log*` call is fully
   `runCatching`-wrapped and dispatched off the caller's thread; a logging failure is swallowed. Prove it
   with a test (a throwing logger must not change a check-in result).
3. **Additive-first.** New files/classes/columns/keys over edits. New DB is isolated (version 1, no
   migration of existing storage). `EvaluationLog` is untouched.
4. **The Activities table is ENGLISH-ONLY.** Hardcode its headers/Who/Activity/Description in English. Only
   `settings.activitiesLabel` is localized (all 6 dicts).
5. **Touch all 6 i18n dicts together** (`history.*` for Problem 1; `settings.activitiesLabel` for Problem 2)
   and re-run `I18nTest`.
6. **Location for Problem 1 needs no client change** — keep the `Local` column; it populates once the
   change-D bundle deploys. Do not remove it.
7. **One prompt = one compilable, test-passing increment.** Run the §0.1 recipe after each; keep the
   baseline green (`testDebugUnitTest` is **207/0** today incl. `I18nTest` 17/0); add **zero** new failures.
8. **Crash-proofing the receivers:** `BootReceiver` / `GeofenceBroadcastReceiver` must keep the process
   alive (`goAsync()`/bounded await) until the activity row is written, or locked-phone events are lost.
9. **Do NOT commit/push/branch/deploy/publish** without explicit human approval (see §0.7).
10. Keep Sections 2/3/4 current. If reality differs from `plan004.md`, **STOP, log in Section 3, report.**

---

## 2. Progress tracker (update after each prompt)

**Execution (build):**
- [x] **EP0** Baseline — 2026-06-21: `compileDebugKotlin` + `compileDebugAndroidTestKotlin` green; `testDebugUnitTest` **207 passed / 0 failed / 0 skipped** (incl. `I18nTest` **17/0**). `checking_kotlin`: branch `main…origin/main`, HEAD `4d6458b` (1.6.1), **tree DIRTY (21 files)** = uncommitted plan003 EP7–9 + U1/U2 (deviation EP0-1). Root repo HEAD `0818364`, dirty (53 files, plan002/003 un-pushed). **Problem-1 deploy gap confirmed:** HEAD `web_check.py` has `check/history`=**0**, `check/state`=**1**; `0078_add_local_to_checkinghistory` **absent from HEAD**. See §4.
- [x] **EP1** Backend: verify the "change D" history bundle + add the guarded `/check/history` prod-e2e read; flag the human-gated deploy — 2026-06-21: **bundle verified complete + correct (no gap, no code change):** `0078` adds `checkinghistory.local` (nullable, outside `uq_checkinghistory_event`, clean up/down); `record_checking_history(... local=local)` persists it (line 62) and the sole caller `user_sync.py:435` threads `local=local`; `get_web_check_history` returns `local=row.local` newest-first (`list_checking_history` ORDER BY time DESC); `WebCheckHistoryItem` carries `local: str|None`. **Added `tests/test_e2e_prod_history.py`** (`@pytest.mark.prod_e2e`, read-only: login TEST → `GET /web/check/history` → 200 + `items` list + every row has the change-D shape + ≥1 non-null `local` post-deploy). **Verify:** `pytest tests/test_prod_e2e_guard.py tests/test_e2e_prod_history.py` → **1 passed / 2 skipped** (new test default-skips; suite stays offline). **Deploy gate (EP1-note §3):** ships with the human-gated root `main` push; **migration `0078` must run in prod** — until then history is empty by design.
- [x] **EP2** Client: `CheckHistoryDialog` error/retry state + VM `retryHistoryDialog()` — 2026-06-21: `CheckHistoryDialog` gained `isError`/`onRetry` params + a 4th exclusive state (loading → **error+retry** → empty → data); the error branch shows `history.loadError` + a `history.retry` TextButton (keys added in EP3; resolve to key-path until then — no test asserts them yet). `CheckViewModel`: extracted `loadHistoryDialog(action)` (success/filter logic **byte-identical**) reused by `openCheckHistoryDialog` + new public `retryHistoryDialog()` (re-loads current `historyDialogAction`). `CheckScreen` passes `isError = state.historyDialogError`, `onRetry = { vm.retryHistoryDialog() }`. Updated the 3 `CheckHistoryDialogSmokeTest` call sites (`isError=false`, `onRetry={}`) so androidTest compiles. **Verify:** `compileDebugKotlin`+`compileDebugAndroidTestKotlin`+`testDebugUnitTest` green; **207/0** (unchanged). Summary (HistoryCard) + success path untouched.
- [x] **EP3** Client: add the **Atividade** column (keep **Local**) + `history.*` i18n (5 keys × 6) — 2026-06-21: `CheckHistoryDialog` columns now **Data | Hora | Atividade | Local** (weights 1 / 0.8 / 1 / 1.4); the Atividade cell is derived per-row from `entry.action` (`CHECKIN`→`history.activityCheckin`, `CHECKOUT`→`history.activityCheckout`). **Local column kept byte-identical** (`entry.local ?: "-"`). Added 5 keys to **all 6 dicts** (`colActivity`, `activityCheckin`, `activityCheckout`, `loadError`, `retry`), terminology consistent with each dict (e.g. zh 活动/签到/签退). **Verify:** parity 6/6 for all 5 keys; `compileDebugKotlin`+`compileDebugAndroidTestKotlin`+`testDebugUnitTest` green; **207/0**; **`I18nTest` 17/0**. The EP2 error/retry strings now resolve natively in all 6 langs. (Zh.kt needed a re-read mid-edit — IDE buffer; no content issue.)
- [x] **EP4** Room foundation: dependency + `activity_log` Entity/DAO/Database + Hilt module — 2026-06-21: added **Room 2.7.2** (KSP2-compatible) to `libs.versions.toml` + `room-runtime`/`room-ktx`/`ksp(room-compiler)` in `app/build.gradle.kts`. New `data/local/activitylog/`: `ActivityLogRow` (`@Entity("activity_log")`, `id` PK autogen, `atEpochMs` indexed, actor/kind/severity/description/location?; enums stored as `name`); `ActivityLogDao` (`insert`, `pageNewestFirst(limit,offset)` ORDER BY atEpochMs DESC,id DESC, `count`, `deleteOlderThan`, `trimToMax`, `clearAll` — manual paging, no Paging3); `CheckingActivityDatabase` (`@Database(version=1, exportSchema=false)`, isolated `checking_activity.db`). `di/ActivityLogModule.kt` provides DB+DAO (`@Singleton`, mirrors `DataStoreModule`). **DAO instrumented tests** `androidTest/.../ActivityLogDaoTest.kt` (5: insert/count, paging blocks of 30 disjoint+newest-first [65 rows], deleteOlderThan, trimToMax keeps newest N, clearAll; `runBlocking`). **Verify:** `compileDebugKotlin`+`compileDebugAndroidTestKotlin`+`testDebugUnitTest` green (Room KSP + Hilt coexist; `CheckingActivityDatabase_Impl.kt` generated); **207/0** (DAO tests are androidTest → device-pending run). Existing DataStore/offline-queue untouched.
- [x] **EP5** `ActivityLogEntry` model + `ActivityLog` store + crash-proof `ActivityLogger` façade — 2026-06-21: `domain/model/ActivityLogEntry.kt` (enums `ActivityActor`/`ActivityKind`{check-in/out, active/inactive, error + trigger/location/sync/auth/system}/`ActivitySeverity`{SUCCESS/FAILURE/WARNING/INFO} + data class). `data/local/activitylog/ActivityLog.kt` (`@Singleton`): `record` (insert + prune **30d via RETENTION_MS + 5,000 via trimToMax** on write), `page(offset, limit=30)`, `count`, `clear`; row↔entry mapping; suspend-only. `platform/activitylog/ApplicationScope.kt` (`@Qualifier`) + provider added to `di/ActivityLogModule.kt` (`CoroutineScope(SupervisorJob()+Dispatchers.IO)`, `@Singleton`). `platform/activitylog/ActivityLogger.kt` (`@Singleton`, injects Clock + ActivityLog + `@ApplicationScope` scope): typed helpers with **exact English** descriptions (`Check-in at <loc>.`, `Check-out failed at <loc>.`, `Checking is now active.`+optional ` (detail)`, etc.), persisted via `appScope.launch { runCatching { record } }` inside an outer `runCatching` → **crash-proof + off-thread**; `verbose` flag mutes `logTrigger`. **JVM tests:** `ActivityLogStoreTest` (2: prune-on-write args, newest-first mapping), `ActivityLoggerTest` (4: exact descriptions/kind/severity/actor, active/inactive exact, verbose gating, **crash-proof — throwing DAO never propagates**) via real store + fake DAO (no mockk on a final class) + `UnconfinedTestDispatcher`. **Verify:** build green; **213/0** (207 → +6). Logger NOT yet wired to any flow (EP6/EP7). (Fixed a `ActivitySeverity.ERROR`→`FAILURE` typo.)
- [x] **EP6** Instrument CORE: manual + automatic check-in/out (ok/fail) + active/inactive (FGS + scheduled pause) — 2026-06-21: **production** — `RunAutomaticActivitiesUseCase` (+`activityLogger` ctor): Submitted→`logCheckIn/Out(SYS,local,true)`, network→`logQueuedOffline(SYS,kind,local)`, non-network fail→`logCheckIn/Out(SYS,local,false)`. `CheckViewModel.onSubmit` (+`activityLogger` ctor, last param): success→`logCheckIn/Out(USER,local,true)`, 401→`logError("Session expired — sign in again.")`, network→`logQueuedOffline(USER,…)`, other→`logCheckIn/Out(USER,local,false)`. `AutoActivityForegroundService` (@Inject): onCreate→`logActive("Background service started.")`, onDestroy→`logInactive("Background service stopped.")`. `BackgroundCheckOrchestrator` (+`activityLogger` ctor): pause begin→`logInactive("Scheduled pause started.")`, pause end→`logActive("Scheduled pause ended.")`. No control-flow changes. **Tests** — 8 existing construction sites (3 use-case + 3 orchestrator + 2 VM) get a no-op `mockk(relaxed=true)` logger; new `RunAutomaticActivitiesLoggingTest` (4: success→CHECK_IN/SUCCESS, network→SYNC/WARNING queued, http→CHECK_IN/FAILURE, **crash-proof: throwing DAO → result still Submitted**) via real logger + capturing DAO. **Verify:** build green; **217/0** (213→+4). Scoping notes in §3 EP6-1 (raw-reading offline → EP7; manual VM-submit assertion → TP3).
- [x] **EP7** Instrument EXTENDED suite: triggers, geofence, location, offline/sync, auth/reauth, permission/battery, boot, watchdog, app-start, toggle — 2026-06-21: **production (side-effect-only, NO control-flow change), strictly per plan004 §3.4.** `BackgroundCheckOrchestrator.runOnceLocked`: entry→`logTrigger(trigger.name)` (verbose-gated), TOGGLE_OFF→`logSystem(WARNING)`, SKIP→`logSystem`, `NoAction`→`logSystem` (Submitted/NetworkError/NotConfigured stay owned by the use-case → no dup); `attemptSilentRelogin`: success→`logAuth("Session refreshed.")`, both failures→`logError("Re-authentication required.")`. `RunAutomaticActivitiesUseCase`: NotConfigured→`logSystem(WARNING)`, raw-reading offline→`logLocation(WARNING)` (resolves EP6-1a). `CaptureLocationUseCase` (+`activityLogger` ctor): Matched→`logLocation` fixed (INFO) / accuracy-too-low (WARNING) — **single chokepoint for manual+auto**. `PendingCheckReplayer` (+ctor): drain→`logSyncing(n)`, DONE→`logSynced(kind,local)`, DROP→`logSyncDropped(kind)` (RETRY logs nothing). `GeofenceBroadcastReceiver`/`BootReceiver` (+`@Inject`): enter/exit→`logLocation` (before goAsync), reboot→`logSystem` (after re-arm). `GeofenceManager` (+ctor): register→`logSystem`. `AutoActivityWatchdogWorker` (+@AssistedInject): healthy→`logSystem` / restart→`logSystem(WARNING)`. `CheckingApp` (+`@Inject`): onCreate→`logSystem("App started.")`. `CheckViewModel`: attemptLogin→`logAuth("Signed in.")`/`logError("Sign-in failed.")`, permission revoke→`logWarning`, toggle→`logSystem(enabled/disabled by user)`. **De-dup/consolidation in §3 EP7-1** (OfflineCheckQueue + SyncPendingChecksWorker NOT instrumented; capture logged in use-case not VM). **Tests** — `PendingCheckReplayerTest` (logger→field + 3 verify: syncing/synced/dropped); +2 in `RunAutomaticActivitiesLoggingTest` (NotConfigured→SYSTEM/WARNING, raw-queued→LOCATION/WARNING); new `CaptureLocationLoggingTest` (3: fixed INFO / accuracy WARNING / crash-proof). Only real test-construction site touched: `PendingCheckReplayerTest:44` (recon-confirmed all others mock). **Verify:** `compileDebugKotlin`+`compileDebugAndroidTestKotlin`+`testDebugUnitTest` green; **224/0** (217→+7). Orchestrator outcome/auth/watchdog/receiver/app assertions deferred to TP3 (Android-static / heavy-setup); receiver goAsync write-completion argued in §3 EP7-1(e).
- [x] **EP8** UI: Settings "Activities" row + `CheckDialog.Activities` + paged `ActivityLogDialog` + theme colors + `settings.activitiesLabel` (× 6) — 2026-06-21: **Theme** — `CheckingActivityWarning` (orange-600) + `CheckingActivityInfo` (blue-800/dark blue) in `Color.kt` (SUCCESS/FAILURE reuse `CheckingSuccess`/`CheckingErrorVivid`). **i18n** — `settings.activitiesLabel` in all 6 dicts (Atividades/Activities/活动/Aktiviti/Aktivitas/Mga Aktibidad) — the ONLY localized string; table is English. **State** — `CheckUiState`: `CheckDialog.Activities` + `activityEntries`/`activityNextOffset`/`activityCanLoadMore`/`isActivitiesLoading`. **VM** (+`activityLog: ActivityLog` ctor, last param): `openActivitiesDialog()` (reset + page 0 of 30, set canLoadMore), `loadMoreActivities()` (append next 30, advance offset, guard re-entrancy + end), `clearActivities()` — every store read `runCatching`-wrapped (crash-proof). **Settings row** — `SettingsDialog` +`onActivitiesClick` param + `Icons.Outlined.History` row in the Ajuda group; `CheckScreen` wires `onActivitiesClick = { dismiss(); openActivitiesDialog() }` + renders `CheckDialog.Activities -> ActivityLogDialog(...)`. **Dialog** — new `presentation/settings/activitylog/ActivityLogDialog.kt` (style mirrors `EvaluationLogDialog`): title "Activities" + bounded-height `LazyColumn` (440.dp — REQUIRED inside DialogScaffold's verticalScroll), day-grouped (date header per local day, English `EEE, dd MMM yyyy`), rows Time(`HH:mm:ss`, mono)·Who(`user`/`sys`)·Activity(kind text)·Description, **text color by severity** (green/red/orange/dark-blue), lazy load-more on scroll (`derivedStateOf` near-end → `loadMoreActivities`, trailing "Loading…"), empty → "No activity recorded yet.", Clear + Close. **Tests** — new `CheckViewModelActivitiesPagingTest` (2: page-0 sets canLoadMore; loadMore appends + stops on short page + no-op when exhausted); new androidTest `ActivityLogDialogSmokeTest` (3: empty / English rows / Close→dismiss — device-pending); +1 `I18nTest` (`settings.activitiesLabel` ×6); updated the 2 VM ctor sites (+`mockk` activityLog). Only 3 real `CheckViewModel(` sites exist (grep-confirmed). **Verify:** `compileDebugKotlin`+`compileDebugAndroidTestKotlin`+`testDebugUnitTest` green; **228/0** (225→+3 JVM; the dialog smoke is androidTest → device-pending); **`I18nTest` 19/0**. `EvaluationLog` + every other Settings row untouched. Minor spec-latitude choices in §3 EP8-1.

**Verification (PHASE T):**
- [x] **TP0** Test harness, recipes, prod-safety confirmation — 2026-06-21: confirmed **Kotlin JVM unit** (`mockk`+`StandardTestDispatcher`+`runTest`, template `CheckViewModelForegroundTest`), **Room instrumented DAO** (`Room.inMemoryDatabaseBuilder`, `ActivityLogDaoTest`), **Compose smoke** (`createComposeRule`; `EvaluationLogDialogSmokeTest`/`CheckHistoryDialogSmokeTest`/`ActivityLogDialogSmokeTest`), **`I18nTest`** (19/0), and the **backend `prod_e2e` guard** (`CHECKING_E2E_PROD` → 2 prod tests skip). Default suites offline: **Kotlin 232/0**; **backend 607 passed / 12 skipped / 33 failed** where the 33 are PRE-EXISTING `test_transport_ai_*` (OUT of plan004 scope — no transport backend change; transport_ai `.py` unmodified vs HEAD; plan004 backend tests = **8 passed / 2 skipped**). Recorded in §4.
- [x] **TP1** Problem 1 — history exhaustive — 2026-06-21: **1. VM** — new `CheckViewModelHistoryDialogTest` (4): Success → `historyDialogEntries` filtered by action (check-ins under CHECKIN / check-outs under CHECKOUT) incl. **non-null `local` preserved**, `historyDialogError=false`; Failure → `historyDialogError=true` + entries empty (never a silent "empty"); `retryHistoryDialog()` re-loads the **current** action + clears the error. **2. Mapper** — `CheckHistoryMapperTest` already asserts non-null `local` ("Área X") + null passthrough (`assertNull`) + empty list survive DTO→domain (no change needed). **3. Smoke** — `CheckHistoryDialogSmokeTest` +3 (compile-gated): error state shows `loadError`+`retry` and NOT `empty` (error shadows empty); `colActivity` header + `activityCheckin`/`activityCheckout` per-action labels render; existing location ("Área X") / null→"-" kept. **4. Guarded prod read** — `test_e2e_prod_history` default-skips (asserts non-null `local` post-deploy under `CHECKING_E2E_PROD=1`). **Verify:** `compileDebugKotlin`+`compileDebugAndroidTestKotlin`+`testDebugUnitTest` green; **232/0** (228→+4 JVM; smoke +3 androidTest/device-pending); `I18nTest` 19/0; plan004 backend history tests 8 passed/2 skipped.
- [x] **TP2** Room store/DAO exhaustive — 2026-06-21: existing coverage confirmed + extended. **DAO** (`ActivityLogDaoTest`, androidTest): insert/count; `pageNewestFirst(30,0)`/`(30,30)` disjoint+newest-first (65 rows); `deleteOlderThan` removes only old; `trimToMax(4)` keeps newest N; **+NEW `trimToMax_at5000_keepsNewest5000`** (seed 5001 → trim 5000 → count 5000, oldest dropped / newest kept). **Store** (`ActivityLogStoreTest`, JVM fake-DAO): `record` prunes-on-write with correct args (`deleteOlderThan(at−RETENTION_MS)` + `trimToMax(MAX_ROWS)`); `page` newest-first mapping; **+NEW literal-pin** (`RETENTION_DAYS=30L`, `RETENTION_MS=2_592_000_000L`, `MAX_ROWS=5_000`, `PAGE_SIZE=30` — guards the Int-overflow regression). **+NEW real-Room `ActivityLogStoreRoomTest`** (androidTest): `record`→`page` round-trip newest-first with all fields preserved; the 30-day age prune enforced ON WRITE. **Verify:** `compileDebugKotlin`+`compileDebugAndroidTestKotlin`+`testDebugUnitTest` green; **239/0** (store literal-pin +1 JVM; DAO `trimToMax5000` + the store round-trip/prune are androidTest → device-pending).
- [x] **TP3** `ActivityLogger` + instrumentation exhaustive — 2026-06-21: **1. Mapping** — `ActivityLoggerTest` extended to the FULL helper table (offline/sync: `logQueuedOffline` USER+SYS / `logSyncing` / `logSynced` / `logSyncDropped`; background: `logTrigger` / `logLocation` INFO+WARNING / `logAuth` / `logSystem` INFO+WARNING / `logWarning` / `logError`) — each → exact §0.5/§3.1 English description + correct kind/severity/actor; **unknown-location fallback** ("an unknown location" for null/blank) asserted. **2. Crash-proof** — `crashProof_allHelpers_neverPropagate` (a throwing DAO never propagates out of ANY helper); use-case end-to-end crash-proof (`RunAutomaticActivitiesLoggingTest`); manual `onSubmit` crash-proof transitively (its `logCheckOut` is crash-proof). **3. Seams** — automatic ok/fail end-to-end (`RunAutomaticActivitiesLoggingTest`); replayer syncing/synced/dropped (`PendingCheckReplayerTest`); capture fixed/accuracy (`CaptureLocationLoggingTest`); **manual (USER) submit** mapped at the logger seam (`manual_submit_calls_map_to_user_rows`: check-out ok/fail, queued-offline, session-expired). **4. Verbose** — `verboseOff_mutesOnlyTrigger_coreStillLogs` (verbose off → `logTrigger` muted; check-in/active/error still log). The VM-through-`onSubmit` end-to-end needs an AUTHENTICATED state (Android statics) → covered on-device; see §3 TP3-1. **Verify:** build green; **239/0** (`ActivityLoggerTest` +6 JVM).
- [x] **TP4** Activities UI — 2026-06-21: extended `ActivityLogDialogSmokeTest` (androidTest, compile-gated; **on-device run pending** per plan003 TP5) — now 7 cases. **+ two date headers** across two local days (newest day's group first) **+ Time column** (`HH:mm:ss`), both asserted via the dialog's exact formatters (deterministic on any device/zone); **+ all four severities render** (SUCCESS/FAILURE/WARNING/INFO rows — actual green/red/orange/dark-blue COLOR is device-visual → device-pending); **+ load-more trigger** (`canLoadMore` + near-end → `onLoadMore` fired via the `derivedStateOf`+`LaunchedEffect` path; the physical scroll-past-30 gesture is device-visual); **+ Clear → `onClear`**. Existing EP8 cases kept (empty state; English Who/Activity/Description rows; Close→dismiss) → columns Time·Who·Activity·Description all covered. **Verify:** `compileDebugKotlin`+`compileDebugAndroidTestKotlin`+`testDebugUnitTest` green; unit **239/0** unchanged (TP4 is androidTest-only; device run via `am instrument` ×2 pending).
- [x] **TP5** Master non-regression + coverage-matrix sign-off — 2026-06-21: coverage matrix written into §4 — every plan004 requirement maps to ≥1 green test. **Final snapshot:** Kotlin **239/0** (`I18nTest` 19/0; baseline 207 → **+32**, 0 new failures); androidTest compiles green (device-pending). Backend re-run **607 passed / 12 skipped / 33 failed** — the 33 are PRE-EXISTING `test_transport_ai_*` (out of plan004 scope, stable across runs); plan004 backend tests **8 passed / 2 skipped**. Protected behaviors (§4) intact (additive-only; AUDIT-1 + this run confirm no control-flow/behavior change). Acknowledged non-automated cells listed in §4 (device-pending androidTest + colors/scroll; receiver/app on-device; guarded prod read pending deploy+`0078`; AAB publish + backend deploy human-gated). **No uncovered requirement — plan004 is code-complete + verified.** Only the human-gated rollout (§6) remains.

---

## 3. Deviations log (append-only)
- **TP3-1 — 2026-06-21 — manual `onSubmit` end-to-end is covered at the logger seam + on-device, not via a
  driven VM (closes EP6-1b).** `CheckViewModel.onSubmit` opens with `if (!state.canSubmit) return`, and
  `canSubmit` requires `isAuthenticated`. Authenticating the VM in a JVM unit test means driving the
  auth-success path, which invokes Android statics (`PermissionLadder.checkStatus`, `AutoActivityController`)
  — the exact fragility `CheckViewModelForegroundTest` already documents and refuses. A first attempt at a
  driven `onSubmit` test failed for precisely this reason (unauthenticated → early return) and was removed.
  The manual (USER) path is instead covered by: (a) `ActivityLoggerTest.manual_submit_calls_map_to_user_rows`
  — the EXACT calls `onSubmit` makes (check-out ok/fail, queued-offline, session-expired) mapped to USER
  rows; (b) the logger-level crash-proof (a throwing `record` never propagates from `logCheckOut`, so
  `onSubmit` can never be broken by logging); (c) the EP6 compile-verified `onSubmit` wiring at all 4
  branches; (d) the AUTOMATIC path proven end-to-end; (e) on-device manual smoke (a manual check-in/out adds
  a USER row — TP4/device). No static-mocking was forced (it would couple the test to auth internals);
  this matches the project's established JVM-unit boundary.
- **EP8-1 — 2026-06-21 — two minor spec-latitude choices (not blockers; both within plan004 §3.5's stated
  latitude).** (a) **Settings row placement:** the "Activities" row sits in the **Ajuda (Help)** group
  (always visible, next to About), since this SettingsDialog has no diagnostics group and §3.5 said "a
  sensible group (e.g. near the existing diagnostics/help)". (b) **Dialog back affordance:** the dialog uses
  `DialogScaffold` (which already provides a `BackHandler` + scrim-tap dismiss) plus an explicit **Close**
  button, rather than a literal top-bar back-arrow icon — matching `EvaluationLogDialog`, the cited style
  reference. The title "Activities" + Close + system-back together satisfy the navigation intent. Also: the
  `LazyColumn` is given a **bounded height (440.dp)** because `DialogScaffold` already wraps its content in a
  `verticalScroll` Column (an unbounded lazy list inside a scrollable parent crashes at measure time) — same
  pattern `EvaluationLogDialog` uses (400.dp). Snapshot-at-open semantics (no auto-stream) per §3.5; a Clear
  action is wired (`clearActivities`).
- **AUDIT-1 — 2026-06-21 — adversarial consistency audit of EP0–EP6 (8 reviewers).** Triggered by a request
  to confirm the foundation (built by a less-capable agent) is correct. **Verdict: the EP0–EP6 CODE is
  consistent and correct — ZERO correctness defects.** All high-risk traps were avoided: the 30-day retention
  constant is `Long` (`RETENTION_DAYS * 24L * 60L * 60L * 1_000L` = 2,592,000,000L — no Int overflow);
  `trimToMax` SQL keeps the NEWEST N (`id NOT IN (… ORDER BY atEpochMs DESC, id DESC LIMIT :max)`);
  `pageNewestFirst` is `atEpochMs DESC, id DESC LIMIT/OFFSET`; prune-on-write enforces 30d **and** 5,000; the
  façade emits the EXACT §3.1 strings and is genuinely crash-proof (double `runCatching` + off-thread
  `appScope`); EP6 instrumentation is side-effect-only with correct actors (USER vs SYS), no control-flow
  change, no duplicate rows, all 8 test sites updated; EP1 backend bundle is correct + the prod-e2e test
  default-skips (verified `1 passed, 2 skipped`); Hilt graph complete with no duplicate/shadowing `@Provides`;
  all 41 `activityLogger.*` call sites use valid façade methods (no API drift); i18n parity verified across
  all 30 cells (5 keys × 6 dicts, correctly translated incl. zh 活动/签到/签退). **Findings were only
  test-coverage gaps + expected-not-yet-built EP8 + 1 stale comment — NOT bugs:**
  - **Fixed now:** (i) added `I18nTest.historyPlan004Keys_resolveInAllSixLanguages` — EP3's Verify promised
    "the 5 keys resolve in all 6 languages" but shipped no test; the keys were all present, just unguarded.
    (ii) Corrected a misleading inline comment in `GeofenceBroadcastReceiver` that overstated the goAsync
    write-completion guarantee (logging is best-effort off the application scope — already documented honestly
    in EP7-1(e)).
  - **Deferred to the TP verification phases (by design, not gaps in EP0–6):** VM unit test for the history
    dialog success/failure/retry + the `isError=true` smoke (→ TP1); the unknown-location fallback +
    `RETENTION_MS` literal-pin (→ TP2/TP3). The audit confirmed NO `@Ignore`/`@Disabled`/hollow tests exist.
  - **Expected (EP8 not built yet):** the Activities **viewer** UI — `CheckDialog.Activities`,
    `ActivityLogDialog`, `openActivitiesDialog`/`loadMoreActivities`, `settings.activitiesLabel` — and thus
    the store READ API (`page`/`count`/`clear`) is currently write-only/unconsumed. §2 correctly shows EP8
    `[ ]`; this is the next phase, NOT a defect. Backing layer (Room DB/DAO/store/logger + instrumentation)
    is complete + tested.
- **EP7-1 — 2026-06-21 — de-duplication + consolidation decisions (not blockers; all honor "do NOT spam
  duplicate rows" + "no control-flow change").**
  (a) **`OfflineCheckQueue.enqueue` is NOT instrumented.** Its callers already emit `logQueuedOffline`
  (`CheckViewModel.onSubmit` network branch + the use-case decided branch, both EP6). Logging inside
  `enqueue` would double every queued row. OfflineCheckQueue keeps its ctor unchanged (no test churn).
  (b) **`SyncPendingChecksWorker` is NOT instrumented.** It is a thin wrapper over
  `PendingCheckReplayer.drain()`, which now logs `logSyncing`/`logSynced`/`logSyncDropped`; instrumenting
  the worker too would double the "Syncing N" row. The worker's sync IS logged (via the replayer).
  (c) **Location-fix + accuracy-too-low are logged in `CaptureLocationUseCase` (one chokepoint), NOT in
  `CheckViewModel.captureLocation`.** The use-case is the single call site for BOTH manual and automatic
  captures, so a foreground capture is never logged twice. §3.4 suggested the VM site; the use-case is the
  de-duplicating equivalent that also covers the automatic path.
  (d) **Raw-reading offline queue (resolves EP6-1a).** Logged at the `RunAutomaticActivitiesUseCase`
  raw-enqueue site as a `LOCATION`/WARNING row ("Location reading queued offline — will sync on
  reconnect."), because no action kind is decided there — `logQueuedOffline` (which needs a kind) is
  inappropriate. The two DECIDED automatic outcomes were already instrumented in EP6.
  (e) **Receiver crash-proofing / write-completion.** `GeofenceBroadcastReceiver`/`BootReceiver` log via the
  injected `ActivityLogger`, whose Room write runs on the process-lifetime `@ApplicationScope`
  (`SupervisorJob`+`Dispatchers.IO`). The geofence row is logged BEFORE `goAsync()`, and the process stays
  alive for the seconds-long `orchestrator.runOnce` that follows — far longer than the tiny insert. The boot
  row is logged right after `AutoActivityController.start(...)` inside the goAsync coroutine, before
  `finish()`. Logging is best-effort by design (golden rule 2) — never a control-flow dependency — so a row
  lost under extreme process-death timing is acceptable for a debug log; NO receiver control flow changed
  (no `goAsync` restructuring, no awaiting of the fire-and-forget logger).
  (f) **Toggle vs. permission-revoke (minor, intentional redundancy).** A permission revoke routes through
  `onAutomaticActivitiesToggled(false)`, so it emits BOTH `logWarning("Location permission revoked — auto
  disabled.")` and `logSystem("Automatic activities disabled by user.")`. Kept: a debug log benefits from
  seeing cause + effect; deduping would require changing `onAutomaticActivitiesToggled` to detect its caller
  (control-flow risk, not worth it).
  (g) **Optional low-signal rows skipped.** `PermissionLadder` battery-degraded, SSE connect/disconnect, and
  exact-alarm scheduling (all marked *optional*/verbose in §3.4) are deferred — they are high-frequency/
  low-signal and would dilute the log. The required core + high-value background signals are all present.
  **Deferred to TP3 (exhaustive instrumentation phase):** unit assertions for the orchestrator outcome rows
  (trigger/toggle-off/skip/no-action), `attemptSilentRelogin`, the watchdog, `CheckingApp` start, and the
  two receivers (all need Android statics / heavy state setup). EP7 spot-checks the clean JVM seams:
  replayer (syncing/synced/dropped), use-case (NotConfigured/raw-queued), `CaptureLocationUseCase`
  (fixed/accuracy + crash-proof) — 7 new tests, all green.
- **EP6-1 — 2026-06-21 — two scoping notes (not blockers).** (a) The **raw-reading offline enqueue** in
  `RunAutomaticActivitiesUseCase` (~L43–59, network failure during location capture, BEFORE an action is
  resolved) is **deferred to EP7**: there is no check-in/check-out kind to log there, so it belongs with
  EP7's `location`/`sync` extended suite (logged as a LOCATION/SYNC event, not `logQueuedOffline` which
  needs a kind). The two DECIDED automatic outcomes (success + network-decided-enqueue + non-network
  failure) ARE instrumented in EP6. (b) The **manual (USER) path** is instrumented at all 4 `onSubmit` call
  sites (compile-verified) and the logger mapping for actor=USER is unit-proven in EP5
  (`ActivityLoggerTest`); the heavy end-to-end **VM-submit** assertion (drive `onSubmit` with full state) is
  **folded into TP3** rather than EP6, to avoid a fragile state-setup test. The AUTOMATIC path is asserted
  end-to-end here (success/queued/fail) plus crash-proof.
- **EP1-note — 2026-06-21 — change-D bundle is complete; deploy is the only gap.** All four pieces verified
  present + correct in the working tree (migration `0078`, `record_checking_history(local=local)` +
  caller `user_sync.py:435`, `get_web_check_history` returning `local=row.local` newest-first,
  `WebCheckHistoryItem.local`). **No code gap, no backend change made.** The ONLY blocker for Problem 1's
  data + location is the **human-gated deploy**: commit + push the change-D bundle on root `main`
  (deploys PRODUCTION) **and run migration `0078` in prod**. Until then `GET /check/history` 404s and the
  app's history is empty by design (root cause §1.2). Guarded verification: `tests/test_e2e_prod_history.py`
  (default-skipped; run with `CHECKING_E2E_PROD=1` after deploy). *Not a deviation — recorded here as the
  deploy-gate provenance per the EP1 prompt.*
- **EP0-1 — 2026-06-21 — baseline sits on a DIRTY `checking_kotlin` tree.** The Kotlin repo HEAD is
  `4d6458b` (released 1.6.1), but the working tree has **21 uncommitted files** = the plan003 Kotlin work
  (EP7–EP9: approval-gate DTOs/models/repo/VM/UI + 6 dicts) **and** the U1/U2 UX changes
  (`SettingsDialog`, `CheckScreen`, `CheckingNavHost`, `ManualScreen`, 6 dicts, `I18nTest`). plan004 work
  therefore stacks on top of un-committed plan003/U changes (analogous to temp003 EP0-1 on the root repo).
  **Not a blocker** — the tree compiles and `testDebugUnitTest` is 207/0 — but `git status` will never be
  clean, and a future AAB/commit carries plan003 + U1/U2 + plan004 together (still human-gated). The
  *released* 1.6.1 APK that testers run is HEAD `4d6458b` (does NOT include plan003/U/plan004); Problem 1's
  empty history is reproduced against that build hitting production.

---

## 4. Baseline log (filled by EP0, then mostly read-only)
- **Kotlin** (`checking_kotlin/`, EP0 — 2026-06-21): `compileDebugKotlin` + `compileDebugAndroidTestKotlin`
  **clean**; `testDebugUnitTest` **207 passed / 0 failed / 0 skipped → GREEN** (incl. `I18nTest` **17/0**).
  Baseline = "≥ 207 pass, 0 fail"; plan004 must add **zero** new failures.
- **Git trees:** `checking_kotlin` branch `main…origin/main`, HEAD `4d6458b` (1.6.1), **DIRTY (21 files,
  uncommitted plan003 EP7–9 + U1/U2 — EP0-1)**. Root repo HEAD `0818364`, dirty (53 files, un-pushed
  plan002/003).
- **Problem-1 deploy gap (confirmed):** `git show HEAD:sistema/app/routers/web_check.py` →
  `check/history`=**0**, `check/state`=**1**; `git show HEAD:alembic/versions/0078_add_local_to_checkinghistory.py`
  → **absent**. The released app calls `/check/history` → prod 404 → silently "empty" (root cause, plan004
  §1.2/§2.1). The change-D bundle must deploy (human-gated) for Problem 1's data + location.
  - **LIVE confirmation (2026-06-21, read-only, single-shot, real account):** authenticated against
    `https://tscode.com.br/api` and observed `GET /web/check/history` → **404 `{"detail":"Not Found"}`**
    while `GET /web/check/state` → **200** with real summary data (`current_action`, `last_checkin_at`,
    `last_checkout_at`, `current_local`). This **empirically proves** the root-cause split: the summary cells
    work (via the deployed `/check/state`); the history dialog is empty because `/check/history` is **not
    deployed**. Confirms Problem 1 is a deploy gap, not a client bug. (No writes; no credentials persisted.)
- **Test inventory (touched by plan004):** Problem 1 — `presentation/.../CheckHistoryDialog*`,
  `CheckViewModel`/`CheckScreen`, `data/repository/CheckHistoryMapperTest`, the 6 dicts (`history.*`).
  Problem 2 — new `activitylog/` (Room DAO/store/façade), the background instrumentation sites (§0.4),
  `SettingsDialog`/`ActivityLogDialog`, `theme/Color`, `I18nTest` (`settings.activitiesLabel`).

### TP0 harness/recipe + offline-suite confirmation (2026-06-21)
- **Kotlin JVM unit** (`./gradlew testDebugUnitTest`): **232 passed / 0 failed / 0 skipped** (incl. `I18nTest`
  **19/0**). Template: `CheckViewModelForegroundTest` (`mockk` + `StandardTestDispatcher` + `runTest`).
- **Room instrumented DAO** (`ActivityLogDaoTest`, `Room.inMemoryDatabaseBuilder`) + **Compose smoke**
  (`EvaluationLogDialogSmokeTest`, `CheckHistoryDialogSmokeTest`, `ActivityLogDialogSmokeTest`,
  `createComposeRule`): `compileDebugAndroidTestKotlin` green — **compile-gated; on-device run pending**
  (never `connectedAndroidTest` — `BootReceiver` crashes it).
- **Backend `prod_e2e` guard** (`CHECKING_E2E_PROD`): the 2 prod-e2e tests **default-skip** (confirmed).
- **Backend default (offline) suite** `python -m pytest -q --ignore=tests/test_api_flow.py` → **607 passed /
  12 skipped / 33 failed (622s)**. **The 33 failures are ALL `test_transport_ai_*` and PRE-EXISTING / out of
  plan004 scope:** `git diff HEAD -- sistema/app` shows only `checking_history.py`/`web_check.py`/`schemas.py`/
  `models.py`/`user_sync.py` + a static JS file — the transport_ai `.py` is **unmodified vs HEAD**, so these
  fail independent of plan004 (env-dependent LLM/runtime config). **plan004-relevant backend tests are GREEN:**
  `test_checking_history_local` + `test_web_check_history` + `test_prod_e2e_guard` + `test_e2e_prod_history`
  → **8 passed / 2 skipped**. Default suites run offline (no prod calls). *(Recorded per golden rule 10: the
  transport_ai failures are an out-of-scope reality, NOT a plan004 regression — TP5 will re-confirm.)*

### Protected behaviors — MUST remain identical end-to-end
- Manual + automatic check-in/check-out (decision, location match, submit, dedup, offline queue + replay).
- The background orchestrator's triggers/outcomes, geofencing, the FGS lifecycle, the watchdog, scheduled
  pause, exact-alarm wakes — behavior unchanged; instrumentation is observe-only.
- Auth/login/silent re-auth, session, sync, transport, accident mode.
- The "ÚLTIMO CHECK-IN/CHECK-OUT" **summary** (last timestamps via `/check/state`) — already works; do not
  regress it while changing the dialog.
- `EvaluationLog`/`EvaluationLogDialog` (untouched).
- Every existing Settings row + every screen/dialog/route.

### TP5 — Master coverage matrix + sign-off (2026-06-21)
**Final suite snapshot:** Kotlin `compileDebugKotlin`+`compileDebugAndroidTestKotlin`+`testDebugUnitTest` →
**239 passed / 0 failed** (incl. `I18nTest` **19/0**); androidTest **compiles green** (on-device run pending).
Backend `pytest -q --ignore=tests/test_api_flow.py` → **607 passed / 12 skipped / 33 failed** (re-run, stable)
— the 33 are PRE-EXISTING `test_transport_ai_*`, OUT of plan004 scope (no transport backend change); the
plan004-relevant backend tests are **8 passed / 2 skipped**. Baseline 207/0 → **+32 Kotlin unit tests, 0
failures added.**

| Requirement | Covering test(s) | Lane |
|---|---|---|
| History filter-by-action | `CheckViewModelHistoryDialogTest` (checkin→CHECKIN-only / checkout→CHECKOUT-only) | JVM ✅ |
| History **location** | ↑ (non-null `local` preserved) · `CheckHistoryMapperTest` (non-null+null DTO→domain) · `CheckHistoryDialogSmokeTest` (Local "Área X" / null→"-") | JVM ✅ + androidTest |
| History error/retry | `CheckViewModelHistoryDialogTest` (failure→error; retry reloads current action) · `CheckHistoryDialogSmokeTest` (loadError+retry, NOT empty) | JVM ✅ + androidTest |
| Atividade column + i18n | `CheckHistoryDialogSmokeTest` (colActivity + activityCheckin/out) · `I18nTest.historyPlan004Keys` (5×6) | androidTest + JVM ✅ |
| Backend bundle/deploy | `test_checking_history_local` · `test_web_check_history` (8/2-skip) · `test_e2e_prod_history` (guarded, skips) · LIVE prod confirm (history 404 / state 200) | backend ✅ (deploy human-gated) |
| Room paging-30 | `ActivityLogDaoTest.pageNewestFirst` (30,0)/(30,30) disjoint (65 rows) · `ActivityLogStoreRoomTest` round-trip | androidTest (device-pending) |
| Retention 30d / 5,000 | `ActivityLogDaoTest` (`deleteOlderThan` + `trimToMax_at5000`) · `ActivityLogStoreTest` (prune-args + literal-pin) · `ActivityLogStoreRoomTest` (30d prune on write) | JVM + androidTest ✅ |
| Logger descriptions/colors/actor | `ActivityLoggerTest` (full helper table → exact §3.1 strings + kind/severity/actor + unknown-location) | JVM ✅ |
| Crash-proof | `ActivityLoggerTest.crashProof_allHelpers` · `RunAutomaticActivitiesLoggingTest` (use-case e2e) · `CaptureLocationLoggingTest` | JVM ✅ |
| Each instrumented activity ok/fail | auto `RunAutomaticActivitiesLoggingTest` (success/network/http/NotConfigured/raw-queued) · sync `PendingCheckReplayerTest` (syncing/synced/dropped) · location `CaptureLocationLoggingTest` (fixed/accuracy) · manual USER `ActivityLoggerTest.manual_submit_calls` | JVM ✅ |
| Active/inactive incl. pause & boot | `ActivityLoggerTest` (active/inactive exact) + EP6/EP7 compile-verified wiring (FGS onCreate/onDestroy, orchestrator pause begin/end, Boot re-arm) | JVM + compile-verified (receivers device-pending) |
| Settings row + paged dialog + grouping + colors | `CheckViewModelActivitiesPagingTest` (open/loadMore/stop) · `ActivityLogDialogSmokeTest` (2 day headers, columns, 4 severities, load-more, clear, empty) | JVM + androidTest ✅ |
| `settings.activitiesLabel` ×6 | `I18nTest.settingsActivitiesLabel_resolvesInAllSixLanguages` | JVM ✅ |
| English-only table | `ActivityLogDialogSmokeTest` (English literals; only the row label is localized) | androidTest ✅ |

**Non-regression (Protected behaviors above):** all intact — plan004 added ONLY side-effect-only
instrumentation + new files; AUDIT-1 + this final run confirm **no control-flow change, no behavior change,
0 new failures**. `EvaluationLog`, every existing Settings row, screen, dialog and route untouched.

**Acknowledged non-automated / pending cells:**
- All `androidTest` (Room DAO/store, both dialog smokes) are **compile-gated** here → on-device run via
  `am instrument` ×2 pending (never `connectedAndroidTest` — `BootReceiver` crashes it).
- Severity **colors** + the physical **scroll-past-30** gesture are device-visual → device-pending.
- Receiver/worker/app instrumentation (Boot / Geofence / Watchdog / `CheckingApp`) verified by compile +
  logger mapping + reasoning (§3 EP7-1e) → on-device confirmation pending.
- Manual on-device smoke: a manual check-in/out adds a `USER` row; auto runs add `SYS` rows (§3 TP3-1).
- Guarded prod `/check/history` read: **pending the human-gated deploy + migration `0078`** (empirically
  404 today — confirmed live, §4 above).
- **AAB publish** + **backend `main` deploy**: human-gated (§6).
- Backend `test_transport_ai_*` (33 fail): PRE-EXISTING, out of plan004 scope.

**SIGN-OFF:** every plan004 requirement maps to ≥1 green test; Kotlin suites green (**239/0**); no uncovered
requirement; protected behaviors intact. **plan004 is code-complete and verified — only the human-gated
rollout (§6) remains.**

---

## 5. Definition of done
Section 2 fully ticked (EP0–EP8, TP0–TP5); Kotlin suites ≥ baseline + new, **0 failures** (`I18nTest`
green); the activity logger is proven crash-proof; **all protected behaviors (Section 4) intact**.
Problem 1: once the change-D bundle is deployed, both cells show the correct action's history with **date,
time, activity, and location**, and a load failure shows a clear retryable error (never a silent "empty").
Problem 2: a localized "Atividades/Activities" row opens an English-only, day-grouped, color-coded, paged
(30/block) table backed by a persisted Room store (30 days / 5,000 entries) covering the complete
background suite, surviving restarts/reboots. **Backend deploy (root `main`, runs migration `0078`) and the
AAB publish require explicit human approval;** the deploy is what makes Problem 1's data + location appear.

---

# EXECUTION PHASES (drive `plan004.md` to completion)

> Each EP recaps goal/context and points to the `plan004.md` section to apply, then runs its own Verify.
> **Kotlin-app changes ship via an AAB; the backend deploy is human-gated — never push/deploy/publish
> without explicit approval.**

## EP0 — Baseline
**Goal:** prove all suites green and snapshot what must not regress.
**Do:**
1. From `checking_kotlin/`: run `./gradlew compileDebugKotlin compileDebugAndroidTestKotlin
   testDebugUnitTest`. Record counts (expect `testDebugUnitTest` ~**207/0**, `I18nTest` 17/0; both compiles
   green).
2. Record git tree state for `checking_kotlin` (`git status`, HEAD) and note the root repo is dirty with
   un-pushed plan002/003 work (expected).
3. Confirm the Problem-1 deploy gap: `git show HEAD:sistema/app/routers/web_check.py | grep -c "check/history"`
   → **0**; `… | grep -c "check/state"` → **1**; `git show HEAD:alembic/versions/0078_add_local_to_checkinghistory.py`
   → absent. Record in §4.
**Do NOT:** change any code.
**Verify:** all suites green; baseline recorded in §4. **Update:** tick EP0.

## EP1 — Backend: confirm the "change D" history bundle + guarded e2e + deploy gate
**Goal:** guarantee the data path exists and is correct, add a guarded prod check, and make the
human-gated deploy explicit. **No new backend code.**
**Context to load:** plan004 §2.1, §0.6; `routers/web_check.py:892`, `schemas.py:4186/4196`,
`services/checking_history.py:25 & :68`, `alembic/versions/0078_add_local_to_checkinghistory.py`.
**Do:**
1. **Verify** (read-only) the four bundle pieces are present + correct in the working tree: the `0078`
   migration adds `CheckingHistory.local`; `record_checking_history(... local=local)` persists it;
   `get_web_check_history` returns `local=row.local` newest-first; the schemas carry `local`. Note any gap
   in §3 (do NOT "fix" working backend behavior — only report).
2. **Add a guarded prod-e2e read** (default-skipped) — extend `tests/test_e2e_prod_user_approval.py` or add
   `tests/test_e2e_prod_history.py`: `@pytest.mark.prod_e2e` test that, with `CHECKING_E2E_PROD=1` + an
   authenticated `TEST` session, `GET /web/check/history?chave=TEST` returns 200 with `items`, and (after
   deploy) at least one item has a **non-null `local`**. Confirm it **default-skips** without the opt-in.
3. **Document the deploy gate** in §3/§5: the bundle ships with the existing human-gated root `main` push
   and **migration `0078` must run in prod**; until then the app's history is empty by design.
**Do NOT:** write/modify backend endpoints, schemas, or migrations; push or deploy; loop prod calls.
**Verify:** `python -m pytest -q tests/test_prod_e2e_guard.py tests/test_e2e_prod_history.py` → the new
test **skips** by default (default suite stays offline). **Update:** tick EP1.

## EP2 — Client: history dialog error/retry state
**Goal:** a load failure is visibly distinct from a genuinely empty history (today it is silently "empty").
**Context to load:** plan004 §2.2; `CheckHistoryDialog.kt`, `CheckScreen.kt` (~L503–510),
`CheckViewModel.kt` (`openCheckHistoryDialog` ~L681–708), `CheckUiState.kt` (`historyDialogError`).
**Do:**
1. `CheckHistoryDialog.kt`: add params `isError: Boolean` and `onRetry: () -> Unit`. Render four exclusive
   states: **loading** (existing spinner), **error** (a clear "couldn't load — retry" message + a retry
   button; neutral/amber), **empty** (existing `history.empty`), **data** (existing table). Keep all
   existing params/behavior.
2. `CheckViewModel.kt`: extract the load body of `openCheckHistoryDialog(action)` into a private
   `loadHistoryDialog(action)` reused by both open and a new `retryHistoryDialog()` (re-loads the current
   `historyDialogAction`). No change to the success/filter logic.
3. `CheckScreen.kt`: pass `isError = state.historyDialogError`, `onRetry = { vm.retryHistoryDialog() }`.
**Do NOT:** change the success path, the action filter, or the summary (HistoryCard); remove any state.
**Verify:** `compileDebugKotlin compileDebugAndroidTestKotlin testDebugUnitTest` green. **Update:** tick EP2.

## EP3 — Client: Atividade column + history i18n (keep Local)
**Goal:** each row shows **date, time, activity, location**; new strings localized in all 6 langs.
**Context to load:** plan004 §2.3; `CheckHistoryDialog.kt`, `domain/model/CheckModels.kt` (`CheckAction`),
the 6 dicts (`history` namespace).
**Do:**
1. `CheckHistoryDialog.kt`: add an **Atividade** column → columns **Data | Hora | Atividade | Local**. The
   activity text is derived from `entry.action` (`CHECKIN` → `t("history.activityCheckin")`, `CHECKOUT` →
   `t("history.activityCheckout")`). **Keep the `Local` column exactly as is** (`entry.local ?: "-"`).
2. Add to **all 6 dicts** (same structure, professionally translated): `history.colActivity`,
   `history.activityCheckin`, `history.activityCheckout`, `history.loadError`, `history.retry`. Re-run
   `I18nTest`.
**Do NOT:** remove/rename existing `history.*` keys or the Local column; localize anything outside these
keys.
**Verify:** all suites + `I18nTest` green; the 5 keys resolve in 6 langs. **Update:** tick EP3.

## EP4 — Room foundation (dependency + activity_log Entity/DAO/Database + Hilt)
**Goal:** a persistent, paged, prunable store exists and is unit-proven — no instrumentation yet.
**Context to load:** plan004 §3.2 (Room decision), §3.3 (schema/DAO/pruning); `app/build.gradle.kts`,
`gradle/libs.versions.toml`; how the existing Hilt KSP + DI modules are wired.
**Do:**
1. Add Room to the build: `androidx.room:room-runtime`, `room-ktx`, and the `room-compiler` via **KSP**
   (the app already uses KSP for Hilt). Add the version to `libs.versions.toml`. Keep it minimal.
2. `data/local/activitylog/ActivityLogRow.kt`: `@Entity("activity_log")` `id Long PK autogen`, `atEpochMs
   Long` (indexed), `actor`, `kind`, `severity`, `description`, `location String?` (enums stored as `name`).
3. `data/local/activitylog/ActivityLogDao.kt`: `insert(row)`; `pageNewestFirst(limit, offset)`
   (`ORDER BY atEpochMs DESC, id DESC LIMIT :limit OFFSET :offset`); `count()`; `deleteOlderThan(epochMs)`;
   `trimToMax(max)`; `clearAll()`.
4. `data/local/activitylog/CheckingActivityDatabase.kt`: `@Database(version=1)` — a NEW DB file, isolated
   from any existing storage. Provide DB + DAO via a Hilt `@Module` (`@Singleton`).
5. **DAO instrumented tests** (`androidTest`, `Room.inMemoryDatabaseBuilder`): insert order; two
   `pageNewestFirst(30, 0)`/`(30, 30)` return disjoint newest-first blocks (seed > 60); `count()`;
   `deleteOlderThan` removes only old; `trimToMax(N)` caps to newest N; `clearAll()` empties.
**Do NOT:** touch existing DataStore/offline-queue storage; add Paging3 (manual paging only); change Hilt
graph behavior elsewhere.
**Verify:** `compileDebugKotlin compileDebugAndroidTestKotlin testDebugUnitTest` green (KSP Room + Hilt
coexist); DAO tests compile (run on device if available, else device-pending). **Update:** tick EP4.

## EP5 — ActivityLog store + crash-proof ActivityLogger façade
**Goal:** a typed, crash-proof logging API that builds English descriptions + severity and persists
off-thread.
**Context to load:** plan004 §3.1 (descriptions/colors), §3.3 (store + façade + crash-proofing);
`core/time/Clock`, the app's `@ApplicationScope`/coroutine-scope provision (or add one), `EvaluationLog`
for style.
**Do:**
1. `domain/model/ActivityLogEntry.kt`: enums `ActivityActor{USER,SYS}`,
   `ActivityKind{CHECK_IN,CHECK_OUT,ACTIVE,INACTIVE,TRIGGER,LOCATION,SYNC,AUTH,SYSTEM,ERROR}`,
   `ActivitySeverity{SUCCESS,FAILURE,WARNING,INFO}` + `data class ActivityLogEntry(at,actor,kind,severity,
   description,location?)`.
2. `data/.../activitylog/ActivityLog.kt` (`@Singleton`): wraps the DAO — `record(entry)`,
   `page(offset, limit=30)`, `count()`, `clear()`; maps row↔domain; all on `Dispatchers.IO`; pruning
   (`deleteOlderThan(now−30d)` + `trimToMax(5000)`) on write.
3. `platform/activitylog/ActivityLogger.kt` (`@Singleton`, injected `Clock` + `ActivityLog` + an
   application-scoped coroutine scope): typed helpers that build the **exact English** descriptions
   (plan004 §3.1) + pick `kind`/`severity`/`actor` and persist via
   `appScope.launch(Dispatchers.IO) { runCatching { ... } }`. Helpers per plan004 §3.3 (`logCheckIn/Out`,
   `logQueuedOffline`, `logSyncing/Synced/SyncDropped`, `logActive/Inactive`, `logTrigger`, `logLocation`,
   `logAuth`, `logSystem`, `logWarning`, `logError`). Optionally a `verbose` constant gating high-frequency
   helpers (plan004 §3.4).
4. **JVM tests:** façade mapping (each helper → exact description + kind/severity/actor against a **fake
   `ActivityLog`**); **crash-proof** (a fake whose `record` throws never propagates out of any helper);
   store paging/prune behavior (fake DAO or in-memory).
**Do NOT:** call the logger from any flow yet (that is EP6/EP7); throw from any helper; touch `EvaluationLog`.
**Verify:** all suites green; façade + crash-proof tests pass. **Update:** tick EP5.

## EP6 — Instrument CORE activities (check-in/out + active/inactive)
**Goal:** the user's required activities are logged, by the right actor, with the right color.
**Context to load:** plan004 §3.4 (rows: manual submit, auto use-case, FGS, scheduled pause); the sites in
§0.4.
**Do (add ONE `ActivityLogger` call per site; no logic/control-flow change):**
1. **Manual check-in/out** — `CheckViewModel.onSubmit`: success (~L1049–1064) → `logCheckIn/Out(USER, local,
   success=true)` (pick by `selectedAction`); other-error (~L1112–1121) → `success=false`; network
   (~L1084–1103) → `logQueuedOffline(USER,…)`; 401 (~L1084) → `logError("Session expired — sign in again.")`.
2. **Automatic check-in/out** — `RunAutomaticActivitiesUseCase`: Submitted (~L83) → `logCheckIn/Out(SYS,
   local, success=true)`; network/enqueue (~L43–59, L84–99) → `logQueuedOffline(SYS,…)`.
3. **Active/Inactive (FGS)** — `AutoActivityForegroundService.onCreate` (~L38) → `logActive("Background
   service started.")`; `onDestroy` (~L77) → `logInactive("Background service stopped.")`.
4. **Active/Inactive (scheduled pause)** — `BackgroundCheckOrchestrator` pause→active (~L194–198) →
   `logActive("Scheduled pause ended.")`; active→pause (~L181–188) → `logInactive("Scheduled pause
   started.")`.
**Do NOT:** change any result, branch, or order at these sites; block the caller (logging is off-thread);
duplicate-log the same event.
**Verify:** all suites green; extend a VM/use-case unit test to assert a successful and a failed manual +
automatic submit each call the logger with the expected entry (fake logger), and that a throwing logger
does not change the check-in result. **Update:** tick EP6.

## EP7 — Instrument the EXTENDED background suite
**Goal:** the complete suite (plan004 §3.4) so the log explains anything that happens in the background,
even when locked.
**Context to load:** plan004 §3.4 (all remaining rows); §0.4 sites.
**Do (one call per site; no logic change):**
1. **Triggers/outcomes** — `BackgroundCheckOrchestrator.runOnceLocked`: `logTrigger("Background evaluation
   (<TRIGGER>).")` at entry; `NO_ACTION`/`SKIP`/`PAUSED`/`TOGGLE_OFF` → `logSystem(...)`(INFO/WARNING).
2. **Geofence** — `GeofenceBroadcastReceiver.onReceive` (**goAsync**) → `logLocation("Entered/Exited
   geofence <local>.")`; `GeofenceManager` register → `logSystem("Geofences registered (<n>).")` (optional).
3. **Location** — `CaptureLocationUseCase`/capture: fix → `logLocation("Location fixed (±Xm) → <local|
   unknown>.")`; accuracy too low (`CheckViewModel.captureLocation` ~L481–493) → `logWarning("Location
   accuracy too low …")`.
4. **Offline/sync** — `OfflineCheckQueue.enqueue` → `logQueuedOffline(...)`; `PendingCheckReplayer`
   (~L36–110) → `logSyncing(n)` / `logSynced(...)` / `logSyncDropped(...)`; `SyncPendingChecksWorker` →
   `logSyncing(n)`.
5. **Auth** — `CheckViewModel.attemptLogin` (~L277–324) → `logAuth("Signed in.")`/`logError("Sign-in
   failed.")`; `BackgroundCheckOrchestrator.attemptSilentRelogin` (~L414–436) → `logAuth("Session
   refreshed.")` / `logError("Re-authentication required.")`.
6. **Lifecycle/system** — Application start → `logSystem("App started.")`; `BootReceiver` (**goAsync**) →
   `logSystem("Device rebooted — Checking re-armed.")`; `AutoActivityWatchdogWorker` → healthy/restart
   `logSystem(...)`; `CheckViewModel.onAutomaticActivitiesToggled` (~L1256) → `logSystem("Automatic
   activities enabled/disabled by user.")`; `CheckViewModel.onLocationPermissionStateChanged` (~L540) →
   `logWarning("Location permission revoked — auto disabled.")`; (optional) battery/SSE/exact-alarm rows
   behind the `verbose` flag.
**Do NOT:** change control flow; let a receiver die before its row is written (use `goAsync()`); spam
duplicate rows.
**Verify:** all suites green; spot-check unit tests (where a use-case/VM seam exists) assert the right entry
is recorded; manual reasoning notes that receiver `goAsync()` writes complete. **Update:** tick EP7.

## EP8 — UI: Settings row + paged Activities dialog
**Goal:** the visible feature — one localized row → an English-only, day-grouped, colored, paged table.
**Context to load:** plan004 §3.5; `SettingsDialog.kt`, `CheckUiState.kt`, `CheckViewModel.kt`,
`CheckScreen.kt`, `presentation/theme/Color.kt`, `EvaluationLogDialog.kt` (style).
**Do:**
1. **Theme:** add two tokens in `presentation/theme/Color.kt` — a warning **orange** and an info **dark
   blue** (reuse `CheckingSuccess`/`CheckingErrorVivid` for green/red).
2. **i18n:** add `settings.activitiesLabel` to all 6 dicts ("Atividades"/"Activities"/translated). Re-run
   `I18nTest`. **No other localized strings** (table is English).
3. **State:** `CheckUiState.kt` — add `CheckDialog.Activities` + `activityEntries`, `activityNextOffset`,
   `activityCanLoadMore`, `isActivitiesLoading`.
4. **VM:** `openActivitiesDialog()` (reset + load page 0 of 30, set `activityCanLoadMore`),
   `loadMoreActivities()` (append next 30, advance offset, guard re-entrancy), optional `clearActivities()`.
5. **Settings row:** `SettingsDialog.kt` — add `SettingsRow(icon = <History/ListAlt>, label =
   t("settings.activitiesLabel", null), onClick = onActivitiesClick)` (+ `onActivitiesClick` param,
   defaulted). `CheckScreen.kt` wires `onActivitiesClick = { vm.dismissDialog(); vm.openActivitiesDialog() }`
   and renders `CheckDialog.Activities -> ActivityLogDialog(...)`.
6. **Dialog:** new `presentation/settings/activitylog/ActivityLogDialog.kt` — back arrow + title "Activities"
   (English literal); `LazyColumn` over `state.activityEntries` **grouped by local date** (date header per
   day); rows **Time(`HH:mm:ss`) · Who(`user`/`sys`) · Activity(kind text) · Description**; text color by
   `severity` (green/red/orange/dark-blue); **paging** (when nearing the end + `activityCanLoadMore` →
   `vm.loadMoreActivities()`, trailing loading row); empty → "No activity recorded yet."; newest day & row
   first; optional Refresh/Clear.
**Do NOT:** localize the table; auto-stream (snapshot-at-open is fine); change other Settings rows.
**Verify:** all suites + `I18nTest` green; `ActivityLogDialog` smoke compiles (device-pending run). Manual
device smoke: Settings → Activities shows the day-grouped colored table; a manual check-in adds a `user`
row; auto runs add `sys` rows. **Update:** tick EP8.

---

# PHASE T — verification suite

> Runs after EP0–EP8. Goal: prove both features are correct and robust, and that **every existing flow is
> untouched**. Default everything to LOCAL.

## TP0 — Test harness, recipes, prod-safety
**Goal:** confirm every harness the suite relies on. **No code change.**
**Do:** confirm (and record in §4): Kotlin JVM unit tests (`mockk` + `StandardTestDispatcher` + `runTest`,
template `CheckViewModelForegroundTest`); Room **instrumented** DAO tests (`Room.inMemoryDatabaseBuilder`,
`androidTest`); Compose smoke (`createComposeRule`, template `EvaluationLogDialogSmokeTest`); `I18nTest`;
backend `prod_e2e` guard (`CHECKING_E2E_PROD`). Confirm the default suites run offline and green.
**Verify:** recipes recorded; default suites green. **Update:** tick TP0.

## TP1 — Problem 1: history exhaustive
**Goal:** the dialog shows the right action's rows **with location**, and fails loudly.
**Tests:**
1. **VM (mocked `CheckRepository`):** Success → `historyDialogEntries` filtered by action (check-ins under
   CHECKIN, check-outs under CHECKOUT), **including non-null `local`**; `historyDialogError == false`.
   Failure → `historyDialogError == true`, entries empty. `retryHistoryDialog()` re-calls the repo for the
   current action.
2. **Mapper (`CheckHistoryMapperTest`):** `local` (non-null + null) survives DTO→domain.
3. **Smoke (`CheckHistoryDialogSmokeTest`, compile-gated):** error+retry state distinct from empty; the
   **Atividade** column shows the right label per action; an entry **with** a location renders that location
   in the **Local** column (null → "-").
4. **Guarded prod read (EP1 test):** with the opt-in (post-deploy), `GET /check/history` items carry
   non-null `local`.
**Verify:** green (prod test skipped by default). **Update:** tick TP1.

## TP2 — Room store/DAO exhaustive
**Goal:** persistence, paging in blocks of 30, and retention are correct.
**Tests (in-memory Room):** insert/order; `pageNewestFirst(30, 0)` then `(30, 30)` disjoint & newest-first
(seed > 60); `count()`; `deleteOlderThan(now−30d)` removes only old; `trimToMax(5000)` keeps the newest
5,000; `clearAll()`; `ActivityLog.record`→`page` round-trip; pruning enforces **30 days OR 5,000** on write.
**Verify:** green (device-pending where instrumented). **Update:** tick TP2.

## TP3 — ActivityLogger + instrumentation exhaustive
**Goal:** every activity maps correctly and logging can never break a flow.
**Tests:**
1. **Mapping (JVM, fake `ActivityLog`):** each helper → exact English description + correct
   `kind`/`severity`/`actor` (cover: check-in/out ok+fail user+sys; active/inactive service+pause;
   trigger; location ok+accuracy; sync queued/synced/dropped; auth ok+fail+reauth; boot; watchdog;
   toggle; permission). Assert the **required exact strings** from §0.5.
2. **Crash-proof (JVM):** a fake whose `record` throws never propagates out of any helper; and a thrown
   logger in `onSubmit`/the use-case does NOT change the check-in/out result (end-to-end).
3. **Instrumentation seams (JVM where available):** a successful + failed manual submit and a successful +
   failed automatic run each record exactly one entry with the right actor.
4. **Verbose flag:** with verbose off, the high-frequency optional rows are muted; core rows always log.
**Verify:** green. **Update:** tick TP3.

## TP4 — Activities UI
**Goal:** the visible table matches the spec.
**Tests (Compose smoke, compile-gated; colors device-visual → device-pending per plan003 TP5):** entries
across two days render two **date headers** in newest-first order; columns Time/Who/Activity/Description
present; a SUCCESS row is green, FAILURE red, WARNING orange, INFO dark blue (assert text/semantics);
scrolling past the first 30 triggers `loadMoreActivities`; empty state renders; (optional) Clear empties.
**Verify:** `compileDebugAndroidTestKotlin` green; on-device run ×2 via `am instrument` else device-pending.
**Update:** tick TP4.

## TP5 — Master non-regression + coverage-matrix sign-off
**Goal:** one place proving every requirement maps to a green test and nothing regressed.
**Steps:**
1. Build the coverage matrix (each row → ≥1 test): history filter-by-action (TP1) · history **location**
   (TP1) · history error/retry (TP1, EP2) · Atividade column + i18n (TP1, EP3) · backend bundle/deploy
   (EP1) · Room paging-30 (TP2) · retention 30d/5,000 (TP2) · logger descriptions/colors/actor (TP3) ·
   crash-proof (TP3) · each instrumented activity ok/fail (TP3, EP6/EP7) · active/inactive incl. pause &
   boot (TP3) · Settings row + paged dialog + grouping + colors (TP4, EP8) · `settings.activitiesLabel` ×6
   (EP8) · English-only table (TP4).
2. Run the full suites and snapshot counts: `./gradlew compileDebugKotlin compileDebugAndroidTestKotlin
   testDebugUnitTest`; backend `pytest` (prod tests skipped). Confirm **Protected behaviors (Section 4)**
   all still pass; Kotlin count ≥ baseline + new, 0 failures.
3. List acknowledged **non-automated cells**: on-device colors/`am instrument` runs (device-pending); the
   guarded prod `/check/history` read (pending the human-gated deploy + migration `0078`); the AAB publish.
**Verify:** no uncovered requirement; suites green. **Update:** tick TP5; write the final matrix into §4.

---

## 6. Rollout (all human-gated — do NOT do unprompted)
1. **Backend deploy** of the change-D bundle (migration `0078` + `local` write + `/check/history` +
   schemas) via the existing pending root `main` push — runs migration `0078` in prod. **This is what makes
   Problem 1's data + location appear.** The app already calls the endpoint.
2. **AAB** rebuild + Play publish for the Kotlin changes (history error/retry + Atividade column + the
   Activities log), versioned per the existing release process (`kotlin_play_publishing`). Separate,
   human-approved step.
