# Checking Android — Settings/UX Overhaul: Cautious Implementation Plan (agent prompts)

> **Audience:** an AI coding agent that will execute the changes one prompt at a time.
> **Prime directive:** the app currently works **perfectly**. Every change here is cosmetic/UX
> reorganization. **No change may alter background behavior, the permission engine, the foreground
> service, or check-in/check-out logic.** If a step would touch behavior, stop and report instead.

This document is the single source of truth for the work. It is split into **7 phases**: a baseline
**Phase 0** (snapshot the app as it is now), five change phases (**1–5**), and a final integrity
**Phase 6** (prove nothing regressed). Each phase is split into **self-contained prompts**. Execute
prompts **strictly in order**. Do not start a prompt until the previous one is
committed-to-working-tree-clean and its **Verify** block passes. **Never start a change phase on a red
baseline** — if Phase 0 is not green, stop and report.

---

## 0. Global context (every prompt assumes you have read this section)

**Repository root:** `c:\dev\projetos\checkcheck`
**App module:** `checking_kotlin/` (Android, Kotlin, Jetpack Compose, Hilt, DataStore).
**Run all Gradle commands from `checking_kotlin/`.**

**Architecture you will touch:**
- Compose UI lives under `app/src/main/java/br/com/tscode/checking/presentation/`.
- The Check screen is `presentation/check/CheckScreen.kt`; its state holder is
  `presentation/check/CheckUiState.kt`; its ViewModel is `presentation/check/CheckViewModel.kt`.
- Settings dialog: `presentation/components/SettingsDialog.kt`.
- Auto-activities sub-dialog: `presentation/settings/autoactivities/AutoActivitiesDialog.kt`.
- Permissions sub-dialog: `presentation/settings/permissions/PermissionsDialog.kt`.
- Auth row (chave/senha fields + gear icon): `presentation/components/AuthRow.kt`.
- Reusable glow text field: `presentation/components/GlowField.kt` (defines `enum FieldGlow { None, Pending, Authenticated }`).
- Buttons: `presentation/components/PrimaryButton.kt` (defines **both** `PrimaryButton` and `SecondaryButton`).
- Modal scaffold (already scrolls): `presentation/components/DialogScaffold.kt`.
- Permission primitives (DO NOT MODIFY LOGIC): `platform/background/permissions/PermissionLadder.kt`
  and `platform/background/permissions/PermissionsInspector.kt`.
- Background engine (NEVER TOUCH): `platform/background/AutoActivityController.kt`,
  `AutoActivityForegroundService.kt`, `AutoActivityWatchdogWorker.kt`.

**i18n:** there are **6 dictionaries**, all under `app/src/main/java/br/com/tscode/checking/i18n/dictionaries/`:
`Pt.kt`, `En.kt`, `Zh.kt`, `Ms.kt`, `Id.kt`, `Tl.kt`. The `t()` function falls back to `pt`, but the
project keeps full translations and a unit test (`i18n/I18nTest.kt`) may assert **key parity** across
dictionaries. **Any key you add or rename must be applied to all 6 files.** Português is the source of
truth for wording; for other languages, translate faithfully (if unsure, ask; do not leave a Portuguese
string in a non-pt dictionary unless that is already the existing pattern).

**Permission status APIs you will reuse (read-only — do not change their logic):**
- `PermissionsInspector.inspect(context, oemAutoStartAcknowledged): PermissionsStatus` with fields
  `location: LocationStatus {PRECISE, IMPRECISE, DENIED}`, `cameraMicGranted`, `autoStartEnabled`,
  `batteryRestricted`, `backgroundGranted`, `notificationsGranted`.
- `PermissionLadder.checkStatus(context, oemGuidanceShown=false): PermissionLadderStatus` with
  `notificationsGranted`, `fineLocationGranted`, `backgroundLocationGranted`, `batteryOptExempt`,
  derived `minimumToStartGranted` (notifications + fine location) and `allRecommendedGranted`
  (those two + background "allow all the time" + battery exemption), and `nextStep`.
- Action launchers: `PermissionLadder.launchLocationSettings(context)`,
  `launchBatteryOptimizationRequest(context)`, `launchAppNotificationSettings(context)`,
  `launchOemAutostartSettings(context)`, `detectOemType()`, `canDeepLinkToOemAutostart(context)`.

**Relevant ViewModel methods (line numbers approximate — re-locate by name):**
`onLanguageSelected`, `onForegroundResume`, `onLocationPermissionStateChanged(fineGranted, backgroundGranted, context)`
(this is where `locationPermissionSufficient` is computed via `PermissionLadder.checkStatus(...).minimumToStartGranted`),
`onAutomaticActivitiesToggled(enabled, context)`, `onAutoActivitiesPermissionsGranted(context)`,
`onAutoActivitiesPermissionsDenied()`, `openSettings`, `openAutoActivitiesDialog`, `openPermissionsDialog`,
`openNotificationsDialog`, `openScheduledPauseDialog`, `dismissDialog`. The injected
`appPreferences: AppPreferencesDataSource` exposes generic `fun getFlag(name): Flow<Boolean>` and
`suspend fun setFlag(name, value)` (used for the Phase 5 nudge — **per-chave**, no schema migration).

**Tests:**
- Unit: `./gradlew testDebugUnitTest` (run from `checking_kotlin/`).
- Compile check (fast): `./gradlew compileDebugKotlin`.
- Instrumented smoke tests live under `app/src/androidTest/...`. **Do not** run
  `./gradlew connectedAndroidTest` (the `BootReceiver` crashes that task). If you must run an
  instrumented test, run it twice via `am instrument` (the first run may fail to register; the
  second passes) — only attempt this if a device/emulator is connected; otherwise note it as
  "manual verification pending" and rely on `compileDebugKotlin` + unit tests.

---

## 1. Golden rules (apply to EVERY prompt)

1. **Additive-first.** Prefer new optional parameters (with defaults), new enums, new composables.
   Never change the meaning of an existing parameter.
2. **Preserve every existing callback and `onClick` wiring.** Reorganizing layout must not drop or
   rename a behavior hook. If a hook must be removed (Phase 4 only), it is called out explicitly.
3. **Do not touch permission/engine LOGIC.** You may *call* `PermissionLadder`/`PermissionsInspector`
   and *route to* their launchers, but never edit their bodies, and never edit the FGS/controller/worker.
4. **No heavy work in composition.** Derive permission "health" in the ViewModel on the existing
   re-evaluation path, store it in `CheckUiState`. Never call `PermissionLadder.checkStatus` directly
   inside a `@Composable` body on every recomposition for new features.
5. **Touch all 6 dictionaries together** whenever keys change.
6. **One prompt = one compilable, behavior-preserving increment.** After each prompt the project must
   compile and all existing tests must pass.
7. **Do NOT run `git commit`, `git push`, or create branches** unless the human explicitly asks.
8. **Keep this file's progress tracker current** (Section 2) and log any deviation in Section 3 before
   you finish a prompt. This is how the next agent recovers full context.
9. If reality contradicts this plan (a file moved, a test asserts something unexpected, a signature
   differs), **stop, document it in Section 3, and report** rather than guessing.

---

## 2. Progress tracker (update after each prompt)

Mark `[x]` when the prompt's Verify block passes. Add the date and a one-line note.

- [x] **P0.1** Capture green baseline — 2026-06-17: **140 tests, all passed**; `compileDebugKotlin` clean (Section 4)
- [x] **P0.2** Inventory tests (10 unit + 3 instrumented) + `checking_kotlin` clean & protected-files diff EMPTY — 2026-06-17
- [x] **P1.1** Rename `resetPasswordLabel` → "Alterar Senha"/"Change Password"/etc. (6 dicts) + Pt/En manual refs — 2026-06-17: build green, 140 tests, no "Resetar Senha" left
- [x] **P1.2** Rename settings "Notificações"→"Avisos" / "Notifications"→"Alerts" (`notificationsLabel` + `notifications.title`, **Pt/En only** — see §3) — 2026-06-17: build green, 140 tests; `permissions.notificationsButton` kept
- [x] **P2.1** Add `AutoActivitiesHealth` enum + `CheckUiState.autoActivitiesHealth` (default Off) + pure `toGlow()` (in CheckUiState.kt) + `AutoActivitiesHealthTest` — 2026-06-17: 143 tests (was 140), all green
- [x] **P2.2** Derive `autoActivitiesHealth` in `CheckViewModel` (`computeHealth` + reuse `status` in `onLocationPermissionStateChanged`; 4 methods populate it) — 2026-06-17: build green, 143 tests; `locationPermissionSufficient`/FGS start-stop unchanged
- [x] **P2.3** Gear glow in `AuthRow` (`autoActivitiesGlow` param + CircleShape shadow) + wired from `CheckScreen` (`state.autoActivitiesHealth.toGlow()`) — 2026-06-17: build green, 143 tests; **visual check pending-for-device**
- [x] **P3.1** Restructure `SettingsDialog` into grouped rows (`SettingsRow`/`SettingsGroupHeader`) + 3 `settings.group*` keys (Pt/En) — 2026-06-17: compile + androidTest-compile OK, 143 tests; signature/callbacks/auth-gating unchanged; smoke run pending-for-device
- [x] **P3.2** Status chip on Auto-activities row (`autoActivitiesHealth` param + `StatusChip`) + `settings.status*` keys (Pt/En) — 2026-06-17: compile + androidTest OK, 143 tests; smoke test needed NO edit (trailing default + named args)
- [x] **P4.1** Live permission checklist in `AutoActivitiesDialog` (`ChecklistRow` + status-only ON_RESUME refresh; reuses `PermissionsInspector`/`PermissionLadder`) + 4 row-label keys (Pt/En) — 2026-06-17: compile + androidTest OK, 143 tests; ladder/notices untouched; device verification pending
- [x] **P4.2** Remove "Permissões" entry from the Settings menu (PermissionsDialog kept as dead safety net) — 2026-06-17: compile + androidTest-compile OK, 143 tests; `onPermissionsClick` gone everywhere; `openPermissionsDialog`/`CheckDialog.Permissions ->`/`PermissionsDialog` import intact (dead). **P4.3 BLOCKED — see §3.**
- [x] **P4.3** Delete the now-unused PermissionsDialog plumbing — 2026-06-17: gate satisfied (human device sign-off logged in §3); `PermissionsDialog.kt` deleted, `CheckDialog.Permissions` + `openPermissionsDialog()` + routing/import removed; dead i18n key `settings.permissionsLabel` removed (Pt/En); `PermissionsInspector`/`PermissionLadder` untouched. compile + androidTest-compile OK, 143 tests; grep clean
- [x] **P5.1** Nudge state plumbing (per-chave flag, VM predicate + dismiss) + unit test — 2026-06-17: `CheckUiState.showAutoActivitiesNudge` + pure `shouldShowAutoActivitiesNudge(...)`; VM computes it in `onAuthenticationSucceeded`, clears on enable/granted/logout/dialog-open; `dismissAutoActivitiesNudge()` + per-chave flag; new `AutoActivitiesNudgeTest` (5). compile + 148 tests green (was 143)
- [x] **P5.2** Render first-login nudge card in `CheckScreen` — 2026-06-17: new `AutoActivitiesNudgeCard` (TintedPanel + "Ativar agora"/"Agora não") rendered inside the authenticated block before `RegistrationFieldset`, guarded by `if (state.showAutoActivitiesNudge)` (zero height when absent); 3 `autoActivities.nudge*` keys (Pt/En, others fall back to pt); new instrumented `AutoActivitiesNudgeCardSmokeTest` (3, compile-verified). compile + androidTest-compile OK, 148 tests; on-device run pending
- [x] **P6.1** Full regression run + protected-files zero-diff check vs. Section 4 baseline — 2026-06-17: 148 tests green (≥140 baseline), `compileDebugKotlin` clean, `I18nTest` 16/16; protected diff = **only** the authorized `AutoActivityForegroundService.kt` (+6/−5), all other Section 5 paths empty. See §4 result.
- [~] **P6.2** Manual device regression — 2026-06-17: **emulator UX pass DONE** (integrated build installs+launches; items 3-UI/4/5 PASS in en+pt, item 1 green confirmed). **PENDING human/real-device:** item 2 (prod-writing check-in/out), item 6 (needs auto-OFF chave), item 7 (accident/transport/pause/offline/Avisos prefs), and background/geofence of item 3. See §3 P6.2. **Not fully ticked — awaits human device sign-off.**

---

## 3. Deviations log (append-only)

> Record anything that differed from the plan: unexpected signatures, extra files touched, tests that
> needed editing, decisions taken. Format: `Pxx — YYYY-MM-DD — <what & why>`.

- P1.1 — 2026-06-17 — Besides the `settings.resetPasswordLabel` key, the in-app **manual** referenced the
  button by its old name. Updated `manual.passwordChange.item1` + `.figureCaption` in **Pt** ("Resetar
  Senha"→"Alterar Senha") and **En** ("Reset Password"→"Change Password") so the help text matches the
  renamed button (within Change #2 scope; needed to pass the "no remaining Resetar Senha" Verify). Left the
  section heading `manual.passwordChange.title` ("Resetar ou trocar senha" / "Reset or change password")
  unchanged — it is a topic heading, not a button reference. Ms/Zh/Id/Tl had **no** old-label manual
  references (no change). Each dict's `resetPasswordLabel` was set equal to its own
  `passwordDialog.titleChange` for consistency (the button opens that dialog). No test asserted the old text.
- P1.2 — 2026-06-17 — Plan assumed all 6 dicts have `settings.notificationsLabel`, the `notifications`
  block, and `permissions.notificationsButton`. Reality: only **Pt** and **En** define them; **Ms/Zh/Id/Tl
  are partial dictionaries** that omit these sections and fall back to pt (existing pattern; `I18nTest`
  does NOT enforce full key parity). So `settings.notificationsLabel` + `notifications.title` were changed
  to "Avisos"/"Alerts" in **Pt and En only**; Ms/Zh/Id/Tl inherit the new pt value via fallback (just as
  they already inherited "Notificações"). `permissions.notificationsButton` left "Notificações"/"Notifications"
  (the OS-permission label). No test asserted these strings. (Same partial-dict reality will apply to later
  phases that add `settings.*` keys — e.g. P3.1 section headers, P3.2 status chip: add them to Pt/En;
  Ms/Zh/Id/Tl will fall back to pt.)
- P2.3 — 2026-06-17 — Gear glow wired (green = Healthy / orange = Degraded / none = Off). No device/emulator
  available → **manual visual check pending-for-device**: logged out → no glow; auto on + healthy → green;
  a recommended permission revoked → orange. The chave/senha field glow, the gear `onSettingsClick`, and the
  row height are unchanged (gear shadow uses `clip = false`, so layout size is unaffected). No protected
  file touched (only `presentation/components/AuthRow.kt` + `presentation/check/CheckScreen.kt`).
- P3.1 — 2026-06-17 — Rewrote the `SettingsDialog` body into grouped rows under 3 section headers
  (Atividades Automáticas / Preferências / Ajuda) via new private `SettingsRow` + `SettingsGroupHeader`.
  Signature, callbacks, auth-gating and the visible `t()` keys are unchanged, so `SettingsDialogSmokeTest`
  needed **NO edit** (verified it still compiles via `compileDebugAndroidTestKotlin`; every asserted text
  is still rendered). New `settings.group{AutoActivities,Preferences,Help}` keys added to **Pt + En only**
  (Ms/Zh/Id/Tl fall back to pt — same partial-dict pattern as P1.2). Icons from `material-icons-extended`
  (already a dependency). Bare dividers replaced by headers (dropped now-unused `HorizontalDivider` /
  `CheckingDivider` imports). Instrumented smoke run is **pending-for-device**.
- P3.2 — 2026-06-17 — Added a trailing `StatusChip` to the Auto-activities row (Ativadas/green,
  Atenção/orange, Desativadas/muted), driven by a new **trailing-defaulted** `SettingsDialog` param
  `autoActivitiesHealth = AutoActivitiesHealth.Off` (passed from `CheckScreen`). **The prompt's "required"
  smoke-test edit was NOT needed**: the param is trailing-with-default and every call site uses named
  args, so `SettingsDialogSmokeTest` still compiles unchanged (verified via
  `compileDebugAndroidTestKotlin`). New `settings.status{On,Attention,Off}` keys added to **Pt + En only**
  (Ms/Zh/Id/Tl fall back to pt). `SettingsDialog` now imports `AutoActivitiesHealth` from
  `presentation.check` (components→check) — compiles fine; row visibility unchanged (chip only changes
  text/tone). Instrumented run **pending-for-device**.
- P4.1 — 2026-06-17 — Added a live, tappable permission checklist (Notificações / Localização "o tempo
  todo" / Bateria / Iniciar com o aparelho) below the enable checkbox in `AutoActivitiesDialog`, sourced
  from `PermissionsInspector.inspect(...)` and refreshed by a **status-only** ON_RESUME observer
  (`refreshKey`) that never touches the ladder's `stepIndex`/`isWaitingForResume` (does not fight the step
  machine). Each row's "fix" launches the matching `PermissionLadder` screen (read-only calls; primitives
  unchanged). Reused the existing `permissions.*` status-value keys for the status text; added only the 4
  row-label keys (`autoActivities.perm*`) to **Pt + En** (Ms/Zh/Id/Tl fall back to pt). Kept the existing
  notices + "Revisar Permissões" ladder button intact (dialog is a strict superset). NOTE: the En
  `autoActivities` block already diverges from Pt (lacks `explanation`/`reviewPermissions`/
  `permissionsNotice`/`close`; older `permStep` shape) — a **pre-existing** translation gap (falls back to
  pt), not introduced here. Instrumented/device verification **pending-for-device**.
- EMULATOR VALIDATION — 2026-06-17 (`Pixel_8_API_35`, Android 15, debug build `com.br.checking.debug`,
  chave HR70 session) — visually verified via screenshots: **P1.1** "Change Password", **P1.2** "Alerts",
  **P2.3** green gear glow (auto on + healthy), **P3.1** grouped Settings (AUTOMATIC ACTIVITIES /
  PREFERENCES / HELP, icons + chevrons), **P3.2** green "Active" chip on the Auto-activities row, **P4.1**
  live permission checklist (Notifications=allowed / Location 'all the time'=precise allowed / Battery
  unrestricted=not restricted, all green; OEM "Start with device" row correctly HIDDEN on GENERIC; tapping
  the Notifications row opened the system App-notification settings; Back → ON_RESUME refreshed the
  checklist with no crash). **NOT exercised on the emulator:** the denied→granted color transition (all
  perms were already granted), the OEM-autostart row (emulator is GENERIC), and geofence/FGS background
  (not emulator-reliable). This is strong evidence but is an automated emulator smoke, not the formal
  human device sign-off that the **P4.3** gate requires.
- EMULATOR VALIDATION (cont.) — 2026-06-17 — **denied→granted transition now VERIFIED** on
  `Pixel_8_API_35`: `adb shell pm revoke ... POST_NOTIFICATIONS` → the Notifications checklist row turned
  **red "not allowed"** and the blocking "minimum permissions not granted" notice appeared; then
  `adb shell pm grant ... POST_NOTIFICATIONS` + ON_RESUME (HOME→resume) → the row returned to **green
  "allowed"** and the notice cleared — **without** restarting or re-navigating. Confirms the checklist
  reads live permission state and refreshes both ways via the ON_RESUME observer, and that the existing
  `insufficientPermissions` notice integrates correctly. Residual not-exercised on emulator: the
  OEM-autostart row (GENERIC emulator hides it correctly — needs a restrictive-OEM device) and
  geofence/FGS background.
- P4.2 — 2026-06-17 — Removed the standalone **Permissões** menu row + the `onPermissionsClick`
  parameter from `SettingsDialog`, and the `onPermissionsClick = { … }` argument from the
  `SettingsDialog(...)` call in `CheckScreen.kt`. The now-unused `Icons.Outlined.Security` import was
  dropped from `SettingsDialog.kt` (only that row used it). As required, edited
  `SettingsDialogSmokeTest.kt`: removed `onPermissionsClick = {},` from all **7** constructor calls
  (the only expected test edit). **Safety net kept exactly as instructed (dead but compiling):**
  `PermissionsDialog.kt`, the `CheckDialog.Permissions` enum value, `CheckViewModel.openPermissionsDialog()`,
  and the `CheckDialog.Permissions -> PermissionsDialog(...)` routing + `PermissionsDialog` import in
  `CheckScreen.kt` are all untouched. The i18n key `settings.permissionsLabel` ("Permissões"/"Permissions",
  Pt/En) was **left in place** — now unreferenced by the menu but still used by `PermissionsDialog`'s own
  flow; removing it is deferred to P4.3 cleanup. Verify: `compileDebugKotlin` + `compileDebugAndroidTestKotlin`
  + `testDebugUnitTest` green (143 tests, 0 failures); grep confirms zero remaining `onPermissionsClick`
  references and that the safety-net symbols still resolve. (Pre-existing `Icons.Outlined.Chat` deprecation
  warning is from P3.1, not introduced here.)
  **P4.3 is BLOCKED until a human confirms on a real device that the Auto-activities checklist grants
  every permission correctly** — in particular the OEM-autostart row, which the GENERIC emulator hides
  and therefore could not be exercised in the EMULATOR VALIDATION runs above.
- **device-verified: checklist grants all perms** — 2026-06-17 — Human sign-off (user `tamer79@gmail.com`):
  inspected the app and confirmed the fused Auto-activities checklist grants every permission correctly;
  explicitly authorized proceeding to P4.3 ("inspecionei o app e podemos prosseguir para o P4.3 sem
  problemas"). This satisfies the P4.3 precondition gate.
- P4.3 — 2026-06-17 — Gate satisfied (sign-off above). Deleted
  `presentation/settings/permissions/PermissionsDialog.kt` (the dir is now empty). Removed the
  `Permissions` value from the `CheckDialog` enum in `CheckUiState.kt`, removed
  `CheckViewModel.openPermissionsDialog()`, and removed the `CheckDialog.Permissions -> PermissionsDialog(...)`
  routing branch + the `PermissionsDialog` import in `CheckScreen.kt`. **Extra cleanup (was deferred from
  P4.2):** removed the now-orphaned i18n key `settings.permissionsLabel` from **Pt + En** (its only
  consumer was the menu row deleted in P4.2; the still-used `permissions.*` status block — read by the
  P4.1 checklist — was left fully intact). Fixed two stale comments that referenced the deleted file
  (`SettingsDialog.kt` header note; `AutoActivitiesDialog.kt` tone-palette note). **Did NOT touch**
  `PermissionsInspector`/`PermissionLadder` (the checklist depends on them — both still present).
  **No test referenced any of the removed symbols** (so change #5 was a no-op:
  `SettingsDialogSmokeTest` was already adjusted in P4.2; grep over `app/src` found zero test refs to
  `PermissionsDialog`/`CheckDialog.Permissions`/`openPermissionsDialog`). Verify: `compileDebugKotlin` +
  `compileDebugAndroidTestKotlin` + `testDebugUnitTest` green (143 tests, 0 failures); grep confirms the
  only remaining `PermissionsDialog` mentions are the two corrected comments; `git status` shows the file
  as deleted. (Pre-existing `Icons.Outlined.Chat` deprecation warning unrelated.) **Phase 4 complete.**
- P5.1 — 2026-06-17 — Added the first-login nudge **state plumbing only** (no UI yet — that is P5.2).
  • `CheckUiState.showAutoActivitiesNudge: Boolean = false` (additive, default false). • Pure predicate
  `shouldShowAutoActivitiesNudge(authenticated, autoEnabled, dismissed)` added as a **top-level function in
  `CheckUiState.kt`**, mirroring the existing `AutoActivitiesHealth.toGlow()` pattern so it is unit-testable
  without instantiating the (Android-context-dependent) ViewModel. • Reused the **single existing
  auth-success path** `onAuthenticationSucceeded(chave, status)` (covers both live login and init→session
  restore — no new lifecycle source): a new `viewModelScope.launch` reads `appPreferences.getFlag(nudgeFlag(chave)).first()`
  and applies the predicate with `authenticated = status.authenticated`. • Flag helper
  `private fun nudgeFlag(chave) = "auto_activities_prompt_dismissed_$chave"` (generic flag API → DataStore key
  `pref_flag_auto_activities_prompt_dismissed_<chave>`; **no `UserSettings`/`PersistedSettings` change**).
  • `dismissAutoActivitiesNudge()` (the future "Agora não") persists the flag + sets the field false.
  • The nudge is also cleared (set false) when auto becomes enabled — in `onAutomaticActivitiesToggled(enabled=true)`
  and `onAutoActivitiesPermissionsGranted` — on logout (`handleAuthExpiry`), and on `openAutoActivitiesDialog()`
  (which is what the future "Ativar agora" will call, so opening hides the transient card; harmless when opened
  from Settings since the card isn't visible there anyway). No existing behavior/callback changed; FGS/engine
  paths untouched. New test `presentation/check/AutoActivitiesNudgeTest` (5 cases) green. Verify:
  `compileDebugKotlin` + `testDebugUnitTest` → 148 tests (was 143), 0 failures. **P5.2 will render the card
  and wire its two buttons to `openAutoActivitiesDialog()` / `dismissAutoActivitiesNudge()`.**
- P5.2 — 2026-06-17 — Created `presentation/components/AutoActivitiesNudgeCard.kt`: a dismissible card
  built on the existing `TintedPanel` (so it matches the History/Notification/Location cards — slate tint
  + subtle teal border + rounded corners), with the explanatory line `autoActivities.nudgeQuestion`, a
  primary `PrimaryButton` "Ativar agora" (`onActivate`) and a low-emphasis `TextButton` "Agora não"
  (`onDismiss`), laid out 50/50 in a Row. Wired into `CheckScreen.kt` **inside the authenticated block**
  (`if (state.isAuthenticated)`), immediately **before `RegistrationFieldset`**, itself guarded by
  `if (state.showAutoActivitiesNudge)`. **Zero height when absent**: the surrounding Column uses
  `Arrangement.spacedBy(...)`, which only inserts spacing between children that are actually emitted, so
  a hidden nudge contributes nothing (no empty slot, no gap). `onActivate = { vm.openAutoActivitiesDialog() }`
  (P5.1 already makes that call clear `showAutoActivitiesNudge`); `onDismiss = vm::dismissAutoActivitiesNudge`.
  i18n: added `autoActivities.nudgeQuestion` / `nudgeActivate` ("Ativar agora"/"Activate now") /
  `nudgeLater` ("Agora não"/"Not now") to **Pt + En only** — the `autoActivities` block exists only in those
  two dicts; Zh/Ms/Id/Tl fall back to pt via `t()` (same partial-dict reality as P1.2/P3.x/P4.1; `I18nTest`
  asserts fallback + resolution, NOT full key parity, so it stays green). Added instrumented
  `ui/AutoActivitiesNudgeCardSmokeTest` (3 cases: renders question + both actions; each button fires its
  callback) — **compile-verified** via `compileDebugAndroidTestKotlin`; on-device run **pending-for-device**
  (connectedAndroidTest crashes on `BootReceiver`; the running emulator's session has auto-activities ON, so
  the card isn't shown for it — a fresh chave with auto OFF is needed to see it live). Verify:
  `compileDebugKotlin` + `compileDebugAndroidTestKotlin` + `testDebugUnitTest` green (148 tests, 0 failures).
  **Phase 5 complete.**
- I18N AUDIT (pre-Phase-6, user-requested) — 2026-06-17 — User reported seeing some English messages on the
  emulator while auto-activities permissions were incomplete, and asked to ensure all user notifications
  follow the multi-language pattern. **Findings:** (1) All notification STRINGS are fully i18n'd via
  `t(key, lang=…)` and complete in **pt+en** (`AutoActivityNotifications`, `AutoActivitiesDialog`, channel
  names via `R.string`); no hardcoded English in the user notification/permission flow (the only hardcoded
  English is in the dev-only `EvaluationLogDialog`). (2) **Root cause = language-source divergence:** the
  foreground UI resolves language via `resolveInitialLanguageCode` (stored → **device locale** → pt), but the
  background (FGS + orchestrator) read `appPrefs.language.first().ifEmpty { DEFAULT_LANGUAGE }` (stored → **pt**,
  no device fallback). So when the user hasn't explicitly picked a language, the UI follows the device while
  notifications fall back to pt → the two can render in different languages. (3) Secondary translation gaps:
  the En `autoActivities` block omits `explanation`/`reviewPermissions`/`permissionsNotice`/`close`/
  `permStep.oemGuidance*` (English users get pt fallback there), and Zh/Ms/Id/Tl have no
  `autoActivities`/`permissions`/`scheduledPause`/`notification` blocks (fall back to pt).
  **User decisions (AskUserQuestion):** (a) fix the divergence by **unifying in the background**; (b) for the
  translation gaps, **only document for now** (no En completion / no Zh-Ms-Id-Tl translation this pass).
- PROTECTED-FILE SIGN-OFF — 2026-06-17 — **device-verified human authorization to edit a Section 5 protected
  file**: the user explicitly chose "Unificar no background", which requires editing
  `platform/background/AutoActivityForegroundService.kt` (protected). Authorized. **Consequence for P6.1:** the
  protected-files zero-diff check will legitimately show a non-empty diff for THIS ONE file
  (`AutoActivityForegroundService.kt`) — that is expected and authorized here, not a regression. All other
  Section 5 files must still be diff-empty.
- I18N FIX — 2026-06-17 — Added a pure resolver `resolveEffectiveLanguageCode(storedCode): String`
  (stored → device → pt) to `i18n/I18n.kt` — mirrors `resolveInitialLanguageCode`'s precedence but does **not**
  mutate the global `activeLanguageCode`, so it is safe off the UI thread. Switched the background language
  source to it in **`BackgroundCheckOrchestrator.kt`** (3 sites: `runOnce` re-login, `runAccidentCheck`,
  `runOnceLocked`; not protected) and in **`AutoActivityForegroundService.kt`** (protected, authorized: the
  immediate `startForeground` guess + the async refine). Now background notifications follow the same language
  the UI resolves (stored choice, else device locale, else pt) instead of always defaulting to pt. No string
  added/changed; no behavior beyond language selection. DEFAULT_LANGUAGE import dropped from both files (now
  unused). Verify: `compileDebugKotlin` + `testDebugUnitTest` green (148 tests, 0 failures); grep confirms no
  remaining `DEFAULT_LANGUAGE` in `platform/background`. **Translation gaps (En block, Zh/Ms/Id/Tl) left as
  documented-only per the user's decision** — not fixed this pass.
- P6.1 — 2026-06-17 — Final automated regression + protected-files check. `testDebugUnitTest` = **148 tests,
  0 failures/errors/skipped** (baseline 140; +8 across 2 additive suites — `AutoActivitiesHealthTest`,
  `AutoActivitiesNudgeTest`). `compileDebugKotlin` clean. `I18nTest` 16/16 green. **Step 4 nuance:** the
  prompt says the protected-files diff MUST be empty, else STOP. It is **not** empty — but the ONLY file that
  appears is `platform/background/AutoActivityForegroundService.kt` (+6/−5), which is the **pre-authorized**
  exception logged under "PROTECTED-FILE SIGN-OFF" / "I18N FIX" above (user chose "Unificar no background").
  So this is the documented, expected outcome — not an integrity breach. I verified **every other** Section 5
  path (controller, watchdog, geofence/boot/accident receivers, `offline/`, `permissions/PermissionLadder` +
  `PermissionsInspector`, `domain/checkrules/`, `domain/clientstate/ClientStateFunctions`+`PersistedSettings`,
  `data/api`+`dto`+`repository`) is **diff-empty** vs `a0d45cc`. No assertion deleted/weakened to force green.
  Section 4 updated with the final comparison. **P6.1 complete; only P6.2 (manual device regression) remains.**
- P6.2 — 2026-06-17 — **Emulator UX pass** on `Pixel_8_API_35` (Android 15) with the **final integrated debug
  build** (`installDebug` → built/packaged/installed/launched cleanly — itself a strong integrity signal),
  session chave **HR70** (auto-activities ON, all perms granted). The emulator's device locale is **en-US**, so
  the app launched in **English** — incidentally re-confirming the I18N AUDIT diagnosis (UI follows device
  locale). Per-item results:
  • **(1) Auth** — PARTIAL/PASS: authenticated **green** state confirmed (green Key border, "Authentication
    completed"). Found-orange glow + wrong-password handling + logout-reset were confirmed in prior sessions;
    not re-driven here → treat as **pending re-drive** for a formal sign-off.
  • **(2) Manual check-in/check-out** — **PENDING (human)**: deliberately NOT exercised — it writes real
    events to the production backend (outward-facing/destructive); must be signed off by the human on a device.
  • **(3) Auto-activities** — UI **PASS** / background **PENDING (real device)**: the fused live checklist
    renders intact **after the P4.3 deletion** — "Notificações: permitidas", "Localização 'o tempo todo':
    permitida precisa", "Bateria sem restrição: não restrito" (all green), "Revisar Permissões" present, OEM
    row correctly hidden on GENERIC. FGS-start notification / revoke-recommended→orange / **geofence trigger**
    = real-device (the denied→granted color transition was already validated in the earlier P4.1 EMULATOR
    VALIDATION).
  • **(4) Gear glow** — **PASS**: green/Healthy, and tapping it opened Settings (never blocks the tap).
  • **(5) Settings dialog** — **PASS** (verified in BOTH en + pt): grouped under 3 headers
    (AUTOMATIC ACTIVITIES/PREFERENCES/HELP ↔ ATIVIDADES AUTOMÁTICAS/PREFERÊNCIAS/AJUDA), green
    **Active/Ativadas** chip, **"Alerts"/"Avisos"** (P1.2) + **"Change Password"/"Alterar Senha"** (P1.1),
    **NO "Permissions"/"Permissões" entry** (P4.2/P4.3), all 6 languages in the dropdown, and the **language
    switch works** (en→pt applied live). (Side effect: the app's persisted language is now **pt**.)
  • **(6) First-login nudge** — **PENDING (needs auto-OFF chave)**: correctly **not shown** for HR70 (auto ON
    ⇒ suppressed, as designed). Live "appears once / Agora não persists / Ativar agora opens dialog" needs a
    fresh login on a chave with auto-activities OFF; logic is covered by `AutoActivitiesNudgeTest` (unit) +
    `AutoActivitiesNudgeCardSmokeTest` (instrumented, compile-verified).
  • **(7) Untouched subsystems** (Accident, Transport, Scheduled Pause, offline replay, "Avisos" push prefs)
    — **PENDING (human)**: not exercised this pass (out of this plan's change scope; the "Avisos" label itself
    is confirmed via item 5).
  **Conclusion:** every UX surface THIS plan changed (items 3-UI, 4, 5; item 1 green state) is verified on the
  emulator and matches intent. Items **2, 6, 7** and the **background/geofence** parts of item 3 are
  **pending-for-device / human sign-off** (destructive prod writes, real-device-only behavior, or
  specific-account state). Therefore **P6.2 is NOT fully ticked** — marked partial pending the human device pass.

---

## 4. Baseline log (filled by Phase 0, then read-only)

> The reference snapshot of "the app as it is now". Phase 6 compares against this. Do not edit after
> Phase 0 except to append the Phase 6 comparison result.

- Unit suite (`testDebugUnitTest`): **140 tests — 0 failures / 0 errors / 0 skipped → ALL PASSED**
  (across 10 test classes). `compileDebugKotlin` → BUILD SUCCESSFUL (clean). Captured **2026-06-17**.
  (Gradle reported `testDebugUnitTest` UP-TO-DATE — i.e. the current sources' last run was green, since a
  failed test task is never UP-TO-DATE; counts read from `app/build/test-results/testDebugUnitTest/*.xml`.)
- Unit test classes inventory (10, under `app/src/test/`): `data/local/AppPreferencesDataSourceTest`,
  `domain/checkrules/AutoActivitiesTest`, `domain/checkrules/ScheduledPauseTest`,
  `checkrules/AutoActivitiesSituationTest`, `domain/clientstate/ClientStateFunctionsTest`,
  `domain/usecase/RunAutomaticActivitiesOfflineTest`, `i18n/I18nTest`,
  `platform/background/AccidentNotificationDecisionTest`,
  `platform/background/offline/OfflineCheckQueueTest`, `platform/background/offline/PendingCheckReplayerTest`
  (= the 10 suites / 140 tests from P0.1).
- Instrumented test classes inventory (under `app/src/androidTest/`): `ui/SettingsDialogSmokeTest`,
  `ui/EvaluationLogDialogSmokeTest`, `notifications/NotificationMechanismTest` (+ `HiltTestRunner` — the
  runner, not a test). Not executed here (no device; see §0 "Tests").
- `git status` at baseline (2026-06-17): `checking_kotlin` repo **clean** — `## main...origin/main`,
  empty `--porcelain`, no tracked diff (baseline commit `a0d45cc`). App build outputs are gitignored.
- Protected-files diff at baseline: **EMPTY** — `git diff` over every Section 5 path returned nothing;
  protected files are pristine.
- Phase 6 comparison result (P6.1 — 2026-06-17): **final unit suite = 148 tests, 0 failures / 0 errors /
  0 skipped → ALL PASSED** (baseline 140; +8 from **2 new suites**: `AutoActivitiesHealthTest` [P2.1] +
  `AutoActivitiesNudgeTest` [P5.1] → 12 suites total). `compileDebugKotlin` clean. `I18nTest` green (16/16 —
  resolution + pt fallback; note: it does NOT assert full 6-dict key parity, by existing design — the
  documented partial-dict gaps remain per the user's "document-only" decision). **Protected-files diff vs
  baseline `a0d45cc`: exactly ONE file changed — `platform/background/AutoActivityForegroundService.kt`
  (+6/−5, the AUTHORIZED i18n language-source unification, see §3 PROTECTED-FILE SIGN-OFF); every OTHER
  Section 5 path is diff-EMPTY.** No assertion was deleted or weakened to force green (the only test edits
  were the additive new suites + the P4.2 `onPermissionsClick` signature removal).
- P6.2 device pass (2026-06-17): final integrated debug build **installs + launches** on `Pixel_8_API_35`;
  UX surfaces changed by this plan verified on-emulator (Settings grouping/labels/no-Permissões in en+pt,
  gear glow Healthy, fused permission checklist intact post-P4.3, authenticated green state). Items 2/6/7 +
  background/geofence of item 3 are **pending human/real-device sign-off** (see §3 P6.2). P6.2 left **partial**.

## 5. Protected files — MUST show zero git diff through the ENTIRE work

These hold behavior that must not change. At Phase 0 they are the baseline; at Phase 6 `git diff` on
them MUST be empty. If a change ever seems unavoidable, STOP and get explicit human sign-off in
Section 3 before proceeding — never silently edit one.

- `platform/background/AutoActivityController.kt`
- `platform/background/AutoActivityForegroundService.kt` ⚠ **AUTHORIZED EXCEPTION (2026-06-17, see §3 I18N FIX):** the user signed off on editing this file to unify the background notification language with the UI. Its P6.1 diff is expected to be non-empty (language-source change only; no string/behavior change). Every OTHER file below must still be diff-empty.
- `platform/background/AutoActivityWatchdogWorker.kt`
- `platform/background/GeofenceBroadcastReceiver.kt`
- `platform/background/BootReceiver.kt`
- `platform/background/AccidentWatchWorker.kt`
- `platform/background/offline/` (offline check queue + sync worker)
- `platform/background/permissions/PermissionLadder.kt`
- `platform/background/permissions/PermissionsInspector.kt` (reused read-only; no edits)
- `domain/checkrules/` (AutoActivities, ScheduledPause — decision logic)
- `domain/clientstate/ClientStateFunctions.kt` and `PersistedSettings.kt` (serialization contract)
- `data/api/`, `data/dto/`, `data/repository/` (network + serialization contract)

> Note: `CheckViewModel.kt`, `CheckUiState.kt`, and `presentation/**` ARE expected to change (that is
> where the UX work lives) — they are deliberately NOT in this list.

---

# PHASE 0 — Baseline capture (run BEFORE touching any code)

> Goal: snapshot "the app as it is now" so Phase 6 can prove integrity was preserved. This phase writes
> NO production code — it only runs the existing suite and records facts into Section 4.

## Prompt P0.1 — Capture the green baseline

**Goal:** prove the suite is green right now and record the numbers as the reference.

**Risk:** none (run/measure only).

**Context to load before editing:** Read Sections 0, 1, 4, 5 of this file.

**Steps:**
1. From `checking_kotlin/`, run `./gradlew testDebugUnitTest`. It MUST be fully green. If it is NOT
   green on a clean checkout, STOP — do not start any change phase on a red baseline; report to the human.
2. Run `./gradlew compileDebugKotlin` and confirm it is clean.
3. Record in Section 4: the total number of tests executed + "all passed", and the date.

**Do NOT:** change any source file. This is measurement only.

**Verify:** Section 4 now holds the baseline unit-suite result and a clean compile.

**Update progress & memory:** tick P0.1; log anything unexpected in Section 3.

## Prompt P0.2 — Inventory tests + confirm a pristine working tree

**Goal:** record the full test surface and prove the protected files start untouched.

**Risk:** none.

**Context to load before editing:** Read Sections 0, 1, 4, 5.

**Steps:**
1. List every test class under `app/src/test/` (unit) and `app/src/androidTest/` (instrumented), and
   write both lists into Section 4. This is the coverage surface that must stay green.
2. Run `git status` and record it in Section 4. The tree must be clean except pre-existing untracked
   docs (e.g. this plan). If there are unexpected local edits, STOP and report.
3. Confirm `git diff` shows no changes to any path in Section 5, and record "protected-files diff:
   empty" in Section 4.

**Do NOT:** change any source file.

**Verify:** Section 4 contains the test inventory, baseline `git status`, and "protected-files diff: empty".

**Update progress & memory:** tick P0.2; log deviations.

---

# PHASE 1 — Label changes (risk: ~zero, text only)

## Prompt P1.1 — Rename "Resetar Senha" → "Alterar Senha"

**Goal:** change the Settings button label key `settings.resetPasswordLabel` from "Resetar Senha" to
"Alterar Senha". It is more correct: the button only appears for authenticated users who already have a
password, and the dialog it opens already titles itself `passwordDialog.titleChange` = "Alterar Senha".

**Risk:** none (string only). No code logic changes.

**Context to load before editing:**
- Read Section 0 + Section 1 of this file.
- Open all 6 dictionaries in `i18n/dictionaries/`.
- Grep the whole `checking_kotlin/` tree for `resetPasswordLabel` and for the literal `Resetar Senha`
  to find any test or comment that asserts the old wording.

**Changes:**
1. In each of the 6 dictionaries, find the `settings` block, key `resetPasswordLabel`, and change the
   **Portuguese source** value to `"Alterar Senha"`. For the other 5 languages, set the natural
   translation of "Change Password" (en: `"Change Password"`; others: translate faithfully, matching
   the tone already used in that dictionary's `passwordDialog.titleChange`).
2. Update any test/string that asserts the old "Resetar Senha" text.

**Do NOT:** rename the key itself; touch any other key; change `passwordDialog.*`.

**Verify:**
- `./gradlew compileDebugKotlin` succeeds.
- `./gradlew testDebugUnitTest` passes (especially `i18n/I18nTest`).
- Grep confirms no remaining `Resetar Senha` literal except in this plan/changelog docs.

**Update progress & memory:** tick P1.1 in Section 2 with date + note; log deviations in Section 3.

---

## Prompt P1.2 — Rename Settings "Notificações" → "Avisos"

**Goal:** the word "Notificações" is overloaded (it names the Settings menu entry for *push
preferences*, AND the Android *permission*). Rename the **Settings preference** to "Avisos" so it stops
colliding with the OS permission. Keep the OS permission label as "Notificações".

**Risk:** none (string only).

**Context to load before editing:**
- Read Section 0 + Section 1.
- In the 6 dictionaries, locate: `settings.notificationsLabel` (the menu entry, currently
  "Notificações"), `notifications.title` (the dialog title, currently "Notificações"), and
  `permissions.notificationsButton` (the OS permission — currently "Notificações", **must stay**).
- Grep for `notificationsLabel` and `notifications.title` usages in tests.

**Changes:**
1. In all 6 dictionaries, change `settings.notificationsLabel` and `notifications.title` to "Avisos"
   (en: `"Alerts"`; translate the others faithfully). **Leave `permissions.notificationsButton`
   unchanged.** Leave the body/checkbox strings inside the `notifications` block unchanged.
2. Update any test asserting the old title/label.

**Do NOT:** touch `permissions.*`, the 3 push-preference checkbox strings, or the `NotificationsDialog`
behavior. Do not rename keys.

**Verify:** same as P1.1 (`compileDebugKotlin`, `testDebugUnitTest`, grep). Confirm
`permissions.notificationsButton` still says "Notificações".

**Update progress & memory:** tick P1.2; log deviations.

---

# PHASE 2 — Colored glow on the gear icon (risk: low, additive)

**Concept:** reuse the existing field-glow look (the colored "brilho" around chave/senha) on the gear
icon, driven by **auto-activities health**: green = on & fully healthy, orange = on but degraded
(a recommended permission is missing), no glow = off. The glow technique is the `Modifier.shadow(...)`
in `GlowField.kt` (`elevation = 16.dp`, `clip = false`, `ambientColor`/`spotColor` = glow color). The
colors already exist in the theme: `CheckingFieldAuthedGlow` / `CheckingFieldAuthedBorder` (green) and
`CheckingFieldPendingGlow` / `CheckingFieldPendingBorder` (orange).

## Prompt P2.1 — Health enum + state field + pure mapping (no wiring yet)

**Goal:** introduce the data and the pure mapping, fully additive. Nothing consumes them yet, so the
app is unchanged.

**Risk:** low (new code only).

**Context to load before editing:**
- Read Section 0 + Section 1.
- Read `presentation/check/CheckUiState.kt` and `presentation/components/GlowField.kt` (note the
  `FieldGlow` enum and the shadow technique).

**Changes:**
1. Create `enum class AutoActivitiesHealth { Off, Healthy, Degraded }`. Place it next to `CheckUiState`
   (top of `CheckUiState.kt`, near `NotificationTone`).
2. Add a field to `CheckUiState`: `val autoActivitiesHealth: AutoActivitiesHealth = AutoActivitiesHealth.Off`.
3. Add a **pure** mapping function (a top-level `fun` in the same file or a small new file under
   `presentation/components/`): `fun AutoActivitiesHealth.toGlow(): FieldGlow` returning
   `Off -> FieldGlow.None`, `Healthy -> FieldGlow.Authenticated`, `Degraded -> FieldGlow.Pending`.
4. Add a unit test (e.g. `app/src/test/.../presentation/AutoActivitiesHealthTest.kt`) asserting all
   three mappings.

**Do NOT:** call any Android/permission API here; do not change the ViewModel or any UI yet.

**Verify:** `./gradlew testDebugUnitTest` passes (new test green). App behavior unchanged (nothing
reads the new field).

**Update progress & memory:** tick P2.1; log deviations.

---

## Prompt P2.2 — Derive health in the ViewModel

**Goal:** populate `CheckUiState.autoActivitiesHealth` from the live permission status, on the
**existing** re-evaluation path. No UI consumes it yet.

**Risk:** low (writes a new state field only; never gates behavior on it).

**Context to load before editing:**
- Read Section 0 + Section 1 + P2.1's result.
- Read `presentation/check/CheckViewModel.kt`, focusing on `onLocationPermissionStateChanged`,
  `onAutomaticActivitiesToggled`, `onAutoActivitiesPermissionsGranted`,
  `onAutoActivitiesPermissionsDenied`. Note `onLocationPermissionStateChanged` already calls
  `PermissionLadder.checkStatus(context)` and is invoked on `ON_RESUME` from `CheckScreen`.

**Changes:**
1. Add a private helper, e.g.
   `private fun computeHealth(enabled: Boolean, context: Context): AutoActivitiesHealth` that returns
   `Off` when `!enabled`, else uses `PermissionLadder.checkStatus(context)`: `Healthy` if
   `allRecommendedGranted`, otherwise `Degraded`. (Rationale: if the engine is on, it is at least at
   the start minimum; missing *recommended* perms = degraded, not off.)
2. Call it wherever `automaticActivitiesEnabled` or location permission is (re)evaluated:
   in `onLocationPermissionStateChanged` (you already have `context` and the enabled flag from state),
   and at the end of `onAutomaticActivitiesToggled`, `onAutoActivitiesPermissionsGranted`,
   `onAutoActivitiesPermissionsDenied`. Each should `_uiState.update { it.copy(autoActivitiesHealth = ...) }`.
   Reuse the already-computed `checkStatus` where one is available rather than calling it twice.

**Do NOT:** change `locationPermissionSufficient` logic, the engine start/stop calls, or any other
state field. Do not gate any behavior on `autoActivitiesHealth`.

**Verify:** `./gradlew testDebugUnitTest` and `compileDebugKotlin` pass. Manually reason that
`automaticActivitiesEnabled`, `locationPermissionSufficient`, and the FGS start/stop paths are byte-for-byte
unchanged (only an extra `copy(...)` added).

**Update progress & memory:** tick P2.2; log deviations.

---

## Prompt P2.3 — Apply the glow to the gear icon

**Goal:** render the colored glow around the gear, driven by the state from P2.2.

**Risk:** low; worst case is a wrong glow color — never a functional break.

**Context to load before editing:**
- Read Section 0 + Section 1 + P2.1/P2.2 results.
- Read `presentation/components/AuthRow.kt` (the gear is a `Box` wrapping an `IconButton`, around
  lines 139–150) and `presentation/components/GlowField.kt` (copy the `Modifier.shadow` technique;
  use `CircleShape` for the gear).
- Read the gear/`AuthRow` call site in `presentation/check/CheckScreen.kt` (around line 300).

**Changes:**
1. Add an optional param to `AuthRow`: `autoActivitiesGlow: FieldGlow = FieldGlow.None`. (Default keeps
   every existing caller/test compiling and visually unchanged.)
2. In the gear `Box`, when `autoActivitiesGlow != FieldGlow.None`, apply
   `Modifier.shadow(elevation = 16.dp, shape = CircleShape, clip = false, ambientColor = glowColor, spotColor = glowColor)`
   where `glowColor` is `CheckingFieldAuthedGlow` for `Authenticated` and `CheckingFieldPendingGlow`
   for `Pending`. Optionally tint the gear icon with the matching border color; keep `CheckingPrimary`
   for `None`. Do **not** refactor `GlowField` — replicate the ~4 shadow lines inline.
3. In `CheckScreen.kt`, pass `autoActivitiesGlow = state.autoActivitiesHealth.toGlow()` to `AuthRow`.

**Do NOT:** change the chave/senha field glow logic; change the gear's `onSettingsClick`; alter layout
spacing so the row height changes (keep the gear inside its existing `Box` height = `Tokens.controlHeight`).

**Verify:** `compileDebugKotlin` + `testDebugUnitTest` pass. If a device/emulator is available, manually
confirm: logged out → no gear glow; auto-activities on & healthy → green; on & a recommended perm revoked
→ orange. Otherwise note "manual visual check pending" in Section 3.

**Update progress & memory:** tick P2.3; log deviations.

---

# PHASE 3 — Visual reorganization of the Settings dialog (risk: medium; behavior identical)

**Concept:** keep the dialog (it scrolls via `DialogScaffold`). Replace the flat wall of identical
`PrimaryButton`s with grouped **rows** under section headers, with a leading icon and a trailing
chevron. Three groups: **ATIVIDADES AUTOMÁTICAS**, **PREFERÊNCIAS** (Pausa Programada, Avisos, Idioma,
Alterar Senha), **AJUDA** (Suporte, Sobre). Every existing callback and `t()` key stays. In Phase 3 the
"Permissões" entry **remains wired** — it is removed only in Phase 4, to keep "visual change" isolated
from "structural change".

## Prompt P3.1 — Restructure layout into grouped rows (no new data dependency)

**Goal:** re-skin `SettingsDialog` only. Same inputs, same callbacks, same auth-gating, same visible
text keys.

**Risk:** medium (layout rewrite), but zero behavior change if callbacks are preserved.

**Context to load before editing:**
- Read Section 0 + Section 1.
- Read `presentation/components/SettingsDialog.kt` (current params and order), `PrimaryButton.kt`
  (has `SecondaryButton` too), and `presentation/theme/Tokens.kt` (spacing tokens).
- Read `app/src/androidTest/.../ui/SettingsDialogSmokeTest.kt` — it constructs `SettingsDialog` with
  the full param list and asserts: `settings.title`, `settings.languageLabel` shown; 6 language labels;
  language switch callback; auth-gated `autoActivities.title` + `scheduledPause.buttonLabel` shown when
  authenticated and absent when not; dismiss via `settings.backButton`; English strings render.

**Changes:**
1. Keep the `SettingsDialog` **signature unchanged in this prompt** (all current params, including
   `onPermissionsClick`). Only the body layout changes.
2. Introduce a small private `SettingsRow(icon, label, onClick, trailing?)` composable (leading icon,
   label, trailing chevron `Icons.Filled.ChevronRight` or similar). Use `Icons` already on the
   classpath. Convert the action buttons to rows; keep the language dropdown as-is.
3. Add section headers (small, uppercase, `CheckingTextMuted`, `labelMedium`) replacing the bare
   dividers: **Atividades Automáticas**, **Preferências**, **Ajuda**. Add new i18n keys for the three
   headers in all 6 dictionaries (e.g. `settings.groupAutoActivities`, `settings.groupPreferences`,
   `settings.groupHelp`). Order rows: Auto-activities row (auth-gated) under group 1; Pausa Programada,
   Avisos, Idioma, Alterar Senha under group 2 (respect existing auth/hasPassword gating); Permissões
   stays for now — place it under group 1 (it relates to auto-activities) until Phase 4 removes it;
   Suporte, Sobre under group 3.
4. Preserve **every** auth-gate exactly as today (`isAuthenticated`, `isAuthenticated && hasPassword`).
   Preserve the dismiss "Voltar" `TextButton`.

**Do NOT:** change the param list; drop any callback; change which keys render as visible text (the
smoke test relies on `autoActivities.title`, `scheduledPause.buttonLabel`, `settings.title`,
`settings.languageLabel`, `settings.backButton` being present with the same wording).

**Verify:** `compileDebugKotlin` + `testDebugUnitTest` pass. The smoke test must still pass **unchanged**
(if it fails because a row uses a different node type, adjust the test's matcher minimally and record it
in Section 3 — but the asserted *text* must remain present). Add the 3 new header keys to all 6 dicts
(re-run `I18nTest`).

**Update progress & memory:** tick P3.1; log deviations.

---

## Prompt P3.2 — Status chip on the Auto-activities row

**Goal:** show the auto-activities state at a glance on its row: "Ativadas" (green), "Atenção" (orange),
"Desativadas" (muted), driven by `AutoActivitiesHealth` from Phase 2.

**Risk:** low–medium (adds one param + a small composable).

**Context to load before editing:**
- Read Section 0 + Section 1 + P2.1 + P3.1 results.
- Re-read the (now row-based) `SettingsDialog.kt` and the smoke test.

**Changes:**
1. Add an optional param `autoActivitiesHealth: AutoActivitiesHealth = AutoActivitiesHealth.Off` to
   `SettingsDialog`. Pass it from `CheckScreen.kt` (`autoActivitiesHealth = state.autoActivitiesHealth`).
2. On the Auto-activities `SettingsRow`, render a small trailing status chip (text + tone color reusing
   the same green/orange/muted palette as the glow). Add i18n keys `settings.statusOn`,
   `settings.statusAttention`, `settings.statusOff` to all 6 dicts.
3. Update `SettingsDialogSmokeTest` constructor call to pass the new param (default is fine, but make
   the call compile). This is a **required, expected** test edit — note it in Section 3.

**Do NOT:** gate visibility of the row on health; the row must always show when authenticated (only the
chip text/tone changes). Do not change other rows.

**Verify:** `compileDebugKotlin` + `testDebugUnitTest` pass (smoke test updated to new signature). 6-dict
parity green.

**Update progress & memory:** tick P3.2; log deviations.

---

# PHASE 4 — Fuse "Permissões" into "Atividades Automáticas" (risk: HIGH; structural)

**Concept:** make the Auto-activities dialog the single home for granting everything, via a **live
checklist** sourced from `PermissionsInspector.inspect(...)`, each row tappable to fix using existing
`PermissionLadder` launchers. The existing automatic ladder (steps 0–5) stays as the "grant all
pending" path. Then remove the standalone "Permissões" menu entry. The `PermissionsDialog` file is kept
as an **unreachable safety net** until device verification, then deleted in P4.3.

> ⚠ This is the only phase that removes a behavior hook (`onPermissionsClick`). Proceed only after
> Phases 1–3 are green. Manual device verification is required before P4.3.

## Prompt P4.1 — Add the live checklist inside AutoActivitiesDialog (additive)

**Goal:** add a status-aware, tappable checklist to `AutoActivitiesDialog` so the user can see and fix
each requirement from one place. Add it **alongside** the existing controls; remove nothing yet.

**Risk:** medium here (UI only; reuses tested primitives).

**Context to load before editing:**
- Read Section 0 + Section 1.
- Read `presentation/settings/autoactivities/AutoActivitiesDialog.kt` in full (note the step machine in
  the `LaunchedEffect(stepIndex)`, the `minimumToStartGranted` vs `allRecommendedGranted` notices, and
  the existing `SecondaryButton` "Revisar Permissões").
- Read `presentation/settings/permissions/PermissionsDialog.kt` in full — it already implements the
  three sections (location / background-ops / notifications) and a colored status report using
  `PermissionsInspector`. **You are re-presenting this same content as a checklist inside
  AutoActivities; reuse the same launchers and the same `PermissionsInspector.inspect(...)` call.**
- Read `PermissionsInspector.kt` and `PermissionLadder.kt` for the exact fields/launchers.

**Changes:**
1. Inside `AutoActivitiesDialog`, below the enable checkbox, render a checklist of rows (reuse a small
   local `ChecklistRow(label, statusText, tone, onFix)` composable). Bind each row's status live from
   `PermissionsInspector.inspect(context, oemAck)` re-read on `ON_RESUME` (the dialog already observes
   lifecycle for the ladder; reuse/extend that — do not add a second competing observer that fights the
   step machine). Rows:
   - **Notificações** → `notificationsGranted`; fix → request `POST_NOTIFICATIONS` or
     `launchAppNotificationSettings`.
   - **Localização "o tempo todo"** → green only when `location == PRECISE && backgroundGranted`,
     orange when precise-without-background or imprecise, red when denied; fix → request fine/coarse or
     `launchLocationSettings`.
   - **Bateria sem restrição** → `!batteryRestricted`; fix → `launchBatteryOptimizationRequest`.
   - **Iniciar com o aparelho** (only when `detectOemType() != GENERIC`) → `autoStartEnabled`; fix →
     `launchOemAutostartSettings`.
   Use the same tone colors as `PermissionsDialog` (green/orange/red).
2. Keep the existing "Conceder permissões pendentes" path: the current automatic ladder is fine — you
   may relabel the existing `SecondaryButton` to a clearer key (add i18n key, all 6 dicts) but keep its
   `onClick` (start the ladder) intact.
3. Add all new row-label / status i18n keys to **all 6 dictionaries**.

**Do NOT:** modify the step machine logic, `onPermissionsGranted`/`onPermissionsDenied` contracts,
`PermissionLadder`, or `PermissionsInspector`. Do not remove the existing notices yet — you may keep or
fold them, but the dialog must remain functionally a superset of today.

**Verify:** `compileDebugKotlin` + `testDebugUnitTest` pass. Add/extend an instrumented smoke test only
if feasible; otherwise note "device verification pending". 6-dict parity green.

**Update progress & memory:** tick P4.1; log deviations.

---

## Prompt P4.2 — Remove the "Permissões" entry from the Settings menu

**Goal:** now that Auto-activities owns the checklist, drop the standalone "Permissões" row so there is
one clear path. Keep `PermissionsDialog`, `CheckDialog.Permissions`, `openPermissionsDialog()` and its
routing **in place but unreachable** (safety net) — only the menu entry and its callback wiring go.

**Risk:** HIGH (removes a hook + changes `SettingsDialog` signature + edits tests).

**Context to load before editing:**
- Read Section 0 + Section 1 + P4.1 result.
- Read `SettingsDialog.kt`, the `SettingsDialog(...)` call in `CheckScreen.kt`, and
  `SettingsDialogSmokeTest.kt` (it passes `onPermissionsClick`).

**Changes:**
1. Remove the **Permissões** row and the `onPermissionsClick` parameter from `SettingsDialog`.
2. In `CheckScreen.kt`, remove the `onPermissionsClick = { ... }` argument from the `SettingsDialog`
   call. **Leave** `CheckDialog.Permissions ->` routing and `PermissionsDialog` import intact (dead but
   present) — do not delete them in this prompt.
3. Update `SettingsDialogSmokeTest.kt`: remove `onPermissionsClick` from all constructor calls. This is
   a required, expected edit — record it in Section 3.

**Do NOT:** delete `PermissionsDialog.kt`, the enum value, or `openPermissionsDialog()` yet. Do not
touch the auto-activities dialog.

**Verify:** `compileDebugKotlin` + `testDebugUnitTest` pass. Confirm by grep that the only remaining
references to `onPermissionsClick` are gone and `PermissionsDialog`/`CheckDialog.Permissions` still
compile (unreferenced from the menu is OK).

**Update progress & memory:** tick P4.2; log deviations. **Add a note: "P4.3 is BLOCKED until a human
confirms on a real device that the Auto-activities checklist grants every permission correctly."**

---

## Prompt P4.3 — Delete the now-unused Permissions plumbing (GATED)

**Goal:** final cleanup once the fused flow is verified on a real device.

**Risk:** HIGH; only run after explicit human confirmation logged in Section 3.

**Precondition:** Section 3 contains a human-signed note "device-verified: checklist grants all perms".
If absent, **stop and ask** — do not proceed.

**Context to load before editing:**
- Read Section 0 + Section 1 + P4.1/P4.2.
- Grep for `Permissions` usages: `CheckDialog.Permissions`, `openPermissionsDialog`, `PermissionsDialog`.

**Changes:**
1. Delete `presentation/settings/permissions/PermissionsDialog.kt`.
2. Remove the `Permissions` value from the `CheckDialog` enum in `CheckUiState.kt`.
3. Remove `openPermissionsDialog()` from `CheckViewModel.kt`.
4. Remove the `CheckDialog.Permissions ->` branch and the `PermissionsDialog` import in `CheckScreen.kt`.
5. Remove/adjust any test referencing these.
6. **Do NOT** remove `PermissionsInspector` or `PermissionLadder` — the checklist depends on them.

**Verify:** `compileDebugKotlin` + `testDebugUnitTest` pass; grep shows no dangling references.

**Update progress & memory:** tick P4.3; log deviations.

---

# PHASE 5 — First-login nudge (risk: medium; isolated, additive)

**Concept:** a one-time, dismissible card shown in the Check screen body after a successful login, for
users who have not enabled auto-activities and have not dismissed it. "Ativar agora" opens the
Auto-activities dialog; "Agora não" dismisses it forever (per chave). Transient → no permanent height
cost. Persistence uses the existing generic flag API (`appPreferences.getFlag/setFlag`) keyed by chave,
so there is **no UserSettings schema migration**.

## Prompt P5.1 — Nudge state plumbing

**Goal:** add the persisted per-chave flag, the visibility predicate, and the dismiss action in the VM.

**Risk:** medium (new state + persistence), but additive and behavior-gated only on the new card.

**Context to load before editing:**
- Read Section 0 + Section 1.
- Read `data/local/AppPreferencesDataSource.kt` (note `getFlag(name): Flow<Boolean>` and
  `setFlag(name, value)`), `presentation/check/CheckViewModel.kt` (how `appPreferences`, `chave`,
  `automaticActivitiesEnabled`, and `_uiState` are used; how the chave/auth flow sets state), and
  `CheckUiState.kt`.

**Changes:**
1. Add `val showAutoActivitiesNudge: Boolean = false` to `CheckUiState`.
2. Define the flag name helper, e.g. `private fun nudgeFlag(chave: String) = "auto_activities_prompt_dismissed_$chave"`.
3. When a user becomes authenticated for a 4-char chave (reuse the existing auth-success path; do not
   add a new lifecycle source), compute and set `showAutoActivitiesNudge = isAuthenticated &&
   !automaticActivitiesEnabled && !appPreferences.getFlag(nudgeFlag(chave)).first()`.
   Recompute (set to false) when auto-activities becomes enabled or the user logs out.
4. Add `fun dismissAutoActivitiesNudge()`: `viewModelScope.launch { appPreferences.setFlag(nudgeFlag(chave), true) }`
   and set `showAutoActivitiesNudge = false`. (The "Ativar agora" action reuses the existing
   `openAutoActivitiesDialog()`; it should also hide the nudge.)
5. Add a unit test for the **pure** predicate (extract the boolean expression into a testable pure
   function `fun shouldShowAutoActivitiesNudge(authenticated, autoEnabled, dismissed): Boolean`).

**Do NOT:** modify `UserSettings`/`PersistedSettings.kt` serialization; change login/auth logic beyond
setting the new flag-derived state field.

**Verify:** `compileDebugKotlin` + `testDebugUnitTest` pass (new predicate test green).

**Update progress & memory:** tick P5.1; log deviations.

---

## Prompt P5.2 — Render the nudge card

**Goal:** show the card in the Check screen body when `showAutoActivitiesNudge` is true.

**Risk:** low–medium (new composable; conditional rendering).

**Context to load before editing:**
- Read Section 0 + Section 1 + P5.1 result.
- Read `presentation/check/CheckScreen.kt`, specifically the authenticated section
  (`if (state.isAuthenticated) { ... }`) and how existing cards (`NotificationCard`, `LocationCard`)
  are placed; read `presentation/components/CheckCard.kt`/`NotificationCard.kt` for the visual style to
  match.

**Changes:**
1. Create `presentation/components/AutoActivitiesNudgeCard.kt`: a dismissible card with the explanatory
   line and two actions — primary "Ativar agora" (`onActivate`) and text "Agora não" (`onDismiss`).
   Match the existing card styling (rounded, `CheckingCardBg`, theme colors).
2. In `CheckScreen.kt`, inside the authenticated block (near the top, before `RegistrationFieldset`),
   render `if (state.showAutoActivitiesNudge) AutoActivitiesNudgeCard(onActivate = { vm.openAutoActivitiesDialog(); /* nudge hides via state */ }, onDismiss = vm::dismissAutoActivitiesNudge, t = t)`.
3. Add i18n keys to all 6 dictionaries: `autoActivities.nudgeQuestion`, `autoActivities.nudgeActivate`
   (e.g. "Ativar agora"), `autoActivities.nudgeLater` (e.g. "Agora não").
4. Add an instrumented smoke test for the card if feasible (renders, both buttons fire callbacks);
   otherwise note manual check pending.

**Do NOT:** add the card outside the authenticated block; make it persistent; change main-screen layout
height when the nudge is absent (it must contribute zero height when `showAutoActivitiesNudge` is false).

**Verify:** `compileDebugKotlin` + `testDebugUnitTest` pass. 6-dict parity green. If a device is
available: log in fresh → card appears once; tap "Agora não" → gone and stays gone after relaunch; tap
"Ativar agora" → Auto-activities dialog opens and the card is gone.

**Update progress & memory:** tick P5.2; log deviations.

---

# PHASE 6 — Final integrity verification (run AFTER all change phases)

> Goal: prove the app's integrity is preserved versus the Phase 0 baseline — that the only things that
> changed are the intended cosmetic/UX surfaces, and every critical user flow still works.

## Prompt P6.1 — Automated regression + protected-files zero-diff

**Goal:** confirm the full suite is still green and that the protected files never changed.

**Risk:** none (verification).

**Context to load before editing:** Read Sections 0, 1, 4, 5 and the Phase 0 baseline you recorded.

**Steps:**
1. From `checking_kotlin/`, run `./gradlew testDebugUnitTest`. It MUST be green, with a test count
   **>= the Phase 0 baseline** (P2.1/P5.1 add tests, raising it). No test may be deleted to force
   green — the only allowed test edits are the smoke-test signature updates in P3.2/P4.2, which
   *modify* assertions, not remove coverage.
2. Run `./gradlew compileDebugKotlin` — clean.
3. Confirm 6-dictionary key-parity (`I18nTest`) is green.
4. Run `git diff` restricted to every path in Section 5. It MUST be empty. If anything appears, the
   integrity guarantee is broken — STOP, document in Section 3, and report. Do NOT "fix" it by editing
   a protected file.
5. Append to Section 4: final test count vs. baseline, and "protected-files diff: empty".

**Do NOT:** delete or weaken existing assertions to force green; modify any protected file.

**Verify:** suite green (count >= baseline), parity green, protected diff empty, Section 4 updated.

**Update progress & memory:** tick P6.1; log deviations.

## Prompt P6.2 — Manual device regression checklist

**Goal:** exercise the flows that unit/smoke tests cannot fully cover (they need a real device), to
prove behavior is unchanged. Requires a connected device/emulator. If none is available, mark each item
"pending-for-device" and hand the checklist to the human — do NOT tick P6.2 as done without a device pass.

**Context to load before editing:** Read Sections 0, 1.

**Run the debug build on a device and confirm each item matches pre-change behavior:**
1. **Auth:** known chave → "found" orange glow on the fields; log in → green; wrong password handled as
   before; logout resets state.
2. **Manual check-in / check-out (core path — must be untouched):** with auto-activities OFF, the
   "Local" dropdown appears, submit works, history updates.
3. **Auto-activities ON (riskiest area):** enabling via the dialog drives each grant through the
   checklist; granting the minimum starts the foreground-service notification; the "Local" GPS card
   appears; revoking a *recommended* permission shows degraded (orange) state while the engine keeps
   running. (Geofence triggering may not fire on an emulator — verify on a real device or note it.)
4. **Gear glow:** reflects Off / Healthy (green) / Degraded (orange) correctly and never blocks the gear tap.
5. **Settings dialog:** grouped and legible; every row opens the correct destination; "Avisos" and
   "Alterar Senha" labels correct; no "Permissões" entry remains (Phase 4); language switch works.
6. **First-login nudge:** appears once for a fresh login without auto-activities; "Agora não" dismisses
   permanently (survives relaunch); "Ativar agora" opens the auto-activities dialog.
7. **Untouched subsystems still work:** Accident mode (banner, report, video), Transport screen,
   Scheduled Pause, offline queue replay on reconnect, push-notification ("Avisos") preferences.

**Verify:** every item passes (or is explicitly marked pending-for-device with human acknowledgement).

**Update progress & memory:** tick P6.2; record results in Section 3/4.

---

## Acceptance summary

Integrity is preserved when: Section 2 is fully ticked; **P6.1** shows the suite green (count >=
baseline) with an **empty protected-files diff**; **P6.2** device checklist passed; and Sections 3/4
capture every deviation plus the baseline-vs-final comparison. The background engine, foreground
service, geofencing, serialization contract, and check-in/out behavior remain unchanged. Do not
commit/push unless asked.
