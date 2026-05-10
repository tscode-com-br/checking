(function (root) {
  const checkI18n = root.CheckingWebI18n;

  if (!checkI18n || typeof document === 'undefined') {
    return;
  }

  const manualLanguageBadge = document.getElementById('manualLanguageBadge');
  const supportedManualLanguages = new Set(['pt', 'en']);

  function resolveManualLanguageCode() {
    const preferredLanguageCode = checkI18n.resolveInitialLanguageCode();
    if (supportedManualLanguages.has(preferredLanguageCode)) {
      return preferredLanguageCode;
    }
    return 'pt';
  }

  function applyTextTranslations(languageCode) {
    const translatedElements = document.querySelectorAll('[data-i18n]');
    translatedElements.forEach(function (element) {
      const translationKey = element.getAttribute('data-i18n');
      if (!translationKey) {
        return;
      }
      element.textContent = checkI18n.t(translationKey, null, languageCode);
    });
  }

  function applyAttributeTranslations(languageCode) {
    const altTranslatedElements = document.querySelectorAll('[data-i18n-alt]');
    altTranslatedElements.forEach(function (element) {
      const translationKey = element.getAttribute('data-i18n-alt');
      if (!translationKey) {
        return;
      }
      element.setAttribute('alt', checkI18n.t(translationKey, null, languageCode));
    });

    const ariaTranslatedElements = document.querySelectorAll('[data-i18n-aria-label]');
    ariaTranslatedElements.forEach(function (element) {
      const translationKey = element.getAttribute('data-i18n-aria-label');
      if (!translationKey) {
        return;
      }
      element.setAttribute('aria-label', checkI18n.t(translationKey, null, languageCode));
    });
  }

  function applyManualLanguage(languageCode) {
    const resolvedLanguageCode = supportedManualLanguages.has(languageCode)
      ? languageCode
      : 'pt';
    const languageMetadata = checkI18n.getLanguage(resolvedLanguageCode);

    document.documentElement.lang = languageMetadata.locale || resolvedLanguageCode;
    document.title = checkI18n.t('document.manualTitle', null, resolvedLanguageCode);
    applyTextTranslations(resolvedLanguageCode);
    applyAttributeTranslations(resolvedLanguageCode);

    if (manualLanguageBadge) {
      manualLanguageBadge.textContent = languageMetadata.nativeLabel || languageMetadata.label || resolvedLanguageCode;
    }
  }

  applyManualLanguage(resolveManualLanguageCode());
})(typeof globalThis !== 'undefined' ? globalThis : this);
