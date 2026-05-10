(function (root, factory) {
  const exported = factory();

  if (typeof module === 'object' && module.exports) {
    module.exports = exported;
  }

  root.CheckingWebClientState = exported;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const SINGAPORE_TIME_ZONE = 'Asia/Singapore';

  function sanitizeSettingsChave(value) {
    return String(value || '')
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '')
      .slice(0, 4);
  }

  function splitNotificationMessage(message, maxPrimaryLength) {
    const limit = Number.isFinite(maxPrimaryLength) && maxPrimaryLength > 8
      ? Math.floor(maxPrimaryLength)
      : 62;
    const rawText = String(message || '').trim();
    if (!rawText) {
      return { primary: '', secondary: '' };
    }

    const explicitLines = rawText
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
    if (explicitLines.length > 1) {
      return {
        primary: explicitLines[0],
        secondary: explicitLines.slice(1).join(' '),
      };
    }

    const normalized = rawText.replace(/\s+/g, ' ');
    if (normalized.length <= limit) {
      return { primary: normalized, secondary: '' };
    }

    let splitIndex = normalized.lastIndexOf(' ', limit);
    if (splitIndex < Math.floor(limit * 0.55)) {
      splitIndex = normalized.indexOf(' ', limit);
    }
    if (splitIndex === -1) {
      splitIndex = limit;
    }

    return {
      primary: normalized.slice(0, splitIndex).trim(),
      secondary: normalized.slice(splitIndex).trim(),
    };
  }

  function normalizeProjectValue(projectValue, allowedProjects, fallbackProject) {
    const normalizedValue = String(projectValue || '').trim().toUpperCase();
    if (Array.isArray(allowedProjects) && allowedProjects.includes(normalizedValue)) {
      return normalizedValue;
    }
    return fallbackProject;
  }

  function normalizeProjectValues(projectValues, allowedProjects, fallbackProjects) {
    const normalizedAllowedProjects = Array.isArray(allowedProjects)
      ? allowedProjects.map((project) => String(project || '').trim().toUpperCase()).filter(Boolean)
      : [];
    const allowedProjectSet = new Set(normalizedAllowedProjects);
    const normalizedFallbackProjects = Array.isArray(fallbackProjects)
      ? fallbackProjects.map((project) => String(project || '').trim().toUpperCase()).filter(Boolean)
      : [];
    const rawValues = Array.isArray(projectValues)
      ? projectValues
      : [projectValues];
    const normalizedProjects = [];
    const seenProjects = new Set();

    rawValues.forEach((projectValue) => {
      const normalizedValue = String(projectValue || '').trim().toUpperCase();
      if (!normalizedValue || seenProjects.has(normalizedValue)) {
        return;
      }
      if (normalizedAllowedProjects.length && !allowedProjectSet.has(normalizedValue)) {
        return;
      }
      seenProjects.add(normalizedValue);
      normalizedProjects.push(normalizedValue);
    });

    if (normalizedProjects.length) {
      return normalizedProjects;
    }

    return normalizedFallbackProjects.filter((project, index) => normalizedFallbackProjects.indexOf(project) === index);
  }

  function resolveFallbackProjects(defaults) {
    const safeDefaults = defaults || {};
    const allowedProjects = Array.isArray(safeDefaults.allowedProjects)
      ? safeDefaults.allowedProjects
        .map((project) => String(project || '').trim().toUpperCase())
        .filter(Boolean)
      : [];
    const defaultProjects = Array.isArray(safeDefaults.projects)
      ? safeDefaults.projects
      : [safeDefaults.project];
    const normalizedDefaultProjects = defaultProjects
      .map((project) => String(project || '').trim().toUpperCase())
      .filter(Boolean)
      .filter((project, index, values) => values.indexOf(project) === index);
    const filteredDefaults = normalizedDefaultProjects.filter((project) => allowedProjects.includes(project));

    if (filteredDefaults.length) {
      return filteredDefaults;
    }

    if (allowedProjects.length) {
      return allowedProjects;
    }

    return normalizedDefaultProjects;
  }

  function resolveFallbackProject(defaults) {
    return resolveFallbackProjects(defaults)[0] || '';
  }

  function resolveFallbackActiveProject(defaults, fallbackProjects) {
    const normalizedFallbackProjects = Array.isArray(fallbackProjects)
      ? fallbackProjects.map((project) => String(project || '').trim().toUpperCase()).filter(Boolean)
      : [];
    const rawDefaultActiveProject = String(
      (defaults && (defaults.activeProject || defaults.project)) || ''
    ).trim().toUpperCase();

    if (rawDefaultActiveProject && normalizedFallbackProjects.includes(rawDefaultActiveProject)) {
      return rawDefaultActiveProject;
    }

    return normalizedFallbackProjects[0] || rawDefaultActiveProject;
  }

  function shouldAttemptSilentLocationLookup(permissionState, hasPersistedGrant) {
    void hasPersistedGrant;

    if (permissionState === 'denied') {
      return false;
    }

    return true;
  }

  function isPasswordLengthValid(password) {
    const rawPassword = String(password ?? '');
    return rawPassword.length >= 3 && rawPassword.length <= 10 && rawPassword.trim().length > 0;
  }

  function isPasswordVerificationInputValid(password) {
    const rawPassword = String(password ?? '');
    return rawPassword.length >= 1 && rawPassword.length <= 10;
  }

  function autofillPetrobrasEmailDomain(value) {
    const rawValue = String(value ?? '');
    const atIndex = rawValue.indexOf('@');
    if (atIndex === -1) {
      return rawValue;
    }

    const localPart = rawValue.slice(0, atIndex);
    const domainPart = rawValue.slice(atIndex + 1);
    if (!localPart || domainPart.length > 0) {
      return rawValue;
    }

    return `${localPart}@petrobras.com.br`;
  }

  function resolveCalendarDayKey(value, timeZone) {
    if (!value) {
      return '';
    }

    const parsedValue = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(parsedValue.getTime())) {
      return '';
    }

    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone: timeZone || SINGAPORE_TIME_ZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
    return formatter.format(parsedValue);
  }

  function hasCurrentDayCheckIn(historyState, referenceValue, timeZone) {
    if (historyState && typeof historyState.has_current_day_checkin === 'boolean') {
      return historyState.has_current_day_checkin;
    }

    const lastCheckinAt = historyState && historyState.last_checkin_at;
    if (!lastCheckinAt) {
      return false;
    }

    const checkinDayKey = resolveCalendarDayKey(lastCheckinAt, timeZone || SINGAPORE_TIME_ZONE);
    const referenceDayKey = resolveCalendarDayKey(referenceValue || new Date(), timeZone || SINGAPORE_TIME_ZONE);
    return Boolean(checkinDayKey && referenceDayKey && checkinDayKey === referenceDayKey);
  }

  function formatTransportVehicleType(value) {
    switch (String(value || '').trim().toLowerCase()) {
      case 'carro':
        return 'carro';
      case 'minivan':
        return 'minivan';
      case 'van':
        return 'van';
      case 'onibus':
        return 'ônibus';
      default:
        return String(value || '').trim();
    }
  }

  function resolvePersistedPassword(passwordsByChave, chave) {
    const normalizedChave = sanitizeSettingsChave(chave);
    if (normalizedChave.length !== 4) {
      return '';
    }

    const storedPassword = passwordsByChave && typeof passwordsByChave === 'object'
      ? passwordsByChave[normalizedChave]
      : '';
    return isPasswordLengthValid(storedPassword) ? storedPassword : '';
  }

  function withPersistedPassword(passwordsByChave, chave, password) {
    const normalizedChave = sanitizeSettingsChave(chave);
    const currentMap = passwordsByChave && typeof passwordsByChave === 'object'
      ? { ...passwordsByChave }
      : {};
    if (normalizedChave.length !== 4) {
      return currentMap;
    }

    if (isPasswordLengthValid(password)) {
      currentMap[normalizedChave] = String(password);
      return currentMap;
    }

    delete currentMap[normalizedChave];
    return currentMap;
  }

  function resolveAuthenticationPromptMessage(authState) {
    const state = authState && typeof authState === 'object' ? authState : {};

    if (state.authenticated) {
      return '';
    }

    if (state.hasPassword) {
      return 'Digite sua senha para iniciar.';
    }

    return 'Digite sua chave e crie uma senha.';
  }

  function resolvePersistedUserSettings(settingsByChave, chave, defaults) {
    const normalizedChave = sanitizeSettingsChave(chave);
    const safeDefaults = defaults || {};
    const fallbackProjects = resolveFallbackProjects(safeDefaults);
    const fallbackActiveProject = resolveFallbackActiveProject(safeDefaults, fallbackProjects);
    const fallbackAutomaticActivitiesEnabled = Boolean(safeDefaults.automaticActivitiesEnabled);
    if (normalizedChave.length !== 4) {
      return {
        projects: fallbackProjects,
        activeProject: fallbackActiveProject,
        automaticActivitiesEnabled: fallbackAutomaticActivitiesEnabled,
      };
    }

    const record = settingsByChave && typeof settingsByChave === 'object'
      ? settingsByChave[normalizedChave]
      : null;
    const allowedProjects = Array.isArray(safeDefaults.allowedProjects)
      ? safeDefaults.allowedProjects
      : [];
    const resolvedProjects = normalizeProjectValues(
      record && Array.isArray(record.projects) && record.projects.length
        ? record.projects
        : (record && record.project),
      allowedProjects,
      fallbackProjects
    );
    const resolvedActiveProject = normalizeProjectValue(
      record && (record.activeProject || record.project),
      resolvedProjects,
      resolveFallbackActiveProject(safeDefaults, resolvedProjects)
    );

    return {
      projects: resolvedProjects,
      activeProject: resolvedActiveProject,
      automaticActivitiesEnabled:
        record && typeof record.automaticActivitiesEnabled === 'boolean'
          ? record.automaticActivitiesEnabled
          : fallbackAutomaticActivitiesEnabled,
    };
  }

  function withPersistedUserSettings(settingsByChave, chave, nextSettings, defaults) {
    const normalizedChave = sanitizeSettingsChave(chave);
    const safeDefaults = defaults || {};
    if (normalizedChave.length !== 4) {
      return settingsByChave && typeof settingsByChave === 'object' ? { ...settingsByChave } : {};
    }

    const currentMap = settingsByChave && typeof settingsByChave === 'object' ? { ...settingsByChave } : {};
    const allowedProjects = Array.isArray(safeDefaults.allowedProjects)
      ? safeDefaults.allowedProjects
      : [];
    const fallbackProjects = resolveFallbackProjects(safeDefaults);
    const resolvedProjects = normalizeProjectValues(
      nextSettings && Array.isArray(nextSettings.projects) && nextSettings.projects.length
        ? nextSettings.projects
        : (nextSettings && nextSettings.project),
      allowedProjects,
      fallbackProjects
    );
    const resolvedActiveProject = normalizeProjectValue(
      nextSettings && (nextSettings.activeProject || nextSettings.project),
      resolvedProjects,
      resolveFallbackActiveProject(safeDefaults, resolvedProjects)
    );
    currentMap[normalizedChave] = {
      projects: resolvedProjects,
      activeProject: resolvedActiveProject,
      automaticActivitiesEnabled: Boolean(
        nextSettings && nextSettings.automaticActivitiesEnabled
      ),
    };
    return currentMap;
  }

  return {
    sanitizeSettingsChave,
    splitNotificationMessage,
    normalizeProjectValue,
    normalizeProjectValues,
    shouldAttemptSilentLocationLookup,
    isPasswordLengthValid,
    isPasswordVerificationInputValid,
    autofillPetrobrasEmailDomain,
    hasCurrentDayCheckIn,
    formatTransportVehicleType,
    resolvePersistedPassword,
    withPersistedPassword,
    resolveAuthenticationPromptMessage,
    resolvePersistedUserSettings,
    withPersistedUserSettings,
  };
});