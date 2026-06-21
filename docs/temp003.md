# Checking — Execution Playbook for `plan003.md` (agent prompts) + verification suite

> **Audience:** an AI coding agent that executes `docs/plan003.md` end to end, one prompt at a time.
> **Prime directive:** the app is in **final testing and everything works very well**. The ONLY new
> behavior is the **new-user approval gate**. Every existing flow — login, check-in/check-out, the
> situation engine, sync, transport, accident mode, RFID pending, offline replay — **must stay
> byte-for-byte intact**. `plan003.md` is the canonical spec (the *what*/*why*); this file (`temp003.md`)
> is the *how*: ordered, self-contained prompts + verification. When a prompt says "apply plan003 §X",
> open `plan003.md`, read that section in full, and implement it exactly.

Modeled on `docs/temp002.md`. Execute prompts **strictly in order**. Do not start a prompt until the
previous one compiles, its tests pass, and its **Verify** block is satisfied. **Never start a change phase
on a red baseline.**

This work spans **four surfaces**, in two git repos:
- **Backend monolith** — `sistema/app/` (root repo `checking`). Pushing `main` deploys to **PRODUCTION**
  via `Deploy OceanDrive`. See `docs/Instrucoes/instrucoes_acesso_repositórios_github.md` §2.1/§3.1 and
  `instrucoes_acesso_Digital_Ocean.md`.
- **Check Web** — `sistema/app/static/check/` (served by the monolith at `tscode.com.br/checking/user`).
  **Deploys with the backend** (same `git push origin main`). Memory: *checkweb_public_served_by_monolith*.
- **Admin v2** — `sistema/app/static/admin2/`. Deploys via the **parent-repo pipeline**; the source MUST
  be **mirrored byte-for-byte** to `deploy/docker/admin2-web/` (memories *admin2_mirror_sync*,
  *admin2_deploy_pipeline*).
- **Kotlin app** — `checking_kotlin/` (own git repo `checking-kotlin`; commit/push per
  `instrucoes_acesso_repositórios_github.md` §1.7/§2.6). Distributes via Play Store **AAB**; no auto-deploy.

> **Decisions are LOCKED (plan003 §11):** (1) the gate applies to **all clients** (app **and** Check Web);
> (2) admin sees pendings **scoped to their project(s)** (multi-project admin → union; perfil 9 → all);
> (3) the registration form **auto-opens** on an unknown key **and has a top-left "Back" arrow**;
> (4) rejection is **silent** (no message to the user).

---

## 0. Global context (every prompt assumes you have read this section)

### 0.1 Repos, build, run
- Repo root: `c:\dev\projetos\checkcheck`.
- **Backend tests:** from repo root, `python -m pytest -q --ignore=tests/test_api_flow.py`
  (`test_api_flow.py` has a Windows DB-lock collection bug; it is a known exclusion). SQLite; no prod.
- **Check Web tests:** Node JS harness in `tests/` (e.g. `tests/check_user_location_ui.test.js`). Run the
  project's JS test command (the existing `check_*.test.js` runner). Pure DOM/logic; no network.
- **Admin2:** no JS test harness. Verified via the backend endpoint tests + a manual checklist.
- **Kotlin:** from `checking_kotlin/`: `./gradlew compileDebugKotlin compileDebugAndroidTestKotlin
  testDebugUnitTest`. Counts come from `app/build/test-results/testDebugUnitTest/*.xml`. **Never** run
  `connectedAndroidTest` (BootReceiver crashes it). Instrumented tests: run on a connected device via
  `am instrument` twice, else mark "device verification pending".

### 0.2 The change set (full detail in `plan003.md`)
A new user submits the self-registration form and is **NOT authenticated**; they enter an **"awaiting
approval"** state (key/password fields **bright orange**; notification bar shows, **in red**, "Aguardando
aprovação de cadastro."). The pending record lives in a **separate table** `pending_user_registrations`
(the `User` is created only on approval — so nothing in `users` is affected). A pending **queue cap of
300**: when full, the red message becomes "Fila de cadastro cheia. Informe ao administrador do sistema."
An admin (perfil 1/9) sees **"Pendências de Usuários"** in admin2 and **Approves** (creates the `User`;
client then logs in and runs the engine) or **Rejects** (deletes the pending row; no user is created; the
client silently returns to the unknown-key state). The existing "Cadastro de Pendências" (RFID) table is
**renamed "Pendências de RFID"**; the new table sits **immediately above** it. The approval state is
**server-derived** (`/auth/status` reports `pending_approval`) and clients **poll** for approval. A feature
flag `CHECK_USER_APPROVAL_REQUIRED` (default ON) allows instant rollback.

### 0.3 Key backend files (re-locate symbols by name; line numbers drift)
- `sistema/app/models.py` — `User` (~73, no approval concept; `perfil` 0/1/9; `chave` unique),
  `UserProjectMembership` (~99), `PendingRegistration` (RFID, ~261; the *pattern* to mirror),
  `AdminAccessRequest` (~733). **Add** `PendingUserRegistration` (plan003 §2.1).
- `sistema/app/routers/web_check.py` — `register_web_user` (~431; today creates `User` + sets session +
  authenticates), `get_web_password_status` / `_build_web_password_status` (~391), `login_web_user`
  (~530), helpers `_validate_public_chave`, `find_user_by_chave`, `_normalize_known_web_user_projects`,
  `replace_user_project_memberships`, `_set_web_session_chave`, `hash_password`.
- `sistema/app/routers/admin.py` — RFID pattern to mirror: `list_pending` (~3242, `GET /pending`),
  approve (~3852), `remove_pending` (~3890, `DELETE /pending/{id}`); deps `require_full_admin_session`
  (= perfil 1/9 via `user_has_admin_access`), scope helpers `resolve_effective_admin_project_names`,
  `pending_matches_admin_scope`; `notify_admin_views`, `log_event`.
- `sistema/app/schemas.py` — `WebPasswordStatusResponse` (~3828), `WebUserSelfRegistrationRequest`
  (~3863), `WebUserSelfRegistrationResponse` (~3975), `WebPasswordActionResponse` (~3968).
- `sistema/app/core/config.py` — `class Settings(BaseSettings)` (pattern: `forms_queue_enabled: bool =
  True`). Add `check_user_approval_required: bool = True`, `pending_user_registration_limit: int = 300`.
- `sistema/app/services/admin_updates.py` — `notify_admin_data_changed`, `notify_web_check_data_changed`.
- Migrations: `alembic/versions/` (latest = `0078_add_local_to_checkinghistory.py`; **next = 0079**).

### 0.4 Key Check Web files (`sistema/app/static/check/`)
- `app.js` — `authStatusEndpoint` / `authUserRegisterEndpoint` (top, from `form.dataset.*`);
  `notificationState {message, tone}` + `renderNotifications()` + `applyNotificationLine(el, msg, tone)`
  (~1945–1970); field classes `auth-field-pending` (orange) / `auth-field-authenticated` (green) toggled
  ~1257–1261 (function reading `authenticated`/`assistanceModeActive`); `registrationDialog`,
  `requestRegistrationButton` (~1396), `userSelfRegistrationInProgress` (~302), `authState`.
- `i18n-dictionaries.js` (6 dicts pt/en/zh/ms/id/tl) + `i18n.js` (`t()` with pt fallback).
- `index.html` (registration dialog markup; assets carry `?v=` cache-busting), `styles.css`
  (`.auth-field-pending` etc.).

### 0.5 Key admin2 files (`sistema/app/static/admin2/`)
- `index.html` — `<h2>Cadastro de Pendências</h2>` (~375) inside `<article …
  data-cadastro-section="pendencias">` with `<tbody id="pendingBody">` (~382), in `#tab-cadastro`.
- `app.js` — `loadPending({silent})` (~5118, fetches `/api/admin/pending`), `fetcher`, `postJson`,
  `deleteJson` (~6092), `renderEmptyStateRow(bodyId, cols, msg)` (~3447), `applyResponsiveLabels`,
  initial `Promise.all([loadAdministrators(), loadPending(), loadRegisteredUsers()])` (~5297/5324),
  SSE `EventSource("/api/admin/stream")` (~5831) with refresh jobs (~5769/5794), `#pendingBody` click
  handler (~6724). **Mirror:** `deploy/docker/admin2-web/`.

### 0.6 Key Kotlin files (`checking_kotlin/app/src/main/java/br/com/tscode/checking/`)
- `data/api/AuthApi.kt` — `getStatus` (`GET auth/status`), `registerUser` (`POST auth/register-user`),
  `login` (`POST auth/login`).
- `data/dto/…` — `WebPasswordStatusResponse`, `WebUserSelfRegistrationRequest/Response`.
- `domain/model/AuthStatus` (`found, chave, hasPassword, authenticated, message`),
  `domain/repository/AuthRepository`, `data/repository/AuthRepositoryImpl` (`getStatus`/`login`/
  `selfRegister` map DTO→`AuthStatus`).
- `presentation/check/CheckUiState.kt` — `enum NotificationTone {None,Info,Success,Error,Teal}`,
  `authStatus`, `selfRegistrationFields`, `notificationPrimary/Secondary/Tone`, derived `isAuthenticated`/
  `isFound`/`hasPassword`; `CheckDialog` routing.
- `presentation/check/CheckViewModel.kt` — `submitSelfRegistration` (~809, today calls
  `onAuthenticationSucceeded` on success), `onChaveChanged` (~131) → `getStatus` (~188),
  `onForegroundResume` (~388), `onAuthenticationSucceeded`, `securePasswordStore`.
- `presentation/components/AuthRow.kt` — field glow: `isAuthenticated`→green (`FieldGlow.Authenticated`),
  `isFound`→orange (`FieldGlow.Pending`), else None.
- `presentation/components/NotificationCard.kt` — `NotificationTone.Error → CheckingErrorVivid` (vivid red).
- the registration dialog (driven by `selfRegistrationFields` / `CheckDialog`), `CheckScreen.kt`.
- i18n: `i18n/dictionaries/{Pt,En,Zh,Ms,Id,Tl}.kt`; `i18n/I18nTest.kt` (resolution/fallback, not parity).

### 0.7 Test credentials & a fresh key for pending tests (provided by product owner)
- Existing user: **chave `TEST` / senha `000000`** → already registered (use to assert "found", and that
  re-registering it 409s).
- For **pending-registration** tests, use a throwaway 4-char key not present in the DB (e.g. `NEW1`, or a
  per-test unique key) so the row goes through the pending path cleanly.

### 0.8 Production access & safety (prefer LOCAL always)
Per `instrucoes_acesso_Digital_Ocean.md`: public base `https://tscode.com.br/api`; health
`/api/health`; SSH via WSL (key at `deploy/keys/do_checkcheck`); read-only DB inspect via
`docker exec checkcheck-db-1 psql …` (memory *prod_db_readonly_audit*) on tables `users`,
`pending_user_registrations`. **Safety:** default ALL tests to LOCAL. Reuse the existing `prod_e2e`
marker + `CHECKING_E2E_PROD=1` skip guard from plan002 (`tests/conftest.py`, `tests/test_prod_e2e_guard.py`)
for any prod-touching test; writes require `CHECKING_E2E_PROD_SUBMIT=1` **and** human approval. Never
loop-submit to prod.

### 0.9 The contract (authoritative — backend ↔ app ↔ web ↔ admin); full detail in `plan003.md` §2
- **Table** `pending_user_registrations`: `id, chave (unique), nome_completo, projetos_json (JSON in Text),
  email (nullable), password_hash, client (nullable, 16), requested_at`. Cap `PENDING_USER_REGISTRATION_LIMIT
  = 300`.
- **`GET …/auth/status`** gains **`pending_approval: bool = False`**: `User` exists → `found=true,
  pending_approval=false`; no `User` but pending row → `found=false, has_password=false,
  authenticated=false, pending_approval=true`; nothing → all false. **Additive; no existing field changes.**
- **`POST …/auth/register-user`**: with `gate = settings.check_user_approval_required` (**unconditional**,
  all clients): if gate OFF → legacy (create `User` + session + authenticate) → `201
  {status:"registered", authenticated:true, projects, active_project}`. If gate ON: 409 on existing
  `User`/existing pending/existing `AdminAccessRequest`; if `COUNT(pending) >= 300` → `200
  {status:"queue_full", authenticated:false, pending_approval:false}`; else create pending row (store
  `client` from `X-Client` header or `"web"`), **no `User`, no session**, notify admin → `202
  {status:"pending", authenticated:false, pending_approval:true, projects, active_project:""}`. Response
  model gains `status: Literal["registered","pending","queue_full"]`, `pending_approval`, `queue_full`,
  and `projects`/`active_project` become **optional**. All codes are 2xx (clients read the body; decide by
  `status`).
- **Admin endpoints** (all `Depends(require_full_admin_session)`): `GET /api/admin/user-pending`
  (project-scoped; perfil 9 = all), `POST /api/admin/user-pending/{id}/approve` (create `User`+memberships,
  delete pending, notify admin + `notify_web_check_data_changed()`, `log_event("user_approve")`),
  `POST /api/admin/user-pending/{id}/reject` (delete pending, notify, `log_event("user_reject")`). `action`
  strings ≤ 16 chars. Schema `AdminUserPendingRow {id, requested_at, chave, nome_completo, projetos:
  list[str], email}`.
- **Messages (exact):** `auth.awaitingApproval` = "Aguardando aprovação de cadastro.";
  `auth.registrationQueueFull` = "Fila de cadastro cheia. Informe ao administrador do sistema." — pt with
  these exact strings; en/zh/ms/id/tl translated (app: 6 `*.kt` dicts; web: `i18n-dictionaries.js`).

---

## 1. Golden rules (apply to EVERY prompt)
1. **Existing flows are sacred.** The only behavior change is the autocadastro path for an **unknown key**.
   Login, password register/change, check-in/out, the engine, sync, transport, accident, RFID pending,
   offline replay, and any **already-authenticated** client → untouched.
2. **Never create a `User` for a pending registration.** The `User` is created **only on approval**, reusing
   the extracted `create_user_from_registration` helper. Pending lives only in `pending_user_registrations`.
3. **Additive-first.** New table/columns/fields/endpoints over edits. New response/status fields default so
   old clients ignore them. New DB column unique only on `chave`.
4. **Server is the source of truth for the awaiting state.** Clients derive "awaiting" from
   `pending_approval` and **poll**; no fragile local-only flag. Keep the typed password locally for the
   post-approval auto-login.
5. **Feature flag gates the whole feature.** `CHECK_USER_APPROVAL_REQUIRED=false` ⇒ exact legacy behavior.
   Every backend prompt must keep the flag-off path working.
6. **The gate is system-wide.** Do **not** branch on `X-Client` for the gate (decision 1). `X-Client` is
   recorded only as `client` for observability.
7. **Admin actions are project-scoped** (decision 2) and require an admin session (perfil 1/9). They create
   a normal `User` (no `*_by_admin_id` writes) → `require_full_admin_session` suffices (see `CLAUDE.md`
   §Identidade de admin). Audit every approve/reject via `log_event` (`action` ≤ 16 chars).
8. **Touch all 6 dictionaries together** (app `*.kt` and web `i18n-dictionaries.js`). Re-run `I18nTest`.
   For changed `static/check` assets, bump `?v=` in `index.html` (cache-busting rule).
9. **admin2 edits must be mirrored** byte-for-byte to `deploy/docker/admin2-web/`.
10. **One prompt = one compilable, test-passing increment.**
11. **Do NOT `git commit`/`push`/branch** unless the human asks. **Pushing the root `main` deploys backend +
    Check Web to PRODUCTION**; the migration must run there. AAB publish is a separate, human-gated step.
12. Keep Sections 2/3/4 current. If reality differs from the plan, STOP, log in Section 3, report.

---

## 2. Progress tracker (update after each prompt)

**Execution (backend → Check Web → admin2 → app; plan003 §9 order):**
- [x] **EP0** Baseline — 2026-06-20: Kotlin `testDebugUnitTest` **193/0** + `compileDebugKotlin` clean; backend `pytest` **574 pass / 33 pre-existing fail (all `test_transport_ai_suggestion_commands.py`) / 8 skip**; Check Web JS `node --test` **353 pass / 43 pre-existing fail** (admin2 + transport, out of scope; 3 in `static/check` from uncommitted plan002 `?v=`/layout drift). Trees: **Kotlin clean**, **root dirty** (uncommitted plan002 backend + docs — anomaly EP0-1). See §3/§4.
- [x] **EP1** Backend: model `PendingUserRegistration` + migration 0079 + config flag/limit — 2026-06-20: added `PendingUserRegistration` (unique `chave`, index `requested_at`), `alembic/versions/0079_add_pending_user_registrations.py` (chained to 0078; create+index / downgrade drops both), config `check_user_approval_required=True` + `pending_user_registration_limit=300`, and `tests/test_pending_user_registration_migration.py`. Full `pytest` **575 pass / 33 pre-existing fail / 8 skip** (was 574 → +1 new test, ZERO new failures). Additive; no behavior change. **⚠ Backend — NOT deployed; needs human approval before push (EP1-deploy).**
- [x] **EP2** Backend: schemas (`pending_approval`, register response `status`, `AdminUserPendingRow`) + `/auth/status` reports `pending_approval` + extract `create_user_from_registration` (no behavior change) — 2026-06-20: `WebPasswordStatusResponse += pending_approval`; `WebUserSelfRegistrationResponse += status/pending_approval/queue_full` (projects/active_project now optional); new `AdminUserPendingRow`; extracted `create_user_from_registration` (byte-identical) + `register_web_user` calls it; `get_web_password_status` computes `pending_approval` only when no `User` (querying `PendingUserRegistration`). Sanity: imports clean, `pending_approval` defaults False for normal users, register default `status="registered"`. Full `pytest` **575 pass / 33 pre-existing fail / 8 skip** (unchanged → ZERO regressions). **⚠ Backend — NOT deployed; needs human approval before push (EP1-deploy).**
- [x] **EP3** Backend: `register-user` pending behavior (flag gate, 300 cap, pending creation, notify; legacy when flag off) — 2026-06-20: rewrote `register_web_user` per §2.4 — 409s (existing User / existing pending / existing AdminAccessRequest); `gate = settings.check_user_approval_required` (NO X-Client branch); flag OFF → legacy 201 registered+authenticated; flag ON → COUNT≥limit → 200 queue_full (inserts nothing) else insert `PendingUserRegistration` (client=`X-Client` or "web", `now_sgt()`), no User/session, notify admin, 202 pending; cap race-guard (re-count after flush → rollback). Added `Response`/`func`/`settings` imports + `_registration_queue_full_response`. **Focused test `tests/routers/test_web_self_registration_pending.py` (6) green** (android/web pending, queue-full, flag-off legacy, duplicate 409, invalid 422). Full-suite confirmed in the EP3+EP4 batch (**586 pass / 33 / 8**, Option A). **⚠ Backend — NOT deployed; needs human approval before push (EP1-deploy).**
- [x] **EP4** Backend: admin endpoints `user-pending` GET(scoped)/approve/reject + scope helper + audit — 2026-06-20: added `GET /api/admin/user-pending` (newest-first, `AdminUserPendingRow`, project-scoped via `_user_pending_in_admin_scope`: perfil 9 → all, else intersection with `resolve_effective_admin_project_names`), `POST .../{id}/approve` (reuses `create_user_from_registration` via local import, deletes pending, `log_event("user_approve")`, `notify_admin_views`+`notify_web_check_data_changed`, idempotent if User exists, 404 if missing/out-of-scope), `POST .../{id}/reject` (deletes pending, `log_event("user_reject")`, no User). All `Depends(require_full_admin_session)`; `action`≤16. **Focused test `tests/test_admin_user_pending_endpoints.py` (5) green** (401 no-session, perfil-9 sees all, perfil-1 no-membership sees none, approve→User+membership+status-flip+re-approve-404, reject→no-User). EP3+EP4 batch full `pytest` **586 pass / 33 pre-existing fail / 8 skip** (575→+11, ZERO new failures). **⚠ Backend — NOT deployed; needs human approval before push (EP1-deploy).**
- [x] **EP5** Check Web: awaiting/queue-full UI + auto-open form + Back arrow + approval polling + i18n + cache-bust — 2026-06-20: `app.js` — `authState.pendingApproval`; `applyAuthenticationStatusPayload` reads `pending_approval`, shows red `setStatus(t('auth.awaitingApproval'),'error')`, drives polling; `resolveAuthenticationAssistanceStateKey` → distinct `:pending-approval` key (so the form does NOT re-open for pending); orange fields via `syncAuthenticationFieldHighlights`; register-submit branches on `status` (`pending`→awaiting+persist pw+poll, `queue_full`→red msg, both no-auth; `registered` legacy untouched); `schedulePendingApprovalPolling` (15s, self-re-arming, stops on approve/reject). Auto-open on unknown key + **Voltar** button already existed (kept). i18n: `auth.awaitingApproval`+`auth.registrationQueueFull` added to all 6 dicts (pt exact). Cache-bust app.js/i18n-dictionaries `?v=6`. **JS suite 353 pass / 43 fail — identical per-file to EP0 baseline (ZERO new failures)**; `node --check` clean. Dedicated behavioral test `check_user_approval_ui.test.js` + manual/browser smoke → TP6. **⚠ Check Web deploys with backend → human approval before push.**
- [x] **EP6** Admin2: rename → "Pendências de RFID"; add "Pendências de Usuários" table + loadUserPending + approve/reject + SSE + **mirror** — 2026-06-20: `index.html` renamed RFID `<h2>` and inserted the `pendencias-usuarios` article **above** it (Data/Chave/Nome Completo/Projetos/E-Mail/Ações, `#userPendingBody`); auto-collapsible via the existing `setupCadastroSectionPanels` (no registry). `app.js`: `makeUserPendingRow`, `loadUserPending` (renderEmptyStateRow on empty), `approveUserPending`/`rejectUserPending` (confirmDestructive) + `#userPendingBody` click handler; wired `loadUserPending` into `refreshActiveTab` (cadastro initial load), `refreshAllTables` (SSE), `refreshAutomaticTables` (background), and the RFID save/remove handlers; edit-guard selector extended. **NOT** wired into the project-editor reload (would break `check_admin_project_scope_ui`'s pinned sequence — caught + reverted; user-pending doesn't depend on project edits). JS suite **353 pass / 43 fail = EP0 baseline (ZERO new failures)**; `node --check` clean. **Mirror `deploy/docker/admin2-web/` byte-identical for ALL served assets (index.html + app.js + styles.css)** — styles.css reconciled (EP6-1 RESOLVED: stale mirror re-synced to the canonical nested-repo source). **⚠ admin2 deploys via parent pipeline.**
- [x] **EP7** Kotlin: data layer — DTOs + `AuthStatus.pendingApproval`/`queueFull` + repo mapping — 2026-06-20: `WebPasswordStatusResponse += pending_approval`; `WebUserSelfRegistrationResponse += status/pending_approval/queue_full` (projects/active_project now optional w/ defaults); `AuthStatus += pendingApproval/queueFull` (defaults). `AuthRepositoryImpl.getStatus` maps `pendingApproval`; `selfRegister` maps `found = (status=="registered")` + `pendingApproval`/`queueFull` (login/registerPassword/changePassword keep defaults=false). Additive; serialization rules preserved. `compileDebugKotlin` + `testDebugUnitTest` **193/0** (unchanged). Behavioral mapping test → TP4. Kotlin repo only (non-prod).
- [x] **EP8** Kotlin: ViewModel state machine — submit→pending/queue-full; polling; approval→login→engine; rejection silent; auto-open — 2026-06-20: `CheckUiState.isAwaitingApproval`. `submitSelfRegistration` branches: `queueFull`→red `auth.registrationQueueFull` (not auth/awaiting); `pendingApproval`→red `auth.awaitingApproval` + close dialog + `startPendingApprovalPolling` (no `onAuthenticationSucceeded`); else legacy authenticated. `probeStatus`: pending→red bar + poll (no auto-open); else stop poll + existing auto-open + auto-login (approval flips found→true → `attemptLogin` → `onAuthenticationSucceeded` → `ensureEngineRunningIfEligible`, req 7). `maybeAutoOpenAssistanceDialog` guarded against pending (no form re-open). Polling = `viewModelScope` loop, ~20s, exits when not awaiting; restart reconstructs via `init`→`probeStatus`; `onForegroundResume` re-probes when awaiting; `onChaveChanged` stops the poll. Rejection (found=false && !pending) → silent return to unknown-key state (auto-open form, no message — decision 4). `compileDebugKotlin` + `testDebugUnitTest` **193/0** (unchanged). VM behavioral tests → TP4. Kotlin repo only (non-prod).
- [x] **EP9** Kotlin: UI — orange fields when awaiting + red notification + registration-dialog Back arrow + i18n (6) — 2026-06-20: `AuthRow += awaitingApproval` (glow = `FieldGlow.Pending`/orange when `awaitingApproval || isFound` and not authenticated); `CheckScreen` passes `awaitingApproval = state.isAwaitingApproval`; red bar is the existing `NotificationCard` (`NotificationTone.Error`, set by EP8). `SelfRegistrationDialog`: top-left `IconButton(Icons.AutoMirrored.Filled.ArrowBack)` in the header → `onDismiss` (returns to main; `dismissDialog` also blocks auto-reopen), contentDescription `t("settings.backButton")`. i18n: `auth.awaitingApproval` + `auth.registrationQueueFull` added to **all 6** dicts (pt exact, others translated — same strings as Check Web). `compileDebugKotlin` + `compileDebugAndroidTestKotlin` + `testDebugUnitTest` **193/0** + `I18nTest` **16/0**. Kotlin repo only (non-prod). UI smoke/instrumented → TP5.

**Verification suite (PHASE T):**
- [x] **TP0** Test harness, credentials, prod-safety, run recipes (4 surfaces) — 2026-06-20: confirmed all 4 harnesses (backend `TestClient`+`admin_perfil_1/9` fixtures via `pytest_plugins`, flag-flip `monkeypatch.setattr(settings,…)`, `X-Client` header; `prod_e2e` guard + `CHECKING_E2E_PROD`/`CHECKING_E2E_PROD_SUBMIT`; Check Web `node:test`+`vm`; Kotlin `mockk`+`StandardTestDispatcher`+`runTest`, template `CheckViewModelForegroundTest`). Default suites run offline (586/33/8 · 193/0+I18nTest 16/0 · JS 353/43). Recorded in §4. No code change.
- [x] **TP1** Backend: self-registration → pending (exhaustive: pending/queue-full/duplicate/validation/flag-off) — 2026-06-20: expanded `tests/routers/test_web_self_registration_pending.py` to **18** (was 6): android→202 pending (no User, client recorded, **no web session** via authed `/api/web/user-projects`→401), web(no X-Client)→202 client="web", `/auth/status` found=false+pending_approval=true, duplicates (existing pending / existing **User** / **AdminAccessRequest**) →409 + no pending row, **queue-full at the REAL 300 cap** (seed 300 → 301st→200 queue_full, count stays 300) + the limit-2 variant, 6-case **validation** matrix (short name / bad email / pw too short+long / empty projects / confirmation mismatch)→422 no row, **flag-off web & android**→201 authenticated. **18 passed** (targeted). Full-suite confirmation batched with TP2+TP3 (Option A).
- [x] **TP2** Backend: admin approve/reject + project scope + auth gating + audit (exhaustive) — 2026-06-20: expanded `tests/test_admin_user_pending_endpoints.py` to **14** (was 5): auth gating **401**(no session)/**403**(perfil-0 — logs into panel via `user_can_access_admin_panel` but lacks full access)/**200**(perfil-1); **scope** seed P80/P83/P90 → perfil-9 all, perfil-1 {P80}→only S80, perfil-1 {P80,P83}→**union** (not P90), no-membership→none; **approve** multi-project → User w/ `nome_completo`/`email` + memberships for **all** projetos + pending deleted + `/auth/status` found=true, **idempotent** (User already exists → `already_existed`, no 500); **reject** → no User + `/auth/status` found=false&&pending_approval=false; **audit** `user_approve`/`user_reject` CheckEvents (≤16 chars); **404** missing id + **out-of-scope** id (row untouched). **14 passed** (targeted). Full-suite batched with TP3 (Option A).
- [x] **TP3** Backend: migration 0079 on fresh SQLite + non-regression of existing flows — 2026-06-20: migration test (`test_pending_user_registration_migration.py`) green (table + unique `chave` + index `requested_at`; clean downgrade). **Non-regression:** changes are additive/gated — RFID `/api/admin/pending` untouched, `/auth/status` only gained an additive field, `register_web_user` keeps the legacy path under the flag; login/register-password/auth-status (normal users) are primarily in the excluded `test_api_flow.py` (EP0-3) — the full runnable suite passing unchanged is the proof. **Full-suite snapshot (TP1+TP2+TP3 batch, Option A): 607 pass / 33 pre-existing fail / 8 skip** (574 baseline + migration 1 + TP1 18 + TP2 14 = 607; all 33 in `test_transport_ai_suggestion_commands.py`; ZERO new failures).
- [x] **TP4** Kotlin: mapping + VM approval state machine (pending/queue-full/approval→engine/rejection/restart/guards) — 2026-06-20: 2 new files, **+13 tests** (193→**206**, all green). **`AuthMappingTest`** (5): `getStatus` maps `pending_approval`; `selfRegister` status→`pending`/`queue_full`/`registered`. **`SelfRegistrationApprovalTest`** (8, mocked repos + `StandardTestDispatcher`): submit→**pending** (awaiting, `auth.awaitingApproval` Error, password stored, `getHistory`/`orchestrator.runOnce` NOT called, `canSubmit==false`); submit→**queue_full** (`auth.registrationQueueFull` Error, not awaiting/auth); probe→**pending** (awaiting + `canSubmit==false`); **approval** (`found` flips true → `coVerify login(chave, storedPw)`); **rejection/unknown** silent auto-open (dialog=SelfRegistration, tone=None — decision 4); **dismiss** sets guard + no reopen on foreground; **restart** (stored pending key at init → awaiting reconstructed); **awaiting foreground** re-probes, `orchestrator.runOnce` exactly 0. Notes: awaiting tests settle via `runCurrent()` + cancel the 20s poll with `onChaveChanged("")`; approval asserts up to `login()` (login→engine fan-out hits Android statics when auto ON — covered on-device TP5/TP9); restart needed `userSettingsJson` stubbed. **`testDebugUnitTest` 206/0; `I18nTest` green** (both keys in all 6 dicts).
- [x] **TP5** Kotlin: UI smoke (orange fields, red bar, Back arrow, auto-open) — device-pending where needed — 2026-06-20: new instrumented `app/src/androidTest/.../ui/SelfRegistrationApprovalUiSmokeTest.kt` (5 tests, SettingsDialogSmokeTest style, `createComposeRule`): (1) `AuthRow(awaitingApproval=true)` renders key+password fields; (2)/(2b) `NotificationCard(tone=Error)` renders `auth.awaitingApproval` / `auth.registrationQueueFull`; (3) `SelfRegistrationDialog` top-left Back arrow (contentDescription `settings.backButton`) `assertIsDisplayed` + `performClick`→`onDismiss` fired; (4) dialog renders title + read-only key when open (what unknown-key auto-open shows). **`compileDebugAndroidTestKotlin` green.** Compose UI tests assert text/contentDescription/click, **not pixel colors** — the **orange glow / vivid-red bar are visual**, so color confirmation is **device-pending** (the FieldGlow.Pending / tone=Error decisions are unit-covered in TP4); auto-open **trigger** is unit-covered (TP4 `unknown_key_autoopens_registration_silently`). **`adb devices` = none → on-device run (twice via `am instrument`) DEVICE-PENDING** (folded into TP9). Unit suite still **206/0**.
- [x] **TP6** Check Web: JS UI suite (`tests/check_user_approval_ui.test.js`) + existing JS suite green — 2026-06-20: new `tests/check_user_approval_ui.test.js` (**9 tests, all green**), 4 `node:vm` harnesses extracting the EP5 functions from `app.js`: (1) `applyAuthenticationStatusPayload` pending → `authState.pendingApproval`+red `setStatus('auth.awaitingApproval','error')`+`schedulePendingApprovalPolling`+auto-open state carries `pendingApproval` (form won't reopen); (1) `syncAuthenticationFieldHighlights` toggles orange `auth-field-pending` when pending & not authenticated; (2) `submitUserSelfRegistration` queue_full→red `auth.registrationQueueFull` (no auth, no `loadAuthenticatedApplication`) + (2b) pending→awaiting+password kept+polling; (3) approval (next status found=true) clears awaiting + `clearPendingApprovalPolling`; (4) rejection (found=false,!pending) silent (no new status) + `:missing-user` re-auto-opens; (5) unknown→`:missing-user` auto-opens registration **once**, Back (`markCurrent…Dismissed`) keeps it closed, and `:pending-approval` never reopens the form. (Realm gotcha: `reset()` truncates the outer array in place so `deepStrictEqual`'s prototype check passes.) **Fixed `check_registration_widget`** stale `?v=` script-order regex (EP5 bump → 8 versioned scripts; the EP0-3-tracked TP6 fix). **Non-regression:** `check_user_location_ui` 65/0, `check_transport_request_history` 7/0. **Full JS suite 405/363 pass/42 fail** (EP0 baseline 396/353/43 → **+9 new pass, −1 fail, ZERO new failures**). Remaining 42 all pre-existing out-of-scope: 40 admin2/transport + **2 `check_responsive_layout`** (plan002 CSS-contract selector-list drift — `touch-action`/`@media 480px` font-size; untouched, NOT plan003, per EP0-3). **⚠ Check Web deploys with backend → human approval before push.**
- [~] **TP7** End-to-end vs production (guarded, read-mostly) — **AUTHORED; RUN PENDING DEPLOY + OPT-IN** — 2026-06-21: new `tests/test_e2e_prod_user_approval.py` (3 `@pytest.mark.prod_e2e` tests, reuses the plan002 `prod_e2e` guard in `conftest.py`). **Read-only** (`CHECKING_E2E_PROD=1`): `GET /health` 200; `GET /web/auth/status` for a throwaway key exposes `pending_approval` (validates 0079/EP2 deployed). **Controlled write** (additionally `CHECKING_E2E_PROD_SUBMIT=1` + `CHECKING_E2E_ADMIN_CHAVE`/`_SENHA` + `CHECKING_E2E_PROJECT`, all env — never hardcoded; deploy key never read): register a verified-unused throwaway key → **202 pending** → `/auth/status pending_approval=true` → admin login + `GET /admin/user-pending` (scope-visible) + approve → `/auth/status found=true`; **`finally` ALWAYS cleans up** (reject leftover pending + `DELETE /admin/users/{id}` for the created User) and asserts the key is gone. Queue-full NOT exercised vs prod (stays LOCAL, TP1#5); no loops; no left-behind users. **Default-skips confirmed**: `pytest tests/test_e2e_prod_user_approval.py tests/test_prod_e2e_guard.py` → **1 passed / 4 skipped** (all prod-touching skipped; safety guard intact). **Cannot run for real until backend+0079 deployed (human-gated push) and operator opts in.**
- [x] **TP8** Master non-regression + coverage-matrix sign-off — 2026-06-21: full coverage matrix (every plan003 requirement → ≥1 green test across backend/Kotlin/Web) + final snapshots written into **§4**. **Backend 607 pass / 33 pre-existing fail / 11 skip** (ZERO new failures; 33 all transport-AI EP0-2; 11 skip incl. 3 TP7 prod_e2e). **Kotlin `testDebugUnitTest` 206/0** (+`I18nTest`) + `compileDebugKotlin`/`compileDebugAndroidTestKotlin` green. **Check Web JS 405/363/42** (+9 new, −1 fail vs EP0; 42 pre-existing out-of-scope). Protected behaviors all pass. **No uncovered requirement.** Acknowledged non-automated cells: TP5 on-device run + color (device-pending→TP9), TP7 prod e2e (pending deploy+opt-in), approval→engine FGS start (device TP9), admin2 UI (manual EP6 + endpoint tests).

**UX cleanup (Settings → "Instruções de Uso"; independent of the approval feature):**
- [x] **U1** Merge the two Settings rows ("Instruções" + "Manual completo") into one **"Instruções de Uso"** section (i18n, all 6 languages) — 2026-06-21: unified on the **visual `ManualScreen`** (decision confirmed). **Code:** `SettingsDialog.kt` dropped the `School`/`instructionsLabel`/`onInstructionsClick` row (+param +import) → ONE `groupHelp` row (`MenuBook` → `settings.manualLabel`); `CheckScreen.kt` + `CheckingNavHost.kt` dropped the `onNavigateToInstructions` plumbing, `Routes.INSTRUCTIONS` const, its `composable`, and the `InstructionsScreen` import (file **kept, unreferenced**); "Sobre"/`Routes.ABOUT` untouched. **i18n:** `settings.manualLabel` → "Instruções de Uso"/"Usage Instructions"/使用说明/Arahan Penggunaan/Petunjuk Penggunaan/Mga Tagubilin sa Paggamit; `settings.instructionsLabel` removed from all 6; `manual.heading` relabeled in all 6. **Headline:** the full `manual.*` block (was pt/en only) **fully translated into zh/ms/id/tl** (4 parallel subagents, one file each) — structural parity verified: **all 6 dicts = 154 identical manual entries**, no pt fallback. **New sections (step 4):** `manual.sections.scheduledPause` (15) + `manual.sections.accident` (16) added to `ManualScreen.kt` (text-only) + all 6 dicts (reusing `instructions.step4`/`step7`; titles carry no number). **Verify:** `compileDebugKotlin`+`compileDebugAndroidTestKotlin`+`testDebugUnitTest` **206/0** (+`I18nTest`) green; grep confirms zero dangling `instructionsLabel`/`onInstructionsClick`/`Routes.INSTRUCTIONS` refs.
- [x] **U2** Fix the duplicated step numbering ("1. 1. Título" → "1. Título") — 2026-06-21: **already resolved by U1** (the doubled "N. N." lived in the text `InstructionsScreen`, removed from the menu). **Step 1 (verify):** `ManualScreen.ManualSection` renders the number exactly once (bold `index` "01".."16" + **unnumbered** title); the new Scheduled-Pause/Accident titles carry no number. **Step 2 (regression guard):** added `I18nTest.manualSectionTitles_doNotEmbedNumberPrefix` — asserts no `manual.sections.*.title` (all **16** sections × **6** langs = 96) starts with `^\s*\d+\.`; also catches an unresolved key. **Step 3:** no-op (text tutorial not user-facing per U1). **Verify:** `compileDebugKotlin` + `testDebugUnitTest` **207/0** (+1) · **`I18nTest` 17/0** (+1) green; offline grep confirms 96 titles, 0 number-prefixed. **No** manual title content/order changed.

---

## 3. Deviations log (append-only)

- **EP6-1 — 2026-06-20 — pre-existing admin2 `styles.css` source↔mirror divergence (NOT caused by EP6).**
  EP6 touched only `index.html` + `app.js` (mirrored byte-identical). But `diff sistema/app/static/admin2/styles.css
  deploy/docker/admin2-web/styles.css` is **non-empty** and diverges in **both** directions: the source has
  `event-chave-tip-*` / `.membership-projects-panel[hidden]` / different `.user-chave` widths; the mirror has
  `.events-table` column-width rules the source lacks. This predates plan003 (part of the EP0-1 uncommitted
  tree) — a prior styles.css edit on one side was never mirrored. **Not reconciled here:** EP6 needs no
  styles change (the new table reuses `.cadastro-pending-table`), and blindly copying source→mirror would
  drop the mirror's events-table rules (possible prod-styling regression). **Flagged for the human** to
  reconcile styles.css separately before the next admin2 deploy.
  - **RESOLVED — 2026-06-20:** investigated. The admin2 **source is a nested git repo**; its `styles.css`
    is clean at HEAD with commits up to **2026-06-02** (*"tooltip na coluna Chave"* → `event-chave-tip`;
    *"corrige … larguras de coluna"* → restructured the events-table widths; *"min-width … Acoes"*). The
    root-tracked **mirror** styles.css last changed **2026-05-26** — a week older — so it was simply never
    re-synced after the 2026-06-02 admin2 work (the divergence is *stale mirror*, not a real two-way fork;
    the source's "corrige larguras" commit removed the old `.events-table` nth-child widths, and `app.js`
    — already mirrored — uses `event-chave-tip`). The source is canonical (newest + what the JS suite
    tests). Fix: `cp sistema/app/static/admin2/styles.css deploy/docker/admin2-web/styles.css`. Now **all
    served assets (index.html + app.js + styles.css) are byte-identical**; `.github`/`Dockerfile`/`nginx.conf`
    correctly remain source-only (admin2 repo infra, not the served bundle). JS suite unaffected (reads the
    source, unchanged).
- **EP0-1 — 2026-06-20 — baseline sits on a DIRTY root tree.** The root repo (`checking`) has the full
  uncommitted **plan002** delta still present (`models.py`, `routers/web_check.py`, `schemas.py`,
  `services/{checking_history,forms_submit,user_sync}.py`, `static/check/{app.js,i18n-dictionaries.js,
  index.html,styles.css,transport-screen.js}`, `tests/conftest.py`, several new `tests/*.py`) plus all the
  docs (`plan002/003.md`, `temp001/002/003.md`, etc.). The **Kotlin** repo is clean (`main…origin/main`,
  committed at `4d6458b`). plan003 backend/Check-Web work therefore stacks on top of un-pushed plan002
  changes. **Not a blocker** (mirrors temp002 EP0-1); just be aware that `git status` will never be clean
  on root and that a future push carries plan002 **and** plan003 together (still human-gated).
- **EP0-2 — 2026-06-20 — 33 pre-existing backend failures.** All in
  `tests/test_transport_ai_suggestion_commands.py` (async 202 vs asserted 201; documented since plan002).
  Unrelated to plan003. Baseline = "≤33 known fails, all in that one file"; plan003 must add **zero** new.
- **EP0-3 — 2026-06-20 — 43 pre-existing Check Web / JS failures.** `node --test tests/*.test.js` →
  353 pass / 43 fail. Concentrated in **admin2** (`check_admin_*`: presence-forms-layout 10, project-timezone
  3, reports 3, table-refresh 2, accident 2, auth 2, icon 1, polygon 1, project-scope 1) and **transport**
  (`transport_page_date` 12, `transport_i18n_guardrails` 2, `transport_dashboard_burst` 1) — **out of
  plan003 scope**. Only **3** touch `static/check`: `check_registration_widget` (1 — its regex expects 4
  **un-versioned** scripts `i18n-dictionaries→i18n→transport-screen→app`, but `index.html` now ships **8**
  scripts with `?v=5` cache-busting [`automatic-activities, web-client-state, i18n-dictionaries, i18n,
  transport-screen, accident-camera, accident, app`]; stale test, not a functional break) and
  `check_responsive_layout` (2 — CSS-contract regexes for `touch-action: manipulation` and
  `grid-template-columns: repeat(3, …)` in `styles.css` drifted). These are a **dirty-baseline** artifact
  of the un-committed plan002 `static/check` state, analogous to EP0-2. plan003 EP5/EP6 must add **zero**
  new JS failures; the `check_registration_widget` regex will need updating when EP5 re-bumps `?v=` (track
  under TP6).

---

## 4. Baseline log (filled by EP0, then mostly read-only)

- **Kotlin** (`checking_kotlin/`, EP0 — 2026-06-20): `testDebugUnitTest` **193 passed / 0 failed / 0
  skipped → GREEN**; `compileDebugKotlin` clean. `git status` = `main…origin/main` (clean; HEAD `4d6458b`).
- **Backend** (`python -m pytest -q --ignore=tests/test_api_flow.py`, repo root, EP0 — 2026-06-20):
  **574 passed / 33 failed / 8 skipped** (619s). **All 33 failures pre-existing & unrelated** — entirely
  in `tests/test_transport_ai_suggestion_commands.py` (EP0-2). Baseline = "≤33 known fails, all in that one
  file." plan003 must add **zero** new failures beyond this set.
- **Check Web / JS** (`node --test tests/*.test.js`, EP0 — 2026-06-20): **396 tests / 353 pass / 43 fail /
  0 skipped** (~29s). All 43 pre-existing (EP0-3): admin2 + transport (out of scope) + 3 `static/check`
  drift. plan003 EP5/EP6 must add **zero** new JS failures.
- **Trees:** Kotlin clean; root dirty (un-pushed plan002 + docs — EP0-1).
- **Test inventory (touched by plan003):** backend `tests/` (esp. `tests/routers/test_web_*`,
  `tests/test_admin_*`, `tests/conftest.py` with the `prod_e2e` guard); Check Web `tests/check_*.test.js`
  (esp. `check_registration_widget`, `check_user_location_ui`); Kotlin auth/VM unit tests under
  `app/src/test/.../presentation/check` + `data/repository` + `i18n/I18nTest`.

### TP0 — test harness, credentials, prod-safety, run recipes (confirmed 2026-06-20; no code change)
- **Run commands (all default to LOCAL/offline):** backend `python -m pytest -q --ignore=tests/test_api_flow.py`
  (repo root); Kotlin `cd checking_kotlin && ./gradlew compileDebugKotlin compileDebugAndroidTestKotlin
  testDebugUnitTest`; Check Web JS `node --test tests/*.test.js`. **Never** `connectedAndroidTest`.
- **Backend test style (confirmed via the EP3/EP4 tests already written):** `TestClient(app)` + the shared
  **`admin_perfil_1` / `admin_perfil_9`** `AdminSession` fixtures (auto-registered via
  `pytest_plugins = ["tests.conftest_accident"]` in `tests/conftest.py`); `X-Client` via a header dict
  (`{"X-Client": "checking-android"}`); **flag-flip** = `monkeypatch.setattr(settings,
  "check_user_approval_required", True/False)` and `…, "pending_user_registration_limit", N`; per-test
  cleanup of `pending_user_registrations` + created users; DB = shared `test_checking.db` (`create_all`
  builds the new table).
- **Prod-safety (reuse plan002):** `prod_e2e` marker + `pytest_collection_modifyitems` skip in
  `tests/conftest.py` (`prod_e2e_enabled()` ← `CHECKING_E2E_PROD=1`); self-verified by
  `tests/test_prod_e2e_guard.py`. WRITE/submit prod tests ADDITIONALLY require **`CHECKING_E2E_PROD_SUBMIT=1`**
  (`tests/test_e2e_prod.py`). Default suites are fully offline (prod tests skipped).
- **Fresh-key convention (§0.7):** existing user `TEST/000000`; throwaway 4-char keys (e.g. `NEW1`, `PNA1`,
  `UP01`) for pending-registration tests so the row goes through the pending path cleanly + is cleaned up.
- **Check Web JS harness:** `node:test` + `node:vm` + `fs.readFileSync` of `static/check/{index.html,app.js}`;
  mock DOM/`fetch` in the VM sandbox. Pattern to reuse for `check_user_approval_ui.test.js` (TP6).
- **Kotlin VM test style:** `mockk(relaxed=true)` for `AuthRepository`/`AppPreferencesDataSource`/
  `SecurePasswordStore`/`ProjectRepository`/orchestrator; `StandardTestDispatcher` + `Dispatchers.setMain`
  + `runTest`; template = `presentation/check/CheckViewModelForegroundTest.kt` (set stored language "pt" to
  avoid the un-mocked `LocaleList.getDefault()` Android stub). Pattern to reuse for TP4.
- **Verify:** all three default suites confirmed running offline during EP0–EP9 (backend 586/33/8, Kotlin
  193/0 + I18nTest 16/0, Check Web JS 353/43). No new test files in TP0 (infrastructure confirmation only).

### Protected behaviors — MUST remain identical end-to-end
- Login (`/auth/login`), `register-password`, password change, and `/auth/status` for **existing** users.
- Check-in/check-out engine, automatic check-out, skip-if-unchanged, offline queue + replay, geofencing,
  FGS, transport, accident mode.
- **RFID** pending (`/api/admin/pending`, approve/reject) — only the HTML **title** changes.
- Any **already-authenticated** client (app or web): zero behavior change.
- `users` table and every query/count/sync/report over it (pendings never enter `users`).

### TP8 — Master coverage matrix & sign-off (2026-06-21)

**Final suite snapshot (all LOCAL/offline):**
- **Backend** `python -m pytest -q --ignore=tests/test_api_flow.py` → **607 passed / 33 failed / 11 skipped** (536s). All 33 failures pre-existing & unrelated (entirely `tests/test_transport_ai_suggestion_commands.py`, EP0-2); 11 skip = 8 prior + 3 new TP7 `prod_e2e` (default-skipped). **ZERO new failures.**
- **Kotlin** (`checking_kotlin/`) → `compileDebugKotlin` + `compileDebugAndroidTestKotlin` green; `testDebugUnitTest` **206 passed / 0 failed** (incl. `I18nTest`). (EP0 baseline was 193 → +13 from TP4.)
- **Check Web JS** `node --test tests/*.test.js` → **405 tests / 363 pass / 42 fail** (EP0 baseline 396/353/43 → **+9 new pass (TP6), −1 fail (check_registration_widget), ZERO new failures**). The 42 are all pre-existing out-of-scope: 40 admin2/transport + 2 `check_responsive_layout` (plan002 CSS-contract drift; untouched per EP0-3).

**Coverage matrix (each plan003 requirement → ≥1 green test):**

| Requirement | Backend | Kotlin app | Check Web |
|---|---|---|---|
| register → **pending** (android + web) | TP1 (android→202, web→202 `client="web"`) | TP4 `AuthMappingTest.selfRegister` pending; TP4 VM submit→pending | TP6.2b |
| **client** recorded (X-Client→`client` col) | TP1 (`checking-android` vs `web`) | — (header set in `AuthRepositoryImpl`) | — |
| `/auth/status` exposes **`pending_approval`** | TP1#3 (found=false+pending=true) | TP4#1 `getStatus` maps it | TP6.1 |
| duplicates → **409** (User/pending/AdminAccessRequest) | TP1#4 | — | — |
| **queue cap 300** (LOCAL only) | TP1#5 (real 300 + limit-2) | — | (not run vs prod, TP7#3) |
| validation → **422** | TP1#6 (6-case) | — | — |
| **flag-off legacy** (201 authenticated) | TP1#7 + TP3#2 regression | — | — |
| admin **gating** 401/403/200 | TP2#1 (no-session/perfil-0/perfil-1) | — | — |
| **project scope** (union + perfil 9) | TP2#2 (P80/P83/P90) | — | — |
| **approve** → User+memberships+status flip | TP2#3 (multi-proj, fields, idempotent) | — | TP7#2 (prod, run pending) |
| **reject** → no User | TP2#4 (+`/auth/status` cleared) | — | — |
| **audit** `user_approve`/`user_reject` ≤16 | TP2#5 (CheckEvent) | — | — |
| **migration 0079** (table/unique/index/downgrade) | TP3#1 | — | — |
| app **orange fields + red bar** | — | TP4 (FieldGlow.Pending / tone=Error logic); TP5#1/#2 instrumented (compile; **color device-pending**) | TP6.1 (`auth-field-pending` + red `setStatus`) |
| **Back arrow** (decision 3) | — | TP5#3 (contentDescription + `onDismiss`) | TP6.5 (Back keeps it closed) |
| **auto-open** on unknown key | — | TP4 `unknown_key_autoopens` + TP5#4 | TP6.5 (`:missing-user`→open once) |
| **approval → login → engine** (req 7) | — | TP4 `approval` (→`login(chave,storedPw)`; engine = existing auth path, **device TP9**) | TP6.3 (found=true → normal flow) |
| **rejection silent** (decision 4) | — | TP4 `rejection` (no message) | TP6.4 (no status message) |
| **web mirror** of all of the above | — | — | TP6 (`check_user_approval_ui` 9/9) |
| **admin2** endpoints/UI | TP2 (endpoints) | — | manual EP6 (mirror byte-identical; no JS harness) |

**Acknowledged non-automated cells (verified by other means / deferred):**
- **TP5 on-device run + actual colors** — Compose tests assert text/contentDescription/click, not pixels; the orange-glow/red-bar **color** + the `am instrument` ×2 run are **device-pending** (no device attached) → folded into **TP9**. The underlying glow/tone/auto-open decisions ARE unit-covered (TP4).
- **TP7 prod e2e** — authored + default-skip verified, but the real run is **pending the backend+0079 deploy (human-gated push) and operator opt-in** (`CHECKING_E2E_PROD[_SUBMIT]`, admin creds, project via env).
- **approval → engine start** (req 7) — asserted up to `login()` in TP4; the `login → onAuthenticationSucceeded → ensureEngineRunningIfEligible` chain is the pre-existing authenticated path (compile-verified EP9) and the live FGS start is **on-device (TP9)**.
- **admin2 UI** — no JS test harness exists; covered by backend endpoint tests (TP2) + the manual EP6 checklist + byte-identical `deploy/docker/admin2-web/` mirror.

**Protected behaviors (above) — all still pass:** the full backend suite is green except the same 33 pre-existing transport-AI reds (login/`register-password`/password-change/`/auth/status` for existing users, RFID pending, engine/sync/transport/accident in the runnable set); Kotlin 206/0; Check Web JS adds zero new failures. **No plan003 requirement is uncovered** (modulo the acknowledged device/deploy cells).

---

# EXECUTION PHASES (drive `plan003.md` to completion)

> Each EP recaps the goal/context and points to the `plan003.md` section to apply exactly, then runs its
> own Verify. Backend + Check Web changes deploy to PRODUCTION on push — **never push without human
> approval**; the migration must run in prod before the feature is relied upon.

## EP0 — Baseline
**Goal:** prove all suites green and snapshot what must not regress.
**Do:** run Kotlin `./gradlew testDebugUnitTest compileDebugKotlin` (in `checking_kotlin/`), backend
`python -m pytest -q --ignore=tests/test_api_flow.py` (repo root), and the Check Web JS suite. Record
counts/date + the protected-behavior snapshot in Section 4. If anything in scope is red, STOP.
**Verify:** Section 4 has baseline counts + clean `git status` (both repos).
**Update:** tick EP0; log anomalies in Section 3.

## EP1 — Backend: model + migration + config (apply plan003 §2.1, §2.2, §1.4)
**Goal:** add the storage + the rollback flag, with **no behavior change yet**.
**Do:**
1. `models.py`: add `PendingUserRegistration` exactly per §2.1 (unique `chave`; index on `requested_at`;
   `projetos_json` as `Text`; `email` nullable; `client` nullable `String(16)`).
2. `alembic/versions/0079_add_pending_user_registrations.py`: `create_table` (+ unique + index);
   `downgrade` = `drop_table`. Chain `down_revision` to `0078`.
3. `core/config.py` `Settings`: add `check_user_approval_required: bool = True` and
   `pending_user_registration_limit: int = 300` (env-overridable, pydantic-settings).
**Do NOT:** wire any endpoint to the table yet.
**Verify:** `pytest -q` green; the migration applies on a **fresh SQLite** (create + downgrade) — add a
quick migration test now or in TP3. `create_all` in dev sees the new table.
**Update:** tick EP1. **Backend change → flag for human approval before any deploy (Section 3).**

## EP2 — Backend: schemas + status + creation helper (apply plan003 §2.3, §2.4 response shape, §3 helper)
**Goal:** extend the contract types and the status endpoint; extract the `User`-creation helper — **still
no behavior change** to register-user.
**Do:**
1. `schemas.py`: `WebPasswordStatusResponse += pending_approval: bool = False`;
   `WebUserSelfRegistrationResponse += status: Literal["registered","pending","queue_full"] =
   "registered"`, `pending_approval: bool = False`, `queue_full: bool = False`, and make `projects`
   (`default_factory=list`) and `active_project` (`default=""`) **optional**. Add `AdminUserPendingRow`.
2. `web_check.py`: extract `create_user_from_registration(db, *, chave, nome, projetos, email,
   password_hash) -> User` from the current body of `register_web_user` (same `User(...)` construction +
   `replace_user_project_memberships`); refactor `register_web_user` to call it. **Byte-identical
   behavior.**
3. `_build_web_password_status` / `get_web_password_status`: compute `pending_approval` per §2.3 (query
   `PendingUserRegistration` by chave only when no `User`). Keep all existing fields exactly.
**Verify:** `pytest -q` green (existing `/auth/status` and register tests unchanged); status response now
carries `pending_approval=false` for normal users.
**Update:** tick EP2. **Backend change → human approval before deploy.**

## EP3 — Backend: register-user pending behavior (apply plan003 §2.4, §1.3, §1.4)
**Goal:** the core gate. With the flag ON, autocadastro creates a **pending** row and does **not**
authenticate; with it OFF, behavior is exactly legacy.
**Do:** rewrite `register_web_user` per §2.4:
- 409s for existing `User` / existing pending (`uq_pending_user_registrations_chave`) / existing
  `AdminAccessRequest` (keep current 409s).
- `gate = settings.check_user_approval_required` (no `X-Client` branch).
- gate OFF → call `create_user_from_registration` + `_set_web_session_chave` + notify + return `201
  {status:"registered", authenticated:true, projects, active_project}` (legacy).
- gate ON → `COUNT(pending)`; `>= limit` → `200 {status:"queue_full", authenticated:false}` (insert
  nothing); else insert `PendingUserRegistration` (`client = request.headers.get("X-Client") or "web"`,
  `requested_at = now`), **no `User`, no session**, `notify_admin_data_changed("admin")` +
  `notify_admin_data_changed("register")`, return `202 {status:"pending", authenticated:false,
  pending_approval:true, projects, active_project:""}`.
- Cap race guard: `COUNT`+`INSERT` in one transaction; after insert, re-check count and rollback→`queue_full`
  if it exceeded.
**Do NOT:** branch the gate on `X-Client`; touch the web session for the pending path.
**Verify:** focused `pytest` (full matrix in TP1): flag-on any client → 202 pending + 0 `User` + 1 pending
row + no session; flag-on at 300 → 200 queue_full + count stays 300; flag-off → 201 authenticated + `User`
created; duplicate key → 409; invalid payload → 422.
**Update:** tick EP3. **Backend change → human approval before deploy.**

## EP4 — Backend: admin user-pending endpoints (apply plan003 §2.5)
**Goal:** list / approve / reject, project-scoped, audited.
**Do (mirror the RFID `/pending` pattern in `admin.py`):**
1. `GET /api/admin/user-pending` → `list[AdminUserPendingRow]` ordered by `requested_at desc`, filtered by
   a new `user_pending_matches_admin_scope(...)` (intersect `projetos_json` with
   `resolve_effective_admin_project_names(db, current_admin)`; perfil 9 → all). `Depends(require_full_admin_session)`.
2. `POST /api/admin/user-pending/{id}/approve` → load row (404 if gone / out of scope); if `User(chave)`
   already exists, treat as already-approved (delete row, return ok); else
   `create_user_from_registration(...)` from the row's fields, `db.delete(row)`, `commit`,
   `notify_admin_views("register","event")` + `notify_web_check_data_changed()`, `log_event(action=
   "user_approve")`.
3. `POST /api/admin/user-pending/{id}/reject` → load (404 if gone/out of scope), `db.delete(row)`, `commit`,
   `notify_admin_views("register","event")`, `log_event(action="user_reject")`.
**Do NOT:** use `require_admin_identity` (no `*_by_admin_id` writes); exceed 16 chars in `action`.
**Verify:** focused `pytest` (full matrix in TP2): GET requires admin (401/403), scoped; approve creates
`User`+memberships and removes the row; reject removes the row with no `User`; both idempotent against a
missing/duplicate row.
**Update:** tick EP4. **Backend change → human approval before deploy.**

## EP5 — Check Web: awaiting/queue-full UI + auto-open + Back + polling (apply plan003 §6)
**Goal:** mirror the app's approval UX in the browser client (decision 1). Deploys with the backend.
**Do (in `sistema/app/static/check/`):**
1. `app.js`: read `pending_approval` from `auth/status`; keep `authState.pendingApproval`. When pending,
   force `auth-field-pending` (orange) on the key/password fields and set `notificationState` to
   `t('auth.awaitingApproval')` with the **error/red** tone; `renderNotifications()`.
2. On `register-user` response: `status==="pending"` → enter awaiting (orange + red), do **not**
   authenticate; `status==="queue_full"` → red `t('auth.registrationQueueFull')`, do **not** authenticate.
3. **Polling:** while awaiting, re-validate `auth/status` periodically (reuse the existing status mechanism):
   `found===true` → authenticate with the in-memory password / re-login → normal flow (engine runs);
   `found===false && !pending_approval` → **rejected**: silently return to the unknown-key state (decision
   4 — no message).
4. **Auto-open (decision 3):** when the typed key is unknown, open `registrationDialog` automatically (keep
   `requestRegistrationButton` as fallback).
5. `index.html` + `styles.css`: add a **Back arrow** at the top-left of `registrationDialog` that closes it
   and returns to the main screen (reuse the dialog close/back style). Bump `?v=` for changed assets.
6. `i18n-dictionaries.js`: add `auth.awaitingApproval` + `auth.registrationQueueFull` to **all 6** dicts
   (pt exact; others translated; pt fallback via `t()`).
**Do NOT:** change behavior for already-authenticated users; leave assets un-cache-busted.
**Verify:** the Check Web JS suite green incl. the new `tests/check_user_approval_ui.test.js` (authored in
TP6); manual smoke of pending/queue-full/auto-open/Back.
**Update:** tick EP5. **Check Web change → deploys with backend → human approval before deploy.**

## EP6 — Admin2: "Pendências de Usuários" table (apply plan003 §4)
**Goal:** the admin surface for approve/reject. **Pure frontend** (uses EP4 endpoints).
**Do (in `sistema/app/static/admin2/`):**
1. `index.html`: rename `<h2>Cadastro de Pendências</h2>` → **`<h2>Pendências de RFID</h2>`**; insert, **above**
   `data-cadastro-section="pendencias"`, a new `data-cadastro-section="pendencias-usuarios"` article with a
   table (cols **Data, Chave, Nome Completo, Projetos, E-Mail, Ações**) and `<tbody id="userPendingBody">`.
2. `app.js`: `loadUserPending({silent})` mirroring `loadPending()` (fetch `/api/admin/user-pending`; render
   rows with **Aprovar**/**Reprovar** buttons carrying `data-id`; format Data via the existing helper;
   Projetos as a list; empty state via `renderEmptyStateRow("userPendingBody", 6, …)`;
   `applyResponsiveLabels`). Call it everywhere `loadPending()` runs (initial `Promise.all`, SSE refreshes,
   manual refresh). Add a `#userPendingBody` click handler: **Aprovar** → `postJson(".../approve")`;
   **Reprovar** → `confirm(...)` + `postJson(".../reject")`; then reload `loadUserPending()` +
   `loadRegisteredUsers()`. Include `#userPendingBody` in the edit-in-progress guard (~4965).
3. `styles.css`: reuse `.cadastro-pending-table`; adjust only if the E-Mail column needs width.
4. **Mirror** the changed files byte-for-byte to `deploy/docker/admin2-web/`.
**Do NOT:** forget the mirror; alter the RFID table behavior.
**Verify:** with the backend running, the new table lists a pending, **Aprovar** creates the user (row
disappears, user appears in registered users), **Reprovar** removes it; SSE refresh works; mirror is
identical (diff clean).
**Update:** tick EP6.

## EP7 — Kotlin: data layer (apply plan003 §5.1)
**Goal:** carry the new contract to the domain layer; no UI change yet.
**Do:** `WebPasswordStatusResponse += pendingApproval=false`; `WebUserSelfRegistrationResponse += status,
pendingApproval=false, queueFull=false` (+ `projects` optional). `AuthStatus += pendingApproval=false`
(and transient `queueFull=false`). Map them in `AuthRepositoryImpl.getStatus`/`login`/`selfRegister`
(`selfRegister` maps `status` → `pendingApproval`/`queueFull`). Keep serialization rules (`explicitNulls`,
send `""` not `null` for str-with-default).
**Verify:** `compileDebugKotlin` + `testDebugUnitTest` green; add a mapping unit test (or defer to TP4).
**Update:** tick EP7.

## EP8 — Kotlin: ViewModel state machine (apply plan003 §5.2)
**Goal:** the client behavior — submit→pending/queue-full; poll for approval; on approval log in and run the
engine; on rejection silently reset; auto-open on unknown key.
**Do (in `CheckViewModel.kt` / `CheckUiState.kt`):**
1. `CheckUiState`: `val isAwaitingApproval get() = authStatus?.pendingApproval == true`.
2. `submitSelfRegistration()` success branch: **always** `securePasswordStore.setPassword(chave, senha)`;
   `queueFull` → red `auth.registrationQueueFull`, not awaiting, not authenticated; `pending` →
   `authStatus(pendingApproval=true, authenticated=false)` + red `auth.awaitingApproval` + close dialog;
   **remove** the `onAuthenticationSucceeded` call on these paths.
3. **Polling:** while `isAwaitingApproval`, a light periodic `getStatus` (~20–30s via `viewModelScope` +
   `delay`, cancelled on exit) **and** re-validate in `onForegroundResume`. On response: `pending_approval`
   → stay; `found==true` → `login(chave, stored)` → `onAuthenticationSucceeded` (**engine runs**, req. 7);
   `found==false && !pending_approval` → exit awaiting **silently** (decision 4) back to unknown-key state.
4. **Restart:** initial `getStatus` reconstructs awaiting from `pending_approval`.
5. **Auto-open (decision 3):** when `getStatus` returns `found=false && !pending_approval` for a freshly
   typed 4-char key, open the registration dialog automatically (once per key; respect
   `dismissedAssistanceForChave`).
**Do NOT:** authenticate a pending user; run the engine for a non-authenticated user (the orchestrator is
already gated by `isAuthenticated` — keep it so).
**Verify:** `compileDebugKotlin` + `testDebugUnitTest` green (VM tests in TP4).
**Update:** tick EP8.

## EP9 — Kotlin: UI + i18n (apply plan003 §5.3, §5.4)
**Goal:** the visible state — orange fields, red bar, Back arrow — in 6 languages.
**Do:**
1. `AuthRow`: add `awaitingApproval: Boolean = false`; glow = `FieldGlow.Pending` (orange) when
   `awaitingApproval && !isAuthenticated`, else the current rule. `CheckScreen` passes
   `awaitingApproval = state.isAwaitingApproval`. The red bar is the existing `NotificationCard` with
   `notificationTone = Error`.
2. **Back arrow (decision 3):** add a top-left `IconButton` with `Icons.AutoMirrored.Filled.ArrowBack` to
   the registration dialog that dismisses it and returns to the main screen (clears `selfRegistrationFields`;
   does not alter the typed key). `contentDescription` from `t("settings.backButton")` (or a new
   `auth.backToMain`).
3. i18n: add `auth.awaitingApproval`, `auth.registrationQueueFull` (and `auth.backToMain` if used) to
   **Pt, En, Zh, Ms, Id, Tl** (pt exact).
**Verify:** `compileDebugKotlin` + `compileDebugAndroidTestKotlin` + `testDebugUnitTest` + `I18nTest` green.
**Update:** tick EP9.

---

# PHASE T — verification suite

> Runs after EP0–EP9. Goal: prove the approval gate is correct and robust on **all surfaces**, and that
> **every existing flow is untouched**. Default everything to LOCAL.

## Prompt TP0 — Test harness, credentials, prod-safety, run recipes
**Goal:** stand up/confirm the infrastructure the rest depends on, across the 4 surfaces.
**Steps:**
1. Confirm backend test style: per-test isolated SQLite (`_make_session(tmp_path)`) or `TestClient(app)` +
   login session; how to set the `X-Client` header and the admin session in tests; how to flip
   `CHECK_USER_APPROVAL_REQUIRED` per test (monkeypatch `settings`).
2. Confirm/reuse the `prod_e2e` guard (`tests/conftest.py`, `tests/test_prod_e2e_guard.py`) from plan002;
   document `CHECKING_E2E_PROD` / `CHECKING_E2E_PROD_SUBMIT`.
3. Confirm the Check Web JS harness (how `tests/check_*.test.js` mock the DOM + fetch). Note the pattern to
   reuse for `check_user_approval_ui.test.js`.
4. Confirm Kotlin VM test style (mocked repos, `runTest`/`StandardTestDispatcher`, `mockk`).
5. Record in Section 4: test roots per surface, the fresh-key convention (§0.7), the flag-flip recipe, and
   the run commands.
**Do NOT:** let the default run hit prod or require a device.
**Verify:** default backend `pytest` + Kotlin `testDebugUnitTest` + Check Web JS suite all run offline.
**Update:** tick TP0.

## Prompt TP1 — Backend: self-registration → pending (exhaustive)
**Goal:** pin every branch of the new `register-user`.
**Tests (`tests/routers/test_web_self_registration_pending.py`, LOCAL):**
1. **Flag ON, with `X-Client: checking-android`:** `register-user` (fresh key) → **202**,
   `status=="pending"`, `authenticated==false`, `pending_approval==true`; **0** `User`; **1** pending row
   with `client=="checking-android"`; **no** web session set.
2. **Flag ON, no `X-Client` (web):** same as #1 but `client=="web"` (proves the gate is system-wide, not
   `X-Client`-dependent).
3. `GET /auth/status` for that key → `found==false`, `pending_approval==true`.
4. **Duplicates:** 2nd pending for same key → **409**; key already a `User` (`TEST`) → **409**; key in
   `admin_access_requests` → **409**. No extra row created.
5. **Queue full:** seed 300 pending rows → next register → **200**, `status=="queue_full"`,
   `pending_approval==false`; count stays **300** (nothing inserted).
6. **Validation:** invalid payloads (short name, bad email, password out of 3–10, empty projects,
   confirmation mismatch) → **422**; no pending row.
7. **Flag OFF** (`CHECK_USER_APPROVAL_REQUIRED=false`), web **and** android → **201**,
   `authenticated==true`, `User` created, memberships set (legacy intact).
**Verify:** all green. **Update:** tick TP1.

## Prompt TP2 — Backend: admin approve/reject + scope (exhaustive)
**Goal:** pin the admin surface.
**Tests (`tests/test_admin_user_pending_endpoints.py`, integration HTTP):**
1. **Auth gating:** `GET /api/admin/user-pending` with no admin session → **401**; with a `User` perfil 0
   session → **403**; with admin (perfil 1) → **200**.
2. **Scope (decision 2):** seed pending rows across projects P80/P83/P90; admin scoped to {P80} sees only
   P80 pendings; admin scoped to {P80,P83} sees the **union**; **perfil 9** sees **all**.
3. **Approve:** `POST .../{id}/approve` → creates `User` with `nome_completo`/`email` and **memberships for
   all `projetos`**; pending row deleted; subsequent `GET` no longer lists it; `GET /auth/status` for that
   key now `found==true`; **idempotent** if `User(chave)` already exists (no 500, row cleaned).
4. **Reject:** `POST .../{id}/reject` → pending row deleted; **no** `User` created; `GET /auth/status` →
   `found==false && pending_approval==false`. (Silent on the client — verified in TP4/TP6.)
5. **Audit:** `log_event` rows written with `action in {"user_approve","user_reject"}` (≤16 chars).
6. **Not-found / out-of-scope id:** approve/reject of a missing or out-of-scope id → **404**, no change.
**Verify:** all green. **Update:** tick TP2.

## Prompt TP3 — Backend: migration + non-regression
**Goal:** the schema change is safe and nothing else moved.
**Tests:**
1. `tests/test_pending_user_registration_migration.py`: on a **fresh SQLite**, upgrade to `0079` →
   table + unique(`chave`) + index(`requested_at`) exist; `downgrade` drops it cleanly.
2. **Non-regression:** existing tests for login, `register-password`, password change, `/auth/status`
   (normal users), and **RFID** pending (`/api/admin/pending`, approve/reject) pass unchanged.
3. Full-suite snapshot: `python -m pytest -q --ignore=tests/test_api_flow.py` → record counts; the only
   reds remain the **33 pre-existing** `test_transport_ai_suggestion_commands.py` failures; **zero** new
   failures attributable to plan003.
**Verify:** green (modulo the known 33). **Update:** tick TP3.

## Prompt TP4 — Kotlin: mapping + VM approval state machine (exhaustive)
**Goal:** pin the client logic with fast, deterministic unit tests (mocked repos; `runTest`).
**Tests:**
1. `AuthMappingTest`: `getStatus` maps `pending_approval`; `selfRegister` maps `status` →
   `pending`/`queue_full`/`registered` onto `AuthStatus`.
2. `SelfRegistrationApprovalTest` (VM):
   - **pending:** `submitSelfRegistration` → `isAwaitingApproval==true`,
     `notificationPrimary==auth.awaitingApproval`, `notificationTone==Error`, password stored,
     **`onAuthenticationSucceeded` NOT called** and the orchestrator/engine NOT run.
   - **queue_full:** notification `auth.registrationQueueFull` (Error), not awaiting, not authenticated.
   - **approval:** polling `getStatus` returns `found==true` → VM calls `login(chave, stored)` →
     `onAuthenticationSucceeded` path (assert an engine evaluation is triggered — req. 7).
   - **rejection:** polling returns `found==false && !pending_approval` → exits awaiting **with no
     notification** (decision 4).
   - **restart:** initial `getStatus` with `pending_approval==true` → awaiting reconstructed.
   - **auto-open:** unknown key (`found==false && !pending_approval`) → registration dialog opened once
     (respects `dismissedAssistanceForChave`).
3. **Guard:** a pending/unauthenticated user → `canSubmit==false`; orchestrator gate keeps the engine off
   when not authenticated (extend the existing gate tests).
**Verify:** `testDebugUnitTest` green; `I18nTest` green (new keys present in 6 dicts). **Update:** tick TP4.

## Prompt TP5 — Kotlin: UI smoke (instrumented; device-pending where needed)
**Goal:** the visible spec.
**Tests (Compose/androidTest, in the style of `SettingsDialogSmokeTest`; mark pending-for-device if no
device):**
1. `AuthRow` with `awaitingApproval=true` → key/password fields show the **orange** (Pending) glow.
2. Notification bar with `tone=Error` + `auth.awaitingApproval` → renders **red**; queue-full message
   renders red.
3. Registration dialog shows a **top-left Back arrow** that dismisses it and returns to the main screen.
4. Unknown key → dialog **auto-opens**.
**Verify:** `compileDebugAndroidTestKotlin` green; on-device run twice via `am instrument`, else
"device verification pending". **Update:** tick TP5.

## Prompt TP6 — Check Web: JS UI suite
**Goal:** the browser client mirrors the app.
**Tests (`tests/check_user_approval_ui.test.js`, mocking DOM + fetch like the existing `check_*.test.js`):**
1. `auth/status` with `pending_approval=true` → key/password fields get class `auth-field-pending`
   (orange); `notificationState` shows `auth.awaitingApproval` with the **error/red** tone; not
   authenticated.
2. `register-user` → `status:"queue_full"` → red `auth.registrationQueueFull`; not authenticated.
3. Approval: next `auth/status` `found=true` → proceeds to the authenticated state (engine/normal flow).
4. Rejection: `found=false && !pending_approval` → returns to unknown-key state with **no** message.
5. Unknown key → `registrationDialog` **auto-opens**; the **Back** control closes it.
**Also:** run the existing JS suite (`check_user_location_ui`, `check_transport_request_history`) for
non-regression.
**Verify:** JS suite green. **Update:** tick TP6.

## Prompt TP7 — End-to-end vs production (guarded, read-mostly)
**Goal:** confirm the wired system once the backend + Check Web are deployed. **Pending deploy + opt-in.**
**Steps (default skipped; `@pytest.mark.prod_e2e`; writes need `CHECKING_E2E_PROD_SUBMIT=1` + approval):**
1. Read-only: `GET /api/health` ok; `GET /auth/status` for a brand-new key returns the field (validates
   `0079`/EP2 deployed).
2. Controlled (double-guarded): register a throwaway key → expect `202 pending`; `GET /auth/status` →
   `pending_approval=true`; approve it via an admin session → `GET /auth/status` → `found=true`; clean up
   (reject/remove the test user) and annotate.
3. Queue behavior is **not** exercised against prod (would require 300 rows) — keep it LOCAL (TP1#5).
**Do NOT:** loop submissions; leave test users in prod; expose the deploy key.
**Verify:** read-only checks pass; any write is annotated + cleaned. **Update:** tick TP7 (or `[~]` pending
deploy).

## Prompt TP8 — Master non-regression + coverage-matrix sign-off
**Goal:** one place that proves every requirement maps to a green test and nothing regressed.
**Steps:**
1. Build the coverage matrix (each row → ≥1 test): register→pending (TP1#1/2), client recorded (TP1#1/2),
   status `pending_approval` (TP1#3, TP4#1, TP6#1), duplicates 409 (TP1#4), **queue cap 300** (TP1#5),
   validation 422 (TP1#6), **flag-off legacy** (TP1#7, plus regression TP3#2), admin gating (TP2#1),
   **project scope incl. union + perfil 9** (TP2#2), approve→User+memberships+status flip (TP2#3,
   TP7#2), reject→no user (TP2#4), audit (TP2#5), migration (TP3#1), app orange fields + red bar (TP5#1/2),
   **Back arrow** (TP5#3, TP6#5), **auto-open** (TP4#auto-open, TP5#4, TP6#5), approval→login→engine
   (TP4#approval), **rejection silent** (TP4#rejection, TP6#4), web mirror of all of the above (TP6),
   admin2 endpoints (TP2 + manual EP6).
2. Run the full suites and snapshot counts: backend `pytest`, Kotlin `testDebugUnitTest`/`I18nTest`/compiles,
   Check Web JS. Confirm the **protected behaviors** (Section 4) all still pass.
3. List acknowledged **non-automated** cells (e.g., TP5 device-only items; TP7 prod e2e pending deploy).
**Verify:** no uncovered requirement; suites green (modulo the known 33 backend reds). **Update:** tick TP8;
write the final matrix into Section 4.

---

# PHASE U — UX cleanup: unify Settings "Instruções de Uso" (independent of plan003)

> Self-contained UX fix, **Kotlin app only** (`checking_kotlin/`). Two near-duplicate Settings entries —
> **"Instruções"** (`settings.instructionsLabel` → `InstructionsScreen`) and **"Manual completo"**
> (`settings.manualLabel` → `ManualScreen`) — become a single **"Instruções de Uso"** entry, and the step
> numbering bug is fixed. Keep every other behavior intact (golden rule 1). Can run before, during, or
> after the EP/TP phases; it touches no backend/web/admin code.

## Prompt U1 — Merge "Instruções" + "Manual completo" → one "Instruções de Uso"
**Goal:** one Settings row, one screen, one source of truth, in all 6 languages.
**Context to load:**
- `presentation/components/SettingsDialog.kt` — the Ajuda/`groupHelp` group has TWO rows: the `School`-icon
  row `settings.instructionsLabel` → `onInstructionsClick`, and the `MenuBook`-icon row
  `settings.manualLabel` → `onManualClick`.
- `presentation/navigation/CheckingNavHost.kt` — `Routes.INSTRUCTIONS` → `InstructionsScreen`,
  `Routes.MANUAL` → `ManualScreen` (both reuse `ManualViewModel.languageFlow`), and `Routes.ABOUT` →
  `AboutScreen`.
- `presentation/check/CheckScreen.kt` — wires `onInstructionsClick`/`onManualClick`/`onAboutClick` to
  `onNavigateToInstructions`/`onNavigateToManual`/`onNavigateToAbout`.
- `presentation/instructions/InstructionsScreen.kt` — the text tutorial (8 steps; heading
  `instructions.heading`); fully translated in all 6 dicts.
- `presentation/manual/ManualScreen.kt` — the 14-section visual manual (`manual.*` keys); **pt/en only**
  (zh/ms/id/tl fall back to pt) + screenshot drawables.
- the 6 i18n dicts `i18n/dictionaries/{Pt,En,Zh,Ms,Id,Tl}.kt`.

**Decision (CONFIRMED by the product owner): keep the VISUAL manual.** Unify on **`ManualScreen`** (the
14-section visual manual with screenshots) as the single **"Instruções de Uso"** entry. The text
`InstructionsScreen` is **removed from the Settings menu**. **Critical consequence:** `manual.*` is
currently **pt/en only** (zh/ms/id/tl fall back to pt), so to satisfy "atender a todos os idiomas" the
manual block MUST be **fully translated into zh/ms/id/tl** as part of this prompt. Nothing the text tutorial
uniquely covered may be lost (see step 4). Leave `InstructionsScreen.kt` + the `instructions.*` keys
**unreferenced** (do NOT delete files unless explicitly asked).

**Do:**
1. **i18n label + heading — all 6 dicts:** the kept row routes to `ManualScreen`, so relabel **its** key
   `settings.manualLabel` → **"Instruções de Uso"** (pt) + translations (en "Usage Instructions";
   zh/ms/id/tl accordingly). Set the screen heading `manual.heading` → **"Instruções de Uso"** in all 6
   (and `document.manualTitle` if it is shown). The text-tutorial label `settings.instructionsLabel` is no
   longer used by the menu — remove it from all 6 dicts (no dangling reference) or leave it only if still
   referenced elsewhere (grep first).
2. **Translate the full `manual.*` block into zh/ms/id/tl (the headline deliverable).** Today only Pt/En
   define `manual.*`; add the **complete** block (highlights, all 14 `manual.sections.*` → title/lead/
   item1..3/figureCaption(s), the FAQ q/a, and any callouts) to **Zh, Ms, Id, Tl**, mirroring the recent
   `about`/`instructions` translation work (faithful, professional; keep the same keys/structure). Run
   `I18nTest`. Verify each language renders the manual natively (no pt fallback) for every key.
3. **`SettingsDialog.kt`:** delete the `School` / `settings.instructionsLabel` / `onInstructionsClick` row;
   keep ONE `groupHelp` row → "Instruções de Uso" (`MenuBook` icon, `settings.manualLabel`) → the manual.
   Remove the now-unused `onInstructionsClick` parameter and its `School` import.
4. **Do NOT lose the tutorial's unique topics.** The text tutorial uniquely walked through **Scheduled
   Pause** and **Accident mode** (and an offline note) — the manual's 14 sections cover overview/auth/
   registration/password/login/attendance/projects/location/automatic-activities/transport/password-change/
   settings/support/FAQ but **not** a dedicated Scheduled-Pause or Accident section. Add new `ManualSection`s
   for those (e.g. index "15"/"16", keys `manual.sections.scheduledPause.*` / `manual.sections.accident.*`),
   **in all 6 languages**, following the manual's pattern (title carries **no** number — see U2). Reuse the
   wording from the existing `instructions.step4` (Scheduled Pause) and `instructions.step7` (Accident).
   (Screenshots optional; the section may be text-only like the FAQ.)
5. **Wiring:** in `CheckScreen.kt` drop the `onInstructionsClick`/`onNavigateToInstructions` plumbing for
   this row; the single row routes to `Routes.MANUAL` → `ManualScreen`. In `CheckingNavHost.kt` remove the
   user-facing `Routes.INSTRUCTIONS` composable **only if** nothing else navigates to it (grep first).
6. **Guard "Sobre":** verify `onAboutClick` still routes to `AboutScreen` (`Routes.ABOUT`), unaffected.

**Do NOT:** touch `AboutScreen`/"Sobre"; delete `InstructionsScreen.kt` (just unreference); leave any
`manual.*` key untranslated in zh/ms/id/tl; leave a dangling `settings.instructionsLabel`/`onInstructionsClick`
reference; embed a number in any new section title (U2).
**Verify:** `compileDebugKotlin` + `compileDebugAndroidTestKotlin` + `testDebugUnitTest` + `I18nTest` green.
Settings shows exactly ONE "Instruções de Uso" entry → the visual manual; the label, heading, **and every
manual section** render natively in all 6 languages (no pt fallback); Scheduled-Pause + Accident sections
are present. Grep confirms no remaining `settings.instructionsLabel`/`onInstructionsClick` usage and no
orphaned navigation to the removed route.
**Update:** tick U1.

## Prompt U2 — Single numbering in the canonical screen ("1. 1. Título" → "1. Título")
**Goal:** each section shows its number exactly once, in all 6 languages.
**Root cause + effect of U1:** the doubled "1. 1." lived in the **text** `InstructionsScreen` —
`StepSection` rendered `index` ("1") **and** every i18n `instructions.stepN.title` already began with "N. "
(e.g. "1. Entrar no aplicativo", "1. 登录应用"). With U1 making the **visual `ManualScreen`** the canonical
screen (and removing the text tutorial from the menu), the bug is **no longer user-visible**:
`ManualScreen.ManualSection` renders `index` ("01".."14") with **unnumbered** titles — correct, single
numbering.
**Do:**
1. **Verify** `ManualScreen.ManualSection` shows the number exactly once (bold `index` + unnumbered title)
   for **every** section, including the **new** Scheduled-Pause/Accident sections added in U1 — their
   titles must NOT embed a number (use "Pausa Programada", not "15. Pausa Programada").
2. **Regression guard:** assert (smoke test / grep) that no `manual.sections.*.title` in any of the 6 dicts
   begins with a number-dot prefix (regex `^\s*\d+\.`), so a manual section can never reproduce "N. N.".
3. **Only if** the text tutorial is kept anywhere user-facing (contrary to U1's decision): apply the
   original fix — strip the leading "N. " from every `instructions.stepN.title` in all 6 dicts (and/or
   render the `StepSection` index as `"$index."`). Otherwise this is a no-op beyond steps 1–2.
**Do NOT:** add numbered prefixes to any manual section title; change section content/order.
**Verify:** `compileDebugKotlin` + `testDebugUnitTest` + `I18nTest` green; render/smoke check: every section
header reads "NN  Title" once, all 6 languages; the regex guard passes.
**Update:** tick U2.

---

## 5. Definition of done
Section 2 fully ticked (EP0–EP9, TP0–TP8, **U1–U2**); all suites green (Kotlin count ≥ baseline + new; backend only
the 33 pre-existing reds; Check Web JS green); the four contract pieces (§0.9) implemented identically
across backend/app/web/admin; **all protected behaviors (Section 4) intact**; admin2 mirrored to
`deploy/docker/admin2-web/`. Backend + Check Web deploy (root `main`) and the AAB publish require
**explicit human approval**; the `0079` migration must run in production before the feature is relied upon;
`CHECK_USER_APPROVAL_REQUIRED` is the documented rollback switch.
