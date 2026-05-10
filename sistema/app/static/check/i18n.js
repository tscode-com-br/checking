(function (root, factory) {
  const exported = factory(root);

  if (typeof module === 'object' && module.exports) {
    module.exports = exported;
  }

  root.CheckingWebI18n = exported;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  const dictionarySource = root.CheckingWebI18nDictionaries || {};
  const defaultLanguage = typeof dictionarySource.defaultLanguage === 'string'
    ? dictionarySource.defaultLanguage
    : 'pt';
  const languages = Array.isArray(dictionarySource.languages)
    ? dictionarySource.languages.slice()
    : [];
  const dictionaries = dictionarySource.dictionaries && typeof dictionarySource.dictionaries === 'object'
    ? dictionarySource.dictionaries
    : {};
  const languageStorageKey = 'checking.web.language';
  const languageAliasMap = {
    fil: 'tl',
    tl: 'tl',
    pt: 'pt',
    en: 'en',
    zh: 'zh',
    ms: 'ms',
    id: 'id',
    in: 'id',
  };
  let activeLanguageCode = resolveLanguageCode(
    defaultLanguage,
    languages.length ? languages[0] && languages[0].code : 'pt'
  );

  function resolveSupportedCodes() {
    return languages.map(function (language) {
      return String(language && language.code || '').trim().toLowerCase();
    }).filter(Boolean);
  }

  function resolveLanguageCode(languageCode, fallbackCode) {
    const supportedCodes = resolveSupportedCodes();
    const fallbackWasProvided = fallbackCode !== undefined && fallbackCode !== null;
    const fallback = String(
      fallbackWasProvided ? fallbackCode : (defaultLanguage || supportedCodes[0] || 'pt')
    ).trim().toLowerCase();
    const normalized = String(languageCode || '').trim().toLowerCase();

    if (!normalized) {
      if (!fallback && fallbackWasProvided) {
        return '';
      }
      return supportedCodes.includes(fallback) ? fallback : (supportedCodes[0] || 'pt');
    }

    if (supportedCodes.includes(normalized)) {
      return normalized;
    }

    const baseCode = normalized.split(/[-_]/)[0];
    const aliasedCode = languageAliasMap[normalized] || languageAliasMap[baseCode] || baseCode;
    if (supportedCodes.includes(aliasedCode)) {
      return aliasedCode;
    }

    if (!fallback && fallbackWasProvided) {
      return '';
    }

    return supportedCodes.includes(fallback) ? fallback : (supportedCodes[0] || 'pt');
  }

  function getLanguage(languageCode) {
    const resolvedCode = resolveLanguageCode(languageCode);
    return languages.find(function (language) {
      return language.code === resolvedCode;
    }) || languages[0] || {
      code: resolvedCode,
      label: resolvedCode,
      nativeLabel: resolvedCode,
      locale: 'pt-BR',
    };
  }

  function getDictionary(languageCode) {
    const resolvedCode = resolveLanguageCode(languageCode);
    return dictionaries[resolvedCode] || dictionaries[defaultLanguage] || {};
  }

  function detectBrowserLanguageCode(navigatorObject) {
    const runtimeNavigator = navigatorObject || root.navigator || {};
    const languageCandidates = Array.isArray(runtimeNavigator.languages) && runtimeNavigator.languages.length
      ? runtimeNavigator.languages
      : [runtimeNavigator.language];

    for (let index = 0; index < languageCandidates.length; index += 1) {
      const candidate = resolveLanguageCode(languageCandidates[index], '');
      if (candidate) {
        return candidate;
      }
    }

    return resolveLanguageCode(defaultLanguage);
  }

  function getStoredLanguageCode(storageObject) {
    const runtimeStorage = storageObject || (root.localStorage || null);
    if (!runtimeStorage || typeof runtimeStorage.getItem !== 'function') {
      return '';
    }

    try {
      return resolveLanguageCode(runtimeStorage.getItem(languageStorageKey), '');
    } catch {
      return '';
    }
  }

  function setStoredLanguageCode(languageCode, storageObject) {
    const runtimeStorage = storageObject || (root.localStorage || null);
    const resolvedCode = resolveLanguageCode(languageCode);
    if (!runtimeStorage || typeof runtimeStorage.setItem !== 'function') {
      return resolvedCode;
    }

    try {
      runtimeStorage.setItem(languageStorageKey, resolvedCode);
    } catch {
      // Ignore browsers with unavailable storage.
    }

    return resolvedCode;
  }

  function getActiveLanguageCode() {
    return activeLanguageCode;
  }

  function setActiveLanguageCode(languageCode) {
    activeLanguageCode = resolveLanguageCode(languageCode);
    return activeLanguageCode;
  }

  function resolveInitialLanguageCode(options) {
    const settings = options || {};
    const storedLanguage = settings.skipStoredPreference
      ? ''
      : getStoredLanguageCode(settings.storage);
    if (storedLanguage) {
      return setActiveLanguageCode(storedLanguage);
    }

    const browserLanguage = detectBrowserLanguageCode(settings.navigator);
    if (browserLanguage) {
      return setActiveLanguageCode(browserLanguage);
    }

    return setActiveLanguageCode(defaultLanguage);
  }

  function readTranslationValue(source, keyPath) {
    if (!source || typeof source !== 'object') {
      return undefined;
    }

    const normalizedKeyPath = String(keyPath || '').trim();
    if (!normalizedKeyPath) {
      return undefined;
    }

    return normalizedKeyPath.split('.').reduce(function (currentValue, segment) {
      if (!currentValue || typeof currentValue !== 'object') {
        return undefined;
      }
      return currentValue[segment];
    }, source);
  }

  function interpolateTranslation(template, values) {
    if (typeof template !== 'string' || !values || typeof values !== 'object') {
      return template;
    }

    return template.replace(/\{([^}]+)\}/g, function (_match, token) {
      const resolvedValue = values[token];
      return resolvedValue === undefined || resolvedValue === null
        ? ''
        : String(resolvedValue);
    });
  }

  function t(keyPath, values, languageCode) {
    const resolvedLanguageCode = resolveLanguageCode(languageCode || activeLanguageCode);
    const dictionary = getDictionary(resolvedLanguageCode);
    const fallbackDictionary = getDictionary(defaultLanguage);
    const translatedValue = readTranslationValue(dictionary, keyPath);
    const fallbackValue = translatedValue === undefined
      ? readTranslationValue(fallbackDictionary, keyPath)
      : translatedValue;

    if (typeof fallbackValue === 'string') {
      return interpolateTranslation(fallbackValue, values);
    }

    return fallbackValue === undefined ? String(keyPath || '') : fallbackValue;
  }

  resolveInitialLanguageCode();

  return {
    defaultLanguage,
    dictionaries,
    getActiveLanguageCode,
    getDictionary,
    getLanguage,
    getStoredLanguageCode,
    interpolateTranslation,
    languageStorageKey,
    languages,
    readTranslationValue,
    resolveBrowserLanguageCode: detectBrowserLanguageCode,
    resolveInitialLanguageCode,
    resolveLanguageCode,
    setActiveLanguageCode,
    setStoredLanguageCode,
    t,
  };
});
