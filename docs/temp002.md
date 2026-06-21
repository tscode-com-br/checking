# Checking — Execution Playbook for `plan002.md` (agent prompts) + IMMENSE test suite

> **Audience:** an AI coding agent that executes `docs/plan002.md` end to end, one prompt at a time.
> **Prime directive:** the app works **very well**, and **check-out is perfect and must stay intact**.
> `plan002.md` is the canonical change spec (the *what* and *why*). This file (`temp002.md`) is the
> *how*: the ordered, self-contained execution prompts + a very large verification suite. When a prompt
> says "execute plan002 Pn.x", open `plan002.md`, read that prompt in full, and apply it exactly — this
> file restates the essential context so you rarely need to flip back, but `plan002.md` is authoritative
> for the code-level details.

Modeled on `docs/temp001.md`. Execute prompts **strictly in order**. Do not start a prompt until the
previous one compiles, its tests pass, and its **Verify** block is satisfied. **Never start a change
phase on a red baseline.** Backend changes (EP1, EP5, EP7) deploy to **production** on push — never push
without explicit human approval.

This work spans **two codebases**:
- **Kotlin app** — `checking_kotlin/` (own git repo `checking-kotlin`; commit/push per
  `docs/Instrucoes/instrucoes_acesso_repositórios_github.md` §1.7/2.6).
- **Backend monolith** — `sistema/app/` in root repo `checking` (pushing `main` deploys to PRODUCTION
  via `Deploy OceanDrive`; see §2.1/§3.1 of the same doc and `instrucoes_acesso_Digital_Ocean.md`).

---

## 0. Global context (every prompt assumes you have read this section)

### 0.1 Repos, build, run
- Repo root: `c:\dev\projetos\checkcheck`. Kotlin module: `checking_kotlin/` (run Gradle from there).
- Kotlin tests: `./gradlew testDebugUnitTest`; fast compile: `./gradlew compileDebugKotlin`.
  Do NOT run `connectedAndroidTest` (BootReceiver crashes it). Instrumented tests: run twice via
  `am instrument` on a connected device, else mark "device verification pending".
- Backend tests: from repo root, `pytest -q` (SQLite; no prod needed).

### 0.2 The change set (full detail in `plan002.md` §0)
- **A — Check-in only on location change.** No blind 15-min heartbeat. The TIMER still runs and verifies
  location, but a check-in is submitted **only when the resolved location differs from the last check-in
  location**. Same location → no action. **Keep** the TIMER skip-if-unchanged. Continuation: if last
  action = check-IN and the user is "near but not inside" any area (`NOT_IN_KNOWN_LOCATION`), submit a
  check-in as **"Localização não Cadastrada"** — only if it is a *change* (last check-in wasn't already
  that). If last action = check-OUT, never check-in outside a registered area. **Change A also FIXES the
  duplicate check-in** (repeated triggers at the same location → no-op); see plan002 §0 "B — REMOVED".
- **B — De-dup — REMOVED.** Originally a 10-min same-location dedup; **dropped**. The duplicate check-in is
  fixed at its root by **change A** (P6.1 — check-in only on location change), confirmed by the 2026-06-17
  production-log investigation (chaves U3RD/U390/UQL2). See plan002 §0 "B — REMOVED". Letters C/D/E are kept
  as-is to avoid breaking cross-references. **Never two consecutive check-outs** still holds.
- **C — Foreground trigger.** Opening/foregrounding the app (auto-activities ON) runs the engine.
- **D — History with location.** Tapping "ÚLTIMO CHECK-IN"/"ÚLTIMO CHECK-OUT" opens a dialog with the
  full history table showing **date, time, and location**, from a new backend endpoint.
- **E — FORMS per project.** First check-in of the day + every check-out → FORMS filled/submitted **once
  per project** the user is registered in (e.g. P80 **and** P83 → two submissions).

### 0.3 Key Kotlin files (re-locate symbols by name; line numbers drift)
- Engine (PURE, single source of truth; **also used by offline replay**):
  `domain/checkrules/AutoActivities.kt` — `resolveAutomaticActivityForMatch(match, currentState,
  mixedZoneIntervalMinutes)`, `shouldAttemptAutomaticLocationEvent(...)`, `resolveRecordedCheckInLocation`,
  `resolveLastRecordedAction`, `normalizeLocationName`, constants `AUTOMATIC_CHECKOUT_LOCATION`,
  `AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION = "Localização não Cadastrada"`, `MIXED_ZONE_LOCATION`.
- Live flow: `domain/usecase/RunAutomaticActivitiesUseCase.kt` (`clock: Clock` injected).
- Orchestrator: `platform/background/BackgroundCheckOrchestrator.kt` (`OrchestratorTrigger {TIMER,
  GEOFENCE, FOREGROUND}`; **skip-if-unchanged** = `runOnceLocked` Step 3 `shouldSkip()` for TIMER — KEEP).
- FGS: `platform/background/AutoActivityForegroundService.kt` (`TIMER_INTERVAL_MS = 15 min`).
- Offline replay: `platform/background/offline/PendingCheckReplayer.kt`, `SyncPendingChecksWorker.kt`.
- Models: `domain/model/CheckModels.kt` — `HistoryState(lastCheckinAt, lastCheckoutAt, currentAction,
  currentLocal, projeto, ...)`, `MatchStatus {MATCHED, ACCURACY_TOO_LOW, NOT_IN_KNOWN_LOCATION,
  OUTSIDE_WORKPLACE, NO_KNOWN_LOCATIONS}`.
- ViewModel: `presentation/check/CheckViewModel.kt` (`onForegroundResume`, `onRefreshLocation`,
  `onAutomaticActivitiesToggled`, `automaticActivitiesEnabled`, `chave`).
- History UI: `presentation/components/HistoryCard.kt` (two cells, currently NOT clickable; zone
  `Asia/Singapore`). Dialog routing: `CheckDialog` in `presentation/check/CheckUiState.kt`, rendered in
  `CheckScreen.kt`. Scaffold: `presentation/components/DialogScaffold.kt`.
- API: `data/api/CheckApi.kt`, DTOs `data/dto/CheckDtos.kt`, repo `data/repository/CheckRepositoryImpl.kt`.
- i18n: 6 dictionaries in `i18n/dictionaries/` (Pt/En/Zh/Ms/Id/Tl); `i18n/I18nTest.kt` parity.

### 0.4 Key backend files
- `sistema/app/routers/web_check.py` — `GET /check/state` (`build_web_check_history_state`); `POST /check`
  (`submit_web_check` → `_reject_non_operational_web_submit_local`, 422 on "Localização não Cadastrada");
  `X-Client: checking-android` → `WEB_CHECK_ANDROID_CHANNEL` (~134); `_validate_public_chave`.
- FORMS: `services/forms_submit.py` (`submit_forms_event`), `services/forms_queue.py`
  (`enqueue_forms_submission(request_id, projeto, project_candidates, ...)`), `services/forms_worker.py`
  (selects ONE project from candidates today), `services/user_sync.py`
  (`create_user_sync_event` → `record_checking_history`; `should_enqueue_forms_for_action`),
  `services/project_catalog.py` (`is_forms_enabled_for_project`), `services/checking_history.py`
  (`record_checking_history`), models `CheckingHistory` (no `local` yet) / `CheckEvent` (has `local`) /
  `FormsSubmission` in `models.py`.
- Schemas: `schemas.py`. Migrations: `sistema/app/migrations/`. Tests: `tests/`.

### 0.5 Test credentials (provided by the product owner — use freely in tests)
- **chave: `TEST`** · **senha: `000000`**.
- Use these for engine fixtures, backend tests, and (carefully) end-to-end checks. For e2e against the
  Kotlin client, log in with TEST/000000.

### 0.6 Production access (only when a test must touch prod — prefer LOCAL otherwise)
Per `docs/Instrucoes/instrucoes_acesso_Digital_Ocean.md`:
- Public API base: `https://tscode.com.br/api`. Health: `https://tscode.com.br/api/health`.
- SSH to host (Windows → via WSL):
  `wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21 'CMD'; rm -f /tmp/do_ck"`
- Read-only DB inspection (per memory `prod_db_readonly_audit`): `docker exec checkcheck-db-1 psql ...`
  inside the host to inspect `checkinghistory`, `check_events`, `forms_submission`, `user_sync_events`.
- **PROD SAFETY (critical):** a real check-in/check-out submit to prod for chave `TEST` writes real
  events **and triggers real FORMS browser automation** for TEST's projects. Therefore:
  - Default all submit/FORMS tests to the **LOCAL** backend (`pytest` + a local dev server), NOT prod.
  - Use prod ONLY for **read** verification (`GET /check/state`, `GET /check/history`,
    `GET /check/locations`) and a **small, clearly-marked, cleaned-up** set of e2e submits.
  - Never loop-submit to prod. Never run the FORMS-per-project e2e against prod without explicit human
    approval (it launches N headless-browser submissions per event).

### 0.7 The behavior spec under test
`docs/regras_e_situacoes/regras_checkin_checkout_kotlin.txt` defines Situations 1–9. **plan002 P8.1
updates it** (Situations 4/5/6 + FORMS-per-project). The IMMENSE test suite (PHASE T) encodes the
**post-plan002** expected behavior, situation by situation. The one prior contradiction (Situation 7B) is
**RESOLVED** (T1): it follows Situação 3 — a checked-out user out-of-area gets no check-in.

---

## 1. Golden rules (apply to EVERY prompt)
1. **Check-out is sacred.** Never touch `shouldAttemptAutomaticOutOfRangeCheckout`, the checkout-zone
   branch, the mixed-zone toggle, or any check-out path/timing/location.
2. **No blind heartbeat; keep skip-if-unchanged.** Check-in fires only on location change.
3. **Additive-first.** New params default; new endpoints/DTOs/columns/functions over edits. New DB
   columns nullable and NOT in existing unique keys.
4. **The duplicate check-in is fixed at the engine layer (change A / P6.1), NOT by a time-window dedup.**
   Do not add a same-location/10-minute dedup guard. (See plan002 §0 "B — REMOVED".)
5. **Engine changes affect offline replay** — verify `PendingCheckReplayer`/`SyncPendingChecksWorker`.
6. **Backend 422 relaxation is scoped** to `X-Client: checking-android` + check-in only. Web still 422s.
7. **FORMS multi-project preserves single-project behavior** byte-for-byte; preserve idempotency
   (per-project `request_id`/`source_request_id`).
8. **Touch all 6 dictionaries together.** Re-run `I18nTest`.
9. **One prompt = one compilable, test-passing increment.**
10. **Do NOT `git commit`/`push`/branch** unless the human asks. Backend push = production deploy.
11. Keep Sections 2/3/4 current. If reality differs from the plan, STOP, log in Section 3, report.

---

## 2. Progress tracker (update after each prompt)

**Execution (from plan002):**
- [x] **EP0** Baseline (plan002 P0.1–P0.2) — 2026-06-17: Kotlin **148 green** + compile clean; backend pytest **555 pass / 33 pre-existing fails (all in `test_transport_ai_suggestion_commands.py`) / 2 skip** (`test_api_flow.py` collection-blocked on Windows — EP0-3); protected check-out + FORMS snapshot recorded (§4). **Trees NOT clean** — baseline sits on uncommitted temp001 (anomaly EP0-1). See §3.
- [x] **EP1** Backend: `local` on `CheckingHistory` + populate + `GET /check/history` (plan002 P1.1–P1.2) — 2026-06-17: migration 0078 (nullable `local`, NOT in unique key) + `record_checking_history(local=…)` + `list_checking_history` + schemas + `GET /check/history`. Full pytest **561 pass / 33 pre-existing fail / 2 skip** (was 555 → +6 new, ZERO new failures); migration applies on fresh SQLite. **⚠ Backend change — NOT deployed; needs human approval before push (EP1-1).**
- [x] **EP2** Kotlin: history data layer + dialog with location (plan002 P2.1–P2.2) — 2026-06-17: DTOs + `CheckApi.getHistory` + `CheckHistoryEntry` + repo mapper; `CheckHistoryDialog` (Data/Hora/Local) opened by tapping either `HistoryCard` cell; 7 i18n keys added to **all 6 dicts**. `compileDebugKotlin` + `testDebugUnitTest` (**150**, +2) + `I18nTest` (16) green. Kotlin repo only (non-prod).
- [x] **EP3** Kotlin: foreground trigger (plan002 P3.1) — 2026-06-17: `onForegroundResume()` now also launches `orchestrator.runOnce(OrchestratorTrigger.FOREGROUND)` when `isAuthenticated && automaticActivitiesEnabled` (mirrors `onRefreshLocation`; single-flight + change A prevent dup check-ins; no-op when auto OFF; no second lifecycle observer). `compileDebugKotlin` + `testDebugUnitTest` (150) green. Kotlin repo only (non-prod). Device check (foreground→checks in/out/no-dup) pending-for-device.
- ~~**EP4** check-in dedup~~ — **REMOVED** (superseded by EP6/P6.1; see plan002 §0 "B — REMOVED"). No work.
- [x] **EP5** Backend: allow "Localização não Cadastrada" check-in for android client (plan002 P5.1) — 2026-06-18: scoped relaxation of `_reject_non_operational_web_submit_local` (android client + check-in only); web + any check-out still 422. 3 new tests (a/b/c); full pytest **564 pass / 33 pre-existing fail / 2 skip** (was 561 → +3, ZERO new failures). **⚠ Prod backend change — NOT deployed; needs human approval before push (EP5-1).**
- [x] **EP6** Kotlin: engine — location-change check-in + "Não Cadastrada" continuation (plan002 P6.1–P6.2) — 2026-06-18: P6.1 suppresses same-location re-check-in; P6.2 adds `NOT_IN_KNOWN_LOCATION`→unregistered check-in (as a change). **Check-out branches + skip-if-unchanged untouched (git-diff-confirmed).** Offline replay coherent. `testDebugUnitTest` **153** (was 150), 0 failures. Kotlin repo only; relies on EP5 backend (pending deploy) for the app to actually submit the unregistered check-in.
- [x] **EP7** Backend: FORMS per project (plan002 P7.1–P7.2) — 2026-06-18: `submit_forms_event` fans out one FormsSubmission + sync/history row per registered project (per-project request_id + forms_enabled gate + idempotency); single-project byte-for-byte. P7.2 needs no worker change (per-row isolation is structural). 6 new tests; full pytest **570 pass / 33 pre-existing fail / 2 skip** (was 564 → +6, ZERO new failures). **⚠ Prod backend change — NOT deployed; needs human approval before push (EP7-1).**
- [x] **EP8** Update the rules file (plan002 P8.1) — 2026-06-18: `regras_checkin_checkout_kotlin.txt` amended — Situações 4/6 (location-change-only), 5 ("Não Cadastrada" continuation), Situação-3 IMPORTANTE note (cross-ref fixed); 7A/7B verified unchanged; appended general-notes block (foreground trigger, no 10-min dedup, FORMS-per-project, preserved check-out invariants). Docs-only; re-read consistent with EP5–EP7.

**IMMENSE test suite (PHASE T):**
- [x] **TP0** Test harness, credentials, prod-access safety, run recipes — 2026-06-18: confirmed the engine factories + fixed clock (`AutoActivitiesSituationTest`); added the `prod_e2e` marker + skip-unless-`CHECKING_E2E_PROD=1` guard in `tests/conftest.py` (self-verified by `tests/test_prod_e2e_guard.py`); default suites run offline (607 backend collected). See §4.
- [x] **TP1** Engine SITUATION MATRIX (all 9 situations) — unit tests — 2026-06-18: new `SituationMatrixTest.kt` — 18 explicit pure-engine cases (1a/1b/2a/2b/3a/3b/4a/4b/5a/5b/6a/6b/7A/7B/8a/8b/8c/8d) on `resolveAutomaticActivityForMatch`, asserting exact `AutomaticActivity(action, local)?`; **7B = null**; Situação 9 (auto OFF) deferred to TP4. testDebugUnitTest **171** (was 153), 0 failures.
- [x] **TP2** Location-change-only + "Não Cadastrada" continuation — unit/use-case tests — 2026-06-18: new `LocationChangeContinuationTest.kt` (6 sequence tests on the pure engine): only-on-change (repeated identical reads → 1 check-in), Portaria→Portaria→Refeitorio, full Não-Cadastrada continuation cycle, checkout+NOT_IN_KNOWN_LOCATION→null, ACCURACY_TOO_LOW/NO_KNOWN_LOCATIONS→always null. testDebugUnitTest **177** (was 171), 0 failures.
- [x] **TP3** Duplicate-elimination via P6.1 (multi-trigger, same location) — use-case/orchestrator tests — 2026-06-18: `DuplicateEliminationTest` (4, use-case): two runs at the same new location → exactly ONE submit (the prod bug); stationary repeats → 0; genuine A→B→C → 2; failed-submit edge documented (no guard). `OrchestratorSingleFlightTest` (1): concurrent `runOnce` blocked by the `Mutex` (`tryLock` fails → returns, no submit). testDebugUnitTest **182** (was 177), 0 failures.
- [~] **TP4** Foreground trigger + toggle gate (Situação 9) — VM/integration tests — 2026-06-18: **Test 2 DONE** (`OrchestratorToggleGateTest`: auto OFF → `EvaluationOutcome.TOGGLE_OFF` recorded, no engine/submit — Situação 9). **Test 1 partial** (`CheckViewModelForegroundTest`: NOT authenticated → orchestrator NOT run); the authenticated sub-cases (auto ON→runs / auto OFF→not) need the VM auth-success path (Android statics) → **pending-for-device (TP9)** + covered by EP3 + TP1/TP3. **Test 3** covered by TP1 (4a/6a) + TP3 (two-runs) + EP3 (no new test). testDebugUnitTest **184** (was 182), 0 failures.
- [x] **TP5** FORMS per project — backend pytest (+ guarded e2e) — 2026-06-18: all 8 cases green. `tests/services/test_forms_submit_per_project.py` (cases 1–6 + case 8 history-per-project; case 6 now also asserts no duplicate UserSyncEvent/CheckingHistory on replay) + `tests/services/test_forms_per_project_worker_isolation.py` (case 7: unsupported PXX fails only its own row, P80 unaffected — worker boundary mocked). Guarded prod e2e left OPTIONAL (CHECKING_E2E_PROD + human approval). Test-only (no prod code change).
- [x] **TP6** History with location — backend pytest + Kotlin mapper/dialog tests — 2026-06-18: backend `tests/test_web_check_history.py` (4: newest-first + action map + null passthrough + 422; **+ multi-project & null-serialized-as-JSON-null**); Kotlin `CheckHistoryMapperTest` (EP2, DTO→CheckHistoryEntry incl. null) + new instrumented `CheckHistoryDialogSmokeTest` (Data/Hora/Local headers, "Área X" row, null→"-", empty state) — compile-verified, on-device run pending. pytest history 4/4 + `compileDebugAndroidTestKotlin` + `testDebugUnitTest` green.
- [x] **TP7** Check-out preservation regression — unit tests — 2026-06-18: new `CheckoutPreservationTest` (9): matrix check-out cases 1a/1b/2a/2b/3a/7A/8a/8d + the two invariants (never two consecutive check-outs; after check-out the next action is a check-in, via sequences). `git diff` of `AutoActivities.kt` vs EP0 baseline shows ONLY check-IN branch + comment changes — no check-out logic touched. testDebugUnitTest **193** (was 184), 0 failures.
- [~] **TP8** End-to-end vs production (chave TEST) — read-mostly + controlled submit — 2026-06-18: **authored** `tests/test_e2e_prod.py` (5 tests, all `@pytest.mark.prod_e2e` → skip by default). Read-only: health + login + state + `/check/history` (EP1) + locations; negative: web client + "não Cadastrada" → 422. Writes (android "não Cadastrada" → 200 [EP5]; controlled check-in → in history) **double-guarded** by `CHECKING_E2E_PROD_SUBMIT=1`. Step 2 (prod-DB inspection) = manual SSH+docker recipe. **Execution PENDING:** needs EP1/EP5/EP7 **deployed** + operator opt-in. Verified all 5 skip in the default suite.
- [~] **TP9** Device/instrumented matrix (geofence, FGS, foreground) — 2026-06-18: **all 8 items PENDING-FOR-DEVICE** (no device; emulator can't fire geofences). Deliverables: fresh debug APK `checking_kotlin/app/build/outputs/apk/debug/app-debug.apk` + tester checklist `docs/temp002_TP9_checklist_testadores.md`. Items 1/2/4/5/8 testable with the app alone; **3/6/7 also need backend EP5/EP7/EP1 deployed**. Awaits tester device pass.
- [x] **TP10** Master coverage matrix sign-off — 2026-06-18: full situation/change → test matrix in §4 (every TP1 cell 1a–9 → ≥1 green test; **7B = null**; no uncovered cell). Kotlin `testDebugUnitTest` **193/0** + `I18nTest` 16/0 + `compileDebugKotlin` clean; backend `pytest` **574 pass / 33 pre-existing fail / 8 skip** clean (no new failures). Check-out (TP7) + single-project FORMS (TP5#4) green. Acknowledged non-automated cells: TP4-auth-foreground & TP9 (device), TP8 (pending deploy + opt-in).

---

## 3. Deviations log (append-only)
> `EPn/TPn — YYYY-MM-DD — what & why`. Record unexpected signatures, reconciliations, test edits, etc.
- **EP0-1 — 2026-06-17 — git trees NOT clean at baseline.** This temp002 baseline is captured **on top of the
  completed-but-uncommitted `temp001` Kotlin UX overhaul** (148 tests incl. +2 new suites; `PermissionsDialog`
  deleted; an authorized i18n change to the protected `AutoActivityForegroundService.kt`). The root repo also
  carries pre-existing uncommitted changes (`sistema/app/static/check/*` + docs). This is the deliberate
  starting point, but EP0's Verify ("clean git status both repos") is therefore NOT met. **Recommendation
  (flagged for the human):** commit the `temp001` work in the `checking_kotlin` repo **before** the plan002
  Kotlin phases (EP2/EP3/EP6) so the two efforts stay separately reviewable — otherwise their diffs intermix.
  No commit was made (golden rule 10). **Awaiting the human's call on whether to commit temp001 first.**
- **EP0-2 — 2026-06-17 — 33 pre-existing backend failures, all unrelated.** Every failure is in
  `tests/test_transport_ai_suggestion_commands.py`: the harness runs a subprocess that asserts the transport-AI
  start endpoint returns HTTP `201`, but it returns the async `passengers_reset` path
  ("Cálculo iniciado…"). Pre-dates this work (visible in the May-23 `pytest_output.txt`). **Transport-AI only —
  not check-in/check-out/history/FORMS.** Recorded so plan002 can prove it adds none.
- **EP0-3 — 2026-06-17 — `tests/test_api_flow.py` cannot be collected on Windows.** At module import it does
  `Path("test_checking.db").unlink()` (L47–48), but another already-imported test module holds an open SQLite
  handle to that file → `PermissionError [WinError 32]`, which aborts the ENTIRE pytest collection. Worked
  around for the baseline with `--ignore=tests/test_api_flow.py`. Pre-existing Windows/test-isolation fragility
  (POSIX allows unlinking an open file; Windows does not) — not introduced here. To run the full suite on
  Windows this file needs isolation or a fixture that disposes engines before the unlink.
- **EP1 — 2026-06-17 — backend history-with-location implemented (plan002 P1.1+P1.2).** Changes (all
  additive): `CheckingHistory.local` nullable `String(40)` (NOT in `uq_checkinghistory_event`); Alembic
  migration `0078_add_local_to_checkinghistory` (chains from 0077; applies cleanly on fresh SQLite — verified
  `alembic upgrade head` → column present); `record_checking_history(..., local=None)` sets it (dedup query
  unchanged on the 5-field key); `create_user_sync_event` passes `local=local`; new
  `list_checking_history(db, *, chave, limit=500)` (newest-first); new schemas `WebCheckHistoryItem` /
  `WebCheckHistoryListResponse`; new route `GET /check/history` (mirrors `/check/state`'s
  `_require_matching_authenticated_web_user` + `Query(min_length=4, max_length=4)` access model; maps
  `atividade`→`action`). New tests: `tests/test_checking_history_local.py` (3) + `tests/test_web_check_history.py`
  (3). **Shared-DB note:** had to delete the stale `test_checking.db` once so `Base.metadata.create_all`
  rebuilt `checkinghistory` WITH the new `local` column (create_all does not ALTER existing tables) — same
  Windows shared-DB fragility family as EP0-3; harmless (the file is recreated by the suite).
- **EP1-1 — 2026-06-17 — ⚠ AWAITING HUMAN APPROVAL TO DEPLOY.** EP1 modifies the production monolith
  (`models.py`, a new Alembic migration, `web_check.py`, `schemas.py`, `checking_history.py`, `user_sync.py`).
  Pushing `main` deploys to PRODUCTION via *Deploy OceanDrive* and **runs the 0078 migration on the prod DB**.
  Per golden rule 10, **no commit/push was made**. Get explicit human approval (and a prod DB backup/window)
  before deploying. The change is read-additive (nullable column + new read-only endpoint), so blast radius
  is low, but it still touches prod schema.
- **EP2 — 2026-06-17 — Kotlin history dialog (plan002 P2.1+P2.2).** Data layer: `WebCheckHistoryItemDto` /
  `WebCheckHistoryListResponseDto`, `CheckApi.getHistory`, domain `CheckHistoryEntry`, repo `getHistory` +
  private DTO→domain mapper, `DtoInformeType.toDomain()`. UI: `CheckDialog.History` + filter state
  (`historyDialogAction`/`…Entries`/`isHistoryDialogLoading`/`historyDialogError`); `openCheckinHistory()`/
  `openCheckoutHistory()`; `CheckHistoryDialog` (Data/Hora/Local table, Asia/Singapore zone + locale
  formatting mirrored from `HistoryCard`, "-" for null local/time, empty + loading states); the two
  `HistoryCard` cells made clickable via **additive** `onCheckinClick`/`onCheckoutClick` (default no-op →
  preserves the unchanged look/behavior). i18n: the `history` block exists in **all 6 dicts** (fully
  translated, unlike `autoActivities`), so the 7 new keys (`dialogTitleCheckin`/`dialogTitleCheckout`/
  `colDate`/`colTime`/`colLocal`/`empty`/`back`) were added to **all 6** per golden rule 8. Tests:
  `CheckHistoryMapperTest` (2). **Deviations:** (a) `CheckHistoryEntry.time` is `Instant?` (nullable) rather
  than the plan's non-null `Instant` — the server time is parsed from an ISO string at the repo boundary
  (same parser as `HistoryState`), and nullable avoids a crash on an unexpected format (the dialog renders
  "-"), mirroring how `HistoryCard` already handles a null instant. (b) Chose the plan's "one dialog + filter"
  option (`CheckDialog.History` + `historyDialogAction`) over two enum values. (c) No instrumented test added
  — P2.2 doesn't require one; the "both cells load tables with location" device check is **pending-for-device**.
  Verify: `compileDebugKotlin` + `testDebugUnitTest` (150, +2) + `I18nTest` (16) green. **Kotlin repo only — no
  production impact; the EP1 backend `GET /check/history` it consumes is still pending deploy (EP1-1).**
- **EP5 — 2026-06-18 — backend scoped relaxation (plan002 P5.1).** `_reject_non_operational_web_submit_local`
  now takes `is_android_client` + `action` and **skips the 422 only when** client == `checking-android` AND
  action == `checkin`; the browser web app, any check-out, and any other local behave exactly as before.
  `submit_web_check` computes `is_android_client` once (from `X-Client`) and reuses it for both the guard and
  the existing channel selection (replacing the inline ternary). Confirmed nothing else downstream rejects
  this local (grep: the guard was the only server-side rejection; `submit_forms_event` records via
  `create_user_sync_event(local=resolved_local)` independent of FORMS). New tests
  `tests/test_web_check_submit_unregistered_local.py` (3: web+checkin→422, android+checkin→200+recorded,
  android+checkout→422), using `forms_enabled=False` to keep the submit free of FORMS side effects. Verify:
  full `pytest` **564 pass / 33 pre-existing fail / 2 skip** (was 561 → +3, zero new). **Did NOT** widen
  `WEB_NON_OPERATIONAL_SUBMIT_LOCALS` or relax for check-out/web.
- **EP5-1 — 2026-06-18 — ⚠ AWAITING HUMAN APPROVAL TO DEPLOY.** EP5 changes a **deliberate production submit
  invariant** for the app client (`sistema/app/routers/web_check.py`). Pushing `main` deploys to PRODUCTION
  via *Deploy OceanDrive*. Per golden rule 10, no commit/push was made. **Needs explicit human review/approval
  before deploy** — and note it pairs with EP1 (both backend) and is the enabler for EP6's "não Cadastrada"
  continuation, so EP1+EP5 should deploy together (or at least before relying on the app's new check-in path).
- **EP6 — 2026-06-18 — engine change A (plan002 P6.1+P6.2), HIGHEST RISK.** `AutoActivities.kt`: (P6.1)
  `shouldAttemptAutomaticLocationEvent`'s final branch (matched, non-checkout, non-mixed, last=check-in)
  now returns true only when `normalizeLocationName(resolvedLocal)` is non-empty **AND** differs from
  `normalizeLocationName(resolveRecordedCheckInLocation(remoteState))` — suppresses the duplicate
  same-location re-check-in (mirrors the mixed-zone "different location" check). (P6.2)
  `resolveAutomaticActivityForMatch` gains a `NOT_IN_KNOWN_LOCATION` branch → `AutomaticActivity(CHECKIN,
  "Localização não Cadastrada")` only when `resolveLastRecordedAction == CHECKIN` AND the last check-in
  location wasn't already that (a CHANGE); else null. Doc-comment updated. **Check-out branches,
  checkout-zone/mixed-zone logic, and the orchestrator skip-if-unchanged are UNTOUCHED — confirmed by
  reviewing `git diff` (only the two targeted branches + doc-comment changed).** Tests:
  `AutoActivitiesSituationTest` s4 split into same-location→NoAction / different-location→re-check-in; s5
  updated to the unregistered continuation + a no-repeat case (now 19 tests); `PendingCheckReplayerTest` —
  the old "NOT_IN_KNOWN_LOCATION consumed without submit" case repurposed to last=check-OUT (still no
  action) and a new test asserts the offline replay submits the unregistered check-in (CHECKIN,
  "Localização não Cadastrada", original time+id) when last=check-in (now 8 tests). Verify:
  `testDebugUnitTest` **153 / 0 failures** (was 150 → +3 net). **Kotlin repo only (non-prod).** The app only
  actually submits the unregistered check-in once the EP5 backend relaxation is deployed (EP5-1); until then
  the server 422s it (offline replay's HTTP-4xx path drops such an event — acceptable, resolved by deploying EP5).
- **EP7 — 2026-06-18 — FORMS per project (plan002 P7.1+P7.2), HIGH RISK (prod FORMS pipeline).**
  `submit_forms_event`: computes `project_candidates`/`single_project` once; the `forms_enabled` gate is
  scoped to single-project (multi-project gates per project). **Single-project path kept byte-for-byte**
  (the existing try/enqueue/except + `create_user_sync_event` with the bare `client_event_id`, guarded by
  `if single_project:`). Multi-project goes through new `_enqueue_forms_per_project_and_record`: per project
  → per-project idempotency check (existing `UserSyncEvent` with the per-project `source_request_id` → skip),
  enqueue (if `is_forms_enabled_for_project`) else `record_forms_submission_skip`, then
  `create_user_sync_event` (→ per-project history row). Returns the count of newly-recorded projects; **0 →
  full replay → return the duplicate response before the trailing `log_event`** (the multi path bypasses the
  bare-id top short-circuit, so without this a replay hit the `check_events.idempotency_key` unique
  constraint — caught and fixed). **request_id = `{client_event_id}:{sha1(project)[:12]}`** (NOT the literal
  `:{project}` the plan suggested — project names are `String(120)` but `FormsSubmission.request_id` is
  `String(80)` unique; the readable project lives in the row's `projeto` column). **P7.2 needed NO worker
  change:** `_process_submission` already processes one `FormsSubmission` at a time with
  `project_candidates=[project]` (single candidate), so an `UnsupportedProject` fails only that row — tests
  assert each per-project row carries a single candidate (structural isolation). New tests
  `tests/services/test_forms_submit_per_project.py` (6: 2-project checkin/checkout → two rows; no-trigger →
  none pending; forms-disabled project skipped while others pending; single-project → exactly one with bare
  request_id; replay idempotent). Test helper mocks `resolve_latest_internal_user_activity`/`should_enqueue_
  forms_for_action` to isolate the per-project fan-out from the timing logic + a SQLite naive/aware-datetime
  sort artifact (same tz fragility family as EP0-3; not prod). Verify: full `pytest` **570 pass / 33
  pre-existing fail / 2 skip** (was 564 → +6, zero new). **Did NOT** change trigger timing, check-out
  detection, idempotency strength, or single-project behavior.
- **EP7-1 — 2026-06-18 — ⚠ AWAITING HUMAN APPROVAL TO DEPLOY.** EP7 changes the **production FORMS
  pipeline** (`sistema/app/services/forms_submit.py`). For a multi-project user it now submits FORMS once
  PER project (e.g. P80+P83 → two headless-browser submissions per applicable event). Pushing `main` deploys
  to PRODUCTION via *Deploy OceanDrive*; per golden rule 10 no commit/push was made. **Needs explicit human
  review/approval before deploy.** Joins EP1 + EP5 as the backend changes pending deployment; they should
  ship together (and a prod multi-project FORMS smoke should be watched — N browser submissions per event).
- **TP0 — 2026-06-18 — test harness + prod-safety guard (no production reach in the default suite).**
  Engine factories + fixed clock already existed in `AutoActivitiesSituationTest` (documented in §4 — no
  refactor/extraction; TP1–TP3 extend that class). New: `tests/conftest.py` registers the `prod_e2e` marker
  and a `pytest_collection_modifyitems` hook skipping such tests unless `CHECKING_E2E_PROD=1`;
  `tests/test_prod_e2e_guard.py` self-verifies it (default → marked test SKIPPED + offline-default assertion
  passes; opt-in → marked test runs). Verify: default `pytest` offline (607 collected, conftest hooks clean,
  marker registered) and `testDebugUnitTest` is pure/mocked (no network). No prod-touching test exists yet
  (TP8 will add them, marked `prod_e2e`).
- **TP1 — 2026-06-18 — situation matrix on the pure engine.** New `SituationMatrixTest.kt` (package
  `checkrules`) calls `resolveAutomaticActivityForMatch(match, state, mixedZoneIntervalMinutes=15)` directly
  (no mocks/use-case) and asserts the exact decided `AutomaticActivity` for all 18 cells (1a–8d). Mixed-zone
  cooldown cases (8a/8b/8c) use `Instant.now().minus(...)` offsets (the pure engine reads `Instant.now()`
  internally — generous 5-vs-20-min margins vs the 15-min interval keep them deterministic). Case 9 (auto
  OFF) is intentionally NOT a pure-engine test (the orchestrator simply doesn't call the engine) → covered by
  TP4. **7B asserts null** (checked-out + out-of-area → no check-in), per the resolved product decision; no
  `@Ignore`. No engine change (tests encode EP6's behavior). Verify: `testDebugUnitTest` 171 / 0 failures.
- **TP2 — 2026-06-18 — change A pinned via sequences.** New `LocationChangeContinuationTest.kt` drives the
  pure engine across multi-read sequences with an `apply(state, decision)` helper that models how the server
  records each decided activity (monotonic deterministic instants; no mixed-zone → `Instant.now()` never
  consulted). 6 tests: (1) repeated identical MATCHED reads check in only once; (2)
  Portaria→Portaria→Refeitorio — only the move checks in; (3) full continuation cycle
  in@area→outside(Não Cadastrada)→outside(null)→back inside; (4) checkout + NOT_IN_KNOWN_LOCATION → null;
  (5) ACCURACY_TOO_LOW & NO_KNOWN_LOCATIONS → always null (both last actions). Verify: `testDebugUnitTest`
  177 / 0 failures.
- **TP3 — 2026-06-18 — duplicate-elimination at the LIVE flow.** `domain/usecase/DuplicateEliminationTest`
  (4, use-case + fake repo/clock/queue): the exact prod bug (geofence EXIT(A)+ENTER(B) ⇒ two triggers at new
  location B) now yields **exactly one** submit (run 1 submits at B + advances state to "checked-in@B"; run 2
  reading that state → NoAction); stationary repeats → 0 submits; genuine A→B→C → 2 submits (fix doesn't
  over-suppress); test 5 documents the **unchanged offline edge** (a FAILED submit doesn't advance state, so
  a retry re-decides — no guard added, the dropped 10-min dedup never covered it either). `platform/background/
  OrchestratorSingleFlightTest` (1): a `runOnce` held at its first suspend (`appPrefs.chave.first()` via a
  gate) keeps the `Mutex`; a concurrent `runOnce` `tryLock`-fails and returns immediately (proven by it
  completing while run 1 is still suspended) → no extra submit. Verify: `testDebugUnitTest` 182 / 0 failures.
- **TP4 — 2026-06-18 — foreground trigger + Situação 9 toggle gate.** **Test 2 (Situação 9):**
  `platform/background/OrchestratorToggleGateTest` constructs the real orchestrator (mocked Context/PowerManager
  + relaxed deps), feeds an empty `userSettingsJson` (→ default UserSettings, auto OFF) and a no-op accident
  state, runs `runOnce(FOREGROUND)`, and asserts the EvaluationLog has a `TOGGLE_OFF` entry (matched by a
  unique clock instant) with **zero** use-case invocations and **zero** submits. **Test 1 (change C VM gate):**
  `presentation/check/CheckViewModelForegroundTest` proves the NOT-authenticated case (orchestrator never
  run) with a clean JVM build of `CheckViewModel` (stored language "pt" to avoid `LocaleList.getDefault()`,
  which is an un-mocked Android stub in JVM tests; empty stored chave so init does no auth). The two
  AUTHENTICATED sub-cases (auto ON → `runOnce(FOREGROUND)`; auto OFF → not) are **NOT** JVM-unit-tested: the
  VM's auth-success path calls Android statics (`PermissionLadder.checkStatus`, `AutoActivityController`) and
  a chain of sealed-`AppResult` repo calls, which is disproportionate to mock — they're covered by the EP3
  gate code + the engine no-duplicate proofs (TP1 4a/6a, TP3) and are **verified on-device in TP9**. **Test 3
  (foreground same-location → no duplicate)** = engine returns null for same location (TP1 4a/6a, TP3
  two-runs) under the FOREGROUND trigger (EP3) → covered, no new test. TP4 left **partial** (the live
  authenticated foreground behavior is a TP9 device item). Verify: `testDebugUnitTest` 184 / 0 failures.
- **TP5 — 2026-06-18 — FORMS per project (all 8 backend cases, LOCAL only).** Extended EP7's
  `tests/services/test_forms_submit_per_project.py`: cases 1–5 (multi first-checkin → 2 distinct-request_id
  single-candidate rows; multi check-out → 2; no-trigger → 0 pending; single-project → 1 bare request_id;
  per-project forms_enabled skip) were already present; **enhanced case 6** (replay → no duplicate
  FormsSubmission AND no duplicate UserSyncEvent/CheckingHistory per project) and **added case 8** (one
  CheckingHistory row per project per event). **Case 7** in new
  `tests/services/test_forms_per_project_worker_isolation.py`: seeds two "processing" rows (P80 + unsupported
  PXX), mocks `FormsWorker.submit_with_retries` at the browser boundary (PXX→fail / P80→success), runs
  `_process_submission` per row → P80 `success` + untouched, PXX `failed` only on its own row (per-row
  isolation, since each row carries `project_candidates=[project]`). The **guarded prod e2e** is left
  OPTIONAL (requires `CHECKING_E2E_PROD=1` + human approval — never looped). All test-only (no production
  change in TP5). Verify: the 8 cases green. Full `pytest` after TP5 = **572 passed / 34 failed / 3 skipped**
  — **every failure is in the unrelated `test_transport_ai_suggestion_commands.py`** (grep-confirmed; zero in
  check-in/history/FORMS). The 33→34 blip was that flaky subprocess suite (EP0-2) under CPU/DB contention
  (a concurrent targeted `pytest` was running). A **clean re-run (no concurrency) → 574 passed / 33 failed /
  3 skipped** = exactly the pre-existing transport-AI set (574 = 570 EP7 + 1 TP0 + 2 TP5 + 1 TP6; **zero new
  failures**). **Lesson:** don't run two `pytest` processes against the shared `test_checking.db` at once.
- **TP6 — 2026-06-18 — history with location (change D).** Backend: extended `tests/test_web_check_history.py`
  with a **multi-project** case (rows for two projetos, check-in + check-out) asserting both projetos return,
  action mapping, and a **null `local` serialized as JSON null** (4 tests total, all green). Kotlin: the
  DTO→`CheckHistoryEntry` mapper is covered by `CheckHistoryMapperTest` (EP2, incl. null passthrough); added
  instrumented `ui/CheckHistoryDialogSmokeTest` (renders the Data/Hora/Local headers + an "Área X" row, a
  null location as "-", and the empty state) — **compile-verified** via `compileDebugAndroidTestKotlin`;
  on-device run **pending-for-device** (connectedAndroidTest crashes on BootReceiver). Verify: history pytest
  4/4 + `compileDebugAndroidTestKotlin` + `testDebugUnitTest` green.
- **TP7 — 2026-06-18 — check-out preservation regression.** New `CheckoutPreservationTest` (9): the
  check-out-producing matrix cells (1a/1b/2a/2b/3a/7A/8a/8d) + the two invariants (never two consecutive
  check-outs; the action after a check-out is a check-in) proved via engine sequences. `git diff` of
  `domain/checkrules/AutoActivities.kt` vs the EP0 baseline confirms **only check-IN branches + comments**
  changed — no check-out logic, no `AUTOMATIC_CHECKOUT_LOCATION`, no skip-if-unchanged. **No deviation.**
  Verify: `testDebugUnitTest` **193 / 0**.
- **TP8 — 2026-06-18 — e2e vs production (authored, not executed).** Added `tests/test_e2e_prod.py` (5
  tests, all `@pytest.mark.prod_e2e` → skipped by default via the TP0 guard). Read-only path (health, login,
  `/check/accident/state`, `/check/history` [EP1], locations) + the web-client "não Cadastrada" → 422
  negative; the two **write** tests (android "não Cadastrada" → 200 [EP5]; controlled check-in lands in
  `/check/history`) are **double-guarded** behind `CHECKING_E2E_PROD_SUBMIT=1`. **Deviation:** the suite is
  authored but **NOT run** — execution needs EP1/EP5/EP7 *deployed to prod* (still pending human approval)
  and an operator opt-in; httpx pulled via `importorskip`. Step 2 (prod-DB inspection) stays a manual
  SSH+`docker exec` recipe (read-only audit, [[prod_db_readonly_audit]]). Verified all 5 skip in the default
  run. Marked `[~]`.
- **TP9 — 2026-06-18 — device/instrumented matrix (cannot run here).** **Deviation:** all 8 items are
  **pending-for-device** — there is no Android device and the emulator cannot fire real geofence transitions.
  Deliverables produced instead: a fresh debug APK at
  `checking_kotlin/app/build/outputs/apk/debug/app-debug.apk` and a Portuguese tester checklist
  `docs/temp002_TP9_checklist_testadores.md` (8 items; items 1/2/4/5/8 exercise the app alone, items 3/6/7
  additionally require backend EP5/EP7/EP1 deployed). `connectedAndroidTest` is intentionally NOT run
  (BootReceiver crashes the Gradle connected run). Marked `[~]`; awaits a tester device pass.
- **TP10 — 2026-06-18 — master coverage matrix sign-off.** Assembled the full situation/change → test matrix
  in §4: every TP1 cell (1a–9) + changes A/C/D/E + the check-out invariants + single-project FORMS regression
  + the `local`/dedup + android-422 cases map to ≥1 green automated test; **7B is explicitly asserted null**;
  no uncovered cell. Sign-off run: Kotlin `testDebugUnitTest` **193/0** + `I18nTest` 16/0 + `compileDebugKotlin`
  clean; backend `pytest` **574 pass / 33 pre-existing fail / 8 skip** (clean, no concurrency; all 33 in
  `test_transport_ai_suggestion_commands.py`). **Deviation:** three cells remain non-automated by design and
  are acknowledged in the matrix — TP4 authenticated-foreground sub-cases & the TP9 device matrix (device-only),
  and TP8 prod e2e (pending deploy + opt-in). No production code changed in TP10 (doc/test bookkeeping only).
- **temp002.md doc-revert (2026-06-18).** The TP8/TP9/TP10 tracker ticks, the §3 TP7–TP10 entries and the §4
  final coverage matrix were silently lost between sessions (file reverted to ~TP7 state) — almost certainly an
  IDE buffer of `temp002.md`, open during the splash/Instruções UI work, saving a stale copy over the on-disk
  edits. The underlying deliverables (test files, TP9 APK + checklist, conftest guard) were never affected.
  Re-applied here. **Lesson:** when editing a tracker doc the user may have open in the editor, expect IDE
  saves to clobber on-disk edits; re-verify the file after a stretch of unrelated work.

---

## 4. Baseline log (filled by EP0, then mostly read-only)
- **Kotlin unit suite** (`testDebugUnitTest`, EP0 — 2026-06-17): **148 passed / 0 failed / 0 skipped → GREEN**
  (task UP-TO-DATE; a failed test task is never UP-TO-DATE). `compileDebugKotlin` clean. **12 test classes.**
- **Backend pytest** (`pytest -q`, repo root, EP0 — 2026-06-17): **555 passed / 33 failed / 2 skipped**
  (138 warnings, ~8m45s), run with `--ignore=tests/test_api_flow.py` (see anomaly EP0-3). **All 33 failures
  are PRE-EXISTING & UNRELATED** — entirely in `tests/test_transport_ai_suggestion_commands.py` (a
  transport-AI subprocess harness asserting HTTP `201` but the endpoint returns the async `passengers_reset`
  path; failing since at least the May-23 `pytest_output.txt`). **plan002 must add ZERO new failures beyond
  this set.** Baseline = "≤33 known failures, all in that one transport-AI file."
- **Test inventory:**
  - *Kotlin (12):* `data/local/AppPreferencesDataSourceTest`, `domain/checkrules/ScheduledPauseTest`,
    `domain/clientstate/ClientStateFunctionsTest`, `i18n/I18nTest`,
    `platform/background/AccidentNotificationDecisionTest`, **`domain/checkrules/AutoActivitiesTest`**,
    **`checkrules/AutoActivitiesSituationTest`**, **`domain/usecase/RunAutomaticActivitiesOfflineTest`**,
    `platform/background/offline/OfflineCheckQueueTest`, `platform/background/offline/PendingCheckReplayerTest`,
    `presentation/check/AutoActivitiesHealthTest`, `presentation/check/AutoActivitiesNudgeTest`
    (**bold** = the engine/situation/offline suites EP6/TP1-3 must keep green).
  - *Backend /check + FORMS:* `tests/routers/test_web_check_state.py`,
    `tests/routers/test_web_check_state_current_day_checkin.py`, `tests/services/test_forms_submit_resilience.py`,
    `tests/services/test_forms_submit_gates.py`, `tests/services/test_forms_worker_concurrency.py`,
    `tests/services/test_forms_queue_worker_down_warning.py`, `tests/test_api_flow.py` (collection-blocked — EP0-3).
- **Protected check-out + single-project FORMS snapshot (the references EP6/EP7 must NOT regress):**
  - *Check-OUT in `domain/checkrules/AutoActivities.kt`:* const `AUTOMATIC_CHECKOUT_LOCATION="Fora do Local de
    Trabalho"` (L9); `isCheckoutZoneLocationName()` (L16); checkout-zone branch inside
    `shouldAttemptAutomaticLocationEvent` (L133); `shouldAttemptAutomaticOutOfRangeCheckout` (L147 — Situation
    1-out/2, fires checkout on `outside_workplace`); mixed-zone toggle → `CHECKOUT` (L163–176);
    `resolveAutomaticActivityForMatch` MATCHED → `AutomaticActivity(CHECKOUT, AUTOMATIC_CHECKOUT_LOCATION)`
    (L201–202). These branches/timing/locations stay byte-identical.
  - *Single-project FORMS in `services/forms_submit.py`:* `submit_forms_event()` (L45) → gate
    `should_enqueue_forms_for_action()` (L88) → exactly **one** `enqueue_forms_submission(request_id=
    client_event_id, …)` (L169) per applicable event; idempotency via `client_event_id`/`source_request_id`
    (L64/132/203). EP7 must add multi-project WITHOUT changing the single-project result.
- **`git status` (both repos) — NOT clean (see anomaly EP0-1):** the temp002 baseline is taken **on top of the
  completed-but-uncommitted temp001 work**. *Kotlin repo* (`checking_kotlin`): 16 modified + 1 deleted
  (`PermissionsDialog.kt`) + 3 untracked (nudge card/test + `presentation/check` test dir) — the temp001 P0–P6
  changes (incl. the authorized i18n edit to the protected `AutoActivityForegroundService.kt`). *Root repo*
  (`checking`): pre-existing `M` on `sistema/app/static/check/*` (frontend JS) + several docs M/D + untracked
  plan/temp docs (`plan002.md`, `temp001.md`, `temp002.md`, the P6.2 checklist, the kotlin rules file,
  `.claude/`, `pytest_output.txt`). **No `git commit` performed** (per golden rule 10).
- **TP0 test harness (2026-06-18):**
  - *Kotlin engine roots:* `app/src/test/.../domain/checkrules/AutoActivitiesTest.kt` (pure-function calls)
    and `app/src/test/.../checkrules/AutoActivitiesSituationTest.kt` (end-to-end via
    `RunAutomaticActivitiesUseCase` with mocked location/repo). **Factories** (one line per situation,
    already present): `match(status, resolvedLocal, nearest, minimum)` → `LocationMatch`;
    `history(last, currentLocal, lastCheckinAt, lastCheckoutAt)` → `HistoryState`; `run(match, state)`;
    `assertSubmitted(result, action, local)` / `assertNoSubmit(result)`. **Fixed clock:**
    `mockk<Clock> { every { now() } returns Instant.parse("2026-06-16T12:00:00Z") }` (+ explicit
    `referenceTime`/`lastCheckinAt` for mixed-zone cooldown) → deterministic time for TP3 / first-check-in-of-day.
  - *Backend roots:* `tests/` (esp. `tests/routers/`, `tests/services/`); per-test isolated SQLite via
    `_make_session(tmp_path)`, or the shared in-process `TestClient(app)` + login session. No network.
  - *Prod-safety opt-in (plan002 §0.6):* `tests/conftest.py` registers the **`prod_e2e`** marker and a
    `pytest_collection_modifyitems` hook that **skips** any `@pytest.mark.prod_e2e` test unless
    **`CHECKING_E2E_PROD=1`**. Self-verified by `tests/test_prod_e2e_guard.py`. Default suites are fully
    offline (607 backend tests collect; Kotlin unit tests are pure/mocked).
- **Final coverage-matrix result (TP10) — 2026-06-18:** every situation/change cell maps to ≥1 green
  automated test. No uncovered cell. `7B = null` is asserted (not a check-in). Run snapshot at sign-off:
  Kotlin `testDebugUnitTest` **193 / 0 fail**, `I18nTest` 16/0, `compileDebugKotlin` clean; backend
  `pytest -q --ignore=tests/test_api_flow.py` **574 pass / 33 pre-existing fail / 8 skip** (all 33 in
  `test_transport_ai_suggestion_commands.py`, EP0-2; zero in scope).

  | Situation / change | Primary test (file::case) |
  |---|---|
  | 1a NOT_IN_KNOWN_LOCATION, last=check-in → check-in "não Cadastrada" | `SituationMatrixTest`::1a + `LocationChangeContinuationTest` (cycle) |
  | 1b NOT_IN_KNOWN_LOCATION, last=check-out → **null** | `SituationMatrixTest`::1b + `CheckoutPreservationTest` |
  | 2a/2b ACCURACY_TOO_LOW → **null** (both last-states) | `SituationMatrixTest`::2a/2b + `LocationChangeContinuationTest` |
  | 3a/3b NO_KNOWN_LOCATIONS → **null** | `SituationMatrixTest`::3a/3b |
  | 4a known loc, last=check-out → **check-in** | `SituationMatrixTest`::4a + `DuplicateEliminationTest` (A→B→C) |
  | 4b known loc same as last check-in → **null** (change A) | `SituationMatrixTest`::4b + `DuplicateEliminationTest` (two-runs→1) + `OrchestratorSingleFlightTest` |
  | 5a/5b "não Cadastrada" continuation | `SituationMatrixTest`::5a/5b + `LocationChangeContinuationTest` (full cycle) |
  | 6a known loc ≠ last check-in loc → **check-in** (change A) | `SituationMatrixTest`::6a + `LocationChangeContinuationTest` (Portaria→Refeitorio) |
  | 6b same loc → **null** | `SituationMatrixTest`::6b |
  | 7A check-out preserved | `SituationMatrixTest`::7A + `CheckoutPreservationTest` |
  | **7B → null** (no check-in) | `SituationMatrixTest`::7B (explicit null assert) |
  | 8a–8d edge states | `SituationMatrixTest`::8a/8b/8c/8d + `CheckoutPreservationTest`::8a/8d |
  | 9 auto OFF → no engine run | `OrchestratorToggleGateTest` (TOGGLE_OFF) + `CheckViewModelForegroundTest` (unauth) |
  | Change C foreground trigger | EP3 (`onForegroundResume`) + `CheckViewModelForegroundTest`; device pass TP9 |
  | Change D history+location | `CheckHistoryMapperTest` + `tests/test_web_check_history.py` + `CheckHistoryDialogSmokeTest` (instrumented) |
  | Change E FORMS per project | `tests/services/test_forms_submit_per_project.py` (1–6,8) + `test_forms_per_project_worker_isolation.py` (7) |
  | Check-out invariants (never 2 consecutive; next-after-checkout=check-in) | `CheckoutPreservationTest` (sequences) |
  | Single-project FORMS regression | `test_forms_submit_per_project.py`::single-project byte-for-byte |
  | `local` column + dedup invariance | `tests/test_checking_history_local.py` |
  | android "não Cadastrada" check-in allowed; web/check-out still 422 | `tests/test_web_check_submit_unregistered_local.py` (a/b/c) |
  | prod_e2e guard | `tests/test_prod_e2e_guard.py` (skip-unless-flag) |

  **Non-automated (acknowledged):** TP4 authenticated-foreground sub-cases & TP9 device matrix
  (no device / emulator can't fire geofences); TP8 prod e2e (pending EP1/EP5/EP7 deploy + operator opt-in).

### Protected behaviors — MUST remain identical end-to-end
- Automatic **check-out** in every case; no two consecutive check-outs; after check-out → next is check-in.
- TIMER **skip-if-unchanged** stays.
- Manual mode (auto OFF): "Local" dropdown + manual submit flow (Situation 9).
- Offline queue capture + replay at original capture time.
- Browser web app's 422 on "Localização não Cadastrada".
- **Single-project FORMS:** one submission per applicable event, exactly as today.

---

# EXECUTION PHASES (drive `plan002.md` to completion)

> Each EP is a thin, didactic wrapper: it recaps the goal/context and tells you which `plan002.md`
> prompt(s) to apply. **Apply them exactly as written in `plan002.md`.** Then run that EP's Verify.

## EP0 — Baseline (apply plan002 P0.1, P0.2)
**Goal:** prove both suites green and snapshot what must not regress.
**Do:** run `./gradlew testDebugUnitTest` + `compileDebugKotlin` (in `checking_kotlin/`) and `pytest -q`
(repo root). Record counts/date and the protected-behavior snapshot in Section 4. If Kotlin is red, STOP.
**Verify:** Section 4 has baseline counts + clean `git status` (both repos).
**Update:** tick EP0; log anomalies.

## EP1 — Backend: history with location (apply plan002 P1.1, P1.2)
**Goal:** add nullable `local` to `CheckingHistory` (migration) + populate via `record_checking_history`
(local is available in `create_user_sync_event`); add `GET /check/history` returning action/projeto/
local/time/informe. **Do NOT** add `local` to the `uq_checkinghistory_event` unique key.
**Verify:** `pytest -q` green incl. new history-endpoint tests; migration applies on fresh SQLite.
**Update:** tick EP1. **Backend change → flag for human approval before any deploy (Section 3).**

## EP2 — Kotlin: history dialog with location (apply plan002 P2.1, P2.2)
**Goal:** DTO + `CheckApi.getHistory` + repo + domain `CheckHistoryEntry(action, projeto, local, time,
informe)`; a `CheckHistoryDialog` table (Data/Hora/Local) opened by tapping the two `HistoryCard` cells;
i18n in all 6 dicts; show "-" when `local` is null.
**Verify:** `compileDebugKotlin` + `testDebugUnitTest` + `I18nTest` green.
**Update:** tick EP2.

## EP3 — Kotlin: foreground trigger (apply plan002 P3.1)
**Goal:** in `onForegroundResume()`, when `isAuthenticated && automaticActivitiesEnabled`, launch
`orchestrator.runOnce(OrchestratorTrigger.FOREGROUND)` (mirror `onRefreshLocation`). No second lifecycle
observer; never when auto is OFF.
**Verify:** `compileDebugKotlin` + `testDebugUnitTest` green.
**Update:** tick EP3.

## EP4 — (REMOVED) Check-in dedup
**This phase has no work.** The 10-min dedup was dropped; the duplicate check-in is fixed by **EP6 / P6.1**
(check-in only on location change), per the 2026-06-17 production-log investigation (plan002 §0 "B —
REMOVED"). Do **NOT** implement `shouldDedupeCheckIn` or any time-window/same-location guard. EP numbers
are kept stable so cross-references hold; proceed straight to EP5. (The duplicate fix is *verified* later
by TP3.)

## EP5 — Backend: allow "Localização não Cadastrada" check-in for the app (apply plan002 P5.1)
**Goal:** relax `_reject_non_operational_web_submit_local` ONLY when client == `checking-android` AND
action == check-in. Web app + any check-out still 422.
**Verify:** `pytest -q` green incl. (a) web+local→422, (b) android+checkin+local→200, (c)
android+checkout+local→422.
**Update:** tick EP5. **Backend change → flag for human approval before any deploy.**

## EP6 — Kotlin: engine location-change check-in + continuation (apply plan002 P6.1, P6.2)
**Goal:**
- P6.1: in `shouldAttemptAutomaticLocationEvent`, matched+last=check-in returns true only if
  `normalizeLocationName(resolvedLocal) != normalizeLocationName(resolveRecordedCheckInLocation(remoteState))`
  (suppress same-location re-check-in). KEEP skip-if-unchanged. **This is the root-cause fix for the
  duplicate check-in** (plan002 §0 "B — REMOVED"); verified by TP3.
- P6.2: in `resolveAutomaticActivityForMatch`, add `NOT_IN_KNOWN_LOCATION` branch → check-in
  "Localização não Cadastrada" when last action = check-IN and the last check-in wasn't already that;
  else null. Leave check-out branches untouched.
**Verify:** `testDebugUnitTest` green; diff shows only the targeted branches changed; offline replay
coherent. (TP1/TP2 will exhaustively re-verify.)
**Update:** tick EP6.

## EP7 — Backend: FORMS per project (apply plan002 P7.1, P7.2)
**Goal:** in `submit_forms_event`, when `should_queue_forms`, enqueue one `FormsSubmission` **per
project** the user is registered in (per-project `request_id = f"{client_event_id}:{project}"`,
per-project `is_forms_enabled_for_project` gate, per-project `source_request_id`), keeping the per-user
trigger timing (first check-in of day / check-out). Single-project user → exactly one submission
(unchanged). Unsupported project fails only its own submission.
**Verify:** `pytest -q` green incl. P80+P83→two; single-project→one; forms-disabled skip; idempotency on
replay; unsupported-project isolation. (TP5 expands this.)
**Update:** tick EP7. **Backend change → flag for human approval before any deploy.**

## EP8 — Update the rules file (apply plan002 P8.1)
**Goal:** edit `docs/regras_e_situacoes/regras_checkin_checkout_kotlin.txt` to reflect: location-change
check-in (Situações 4/6), "Não Cadastrada" continuation (Situações 3/5), foreground
trigger, FORMS per project; restate the preserved check-out invariants. **Situation 7B is RESOLVED
(follows Situação 3): a checked-out user in a "near but outside" zone gets NO check-in — check-in only on
entering a registered area (Variant 7A). The rules file's 7A/7B text was already corrected when this
decision was taken; just verify it stays consistent and do not revert it.** Do **NOT** add a "dedup de
10 min" rule to the file — that workaround was dropped (the duplicate is fixed by P6.1 / change A); state
instead that check-in happens only on location change.
**Verify:** re-read for consistency with EP5–EP7 (EP4 was removed).
**Update:** tick EP8.

---

# PHASE T — IMMENSE verification suite

> Runs **after** EP0–EP8 (the rules file then reflects the new behavior). Goal: prove **every** situation
> in `regras_checkin_checkout_kotlin.txt` behaves correctly **automatically when "Atividades Automáticas"
> is ON**, prove FORMS is submitted **for each project** the user is in, and prove check-out and all
> existing flows are untouched. Backbone = pure unit tests on the engine (fast, deterministic, no
> network); then use-case/integration tests; then backend pytest; then guarded production e2e; then a
> device matrix.

## Prompt TP0 — Test harness, credentials, prod-access safety
**Goal:** stand up the test infrastructure and the safety rules everything else depends on.
**Context to load:** Read Section 0 (esp. 0.5–0.7), `docs/Instrucoes/instrucoes_acesso_Digital_Ocean.md`,
the existing Kotlin engine tests (`domain/checkrules/AutoActivitiesTest.kt`,
`checkrules/AutoActivitiesSituationTest.kt`), and the existing backend `/check` + FORMS tests in `tests/`.
**Steps:**
1. Confirm how engine unit tests build inputs: `LocationMatch(matched, resolvedLocal, label, status,
   message, accuracyMeters, accuracyThresholdMeters, minimumCheckoutDistanceMeters,
   nearestWorkplaceDistanceMeters)` and `HistoryState(found, chave, projeto, currentAction, currentLocal,
   hasCurrentDayCheckin, lastCheckinAt, lastCheckoutAt, transportEnabled)`. Build small factory helpers in
   the test source so each situation reads as one line.
2. Document a fixed clock for time-dependent tests (use the injected `Clock` / a fake instant) so the
   duplicate-elimination test (TP3) and the "first check-in of day" FORMS rule are deterministic.
3. Write down the prod-safety rules from §0.6 at the top of any test file that can reach prod. Add a
   guard/skip so prod-touching tests run only with an explicit opt-in env var (e.g.
   `CHECKING_E2E_PROD=1`) and never in the default suite.
4. Record in Section 4: the test source roots, the chosen fixtures/factories, and the opt-in flag.
**Do NOT:** make the default test run hit production. **Verify:** the default `testDebugUnitTest` +
`pytest -q` run fully offline. **Update:** tick TP0.

## Prompt TP1 — Engine SITUATION MATRIX (all 9 situations)
**Goal:** one explicit, named unit test per situation (and per relevant variant) on the **pure** engine
`resolveAutomaticActivityForMatch(match, currentState, mixedZoneIntervalMinutes)`, asserting the decided
`AutomaticActivity(action, local)?` for the **post-plan002** behavior. All cases assume auto-activities ON
(the orchestrator gate is tested in TP4). Add them to `AutoActivitiesSituationTest.kt` (or a new
`SituationMatrixTest.kt`).

**The matrix (assert exactly):**

| # | Situation (rules file) | Input: MatchStatus / resolvedLocal | Last action (+ last check-in local) | Expected `AutomaticActivity` | Note |
|---|---|---|---|---|---|
| 1a | 1 — leaving to CheckOut zone | MATCHED / "Zona de CheckOut" | check-in | **CHECKOUT**, local "Zona de CheckOut" | unchanged |
| 1b | 1 — far (>2km) | OUTSIDE_WORKPLACE | check-in | **CHECKOUT**, local "Fora do Local de Trabalho" | unchanged |
| 2a | 2 — CheckOut zone, already out | MATCHED / "Zona de CheckOut" | check-out | **null** (no action) | unchanged |
| 2b | 2 — far, already out | OUTSIDE_WORKPLACE | check-out | **null** | unchanged; never 2nd check-out |
| 3a | 3 — enters registered area | MATCHED / "P80-Portaria" | check-out | **CHECKIN**, local "P80-Portaria" | unchanged |
| 3b | 3-IMPORTANT — near but outside | NOT_IN_KNOWN_LOCATION | check-out | **null** | unchanged (Q1: no check-in out-of-area when last=checkout) |
| 4a | 4 — same registered area | MATCHED / "P80-Portaria" | check-in @ "P80-Portaria" | **null** (no action) | **CHANGED by P6.1** (was re-check-in) |
| 4b | 4 — different registered area | MATCHED / "P80-Refeitorio" | check-in @ "P80-Portaria" | **CHECKIN**, local "P80-Refeitorio" | location changed |
| 5a | 5 — near but outside, was checked-in elsewhere | NOT_IN_KNOWN_LOCATION | check-in @ "P80-Portaria" | **CHECKIN**, local "Localização não Cadastrada" | **CHANGED by P6.2** |
| 5b | 5 — near but outside, already "Não Cadastrada" | NOT_IN_KNOWN_LOCATION | check-in @ "Localização não Cadastrada" | **null** | no repeat (change-only) |
| 6a | 6 — refresh, same area | MATCHED / "P80-Portaria" | check-in @ "P80-Portaria" | **null** | same as 4a (trigger=FOREGROUND in TP4) |
| 6b | 6 — refresh, different area | MATCHED / "P80-Refeitorio" | check-in @ "P80-Portaria" | **CHECKIN**, local "P80-Refeitorio" | same as 4b |
| 7A | 7 — leaves CheckOut → registered area | MATCHED / "P80-Portaria" | check-out | **CHECKIN**, local "P80-Portaria" | = 3a |
| 7B | 7 — leaves CheckOut → near but outside | NOT_IN_KNOWN_LOCATION | check-out | **null** (no action) | **RESOLVED**: follows Situação 3 — no check-in when checked-out & out-of-area |
| 8a | 8 — Zona Mista, last check-in (cooldown elapsed) | MATCHED / "Zona Mista" | check-in @ "Zona Mista", ts older than interval | **CHECKOUT**, local "Zona Mista" | unchanged (mixed-zone toggle) |
| 8b | 8 — Zona Mista, last check-out (cooldown elapsed) | MATCHED / "Zona Mista" | check-out @ "Zona Mista", ts older than interval | **CHECKIN**, local "Zona Mista" | unchanged |
| 8c | 8 — Zona Mista, within cooldown | MATCHED / "Zona Mista" | same action @ "Zona Mista", ts within interval | **null** | unchanged (cooldown blocks) |
| 8d | 8 — exception: from Mista check-in → far/CheckOut | OUTSIDE_WORKPLACE or "Zona de CheckOut" | check-in @ "Zona Mista" | **CHECKOUT** | unchanged (immediate, ignores cooldown) |
| 9  | 9 — auto OFF | (engine not called) | any | **engine never invoked** | TP4 asserts the orchestrator toggle gate |

> **✅ RESOLVED (case 7B) — decided by the product owner:** follow Situação 3 (line 30). A **checked-out**
> user passing through a "near but outside" (unregistered) zone gets **no check-in** (`NOT_IN_KNOWN_LOCATION`
> + last action = check-out → **null**). A checked-out user is checked in **only** upon entering a
> **registered** area (≠ "Zona de CheckOut") — Variant 7A. This matches Q1 and the current/post-plan002
> engine, so it needs **no engine change**. Assert 7B = **null** (do NOT `@Ignore`). The rules file's
> Situação 7A/7B text has been corrected accordingly.

**Do NOT:** change the engine to make a test pass — tests encode the agreed behavior; engine changes only
come from EP6. **Verify:** all matrix tests green (incl. 7B asserting **null**).
**Update:** tick TP1.

## Prompt TP2 — Location-change-only + "Não Cadastrada" continuation
**Goal:** beyond the matrix, exhaustively pin change A.
**Tests (engine, pure):**
1. Repeated identical MATCHED reads while checked-in at the same area → first read after a *different*
   prior location checks in; subsequent identical reads → null (no re-check-in). Confirms "only on change".
2. Sequence P80-Portaria(check-in) → P80-Portaria again → P80-Refeitorio: only the move to Refeitorio
   checks in.
3. NOT_IN_KNOWN_LOCATION continuation: check-in@area → near-but-outside → check-in "Não Cadastrada" →
   still near-but-outside → null → back inside area → check-in@area.
4. last action = check-out + NOT_IN_KNOWN_LOCATION → null (never check-in out-of-area when checked out).
5. ACCURACY_TOO_LOW and NO_KNOWN_LOCATIONS → always null (regardless of last action).
**Do NOT:** rely on the orchestrator here (pure engine only). **Verify:** green. **Update:** tick TP2.

## Prompt TP3 — Duplicate-elimination (the prod bug) via P6.1
**Goal:** prove the **duplicate check-in is gone** — the exact bug seen in production on 2026-06-17 (a
location change firing geofence EXIT(old)+ENTER(new) produced two check-ins at the same new location,
seconds apart, distinct UUIDs). The fix is change A / P6.1 (check-in only on location change); there is
**no** 10-min dedup. This prompt pins that the multi-trigger scenario now yields exactly ONE submit. The
pure-engine "same location → null" assertions live in TP1 (4a/6a) and TP2; here we test the LIVE flow.
**Tests (`RunAutomaticActivitiesUseCase` / orchestrator integration, fake repo + fake `Clock`):**
1. **Two sequential runs, same new location (the bug):** start state = last check-in at A. Run 1 with
   location B (≠ A) → submits ONE check-in at B and updates the cached state to "check-in at B". Run 2
   with location B, reading that updated state → engine returns null → **no second submit**. (Simulates
   geofence EXIT(A)+ENTER(B): two triggers → one check-in.)
2. **Concurrent runs blocked by single-flight:** while run 1 holds the orchestrator `Mutex`, a second
   `runOnce` returns immediately (`tryLock` fails) → no extra submit. (The sequential case in #1 is the
   one P6.1 covers; this is the concurrent guard.)
3. **Stationary repeats:** repeated runs at the same location after a check-in there → all null (no
   re-check-in) — the duplicate cannot accumulate over time.
4. **Genuine move still works:** A → B → C (distinct locations) → exactly one check-in per distinct
   location (the fix must NOT suppress real location-change check-ins).
5. **Offline edge (documented, NOT a regression):** if run 1's submit FAILS (network) the cached state is
   not updated, so run 2 may re-decide a check-in at B → assert this is the known, unchanged edge case
   (the removed 10-min dedup never covered it either). Do **NOT** add a guard for it.
**Verify:** green. **Update:** tick TP3.

## Prompt TP4 — Foreground trigger + the auto-activities toggle gate
**Goal:** pin change C and Situation 9.
**Tests:**
1. VM test: `onForegroundResume()` with `isAuthenticated && automaticActivitiesEnabled` → calls
   `orchestrator.runOnce(FOREGROUND)` (verify via a test double / spy). With auto OFF → does NOT call it.
   With not authenticated → does NOT call it.
2. Orchestrator gate (Situation 9): `runOnceLocked` with `automaticActivitiesEnabled = false` →
   `EvaluationOutcome.TOGGLE_OFF`, no GPS/match/submit. (Use the existing diagnostics/EvaluationLog seam.)
3. Foreground at the same location while checked-in → engine returns null → no duplicate check-in
   (combines change A + the FOREGROUND trigger).
**Verify:** green (instrumented parts marked pending-for-device if needed). **Update:** tick TP4.

## Prompt TP5 — FORMS submitted for EVERY project (change E)
**Goal:** the headline requirement — FORMS once per project the user is registered in.
**Context to load:** `forms_submit.py`, `forms_queue.py`, `forms_worker.py`, `user_sync.py`
(`should_enqueue_forms_for_action`), `project_catalog.py`, the `FormsSubmission` model + its unique
constraint, and existing FORMS tests in `tests/`.
**Backend pytest (LOCAL only — never prod; FORMS automation is mocked at the worker boundary):**
1. **Multi-project first check-in of the day:** user in `["P80","P83"]`, both forms-enabled, first
   check-in of the day → **exactly two** `FormsSubmission` rows, one `projeto="P80"` and one
   `projeto="P83"`, with **distinct** `request_id`s (e.g. `<event>:P80`, `<event>:P83`) and
   `project_candidates` each = its own project.
2. **Multi-project check-out:** same user, a check-out → **two** submissions (one per project).
3. **Trigger timing unchanged:** a **second** check-in the same day (not the first) → **zero** new FORMS
   submissions (first-check-in-of-day rule preserved, just multiplied by project on the first).
4. **Single-project regression:** user in `["P80"]` → **exactly one** submission per applicable event
   (identical to today). This is the protected-behavior guard.
5. **forms_enabled per project:** user in `["P80","P83"]` with P83 forms-disabled → only P80 enqueued;
   P83 recorded as a per-project skip (diagnostics accurate), not a failure.
6. **Idempotency / replay:** replaying the same logical event (same client_event_id) → no duplicate
   submissions and no duplicate `CheckingHistory`/`UserSyncEvent` rows per project.
7. **Unsupported project isolation:** user in `["P80", "PXX"]` where PXX has no Forms xpath mapping →
   P80 submits, PXX fails/skips **only its own** row, P80 unaffected.
8. **History per project:** after a check-in, assert one `CheckingHistory` row per project for that event
   (so the history dialog can show each project's activity).
**Guarded e2e (OPTIONAL, requires `CHECKING_E2E_PROD=1` + human approval):** with chave TEST in ≥2
projects, perform ONE controlled check-out and verify (read-only, via the prod DB per §0.6) that one
`forms_submission` row exists per project. Clean up / annotate. **Never loop this.**
**Verify:** backend `pytest -q` green incl. all 8 cases. **Update:** tick TP5. **Note:** TP5 exercises a
production-behavior change — keep it LOCAL by default.

## Prompt TP6 — History with location (change D)
**Goal:** the history dialog shows date, time, and location for every entry.
**Backend pytest:** seed `CheckingHistory` rows with and without `local` (check-in and check-out, multiple
projects) → `GET /check/history?chave=TEST` returns them newest-first, action mapped to
"checkin"/"checkout", `local` passed through (null → serialized as null/empty), 422 on bad chave.
**Kotlin:** mapper test DTO→`CheckHistoryEntry` (incl. null local → "-"); a dialog smoke test (if
feasible) that the table renders Data/Hora/Local rows and the empty state.
**Verify:** `pytest -q` + `testDebugUnitTest` green. **Update:** tick TP6.

## Prompt TP7 — Check-out preservation regression
**Goal:** prove every check-out path is byte-for-byte unchanged after all edits.
**Tests:** re-run/extend the existing check-out engine tests + assert matrix cases 1a/1b/2a/2b/7A/8a/8d.
Diff-review `AutoActivities.kt` to confirm only the check-IN branches (P6.1/P6.2) changed and the
check-out branches/`shouldAttemptAutomaticOutOfRangeCheckout`/mixed-zone toggle are identical to the EP0
baseline. Assert the "no two consecutive check-outs" invariant (2a/2b) and "after check-out → next is
check-in" (3a/7A).
**Verify:** green; diff confirms no check-out logic change. **Update:** tick TP7.

## Prompt TP8 — End-to-end against the live API (chave TEST)
**Goal:** confirm the wired system (client ↔ backend) behaves, using prod **read-mostly**.
**Context:** §0.6 prod-safety; `https://tscode.com.br/api`; login chave `TEST` / senha `000000`.
**Steps (default = read-only; submits require `CHECKING_E2E_PROD=1` + human approval):**
1. Read-only: `GET /api/health` ok; authenticate TEST; `GET /check/state` (last check-in/out);
   `GET /check/history?chave=TEST` returns the new list **with location** (validates EP1 deployed);
   `GET /check/locations` lists TEST's areas.
2. Inspect prod DB read-only (per §0.6) to confirm, for a recent TEST event: one `checkinghistory` row
   per project, `forms_submission` rows per project, and `check_events.local` matches the history.
3. Controlled submit (guarded): with TEST checked-out and standing inside a registered area, one app
   foreground → exactly one check-in at that area; foreground again at the same spot → **no** duplicate;
   then verify via `GET /check/history`. Undo/annotate as needed.
4. The "Não Cadastrada" continuation against the deployed backend: confirm EP5 accepts an android
   check-in with that local (HTTP 200) and the web app still gets 422 (negative check).
**Do NOT:** run repeated submits; never trigger FORMS-per-project loops against prod; never expose the
deploy key. **Verify:** read-only checks pass; any guarded submit is annotated + cleaned. **Update:** tick TP8.

## Prompt TP9 — Device / instrumented matrix (only a device can prove)
**Goal:** validate the parts unit tests cannot: real geofence wake-ups, the FGS 15-min TIMER + skip,
foreground lifecycle, and notifications. Requires a real device (emulator can't reliably fire geofences;
per memory geofence doesn't trigger in the emulator).
**Checklist (mark pending-for-device if no device):**
1. Auto-activities ON, stationary inside an area → **no** repeated check-in across multiple 15-min ticks
   (skip-if-unchanged + change A).
2. Walk out of area A into area B → **exactly one** check-in at B, even though the move fires geofence
   EXIT(A)+ENTER(B) (two triggers); a later TIMER tick or foreground at B → **no** further check-in
   (P6.1 — same location). This is the on-device confirmation that the duplicate is gone.
3. Checked-in, walk to "near but outside" → check-in "Localização não Cadastrada" once; stay → no repeat.
4. Checked-in, go far / into CheckOut zone → **check-out** (unchanged); never a second check-out.
5. Foreground the app in a new area → one correct check-in/out.
6. User in P80+P83: first check-in of day → FORMS for **both** (verify via admin / prod DB read-only);
   check-out → both.
7. Tap "ÚLTIMO CHECK-IN"/"ÚLTIMO CHECK-OUT" → tables load with **location**.
8. Manual mode (auto OFF): nothing auto-submits; "Local" dropdown works (Situation 9).
**Verify:** each item passes or is explicitly pending-for-device with human acknowledgement.
**Update:** tick TP9; record in Section 3/4.

## Prompt TP10 — Master coverage matrix sign-off
**Goal:** prove every situation + every change is covered by a passing test (or an acknowledged
device/pending item).
**Steps:**
1. Build a checklist mapping each row of the TP1 matrix (1a…9) and each change (A, C, D, E — **B was
   removed**; the duplicate fix is part of A, covered by TP1 4a/6a + TP2 + TP3) to the specific test(s)
   that assert it (file::testName). Every row must point to ≥1 green test (incl. 7B = null).
2. Full runs: Kotlin `testDebugUnitTest` (count ≥ EP0 baseline; new tests added; none deleted to pass) +
   `I18nTest` parity; backend `pytest -q` (no new failures vs baseline). `compileDebugKotlin` clean.
3. Confirm check-out + single-project FORMS regression tests (TP5#4, TP7) are green.
4. Record the final matrix + counts in Section 4.
**Verify:** the matrix has no uncovered cell (7B explicitly flagged). **Update:** tick TP10.

---

## Acceptance summary
Done when: Section 2 fully ticked (EP0–EP8, TP0–TP10); both suites green (Kotlin count ≥ baseline; backend
no new failures); the TP1 situation matrix is fully covered (7B resolved = null); the **duplicate check-in
is proven eliminated** by P6.1 (TP3, plus matrix 4a/6a + TP2); **FORMS is verified to submit once per
project** (TP5) and **single-project FORMS is unchanged**;
**history shows location** (TP6); check-out paths and skip-if-unchanged are unchanged (TP7); and the
device matrix (TP9) is passed or acknowledged. Backend changes (EP1, EP5, EP7) require explicit human
approval before any push (production deploy). Do not commit/push unless asked.
