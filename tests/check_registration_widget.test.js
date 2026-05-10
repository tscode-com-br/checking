const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const checkI18nDictionaries = require('../sistema/app/static/check/i18n-dictionaries.js');
const checkI18nRuntimeSource = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/i18n.js'),
  'utf8'
);

const checkCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/styles.css'),
  'utf8'
);

function loadCheckI18nRuntime(options = {}) {
  const storageState = new Map(Object.entries(options.storage || {}));
  const localStorage = {
    getItem(key) {
      return storageState.has(key) ? storageState.get(key) : null;
    },
    setItem(key, value) {
      storageState.set(key, String(value));
    },
  };
  const context = {
    module: { exports: {} },
    exports: {},
    CheckingWebI18nDictionaries: checkI18nDictionaries,
    navigator: options.navigator || { language: 'en-US', languages: ['en-US'] },
    localStorage,
  };
  context.globalThis = context;
  vm.runInNewContext(checkI18nRuntimeSource, context, {
    filename: 'check/i18n.js',
  });
  return {
    runtime: context.module.exports,
    storageState,
  };
}

test('check page keeps the request-registration trigger hidden and exposes the settings shell structure', () => {
  const checkHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/check/index.html'),
    'utf8'
  );
  const manualEntryExists = fs.existsSync(
    path.join(__dirname, '../sistema/app/static/check/manual.html')
  );

  assert.match(checkHtml, /id="requestRegistrationButton"[^>]*hidden[^>]*aria-hidden="true"/);
  assert.match(checkHtml, />Solicitar cadastro</);
  assert.match(checkHtml, /id="settingsButton"[\s\S]*aria-controls="settingsDialog"[\s\S]*aria-expanded="false"/);
  assert.match(checkHtml, /class="auth-settings-slot"/);
  assert.match(checkHtml, /class="settings-trigger-icon"[\s\S]*viewBox="0 0 24 24"/);
  assert.match(checkHtml, /id="settingsDialogTitle">Ajustes</);
  assert.match(checkHtml, /id="settingsLanguageSelect"/);
  assert.match(checkHtml, /id="settingsResetPasswordButton"[\s\S]*>Resetar Senha</);
  assert.match(checkHtml, /id="settingsLocationPermissionButton"[\s\S]*>Permitir localização</u);
  assert.match(checkHtml, /id="settingsSupportButton"[\s\S]*>Suporte</);
  assert.match(checkHtml, /id="settingsAboutButton"[\s\S]*>Sobre</);
  assert.match(checkHtml, /id="settingsDialogBackButton"[\s\S]*>Voltar</);
  assert.match(checkHtml, /id="registrationDialogTitle">Solicitar Cadastro</);
  assert.match(checkHtml, /id="registrationProjectHint"/);
  assert.match(checkHtml, /id="registrationProjectOptions"/);
  assert.doesNotMatch(checkHtml, /id="registrationProjectSelect"/);
  assert.match(checkHtml, /id="registrationEmailInput"[\s\S]*placeholder="Opcional"/);
  assert.match(checkHtml, /id="registrationDialogSubmitButton"[\s\S]*>Enviar</);
  assert.match(checkHtml, /id="passwordDialogOldPasswordField"/);
  assert.doesNotMatch(checkHtml, /id="registrationAddressInput"/);
  assert.doesNotMatch(checkHtml, /id="registrationZipInput"/);
  assert.equal(manualEntryExists, true);
});

test('check manual page exposes the dedicated static manual surface with final screenshot assets', () => {
  const manualHtmlPath = path.join(__dirname, '../sistema/app/static/check/manual.html');
  const manualCssPath = path.join(__dirname, '../sistema/app/static/check/manual.css');
  const manualScriptPath = path.join(__dirname, '../sistema/app/static/check/manual.js');
  const manualHtml = fs.readFileSync(manualHtmlPath, 'utf8');
  const expectedSnapshotFiles = [
    'auth-shell.png',
    'user-registration.png',
    'password-registration.png',
    'settings-modal.png',
    'password-change.png',
    'location-denied.png',
    'location-granted.png',
    'project-selection.png',
    'transport-screen.png',
    'check-success.png',
  ];

  assert.equal(fs.existsSync(manualHtmlPath), true);
  assert.equal(fs.existsSync(manualCssPath), true);
  assert.equal(fs.existsSync(manualScriptPath), true);
  assert.match(manualHtml, /<link rel="stylesheet" href="manual\.css">/);
  assert.match(manualHtml, /<script src="i18n-dictionaries\.js"><\/script>\s*<script src="i18n\.js"><\/script>\s*<script src="manual\.js"><\/script>/);
  assert.match(manualHtml, /id="manual-overview"/);
  assert.match(manualHtml, /id="manual-auth-flow"/);
  assert.match(manualHtml, /id="manual-user-registration"/);
  assert.match(manualHtml, /id="manual-password-registration"/);
  assert.match(manualHtml, /id="manual-login"/);
  assert.match(manualHtml, /id="manual-attendance"/);
  assert.match(manualHtml, /id="manual-project-selection"/);
  assert.match(manualHtml, /id="manual-location"/);
  assert.match(manualHtml, /id="manual-automatic-activities"/);
  assert.match(manualHtml, /id="manual-transport"/);
  assert.match(manualHtml, /id="manual-password-change"/);
  assert.match(manualHtml, /id="manual-settings"/);
  assert.match(manualHtml, /id="manual-support"/);
  assert.match(manualHtml, /id="manual-faq"/);
  assert.doesNotMatch(manualHtml, /manual-shot-meta/);
  assert.doesNotMatch(manualHtml, /manual-shot-badge/);
  assert.doesNotMatch(manualHtml, /manual\.snapshotSlotLabel/);
  assert.doesNotMatch(manualHtml, /<code>manual-assets\//);

  const assetHashes = new Set();
  expectedSnapshotFiles.forEach((filename) => {
    assert.match(manualHtml, new RegExp(`manual-assets/${filename.replace('.', '\\.')}`));
    const assetPath = path.join(__dirname, '../sistema/app/static/check/manual-assets', filename);
    assert.equal(
      fs.existsSync(assetPath),
      true,
      `Expected final manual asset ${filename} to exist`
    );
    const assetBuffer = fs.readFileSync(assetPath);
    assetHashes.add(crypto.createHash('sha256').update(assetBuffer).digest('hex'));
  });

  assert.equal(assetHashes.size, expectedSnapshotFiles.length);
});

test('check page loads the dedicated dictionary and i18n runtime before app.js', () => {
  const checkHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/check/index.html'),
    'utf8'
  );

  assert.match(
    checkHtml,
    /<script src="i18n-dictionaries\.js"><\/script>\s*<script src="i18n\.js"><\/script>\s*<script src="transport-screen\.js"><\/script>\s*<script src="app\.js"><\/script>/
  );
});

test('check page styles the settings trigger and settings modal shell for mobile-friendly layout', () => {
  assert.match(checkCss, /\.settings-trigger-button \{[\s\S]*min-height: var\(--control-height\)|[\s\S]*display: inline-flex;/);
  assert.match(checkCss, /\.settings-trigger-icon \{[\s\S]*object-fit:\s*contain;/);
  assert.match(checkCss, /\.auth-settings-slot \{[\s\S]*justify-content:\s*center;/);
  assert.match(checkCss, /\.settings-dialog-card \{[\s\S]*width:\s*min\(100%, 460px\);/);
  assert.match(checkCss, /\.settings-option-row-language \{[\s\S]*max-width:\s*min\(100%, 280px\);/);
  assert.match(checkCss, /\.settings-option-row-action \{[\s\S]*justify-items:\s*center;/);
  assert.match(checkCss, /\.settings-option-action \{[\s\S]*white-space:\s*nowrap;/);
  assert.match(checkCss, /\.settings-dialog-actions \{[\s\S]*grid-template-columns:\s*1fr;/);
});

test('check page wires the settings modal lifecycle and routes reset password through the existing password dialog', () => {
  const checkScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/check/app.js'),
    'utf8'
  );

  assert.match(checkScript, /const settingsButton = document\.getElementById\('settingsButton'\);/);
  assert.match(checkScript, /const settingsDialogBackdrop = document\.getElementById\('settingsDialogBackdrop'\);/);
  assert.match(checkScript, /const settingsDialogBackButton = document\.getElementById\('settingsDialogBackButton'\);/);
  assert.match(checkScript, /const settingsResetPasswordButton = document\.getElementById\('settingsResetPasswordButton'\);/);
  assert.match(checkScript, /const settingsLocationPermissionButton = document\.getElementById\('settingsLocationPermissionButton'\);/);
  assert.match(checkScript, /const settingsSupportButton = document\.getElementById\('settingsSupportButton'\);/);
  assert.match(checkScript, /const settingsAboutButton = document\.getElementById\('settingsAboutButton'\);/);
  assert.match(checkScript, /const checkingWebSupportWhatsAppPhone = '5521992174446';/);
  assert.match(checkScript, /const checkingWebManualPath = '\.\/manual\.html';/);
  assert.match(checkScript, /function isSettingsDialogOpen\(\) \{[\s\S]*!settingsDialog\.hidden[\s\S]*\}/);
  assert.match(checkScript, /return isPasswordDialogOpen\(\) \|\| isRegistrationDialogOpen\(\) \|\| isSettingsDialogOpen\(\) \|\| isTransportScreenOpen\(\);/);
  assert.match(checkScript, /function openSettingsDialog\(\) \{[\s\S]*settingsDialog\.hidden = false;[\s\S]*settingsDialogBackdrop\.hidden = false;[\s\S]*settingsButton\.setAttribute\('aria-expanded', 'true'\);/);
  assert.match(checkScript, /function closeSettingsDialog\(options\) \{[\s\S]*settingsDialog\.hidden = true;[\s\S]*settingsDialogBackdrop\.hidden = true;[\s\S]*settingsButton\.setAttribute\('aria-expanded', 'false'\);/);
  assert.match(checkScript, /function canOpenPasswordChangeFromSettings\(\) \{[\s\S]*authState\.hasPassword[\s\S]*isApplicationUnlocked\(\);[\s\S]*\}/);
  assert.match(checkScript, /function resolveSupportRequestChave\(\) \{[\s\S]*authState\.authenticated[\s\S]*sanitizeChave\(authState\.chave\)[\s\S]*getActiveChave\(\)[\s\S]*\}/);
  assert.match(checkScript, /function canOpenSupportFromSettings\(\) \{[\s\S]*resolveSupportRequestChave\(\)\.length === 4[\s\S]*\}/);
  assert.match(checkScript, /function buildCheckingWebSupportMessage\(chave\) \{[\s\S]*supportKey = sanitizeChave\(chave\);[\s\S]*support\.messageTemplate[\s\S]*Preciso de ajuda com a aplicacao Web\. Minha chave e \$\{supportKey\}\./);
  assert.match(checkScript, /function buildCheckingWebSupportWhatsAppUrl\(chave\) \{[\s\S]*https:\/\/wa\.me\/\${checkingWebSupportWhatsAppPhone}\?text=\${encodeURIComponent\(buildCheckingWebSupportMessage\(chave\)\)}[\s\S]*\}/);
  assert.match(checkScript, /function openCheckingWebSupport\(\) \{[\s\S]*closeSettingsDialog\(\{ restoreFocus: false \}\);[\s\S]*buildCheckingWebSupportWhatsAppUrl\(supportChave\)[\s\S]*\}/);
  assert.match(checkScript, /function openCheckingWebManual\(\) \{[\s\S]*closeSettingsDialog\(\{ restoreFocus: false \}\);[\s\S]*openSecondarySurface\(checkingWebManualPath\);[\s\S]*\}/);
  assert.match(checkScript, /function requestPreciseLocationPermissionFromSettings\(\) \{[\s\S]*resolveCurrentLocation\(\{[\s\S]*interactive: true,[\s\S]*forceRefresh: true,[\s\S]*measurementTrigger: 'settings_permission',[\s\S]*showDetectingState: true,[\s\S]*showCompletionStatus: true,[\s\S]*suppressNotification: false,[\s\S]*\}\)/);
  assert.match(checkScript, /if \(control === settingsButton\) \{[\s\S]*passwordLoginInProgress[\s\S]*\}/);
  assert.match(checkScript, /if \(control === settingsResetPasswordButton\) \{[\s\S]*control\.disabled = !canOpenPasswordChangeFromSettings\(\);[\s\S]*\}/);
  assert.match(checkScript, /if \(control === settingsLocationPermissionButton\) \{[\s\S]*isLocationPermissionEffectivelySharedWithWebApp\(\);[\s\S]*\}/);
  assert.match(checkScript, /if \(control === settingsSupportButton\) \{[\s\S]*control\.disabled = !canOpenSupportFromSettings\(\);[\s\S]*\}/);
  assert.match(checkScript, /settingsButton\.addEventListener\('click', openSettingsDialog\);/);
  assert.match(checkScript, /settingsDialogBackButton\.addEventListener\('click', closeSettingsDialog\);/);
  assert.match(checkScript, /settingsDialogBackdrop\.addEventListener\('click', closeSettingsDialog\);/);
  assert.match(checkScript, /settingsResetPasswordButton\.addEventListener\('click', \(\) => \{[\s\S]*closeSettingsDialog\(\{ restoreFocus: false \}\);[\s\S]*openPasswordDialog\(\);[\s\S]*\}\);/);
  assert.match(checkScript, /settingsLocationPermissionButton\.addEventListener\('click', \(\) => \{[\s\S]*requestPreciseLocationPermissionFromSettings\(\);[\s\S]*\}\);/);
  assert.match(checkScript, /settingsSupportButton\.addEventListener\('click', openCheckingWebSupport\);/);
  assert.match(checkScript, /settingsAboutButton\.addEventListener\('click', openCheckingWebManual\);/);
  assert.match(checkScript, /if \(event\.key === 'Escape' && isSettingsDialogOpen\(\)\) \{[\s\S]*closeSettingsDialog\(\);[\s\S]*return;[\s\S]*\}/);
  assert.doesNotMatch(checkScript, /passwordActionButton\.addEventListener\('click'/);
});

test('check auth flow auto-opens self-registration and password-registration without the old CTA labels', () => {
  const checkScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/check/app.js'),
    'utf8'
  );

  assert.doesNotMatch(checkScript, /function resolvePasswordActionButtonLabel\(/);
  assert.doesNotMatch(checkScript, /return 'Chave\?';/);
  assert.doesNotMatch(checkScript, /return 'Senha\?';/);
  assert.doesNotMatch(checkScript, /requestRegistrationButton\.addEventListener\('click'/);
  assert.match(checkScript, /function resolveAuthenticationAssistanceStateKey\(options\) \{/);
  assert.match(checkScript, /function syncAuthenticationAssistanceAutoOpenState\(options\) \{/);
  assert.match(checkScript, /function markCurrentAuthenticationAssistanceDialogAsManuallyDismissed\(\) \{/);
  assert.match(checkScript, /function maybeAutoOpenAuthenticationAssistanceDialog\(\) \{/);
  assert.match(checkScript, /syncAuthenticationAssistanceAutoOpenState\(\{[\s\S]*found: authState\.found,[\s\S]*hasPassword: authState\.hasPassword,[\s\S]*statusResolved: authState\.statusResolved,[\s\S]*statusErrored: authState\.statusErrored,[\s\S]*\}\);[\s\S]*syncFormControlStates\(\);[\s\S]*maybeAutoOpenAuthenticationAssistanceDialog\(\);/);
  assert.match(checkScript, /if \(shouldResetResolvedKeyState\) \{[\s\S]*resetAuthenticationAssistanceAutoOpenState\(\);[\s\S]*clearTypedPasswordAuthentication\(\);/);
  assert.match(checkScript, /if \(normalizedChave\.length !== 4\) \{[\s\S]*resetAuthenticationAssistanceAutoOpenState\(\);[\s\S]*authState\.chave = '';/);
  assert.match(checkScript, /function dismissPasswordDialogManually\(\) \{[\s\S]*isPasswordRegistrationDialogMode\(\)[\s\S]*markCurrentAuthenticationAssistanceDialogAsManuallyDismissed\(\);[\s\S]*closePasswordDialog\(\);[\s\S]*\}/);
  assert.match(checkScript, /function dismissRegistrationDialogManually\(\) \{[\s\S]*markCurrentAuthenticationAssistanceDialogAsManuallyDismissed\(\);[\s\S]*closeRegistrationDialog\(\);[\s\S]*\}/);
  assert.match(checkScript, /passwordDialogBackButton\.addEventListener\('click', dismissPasswordDialogManually\);/);
  assert.match(checkScript, /registrationDialogBackButton\.addEventListener\('click', dismissRegistrationDialogManually\);/);
  assert.match(checkScript, /routeToUnknownUserSelfRegistration\(normalizedChave\);/);
  assert.match(checkScript, /if \(stateKey\.endsWith\(':missing-user'\)\) \{[\s\S]*openRegistrationDialog\(\);/);
  assert.match(checkScript, /if \(stateKey\.endsWith\(':missing-password'\)\) \{[\s\S]*openPasswordDialog\(\);/);
  assert.match(checkScript, /passwordDialogTitle\.textContent = isRegisterMode[\s\S]*t\('passwordDialog\.titleRegister'\)[\s\S]*t\('passwordDialog\.titleChange'\)/);
  assert.match(checkScript, /passwordDialogOldPasswordField\.classList\.toggle\('is-registration-placeholder', isRegisterMode\);/);
  assert.match(checkScript, /oldPasswordInput\.hidden = isRegisterMode;/);
  assert.match(checkCss, /#passwordDialogOldPasswordField\.is-registration-placeholder span\s*\{[\s\S]*text-decoration:\s*line-through;/);
  assert.match(checkScript, /registerPasswordMode[\s\S]*\?[\s\S]*chave: normalizedChave,[\s\S]*senha: newPassword,[\s\S]*:[\s\S]*senha_antiga: oldPassword,[\s\S]*nova_senha: newPassword,/);
  assert.doesNotMatch(checkScript, /projeto: projectSelect\.value/);
  assert.match(checkScript, /const registrationProjectHint = document\.getElementById\('registrationProjectHint'\);/);
  assert.match(checkScript, /const registrationProjectOptions = document\.getElementById\('registrationProjectOptions'\);/);
  assert.match(checkScript, /const projetos = readSelectedRegistrationProjectValues\(\);/);
  assert.match(checkScript, /body: JSON\.stringify\(\{[\s\S]*chave: normalizedChave,[\s\S]*nome,[\s\S]*projetos,[\s\S]*email: email \|\| null,[\s\S]*senha: password,[\s\S]*confirmar_senha: confirmPassword,[\s\S]*\}\)/);
  assert.match(checkScript, /if \(Array\.isArray\(payload\.projects\) && payload\.projects\.length && payload\.active_project\) \{[\s\S]*applyCurrentUserProjectMemberships\(payload\);[\s\S]*\}/);
  assert.match(checkCss, /\.registration-project-options\s*\{[\s\S]*border:\s*1px solid #cbd5e1;/);
  assert.doesNotMatch(checkScript, /body: JSON\.stringify\(\{[\s\S]*end_rua:/);
  assert.doesNotMatch(checkScript, /body: JSON\.stringify\(\{[\s\S]*zip:/);
  assert.match(checkScript, /t\('registrationDialog\.successStatus'\)/);
});

test('check page exposes a dedicated i18n dictionary source with the required languages, order, and namespaces', () => {
  const expectedLanguageOrder = [
    'Chinese',
    'English',
    'Indonesian',
    'Malay',
    'Portuguese',
    'Tagalog (Filipino)',
  ];
  const expectedLanguageCodes = ['zh', 'en', 'id', 'ms', 'pt', 'tl'];
  const representativeNamespaces = [
    'document',
    'auth',
    'settings',
    'passwordDialog',
    'registrationDialog',
    'location',
    'projects',
    'transport',
    'status',
    'manual',
    'support',
  ];

  assert.equal(checkI18nDictionaries.defaultLanguage, 'pt');
  assert.deepStrictEqual(
    checkI18nDictionaries.languages.map((language) => language.label),
    expectedLanguageOrder
  );
  assert.deepStrictEqual(
    checkI18nDictionaries.languages.map((language) => language.code),
    expectedLanguageCodes
  );

  expectedLanguageCodes.forEach((code) => {
    const dictionary = checkI18nDictionaries.getDictionary(code);
    assert.ok(dictionary, `Expected dictionary for ${code}`);
    representativeNamespaces.forEach((namespace) => {
      assert.ok(dictionary[namespace], `Expected ${namespace} namespace for ${code}`);
    });
  });

  assert.equal(
    checkI18nDictionaries.dictionaries.pt.support.messageTemplate,
    'Preciso de ajuda com a aplicação Checking Web. Minha chave é {chave}.'
  );
  assert.equal(
    checkI18nDictionaries.dictionaries.en.transport.kinds.regular,
    'Weekdays'
  );
  assert.equal(
    checkI18nDictionaries.dictionaries.zh.settings.languageLabel,
    '语言'
  );
  assert.equal(
    checkI18nDictionaries.dictionaries.id.auth.passwordLabel,
    'Kata Sandi'
  );
});

test('check page exposes a dedicated i18n runtime with storage, browser fallback, and translation lookup', () => {
  const storedLanguageLoad = loadCheckI18nRuntime({
    storage: {
      'checking.web.language': 'ms',
    },
    navigator: {
      language: 'en-US',
      languages: ['en-US'],
    },
  });
  const browserFallbackLoad = loadCheckI18nRuntime({
    navigator: {
      language: 'fil-PH',
      languages: ['fil-PH', 'en-US'],
    },
  });

  assert.equal(storedLanguageLoad.runtime.languageStorageKey, 'checking.web.language');
  assert.equal(storedLanguageLoad.runtime.defaultLanguage, 'pt');
  assert.equal(storedLanguageLoad.runtime.getStoredLanguageCode(), 'ms');
  assert.equal(storedLanguageLoad.runtime.getActiveLanguageCode(), 'ms');
  assert.equal(storedLanguageLoad.runtime.t('settings.languageLabel'), 'Bahasa');
  assert.equal(storedLanguageLoad.runtime.resolveLanguageCode('id-ID'), 'id');
  assert.equal(storedLanguageLoad.runtime.resolveLanguageCode('zh-Hans'), 'zh');
  assert.equal(browserFallbackLoad.runtime.resolveInitialLanguageCode(), 'tl');
  assert.equal(browserFallbackLoad.runtime.t('settings.supportLabel'), 'Suporta');
});

test('check app wires the settings language selector to the dedicated i18n runtime and translated UI refresh helpers', () => {
  const checkScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/check/app.js'),
    'utf8'
  );

  assert.match(checkScript, /const checkI18n = window\.CheckingWebI18n;/);
  assert.match(checkScript, /function populateSettingsLanguageOptions\(\) \{[\s\S]*checkI18n\.languages\.forEach/);
  assert.match(checkScript, /function applyLanguageSelection\(languageCode, options\) \{[\s\S]*refreshLocaleFormatters\(\);[\s\S]*syncTranslatedRuntimeLabels\(\);[\s\S]*applyStaticTranslations\(\);/);
  assert.match(checkScript, /settingsLanguageSelect\.addEventListener\('change', \(\) => \{[\s\S]*applyLanguageSelection\(settingsLanguageSelect\.value,[\s\S]*persist:\s*true/);
  assert.match(checkScript, /document\.title = t\('document\.title'\);/);
});
