# plan004 — Fix empty check-in/out history + add an in-app "Activities" debug log

> **Scope:** the Kotlin app (`checking_kotlin/`). Problem 1 ALSO needs a one-line backend reality check
> (the history endpoint must be deployed — see §2). Problem 2 is Kotlin-only.
>
> **Prime directive (read first):** the app is **in production and working very well**. Every change here
> is **purely additive**. Do NOT alter check-in/check-out, the situation engine, the background
> orchestrator's decisions, sync, transport, accident mode, offline replay, auth, or any existing screen
> behavior. The two features below must not be able to break an existing flow — in particular, the new
> activity logger (Problem 2) must be **fire-and-forget and never throw** into a check-in path.
>
> Model this plan's discipline on `docs/plans/plan003.md`: additive-first, feature-flag/▸safe seams, all
> six i18n dictionaries touched together, every change covered by a green test, nothing pushed/deployed
> without explicit human approval.

---

## 0. Golden rules (apply to every step)

1. **Existing flows are sacred.** The only new behaviors are: (1) the history dialog shows data + an
   error state, and (2) a new read-only "Activities" log + its dialog. Nothing else changes.
2. **Additive-first.** New files/classes/columns/keys over edits to working code. Instrumentation calls
   are added at existing success/failure sites; they must not change control flow or results.
3. **The activity logger must be crash-proof.** Wrap every `ActivityLogger.log(...)` call so a logging
   failure (serialization, disk) is swallowed and never propagates into a check-in/out, the FGS, or the
   orchestrator. Logging is best-effort diagnostics, never a correctness dependency.
4. **The Activities table is ENGLISH-ONLY** (explicit product decision). Only the Settings *row label*
   ("Atividades"/"Activities") is localized; the table content (headers, "Who", activity names,
   descriptions) is hardcoded English.
5. **Touch all 6 i18n dicts together** for any localized string (Problem 1 dialog + the Activities row
   label) and re-run `I18nTest`.
6. **One step = one compilable, test-passing increment.** Run `./gradlew compileDebugKotlin
   compileDebugAndroidTestKotlin testDebugUnitTest` after each.
7. **Do NOT commit/push/branch or publish an AAB** unless the human asks. The backend deploy in §2 is
   human-gated (pushing root `main` deploys PRODUCTION).
8. **Keep the baseline green:** Kotlin `testDebugUnitTest` is currently **207/0** (incl. `I18nTest` 17/0);
   add zero failures.

---

## 1. Investigation summary (what is already true in the code)

### 1.1 Problem 1 — history dialog wiring (all client-side parts already exist and are correct)
- Main screen card: `presentation/components/HistoryCard.kt` — the two tappable cells "ÚLTIMO CHECK-IN" /
  "ÚLTIMO CHECK-OUT" (labels `history.lastCheckinLabel` / `history.lastCheckoutLabel`) fire
  `vm::openCheckinHistory` / `vm::openCheckoutHistory`. The cell text comes from
  `HistoryState.lastCheckinAt` / `lastCheckoutAt` (a single timestamp each) → **this summary works today**.
- `CheckViewModel.openCheckHistoryDialog(action)` (~L681–708): sets `dialogOpen = CheckDialog.History`,
  `historyDialogEntries = emptyList()`, `isHistoryDialogLoading = true`, then calls
  `checkRepository.getHistory(chave)` and, on success, `historyDialogEntries = r.data.filter { it.action ==
  action }`; on failure sets `historyDialogError = true`.
- `CheckRepositoryImpl.getHistory` → `CheckApi.getHistory` → `GET check/history` →
  `WebCheckHistoryListResponseDto.items` → `CheckHistoryEntry(action, projeto, local, time, informe)`.
  Serialization is correct (`data/dto/CheckDtos.kt`: `@SerialName("checkin")/("checkout")`,
  `@SerialName("normal")/("retroativo")`).
- `presentation/components/CheckHistoryDialog.kt` renders a table **Data | Hora | Local** from `entries`;
  on empty it shows `history.empty`. **It has NO error parameter** — params are `action`, `entries`,
  `isLoading`, `langCode`, `onDismiss`, `t`.
- `CheckUiState` has `historyDialogEntries`, `isHistoryDialogLoading`, **`historyDialogError`** (set by the
  VM but **not consumed by the dialog**).

### 1.2 Problem 1 — ROOT CAUSE (confirmed)
- Backend `GET /api/web/check/history` exists in `sistema/app/routers/web_check.py:892`
  (`get_web_check_history` → `list_checking_history(...)`, newest-first, with location) and is correct.
- **But it is NOT deployed.** `git show HEAD:sistema/app/routers/web_check.py | grep -c "check/history"`
  → **0**, while `"check/state"` → **1**. The endpoint lives only in the uncommitted working tree (it is a
  plan002 "change D" addition that was never committed/pushed). `/check/state` (older, deployed) is why the
  HistoryCard summary works.
- The **released app `4d6458b` already calls `/check/history`**. Against production it gets **404** →
  `safeApiCall` → `AppResult.Failure` → `historyDialogError = true` → but the dialog ignores that field →
  it silently shows the **"empty"** state. **That is the bug the tester sees.**
- **Net:** Problem 1 is a **deployment gap** (endpoint not live) **compounded by a client UX gap** (a load
  failure is indistinguishable from "no history"). A Kotlin-only change cannot produce data without the
  endpoint; the endpoint cannot be debugged from the field without the client surfacing the error.

### 1.3 Problem 2 — existing diagnostics to learn from / reuse
- There is already a real-time in-memory diagnostics ring buffer for the orchestrator:
  `platform/background/diagnostics/EvaluationLog.kt` (`EvaluationEntry`, `EvaluationOutcome`, 50-entry
  `ArrayDeque`, `record()`/`snapshot()`), rendered by
  `presentation/settings/diagnostics/EvaluationLogDialog.kt` (LazyColumn, `HH:mm:ss` formatter,
  color-by-outcome). It is **in-memory only** (lost on process death) and **outcome-centric** — it does NOT
  track manual submissions, the user-vs-system actor, or fine-grained activity types. It is a good
  reference but **not a drop-in** for the user-facing Activities log (see §3.2 decision).
- Activity sites that must be instrumented already exist and are well-defined (see §3.4).
- Clock/format: `core/time/Clock` (`now(): Instant`, `nowInZone(zone)`), `DateTimeFormatter` as in
  `EvaluationLogDialog`.
- Settings wiring pattern: `presentation/components/SettingsDialog.kt` `SettingsRow(icon,label,onClick)`
  → `CheckScreen` `onXxxClick = { vm.dismissDialog(); ... }` / `vm.openXxxDialog()` →
  `CheckUiState.dialogOpen = CheckDialog.Xxx` → `CheckScreen` renders the dialog. (Same pattern the
  `EvaluationLog`/`Manual`/`About` entries use.)

---

## 2. Problem 1 — "ÚLTIMO CHECK-IN / CHECK-OUT" shows empty history

**Goal:** tapping a cell shows that action's history (check-ins under "último check-in", check-outs under
"último check-out"); each row shows **date, activity, and location**; a load failure shows a clear error
(not a silent "empty").

### 2.1 Step P1-A — Backend: deploy the full "change D" history bundle (REQUIRED; human-gated)
History **AND its location** depend on the same un-deployed "change D" bundle (all in the working tree,
**none in HEAD**). The deploy must include **all four** pieces, or the list is empty / `local` is null:
1. **Migration `0078_add_local_to_checkinghistory`** — adds the `CheckingHistory.local` column
   (`alembic/versions/0078…`). Confirmed NOT in HEAD (`git show HEAD:…0078… ` → absent). **Without this
   migration there is no location column to read.**
2. **Write path persists location:** `services/checking_history.py:25 record_checking_history(... local=local)`
   (writes `CheckingHistory.local` on every check-in/out).
3. **Endpoint:** `routers/web_check.py:892 get_web_check_history` (returns `local=row.local`, newest-first)
   + `services/checking_history.py:68 list_checking_history`.
4. **Schemas:** `schemas.py:4186 WebCheckHistoryItem` (has `local`) / `:4196 WebCheckHistoryListResponse`.

**Action:** include all four in the next backend commit + push to root `main` (deploys production) and run
migration `0078` in prod. This is the ONLY thing that makes the list non-empty and the location present.
**This rides the existing plan002/plan003 pending push** — same human approval; *do not push without the
human's explicit go-ahead.* No new backend code is needed; this step is "ensure it all ships + migrates".

> **Note on old rows:** rows recorded BEFORE the deploy were written without `local` → they will show "-"
> in the Local column (expected). Check-ins/outs AFTER the deploy carry their location.
>
> Verify after deploy (read-only, guarded): `GET /api/web/check/history?chave=TEST` with an authenticated
> session returns `{"items":[ … "local": "<area>" … ]}` — i.e. the items include **non-null `local`** for a
> post-deploy event (reuse the `prod_e2e` guard from `tests/test_e2e_prod_user_approval.py`). Until
> deployed, the app's history stays empty by design.

### 2.2 Step P1-B — Client: surface the error state (stop masking failures as "empty")
Make a failed load visibly distinct from a genuinely empty history, so this class of problem is never
again invisible in the field.
- `CheckHistoryDialog.kt`: add an `isError: Boolean` param (and an `onRetry: () -> Unit`). Render three
  states: **loading** (existing spinner), **error** ("Couldn't load history — tap to retry", neutral/amber
  + retry button), **empty** (existing `history.empty`), **data** (table).
- `CheckScreen.kt`: pass `isError = state.historyDialogError` and `onRetry = { vm.retryHistoryDialog() }`.
- `CheckViewModel`: add `retryHistoryDialog()` that re-invokes `openCheckHistoryDialog(historyDialogAction)`
  (or refactor the load into a private `loadHistoryDialog(action)` reused by open + retry). No change to the
  existing success path.

### 2.3 Step P1-C — Client: show date + activity + location per the spec
The spec asks each row to show **date, activity, location**. Today the table is **Data | Hora | Local**
(date/time/location) with the activity only implied by which cell was tapped.
- **Location (required): already rendered, keep it.** `CheckHistoryDialog` already shows the **`Local`**
  column from `entry.local` (null → "-"); `CheckHistoryEntry.local` ← DTO `local` ← backend `row.local`.
  **No client change is needed for location** — it becomes populated automatically once the change-D bundle
  (§2.1, esp. migration 0078 + the `local` write) is deployed. **Do not remove the Local column.**
- Add an **"Atividade"** column so each row reads **Data | Hora | Atividade | Local** (keep Hora — useful).
  The activity value is derived from `entry.action` (`CHECKIN` → check-in label, `CHECKOUT` → check-out).
- Add i18n keys to **all 6 dicts**: `history.colActivity` (column header), `history.activityCheckin`,
  `history.activityCheckout`, `history.loadError`, `history.retry`. (Existing `history.empty`,
  `history.dialogTitleCheckin/Checkout`, the Data/Hora/Local headers stay.)
- Re-run `I18nTest`.

### 2.4 Files (Problem 1)
| File | Change |
|---|---|
| `sistema/app/routers/web_check.py` + `schemas.py` + `services/checking_history.py` | **No edit** — already implemented; just must be committed + deployed (P1-A). |
| `presentation/components/CheckHistoryDialog.kt` | + `isError`/`onRetry` params; error + retry rendering; + Atividade column. |
| `presentation/check/CheckScreen.kt` | pass `isError`/`onRetry`; (no other change). |
| `presentation/check/CheckViewModel.kt` | + `retryHistoryDialog()` (reuse the existing load). |
| `i18n/dictionaries/{Pt,En,Zh,Ms,Id,Tl}.kt` | + `history.colActivity`, `activityCheckin`, `activityCheckout`, `loadError`, `retry` (6 langs). |

### 2.5 Tests (Problem 1)
- **VM unit test** (`CheckViewModel*` test, mocked `CheckRepository`): `getHistory` Success → entries
  filtered by action populate `historyDialogEntries`, `historyDialogError == false`; Failure →
  `historyDialogError == true`, entries empty; `retryHistoryDialog()` re-calls the repo. (Reuse the
  `StandardTestDispatcher` + `mockk` pattern.)
- **Instrumented smoke** (extend `androidTest/.../CheckHistoryDialogSmokeTest.kt`): error state renders the
  error + retry (distinct from empty); the Atividade column renders the right label for CHECKIN vs CHECKOUT;
  **an entry WITH a location renders that location string in the Local column** (and a null location still
  renders "-"). (Device-pending if no device — compile-only, like plan003 TP5.) The existing smoke already
  checks the Local column — extend it to assert a real, non-"-" value.
- **`I18nTest`**: the 5 new keys resolve in all 6 languages.
- **`CheckHistoryMapperTest`** already asserts `local` survives DTO→domain mapping — keep green; add a case
  with a non-null `local` if not present.
- **Backend** (rides §2.1 deploy verification): a `prod_e2e` read asserts `GET /check/history` items carry
  a **non-null `local`** for a post-deploy event; the existing local-suite test for `record_checking_history`
  confirms `CheckingHistory.local` is persisted on check-in/out.

### 2.6 Risks / notes
- **Primary risk:** treating this as client-only. Without P1-A the list stays empty. The plan makes the
  deploy explicit and the client honest about failures.
- The `_require_matching_authenticated_web_user` session requirement is already satisfied by the app's
  cookie jar (the same session that makes `/check/state` work), so no auth change is needed once deployed.

---

## 3. Problem 2 — "Activities" real-time debug log (Settings → Activities)

**Goal:** a read-only, English-only, day-grouped table to diagnose missed automatic actions (e.g. the
tester's missing Friday check-out). Columns: **Time** (`hh:mm:ss`) · **Who** (`user`/`sys`) · **Activity**
(check-in / check-out / active / inactive / error) · **Description**. Colors: success = green, failure =
red, warning = orange, info-only = dark blue. Grouped by day (date headers).

### 3.1 Behavior spec (from the request, plus useful extras)
Activity → Description (English, exact for the required cases; extras follow the same pattern):
| Activity | Severity/Color | Description |
|---|---|---|
| check-in (ok) | success / green | `Check-in at <location>.` |
| check-out (ok) | success / green | `Check-out at <location>.` |
| check-in (fail) | failure / red | `Check-in failed at <location>.` |
| check-out (fail) | failure / red | `Check-out failed at <location>.` |
| active | info / dark blue | `Checking is now active.` |
| inactive | info / dark blue | `Checking is now inactive.` |
| error | failure / red | `<short reason>` (e.g. `Session expired — sign in again.`) |
| *(extra)* check-in/out queued offline | warning / orange | `Check-in queued (offline) at <location>.` |
| *(extra)* offline event synced | success / green | `Queued check-in synced at <location>.` |
| *(extra)* location permission lost | warning / orange | `Location permission revoked.` |
| *(extra)* accuracy too low | warning / orange | `Location accuracy too low — manual fallback.` |
| *(extra)* skipped (no movement) | info / dark blue | `Auto-check skipped (no movement).` |

> "active/inactive" cover BOTH the foreground-service start/stop AND scheduled-pause end/begin (a pause is
> a sleep; resume is a wake) — both map to `active`/`inactive` so the user sees one consistent vocabulary.

### 3.2 Decisions (CONFIRMED 2026-06-21)
1. **Persistence: YES, persisted** (survives process death / FGS restart / reboot) — required to debug a
   past day ("last Friday").
2. **Retention: 30 days OR 5,000 entries, whichever is smaller**, pruned on write. **Read/render in pages
   of 30** (lazy "load more" on scroll — see §3.4 UI).
3. **Store: a NEW dedicated store** (`activitylog/`), independent of `EvaluationLog` (left untouched).
4. **Scope: the COMPLETE background suite** — log *everything relevant that happens while the app runs,
   including in the background with the phone locked* (boot, service start/stop, watchdog, every
   orchestrator trigger + outcome, geofence enter/exit, location fixes, scheduled pause, offline
   queue/replay/connectivity, auth/reauth, permission/battery changes, exact-alarm wakes, SSE, errors).
   Full table in §3.3.

> **New dependency (decided by the above):** the existing persistence (a JSON blob in DataStore, as the
> offline queue uses) does NOT fit a 5,000-row, append-heavy, paged, multi-writer log — rewriting a 5,000-
> item JSON list on every background event would be slow and race-prone. **Add Room** (a small, contained,
> standard dependency: `room-runtime` + `room-ktx` + `room-compiler` via the KSP the app already uses) and
> a dedicated single-table DB for the activity log. This is the smallest change that satisfies §3.2.1–2
> with safe concurrent writes from the FGS/receivers/workers. (minSdk 24 supports Room fully.)

### 3.2b Activity vocabulary (the "Activity" column)
Keep the four required values **check-in, check-out, active, inactive, error**, and ADD a small controlled
set so the complete background suite stays readable + filterable (color still comes from *severity*, not
kind):

| `ActivityKind` (column text) | meaning |
|---|---|
| `check-in` / `check-out` | attendance recorded (or attempted) — by user or system |
| `active` / `inactive` | engine woke / slept (service start/stop, scheduled-pause end/begin, boot re-arm) |
| `trigger` | a background evaluation fired (timer / geofence / foreground / alarm) |
| `location` | a GPS fix / geofence crossing / accuracy result |
| `sync` | offline queue: saved / syncing / synced / dropped |
| `auth` | sign-in / silent re-auth / session expired |
| `system` | lifecycle: boot, watchdog, service, exact-alarm scheduling, SSE, toggle on/off |
| `error` | any failure not covered above |

### 3.3 Architecture (new, additive — Room-backed)
**Model** `domain/model/ActivityLogEntry.kt` (or `activitylog/`):
```
enum class ActivityActor { USER, SYS }
enum class ActivityKind { CHECK_IN, CHECK_OUT, ACTIVE, INACTIVE, TRIGGER, LOCATION, SYNC, AUTH, SYSTEM, ERROR }
enum class ActivitySeverity { SUCCESS, FAILURE, WARNING, INFO }   // drives row color only
data class ActivityLogEntry(
    val at: Instant, val actor: ActivityActor, val kind: ActivityKind,
    val severity: ActivitySeverity, val description: String, val location: String? = null,
)
```
**Persistence (Room)** `data/local/activitylog/`:
- `@Entity("activity_log")` `ActivityLogRow(id Long PK autogen, atEpochMs Long [indexed], actor, kind,
  severity, description, location?)` — store enums as their `name` strings (stable, simple).
- `@Dao ActivityLogDao`: `insert(row)`; `pageNewestFirst(limit, offset): List<ActivityLogRow>`
  (`ORDER BY atEpochMs DESC, id DESC LIMIT :limit OFFSET :offset`); `count(): Int`;
  `deleteOlderThan(epochMs)`; `trimToMax(max)` (`DELETE … WHERE id NOT IN (SELECT id … ORDER BY atEpochMs
  DESC, id DESC LIMIT :max)`); `clearAll()`. (Key-set paging by `(atEpochMs,id)` is more robust than
  OFFSET while new rows arrive during scroll; OFFSET is acceptable for a debug log — implement key-set if
  cheap.)
- `@Database(version=1) CheckingActivityDatabase` (a NEW, dedicated DB — does not touch any existing
  storage). Provide via a Hilt module (`@Singleton`), all access on `Dispatchers.IO`.
- **Pruning** runs inside the same IO write as `insert` (or every Nth insert): `deleteOlderThan(now − 30d)`
  then `trimToMax(5000)` → enforces §3.2.2.
**Store** `data/.../activitylog/ActivityLog.kt` (`@Singleton`): wraps the DAO — `record(entry)`,
`page(offset, limit = 30): List<ActivityLogEntry>`, `count()`, `clear()`; maps row↔domain.
**Façade** `ActivityLogger.kt` (`@Singleton`; injected `Clock` + `ActivityLog` + an `@ApplicationScope`
coroutine scope): typed helpers that build the **English** description, pick `kind`/`severity`, and persist
**off the caller's thread** (`appScope.launch(Dispatchers.IO) { runCatching { … } }`) so a check-in/FGS/
receiver is never blocked or broken by logging. Helpers (non-exhaustive):
`logCheckIn/Out(actor, local, success)`, `logQueuedOffline(actor, kind, local)`, `logSyncing(n)`,
`logSynced(kind, local)`, `logSyncDropped(kind)`, `logActive(reason)`, `logInactive(reason)`,
`logTrigger(name)`, `logLocation(message, local, severity)`, `logAuth(message, severity)`,
`logSystem(message)`, `logWarning(message)`, `logError(message)`.
> **Crash-proofing (golden rule 3):** every helper is fully `runCatching`-wrapped. **BroadcastReceivers**
> (`BootReceiver`, `GeofenceBroadcastReceiver`) must keep the process alive until the row is written — use
> `goAsync()`/`PendingResult` (or the receiver's existing bounded coroutine) so a locked-phone event is
> persisted before the receiver returns. Workers/FGS already run in coroutine scopes; await the insert
> there so it isn't cut off when the work finishes.
**Hilt:** inject the logger by constructor where the graph is available (VM, use-cases, repositories); for
components without direct graph access, obtain it via an `@EntryPoint` exactly as the background components
get their current dependencies.

### 3.4 Instrumentation points — the COMPLETE background suite
Add a single `ActivityLogger` call at each site below (no logic/control-flow change). Organized by
component so coverage is auditable. **Actor** is structural: `CheckViewModel.onSubmit` ⇒ `USER`; everything
in the orchestrator / use-cases / receivers / workers / service ⇒ `SYS`. Severity → color per §3.1.

**App + engine lifecycle (`system`/`active`/`inactive`):**
| Event | Where (file:~line) | Call / description |
|---|---|---|
| App process start | `Application.onCreate` (the `@HiltAndroidApp` class) | `logSystem("App started.")` (INFO) |
| Device reboot → re-arm | `BootReceiver` (onReceive; use `goAsync()`) | `logSystem("Device rebooted — Checking re-armed.")` (INFO) |
| Engine started (FGS) | `AutoActivityForegroundService.onCreate` (~L38) | `logActive("Background service started.")` |
| Engine stopped (FGS) | `AutoActivityForegroundService.onDestroy` (~L77) | `logInactive("Background service stopped.")` |
| User toggled auto ON/OFF | `CheckViewModel.onAutomaticActivitiesToggled` (~L1256) | `logSystem("Automatic activities enabled/disabled by user.")` |
| Watchdog ran / restarted FGS | `AutoActivityWatchdogWorker.doWork` | healthy → `logSystem("Watchdog check: service healthy.")`; restart → `logSystem("Watchdog restarted the background service.")` (WARNING) |

**Every orchestrator run — trigger + outcome (`trigger`/`check-in`/`check-out`/`active`/`inactive`):**
| Event | Where (`BackgroundCheckOrchestrator.runOnceLocked`, ~line) | Call |
|---|---|---|
| Evaluation fired | entry (~L148), with `OrchestratorTrigger` | `logTrigger("Background evaluation (TIMER/GEOFENCE/FOREGROUND/ALARM).")` (INFO) |
| Toggle off at run | (~L151–167) | `logSystem("Automatic activities are OFF.")` (WARNING) |
| Scheduled pause active | (~L170–199) | begin: `logInactive("Scheduled pause started.")`; end: `logActive("Scheduled pause ended.")` |
| Skip (no movement) | (~L207–217) | `logSystem("Auto-check skipped (no movement).")` (INFO) |
| Submitted check-in/out | (~L242–257; `AutoActivitiesResult.Submitted`) | `logCheckIn/Out(SYS, local, success=true)` |
| No action needed | (~L242–257; NoAction) | `logSystem("No action needed (already checked in/out).")` (INFO) |
| Network error | (~L242–257; NetworkError) | `logCheckIn/Out(SYS, local, success=false)` / see offline below |

**Auto-activity engine + location (`check-in`/`check-out`/`location`/`sync`):**
| Event | Where (`RunAutomaticActivitiesUseCase` / `CaptureLocationUseCase`, ~line) | Call |
|---|---|---|
| Not configured | (~L37–38) | `logSystem("No active project — skipped.")` (WARNING) |
| Location fix obtained | capture success (~L40–63) | `logLocation("Location fixed (±Xm) → <local|unknown>.")` (INFO) |
| Accuracy too low | (capture ACCURACY_TOO_LOW) | `logLocation("Location accuracy too low (±Xm).", WARNING)` |
| Network during capture → raw queued | (~L43–59) | `logQueuedOffline(SYS, kind, local)` (WARNING) |
| Auto submit OK | (~L83) | `logCheckIn/Out(SYS, local, success=true)` |
| Auto submit network → decided queued | (~L84–99) | `logQueuedOffline(SYS, kind, local)` (WARNING) |

**Geofencing (`location`/`trigger`):**
| Event | Where | Call |
|---|---|---|
| Geofence enter/exit | `GeofenceBroadcastReceiver.onReceive` (use `goAsync()`) | `logLocation("Entered/Exited geofence <local>.")` (INFO) |
| Geofences (re)registered | `GeofenceManager.register*` | `logSystem("Geofences registered (<n>).")` (INFO, optional) |

**Offline queue + replay + connectivity (`sync`):**
| Event | Where | Call |
|---|---|---|
| Manual save offline | `CheckViewModel.onSubmit` network branch (~L1084–1103) | `logQueuedOffline(USER, kind, local)` (WARNING) |
| Connectivity sync run | `offline/SyncPendingChecksWorker.doWork` | `logSyncing(n)` (INFO) |
| Replay drain start | `offline/PendingCheckReplayer.drain` (~L36–41) | `logSyncing(n)` (INFO) |
| Queued event synced | `PendingCheckReplayer` success (~L52–94) | `logSynced(kind, local)` (SUCCESS) |
| Queued event dropped | `PendingCheckReplayer` permanent 4xx (~L106–110) | `logSyncDropped(kind)` (ERROR) |

**Auth / session (`auth`/`error`):**
| Event | Where | Call |
|---|---|---|
| Manual sign-in OK / fail | `CheckViewModel.attemptLogin` (~L277–324) | `logAuth("Signed in." , INFO)` / `logError("Sign-in failed.")` |
| Silent re-auth OK | `BackgroundCheckOrchestrator.attemptSilentRelogin` (~L414–427) | `logAuth("Session refreshed.", INFO)` |
| Re-auth needed/failed | (~L417–436) | `logError("Re-authentication required.")` |

**Manual user actions (`check-in`/`check-out`):**
| Event | Where (`CheckViewModel.onSubmit`, ~line) | Call |
|---|---|---|
| Manual check-in/out OK | success branch (~L1049–1064) | `logCheckIn/Out(USER, local, success=true)` (pick by `selectedAction`) |
| Manual check-in/out FAIL | other-error branch (~L1112–1121) | `logCheckIn/Out(USER, local, success=false)` |
| Manual auth-expired on submit | 401 branch (~L1084) | `logError("Session expired — sign in again.")` |

**Permissions / environment (`system`/`error`, all WARNING/ERROR):**
| Event | Where | Call |
|---|---|---|
| Location permission revoked | `CheckViewModel.onLocationPermissionStateChanged` (~L540–544) | `logWarning("Location permission revoked — auto disabled.")` |
| Battery not exempt / background-loc missing | `permissions/PermissionLadder.checkStatus` (on detection) | `logWarning("Background reliability degraded (battery/location).")` (optional, de-duped) |
| Exact-alarm wake scheduled/fired (pause) | orchestrator alarm scheduling (~L202/L279) | `logSystem("Scheduled wake set for <time>.")` (INFO, optional) |
| SSE live-updates connect/disconnect | `data/remote/sse/CheckEventStream` | `logSystem("Live updates connected/disconnected.")` (INFO, optional, may be noisy — gate behind a verbose flag) |

> Items marked *optional* are high-frequency/low-signal; include them but consider a simple internal
> "verbose" constant so they can be muted without code changes if the log gets noisy. The required core
> (check-in/out ok/fail, active/inactive, error) and the high-value background signals (triggers, geofence,
> location, offline, auth, pause, boot, watchdog) are always on.

### 3.5 UI (Settings row + paged dialog)
- **`presentation/components/SettingsDialog.kt`:** add one `SettingsRow(icon = <chosen>, label =
  t("settings.activitiesLabel", null), onClick = onActivitiesClick)` (+ the `onActivitiesClick: () -> Unit`
  param, defaulted). Place it in a sensible group (e.g. near the existing diagnostics/help). Suggested icon
  `Icons.Outlined.History` or `Icons.AutoMirrored.Outlined.ListAlt`. **The row label is the only localized
  string** for this feature.
- **`CheckUiState.kt`:** add `CheckDialog.Activities` to the `CheckDialog` enum, plus paged state:
  `activityEntries: List<ActivityLogEntry> = emptyList()`, `activityNextOffset: Int = 0`,
  `activityCanLoadMore: Boolean = false`, `isActivitiesLoading: Boolean = false`.
- **`CheckViewModel`:**
  - `openActivitiesDialog()` → resets the paged state, sets `dialogOpen = CheckDialog.Activities`, and loads
    the **first page of 30** (`ActivityLog.page(offset = 0, limit = 30)`); sets `activityNextOffset = 30`,
    `activityCanLoadMore = (returned.size == 30)`.
  - `loadMoreActivities()` → loads the **next 30** (`page(activityNextOffset, 30)`), appends to
    `activityEntries`, advances `activityNextOffset += returned.size`, updates `activityCanLoadMore`. Guard
    against re-entrancy with `isActivitiesLoading`.
  - (optional) `clearActivities()` → `ActivityLog.clear()` + reset.
  - `CheckScreen` wires `onActivitiesClick = { vm.dismissDialog(); vm.openActivitiesDialog() }`.
- **New `presentation/settings/activitylog/ActivityLogDialog.kt`** (style mirrors `EvaluationLogDialog`):
  scaffold with a back arrow + title "Activities" (English literal — table is English-only). Body =
  a **`LazyColumn`** over `state.activityEntries`, **grouped by local date** (`at` in
  `ZoneId.systemDefault()` → `toLocalDate()`): emit a sticky **date header** per day
  (e.g. "Fri, 20 Jun 2026") then its rows. Each row: **Time** (`HH:mm:ss`) · **Who** (`user`/`sys`) ·
  **Activity** (the `ActivityKind` text, e.g. `check-in`) · **Description**. Text color by `severity`:
  SUCCESS→green (`CheckingSuccess`), FAILURE→red (`CheckingErrorVivid`), WARNING→orange (new token),
  INFO→dark blue (new token). **Paging:** when the last visible item nears the end and
  `activityCanLoadMore`, call `vm.loadMoreActivities()` (a trailing loading row while `isActivitiesLoading`).
  Empty → "No activity recorded yet." Newest day first, newest row within a day first. (Snapshot-at-open
  semantics: it does not auto-stream new rows while open; an optional manual "Refresh" re-opens page 0.)
- **Theme:** add the two missing color tokens in `presentation/theme/Color.kt` (alongside
  `CheckingErrorVivid`/`CheckingSuccess`): a warning **orange** and an info **dark blue**. Reuse green/red.

### 3.6 i18n
- Add **only** `settings.activitiesLabel` to all 6 dicts ("Atividades" pt / "Activities" en / translated
  zh-ms-id-tl). Re-run `I18nTest`. **No other localized strings** — the table is English-only by design.

### 3.7 Tests (Problem 2)
- **`ActivityLogDao` instrumented test** (androidTest, in-memory `Room.inMemoryDatabaseBuilder`): insert
  ordering; `pageNewestFirst(30, 0)` then `(30, 30)` return disjoint, newest-first blocks (seed > 60 rows);
  `count()`; `deleteOlderThan(epochMs)` removes only old rows; `trimToMax(5000)` caps to the newest 5,000;
  `clearAll()` empties. (Room DAO tests require instrumentation context → androidTest, like other DB tests;
  compile-gated, run on device when available.)
- **`ActivityLog` store unit/instrumented test:** `record` → `page` round-trips through Room; pruning
  enforces **30 days OR 5,000** on write; `page(offset, 30)` paginates correctly.
- **`ActivityLogger` mapping unit test (JVM):** each helper produces the exact English description +
  correct `kind`/`severity`/`actor` against a **fake `ActivityLog`** (e.g. `logCheckOut(SYS, "Gate 3",
  success=false)` → kind=CHECK_OUT, severity=FAILURE, actor=SYS, description="Check-out failed at Gate
  3."; `logActive("Background service started.")` → kind=ACTIVE, severity=INFO). Includes a **crash-proof
  test**: a fake `ActivityLog` whose `record` throws does NOT propagate out of any helper.
- **Instrumentation unit tests (JVM):** extend the existing VM / use-case tests (mocked repo + a fake/mock
  `ActivityLogger`) to assert that a successful and a failed manual submit, and a successful and a failed
  automatic run, each call the logger with the expected entry; and that a thrown logger never changes the
  check-in/out result (crash-proof rule, end-to-end).
- **VM paging test (JVM):** `openActivitiesDialog()` loads page 0 (30) and sets `activityCanLoadMore`;
  `loadMoreActivities()` appends the next page and stops when a short page returns; re-entrancy guarded by
  `isActivitiesLoading`. Use a fake `ActivityLog` returning > 60 entries.
- **`ActivityLogDialog` smoke (androidTest, compile-gated):** entries across two days render two date
  headers in order; columns present; SUCCESS row green, FAILURE red, WARNING orange, INFO dark blue (assert
  text/semantics; exact color is device-visual — device-pending per plan003 TP5); empty state renders;
  scrolling past the first 30 triggers `loadMoreActivities`. Reuse `EvaluationLogDialogSmokeTest` style.
- **`I18nTest`:** `settings.activitiesLabel` resolves in all 6 languages.
- **Build:** adding Room must keep `compileDebugKotlin`/`testDebugUnitTest`/KSP green; verify the KSP Room
  processor is wired (the app already uses KSP for Hilt) and no Hilt/Room generation conflict.

### 3.8 Risks / notes
- **Crash-proofing is the top risk.** Logging sits inside check-in/out paths; a thrown exception there
  could break attendance. Every log call is `runCatching`-wrapped and tested for it.
- **Performance / disk.** Writes are tiny and bounded; persist asynchronously (don't block the FGS timer
  or the submit). Prune on write.
- **Process boundaries / concurrency.** The FGS, receivers, workers, and UI all share the process and can
  write concurrently. **Room** handles this safely (transactional, indexed); a singleton DB + `Dispatchers.IO`
  writes. (This is why Room is chosen over the offline queue's DataStore-JSON blob — see §3.2.)
- **New Room dependency.** Adds `androidx.room` (runtime+ktx) + the Room KSP compiler. Contained and
  standard; verify it coexists with the existing Hilt KSP processor and keeps the build green. DB starts at
  `version = 1` (no migration needed); it is a brand-new DB file, isolated from all existing storage.
- **Receiver lifetime.** A locked-phone broadcast (boot/geofence) must persist its row before the receiver
  dies → `goAsync()`/bounded await (golden rule 3 / §3.3). Missing this would drop exactly the
  locked-phone events the tester needs.
- **Log volume.** The "complete suite" can be chatty (every timer tick/trigger). 5,000 rows × ~30 days is
  bounded; the optional *verbose* flag (§3.4) mutes high-frequency low-signal rows if needed.
- **No PII beyond what the app already stores** (location names already shown in history); the log is
  local-only and never uploaded.

---

## 4. Verification (run after each step; full pass at the end)
- `cd checking_kotlin && ./gradlew compileDebugKotlin compileDebugAndroidTestKotlin testDebugUnitTest`
  → green; `testDebugUnitTest` ≥ **207** + new tests, **0 failures**; `I18nTest` green with the new keys.
- Instrumented (`androidTest`) — compile green; on-device run via `am instrument` ×2 when a device is
  available, else "device verification pending" (never `connectedAndroidTest` — BootReceiver crashes it),
  consistent with plan003 TP5.
- Manual smoke on a device: tap "ÚLTIMO CHECK-IN/CHECK-OUT" → list shows date/activity/location (after the
  backend deploy) or a clear error (before it); open Settings → Activities → see the day-grouped, colored,
  English table; perform a manual check-in/out and confirm a `user` row appears; leave auto on and confirm
  `sys` rows + active/inactive transitions.
- Backend (Problem 1 deploy): after the human-approved push, the guarded `prod_e2e` read check returns
  `items` for `GET /check/history`.

## 5. Rollout (all human-gated — do NOT do unprompted)
1. **Backend deploy** of `/check/history` (P1-A) via the existing pending root `main` push — this is what
   makes the history non-empty. The app already calls it.
2. **AAB** rebuild + Play publish for the Kotlin changes (history error/Atividade column + Activities log),
   versioned per the existing release process (`kotlin_play_publishing`). Separate, human-approved step.

## 6. Definition of done
- Problem 1: with the endpoint deployed, both cells show the correct action's history with **date,
  activity, location**; a load failure shows a clear, retryable error (never a silent "empty"); new i18n
  keys in all 6 langs; tests green.
- Problem 2: a "Atividades/Activities" Settings row opens an English-only, **day-grouped, color-coded,
  paged (30-per-block)** table logging the **complete background suite** — check-in/out (ok/fail, user/sys),
  active/inactive (service + scheduled pause + boot), every trigger (timer/geofence/foreground/alarm),
  location fixes, offline queue/replay/connectivity, auth/reauth, permission/battery changes, and errors —
  even while the phone is locked. Backed by a **new Room store**, retained **30 days OR 5,000 entries**
  (pruned on write), surviving restarts/reboots (so "last Friday" is visible). Logging is **crash-proof**
  (never breaks a check-in). Tests green; zero regression to existing flows.
- Kotlin suites ≥ baseline + new, 0 failures; nothing committed/pushed/published without explicit human
  approval.
