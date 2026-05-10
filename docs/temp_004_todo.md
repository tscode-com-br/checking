# TODO List for Modification 4 - AI Agent Prompts

## How to use this document

This file is a phased implementation backlog for the `Checking Web` application.  
Each checklist item is written as a **prompt for an AI coding agent** that will make code changes in the repository.

### Global implementation context for every agent

Use these assumptions in every prompt below:

1. Repository root: `C:\dev\projetos\checkcheck`
2. Main frontend surface: `sistema/app/static/check`
3. Main backend router involved in authentication: `sistema/app/routers/web_check.py`
4. Static assets mount: `/assets` is already served by the backend, and `assets/icons/config.webp` already exists and is valid for use.
5. Existing password-related dialogs already exist and should be **reused whenever possible** instead of being replaced wholesale.
6. Avoid changing backend API contracts unless absolutely necessary. The main requirement is a **frontend behavior and UX refactor**, not an API redesign.
7. Do not revert unrelated user changes in the repo.
8. Preserve mobile-first layout and behavior. The `Checking Web` UI is already optimized primarily for mobile, so all new UI must remain compact, touch-friendly, and keyboard-accessible.
9. Keep the application behavior safe around authentication, geolocation permissions, and modal state transitions.
10. When updating tests, prefer modifying existing `check`-focused tests if they already cover the affected area; add new tests only where coverage would otherwise remain weak.

### Shared acceptance standards for all prompts

For every implementation prompt below, the agent should:

1. Inspect the relevant existing code before editing it.
2. Reuse current patterns already present in:
   - `sistema/app/static/check/app.js`
   - `sistema/app/static/check/styles.css`
   - `sistema/app/static/check/index.html`
   - `sistema/app/static/transport/app.js` and `i18n.js` only as architectural references, not as direct copy-paste dependencies.
3. Keep code readable and cohesive with the current style of the repository.
4. Update or add automated tests related to the modified behavior.
5. Summarize exactly which files were changed and which tests were run.


## Phase 1 - Replace the Main Password Action Button with a Settings Entry Point

### Prompt 1 - Replace the main auth action button with a gear icon trigger and add the Settings modal shell

**Prompt for the AI agent**

Implement the first structural UI refactor for `Checking Web`.

### Goal

Remove the old main-screen password action entry point from the authentication row and replace it with a new **gear icon button** that opens a new **Settings** modal shell. At this stage, focus on **markup, structure, and styling foundations**, not the final business logic of every settings action.

### Required files to inspect first

1. `sistema/app/static/check/index.html`
2. `sistema/app/static/check/styles.css`
3. `sistema/app/static/check/app.js`
4. `assets/icons/config.webp`

### Required implementation details

1. In `index.html`, replace the current visual role of the old action button in the auth row.
   - The current control is the button beside the `Senha` field.
   - The new control must be a **settings trigger button** using the gear icon from `assets/icons/config.webp`.
   - The new button should remain inside the same auth-row area so alignment is preserved.

2. Keep the auth row layout stable.
   - The new settings button must have the **same visual height** as the old action button.
   - Preserve the current `auth-field-button` column structure unless there is a very strong reason not to.
   - Do not make the auth row wider, taller, or visually unbalanced on mobile.

3. Add a new modal shell to `index.html` for `Settings`.
   - Add a backdrop element and a dialog/card container, following the same structural pattern used by the existing password and registration dialogs.
   - Add placeholder sections/controls for:
     - Language
     - Reset Password
     - Allow Location
     - Support
     - About
   - Add a back/close button inside the Settings modal.

4. Add accessibility attributes to the new settings trigger and modal.
   - The trigger button must have a meaningful `aria-label`, such as `Open settings`.
   - The modal must use:
     - `role="dialog"`
     - `aria-modal="true"`
     - `aria-labelledby`
   - The trigger should expose `aria-controls` and later support `aria-expanded`.

5. Add initial CSS for the new settings trigger and settings modal in `styles.css`.
   - The settings trigger should:
     - match the old control height;
     - visually contain the `config.webp` icon cleanly;
     - support `hover`, `focus-visible`, `active`, and `disabled` states;
     - remain touch-friendly.
   - The icon should:
     - use `object-fit: contain`;
     - not stretch;
     - be centered and sized consistently.
   - The Settings modal card should:
     - visually match the family of existing dialogs;
     - be mobile-friendly;
     - support internal scrolling if content exceeds viewport height.

6. Do not implement the full Settings behavior yet.
   - Only create the structural HTML and CSS shell.
   - It is acceptable for buttons inside the Settings modal to be present but not yet fully wired, as long as the structure is correct and intentionally named.

### Naming and DOM expectations

Use stable IDs/classes for future prompts. Recommended IDs:

1. `settingsButton`
2. `settingsDialogBackdrop`
3. `settingsDialog`
4. `settingsDialogTitle`
5. `settingsLanguageSelect`
6. `settingsResetPasswordButton`
7. `settingsLocationPermissionButton`
8. `settingsSupportButton`
9. `settingsAboutButton`
10. `settingsDialogBackButton`

You may add helper wrapper classes such as:

1. `settings-dialog-card`
2. `settings-dialog-form`
3. `settings-option-row`
4. `settings-option-label`
5. `settings-option-action`

### Constraints

1. Do not remove the existing password change dialog or registration dialog.
2. Do not yet remove all old JS references; only remove them if they would break the page immediately.
3. Do not redesign the whole page. This prompt is for structural replacement only.

### Acceptance criteria

1. The main authentication row shows a gear-based settings trigger instead of the old text action button.
2. The gear button uses `assets/icons/config.webp` through the `/assets` mount.
3. The new settings modal shell exists in `index.html`.
4. The new settings modal has placeholder controls for all required options.
5. The UI remains aligned and mobile-safe.

### Tests to update or add

Update or add frontend structure tests to validate:

1. the presence of the settings trigger;
2. the use of `config.webp`;
3. the presence of the Settings modal shell and its key controls.

Relevant existing tests to inspect:

1. `tests/check_registration_widget.test.js`
2. `tests/check_auth_transport_ui.test.js`


## Phase 2 - Wire the Settings Modal and Move the Password Change Entry Point

### Prompt 2 - Implement Settings modal open/close behavior and move the password-change trigger into Settings

**Prompt for the AI agent**

Now that the Settings modal shell exists, implement its opening/closing behavior and make the **Reset Password** option the new entry point for the current password change flow.

### Goal

The Settings modal should behave like the other `Checking Web` dialogs, and the old “button beside Password” behavior for password changes must now live inside `Settings > Reset Password`.

### Required files to inspect first

1. `sistema/app/static/check/app.js`
2. `sistema/app/static/check/index.html`
3. `sistema/app/static/check/styles.css`

### Required implementation details

1. Add DOM bindings in `app.js` for the new Settings elements:
   - `settingsButton`
   - `settingsDialogBackdrop`
   - `settingsDialog`
   - `settingsDialogBackButton`
   - `settingsResetPasswordButton`
   - and any other elements needed for later prompts.

2. Add helper functions for the new modal:
   - `isSettingsDialogOpen()`
   - `openSettingsDialog()`
   - `closeSettingsDialog()`
   - optional: `syncSettingsDialogPresentation()` or similar if needed

3. Integrate the Settings modal into global dialog state management.
   - Update the app’s “is any dialog open?” logic so the Settings modal participates in UI locking.
   - Make sure main form controls are disabled appropriately when Settings is open, following current app conventions.
   - Ensure Settings closes correctly on:
     - backdrop click;
     - `Escape`;
     - explicit back button click.

4. Restore focus correctly.
   - When Settings is closed, focus should return to `settingsButton` when appropriate.
   - Follow the same spirit as other modal flows in the file.

5. Move the password change trigger into Settings.
   - Clicking `settingsResetPasswordButton` should:
     - close the Settings modal;
     - open the existing password dialog in **change mode**;
     - preserve all current validation and submit behavior for changing a password.

6. Preserve the current password dialog implementation.
   - Do not rebuild the existing password change modal unless absolutely necessary.
   - Reuse the current `submitPasswordChange()` flow.
   - Reuse the current `change-password` endpoint and current success/error behavior.

7. Remove the old main-screen password action trigger behavior.
   - Eliminate the old click path that opened password change from the main auth row.
   - Make sure there is no leftover path where the old removed button is still assumed to exist.

8. Control the enabled/disabled state of `Reset Password`.
   - Recommended behavior:
     - keep the menu item visible;
     - disable it when the application is not in a valid authenticated/unlocked state for password change;
     - if there is an explanatory helper text or status message area inside the modal, keep it concise.

### Constraints

1. Do not break password registration mode. The existing password dialog still needs to support both:
   - register password for a user that exists but has no password;
   - change password for an already authenticated user.
2. Do not change backend API contracts.
3. Do not reintroduce any old `Chave?` / `Senha?` label behavior in the main row during this prompt.

### Acceptance criteria

1. Clicking the gear icon opens the Settings modal.
2. Settings closes correctly via backdrop, `Escape`, and back button.
3. `Reset Password` opens the existing password dialog in change mode.
4. Existing password change behavior still works through the current password dialog logic.
5. The page does not reference a removed main password action button in a way that causes runtime errors.

### Tests to update or add

Add or update tests that verify:

1. the gear button opens the Settings modal;
2. the Settings modal closes correctly;
3. `Reset Password` is now the path to open the password change flow;
4. no obsolete main-screen password action trigger remains in the `check` UI.


## Phase 3 - Replace “Chave?” / “Senha?” with Automatic Modal Opening

### Prompt 3 - Remove the old dynamic main-button states and auto-open the registration/password-registration flows

**Prompt for the AI agent**

Refactor the authentication UX so that the old dynamic main-screen prompts (`Chave?` and `Senha?`) disappear entirely from the main auth row. Instead, the correct dialog should open automatically when the key status is resolved.

### Goal

Implement the new behavior:

1. If the typed key does not exist in the database, automatically open the **user self-registration** dialog.
2. If the typed key exists but has no password, automatically open the **password registration** dialog.
3. Prevent endless re-opening loops when the user closes a dialog manually.

### Required files to inspect first

1. `sistema/app/static/check/app.js`
2. `sistema/app/static/check/web-client-state.js`
3. `sistema/app/static/check/index.html`

### Required implementation details

1. Find the current auth-state decision points in `app.js`.
   - Inspect:
     - `refreshAuthenticationStatus(...)`
     - `applyAuthenticationStatusPayload(...)`
     - old button-label logic and related helpers
     - any logic that currently opens dialogs based on button clicks

2. Remove the old main-row dynamic CTA logic.
   - The main auth row must no longer communicate `Chave?` or `Senha?`.
   - If helper functions like `resolvePasswordActionButtonLabel()` become obsolete, either remove them cleanly or simplify them so they no longer drive the old UX.
   - Do not leave dead branches that still assume those states.

3. Introduce automatic modal opening after auth status resolution.
   - When `GET /api/web/auth/status` resolves for a valid 4-character key:
     - if `found = false`, open the user registration dialog automatically;
     - if `found = true` and `has_password = false`, open the password dialog in registration mode automatically.

4. Add robust anti-loop protection.
   - This is critical.
   - The dialog must **not** reopen immediately after a user closes it manually.
   - Create a small, explicit state mechanism that tracks auto-open attempts for the current key and status.
   - Recommended patterns:
     - a per-key record for auto-opened registration states;
     - or dedicated variables such as:
       - `lastAutoOpenedRegistrationChave`
       - `lastAutoOpenedPasswordRegistrationChave`
   - Reset those guards only when meaningful state changes occur, such as:
     - the key changes;
     - the user successfully registers;
     - the user successfully registers a password;
     - the auth status changes into a different state.

5. Keep the existing registration dialogs and submit functions.
   - Reuse `openRegistrationDialog()`.
   - Reuse `openPasswordDialog()` in password-registration mode.
   - Reuse existing form submission logic unless a bug forces a localized fix.

6. Preserve login flow for existing users with passwords.
   - If `has_password = true`, the automatic behavior should not incorrectly open either registration flow.
   - Existing login/verification behavior should still work as before.

7. Handle unknown-user transitions consistently across all auth flows.
   - If a stale request or late response reveals an unknown-user state, route the UI into the correct self-registration path.
   - Preserve current protection against stale async auth verification attempts.

### Constraints

1. Do not break password change mode.
2. Do not break existing login auto-verification behavior for users who already have passwords.
3. Avoid large rewrites of the entire auth subsystem; keep the change focused and intentional.

### Acceptance criteria

1. The main auth row no longer depends on `Chave?` or `Senha?`.
2. Unknown keys open the self-registration dialog automatically.
3. Existing users without passwords open the password-registration dialog automatically.
4. Closing either dialog manually does not cause instant re-opening loops.
5. Changing the key resets the relevant auto-open behavior correctly.

### Tests to update or add

Add or update tests that verify:

1. unknown key -> automatic registration dialog opening;
2. known key without password -> automatic password registration dialog opening;
3. manual dialog close does not create a loop;
4. changing the key resets the auto-open guard correctly.

Existing `check` tests that may need updates:

1. `tests/check_registration_widget.test.js`
2. `tests/check_user_location_ui.test.js`


## Phase 4 - Implement the Settings Location Permission Action

### Prompt 4 - Add the “Allow Location” Settings action and disable it when location sharing is already active

**Prompt for the AI agent**

Implement the Settings action that re-requests precise geolocation access and make it correctly disabled when the web app already has active location permission/state.

### Goal

The Settings modal must contain a working **Allow Location** action that:

1. re-triggers the geolocation flow when permission is not yet granted;
2. becomes disabled when location is already effectively shared with the web app;
3. handles unsupported browsers and insecure contexts gracefully.

### Required files to inspect first

1. `sistema/app/static/check/app.js`
2. `sistema/app/static/check/web-client-state.js`
3. `sistema/app/static/check/index.html`
4. `sistema/app/static/check/styles.css`

### Existing code areas to inspect carefully

1. `queryLocationPermissionState()`
2. `resolveCurrentLocation(...)`
3. `setGpsLocationPermissionGranted(...)`
4. `setLocationWithoutPermission()`
5. `gpsLocationPermissionGranted`
6. `locationPermissionGrantedKey`
7. current messages and flows related to geolocation permission

### Required implementation details

1. Add the Settings action wiring in `app.js`.
   - Bind `settingsLocationPermissionButton`.
   - Add a dedicated function, for example:
     - `requestPreciseLocationPermissionFromSettings()`

2. Reuse the current geolocation pipeline instead of inventing a parallel one.
   - Prefer calling the existing location-resolution flow with options that force an interactive permission request.
   - A good candidate is reusing `resolveCurrentLocation(...)` with options such as:
     - `interactive: true`
     - `forceRefresh: true`
     - `showDetectingState: true`

3. Disable the button when permission is already effectively granted.
   - Base the disabled decision on the current actual app state, not only one browser signal.
   - Consider:
     - `gpsLocationPermissionGranted`
     - persisted permission-granted local flag
     - browser permission state if available
   - The button should not remain enabled when the app is already clearly in the “permission granted / location available” state.

4. Provide graceful user feedback for edge cases.
   - If `navigator.geolocation` is unavailable: show a clear message.
   - If the page is not in a secure context: show a clear message.
   - If the browser permission is permanently denied: show a helpful message telling the user the browser/site permission must be changed manually.

5. Keep the Settings UI synchronized.
   - When permission state changes, the button’s enabled/disabled state must update.
   - If you add a status text inside Settings, keep it short and consistent with existing app tone.

6. Do not break the current location and automatic-activities logic.
   - The Settings action must layer on top of existing behavior, not fork it.
   - Ensure the rest of the UI still reacts correctly after permission is granted or denied.

### Constraints

1. Do not remove the existing manual location fallback logic.
2. Do not break current geolocation status handling outside Settings.
3. Avoid duplicating the location pipeline in a second incompatible code path.

### Acceptance criteria

1. `Allow Location` is visible in Settings.
2. Clicking it attempts to re-trigger precise geolocation permission when possible.
3. The button becomes disabled when the app already has location permission/share state.
4. Unsupported/insecure/denied cases produce clear feedback instead of silent failure.

### Tests to update or add

Add or update tests that verify:

1. the Settings location button exists;
2. the button is disabled when geolocation permission is already effectively granted;
3. clicking the button reuses the current geolocation flow;
4. unsupported and denied flows remain safe and user-visible.

Relevant existing test file to extend:

1. `tests/check_user_location_ui.test.js`


## Phase 5 - Implement Support via WhatsApp and About/Manual Entry

### Prompt 5 - Add the WhatsApp support action and wire the About button to the future manual page

**Prompt for the AI agent**

Implement the two utility actions inside Settings:

1. **Support** opens WhatsApp with a prefilled message.
2. **About** opens the Checking Web manual entry point.

### Goal

Make Settings capable of launching support and documentation from within the web app without disrupting the main auth and check-in flows.

### Required files to inspect first

1. `sistema/app/static/check/app.js`
2. `sistema/app/static/check/index.html`
3. `sistema/app/static/check/styles.css`

### Required implementation details

1. Implement the Support action.
   - Bind `settingsSupportButton`.
   - Build a WhatsApp link using:
     - `https://wa.me/5521992174446?text=...`
   - Prefill the text with:
     - `Checking Webacao Web. Minha chave e <USER_KEY>.`
   - Use `encodeURIComponent(...)` for the message.

2. Resolve the key used in the support message carefully.
   - Use a stable helper for key resolution.
   - Recommended priority:
     1. authenticated current key;
     2. currently typed key if it is a valid 4-character alphanumeric key;
     3. if neither is available, either:
        - disable the button; or
        - use a clearly intentional fallback message.

3. Recommended UX for Support:
   - Prefer disabling the button unless a valid key is available.
   - That makes the required support message more reliable and reduces malformed support requests.

4. Implement the About action.
   - Bind `settingsAboutButton`.
   - Create a helper such as `openCheckingWebManual()`.
   - Open the manual in a **new tab** with `noopener` behavior if possible.

5. Use a stable manual target path.
   - Recommended target:
     - `./manual.html` if you keep it under the same static surface;
     - or another stable path defined by the manual implementation prompt later.
   - The About button wiring should be easy to update if the exact manual file changes in a later prompt.

6. Keep Settings behavior clean.
   - Support and About should not break modal state.
   - It is acceptable to leave Settings open or close it before launching, but choose one consistent behavior and keep it predictable.
   - Recommended behavior:
     - close Settings before opening a secondary surface.

### Constraints

1. Do not implement the full manual page in this prompt; only wire the entry point.
2. Do not hardcode fragile string concatenations for the WhatsApp message; centralize the message builder.

### Acceptance criteria

1. Support opens WhatsApp to `+5521992174446` with a prefilled message containing the user key.
2. About opens the manual entry point in a new tab.
3. Support is not available when the app cannot safely determine a valid user key.

### Tests to update or add

Add or update tests that verify:

1. the Support button exists;
2. it generates the expected WhatsApp URL;
3. the About button points to the intended manual target;
4. the Support action respects the valid-key requirement.


## Phase 6 - Introduce a Centralized Dictionary Layer and I18n Runtime for Checking Web

### Prompt 6A - Create a dedicated dictionary file that contains every end-user label for every supported language

**Prompt for the AI agent**

Create a dedicated translation-dictionary source file for `Checking Web` that centralizes **all user-facing labels and visible strings** used across the web application screens.

### Goal

Before wiring the language selector behavior, create a single structured file that contains the translation dictionaries for every supported language. This dictionary file must become the canonical source for all visible labels shown to the user across the `Checking Web` experience.

### Required files to inspect first

1. `sistema/app/static/check/index.html`
2. `sistema/app/static/check/app.js`
3. `sistema/app/static/check/styles.css`
4. `sistema/app/static/check/transport-screen.js`
5. `sistema/app/static/check/web-client-state.js`
6. `sistema/app/static/check/automatic-activities.js`

Also inspect any manual or related `check` files if they already exist by the time this prompt is executed:

1. `sistema/app/static/check/manual.html`
2. `sistema/app/static/check/manual.js`

### New file to create

Create a dedicated dictionary file, separate from the runtime i18n helper file. Recommended filename:

1. `sistema/app/static/check/i18n-dictionaries.js`

If you choose a different name, it must still be:

1. clearly scoped to `check`;
2. dedicated to dictionary content;
3. easy for the runtime i18n layer to consume.

### Required implementation details

1. Build one dictionary object per supported language.
   - Required languages:
     - English
     - Portuguese
     - Chinese
     - Malay
     - Indonesian
     - Tagalog (Filipino)
   - Recommended language codes:
     - `en`
     - `pt`
     - `zh`
     - `ms`
     - `id`
     - `tl`

2. Translate **all user-facing labels and visible strings** that appear in the `Checking Web` application.
   - This must include, at minimum:
     - main authentication row labels;
     - button labels;
     - dialog titles;
     - form field labels;
     - helper text and placeholder text;
     - success, warning, error, and neutral status strings shown to the user;
     - Settings modal labels;
     - password registration and password change labels;
     - self-registration labels;
     - location-related visible text;
     - project-selection text;
     - transport-screen labels inside the `check` surface;
     - About / Support / Allow Location / Reset Password text;
     - manual-page labels and headings, if the manual surface already exists when this prompt runs.

3. Do a real inventory of user-facing strings instead of translating only the new Settings UI.
   - Search both HTML and JS for hardcoded visible text.
   - Do not limit the work to the main shell.
   - The intent is that the dictionary file becomes the canonical place to find all visible labels used by the `check` web application.

4. Structure dictionaries with stable hierarchical keys.
   - Recommended high-level namespaces:
     - `document`
     - `auth`
     - `settings`
     - `passwordDialog`
     - `registrationDialog`
     - `location`
     - `projects`
     - `transport`
     - `status`
     - `manual`
     - `support`
   - You may refine the structure, but keep it predictable and easy to maintain.

5. Add a language catalog in the same dictionary file or in a clearly connected export.
   - Each language entry should include:
     - `code`
     - canonical display label
     - optional locale metadata
   - For deterministic ordering across multiple scripts, sort the dropdown by the **canonical English language name**, and use this exact order:
     1. `Chinese`
     2. `English`
     3. `Indonesian`
     4. `Malay`
     5. `Portuguese`
     6. `Tagalog (Filipino)`

6. If you choose to render native-language names in the dropdown instead of English labels, keep the **same exact order** listed above.
   - This avoids ambiguity caused by cross-script alphabetical sorting.
   - The final dropdown order must be deterministic and must match the required alphabetical order by canonical English name.

7. Keep Portuguese as the baseline source language.
   - Portuguese is the current application language, so the Portuguese dictionary should reflect the current labels accurately.
   - Do not introduce unnecessary wording drift in Portuguese unless the existing visible label is clearly inconsistent and you intentionally normalize it across all languages.

8. Make the dictionary file runtime-friendly.
   - It should be easy for `i18n.js` to consume.
   - If the project uses global-scope scripts rather than ES modules here, follow the same pattern already used elsewhere in the repository.

### Constraints

1. Do not bury dictionaries directly inside `app.js`.
2. Do not make the runtime i18n file the only place where translation content lives; the dictionaries must live in their own dedicated file.
3. Do not translate only a subset of screens. The task explicitly requires labels across the various web-application screens.

### Acceptance criteria

1. A dedicated dictionary file exists for `Checking Web`.
2. The file contains dictionaries for:
   - English
   - Portuguese
   - Chinese
   - Malay
   - Indonesian
   - Tagalog (Filipino)
3. The file covers all user-facing labels used by the `check` surface, not just the new Settings modal.
4. The language catalog exists and defines the dropdown order exactly as:
   - Chinese
   - English
   - Indonesian
   - Malay
   - Portuguese
   - Tagalog (Filipino)

### Tests to update or add

Add or update tests that verify:

1. the dedicated dictionary file exists;
2. it contains all required language codes;
3. it exposes or makes available the required dropdown language catalog;
4. the catalog order matches the required exact sequence;
5. at least a representative set of key namespaces exists for all languages.

### Prompt 6 - Build a dedicated i18n module for Checking Web and connect it to the Settings language selector

**Prompt for the AI agent**

Implement a dedicated internationalization layer for `Checking Web`, using the `transport` dashboard’s i18n architecture as a reference, but not as a runtime dependency.

### Goal

The new Settings modal must include a working language selector that:

1. uses a dedicated `check` i18n module;
2. consumes the dedicated dictionary file created in Prompt 6A;
3. persists the chosen language locally;
4. applies translated UI strings without a full page reload whenever practical.

### Required files to inspect first

1. `sistema/app/static/transport/i18n.js`
2. `sistema/app/static/transport/app.js`
3. `sistema/app/static/check/index.html`
4. `sistema/app/static/check/app.js`
5. `sistema/app/static/check/styles.css`
6. `sistema/app/static/check/i18n-dictionaries.js`

### New file(s) to create

At minimum:

1. `sistema/app/static/check/i18n.js`

Optionally later:

1. additional manual-specific translation support if the manual page becomes large enough

### Required implementation details

1. Create a dedicated `check` i18n module.
   - Do not duplicate the dictionary content inside this runtime file.
   - Instead, consume the dictionaries and language catalog from `sistema/app/static/check/i18n-dictionaries.js`.
   - The runtime file should be responsible for lookup, persistence, fallback behavior, and UI integration.

2. Implement i18n helper functions similar in spirit to transport:
   - `getDictionary(...)`
   - `resolveLanguageCode(...)`
   - `getStoredLanguageCode(...)`
   - `setStoredLanguageCode(...)`
   - `t(...)`

3. Add a local storage key for the selected Checking Web language.
   - Keep it separate from any transport language storage key.

4. Decide a clean startup flow in `check/app.js`.
   - On initial load, resolve language in this order:
     1. stored user preference;
     2. browser language;
     3. fallback to `pt`.

5. Wire the Settings language dropdown.
   - Populate it from the dedicated language catalog created in Prompt 6A.
   - Respect the exact required order defined there:
     1. `Chinese`
     2. `English`
     3. `Indonesian`
     4. `Malay`
     5. `Portuguese`
     6. `Tagalog (Filipino)`
   - When the user changes language:
     - persist the new choice;
     - update the current UI texts;
     - avoid a full page reload if feasible.

6. Wire the runtime so it can render **all visible user-facing labels** defined in the dedicated dictionary file.
   - This prompt must not stop at the Settings shell if other currently implemented `check` screens still show hardcoded labels.
   - Minimum enforcement scope:
     - main auth labels;
     - Settings modal labels;
     - password dialog title/button labels;
     - registration dialog title and key helper texts;
     - common status messages related to login, registration, password, support, and location;
     - About / Support / Allow Location / Reset Password labels;
     - transport-screen labels that are already rendered inside the `check` surface;
     - any other currently implemented visible labels whose dictionary keys were created in Prompt 6A.

7. Keep the implementation maintainable.
   - Avoid scattering raw translated text replacements throughout the app.
   - Centralize labels and use helper functions where possible.

### Constraints

1. Do not create a direct dependency on the transport runtime.
2. Do not implement the translation layer in a fragmented way that leaves major `check` screens permanently hardcoded after this phase; the end goal is full visible-label coverage for the currently implemented web-application screens.
3. Preserve the current backend API responses; frontend translation may wrap or reinterpret visible messages, but should not require backend contract changes for this prompt.

### Acceptance criteria

1. `Checking Web` has its own `i18n.js`.
2. `Checking Web` consumes a dedicated external dictionary file instead of hardcoding dictionaries in `app.js`.
3. Settings displays a working language dropdown in the required exact order.
4. Language selection persists in local storage.
5. All currently implemented visible labels backed by the dedicated dictionary source update to the selected language.

### Tests to update or add

Add or update tests that verify:

1. the language dropdown is populated with the expected languages;
2. a stored language preference is restored;
3. changing the dropdown updates core labels;
4. the new i18n file is loaded by the `check` surface;
5. the i18n runtime consumes the dedicated dictionary source file;
6. Indonesian is present in the supported language set.


## Phase 7 - Build the Manual Surface

### Prompt 7 - Create the dedicated Checking Web manual page and connect it to the static surface

**Prompt for the AI agent**

Create a dedicated manual surface for `Checking Web` so the About button opens a complete documentation page owned by the `check` frontend.

### Goal

Create a new static manual page that lives alongside the `Checking Web` surface and is designed to receive real snapshots in the next prompt.

### Required files to inspect first

1. `sistema/app/main.py`
2. `sistema/app/static/check/index.html`
3. any static structure patterns already used in:
   - `sistema/app/static/transport`
   - `sistema/app/static/admin`

### New files recommended

1. `sistema/app/static/check/manual.html`
2. `sistema/app/static/check/manual.css`
3. `sistema/app/static/check/manual.js`
4. `sistema/app/static/check/manual-assets/` (directory)

### Required implementation details

1. Create a standalone manual page under the existing `check` static surface.
   - It should be reachable from the About action without backend routing changes if possible.
   - Prefer a relative static page strategy compatible with the current `/user` surface.

2. Build the page structure for a complete user manual.
   - Include clear sections for:
     - overview;
     - authentication flow;
     - automatic user registration;
     - automatic password registration;
     - login;
     - check-in / check-out;
     - project selection;
     - location permission and geolocation behavior;
     - automatic activities;
     - transport access;
     - password reset/change;
     - settings;
     - support;
     - common problems / FAQ.

3. Make the page visually intentional and readable.
   - Do not create a bare dump of text.
   - Use headings, short paragraphs, lists, callouts, and screenshot blocks.
   - Keep it mobile-friendly.

4. Prepare snapshot slots with stable filenames.
   - Even before real images are inserted, the markup should establish exactly where each snapshot belongs.
   - Use consistent filenames in `manual-assets/`, for example:
     - `auth-shell.png`
     - `user-registration.png`
     - `password-registration.png`
     - `settings-modal.png`
     - `password-change.png`
     - `location-denied.png`
     - `location-granted.png`
     - `project-selection.png`
     - `transport-screen.png`
     - `check-success.png`

5. Add alt text for every manual image slot.
   - The manual must be accessible and still understandable if images fail to load.

6. If you decide to use the new i18n system here, do so carefully.
   - At minimum, the page must be complete in English or Portuguese consistently.
   - If multilingual support is too large for this prompt, structure the page to support it later.

### Constraints

1. Do not rely on backend API changes for the manual page.
2. Do not leave the About button targeting an undefined path.
3. Do not postpone the page structure itself; this prompt must produce a real manual surface in code.

### Acceptance criteria

1. A dedicated manual page exists under `sistema/app/static/check`.
2. The About action can open it reliably.
3. The page contains all core sections of the manual.
4. The page includes clear image slots/placeholders for the required snapshots.

### Tests to update or add

Add or update tests that verify:

1. the manual page exists;
2. the About action points to it;
3. required core sections are present in the manual markup.


## Phase 8 - Capture and Integrate Real Snapshots

### Prompt 8 - Replace placeholder screenshot slots with real Checking Web snapshots and finalize the manual

**Prompt for the AI agent**

Now that the UI and manual structure exist, populate the manual with **real snapshots** of the implemented `Checking Web` interface states.

### Goal

Deliver the “About” manual as a real user-facing guide with actual screenshots of the live interface, not conceptual placeholders.

### Required files to inspect first

1. `sistema/app/static/check/manual.html`
2. `sistema/app/static/check/manual.css`
3. `sistema/app/static/check/manual-assets/`
4. the final implemented `Checking Web` UI files after earlier prompts are complete

### Required snapshot inventory

Capture and integrate real images for at least these states:

1. main auth shell;
2. automatic user registration dialog;
3. automatic password registration dialog;
4. Settings modal;
5. password change dialog from Settings;
6. location denied / missing permission state;
7. location granted / healthy location state;
8. project selection area;
9. transport screen;
10. successful check-in or check-out state.

### Required implementation details

1. Use real screenshots of the current implemented interface.
   - Do not use sketches, generated mockups, or generic placeholders.
   - The screenshots should reflect the real final UI state.

2. Save the screenshots into the repository under the manual assets directory.
   - Use stable and readable filenames.
   - Keep file sizes reasonable for web delivery.

3. Update `manual.html` so each snapshot slot points to the real final asset.
   - Make sure all `img` tags load correctly from the static surface.
   - Preserve useful `alt` text.

4. If needed, adjust `manual.css`.
   - Make screenshot blocks readable on mobile.
   - Prevent giant unbounded images.
   - Support side-by-side or stacked layout only if it remains mobile-safe.

5. Review the written manual text against the final UI.
   - Update wording if the implemented UI labels differ from earlier placeholders.
   - Keep the manual truthful to the actual app.

### Constraints

1. Do not leave broken image references.
2. Do not include sensitive or personal data in screenshots.
3. If you need example keys or example projects in screenshots, use intentionally fake or controlled sample data.

### Acceptance criteria

1. The manual displays real screenshots from the actual implemented app.
2. All screenshot file references resolve correctly.
3. The written instructions match the final UI.

### Tests to update or add

Add or update tests that verify:

1. each required manual asset reference exists;
2. the manual page references the expected snapshot filenames;
3. no broken paths remain in the manual markup.


## Phase 9 - Update and Expand Automated Test Coverage

### Prompt 9 - Update the existing test suite to reflect the new Settings-based UX and automatic auth dialogs

**Prompt for the AI agent**

Perform the test refactor needed to support the new `Checking Web` architecture after the Settings and automatic registration changes.

### Goal

Bring automated coverage in line with the new UI and interaction model so regressions are caught automatically.

### Required files to inspect first

1. `tests/check_registration_widget.test.js`
2. `tests/check_auth_transport_ui.test.js`
3. `tests/check_user_location_ui.test.js`
4. `tests/web_client_state.test.js`
5. `tests/test_api_flow.py`

### Required implementation details

1. Update tests that still assume the old main-screen password action behavior.
   - Remove or rewrite expectations tied to:
     - `Chave?`
     - `Senha?`
     - the old main-row action button behavior

2. Add coverage for the new Settings entry point.
   - Test that:
     - the settings trigger exists;
     - it uses the gear icon;
     - the Settings modal contains the required controls.

3. Add coverage for moved password-change access.
   - Test that `Reset Password` is now the way the password change dialog is opened from the main shell.

4. Add coverage for the automatic auth dialog behavior.
   - Unknown key opens self-registration automatically.
   - Known key without password opens password registration automatically.
   - Manual close does not immediately reopen the dialog in a loop.

5. Add or extend location-related tests.
   - Ensure the new Settings location action participates correctly in permission state handling.

6. Add or extend support/manual tests.
   - Validate the WhatsApp URL pattern.
   - Validate the manual page existence and screenshot references.

7. Keep backend API tests focused.
   - If no backend contract changes were made, avoid unnecessary churn in Python API tests.
   - Only update them if visible outputs or expected integration behavior actually changed.

### Constraints

1. Prefer updating existing `check` tests rather than scattering redundant new files everywhere.
2. Keep tests readable and aligned with current repository style.
3. Do not lower coverage just to make the suite pass.

### Acceptance criteria

1. The `check`-focused frontend test suite reflects the new Settings-based UX.
2. Obsolete expectations about `Chave?` / `Senha?` are removed or rewritten.
3. Automatic dialog behavior and Settings behavior are covered by tests.


## Phase 10 - Final Integration, Cleanup, and Regression Sweep

### Prompt 10 - Perform the final integration pass and remove obsolete code paths safely

**Prompt for the AI agent**

Do the final cleanup and regression sweep after all earlier prompts have landed. This is the integration pass that makes the implementation production-ready.

### Goal

Ensure the `Checking Web` codebase is internally consistent after the refactor, with no stale assumptions, dead UI paths, or broken assets.

### Required files to inspect first

1. `sistema/app/static/check/index.html`
2. `sistema/app/static/check/app.js`
3. `sistema/app/static/check/styles.css`
4. `sistema/app/static/check/web-client-state.js`
5. `sistema/app/static/check/i18n.js`
6. `sistema/app/static/check/manual.html`
7. all updated `check` tests

### Required implementation details

1. Remove obsolete code paths that are no longer valid.
   - Search for stale references to:
     - the old main password action button;
     - `Chave?` / `Senha?` label behavior in the main row;
     - dead helper functions no longer used after the refactor.

2. Keep code removal safe.
   - Do not remove shared logic that is still used by password registration or password change.
   - Remove only what has genuinely become obsolete.

3. Validate all modal interactions together.
   - Password dialog
   - Registration dialog
   - Settings dialog
   - Transport screen
   - Ensure they do not conflict in focus, locking, or `Escape` handling.

4. Validate mobile behavior after all changes.
   - auth row alignment;
   - settings icon size and tapability;
   - settings modal scroll behavior;
   - manual page readability on narrow screens.

5. Validate translation completeness for the new UI shell.
   - Ensure there are no obvious untranslated labels in the new Settings experience.

6. Validate the manual integration end-to-end.
   - About opens manual;
   - manual images load;
   - no broken paths remain.

7. Produce a concise integration summary.
   - List changed files.
   - List removed obsolete behaviors.
   - List tests run and results.

### Constraints

1. Do not introduce new behavior in this pass unless required to fix a regression.
2. Keep the cleanup deliberate and minimal-risk.

### Acceptance criteria

1. No stale main-button auth-state UX remains.
2. All new surfaces work together without modal-state conflicts.
3. The manual and Settings surfaces are integrated cleanly.
4. The codebase is cleaner than before, not more fragmented.


## Recommended execution order

Run the prompts in this order:

1. Prompt 1
2. Prompt 2
3. Prompt 3
4. Prompt 4
5. Prompt 5
6. Prompt 6A
7. Prompt 6
8. Prompt 7
9. Prompt 8
10. Prompt 9
11. Prompt 10

This order is important because:

1. the Settings shell must exist before its actions are wired;
2. the password-change entry point should move before old auth-button logic is fully removed;
3. the automatic auth flows should stabilize before the manual and screenshots are finalized;
4. the dedicated dictionary source should exist before the runtime i18n layer is finalized;
5. test refactors are easier and safer once the UI behavior is mostly stable.
