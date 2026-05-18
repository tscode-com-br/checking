  function getDictionaryForLanguage(languageCode) {
    if (transportI18n && typeof transportI18n.getDictionary === "function") {
      return transportI18n.getDictionary(languageCode);
    }

    if (transportI18n && transportI18n.dictionaries && transportI18n.dictionaries[languageCode]) {
      return transportI18n.dictionaries[languageCode];
    }

    return (transportI18n && transportI18n.dictionaries && transportI18n.dictionaries[TRANSPORT_DEFAULT_LANGUAGE]) || {};
  }

  function resolveStoredLanguageCode() {
    if (!globalScope.localStorage) {
      return TRANSPORT_DEFAULT_LANGUAGE;
    }

    try {
      const storedValue = String(globalScope.localStorage.getItem(TRANSPORT_LANGUAGE_STORAGE_KEY) || "").trim();
      return transportLanguages.some(function (item) {
        return item.code === storedValue;
      }) ? storedValue : TRANSPORT_DEFAULT_LANGUAGE;
    } catch (error) {
      return TRANSPORT_DEFAULT_LANGUAGE;
    }
  }

  const transportLanguageState = {
    currentCode: resolveStoredLanguageCode(),
  };

  function setStoredLanguageCode(languageCode) {
    if (!globalScope.localStorage) {
      return;
    }

    try {
      globalScope.localStorage.setItem(TRANSPORT_LANGUAGE_STORAGE_KEY, languageCode);
    } catch (error) {}
  }

  function resolveLanguageCode(languageCode) {
    return transportLanguages.some(function (item) {
      return item.code === languageCode;
    }) ? languageCode : TRANSPORT_DEFAULT_LANGUAGE;
  }

  function getActiveLanguageCode() {
    return resolveLanguageCode(transportLanguageState.currentCode);
  }

  function setActiveLanguageCode(languageCode) {
    const resolvedCode = resolveLanguageCode(languageCode);
    transportLanguageState.currentCode = resolvedCode;
    setStoredLanguageCode(resolvedCode);
    return resolvedCode;
  }

  function getLanguageConfig(languageCode) {
    const resolvedCode = resolveLanguageCode(languageCode);
    const matchedLanguage = transportLanguages.find(function (item) {
      return item.code === resolvedCode;
    });
    return matchedLanguage || transportLanguages[0];
  }

  function readTranslationValue(dictionary, keyPath) {
    return String(keyPath || "")
      .split(".")
      .reduce(function (currentValue, segment) {
        if (!currentValue || typeof currentValue !== "object") {
          return undefined;
        }
        return currentValue[segment];
      }, dictionary);
  }

  function interpolateTranslation(template, values) {
    if (typeof template !== "string") {
      return "";
    }

    return template.replace(/\{(\w+)\}/g, function (_, token) {
      if (!values || values[token] === undefined || values[token] === null) {
        return "";
      }
      return String(values[token]);
    });
  }

  function t(keyPath, values, languageCode) {
    const dictionary = getDictionaryForLanguage(resolveLanguageCode(languageCode || getActiveLanguageCode()));
    const fallbackDictionary = getDictionaryForLanguage(TRANSPORT_DEFAULT_LANGUAGE);
    const template = readTranslationValue(dictionary, keyPath);
    const fallbackTemplate = readTranslationValue(fallbackDictionary, keyPath);
    return interpolateTranslation(template !== undefined ? template : fallbackTemplate !== undefined ? fallbackTemplate : keyPath, values);
  }

  function getResolvedTranslationOrNull(keyPath, values, languageCode) {
    const normalizedKeyPath = String(keyPath || "").trim();
    if (!normalizedKeyPath) {
      return null;
    }

    const translatedValue = t(normalizedKeyPath, values, languageCode);
    return translatedValue === normalizedKeyPath ? null : translatedValue;
  }

  function applyTranslatedAttribute(element, attributeName, keyPath, values, languageCode) {
    if (!element || typeof element.setAttribute !== "function") {
      return;
    }

    const translatedValue = getResolvedTranslationOrNull(keyPath, values, languageCode);
    if (translatedValue === null) {
      return;
    }

    element.setAttribute(attributeName, translatedValue);
    if (attributeName in element) {
      element[attributeName] = translatedValue;
    }
  }

  function applyDeclarativeTranslations(rootElement, languageCode) {
    const translationRoot = rootElement || (typeof document !== "undefined" ? document : null);
    const resolvedLanguageCode = resolveLanguageCode(languageCode || getActiveLanguageCode());
    if (!translationRoot || typeof translationRoot.querySelectorAll !== "function") {
      return;
    }

    translationRoot.querySelectorAll("[data-i18n-text]").forEach(function (element) {
      const translatedValue = getResolvedTranslationOrNull(element.dataset.i18nText, undefined, resolvedLanguageCode);
      if (translatedValue === null) {
        return;
      }
      element.textContent = translatedValue;
    });

    translationRoot.querySelectorAll("[data-i18n-aria-label]").forEach(function (element) {
      applyTranslatedAttribute(
        element,
        "aria-label",
        element.dataset.i18nAriaLabel,
        undefined,
        resolvedLanguageCode
      );
    });

    translationRoot.querySelectorAll("[data-i18n-aria]").forEach(function (element) {
      applyTranslatedAttribute(
        element,
        "aria-label",
        element.dataset.i18nAria,
        undefined,
        resolvedLanguageCode
      );
    });

    translationRoot.querySelectorAll("[data-i18n-placeholder]").forEach(function (element) {
      applyTranslatedAttribute(
        element,
        "placeholder",
        element.dataset.i18nPlaceholder,
        undefined,
        resolvedLanguageCode
      );
    });

    translationRoot.querySelectorAll("[data-i18n-title]").forEach(function (element) {
      applyTranslatedAttribute(
        element,
        "title",
        element.dataset.i18nTitle,
        undefined,
        resolvedLanguageCode
      );
    });

    translationRoot.querySelectorAll("[data-i18n-option]").forEach(function (element) {
      const translatedValue = getResolvedTranslationOrNull(element.dataset.i18nOption, undefined, resolvedLanguageCode);
      if (translatedValue === null) {
        return;
      }
      element.textContent = translatedValue;
    });
  }

  function applyDocumentLanguageMetadata(languageCode) {
    if (typeof document === "undefined" || !document.documentElement) {
      return;
    }

    const resolvedLanguageCode = resolveLanguageCode(languageCode || getActiveLanguageCode());
    document.documentElement.lang = resolvedLanguageCode;
    if (typeof document.documentElement.setAttribute === "function") {
      document.documentElement.setAttribute("lang", resolvedLanguageCode);
    }
    const documentTitle = getResolvedTranslationOrNull("document.title", undefined, resolvedLanguageCode);
    if (documentTitle !== null) {
      document.title = documentTitle;
    }
  }

  function applyInitialDeclarativeTranslations() {
    if (typeof document === "undefined") {
      return;
    }

    applyDocumentLanguageMetadata();
    applyDeclarativeTranslations(document);
  }

  function getTransportLockedMessage() {
    return t("status.locked");
  }

  function getTransportSessionExpiredMessage() {
    return t("status.sessionExpired");
  }

  function getDefaultStatusMessage() {
    return t(DEFAULT_STATUS_MESSAGE_KEY);
  }

