(function (root, factory) {
  const exported = factory();

  if (typeof module === 'object' && module.exports) {
    module.exports = exported;
  }

  root.CheckingWebClientState = exported;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
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

  function shouldAttemptSilentLocationLookup(permissionState, hasPersistedGrant) {
    if (permissionState === 'denied') {
      return false;
    }

    if (permissionState === 'granted') {
      return true;
    }

    return Boolean(hasPersistedGrant);
  }

  function resolvePersistedUserSettings(settingsByChave, chave, defaults) {
    const normalizedChave = sanitizeSettingsChave(chave);
    const safeDefaults = defaults || {};
    const fallbackProject = safeDefaults.project || 'P80';
    const fallbackAutomaticActivitiesEnabled = Boolean(safeDefaults.automaticActivitiesEnabled);
    if (normalizedChave.length !== 4) {
      return {
        project: fallbackProject,
        automaticActivitiesEnabled: fallbackAutomaticActivitiesEnabled,
      };
    }

    const record = settingsByChave && typeof settingsByChave === 'object'
      ? settingsByChave[normalizedChave]
      : null;
    const allowedProjects = Array.isArray(safeDefaults.allowedProjects)
      ? safeDefaults.allowedProjects
      : [];

    return {
      project: normalizeProjectValue(record && record.project, allowedProjects, fallbackProject),
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
    currentMap[normalizedChave] = {
      project: normalizeProjectValue(
        nextSettings && nextSettings.project,
        allowedProjects,
        safeDefaults.project || 'P80'
      ),
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
    shouldAttemptSilentLocationLookup,
    resolvePersistedUserSettings,
    withPersistedUserSettings,
  };
});