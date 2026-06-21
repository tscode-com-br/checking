# Checking — Check-in / FORMS / History Changes: Cautious Implementation Plan (agent prompts)

> **Audience:** an AI coding agent that executes the changes one prompt at a time.
> **Prime directive:** the app works **very well**, and **check-out is perfect and must stay intact**.
> This plan changes only: (A) when an automatic **check-in** fires — which also **fixes the duplicate
> check-in** at its root; (C) running the engine on app foreground; (D) a read-only **history** view with
> **location**; and (E) **FORMS submission per project**. *(Change "B — de-duplication" was dropped — the
> duplicate is fixed by change A; see §0. Letters C/D/E are kept as-is to avoid breaking cross-references.)*
> Anything that would alter check-out, the offline queue semantics, the mixed-zone logic, or the manual
> (auto-activities OFF) flow is OUT OF SCOPE — if a step seems to require it, STOP and report.

Same format as `docs/temp001.md`: numbered infra sections + phases of self-contained prompts. Execute
prompts **strictly in order**. After each prompt the project must compile and all existing tests must
pass before moving on.

This plan spans **two codebases**:
- **Kotlin app** — `checking_kotlin/` (own git repo `checking-kotlin`; see
  `docs/Instrucoes/instrucoes_acesso_repositórios_github.md` §1.7/2.6).
- **Backend monolith** — `sistema/app/` in the root repo `checking` (pushing deploys to PRODUCTION via
  `Deploy OceanDrive`; see the same instruções doc §2.1/§3.1).

> **Revision note (supersedes earlier drafts):** the 15-min "heartbeat" idea is **dropped**. Per tester
> feedback, an automatic check-in now fires **only when the user's location changes** — never a blind
> periodic re-check-in. The TIMER **skip-if-unchanged** stays in place (it saves server resources).

---

## 0. The requested changes + the resolved decisions

**A — Check-in only on location change (revised item 1).**
- Do **not** check-in every 15 minutes blindly. The 15-min TIMER still runs and verifies location, but a
  check-in is submitted **only when the resolved location differs from the user's last check-in
  location**. Same location as the previous check-in → **no action**.
- **Keep** the TIMER skip-if-unchanged optimization (do NOT remove it) — it avoids even the server match
  call when the device hasn't moved, reducing server load.
- Location-change continuation when already checked-in (decision Q1): if the **last activity was a
  check-IN** and the user moves to a spot that is "near but not inside" any registered area
  (`NOT_IN_KNOWN_LOCATION`), submit a check-in recorded as **"Localização não Cadastrada"** — but only if
  that is a *change* (i.e. the last check-in was not already "Localização não Cadastrada"). If the last
  activity was a check-OUT, never check-in outside a registered area.
- Check-out behavior is **unchanged** in every case.
- **This also fixes the DUPLICATE check-in** (confirmed in production on 2026-06-17): once the first
  trigger checks in at the new location, any further trigger for the *same* location becomes a no-op.
  See "B — REMOVED" just below for the root-cause evidence.

**B — De-duplication — REMOVED (superseded by change A / Phase 6).** This was only a workaround. A
real-time production-log investigation (2026-06-17, chaves U3RD/U390/UQL2) showed the duplicate is a
**pair of check-ins at the same location, seconds apart**, each a distinct submission (distinct
`client_event_id` UUID, `device_id=checking-android`). **Root cause:** the *current* engine re-checks-in
at the same matched location on every evaluation (Situations 4/6), and a single location change delivers
**multiple background triggers** — Android sends geofence EXIT(old)+ENTER(new) as separate broadcasts, and
the FGS also re-registers geofences with `INITIAL_TRIGGER_ENTER`. The single-flight mutex only blocks
truly *concurrent* runs; the second broadcast normally arrives after the first run finished its network
I/O, so it runs and re-checks-in. **Change A (P6.1 — check-in only on location change) fixes this at the
root:** the first trigger checks in and updates the cached state *inside the mutex*; the next trigger
reads that fresh state, sees the location unchanged, and does nothing. So the 10-minute same-location
dedup is unnecessary and is **NOT implemented**. (The only case neither approach covered was a
failed/offline first submit; that edge case is unchanged either way.)

**C — Run the engine on app open / foreground (item 3-original).** When the app is opened or foregrounded
and auto-activities is ON, run the situation engine (it decides check-in or check-out).

**D — Full history with LOCATION (items 4/5 + revised item 3).** Tapping **"ÚLTIMO CHECK-IN"** /
**"ÚLTIMO CHECK-OUT"** opens a dialog with the full history table showing **date, time, and the location**
where each activity happened, fetched from the database (decision Q2: new backend endpoint).

**E — FORMS per project (NEW item 2).** When FORMS should be filled/submitted (first check-in of the day,
and every check-out), it must happen **once per project the user is registered in** (e.g. P80 **and**
P83 → two FORMS submissions), not just one. Today only one project is submitted.

### Decisions already made by the product owner (do not re-litigate)
- **Q1:** check-in outside a registered area only as a continuation of an existing check-in (last action
  = check-in), recorded as "Localização não Cadastrada"; never when last action = check-out.
- **Q1 / Situation 7B (RESOLVED):** a **checked-out** user passing through a "near but outside"
  (unregistered) zone gets **no check-in** (`NOT_IN_KNOWN_LOCATION` + last action = check-out → null —
  this is the current engine behavior, **no code change**). A checked-out user is checked in **only** upon
  entering a **registered** area (≠ "Zona de CheckOut"), i.e. Variant 7A. Follows Situação 3 (line 30).
  The rules file's Situação 7A/7B text was corrected to match (and P8.1 keeps it consistent).
- **Q2:** items D use a **new backend endpoint** reading the database.
- **Q3 (superseded):** the proposed 10-min same-location dedup was **dropped** — change A (P6.1) fixes the
  duplicate at its root (see §0 "B — REMOVED"). The check-out invariant still stands: **never two
  consecutive check-outs; after a check-out the next activity is a check-in.**
- **Tester revision:** no blind 15-min heartbeat — check-in only on location change; keep skip-if-unchanged.

---

## 1. Global context (read before any prompt)

**Kotlin — files that matter:**
- Situation engine (PURE, single source of truth): `domain/checkrules/AutoActivities.kt`.
  - `resolveAutomaticActivityForMatch(match, currentState, mixedZoneIntervalMinutes)` → `AutoActivity(action, local)` or null.
  - `shouldAttemptAutomaticLocationEvent(...)`: for a MATCHED non-checkout/non-mixed area it currently
    returns `normalizeLocationName(resolvedLocal).isNotEmpty()` when the last action was a check-in
    (i.e. it re-checks-in at the SAME location — Situations 4/6). **This is the line that change A edits.**
  - Helpers: `resolveLastRecordedAction`, `resolveRecordedCheckInLocation`, `normalizeLocationName`.
  - Constants: `AUTOMATIC_CHECKOUT_LOCATION`, `AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION = "Localização não Cadastrada"` (already defined; currently never submitted), `MIXED_ZONE_LOCATION`.
  - ⚠ **Also used by offline replay** (`platform/background/offline/PendingCheckReplayer.kt`,
    `SyncPendingChecksWorker.kt`). Any engine change affects replay — verify both.
- Live flow: `domain/usecase/RunAutomaticActivitiesUseCase.kt` (captures location → engine → `CheckRepository.submit` → queue on network error). `clock: Clock` is injected (use `clock.now()`).
- Orchestrator (7-step, single-flight): `platform/background/BackgroundCheckOrchestrator.kt`.
  `enum OrchestratorTrigger { TIMER, GEOFENCE, FOREGROUND }`. **skip-if-unchanged** = `runOnceLocked()`
  Step 3 calls `shouldSkip()` **only for TIMER** and returns early on `SkipDecision.SKIP`. **KEEP THIS.**
- FGS 15-min loop: `platform/background/AutoActivityForegroundService.kt` (`TIMER_INTERVAL_MS = 15 min`).
- Geofence: `GeofenceBroadcastReceiver.kt` → `orchestrator.runOnce(GEOFENCE)`.
- Foreground trigger today: `CheckViewModel.kt` runs `orchestrator.runOnce(OrchestratorTrigger.FOREGROUND)`
  from `onRefreshLocation()` and after `loadUserProjects`, and `ensureEngineRunningIfEligible(...)` on
  ON_RESUME — but `onForegroundResume()` itself only calls `refreshCheckState()` (gap for change C).
- Models: `domain/model/CheckModels.kt` — `HistoryState(lastCheckinAt, lastCheckoutAt, currentAction,
  currentLocal, projeto, ...)`, `enum MatchStatus { MATCHED, ACCURACY_TOO_LOW, NOT_IN_KNOWN_LOCATION,
  OUTSIDE_WORKPLACE, NO_KNOWN_LOCATIONS }`.
- History UI: `presentation/components/HistoryCard.kt` (two cells "ÚLTIMO CHECK-IN"/"ÚLTIMO CHECK-OUT",
  currently NOT clickable; formats with zone `Asia/Singapore`). i18n keys `history.lastCheckinLabel`,
  `history.lastCheckoutLabel`, `history.today`, `history.yesterday`.
- API client: `data/api/CheckApi.kt` (Retrofit; has `getState`, `getLocations`, `matchLocation`,
  `getGeofences`, `submit`). DTOs: `data/dto/CheckDtos.kt`. Repository: `domain/repository/CheckRepository.kt`
  + `data/repository/CheckRepositoryImpl.kt`.
- Dialog scaffold (scrolls): `presentation/components/DialogScaffold.kt`. Dialog routing via
  `CheckDialog` enum in `presentation/check/CheckUiState.kt`, rendered in `CheckScreen.kt`.
- i18n: 6 dictionaries in `i18n/dictionaries/` (Pt/En/Zh/Ms/Id/Tl). `i18n/I18nTest.kt` may assert key
  parity — add every new key to all 6.

**Backend — files that matter:**
- Public check router: `sistema/app/routers/web_check.py`.
  - `GET /check/state` → `build_web_check_history_state` (last check-in/out only — NOT a list).
  - `POST /check` → `submit_web_check` calls `_reject_non_operational_web_submit_local(payload.local)`,
    raising **HTTP 422 when local ∈ `WEB_NON_OPERATIONAL_SUBMIT_LOCALS = {"Localização não Cadastrada"}`**
    (~line 170 + ~918).
  - App traffic is identified by header **`X-Client: checking-android`** (`CHECKING_ANDROID_CLIENT`,
    `WEB_CHECK_ANDROID_CHANNEL`, ~line 134) — used to scope change A's backend relaxation to the app only.
  - `_validate_public_chave(chave)` is the chave-validation helper.
- FORMS pipeline:
  - `sistema/app/services/forms_submit.py` — `submit_forms_event(...)`: decides `should_queue_forms`
    (first check-in of day OR check-out) via `should_enqueue_forms_for_action`; **gates on
    `is_forms_enabled_for_project(db, projeto=user.projeto)` (single, active project)**; computes
    `project_candidates = list_user_project_names(db, user)` (ALL the user's projects); then calls
    `enqueue_forms_submission(... projeto=user.projeto, project_candidates=...)` **once**. There is an
    idempotency short-circuit at the top: existing `UserSyncEvent` with `source == channel.user_sync_source`
    AND `source_request_id == client_event_id`.
  - `sistema/app/services/forms_queue.py` — `enqueue_forms_submission(request_id=client_event_id, projeto,
    project_candidates, ...)` writes ONE `FormsSubmission` row (has an `IntegrityError` catch on flush →
    request_id is effectively unique; **verify the exact `FormsSubmission` unique constraint in
    `sistema/app/models.py` before relying on it**). `_process_submission` → `FormsWorker.submit_with_retries(projeto, project_candidates, ...)`.
  - `sistema/app/services/forms_worker.py` — selects **one** supported project from candidates
    (`botao_projeto_{selected}`) and submits the form **once**; raises `UnsupportedProject` when no
    candidate is supported (has an xpath). **This is why only one project is submitted today.**
  - `sistema/app/services/user_sync.py` — `create_user_sync_event(... local=...)` calls
    `record_checking_history(...)` (line ~428). `should_enqueue_forms_for_action` /
    `get_forms_skip_reason` live here (the per-user "first check-in of the day" logic).
  - `sistema/app/services/project_catalog.py` — `is_forms_enabled_for_project(db, projeto=...)`.
- History table + service: `sistema/app/services/checking_history.py` — `record_checking_history(db, *,
  chave, action, projeto, event_time, ontime)` upserts a `CheckingHistory` row. **Model
  `CheckingHistory` (models.py ~691) columns: `chave, atividade ∈ {check-in,check-out}, projeto, time,
  informe`. UNIQUE(chave, atividade, projeto, time, informe). There is NO `local` column** — change D
  adds one. `CheckEvent` (models.py ~272) DOES have `local` (String(40)) but is keyed by `rfid` and is a
  broader audit log; we use `CheckingHistory` as the clean per-chave source and add `local` to it.
- Schemas: `sistema/app/schemas.py` (Pydantic v2; requests/responses separated).
- Migrations: `sistema/app/migrations/` (numbered, e.g. `0077...`). Tests: `tests/` (pytest, SQLite).

**Test / build commands:**
- Kotlin (from `checking_kotlin/`): `./gradlew testDebugUnitTest`, `./gradlew compileDebugKotlin`. Do NOT
  run `connectedAndroidTest` (BootReceiver crashes it); run instrumented via `am instrument` twice if a
  device is attached, else note "device verification pending".
- Backend (repo root): `pytest -q` (or the targeted test file).

---

## 2. Golden rules (apply to EVERY prompt)

1. **Check-out is sacred.** Do not touch `shouldAttemptAutomaticOutOfRangeCheckout`, the checkout-zone
   branch, the mixed-zone toggle, or any check-out path. Do not change check-out timing/location/frequency.
2. **No blind heartbeat.** Check-in fires only on location change. **Keep** the TIMER skip-if-unchanged.
3. **Additive-first.** New params get defaults; new endpoints/DTOs/columns/functions over editing existing
   signatures. New DB columns are nullable and NOT added to existing unique keys.
4. **The duplicate check-in is fixed at the engine layer, NOT by a time-window dedup.** Change A (P6.1 —
   check-in only on location change) is the root-cause fix; do **not** add a same-location/10-minute dedup
   guard. (Rationale + production evidence: §0 "B — REMOVED".)
5. **Engine changes (change A) also affect offline replay** — intended, but verify
   `PendingCheckReplayer`/`SyncPendingChecksWorker` stay coherent.
6. **Backend guard relaxation is scoped to the app** (change A enabler): allow "Localização não
   Cadastrada" only when `X-Client: checking-android` AND action == check-in. The browser web app must
   still 422.
7. **FORMS multi-project must preserve single-project behavior** byte-for-byte for users with one project,
   and must preserve FORMS idempotency/dedup (use a per-project `request_id` / `source_request_id`).
8. **Touch all 6 dictionaries together.** Re-run `I18nTest`.
9. **One prompt = one compilable, test-passing increment.**
10. **Do NOT `git commit`/`push`/branch** unless the human asks. Backend pushes deploy to PRODUCTION —
    never push without explicit instruction.
11. Keep the trackers (Sections 3/4/5) current before finishing a prompt. If reality differs from this
    plan, STOP, document in Section 4, and report.

---

## 3. Progress tracker (update after each prompt)

- [x] **P0.1** Capture green baseline (Kotlin unit suite + backend pytest), counts into Section 5 — 2026-06-17 (via EP0; details in temp002 §4): Kotlin 148 green, backend 555 pass / 33 pre-existing fail / 2 skip
- [x] **P0.2** Inventory tests + snapshot protected check-out + FORMS behaviors + clean trees — 2026-06-17 (via EP0; temp002 §4): trees NOT clean (on uncommitted temp001) — see temp002 §3 EP0-1
- [x] **P1.1** Backend: add nullable `local` to `CheckingHistory` (migration 0078) + populate via `record_checking_history` — 2026-06-17: 3 tests; dedup invariant on 5-field key; migration applies on fresh SQLite
- [x] **P1.2** Backend: add `GET /check/history` (returns action, projeto, local, time, informe) + pytest — 2026-06-17: `list_checking_history` + schemas + endpoint (mirrors `/check/state` auth); 3 tests
- [x] **P2.1** Kotlin: history DTO + `CheckApi.getHistory` + repository + domain model (with location) — 2026-06-17: `WebCheckHistoryItemDto`/`…ListResponseDto`, `getHistory`, `CheckHistoryEntry` (time nullable — see temp002 §3 EP2), repo mapper + `CheckHistoryMapperTest` (2)
- [x] **P2.2** Kotlin: history dialog table (date/time/location) + make the two HistoryCard cells clickable — 2026-06-17: `CheckHistoryDialog` (Data/Hora/Local, "-" for null), `CheckDialog.History` + filter, clickable cells (additive openers), 7 i18n keys × all 6 dicts; 150 tests + I18nTest green
- [x] **P3.1** Kotlin: run orchestrator FOREGROUND trigger from `onForegroundResume()` — 2026-06-17: after the existing `refreshCheckState()`, gated on `isAuthenticated && automaticActivitiesEnabled`, launches `orchestrator.runOnce(OrchestratorTrigger.FOREGROUND)`; no second observer; no-op when auto OFF. 150 tests green
- ~~**P4.1 / P4.2** (10-min check-in dedup)~~ — **REMOVED**: the duplicate is fixed by P6.1 (change A). See §0 "B — REMOVED". No work.
- [x] **P5.1** Backend: allow "Localização não Cadastrada" check-in for `X-Client: checking-android` + pytest — 2026-06-18: `_reject_non_operational_web_submit_local` now skips ONLY for android client + check-in; web app + any check-out still 422. 3 tests; full suite 564 pass / 33 pre-existing fail / 2 skip (zero new). **Prod backend — deploy needs human approval (temp002 §3 EP5-1).**
- [x] **P6.1** Kotlin: engine — check-in only on location change (MATCHED + last=checkin) + tests — 2026-06-18: final branch now requires `normalizeLocationName(resolvedLocal) != normalizeLocationName(resolveRecordedCheckInLocation(remoteState))`; skip-if-unchanged + check-out branches untouched (diff-confirmed). s4 → 2 tests (same→no-action / different→re-check-in)
- [x] **P6.2** Kotlin: engine — `NOT_IN_KNOWN_LOCATION` continuation → "Não Cadastrada" when last=checkin + tests — 2026-06-18: new branch (checkin + last≠"não Cadastrada" → check-in "Localização não Cadastrada", else null); doc-comment updated; s5 → 2 tests + offline-replay coherence (PendingCheckReplayerTest). 153 tests green
- [x] **P7.1** Backend: enqueue FORMS **per project** in `submit_forms_event` (per-project request_id + gate) + pytest — 2026-06-18: multi-project loop (`_enqueue_forms_per_project_and_record`); single-project path byte-for-byte (bare request_id); per-project `{client_event_id}:{sha1[:12]}` (String(80)-safe); per-project forms_enabled gate; per-project idempotency + full-replay short-circuit. 6 tests
- [x] **P7.2** Backend: verify worker/idempotency/user_sync for multi-submission; graceful unsupported-project + pytest — 2026-06-18: **no worker change needed** — `_process_submission` already processes one row at a time with `project_candidates=[project]` (single candidate), so an `UnsupportedProject` fails only its own row. Verified structurally (each row carries a single candidate) in tests
- [x] **P8.1** Update `docs/regras_e_situacoes/regras_checkin_checkout_kotlin.txt` — 2026-06-18: Situações 4/6 → check-in só por mudança de localização; Situação 5 → continuação "Localização não Cadastrada" (como mudança); nota IMPORTANTE da Situação 3 corrigida (cross-ref à S5); 7A/7B mantidos; bloco "Observações Gerais" (foreground, sem dedup-10min, FORMS por projeto, invariantes de check-out). Docs-only
- [ ] **P9.1** Final integrity verification (check-out + single-project FORMS intact) + device checklist

---

## 4. Deviations log (append-only)

> `Pxx — YYYY-MM-DD — what & why`.

- _(none yet)_

---

## 5. Baseline log (filled by Phase 0, then read-only)

- Kotlin unit suite (`testDebugUnitTest`): _(P0.1)_
- Backend pytest: _(P0.1)_
- Test inventory (Kotlin + backend): _(P0.2)_
- Protected check-out + FORMS snapshot: _(P0.2)_
- `git status` (both repos): _(P0.2)_
- Phase 9 comparison result: _(P9.1)_

### Protected behaviors — MUST remain identical end-to-end
- Automatic **check-out** in every case (far away, checkout zone, mixed-zone toggle to checkout).
- "No two consecutive check-outs; after a check-out the next activity is a check-in."
- Manual mode (auto OFF): the "Local" dropdown + manual submit flow.
- Offline queue capture + replay correctness (events replayed at original capture time).
- The browser web app's 422 on "Localização não Cadastrada".
- **Single-project FORMS:** a user in exactly one project gets exactly one FORMS submission per
  applicable event (first check-in of day / check-out), exactly as today.
- The TIMER skip-if-unchanged optimization (kept).

---

# PHASE 0 — Baseline (run BEFORE any change)

## Prompt P0.1 — Capture the green baseline
**Goal:** prove both suites are green now. **Risk:** none.
**Context:** Read Sections 0, 1, 2, 5.
**Steps:**
1. `checking_kotlin/`: `./gradlew testDebugUnitTest` and `./gradlew compileDebugKotlin` — must be green.
2. Repo root: `pytest -q` — green, or record exact pre-existing failures so we can prove we add none.
3. Record counts + date in Section 5. If Kotlin is red, STOP.
**Update:** tick P0.1.

## Prompt P0.2 — Inventory + protected-behavior snapshot
**Goal:** record what must not regress. **Risk:** none.
**Context:** Read Sections 0, 1, 2, 5.
**Steps:**
1. List Kotlin test classes (esp. `domain/checkrules/AutoActivitiesTest.kt`,
   `checkrules/AutoActivitiesSituationTest.kt`, `RunAutomaticActivitiesOfflineTest.kt`) and backend tests
   touching `/check` and FORMS. Write into Section 5.
2. Prose snapshot into Section 5: (a) the exact check-OUT branches in `AutoActivities.kt`; (b) the current
   single FORMS enqueue path in `forms_submit.py` (one submission per event). These are the references.
3. `git status` both repos; record. Trees clean (except known untracked docs).
**Update:** tick P0.2.

---

# PHASE 1 — Backend: history with location (change D data source)

## Prompt P1.1 — Add `local` to `CheckingHistory` and populate it
**Goal:** store the activity location in the per-user history table.
**Risk:** medium (DB migration + write path) — additive and nullable, so low blast radius.
**Context to load:** Read Sections 0, 1, 2; `sistema/app/models.py` (`CheckingHistory` ~691),
`sistema/app/services/checking_history.py` (`record_checking_history`), `sistema/app/services/user_sync.py`
(`create_user_sync_event` ~400, which already has `local` and calls `record_checking_history`), and an
existing migration in `sistema/app/migrations/` for the style.
**Changes:**
1. Add a nullable column `local: Mapped[str | None] = mapped_column(String(40), nullable=True)` to
   `CheckingHistory`. **Do NOT add it to the `uq_checkinghistory_event` unique constraint** (keep the
   5-field key so the existing idempotent upsert is unchanged).
2. Add an Alembic migration (next number) that adds the nullable column. Idempotent / reversible. (Optional,
   note-only: a best-effort backfill from `check_events.local` is possible but out of scope — old rows may
   show blank location.)
3. `record_checking_history(...)`: add a `local: str | None = None` parameter and set it on the new row.
   Keep the existing duplicate-detection query on the 5 unchanged fields (local is not part of it).
4. `create_user_sync_event(...)`: pass `local=local` into `record_checking_history(...)` (it already has
   `local` in scope).
5. Tests: extend/add a pytest asserting a recorded history row carries the `local`; assert the upsert still
   dedups on the 5-field key regardless of `local`.
**Do NOT:** change the unique key; change `CheckEvent`; alter `build_web_check_history_state`.
**Verify:** `pytest -q` green; the migration applies cleanly on a fresh SQLite DB.
**Update:** tick P1.1; log deviations.

## Prompt P1.2 — Add `GET /check/history`
**Goal:** expose the user's full check-in/out history including location (read-only, additive route).
**Risk:** low (new endpoint), production monolith — additive only.
**Context to load:** Read Sections 0, 1, 2; `web_check.py` around `GET /check/state` and
`_validate_public_chave`; `checking_history.py`; `schemas.py`.
**Changes:**
1. Service fn in `checking_history.py`: `list_checking_history(db, *, chave, limit=500)` → user's
   `CheckingHistory` rows ordered by `time` DESC, each with `atividade, projeto, local, time, informe`.
2. Schemas in `schemas.py`: `WebCheckHistoryItem { action: str, projeto: str, local: str | None, time:
   datetime, informe: str }` and `WebCheckHistoryListResponse { items: list[WebCheckHistoryItem] }`. Map
   `atividade` "check-in"/"check-out" → `action` "checkin"/"checkout".
3. `GET /check/history` in `web_check.py`: validate chave via `_validate_public_chave`, return the list.
   Mirror the public-chave access model used by `/check/state`.
4. pytest (`tests/test_web_check_history.py`): seed rows (with and without local), assert newest-first,
   mapped action strings, location passthrough, and 422 on bad chave.
**Do NOT:** modify `/check/state`, `/check`, or any existing route.
**Verify:** `pytest -q` green.
**Update:** tick P1.2.

---

# PHASE 2 — Kotlin: history dialogs with location (change D)

## Prompt P2.1 — Client data layer for history
**Goal:** consume `GET /check/history`. Additive only. **Risk:** low.
**Context to load:** Read Sections 0, 1, 2; `data/api/CheckApi.kt`, `data/dto/CheckDtos.kt`,
`domain/repository/CheckRepository.kt`, `data/repository/CheckRepositoryImpl.kt`, `core/result/AppResult.kt`,
and how `getState` parses timestamps.
**Changes:**
1. DTO in `CheckDtos.kt`: `WebCheckHistoryListResponseDto` / `WebCheckHistoryItemDto` (action, projeto,
   local, time, informe) matching the backend JSON; respect the existing serialization contract
   (`[[kotlin_api_serialization_contract]]`: explicitNulls behavior; send "" not null where defaults apply).
2. `CheckApi.kt`: `@GET("check/history") suspend fun getHistory(@Query("chave") chave: String): WebCheckHistoryListResponseDto`.
3. Domain `CheckHistoryEntry(action: CheckAction, projeto: String, local: String?, time: Instant, informe:
   InformeType)`; `CheckRepository.getHistory(chave): AppResult<List<CheckHistoryEntry>>`; impl maps
   DTO→domain (parse timestamps like `getState`).
**Do NOT:** change existing API methods/mappers.
**Verify:** `compileDebugKotlin` + `testDebugUnitTest`; add a mapper unit test if there is a seam.
**Update:** tick P2.1.

## Prompt P2.2 — History dialog (with location) + clickable cells
**Goal:** tapping "ÚLTIMO CHECK-IN"/"ÚLTIMO CHECK-OUT" opens a dialog with the full history table including
the **location** column. **Risk:** low–medium.
**Context to load:** Read Sections 0, 1, 2; `HistoryCard.kt`, `DialogScaffold.kt`, `CheckUiState.kt`,
`CheckViewModel.kt`, `CheckScreen.kt`.
**Changes:**
1. `CheckUiState.kt`: add `CheckDialog.CheckinHistory` / `CheckDialog.CheckoutHistory` (or one dialog +
   filter) and state for the loaded list + loading/error flags.
2. `CheckViewModel.kt`: `openCheckinHistory()` / `openCheckoutHistory()` → set dialog + launch
   `checkRepository.getHistory(chave)`, store result filtered by action.
3. `presentation/components/CheckHistoryDialog.kt` via `DialogScaffold`: title, a table with **Data / Hora
   / Local** (and informe if useful), empty state, "Voltar". Reuse the `Asia/Singapore` zone + locale
   formatting from `HistoryCard.kt`. Show "-" when `local` is null.
4. Make the two `HistoryCell`s clickable → VM openers (keep their look; optional subtle affordance).
5. Route the dialog(s) in `CheckScreen.kt`.
6. i18n keys (all 6 dicts): dialog titles, column headers (Data/Hora/Local), empty-state, "Voltar".
**Do NOT:** change what `HistoryCard` shows for the "last" values; don't change auth gating beyond
requiring a valid chave (history needs one).
**Verify:** `compileDebugKotlin` + `testDebugUnitTest` + `I18nTest`. Device (if available): both cells load
tables with location.
**Update:** tick P2.2.

---

# PHASE 3 — Kotlin: foreground trigger (change C)

## Prompt P3.1 — Run the engine on app open / resume
**Goal:** when foregrounded with auto-activities ON, evaluate (engine decides check-in OR check-out).
**Risk:** low (FOREGROUND trigger already exists, single-flight; we add a call site).
**Context to load:** Read Sections 0, 1, 2; `CheckViewModel.kt` `onForegroundResume()` (today only
`refreshCheckState()`), `onRefreshLocation()` (already calls `runOnce(FOREGROUND)`), orchestrator FOREGROUND path.
**Changes:**
1. In `onForegroundResume()`, after the existing refresh, if `isAuthenticated` AND
   `automaticActivitiesEnabled`, launch `orchestrator.runOnce(OrchestratorTrigger.FOREGROUND)` in
   `viewModelScope` (mirroring `onRefreshLocation`). FOREGROUND bypasses skip-if-unchanged by design;
   single-flight prevents overlap; and change A (P6.1 — check-in only on location change) prevents
   redundant check-ins at the same location.
**Do NOT:** add a second lifecycle observer; do not trigger when auto-activities is OFF.
**Verify:** `compileDebugKotlin` + `testDebugUnitTest`. Device: foreground in a new area when checked-out →
checks in; foreground far away when checked-in → checks out; foreground at the same area → no duplicate.
**Update:** tick P3.1.

---

# PHASE 4 — (REMOVED) Check-in de-duplication

**This phase was removed — there is NO work to do here.** It originally added a 10-minute same-location
dedup (`shouldDedupeCheckIn`) as a workaround for the duplicate check-in. The real fix is **change A /
P6.1 (check-in only on location change)**, which eliminates the duplicate at its root — confirmed by the
2026-06-17 production-log investigation (see §0 "B — REMOVED" for the evidence and mechanism).

Do **NOT** implement `shouldDedupeCheckIn` or wire any time-window/same-location guard into
`RunAutomaticActivitiesUseCase`. The phase/prompt numbers of later phases (P5.x, P6.x, P7.x, P8.1, P9.1)
are intentionally **kept unchanged** so that cross-references elsewhere in this plan (and in
`docs/temp002.md`) remain valid. Skip straight to Phase 5.

---

# PHASE 5 — Backend: allow "Localização não Cadastrada" check-in for the app (change A enabler)

## Prompt P5.1 — Scoped relaxation of the non-operational-local guard
**Goal:** let the **Kotlin app** submit a **check-in** with local "Localização não Cadastrada"; keep the
browser web app's 422. **Risk:** medium-high (production submit validation) — scope it tightly.
**Context to load:** Read Sections 0, 1, 2 (rule #6); `web_check.py`
`_reject_non_operational_web_submit_local` (~170), `submit_web_check` (~911), the `X-Client` /
`CHECKING_ANDROID_CLIENT` / `WEB_CHECK_ANDROID_CHANNEL` handling (~134) and how the channel/header is
selected in the submit path.
**Changes:**
1. In `submit_web_check`, determine the client from `X-Client` (reuse the existing detection that picks
   `WEB_CHECK_ANDROID_CHANNEL`).
2. Make `_reject_non_operational_web_submit_local` accept the client + action and **skip the rejection
   only when** client == `checking-android` AND action == check-in. Everything else (web app, any
   check-out, any other local) behaves exactly as today.
3. Ensure the rest of the pipeline accepts this local for an android check-in (the event/history row is
   written with local "Localização não Cadastrada"); confirm nothing downstream independently rejects it.
4. pytest: (a) web client + that local check-in → still 422; (b) android header + check-in + that local →
   200 and recorded; (c) android header + **check-out** + that local → still 422.
**Do NOT:** widen `WEB_NON_OPERATIONAL_SUBMIT_LOCALS`; relax for check-out or the web client.
**Verify:** `pytest -q` green incl. the three cases; no existing `/check` test regresses.
**Update:** tick P5.1. **Note in Section 4:** changes a deliberate production invariant for the app client —
flag for human review before any deploy.

---

# PHASE 6 — Kotlin: check-in only on location change (change A core; highest risk)

## Prompt P6.1 — Engine: suppress same-location re-check-in
**Goal:** a MATCHED check-in fires only when the resolved location differs from the last check-in location.
Same location → no action. (This replaces the old "re-check-in even at same location" of Situations 4/6.)
**Risk:** high (shared with offline replay; changes existing behavior).
**Context to load:** Read Sections 0, 1, 2 (rules #2, #5); `AutoActivities.kt`
(`shouldAttemptAutomaticLocationEvent`, `resolveRecordedCheckInLocation`, `normalizeLocationName`), the
offline replay path, and existing engine tests.
**Changes:**
1. In `shouldAttemptAutomaticLocationEvent`, the final branch (matched, non-checkout, non-mixed, last
   action = check-in) changes from `return normalizeLocationName(resolvedLocal).isNotEmpty()` to: return
   true only if `normalizeLocationName(resolvedLocal).isNotEmpty()` **AND**
   `normalizeLocationName(resolvedLocal) != normalizeLocationName(resolveRecordedCheckInLocation(remoteState))`.
   (This mirrors the mixed-zone "different location" check already present in
   `shouldAttemptAutomaticMixedZoneLocationEvent`.) Leave the `lastRecordedAction != CHECKIN` case (last
   was check-out → check-in) and the checkout-zone / mixed-zone branches untouched.
2. **Keep** the orchestrator skip-if-unchanged exactly as is (do NOT remove it).
3. Tests: extend `AutoActivitiesTest` / `AutoActivitiesSituationTest`: matched + last check-in + SAME
   location → null (no action); matched + last check-in + DIFFERENT location → check-in; matched + last
   check-out → check-in (unchanged). All existing check-out tests stay green.
4. Verify offline replay coherence (`PendingCheckReplayer`/`SyncPendingChecksWorker`).
**Do NOT:** alter any check-out branch; do not remove skip-if-unchanged.
**Verify:** `testDebugUnitTest` green; review the diff to confirm only the targeted branch changed.
**Update:** tick P6.1.

## Prompt P6.2 — Engine: "Localização não Cadastrada" continuation
**Goal:** when last action = check-in and the user is "near but not inside" any area
(`NOT_IN_KNOWN_LOCATION`), submit a check-in as "Localização não Cadastrada" — but only as a *change*.
**Risk:** high (engine + offline replay; relies on Phase 5 backend).
**Context to load:** Read Sections 0, 1, 2; `AutoActivities.kt` `resolveAutomaticActivityForMatch`,
`AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION`, `resolveRecordedCheckInLocation`; the offline replay path.
**Changes:**
1. In `resolveAutomaticActivityForMatch`, add a branch for `MatchStatus.NOT_IN_KNOWN_LOCATION`: if
   `resolveLastRecordedAction(currentState) == CheckAction.CHECKIN` AND
   `normalizeLocationName(resolveRecordedCheckInLocation(currentState)) != normalizeLocationName(AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION)`,
   return `AutomaticActivity(CheckAction.CHECKIN, AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION)`; otherwise
   `null`. Leave `OUTSIDE_WORKPLACE`, `MATCHED`, `NO_KNOWN_LOCATIONS`, `ACCURACY_TOO_LOW` as they are.
2. Update the doc-comment in `AutoActivities.kt` (it currently claims it "never submits 'Localização não
   Cadastrada'") to reflect the new scoped behavior.
3. Tests: NOT_IN_KNOWN_LOCATION + last check-in (registered local) → check-in "Localização não Cadastrada";
   NOT_IN_KNOWN_LOCATION + last check-in already "Localização não Cadastrada" → null (no repeat — change A);
   NOT_IN_KNOWN_LOCATION + last check-out → null.
4. Verify offline replay submits the unregistered check-in coherently (depends on Phase 5).
**Do NOT:** alter check-out branches.
**Verify:** `testDebugUnitTest` green; diff review.
**Update:** tick P6.2.

---

# PHASE 7 — Backend: FORMS per project (change E; high risk)

> Goal: when FORMS should be submitted (first check-in of the day, every check-out), submit **once per
> project** the user is registered in — each project gated by its own `forms_enabled`. Keep the per-user
> TRIGGER timing (first check-in of day / check-out) unchanged; only multiply the submissions by project.
> A single-project user must behave exactly as today.

## Prompt P7.1 — Enqueue FORMS per project in `submit_forms_event`
**Goal:** replace the single enqueue with one enqueue per registered project.
**Risk:** high (production FORMS pipeline + idempotency).
**Context to load:** Read Sections 0, 1, 2 (rule #7); `forms_submit.py` (full), `forms_queue.py`
(`enqueue_forms_submission`, `record_forms_submission_skip`), `user_sync.py`
(`should_enqueue_forms_for_action`, `create_user_sync_event`, the top-of-function idempotency check),
`project_catalog.py` (`is_forms_enabled_for_project`), `list_user_project_names`, and the
**`FormsSubmission` unique constraint in `sistema/app/models.py` (verify it before choosing request_id)**.
**Changes:**
1. Keep the per-user decision (`should_enqueue_forms_for_action` → `should_queue_forms`) and the
   first-check-in-of-day / check-out timing unchanged.
2. When `should_queue_forms` is true, iterate over the user's projects (`list_user_project_names(db, user)`).
   For **each** project:
   - Skip if `is_forms_enabled_for_project(db, projeto=<project>)` is false (record a per-project skip via
     `record_forms_submission_skip` if appropriate, so diagnostics stay accurate).
   - Otherwise `enqueue_forms_submission(..., projeto=<project>, project_candidates=[<project>],
     request_id=<per-project unique id>, ...)`. Use a per-project `request_id` such as
     `f"{client_event_id}:{project}"` (confirm uniqueness against the verified constraint).
3. Idempotency/state: today the function short-circuits on an existing `UserSyncEvent` with
   `source_request_id == client_event_id`, and `create_user_sync_event` is called once. For multi-project,
   make the idempotency + `create_user_sync_event` **per project** (e.g. `source_request_id =
   f"{client_event_id}:{project}"`), so a retry of the same event is still idempotent and each project is
   recorded once. **Verify** this does not double-write `CheckingHistory` in a harmful way (the upsert
   dedups on the 5-field key; per-project rows differ by `projeto`, which is correct — one history row per
   project per event).
4. Preserve the single-project path: a user with one project yields exactly one submission and one
   sync/history row, identical to today.
5. pytest (`tests/`): user in P80+P83, first check-in of day → **two** FormsSubmission rows (one per
   project) with distinct request_ids; check-out → two; second check-in same day → none (timing
   unchanged); a project with forms disabled is skipped; a single-project user → exactly one (regression).
   Replaying the same event (same client_event_id) → no duplicates.
**Do NOT:** change the trigger timing; change check-out detection; weaken idempotency; alter behavior for
single-project users.
**Verify:** `pytest -q` green incl. new multi-project tests + existing FORMS tests unchanged.
**Update:** tick P7.1. **Note in Section 4:** production FORMS behavior change — flag for human review.

## Prompt P7.2 — Worker / idempotency / unsupported-project hardening
**Goal:** ensure each per-project submission is processed correctly and an unsupported project fails
gracefully (does not block others).
**Risk:** medium-high.
**Context to load:** Read Sections 0, 1, 2; `forms_queue.py` `_process_submission`, `forms_worker.py`
(`submit_with_retries`, project selection, `UnsupportedProject`).
**Changes:**
1. Confirm `_process_submission` → `submit_with_retries(projeto=<project>, project_candidates=[<project>])`
   submits exactly that project's form. With candidates = a single project, the worker selects it (or
   raises `UnsupportedProject` if it has no xpath mapping).
2. Ensure an `UnsupportedProject` for one project marks **only that** submission failed/skipped (it already
   is a per-row failure) and does not affect the other project's submission. If today an unsupported
   project would have been silently dropped within a multi-candidate set, document the behavior change and
   add a test.
3. pytest: a user in [supported P80, unsupported PXX] → P80 submitted, PXX recorded failed/skipped, P80
   unaffected.
**Do NOT:** change the worker's per-project form-filling logic beyond what is needed for the
single-candidate case.
**Verify:** `pytest -q` green.
**Update:** tick P7.2.

---

# PHASE 8 — Rules documentation

## Prompt P8.1 — Update the Kotlin check rules file
**Goal:** make `docs/regras_e_situacoes/regras_checkin_checkout_kotlin.txt` match the new behavior.
**Risk:** none (docs).
**Context to load:** Read the full rules file + Section 0 of this plan.
**Changes (Portuguese, matching the file's style; edit precisely, don't rewrite the whole file):**
1. Amend Situações 4 and 6: o check-in automático agora ocorre **apenas quando a localização muda** em
   relação ao último check-in. Mesma localização → nenhuma ação (substitui o "re-check-in no mesmo local").
   O TIMER continua com skip-if-unchanged; não há check-in periódico "às cegas".
2. Amend Situação 5 e a nota IMPORTANTE da Situação 3: quando a última atividade foi um **check-in** e o
   usuário está "próximo mas fora" de qualquer área cadastrada, a aplicação realiza check-in como
   **'Localização não Cadastrada'** (apenas se for mudança; não repete se o último check-in já foi
   'Localização não Cadastrada'). Quando a última foi um **check-out**, segue sem check-in fora de área.
   **Situação 7B (já corrigida no arquivo de regras):** ao sair da 'Zona de CheckOut' com a última
   atividade = check-out e posição "próximo mas fora", NÃO há check-in (alinhado à Situação 3); o check-in
   só ocorre ao ingressar em área CADASTRADA (≠ 'Zona de CheckOut'), i.e. Variante 7A. Reflete o engine
   atual — sem mudança de código; apenas reafirmar a consistência do texto.
3. **NÃO** adicionar regra de dedup de 10 min (foi descartada). Em vez disso, deixar explícito que o
   check-in automático só ocorre em **mudança de localização** (mesma localização do último check-in →
   nenhuma ação) — o que também elimina o **duplo check-in**. (Ver §0 "B — REMOVED".)
4. Add the **foreground/abertura** rule: abrir/trazer o app para primeiro plano dispara a avaliação.
5. Add a **FORMS por projeto** note: no primeiro check-in do dia e em cada check-out, o FORMS é preenchido
   e enviado **uma vez por projeto** em que o usuário está cadastrado (respeitando o forms habilitado por
   projeto). Antes: apenas um projeto.
6. Restate the preserved **invariantes de check-out** (nunca dois check-outs; após check-out a próxima é
   check-in; check-out por distância/Zona de CheckOut inalterado).
**Verify:** re-read for consistency with Phases 5–7 (Phase 4 was removed).
**Update:** tick P8.1.

---

# PHASE 9 — Final integrity verification

## Prompt P9.1 — Regression + check-out/FORMS preservation + device checklist
**Goal:** prove only the intended behaviors changed. **Risk:** none (verification).
**Context to load:** Read Sections 0, 1, 2, 5 and the Phase 0 baseline.
**Steps:**
1. Kotlin: `testDebugUnitTest` green, count ≥ baseline; `compileDebugKotlin` clean; `I18nTest` parity green.
2. Backend: `pytest -q` green, no new failures vs. baseline.
3. Diff review: check-out branches in `AutoActivities.kt` unchanged; skip-if-unchanged still present;
   `WEB_NON_OPERATIONAL_SUBMIT_LOCALS` unchanged and web app still 422s (Phase 5 test a); single-project
   FORMS path unchanged (Phase 7 regression test).
4. Manual device/server checklist (else mark pending-for-device):
   - Stationary at the same area, checked-in → **no** repeated check-in.
   - Move to a different registered area → check-in there; a second trigger for the **same** area
     (geofence EXIT+ENTER, or foreground) → **no duplicate** check-in (P6.1 — this is the duplicate fix).
   - Checked-in, move to "near but not inside" → check-in "Localização não Cadastrada" (once; not repeated).
   - Checked-out at home / near work → **no** check-in.
   - Move far / checkout zone while checked-in → **check-out** (unchanged); never a second check-out.
   - Foreground the app → correct single check-in/out fires.
   - Tap "ÚLTIMO CHECK-IN"/"ÚLTIMO CHECK-OUT" → full tables load with **location**.
   - User in P80+P83: first check-in of day → FORMS submitted for **both**; check-out → both; single-project
     user → exactly one (unchanged).
   - Manual mode (auto OFF): nothing auto-submits; "Local" dropdown works.
5. Record results in Sections 4/5.
**Update:** tick P9.1.

---

## Acceptance summary

Done when: Section 3 fully ticked; both suites green (Kotlin count ≥ baseline; backend no new failures);
check-out branches, skip-if-unchanged, the web 422 invariant, and single-project FORMS unchanged; the
changes verified (location-change check-in — which also **eliminates the duplicate check-in** with no
duplicate observed, foreground trigger, history dialogs with location, FORMS per project); the rules file
updated; Sections 4/5 complete. Backend changes (Phases 1, 5, 7) require explicit human approval before any
push, since pushing the root repo deploys to production.
