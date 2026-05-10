const authShell = document.getElementById("authShell");
const adminShell = document.getElementById("adminShell");
const statusLine = document.getElementById("statusLine");
const authStatus = document.getElementById("authStatus");
const sessionBar = document.getElementById("sessionBar");
const sessionUserLabel = document.getElementById("sessionUserLabel");
const loginChaveInput = document.getElementById("loginChave");
const loginSenhaInput = document.getElementById("loginSenha");
const changePasswordModal = document.getElementById("changePasswordModal");
const changePasswordForm = document.getElementById("changePasswordForm");
const changePasswordCurrentInput = document.getElementById("changePasswordCurrent");
const changePasswordNewInput = document.getElementById("changePasswordNew");
const changePasswordConfirmInput = document.getElementById("changePasswordConfirm");
const changePasswordBackButton = document.getElementById("changePasswordBackButton");
const changePasswordSaveButton = document.getElementById("changePasswordSaveButton");
const changePasswordStatus = document.getElementById("changePasswordStatus");
const requestAdminButton = document.getElementById("requestAdminButton");
const requestAdminModal = document.getElementById("requestAdminModal");
const requestAdminChaveInput = document.getElementById("requestAdminChave");
const requestAdminStatus = document.getElementById("requestAdminStatus");
const requestAdminBackButton = document.getElementById("requestAdminBackButton");
const requestAdminRegistrationModal = document.getElementById("requestAdminRegistrationModal");
const requestAdminRegistrationForm = document.getElementById("requestAdminRegistrationForm");
const requestAdminRegistrationChaveInput = document.getElementById("requestAdminRegistrationChave");
const requestAdminRegistrationNomeInput = document.getElementById("requestAdminRegistrationNome");
const requestAdminRegistrationProjetoSelect = document.getElementById("requestAdminRegistrationProjeto");
const requestAdminRegistrationSenhaInput = document.getElementById("requestAdminRegistrationSenha");
const requestAdminRegistrationConfirmInput = document.getElementById("requestAdminRegistrationConfirm");
const requestAdminRegistrationBackButton = document.getElementById("requestAdminRegistrationBackButton");
const requestAdminRegistrationSaveButton = document.getElementById("requestAdminRegistrationSaveButton");
const requestAdminRegistrationStatus = document.getElementById("requestAdminRegistrationStatus");
const reportsSearchChaveInput = document.getElementById("reportsSearchChave");
const reportsSearchNomeInput = document.getElementById("reportsSearchNome");
const reportsClearButton = document.getElementById("reportsClearButton");
const reportsSearchButton = document.getElementById("reportsSearchButton");
const reportsExportButton = document.getElementById("reportsExportButton");
const reportsExportAllButton = document.getElementById("reportsExportAllButton");
const reportsStatus = document.getElementById("reportsStatus");
const projectEditorTitle = document.getElementById("projectEditorTitle");
const projectEditorHelp = document.getElementById("projectEditorHelp");
const projectNameInput = document.getElementById("projectNameInput");
const projectAddressInput = document.getElementById("projectAddressInput");
const projectZipCodeInput = document.getElementById("projectZipCodeInput");
const projectCountrySelect = document.getElementById("projectCountrySelect");
const projectTimezoneInput = document.getElementById("projectTimezoneInput");
const projectCustomCountryInput = document.getElementById("projectCustomCountryInput");
const projectTimezoneOptions = document.getElementById("projectTimezoneOptions");
const saveProjectButton = document.getElementById("saveProjectButton");
const cancelProjectEditButton = document.getElementById("cancelProjectEditButton");
const addProjectButton = document.getElementById("addProjectButton");

const AUTO_REFRESH_MS = 5000;
const REALTIME_DEBOUNCE_MS = 250;
const ARCHIVE_PAGE_SIZE = 8;
const DATABASE_EVENTS_PAGE_SIZE = 50;
const DATABASE_EVENT_DEFAULT_SORT_KEY = "event_time";
const DATABASE_EVENT_DEFAULT_SORT_DIRECTION = "desc";
const ADMIN_SELF_PASSWORD_VERIFY_DEBOUNCE_MS = 260;
const ADMIN_REQUEST_LOOKUP_DEBOUNCE_MS = 260;
const DEFAULT_PROJECT_COUNTRY_CODE = "SG";
const DEFAULT_PROJECT_COUNTRY_NAME = "Singapura";
const DEFAULT_PROJECT_TIMEZONE = "Asia/Singapore";

let activeTab = "checkin";
let autoRefreshHandle = null;
let realtimeConnected = false;
let refreshAllTimer = null;
let eventStream = null;
let isAuthenticated = false;
let adminAccessScope = "full";
let allowedAdminTabs = ["checkin", "checkout", "forms", "inactive", "cadastro", "relatorios", "eventos", "banco-dados"];
let adminCanViewActivityTime = true;
let currentAdminChave = "";
let currentAdminProjectNames = [];
let currentAdminProjectScopeResolved = false;
let currentAdminProjectScopeLoadPromise = null;
let registeredUsersTotal = 0;
let eventArchives = [];
let eventArchivesFilterQuery = "";
let eventArchivesPage = 1;
let eventArchivesTotal = 0;
let eventArchivesTotalPages = 0;
let eventArchivesTotalSizeBytes = 0;
let nextLocationDraftId = 1;
let nextLocationCoordinateDraftId = 1;
let locationRows = [];
let projectMinimumCheckoutDistanceRows = [];
let locationAccuracyThresholdMeters = 30;
let mixedZoneIntervalMinutes = 20;
let locationSettingsDirty = false;
let pendingUsersTotal = 0;
let administratorsTotal = 0;
let eventsTotal = 0;
let eventsRows = null;
let formsTotal = 0;
let formsRows = null;
let lastDashboardRefreshAt = null;
let userTextareaRefreshFrame = null;
let databaseEventsLoaded = false;
let databaseEventsRefreshTimer = null;
let projectCatalog = [];
let projectEditorProjectId = null;
let changePasswordVerifyTimeout = null;
let changePasswordVerifyRequestToken = 0;
let changePasswordCurrentPasswordValid = false;
let changePasswordCurrentPasswordChecking = false;
let changePasswordSaveInProgress = false;
let requestAdminLookupTimeout = null;
let requestAdminLookupRequestToken = 0;
let requestAdminSelfServiceInProgress = false;
let requestAdminRegistrationSaveInProgress = false;
let reportsSearchInProgress = false;
let reportsExportInProgress = false;
let reportsHasLoadedResult = false;
let reportsExportQueryString = "";
let reportsResultsPayload = null;
let reportsSearchUsersByChave = new Map();
const DEFAULT_DISPLAY_TIMEZONE = "Asia/Singapore";
const DEFAULT_TIMEZONE_LABEL = "Singapura (+8)";
const SUPPORTED_PROJECT_COUNTRIES = Object.freeze([
  { code: "BR", name: "Brasil", timezone_name: "America/Sao_Paulo" },
  { code: "CN", name: "China", timezone_name: "Asia/Shanghai" },
  { code: "SG", name: "Singapura", timezone_name: "Asia/Singapore" },
]);

function createDefaultDatabaseEventFilters() {
  return {
    search: "",
    chave: "",
    rfid: "",
    action: "",
    project: "",
    source: "",
    status: "",
    fromDate: "",
    toDate: "",
  };
}

const databaseEventsState = {
  page: 1,
  pageSize: DATABASE_EVENTS_PAGE_SIZE,
  total: 0,
  totalPages: 1,
  filters: createDefaultDatabaseEventFilters(),
  sortKey: DATABASE_EVENT_DEFAULT_SORT_KEY,
  sortDirection: DATABASE_EVENT_DEFAULT_SORT_DIRECTION,
  filterOptions: {
    action: [],
    chave: [],
    rfid: [],
    project: [],
    source: [],
    status: [],
  },
};

function getProjectCatalogNames() {
  return projectCatalog.map((row) => row.name).filter(Boolean);
}

function getProjectOptions(selectedValue, options = {}) {
  const optionValues = getProjectCatalogNames();
  const normalizedSelectedValue = String(selectedValue ?? "").trim();
  if (options.includeDetachedValue && normalizedSelectedValue && !optionValues.includes(normalizedSelectedValue)) {
    return [normalizedSelectedValue, ...optionValues];
  }
  return optionValues;
}

function normalizeProjectNames(values) {
  return Array.from(new Set(
    Array.from(values || [])
      .map((value) => String(value ?? "").trim())
      .filter(Boolean)
  ));
}

function getLocationProjectOptions(selectedValues = []) {
  const selectedProjectNames = normalizeProjectNames(selectedValues);
  const catalogProjectNames = getProjectCatalogNames();
  const detachedProjectNames = selectedProjectNames.filter((projectName) => !catalogProjectNames.includes(projectName));
  return [...detachedProjectNames, ...catalogProjectNames];
}

function normalizeUserProjectMemberships(projectNames, activeProject = "") {
  const normalizedProjectNames = normalizeProjectNames(projectNames);
  const normalizedActiveProject = String(activeProject ?? "").trim();
  if (normalizedActiveProject && !normalizedProjectNames.includes(normalizedActiveProject)) {
    return [normalizedActiveProject, ...normalizedProjectNames];
  }
  return normalizedProjectNames.length ? normalizedProjectNames : (normalizedActiveProject ? [normalizedActiveProject] : []);
}

function formatProjectMembershipSummary(projectNames) {
  const normalizedProjectNames = normalizeProjectNames(projectNames);
  if (!normalizedProjectNames.length) {
    return "Nenhum projeto selecionado";
  }
  return normalizedProjectNames.join(", ");
}

function getUserMembershipProjectNames(row) {
  return normalizeUserProjectMemberships(row?.projetos, row?.projeto);
}

function formatUserMembershipProjects(row, emptyLabel = "-") {
  const projectNames = getUserMembershipProjectNames(row);
  return projectNames.length ? projectNames.join(", ") : emptyLabel;
}

function getProjectMembershipEditorKey(kind, rowId) {
  return `${kind}-${rowId}`;
}

function getProjectMembershipEditorByKey(editorKey) {
  return document.querySelector(`[data-project-membership-editor="${CSS.escape(String(editorKey))}"]`);
}

function getProjectMembershipEditor(kind, rowId) {
  return getProjectMembershipEditorByKey(getProjectMembershipEditorKey(kind, rowId));
}

function parseProjectMembershipSelection(value) {
  try {
    const parsed = JSON.parse(String(value ?? "[]"));
    return normalizeProjectNames(Array.isArray(parsed) ? parsed : []);
  } catch {
    return [];
  }
}

function getStoredProjectMembershipSelection(editor) {
  if (!(editor instanceof HTMLElement)) {
    return [];
  }
  return parseProjectMembershipSelection(editor.dataset.selectedProjects);
}

function setStoredProjectMembershipSelection(editor, projectNames) {
  if (!(editor instanceof HTMLElement)) {
    return [];
  }

  const normalizedProjectNames = normalizeProjectNames(projectNames);
  editor.dataset.selectedProjects = JSON.stringify(normalizedProjectNames);

  const summary = editor.querySelector(".membership-projects-summary");
  if (summary instanceof HTMLElement) {
    const summaryText = formatProjectMembershipSummary(normalizedProjectNames);
    summary.textContent = summaryText;
    summary.title = summaryText;
  }
  return normalizedProjectNames;
}

function getProjectMembershipDisabledTitle(kind) {
  return kind === "pending"
    ? "Clique em Editar antes de selecionar os projetos desta pendência."
    : "Clique em Editar antes de selecionar os projetos deste usuário.";
}

function getProjectMembershipReadyTitle(kind) {
  return kind === "pending"
    ? "Selecione os projetos para este cadastro pendente."
    : "Selecione os projetos vinculados a este usuário.";
}

function getCurrentAdminEditableProjectNames() {
  if (currentAdminProjectScopeResolved) {
    return normalizeProjectNames(currentAdminProjectNames);
  }
  return getProjectCatalogNames();
}

function getProjectMembershipOptionStates(editor) {
  const selectedProjectNames = getStoredProjectMembershipSelection(editor);
  const editableProjectNames = getCurrentAdminEditableProjectNames();
  const editableProjectSet = new Set(editableProjectNames);
  const optionNames = getLocationProjectOptions([...selectedProjectNames, ...editableProjectNames]);
  const selectedProjectSet = new Set(selectedProjectNames);

  return optionNames.map((projectName) => ({
    projectName,
    checked: selectedProjectSet.has(projectName),
    locked: currentAdminProjectScopeResolved && !editableProjectSet.has(projectName),
  }));
}

function getLiveProjectMembershipSelection(editor) {
  if (!(editor instanceof HTMLElement) || !editor.classList.contains("is-open")) {
    return null;
  }

  const editorKey = String(editor.dataset.projectMembershipEditor || "").trim();
  if (!editorKey) {
    return null;
  }

  return normalizeProjectNames(
    Array.from(editor.querySelectorAll(`input[data-project-membership-option="${CSS.escape(editorKey)}"]`))
      .filter((input) => input.checked)
      .map((input) => input.value)
  );
}

function closeProjectMembershipPanel(editor) {
  if (!(editor instanceof HTMLElement)) {
    return;
  }

  const panel = editor.querySelector(".membership-projects-panel");
  if (panel instanceof HTMLElement) {
    panel.hidden = true;
    panel.replaceChildren();
  }

  editor.classList.remove("is-open");
  const button = editor.querySelector("[data-project-membership-toggle]");
  if (button instanceof HTMLButtonElement) {
    button.setAttribute("aria-expanded", "false");
  }
}

function focusProjectMembershipPanel(editor) {
  if (!(editor instanceof HTMLElement)) {
    return;
  }

  editor.querySelector("input[data-project-membership-option]:not(:disabled)")?.focus();
}

function syncProjectMembershipToggleState(editor, editing) {
  if (!(editor instanceof HTMLElement)) {
    return;
  }

  const button = editor.querySelector("[data-project-membership-toggle]");
  if (!(button instanceof HTMLButtonElement)) {
    return;
  }

  const kind = String(editor.dataset.projectMembershipKind || "user").trim();
  const selectedProjectNames = getStoredProjectMembershipSelection(editor);
  const editableProjectNames = getCurrentAdminEditableProjectNames();
  const hasVisibleProjects = editableProjectNames.length > 0 || selectedProjectNames.length > 0;

  if (!editing) {
    button.disabled = true;
    button.title = getProjectMembershipDisabledTitle(kind);
    closeProjectMembershipPanel(editor);
    return;
  }

  if (!hasVisibleProjects) {
    button.disabled = true;
    button.title = currentAdminProjectScopeResolved
      ? "Nenhum projeto disponível no seu escopo."
      : "Cadastre ao menos um projeto antes de continuar.";
    closeProjectMembershipPanel(editor);
    return;
  }

  button.disabled = false;
  button.title = getProjectMembershipReadyTitle(kind);
}

function buildProjectMembershipPanelMarkup(editor) {
  const editorKey = String(editor.dataset.projectMembershipEditor || "").trim();
  const optionStates = getProjectMembershipOptionStates(editor);
  const optionsMarkup = optionStates.map(({ projectName, checked, locked }) => `
      <label class="membership-project-option${locked ? " is-locked" : ""}">
        <input
          type="checkbox"
          data-project-membership-option="${escapeHtml(editorKey)}"
          value="${escapeHtml(projectName)}"
          ${checked ? "checked" : ""}
          ${locked ? 'disabled title="Projeto fora do seu escopo."' : ""}
        />
        <span>${escapeHtml(projectName)}</span>
        ${locked ? "<small>Fora do seu escopo</small>" : ""}
      </label>
    `).join("");

  return `
    <div class="membership-projects-options">
      ${optionsMarkup || `<span class="location-empty-copy">${escapeHtml(currentAdminProjectScopeResolved ? "Nenhum projeto disponível no seu escopo." : "Nenhum projeto cadastrado.")}</span>`}
    </div>
    <div class="membership-projects-panel-footer">
      <button type="button" class="secondary-button" data-project-membership-back="${escapeHtml(editorKey)}">Back</button>
      <button type="button" data-project-membership-apply="${escapeHtml(editorKey)}" ${optionStates.length ? "" : "disabled"}>Save</button>
    </div>
  `;
}

async function ensureCurrentAdminProjectScopeLoaded() {
  if (currentAdminProjectScopeResolved || !currentAdminChave) {
    return;
  }

  if (!currentAdminProjectScopeLoadPromise) {
    currentAdminProjectScopeLoadPromise = loadAdministrators().finally(() => {
      currentAdminProjectScopeLoadPromise = null;
    });
  }

  await currentAdminProjectScopeLoadPromise;
}

async function openProjectMembershipPanelByKey(editorKey) {
  await ensureCurrentAdminProjectScopeLoaded();

  const editor = getProjectMembershipEditorByKey(editorKey);
  if (!(editor instanceof HTMLElement)) {
    return;
  }

  syncProjectMembershipToggleState(editor, true);

  const button = editor.querySelector(`[data-project-membership-toggle="${CSS.escape(String(editorKey))}"]`);
  const panel = editor.querySelector(".membership-projects-panel");
  if (!(button instanceof HTMLButtonElement) || !(panel instanceof HTMLElement) || button.disabled) {
    return;
  }

  if (editor.classList.contains("is-open")) {
    focusProjectMembershipPanel(editor);
    return;
  }

  panel.innerHTML = buildProjectMembershipPanelMarkup(editor);
  panel.hidden = false;
  editor.classList.add("is-open");
  button.setAttribute("aria-expanded", "true");
  focusProjectMembershipPanel(editor);
}

function applyProjectMembershipPanelByKey(editorKey) {
  const editor = getProjectMembershipEditorByKey(editorKey);
  if (!(editor instanceof HTMLElement)) {
    return [];
  }

  const selectedProjectNames = getLiveProjectMembershipSelection(editor) || [];
  setStoredProjectMembershipSelection(editor, selectedProjectNames);
  closeProjectMembershipPanel(editor);
  return selectedProjectNames;
}

function getProjectMembershipSelectionForSubmit(kind, rowId) {
  const editor = getProjectMembershipEditor(kind, rowId);
  if (!(editor instanceof HTMLElement)) {
    return [];
  }

  const selectedProjectNames = getLiveProjectMembershipSelection(editor) || getStoredProjectMembershipSelection(editor);
  setStoredProjectMembershipSelection(editor, selectedProjectNames);
  closeProjectMembershipPanel(editor);
  return selectedProjectNames;
}

function makeProjectMembershipCell({ kind, rowId, selectedProjects }) {
  const projectMembershipKey = getProjectMembershipEditorKey(kind, rowId);
  const summary = formatProjectMembershipSummary(selectedProjects);
  return `
    <div
      class="membership-projects-cell"
      data-project-membership-editor="${escapeHtml(projectMembershipKey)}"
      data-project-membership-kind="${escapeHtml(kind)}"
    >
      <button
        type="button"
        class="secondary-button membership-projects-button"
        data-project-membership-toggle="${escapeHtml(projectMembershipKey)}"
        aria-expanded="false"
        disabled
        title="${escapeHtml(getProjectMembershipDisabledTitle(kind))}"
      >Select</button>
      <span class="membership-projects-summary" title="${escapeHtml(summary)}">${escapeHtml(summary)}</span>
      <div class="membership-projects-panel" hidden></div>
    </div>
  `;
}

function syncSelectOptions(selectElement, optionValues, selectedValue) {
  if (!(selectElement instanceof HTMLSelectElement)) {
    return;
  }

  const nextSelectedValue = String(selectedValue ?? "").trim();
  const fragment = document.createDocumentFragment();
  optionValues.forEach((optionValue) => {
    const option = document.createElement("option");
    option.value = optionValue;
    option.textContent = optionValue;
    fragment.appendChild(option);
  });
  selectElement.replaceChildren(fragment);
  if (optionValues.includes(nextSelectedValue)) {
    selectElement.value = nextSelectedValue;
    return;
  }
  selectElement.value = optionValues[0] || "";
}

function buildProjectOptionsHtml(selectedValue, options = {}) {
  return getProjectOptions(selectedValue, options)
    .map((projectName) => `<option value="${escapeHtml(projectName)}">${escapeHtml(projectName)}</option>`)
    .join("");
}

function setProjectCatalog(rows) {
  projectCatalog = Array.isArray(rows)
    ? rows
      .filter((row) => row && typeof row.name === "string" && row.name.trim())
      .map((row) => ({
        id: row.id,
        name: row.name.trim(),
        country_code: String(row.country_code ?? "").trim(),
        country_name: String(row.country_name ?? "").trim(),
        timezone_name: String(row.timezone_name ?? "").trim(),
        timezone_label: String(row.timezone_label ?? "").trim(),
        address: normalizeProjectMetadataText(row.address),
        zip_code: normalizeProjectMetadataText(row.zip_code),
      }))
    : [];
}

function getProjectById(projectId) {
  const normalizedProjectId = String(projectId ?? "").trim();
  return projectCatalog.find((row) => String(row.id) === normalizedProjectId) || null;
}

function normalizeProjectCountryName(value) {
  return String(value ?? "").trim().replace(/\s+/g, " ");
}

function normalizeProjectTimezoneName(value) {
  return String(value ?? "").trim();
}

function normalizeProjectMetadataText(value) {
  return String(value ?? "").trim().replace(/\s+/g, " ");
}

function normalizeProjectCountryCode(value) {
  return String(value ?? "").trim().toUpperCase();
}

function stripProjectCountryDiacritics(value) {
  return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function deriveProjectCountryCode(countryName, fallbackCode = "") {
  const normalizedFallbackCode = normalizeProjectCountryCode(fallbackCode);
  if (/^[A-Z]{2}$/.test(normalizedFallbackCode)) {
    return normalizedFallbackCode;
  }

  const normalizedCountryName = normalizeProjectCountryName(countryName);
  const knownCountry = SUPPORTED_PROJECT_COUNTRIES.find((row) => row.name.localeCompare(normalizedCountryName, "pt-BR", { sensitivity: "accent" }) === 0);
  if (knownCountry) {
    return knownCountry.code;
  }

  const letters = stripProjectCountryDiacritics(normalizedCountryName).replace(/[^A-Za-z]/g, "").toUpperCase();
  if (letters.length >= 2) {
    return letters.slice(0, 2);
  }
  if (letters.length === 1) {
    return `${letters}X`;
  }
  return DEFAULT_PROJECT_COUNTRY_CODE;
}

function getProjectCountryOptions(selectedValue = DEFAULT_PROJECT_COUNTRY_NAME) {
  const normalizedSelectedValue = normalizeProjectCountryName(selectedValue);
  const optionsByName = new Map();
  const options = [];

  function registerOption(row) {
    const normalizedName = normalizeProjectCountryName(row?.name ?? row?.country_name);
    if (!normalizedName) {
      return;
    }

    const key = normalizedName.toLocaleLowerCase("pt-BR");
    const normalizedTimeZone = normalizeProjectTimezoneName(row?.timezone_name);
    const normalizedCode = deriveProjectCountryCode(normalizedName, row?.code ?? row?.country_code);
    if (optionsByName.has(key)) {
      const existing = optionsByName.get(key);
      if (!existing.timezone_name && normalizedTimeZone) {
        existing.timezone_name = normalizedTimeZone;
      }
      return;
    }

    const option = {
      code: normalizedCode,
      name: normalizedName,
      timezone_name: normalizedTimeZone,
    };
    optionsByName.set(key, option);
    options.push(option);
  }

  SUPPORTED_PROJECT_COUNTRIES.forEach(registerOption);
  projectCatalog.forEach(registerOption);

  if (normalizedSelectedValue && !optionsByName.has(normalizedSelectedValue.toLocaleLowerCase("pt-BR"))) {
    registerOption({
      name: normalizedSelectedValue,
      country_code: deriveProjectCountryCode(normalizedSelectedValue),
      timezone_name: normalizeProjectTimezoneName(projectTimezoneInput ? projectTimezoneInput.value : ""),
    });
  }

  return options;
}

function getProjectCountryOptionByName(countryName) {
  const normalizedCountryName = normalizeProjectCountryName(countryName);
  if (!normalizedCountryName) {
    return null;
  }
  return getProjectCountryOptions(normalizedCountryName).find(
    (row) => row.name.localeCompare(normalizedCountryName, "pt-BR", { sensitivity: "accent" }) === 0,
  ) || null;
}

function getProjectTimezoneValues(selectedValue = "") {
  const values = new Map();

  function registerTimeZone(value) {
    const normalizedValue = normalizeProjectTimezoneName(value);
    if (!normalizedValue) {
      return;
    }
    if (!values.has(normalizedValue)) {
      values.set(normalizedValue, normalizedValue);
    }
  }

  SUPPORTED_PROJECT_COUNTRIES.forEach((row) => registerTimeZone(row.timezone_name));
  projectCatalog.forEach((row) => registerTimeZone(row.timezone_name));
  registerTimeZone(selectedValue);
  return Array.from(values.values()).sort((left, right) => left.localeCompare(right, "en", { sensitivity: "base" }));
}

function syncProjectTimezoneSuggestions(selectedValue = "") {
  if (!projectTimezoneOptions) {
    return;
  }
  projectTimezoneOptions.innerHTML = getProjectTimezoneValues(selectedValue)
    .map((value) => `<option value="${escapeHtml(value)}"></option>`)
    .join("");
}

function syncProjectCountrySelect(selectedValue = DEFAULT_PROJECT_COUNTRY_NAME) {
  if (!projectCountrySelect) {
    return;
  }
  const normalizedSelectedValue = normalizeProjectCountryName(selectedValue) || DEFAULT_PROJECT_COUNTRY_NAME;
  const options = getProjectCountryOptions(normalizedSelectedValue);
  projectCountrySelect.innerHTML = options
    .map(
      (country) => `<option value="${escapeHtml(country.name)}" data-country-code="${escapeHtml(country.code)}" data-timezone-name="${escapeHtml(country.timezone_name)}">${escapeHtml(country.name)}</option>`,
    )
    .join("");
  projectCountrySelect.value = normalizedSelectedValue;
}

function syncProjectTimezoneInput(selectedValue = "", preferredCountryName = DEFAULT_PROJECT_COUNTRY_NAME) {
  const preferredCountry = getProjectCountryOptionByName(preferredCountryName);
  const normalizedTimeZone = normalizeProjectTimezoneName(selectedValue) || preferredCountry?.timezone_name || DEFAULT_PROJECT_TIMEZONE;
  syncProjectTimezoneSuggestions(normalizedTimeZone);
  if (projectTimezoneInput) {
    projectTimezoneInput.value = normalizedTimeZone;
  }
}

function getSelectedProjectCountryOption() {
  if (!projectCountrySelect) {
    return null;
  }

  const selectedOption = projectCountrySelect.selectedOptions[0];
  if (selectedOption) {
    return {
      code: normalizeProjectCountryCode(selectedOption.dataset.countryCode),
      name: normalizeProjectCountryName(selectedOption.value),
      timezone_name: normalizeProjectTimezoneName(selectedOption.dataset.timezoneName),
    };
  }

  return getProjectCountryOptionByName(projectCountrySelect.value);
}

function syncProjectEditorState(options = {}) {
  const { focus = false } = options;
  const editingProject = projectEditorProjectId === null ? null : getProjectById(projectEditorProjectId);
  if (projectEditorProjectId !== null && !editingProject) {
    projectEditorProjectId = null;
  }

  const isEditing = Boolean(editingProject);
  const selectedCountryName = isEditing
    ? normalizeProjectCountryName(editingProject.country_name)
    : normalizeProjectCountryName(projectCountrySelect ? projectCountrySelect.value : "") || DEFAULT_PROJECT_COUNTRY_NAME;

  syncProjectCountrySelect(selectedCountryName);
  syncProjectTimezoneInput(
    isEditing ? editingProject.timezone_name : normalizeProjectTimezoneName(projectTimezoneInput ? projectTimezoneInput.value : ""),
    selectedCountryName,
  );

  if (projectNameInput) {
    if (isEditing) {
      projectNameInput.value = editingProject.name;
    } else {
      projectNameInput.disabled = false;
      projectNameInput.readOnly = false;
    }
  }
  if (projectAddressInput && isEditing) {
    projectAddressInput.value = editingProject.address || "";
  }
  if (projectZipCodeInput && isEditing) {
    projectZipCodeInput.value = editingProject.zip_code || "";
  }
  if (projectCustomCountryInput) {
    projectCustomCountryInput.value = "";
  }

  if (projectEditorTitle) {
    projectEditorTitle.textContent = isEditing ? `Editar Projeto ${editingProject.name}` : "Novo Projeto";
  }
  if (projectEditorHelp) {
    projectEditorHelp.textContent = isEditing
      ? "Nesta etapa, a edição permite alterar nome, endereço, ZIP Code, país e fuso horário."
      : "Informe o nome do projeto, endereço, ZIP Code, país e fuso horário desejados.";
  }
  if (saveProjectButton) {
    saveProjectButton.textContent = isEditing ? "Salvar Alteração" : "Salvar Projeto";
  }
  if (addProjectButton) {
    addProjectButton.textContent = isEditing ? "Novo Projeto" : "Limpar Formulário";
  }

  if (focus) {
    const field = projectNameInput;
    if (field) {
      field.focus();
    }
  }
}

function resetProjectEditor(options = {}) {
  const { focus = false } = options;
  projectEditorProjectId = null;
  if (projectNameInput) {
    projectNameInput.value = "";
  }
  if (projectAddressInput) {
    projectAddressInput.value = "";
  }
  if (projectZipCodeInput) {
    projectZipCodeInput.value = "";
  }
  if (projectCustomCountryInput) {
    projectCustomCountryInput.value = "";
  }
  syncProjectCountrySelect(DEFAULT_PROJECT_COUNTRY_NAME);
  syncProjectTimezoneInput(DEFAULT_PROJECT_TIMEZONE, DEFAULT_PROJECT_COUNTRY_NAME);
  syncProjectEditorState({ focus });
}

function startProjectEdit(projectId) {
  const normalizedProjectId = requireIntegerId(projectId, "Projeto");
  const project = getProjectById(normalizedProjectId);
  if (!project) {
    setStatus("Projeto não encontrado para edição.", false);
    return;
  }
  projectEditorProjectId = normalizedProjectId;
  syncProjectEditorState({ focus: true });
}

const PRESENCE_TABLE_CONFIGS = {
  checkin: {
    bodyId: "checkinBody",
    filterColumns: ["time", "nome", "chave", "projetos", "assiduidade", "local"],
    defaultSortKey: "time",
    defaultSortDirection: "desc",
    renderOptions: { includeElapsedDays: true },
  },
  checkout: {
    bodyId: "checkoutBody",
    filterColumns: ["time", "nome", "chave", "projetos", "assiduidade", "local"],
    defaultSortKey: "time",
    defaultSortDirection: "desc",
    renderOptions: {},
  },
  inactive: {
    bodyId: "inactiveBody",
    filterColumns: ["nome", "chave", "projetos", "latest_time", "inactivity_days"],
    defaultSortKey: "inactivity_days",
    defaultSortDirection: "desc",
    renderOptions: {},
  },
  missingCheckout: {
    bodyId: "missingCheckoutBody",
    filterColumns: ["nome", "chave", "time"],
    defaultSortKey: "time",
    defaultSortDirection: "desc",
    renderOptions: {},
  },
};
const presenceTableStates = Object.fromEntries(
  Object.entries(PRESENCE_TABLE_CONFIGS).map(([tableKey, config]) => [
    tableKey,
    createPresenceTableState(tableKey, config),
  ]),
);
const TAB_LABELS = {
  checkin: "Check-In",
  checkout: "Check-Out",
  forms: "Forms",
  inactive: "Inativos",
  cadastro: "Cadastro",
  relatorios: "Relatórios",
  eventos: "Eventos",
  "banco-dados": "Banco de Dados",
};
const ADMIN_MOBILE_VIEWPORT_QUERY = "(max-width: 800px)";
const DEFAULT_ADMIN_ALLOWED_TABS = Object.freeze(["checkin", "checkout", "forms", "inactive", "cadastro", "relatorios", "eventos", "banco-dados"]);
const LIMITED_ADMIN_ALLOWED_TABS = Object.freeze(["checkin", "checkout"]);
const MOBILE_FILTER_PANEL_KEYS = Object.freeze(["checkin", "checkout", "inactive", "relatorios"]);
let adminViewportMediaQueryList = null;
let adminResponsiveSyncFrame = null;
let adminResponsiveStateKey = "";
const adminMobileFilterPanelState = Object.create(null);

function getDefaultAllowedTabsForScope(scope) {
  return [...(scope === "limited" ? LIMITED_ADMIN_ALLOWED_TABS : DEFAULT_ADMIN_ALLOWED_TABS)];
}

function normalizeAllowedAdminTabs(tabs, scope = "full") {
  const allowedValues = new Set(DEFAULT_ADMIN_ALLOWED_TABS);
  const scopeDefaults = getDefaultAllowedTabsForScope(scope);
  const normalizedTabs = Array.isArray(tabs)
    ? Array.from(new Set(
      tabs
        .map((tab) => String(tab || "").trim())
        .filter((tab) => allowedValues.has(tab))
    ))
    : [];

  if (!normalizedTabs.length) {
    return scopeDefaults;
  }

  if (scope === "limited") {
    return normalizedTabs.filter((tab) => LIMITED_ADMIN_ALLOWED_TABS.includes(tab));
  }

  return normalizedTabs;
}

function isAdminTabAllowed(tab) {
  return allowedAdminTabs.includes(String(tab || "").trim());
}

function getFirstAllowedAdminTab() {
  return allowedAdminTabs[0] || "checkin";
}

function getAdminViewportMediaQueryList() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return null;
  }

  if (!adminViewportMediaQueryList) {
    adminViewportMediaQueryList = window.matchMedia(ADMIN_MOBILE_VIEWPORT_QUERY);
  }

  return adminViewportMediaQueryList;
}

function isMobileAdminViewport() {
  const mediaQueryList = getAdminViewportMediaQueryList();
  if (mediaQueryList) {
    return mediaQueryList.matches;
  }

  if (typeof window !== "undefined" && typeof window.innerWidth === "number") {
    return window.innerWidth <= 800;
  }

  return false;
}

function isLimitedMobileAdminView() {
  return isMobileAdminViewport() && adminAccessScope === "limited";
}

function getPresenceResponsiveVariant(tableKey) {
  const normalizedTableKey = String(tableKey || "").trim();
  if (!["checkin", "checkout"].includes(normalizedTableKey)) {
    return "desktop";
  }

  if (isLimitedMobileAdminView()) {
    return "mobile-limited";
  }

  return isMobileAdminViewport() ? "mobile" : "desktop";
}

function buildAdminResponsiveStateSnapshot() {
  const mobileViewport = isMobileAdminViewport();
  const limitedMobileView = mobileViewport && adminAccessScope === "limited";

  return {
    viewport: mobileViewport ? "mobile" : "desktop",
    accessScope: adminAccessScope,
    mobileMode: limitedMobileView ? "limited" : mobileViewport ? "mobile" : "desktop",
    isMobileViewport: mobileViewport,
    isLimitedMobileView: limitedMobileView,
  };
}

function buildAdminResponsiveStateKey(snapshot) {
  return `${snapshot.viewport}:${snapshot.accessScope}:${snapshot.mobileMode}`;
}

function getAdminMobileFilterPanelExpanded(panelKey) {
  const normalizedPanelKey = String(panelKey || "").trim();
  if (!MOBILE_FILTER_PANEL_KEYS.includes(normalizedPanelKey)) {
    return true;
  }

  if (!Object.prototype.hasOwnProperty.call(adminMobileFilterPanelState, normalizedPanelKey)) {
    adminMobileFilterPanelState[normalizedPanelKey] = false;
  }

  return adminMobileFilterPanelState[normalizedPanelKey];
}

function setAdminMobileFilterPanelExpanded(panelKey, expanded) {
  const normalizedPanelKey = String(panelKey || "").trim();
  if (!MOBILE_FILTER_PANEL_KEYS.includes(normalizedPanelKey)) {
    return;
  }

  adminMobileFilterPanelState[normalizedPanelKey] = Boolean(expanded);
}

function syncAdminTabStrip(snapshot = buildAdminResponsiveStateSnapshot()) {
  const tabs = document.querySelector(".tabs");
  if (!tabs) {
    return;
  }

  tabs.dataset.adminViewport = snapshot.viewport;
  tabs.dataset.adminActiveTab = activeTab;
  const activeButton = tabs.querySelector(`button[data-tab="${activeTab}"]`);
  if (snapshot.isMobileViewport && activeButton && typeof activeButton.scrollIntoView === "function") {
    activeButton.scrollIntoView({ block: "nearest", inline: "center" });
  }
}

function syncAdminMobileFilterPanel(panelKey) {
  const normalizedPanelKey = String(panelKey || "").trim();
  if (!MOBILE_FILTER_PANEL_KEYS.includes(normalizedPanelKey)) {
    return;
  }

  const panel = document.querySelector(`[data-filter-panel="${normalizedPanelKey}"]`);
  const toggleButtons = document.querySelectorAll(`[data-filter-toggle="${normalizedPanelKey}"]`);
  const mobileViewport = isMobileAdminViewport();
  const expanded = mobileViewport ? getAdminMobileFilterPanelExpanded(normalizedPanelKey) : true;

  if (panel) {
    panel.hidden = !expanded;
  }

  toggleButtons.forEach((button) => {
    const openLabel = String(button.dataset.filterOpenLabel || "Mostrar filtros");
    const closeLabel = String(button.dataset.filterCloseLabel || "Ocultar filtros");
    button.hidden = !mobileViewport;
    button.classList.toggle("hidden", !mobileViewport);
    button.textContent = expanded ? closeLabel : openLabel;
    button.setAttribute("aria-expanded", String(expanded));
  });
}

function syncAdminMobileFilterPanels() {
  MOBILE_FILTER_PANEL_KEYS.forEach((panelKey) => {
    syncAdminMobileFilterPanel(panelKey);
  });
}

function toggleAdminMobileFilterPanel(panelKey) {
  const normalizedPanelKey = String(panelKey || "").trim();
  if (!MOBILE_FILTER_PANEL_KEYS.includes(normalizedPanelKey)) {
    return;
  }

  setAdminMobileFilterPanelExpanded(normalizedPanelKey, !getAdminMobileFilterPanelExpanded(normalizedPanelKey));
  syncAdminMobileFilterPanels();
}

function syncAdminShellResponsiveState(snapshot = buildAdminResponsiveStateSnapshot()) {
  syncAdminTabStrip(snapshot);
  syncAdminMobileFilterPanels();
}

function syncAdminResponsiveDatasets(snapshot = buildAdminResponsiveStateSnapshot()) {
  [document.body, authShell, adminShell, sessionBar].filter(Boolean).forEach((element) => {
    element.dataset.adminViewport = snapshot.viewport;
    element.dataset.adminAccessScope = snapshot.accessScope;
    element.dataset.adminMobileMode = snapshot.mobileMode;
  });

  ["checkin", "checkout"].forEach((tableKey) => {
    const variant = getPresenceResponsiveVariant(tableKey);
    const controls = document.querySelector(`.presence-controls[data-presence-table="${tableKey}"]`);
    if (controls) {
      controls.dataset.presenceRenderVariant = variant;
    }

    const section = document.getElementById(`tab-${tableKey}`);
    if (section) {
      section.dataset.presenceRenderVariant = variant;
    }

    const body = document.getElementById(presenceTableStates[tableKey]?.bodyId || "");
    const table = body?.closest("table");
    if (table) {
      table.dataset.presenceRenderVariant = variant;
    }
  });

  const eventsTable = document.querySelector(".events-table");
  if (eventsTable) {
    eventsTable.dataset.eventsRenderVariant = snapshot.viewport === "mobile" ? "mobile" : "desktop";
  }
}

function syncAdminResponsiveState(options = {}) {
  const { force = false } = options;
  const snapshot = buildAdminResponsiveStateSnapshot();
  const nextStateKey = buildAdminResponsiveStateKey(snapshot);

  syncAdminResponsiveDatasets(snapshot);
  syncAdminShellResponsiveState(snapshot);
  if (!force && nextStateKey === adminResponsiveStateKey) {
    return false;
  }

  adminResponsiveStateKey = nextStateKey;
  syncPresenceTimeLabels();
  const canViewFormsTime = syncFormsTimeColumnVisibility();
  const canViewEventsTime = syncEventsPrimaryColumnLabel();

  Object.entries(presenceTableStates).forEach(([tableKey, state]) => {
    const body = document.getElementById(state.bodyId);
    if (!body || (!state.rawRows.length && !body.children.length)) {
      return;
    }

    applyPresenceTableState(tableKey);
  });

  if (formsRows !== null) {
    renderFormsTable(formsRows, { canViewTime: canViewFormsTime });
  }
  if (eventsRows !== null) {
    renderEventsTable(eventsRows, { canViewTime: canViewEventsTime });
  }
  if (reportsResultsPayload !== null) {
    renderReportsResults(reportsResultsPayload);
  }

  updateOperationalChrome();
  return true;
}

function scheduleAdminResponsiveSync(options = {}) {
  const { force = false } = options;
  if (adminResponsiveSyncFrame !== null) {
    window.cancelAnimationFrame(adminResponsiveSyncFrame);
  }

  adminResponsiveSyncFrame = window.requestAnimationFrame(() => {
    adminResponsiveSyncFrame = null;
    syncAdminResponsiveState({ force });
  });
}

function applyAdminTabVisibility() {
  document.querySelectorAll(".tabs button[data-tab]").forEach((button) => {
    const tab = String(button.dataset.tab || "").trim();
    const isAllowed = isAdminTabAllowed(tab);
    button.hidden = !isAllowed;
    button.classList.toggle("hidden", !isAllowed);
    if (!isAllowed) {
      button.classList.remove("active");
    }
  });

  document.querySelectorAll(".tab[id^=\"tab-\"]").forEach((section) => {
    const tab = section.id.startsWith("tab-") ? section.id.slice(4) : "";
    if (!Object.prototype.hasOwnProperty.call(TAB_LABELS, tab)) {
      return;
    }
    const isAllowed = isAdminTabAllowed(tab);
    section.hidden = !isAllowed;
    if (!isAllowed) {
      section.classList.remove("active");
    }
  });

  if (!isAdminTabAllowed(activeTab)) {
    activeTab = getFirstAllowedAdminTab();
  }

  const activeButton = document.querySelector(`.tabs button[data-tab="${activeTab}"]`);
  const activeSection = document.getElementById(`tab-${activeTab}`);
  if (activeButton) {
    activeButton.hidden = false;
    activeButton.classList.add("active");
  }
  if (activeSection) {
    activeSection.hidden = false;
    activeSection.classList.add("active");
  }

  syncAdminTabStrip();
}

function setAdminAccessState(admin) {
  adminAccessScope = admin?.access_scope === "limited" ? "limited" : "full";
  allowedAdminTabs = normalizeAllowedAdminTabs(admin?.allowed_tabs, adminAccessScope);
  adminCanViewActivityTime = Boolean(admin?.can_view_activity_time);
  if (!allowedAdminTabs.length) {
    allowedAdminTabs = getDefaultAllowedTabsForScope(adminAccessScope);
  }
  applyAdminTabVisibility();
  syncAdminResponsiveState({ force: true });
}

function resetAdminAccessState() {
  adminAccessScope = "full";
  allowedAdminTabs = getDefaultAllowedTabsForScope(adminAccessScope);
  adminCanViewActivityTime = true;
  applyAdminTabVisibility();
  syncAdminResponsiveState({ force: true });
}

function canCurrentAdminViewActivityTime() {
  return adminCanViewActivityTime;
}

function isLimitedMobilePresenceVariant(tableKey, responsiveVariant = getPresenceResponsiveVariant(tableKey)) {
  return ["checkin", "checkout"].includes(String(tableKey || "").trim()) && responsiveVariant === "mobile-limited";
}

function getFormsColumnCount(includeTime = canCurrentAdminViewActivityTime()) {
  return includeTime ? 9 : 8;
}

function syncFormsTimeColumnVisibility() {
  const formsTable = document.getElementById("formsTable");
  const formsTimeHeader = document.querySelector("[data-forms-time-column-header]");
  const canViewTime = canCurrentAdminViewActivityTime();

  if (formsTable) {
    formsTable.classList.toggle("forms-table--without-time", !canViewTime);
  }
  if (formsTimeHeader) {
    formsTimeHeader.hidden = !canViewTime;
  }

  return canViewTime;
}

function getEventsPrimaryColumnLabel() {
  return canCurrentAdminViewActivityTime() ? "Horário" : "Data";
}

function syncEventsPrimaryColumnLabel() {
  const eventsHeader = document.querySelector("[data-events-primary-header-label]");
  const canViewTime = canCurrentAdminViewActivityTime();

  if (eventsHeader) {
    eventsHeader.textContent = getEventsPrimaryColumnLabel();
  }

  return canViewTime;
}

function getPresencePrimaryColumnLabel(tableKey) {
  if (getPresenceResponsiveVariant(tableKey) !== "desktop") {
    return "Data";
  }

  return canCurrentAdminViewActivityTime() ? "Horário" : "Data";
}

function getPresencePrimaryFilterLabel(tableKey) {
  if (getPresenceResponsiveVariant(tableKey) !== "desktop") {
    return "Filtrar Data";
  }

  return canCurrentAdminViewActivityTime() ? "Filtrar Horário" : "Filtrar Data";
}

function getPresenceNameColumnLabel(tableKey) {
  return isLimitedMobilePresenceVariant(tableKey) ? "Nome do Usuário" : "Nome";
}

function getPresenceNameFilterLabel(tableKey) {
  return isLimitedMobilePresenceVariant(tableKey) ? "Filtrar Nome do Usuário" : "Filtrar Nome";
}

function getVisiblePresenceFilterKeys(tableKey) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return [];
  }

  if (isLimitedMobilePresenceVariant(tableKey)) {
    return ["time", "nome", "local"];
  }

  return state.filterColumns;
}

function getVisiblePresenceSortKeys(tableKey) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return [];
  }

  if (isLimitedMobilePresenceVariant(tableKey)) {
    return ["time", "nome", "local"];
  }

  return state.filterColumns;
}

function sanitizePresenceSortState(tableKey) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return;
  }

  const visibleSortKeys = getVisiblePresenceSortKeys(tableKey);
  if (visibleSortKeys.includes(state.sortKey)) {
    return;
  }

  const fallbackSortKey = visibleSortKeys.includes(state.defaultSortKey)
    ? state.defaultSortKey
    : (visibleSortKeys[0] || state.defaultSortKey);
  state.sortKey = fallbackSortKey;
  state.sortDirection = getPresenceDefaultSortDirection(fallbackSortKey);
}

function syncPresenceResponsiveControls(tableKey) {
  const state = getPresenceTableState(tableKey);
  const container = document.querySelector(`.presence-controls[data-presence-table="${tableKey}"]`);
  if (!state || !container) {
    return;
  }

  sanitizePresenceSortState(tableKey);
  const visibleFilterKeys = new Set(getVisiblePresenceFilterKeys(tableKey));
  container.querySelectorAll("[data-presence-filter]").forEach((control) => {
    const key = String(control.dataset.presenceFilter || "").trim();
    const field = control.closest(".presence-control-field");
    const isVisible = visibleFilterKeys.has(key);

    control.disabled = !isVisible;
    control.setAttribute("aria-hidden", String(!isVisible));

    if (field) {
      field.hidden = !isVisible;
      field.classList.toggle("hidden", !isVisible);
    }

    if (!isVisible) {
      state.filters[key] = "";
      control.value = "";
    }
  });

  const clearButton = container.querySelector("[data-presence-clear]");
  if (clearButton instanceof HTMLButtonElement) {
    const hasVisibleActiveFilters = getVisiblePresenceFilterKeys(tableKey)
      .some((key) => String(state.filters[key] || "").trim());
    clearButton.disabled = !hasVisibleActiveFilters;
  }
}

function syncPresenceTimeLabels() {
  ["checkin", "checkout"].forEach((tableKey) => {
    const headerLabel = document.querySelector(`[data-presence-primary-header-label="${tableKey}"]`);
    if (headerLabel) {
      headerLabel.textContent = getPresencePrimaryColumnLabel(tableKey);
    }

    const filterLabel = document.querySelector(`[data-presence-primary-filter-label="${tableKey}"]`);
    if (filterLabel) {
      filterLabel.textContent = getPresencePrimaryFilterLabel(tableKey);
    }

    const nameHeaderLabel = document.querySelector(`[data-presence-name-header-label="${tableKey}"]`);
    if (nameHeaderLabel) {
      nameHeaderLabel.textContent = getPresenceNameColumnLabel(tableKey);
    }

    const nameFilterLabel = document.querySelector(`[data-presence-name-filter-label="${tableKey}"]`);
    if (nameFilterLabel) {
      nameFilterLabel.textContent = getPresenceNameFilterLabel(tableKey);
    }

    syncPresenceResponsiveControls(tableKey);
  });
}

function createPresenceFilterState(filterColumns) {
  return Object.fromEntries(filterColumns.map((key) => [key, ""]));
}

function createPresenceTableState(tableKey, config) {
  return {
    tableKey,
    bodyId: config.bodyId,
    renderOptions: config.renderOptions || {},
    filterColumns: config.filterColumns || [],
    defaultSortKey: config.defaultSortKey,
    defaultSortDirection: config.defaultSortDirection,
    rawRows: [],
    filters: createPresenceFilterState(config.filterColumns || []),
    sortKey: config.defaultSortKey,
    sortDirection: config.defaultSortDirection,
  };
}

function setAuthStatus(message, kind = "info") {
  authStatus.textContent = message || "";
  authStatus.className = `auth-status ${kind === "error" ? "status-err" : kind === "success" ? "status-ok" : ""}`;
}

function setChangePasswordStatus(message, kind = "info") {
  if (!changePasswordStatus) {
    return;
  }

  changePasswordStatus.textContent = message || "";
  changePasswordStatus.className = `auth-status ${kind === "error" ? "status-err" : kind === "success" ? "status-ok" : ""}`;
}

function setReportsStatus(message, kind = "info") {
  if (!reportsStatus) {
    return;
  }

  reportsStatus.textContent = message || "";
  reportsStatus.className = `auth-status ${kind === "error" ? "status-err" : kind === "success" ? "status-ok" : ""}`;
}

function normalizeAdminChave(value) {
  return String(value || "")
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, 4);
}

function normalizeReportSearchName(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim();
}

function appendSelectOption(selectElement, value, label) {
  if (!(selectElement instanceof HTMLSelectElement)) {
    return;
  }

  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  selectElement.appendChild(option);
}

function hasSelectOption(selectElement, value) {
  return selectElement instanceof HTMLSelectElement
    && Array.from(selectElement.options).some((option) => option.value === value);
}

function getReportSearchUserByChave(chave) {
  const normalizedChave = normalizeAdminChave(chave);
  if (!normalizedChave) {
    return null;
  }

  return reportsSearchUsersByChave.get(normalizedChave) || null;
}

function getSelectedReportSearchKey(source = null) {
  const selectedChave = normalizeAdminChave(reportsSearchChaveInput ? reportsSearchChaveInput.value : "");
  const selectedNomeKey = normalizeAdminChave(reportsSearchNomeInput ? reportsSearchNomeInput.value : "");

  if (source === "nome") {
    return selectedNomeKey || selectedChave;
  }
  if (source === "chave") {
    return selectedChave || selectedNomeKey;
  }

  return selectedChave || selectedNomeKey;
}

function populateReportsSearchOptions(rows) {
  const users = Array.isArray(rows) ? rows : [];
  const previousSelectedKey = getSelectedReportSearchKey();
  reportsSearchUsersByChave = new Map();

  users
    .map((user) => ({
      chave: normalizeAdminChave(user?.chave),
      nome: normalizeReportSearchName(user?.nome),
    }))
    .filter((user) => user.chave && user.nome)
    .sort((left, right) => left.chave.localeCompare(right.chave, "pt-BR", { sensitivity: "base" }))
    .forEach((user) => {
      if (!reportsSearchUsersByChave.has(user.chave)) {
        reportsSearchUsersByChave.set(user.chave, user);
      }
    });

  const reportUsers = Array.from(reportsSearchUsersByChave.values());
  const duplicateNameCounts = new Map();
  reportUsers.forEach((user) => {
    const duplicateKey = user.nome.toLocaleLowerCase("pt-BR");
    duplicateNameCounts.set(duplicateKey, (duplicateNameCounts.get(duplicateKey) || 0) + 1);
  });

  if (reportsSearchChaveInput instanceof HTMLSelectElement) {
    reportsSearchChaveInput.innerHTML = "";
    appendSelectOption(reportsSearchChaveInput, "", "Selecione uma chave");
    reportUsers.forEach((user) => {
      appendSelectOption(reportsSearchChaveInput, user.chave, user.chave);
    });
  }

  if (reportsSearchNomeInput instanceof HTMLSelectElement) {
    reportsSearchNomeInput.innerHTML = "";
    appendSelectOption(reportsSearchNomeInput, "", "Selecione um nome");
    reportUsers
      .slice()
      .sort((left, right) => {
        const nameComparison = left.nome.localeCompare(right.nome, "pt-BR", { sensitivity: "base" });
        if (nameComparison !== 0) {
          return nameComparison;
        }
        return left.chave.localeCompare(right.chave, "pt-BR", { sensitivity: "base" });
      })
      .forEach((user) => {
        const duplicateKey = user.nome.toLocaleLowerCase("pt-BR");
        const label = duplicateNameCounts.get(duplicateKey) > 1
          ? `${user.nome} (${user.chave})`
          : user.nome;
        appendSelectOption(reportsSearchNomeInput, user.chave, label);
      });
  }

  if (reportsSearchChaveInput instanceof HTMLSelectElement) {
    reportsSearchChaveInput.value = hasSelectOption(reportsSearchChaveInput, previousSelectedKey) ? previousSelectedKey : "";
  }
  if (reportsSearchNomeInput instanceof HTMLSelectElement) {
    reportsSearchNomeInput.value = hasSelectOption(reportsSearchNomeInput, previousSelectedKey) ? previousSelectedKey : "";
  }

  syncReportsSearchInputs();
}

function isAdminCurrentPasswordInputValid(value) {
  const password = String(value || "");
  return password.length >= 3 && password.length <= 20 && password.trim().length > 0;
}

function isAdminNewPasswordInputValid(value) {
  const password = String(value || "");
  return password.length >= 3 && password.length <= 10 && password.trim().length > 0;
}

function isChangePasswordModalOpen() {
  return Boolean(changePasswordModal && !changePasswordModal.classList.contains("hidden"));
}

function clearChangePasswordVerificationTimer() {
  if (changePasswordVerifyTimeout !== null) {
    window.clearTimeout(changePasswordVerifyTimeout);
    changePasswordVerifyTimeout = null;
  }
  changePasswordVerifyRequestToken += 1;
}

function syncChangePasswordFormState() {
  if (!changePasswordSaveButton) {
    return;
  }

  const chave = normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "");
  const currentPassword = String(changePasswordCurrentInput ? changePasswordCurrentInput.value : "");
  const newPassword = String(changePasswordNewInput ? changePasswordNewInput.value : "");
  const confirmPassword = String(changePasswordConfirmInput ? changePasswordConfirmInput.value : "");
  const canSave = chave.length === 4
    && changePasswordCurrentPasswordValid
    && isAdminNewPasswordInputValid(newPassword)
    && newPassword !== currentPassword
    && confirmPassword === newPassword
    && !changePasswordCurrentPasswordChecking
    && !changePasswordSaveInProgress;

  changePasswordSaveButton.disabled = !canSave;
  changePasswordSaveButton.textContent = changePasswordSaveInProgress ? "Salvando..." : "Salvar";

  [changePasswordCurrentInput, changePasswordNewInput, changePasswordConfirmInput, changePasswordBackButton]
    .filter(Boolean)
    .forEach((element) => {
      element.disabled = changePasswordSaveInProgress;
    });
}

function resetChangePasswordVerificationState() {
  clearChangePasswordVerificationTimer();
  changePasswordCurrentPasswordValid = false;
  changePasswordCurrentPasswordChecking = false;
}

function openChangePasswordModal() {
  const normalizedChave = normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "");
  if (loginChaveInput && normalizedChave !== loginChaveInput.value) {
    loginChaveInput.value = normalizedChave;
  }

  if (normalizedChave.length !== 4) {
    setAuthStatus("Informe sua chave antes de alterar a senha.", "error");
    if (loginChaveInput) {
      loginChaveInput.focus();
    }
    return;
  }

  if (!changePasswordModal || !changePasswordForm) {
    return;
  }

  changePasswordForm.reset();
  changePasswordSaveInProgress = false;
  resetChangePasswordVerificationState();
  setChangePasswordStatus("");
  changePasswordModal.classList.remove("hidden");
  changePasswordModal.setAttribute("aria-hidden", "false");
  syncChangePasswordFormState();
  if (changePasswordCurrentInput) {
    changePasswordCurrentInput.focus();
  }
}

function closeChangePasswordModal() {
  if (!changePasswordModal) {
    return;
  }

  if (changePasswordForm) {
    changePasswordForm.reset();
  }
  changePasswordSaveInProgress = false;
  resetChangePasswordVerificationState();
  setChangePasswordStatus("");
  changePasswordModal.classList.add("hidden");
  changePasswordModal.setAttribute("aria-hidden", "true");
  syncChangePasswordFormState();
}

function isStaleChangePasswordVerification(chave, currentPassword, requestToken) {
  return requestToken !== changePasswordVerifyRequestToken
    || !isChangePasswordModalOpen()
    || normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "") !== chave
    || String(changePasswordCurrentInput ? changePasswordCurrentInput.value : "") !== currentPassword;
}

async function verifyCurrentAdminPassword(chave, currentPassword, requestToken) {
  try {
    const payload = await postJson("/api/admin/auth/verify-current-password", {
      chave,
      senha_atual: currentPassword,
    });

    if (isStaleChangePasswordVerification(chave, currentPassword, requestToken)) {
      return;
    }

    changePasswordCurrentPasswordValid = Boolean(payload.valid);
    setChangePasswordStatus(payload.valid ? "Senha atual confirmada." : payload.message, payload.valid ? "success" : "error");
  } catch (error) {
    if (isStaleChangePasswordVerification(chave, currentPassword, requestToken)) {
      return;
    }

    changePasswordCurrentPasswordValid = false;
    setChangePasswordStatus(error.message, "error");
  } finally {
    if (isStaleChangePasswordVerification(chave, currentPassword, requestToken)) {
      return;
    }

    changePasswordCurrentPasswordChecking = false;
    syncChangePasswordFormState();
  }
}

function scheduleChangePasswordVerification() {
  if (!isChangePasswordModalOpen()) {
    return;
  }

  const chave = normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "");
  const currentPassword = String(changePasswordCurrentInput ? changePasswordCurrentInput.value : "");

  resetChangePasswordVerificationState();
  if (!chave || !isAdminCurrentPasswordInputValid(currentPassword)) {
    if (!currentPassword) {
      setChangePasswordStatus("");
    }
    syncChangePasswordFormState();
    return;
  }

  const requestToken = changePasswordVerifyRequestToken;
  changePasswordCurrentPasswordChecking = true;
  setChangePasswordStatus("Verificando senha atual...", "info");
  syncChangePasswordFormState();
  changePasswordVerifyTimeout = window.setTimeout(() => {
    void verifyCurrentAdminPassword(chave, currentPassword, requestToken);
  }, ADMIN_SELF_PASSWORD_VERIFY_DEBOUNCE_MS);
}

async function submitChangePassword() {
  const chave = normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "");
  const currentPassword = String(changePasswordCurrentInput ? changePasswordCurrentInput.value : "");
  const newPassword = String(changePasswordNewInput ? changePasswordNewInput.value : "");
  const confirmPassword = String(changePasswordConfirmInput ? changePasswordConfirmInput.value : "");

  if (chave.length !== 4) {
    setChangePasswordStatus("Informe sua chave antes de alterar a senha.", "error");
    if (loginChaveInput) {
      loginChaveInput.focus();
    }
    return;
  }
  if (!isAdminCurrentPasswordInputValid(currentPassword)) {
    setChangePasswordStatus("A senha atual deve ter entre 3 e 20 caracteres.", "error");
    if (changePasswordCurrentInput) {
      changePasswordCurrentInput.focus();
    }
    return;
  }
  if (!changePasswordCurrentPasswordValid) {
    setChangePasswordStatus("A senha atual nao confere.", "error");
    if (changePasswordCurrentInput) {
      changePasswordCurrentInput.focus();
    }
    return;
  }
  if (!isAdminNewPasswordInputValid(newPassword)) {
    setChangePasswordStatus("A nova senha deve ter entre 3 e 10 caracteres.", "error");
    if (changePasswordNewInput) {
      changePasswordNewInput.focus();
    }
    return;
  }
  if (newPassword === currentPassword) {
    setChangePasswordStatus("A nova senha deve ser diferente da senha atual.", "error");
    if (changePasswordNewInput) {
      changePasswordNewInput.focus();
    }
    return;
  }
  if (confirmPassword !== newPassword) {
    setChangePasswordStatus("A confirmação da senha deve ser idêntica à nova senha.", "error");
    if (changePasswordConfirmInput) {
      changePasswordConfirmInput.focus();
    }
    return;
  }

  changePasswordSaveInProgress = true;
  syncChangePasswordFormState();
  setChangePasswordStatus("Salvando nova senha...", "info");

  try {
    const payload = await postJson("/api/admin/auth/change-password", {
      chave,
      senha_atual: currentPassword,
      nova_senha: newPassword,
      confirmar_senha: confirmPassword,
    });
    if (loginSenhaInput) {
      loginSenhaInput.value = newPassword;
    }
    closeChangePasswordModal();
    setAuthStatus(payload.message, "success");
  } catch (error) {
    setChangePasswordStatus(error.message, "error");
  } finally {
    changePasswordSaveInProgress = false;
    syncChangePasswordFormState();
  }
}

function setStatus(message, ok = true) {
  statusLine.textContent = message;
  statusLine.className = ok ? "status-ok" : "status-err";
}

function clearStatus() {
  statusLine.textContent = "";
  statusLine.className = "";
}

function setTextContentIfPresent(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function formatDashboardRefreshTime(value) {
  if (!(value instanceof Date) || Number.isNaN(value.getTime())) {
    return "Sem atualização";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(value);
}

function updateOperationalChrome() {
  const currentTabLabel = TAB_LABELS[activeTab] || "Painel";
  let realtimeLabel = "Aguardando sessão";
  let realtimeTone = "waiting";
  let connectionSummary = "Aguardando autenticação";

  if (isAuthenticated && realtimeConnected) {
    realtimeLabel = "Tempo real ativo";
    realtimeTone = "live";
    connectionSummary = "Sincronização em tempo real";
  } else if (isAuthenticated) {
    realtimeLabel = "Atualização periódica";
    realtimeTone = "polling";
    connectionSummary = "Fallback por polling a cada 5 s";
  }

  const realtimeBadge = document.getElementById("realtimeStatusBadge");
  if (realtimeBadge) {
    realtimeBadge.textContent = realtimeLabel;
    realtimeBadge.className = `topbar-pill topbar-pill-live is-${realtimeTone}`;
  }

  const lastRefreshLabel = lastDashboardRefreshAt
    ? `Atualizado às ${formatDashboardRefreshTime(lastDashboardRefreshAt)}`
    : "Sem atualização";

  setTextContentIfPresent("lastRefreshBadge", lastRefreshLabel);
  setTextContentIfPresent("activeTabBadge", `Aba atual: ${currentTabLabel}`);
  setTextContentIfPresent("heroMetricConnection", connectionSummary);
  setTextContentIfPresent("heroMetricRefresh", lastRefreshLabel);
  setTextContentIfPresent("heroMetricCurrentTab", currentTabLabel);
  setTextContentIfPresent(
    "heroMetricCoverage",
    registeredUsersTotal === 1 ? "1 usuário monitorado" : `${registeredUsersTotal} usuários monitorados`,
  );
}

function updateDashboardSummary() {
  const counts = {
    checkin: presenceTableStates.checkin.rawRows.length,
    checkout: presenceTableStates.checkout.rawRows.length,
    forms: formsTotal,
    inactive: presenceTableStates.inactive.rawRows.length,
    pending: pendingUsersTotal,
    users: registeredUsersTotal,
    events: eventsTotal,
    missingCheckout: presenceTableStates.missingCheckout.rawRows.length,
    cadastro: registeredUsersTotal,
    eventos: eventsTotal,
    "banco-dados": databaseEventsState.total,
  };

  Object.entries(counts).forEach(([key, value]) => {
    document.querySelectorAll(`[data-dashboard-stat-value="${key}"]`).forEach((element) => {
      element.textContent = String(value);
    });
    document.querySelectorAll(`[data-tab-count-for="${key}"]`).forEach((element) => {
      element.textContent = String(value);
    });
  });

  const criticalPendingLabel = counts.missingCheckout === 0
    ? "Nenhuma pendência crítica"
    : counts.missingCheckout === 1
      ? "1 check-out pendente"
      : `${counts.missingCheckout} check-outs pendentes`;

  const adminCoverageLabel = administratorsTotal === 0
    ? "Sem administradores visíveis"
    : administratorsTotal === 1
      ? "1 administrador visível"
      : `${administratorsTotal} administradores visíveis`;

  setTextContentIfPresent("heroMetricPending", criticalPendingLabel);
  setTextContentIfPresent("heroMetricAdminCoverage", adminCoverageLabel);
  updateOperationalChrome();
}

function markDashboardRefreshed() {
  lastDashboardRefreshAt = new Date();
  updateOperationalChrome();
}

function capturePresencePageScroll() {
  if (typeof window === "undefined" || !["checkin", "checkout"].includes(activeTab)) {
    return null;
  }

  const scrollingElement = document.scrollingElement;
  return {
    x: window.scrollX,
    y: window.scrollY,
    elementTop: scrollingElement ? scrollingElement.scrollTop : null,
    elementLeft: scrollingElement ? scrollingElement.scrollLeft : null,
  };
}

function restorePresencePageScroll(snapshot) {
  if (!snapshot || typeof window === "undefined") {
    return;
  }

  const applySnapshot = () => {
    window.scrollTo(snapshot.x, snapshot.y);
    const scrollingElement = document.scrollingElement;
    if (scrollingElement && snapshot.elementTop !== null && snapshot.elementLeft !== null) {
      scrollingElement.scrollTop = snapshot.elementTop;
      scrollingElement.scrollLeft = snapshot.elementLeft;
    }
  };

  window.requestAnimationFrame(() => {
    applySnapshot();
    window.requestAnimationFrame(applySnapshot);
  });
}

function showAuthShell(message = "", kind = "info") {
  isAuthenticated = false;
  resetAdminAccessState();
  currentAdminChave = "";
  currentAdminProjectNames = [];
  currentAdminProjectScopeResolved = false;
  currentAdminProjectScopeLoadPromise = null;
  locationSettingsDirty = false;
  lastDashboardRefreshAt = null;
  closeChangePasswordModal();
  eventsRows = null;
  formsTotal = 0;
  formsRows = null;
  reportsResultsPayload = null;
  databaseEventsLoaded = false;
  if (databaseEventsRefreshTimer !== null) {
    window.clearTimeout(databaseEventsRefreshTimer);
    databaseEventsRefreshTimer = null;
  }
  databaseEventsState.page = 1;
  databaseEventsState.total = 0;
  databaseEventsState.totalPages = 1;
  databaseEventsState.pageSize = DATABASE_EVENTS_PAGE_SIZE;
  databaseEventsState.filters = createDefaultDatabaseEventFilters();
  databaseEventsState.sortKey = DATABASE_EVENT_DEFAULT_SORT_KEY;
  databaseEventsState.sortDirection = DATABASE_EVENT_DEFAULT_SORT_DIRECTION;
  databaseEventsState.filterOptions = {
    action: [],
    chave: [],
    rfid: [],
    project: [],
    source: [],
    status: [],
  };
  syncDatabaseEventFilterOptions();
  syncDatabaseEventFilterInputs();
  syncDatabaseEventSortHeaders();
  authShell.classList.remove("hidden");
  adminShell.classList.add("hidden");
  sessionBar.classList.add("hidden");
  stopRealtimeUpdates();
  stopAutoRefresh();
  setAuthStatus(message, kind);
  resetReportsView();
  clearStatus();
  syncAdminResponsiveState({ force: true });
  updateOperationalChrome();
}

function showAdminShell(admin) {
  isAuthenticated = true;
  setAdminAccessState(admin);
  currentAdminChave = String(admin?.chave ?? "").trim().toUpperCase();
  currentAdminProjectNames = [];
  currentAdminProjectScopeResolved = false;
  currentAdminProjectScopeLoadPromise = null;
  authShell.classList.add("hidden");
  adminShell.classList.remove("hidden");
  sessionBar.classList.remove("hidden");
  sessionUserLabel.textContent = `${admin.nome_completo} (${admin.chave})`;
  setAuthStatus("");
  syncAdminResponsiveState({ force: true });
  updateOperationalChrome();
}

function applyResponsiveLabels(tbodyId) {
  const body = document.getElementById(tbodyId);
  if (!body) {
    return;
  }
  const table = body.closest("table");
  if (!table) {
    return;
  }
  const headers = Array.from(table.querySelectorAll("thead th")).map((th) => {
    const sortableLabel = th.querySelector(".sortable-header span")?.textContent?.trim();
    return sortableLabel || th.textContent.trim();
  });
  body.querySelectorAll("tr").forEach((tr) => {
    Array.from(tr.children).forEach((cell, idx) => {
      if (cell.tagName === "TD") {
        cell.setAttribute("data-label", headers[idx] || "Campo");
      }
    });
  });
}

function escapeHtml(value) {
  return String(value ?? "-")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function updateAdaptiveInputWidth(input, minimumCharacters = 4) {
  if (!(input instanceof HTMLInputElement)) {
    return;
  }
  const characterCount = Math.max(minimumCharacters, String(input.value || "").trim().length || 0);
  input.style.width = `${characterCount + 1}ch`;
}

function bindAdaptiveInputWidth(input, minimumCharacters = 4) {
  if (!(input instanceof HTMLInputElement)) {
    return;
  }
  updateAdaptiveInputWidth(input, minimumCharacters);
  input.addEventListener("input", () => updateAdaptiveInputWidth(input, minimumCharacters));
}

function updateAutoTextareaHeight(textarea) {
  if (!(textarea instanceof HTMLTextAreaElement)) {
    return;
  }

  const minimumHeightPx = Number(textarea.dataset.minHeightPx || 0);
  textarea.style.height = "auto";
  textarea.style.height = `${Math.max(textarea.scrollHeight, minimumHeightPx)}px`;
}

function bindAutoTextareaHeight(textarea) {
  if (!(textarea instanceof HTMLTextAreaElement)) {
    return;
  }

  if (!textarea.dataset.minHeightPx) {
    textarea.style.height = "auto";
    textarea.dataset.minHeightPx = String(textarea.scrollHeight);
  }
  updateAutoTextareaHeight(textarea);
  textarea.addEventListener("input", () => updateAutoTextareaHeight(textarea));
}

function refreshUserFieldTextareaHeights() {
  document.querySelectorAll(".user-field-textarea").forEach((textarea) => {
    updateAutoTextareaHeight(textarea);
  });
}

function scheduleUserFieldTextareaRefresh() {
  if (userTextareaRefreshFrame !== null) {
    window.cancelAnimationFrame(userTextareaRefreshFrame);
  }

  userTextareaRefreshFrame = window.requestAnimationFrame(() => {
    userTextareaRefreshFrame = null;
    refreshUserFieldTextareaHeights();
  });
}

function resolveDisplayTimeZoneName(timezoneName) {
  const normalizedValue = String(timezoneName ?? "").trim();
  return normalizedValue || DEFAULT_DISPLAY_TIMEZONE;
}

function resolveDisplayTimeZoneLabel(timezoneLabel) {
  const normalizedValue = String(timezoneLabel ?? "").trim();
  return normalizedValue || DEFAULT_TIMEZONE_LABEL;
}

function formatDateTime(value, timezoneName = DEFAULT_DISPLAY_TIMEZONE) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).replace("T", " ").replace(/\.\d+Z?$/, "").replace(/Z$/, "");
  }

  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: resolveDisplayTimeZoneName(timezoneName),
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function formatDateTimeLines(value, timezoneName = DEFAULT_DISPLAY_TIMEZONE) {
  const formatted = formatDateTime(value, timezoneName);
  if (formatted === "-") {
    return { date: "-", time: "" };
  }

  const [datePart, timePart, ...rest] = String(formatted).split(" ");
  return {
    date: datePart || formatted,
    time: [timePart, ...rest].filter(Boolean).join(" "),
  };
}

function getDayKey(value, timezoneName = DEFAULT_DISPLAY_TIMEZONE) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: resolveDisplayTimeZoneName(timezoneName),
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);

  const year = parts.find((part) => part.type === "year")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  const day = parts.find((part) => part.type === "day")?.value;
  if (!year || !month || !day) {
    return null;
  }

  return `${year}-${month}-${day}`;
}

function formatLocal(local) {
  if (local === "main") {
    return "Escritório Principal";
  }
  if (local === "co80") {
    return "Escritório Avançado P80";
  }
  if (local === "un80") {
    return "A bordo da P80";
  }
  if (local === "co83") {
    return "Escritório Avançado P83";
  }
  if (local === "un83") {
    return "A bordo da P83";
  }
  return local || "-";
}

function formatAction(action) {
  if (action === "checkin") {
    return "Check-In";
  }
  if (action === "checkout") {
    return "Check-Out";
  }
  if (action === "register") {
    return "Cadastro";
  }
  if (action === "admin_request") {
    return "Solicitação Admin";
  }
  if (action === "admin_access") {
    return "Admin";
  }
  if (action === "password") {
    return "Senha";
  }
  if (action === "location") {
    return "Localização";
  }
  if (action === "location_config" || action === "location_setting") {
    return "Configuração de Localização";
  }
  if (action === "event_archive") {
    return "Arquivo Eventos";
  }
  return action;
}

function formatEventDetails(details) {
  if (!details) {
    return "-";
  }

  const cleanedParts = String(details)
    .split(";")
    .map((part) => part.trim())
    .filter((part) => part && !part.startsWith("final_url="));

  return cleanedParts.length > 0 ? cleanedParts.join("; ") : "-";
}

function makeEventCell(value, extraClass = "") {
  const className = extraClass ? `event-cell ${extraClass}` : "event-cell";
  return `<span class="${className}">${escapeHtml(value ?? "-")}</span>`;
}

function makeEventDateTimeCell(value, timezoneName = DEFAULT_DISPLAY_TIMEZONE, options = {}) {
  const { date, time } = formatDateTimeLines(value, timezoneName);
  return makeEventDateTimeCellFromParts(date, time, options);
}

function makeEventDateTimeCellFromParts(dateLabel, timeLabel, options = {}) {
  const normalizedDate = String(dateLabel ?? "").trim() || "-";
  const normalizedTime = String(timeLabel ?? "").trim();
  const inline = Boolean(options.inline && normalizedTime);
  const className = inline
    ? "event-cell event-datetime-cell event-datetime-cell--inline"
    : "event-cell event-datetime-cell";
  return `
    <span class="${className}">
      <span class="event-datetime-line">${escapeHtml(normalizedDate)}</span>
      ${normalizedTime ? `<span class="event-datetime-line">${escapeHtml(normalizedTime)}</span>` : ""}
    </span>
  `;
}

function makeEventDetailsButton() {
  return '<button type="button" class="event-details-button">Detalhes</button>';
}

function buildDatabaseEventsQueryParams() {
  const params = new URLSearchParams();
  params.set("page", String(databaseEventsState.page));
  params.set("page_size", String(databaseEventsState.pageSize));
  params.set("sort_by", databaseEventsState.sortKey);
  params.set("sort_direction", databaseEventsState.sortDirection);

  const normalizedKey = databaseEventsState.filters.chave.trim().toUpperCase();
  const normalizedRfid = databaseEventsState.filters.rfid.trim();
  const normalizedSearch = databaseEventsState.filters.search.trim();
  const normalizedSource = databaseEventsState.filters.source.trim().toLowerCase();
  const normalizedStatus = databaseEventsState.filters.status.trim().toLowerCase();
  const normalizedAction = databaseEventsState.filters.action.trim().toLowerCase();
  const normalizedProject = databaseEventsState.filters.project.trim().toUpperCase();

  if (normalizedSearch) {
    params.set("search", normalizedSearch);
  }
  if (normalizedKey) {
    params.set("chave", normalizedKey);
  }
  if (normalizedRfid) {
    params.set("rfid", normalizedRfid);
  }
  if (normalizedAction) {
    params.set("action", normalizedAction);
  }
  if (normalizedProject) {
    params.set("project", normalizedProject);
  }
  if (normalizedSource) {
    params.set("source", normalizedSource);
  }
  if (normalizedStatus) {
    params.set("status", normalizedStatus);
  }
  if (databaseEventsState.filters.fromDate) {
    params.set("from_date", databaseEventsState.filters.fromDate);
  }
  if (databaseEventsState.filters.toDate) {
    params.set("to_date", databaseEventsState.filters.toDate);
  }

  return params;
}

function syncDatabaseEventFilterInputs() {
  const textInputIds = {
    search: "databaseEventsSearch",
    fromDate: "databaseEventsFromDate",
    toDate: "databaseEventsToDate",
  };

  Object.entries(textInputIds).forEach(([filterKey, elementId]) => {
    const element = document.getElementById(elementId);
    if (element) {
      element.value = databaseEventsState.filters[filterKey] ?? "";
    }
  });

  const selectFilterIds = {
    chave: "databaseEventsKey",
    rfid: "databaseEventsRfid",
    action: "databaseEventsAction",
    project: "databaseEventsProject",
    source: "databaseEventsSource",
    status: "databaseEventsStatus",
  };

  Object.entries(selectFilterIds).forEach(([filterKey, elementId]) => {
    const selectElement = document.getElementById(elementId);
    if (selectElement instanceof HTMLSelectElement) {
      selectElement.value = databaseEventsState.filters[filterKey] ?? "";
    }
  });
}

function syncDatabaseEventFilterOptions() {
  const filterSelects = {
    chave: "databaseEventsKey",
    rfid: "databaseEventsRfid",
    action: "databaseEventsAction",
    project: "databaseEventsProject",
    source: "databaseEventsSource",
    status: "databaseEventsStatus",
  };

  Object.entries(filterSelects).forEach(([filterKey, elementId]) => {
    const selectElement = document.getElementById(elementId);
    if (!(selectElement instanceof HTMLSelectElement)) {
      return;
    }

    const optionValues = Array.isArray(databaseEventsState.filterOptions[filterKey])
      ? databaseEventsState.filterOptions[filterKey]
      : [];
    const currentValue = String(databaseEventsState.filters[filterKey] || "").trim();
    const values = currentValue && !optionValues.includes(currentValue)
      ? [currentValue, ...optionValues]
      : optionValues;
    const fragment = document.createDocumentFragment();
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "Todos";
    fragment.appendChild(defaultOption);
    values.forEach((optionValue) => {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionValue;
      fragment.appendChild(option);
    });
    selectElement.replaceChildren(fragment);
    selectElement.value = values.includes(currentValue) ? currentValue : "";
    if (!values.includes(currentValue)) {
      databaseEventsState.filters[filterKey] = "";
    }
  });
}

function getDatabaseEventDefaultSortDirection(sortKey) {
  if (["id", "event_time", "http_status"].includes(sortKey)) {
    return "desc";
  }
  return "asc";
}

function syncDatabaseEventSortHeaders() {
  document.querySelectorAll('.sortable-header[data-sort-table="databaseEvents"]').forEach((button) => {
    const isActive = button.dataset.sortKey === databaseEventsState.sortKey;
    button.classList.toggle("is-active", isActive);
    const indicator = button.querySelector(".sort-indicator");
    if (indicator) {
      indicator.textContent = isActive ? (databaseEventsState.sortDirection === "asc" ? "↑" : "↓") : "↕";
    }
    const parentHeader = button.closest("th");
    if (parentHeader) {
      parentHeader.setAttribute(
        "aria-sort",
        isActive ? (databaseEventsState.sortDirection === "asc" ? "ascending" : "descending") : "none",
      );
    }
  });
}

function applyDatabaseEventSort(sortKey) {
  if (!sortKey) {
    return;
  }

  if (databaseEventsState.sortKey === sortKey) {
    databaseEventsState.sortDirection = databaseEventsState.sortDirection === "asc" ? "desc" : "asc";
  } else {
    databaseEventsState.sortKey = sortKey;
    databaseEventsState.sortDirection = getDatabaseEventDefaultSortDirection(sortKey);
  }

  databaseEventsState.page = 1;
  syncDatabaseEventSortHeaders();
}

function updateDatabaseEventsInsights(rows) {
  const visibleCount = rows.length;
  const visibleCheckins = rows.filter((row) => row.action === "checkin").length;
  const visibleCheckouts = rows.filter((row) => row.action === "checkout").length;
  const total = databaseEventsState.total;
  const page = databaseEventsState.page;
  const totalPages = databaseEventsState.totalPages;
  const startRow = total === 0 ? 0 : (page - 1) * databaseEventsState.pageSize + 1;
  const endRow = total === 0 ? 0 : startRow + visibleCount - 1;

  setTextContentIfPresent("databaseEventsTotalCount", String(total));
  setTextContentIfPresent("databaseEventsVisibleCount", String(visibleCount));
  setTextContentIfPresent("databaseEventsCheckinCount", String(visibleCheckins));
  setTextContentIfPresent("databaseEventsCheckoutCount", String(visibleCheckouts));
  setTextContentIfPresent(
    "databaseEventsResultSummary",
    total === 1 ? "1 evento encontrado" : `${total} eventos encontrados`,
  );
  setTextContentIfPresent("databaseEventsPageInfo", `Página ${page} de ${totalPages}`);
  setTextContentIfPresent(
    "databaseEventsPaginationSummary",
    total === 0 ? "Nenhum evento corresponde aos filtros atuais." : `Mostrando ${startRow}-${endRow} de ${total} eventos.`,
  );

  const previousButton = document.getElementById("databaseEventsPrev");
  if (previousButton) {
    previousButton.disabled = page <= 1 || total === 0;
  }
  const nextButton = document.getElementById("databaseEventsNext");
  if (nextButton) {
    nextButton.disabled = page >= totalPages || total === 0;
  }
}

function renderDatabaseEvents(rows) {
  const body = document.getElementById("databaseEventsBody");
  if (!body) {
    return;
  }

  body.innerHTML = "";
  if (!rows.length) {
    renderEmptyStateRow("databaseEventsBody", 14, "Nenhum evento encontrado para os filtros informados.");
    updateDatabaseEventsInsights([]);
    return;
  }

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    const eventDetails = {
      message: row.message ?? "-",
      details: formatEventDetails(row.details),
    };
    tr.innerHTML = `<td>${makeEventCell(row.id)}</td><td>${makeEventDateTimeCell(row.event_time, row.timezone_name)}</td><td>${makeEventCell(formatAction(row.action))}</td><td>${makeEventCell(row.chave ?? "-")}</td><td>${makeEventCell(row.rfid ?? "-")}</td><td>${makeEventCell(row.project ?? "-")}</td><td>${makeEventCell(formatTimeZoneLabel(row.timezone_label))}</td><td>${makeEventCell(formatLocal(row.local), "event-cell-left")}</td><td>${makeEventCell(row.source ?? "-")}</td><td>${makeEventCell(row.status ?? "-")}</td><td>${makeEventCell(row.http_status ?? "-")}</td><td>${makeEventCell(row.device_id ?? "-", "event-cell-left")}</td><td>${makeEventCell(row.message ?? "-", "event-cell-left")}</td><td>${makeEventDetailsButton()}</td>`;
    tr.querySelector(".event-details-button").addEventListener("click", () => openEventDetails(eventDetails));
    body.appendChild(tr);
  });

  applyResponsiveLabels("databaseEventsBody");
  updateDatabaseEventsInsights(rows);
}

function scheduleDatabaseEventsRefresh(delayMs = REALTIME_DEBOUNCE_MS) {
  if (!isAuthenticated || !document.getElementById("databaseEventsBody")) {
    return;
  }

  if (databaseEventsRefreshTimer !== null) {
    window.clearTimeout(databaseEventsRefreshTimer);
  }

  databaseEventsRefreshTimer = window.setTimeout(() => {
    loadDatabaseEvents().catch((error) => setStatus(error.message, false));
    databaseEventsRefreshTimer = null;
  }, delayMs);
}

function resetDatabaseEventFilters() {
  databaseEventsState.page = 1;
  databaseEventsState.total = 0;
  databaseEventsState.totalPages = 1;
  databaseEventsState.filters = createDefaultDatabaseEventFilters();
  syncDatabaseEventFilterInputs();
}

async function loadDatabaseEvents() {
  if (!document.getElementById("databaseEventsBody")) {
    return;
  }

  const { fromDate, toDate } = databaseEventsState.filters;
  if (fromDate && toDate && fromDate > toDate) {
    throw new Error("O período informado é inválido. Ajuste as datas de início e fim.");
  }

  const params = buildDatabaseEventsQueryParams();
  const payload = await fetchJson(`/api/admin/database-events?${params.toString()}`);
  const rows = Array.isArray(payload?.items) ? payload.items : [];

  databaseEventsLoaded = true;
  databaseEventsState.total = Number(payload?.total) || 0;
  databaseEventsState.page = Number(payload?.page) || 1;
  databaseEventsState.pageSize = Number(payload?.page_size) || DATABASE_EVENTS_PAGE_SIZE;
  databaseEventsState.totalPages = Math.max(1, Number(payload?.total_pages) || 1);
  databaseEventsState.filterOptions = {
    action: Array.isArray(payload?.filter_options?.action) ? payload.filter_options.action : [],
    chave: Array.isArray(payload?.filter_options?.chave) ? payload.filter_options.chave : [],
    rfid: Array.isArray(payload?.filter_options?.rfid) ? payload.filter_options.rfid : [],
    project: Array.isArray(payload?.filter_options?.project) ? payload.filter_options.project : [],
    source: Array.isArray(payload?.filter_options?.source) ? payload.filter_options.source : [],
    status: Array.isArray(payload?.filter_options?.status) ? payload.filter_options.status : [],
  };

  syncDatabaseEventFilterOptions();
  syncDatabaseEventFilterInputs();
  syncDatabaseEventSortHeaders();
  renderDatabaseEvents(rows);
  updateDashboardSummary();
}

function formatOntime(value) {
  if (value === true) return "Sim";
  if (value === false) return "Não";
  return "-";
}

function parseErrorPayload(payload, fallback) {
  if (!payload) {
    return fallback;
  }
  if (typeof payload.detail === "string") {
    return payload.detail;
  }
  if (Array.isArray(payload.detail) && payload.detail.length > 0) {
    return payload.detail.map((item) => item.msg || item.message || "Erro de validação").join("; ");
  }
  return fallback;
}

async function parseErrorResponse(res) {
  let payload = null;
  try {
    payload = await res.json();
  } catch {
    payload = null;
  }

  if (res.status === 401) {
    return parseErrorPayload(payload, "Sua sessão expirou. Faça login novamente.");
  }
  return parseErrorPayload(payload, `HTTP ${res.status}`);
}

async function handleUnauthorized(message) {
  if (!isAuthenticated) {
    setAuthStatus(message, "error");
    return;
  }

  showAuthShell(message || "Sua sessão expirou. Faça login novamente.", "error");
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const message = await parseErrorResponse(res);
    if (res.status === 401) {
      await handleUnauthorized(message);
    }
    throw new Error(message);
  }

  if (res.status === 204) {
    return null;
  }

  return res.json();
}

async function postJson(url, body) {
  const options = {
    method: "POST",
    headers: {},
  };
  if (body !== null && body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  return fetchJson(url, options);
}

async function putJson(url, body) {
  const options = {
    method: "PUT",
    headers: {},
  };
  if (body !== null && body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  return fetchJson(url, options);
}

async function deleteJson(url) {
  return fetchJson(url, { method: "DELETE" });
}

function requireIntegerId(value, label) {
  const normalized = String(value ?? "").trim();
  if (!/^\d+$/.test(normalized)) {
    throw new Error(`${label} inválido para esta ação.`);
  }
  return normalized;
}

function switchTab(tab) {
  if (!isAdminTabAllowed(tab)) {
    return;
  }

  activeTab = tab;
  document.querySelectorAll(".tabs button").forEach((button) => button.classList.remove("active"));
  const targetButton = document.querySelector(`.tabs button[data-tab="${tab}"]`);
  const targetTab = document.getElementById(`tab-${tab}`);
  if (!targetButton || !targetTab) {
    return;
  }
  targetButton.classList.add("active");
  document.querySelectorAll(".tab").forEach((el) => el.classList.remove("active"));
  targetTab.classList.add("active");
  syncAdminTabStrip();
  updateOperationalChrome();
  refreshActiveTab().catch((error) => setStatus(error.message, false));
}

function openEventDetails({ message, details }) {
  const modal = document.getElementById("eventDetailsModal");
  document.getElementById("eventMessageText").value = message || "-";
  document.getElementById("eventDetailsText").value = details || "-";
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

function closeEventDetails() {
  const modal = document.getElementById("eventDetailsModal");
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
}

function openEventArchivesModal() {
  const modal = document.getElementById("eventArchivesModal");
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

function closeEventArchivesModal() {
  const modal = document.getElementById("eventArchivesModal");
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
}

function setRequestAdminStatus(message, kind = "info") {
  if (!requestAdminStatus) {
    return;
  }

  requestAdminStatus.textContent = message || "";
  requestAdminStatus.className = `auth-status ${kind === "error" ? "status-err" : kind === "success" ? "status-ok" : ""}`;
}

function setRequestAdminRegistrationStatus(message, kind = "info") {
  if (!requestAdminRegistrationStatus) {
    return;
  }

  requestAdminRegistrationStatus.textContent = message || "";
  requestAdminRegistrationStatus.className = `auth-status ${kind === "error" ? "status-err" : kind === "success" ? "status-ok" : ""}`;
}

function cancelRequestAdminLookup() {
  if (requestAdminLookupTimeout) {
    window.clearTimeout(requestAdminLookupTimeout);
    requestAdminLookupTimeout = null;
  }
  requestAdminLookupRequestToken += 1;
}

function isAdminRequestKeyValid(chave) {
  return /^[A-Z0-9]{4}$/.test(String(chave || ""));
}

function isAdminRequestPasswordValid(value) {
  return value.length >= 3 && value.length <= 10 && value.trim().length > 0;
}

function syncRequestAdminRegistrationFormState() {
  if (!requestAdminRegistrationSaveButton) {
    return;
  }

  const nome = requestAdminRegistrationNomeInput ? requestAdminRegistrationNomeInput.value.trim() : "";
  const projeto = requestAdminRegistrationProjetoSelect ? requestAdminRegistrationProjetoSelect.value.trim() : "";
  const senha = requestAdminRegistrationSenhaInput ? requestAdminRegistrationSenhaInput.value : "";
  const confirmarSenha = requestAdminRegistrationConfirmInput ? requestAdminRegistrationConfirmInput.value : "";
  const canSave = nome.length >= 3
    && projeto.length >= 2
    && isAdminRequestPasswordValid(senha)
    && senha === confirmarSenha
    && !requestAdminRegistrationSaveInProgress;
  requestAdminRegistrationSaveButton.disabled = !canSave;
}

async function loadRequestAdminProjects(selectedValue = "") {
  const rows = projectCatalog.length > 0 ? projectCatalog : await fetchJson("/api/web/projects");
  setProjectCatalog(rows);
  const optionValues = getProjectOptions(selectedValue, { includeDetachedValue: true });
  syncSelectOptions(requestAdminRegistrationProjetoSelect, optionValues, selectedValue || optionValues[0] || "");
}

function resetRequestAdminRegistrationState(options = {}) {
  const preserveKey = options.preserveKey === true;
  if (requestAdminRegistrationChaveInput && !preserveKey) {
    requestAdminRegistrationChaveInput.value = "";
  }
  if (requestAdminRegistrationNomeInput) {
    requestAdminRegistrationNomeInput.value = "";
  }
  if (requestAdminRegistrationSenhaInput) {
    requestAdminRegistrationSenhaInput.value = "";
  }
  if (requestAdminRegistrationConfirmInput) {
    requestAdminRegistrationConfirmInput.value = "";
  }
  setRequestAdminRegistrationStatus("");
  syncRequestAdminRegistrationFormState();
}

function openRequestAdminModal() {
  cancelRequestAdminLookup();
  if (requestAdminRegistrationModal) {
    requestAdminRegistrationModal.classList.add("hidden");
    requestAdminRegistrationModal.setAttribute("aria-hidden", "true");
  }
  resetRequestAdminRegistrationState();
  setRequestAdminStatus("");
  if (requestAdminChaveInput) {
    requestAdminChaveInput.value = "";
  }
  if (!requestAdminModal) {
    return;
  }
  requestAdminModal.classList.remove("hidden");
  requestAdminModal.setAttribute("aria-hidden", "false");
  if (requestAdminChaveInput) {
    requestAdminChaveInput.focus();
  }
}

function closeRequestAdminModal() {
  cancelRequestAdminLookup();
  if (requestAdminModal) {
    requestAdminModal.classList.add("hidden");
    requestAdminModal.setAttribute("aria-hidden", "true");
  }
  if (requestAdminChaveInput) {
    requestAdminChaveInput.value = "";
  }
  setRequestAdminStatus("");
}

function closeRequestAdminRegistrationModal() {
  if (!requestAdminRegistrationModal) {
    return;
  }
  requestAdminRegistrationModal.classList.add("hidden");
  requestAdminRegistrationModal.setAttribute("aria-hidden", "true");
  resetRequestAdminRegistrationState();
}

async function openRequestAdminRegistrationModal(chave) {
  if (!requestAdminRegistrationModal || !requestAdminRegistrationChaveInput) {
    return;
  }

  requestAdminRegistrationChaveInput.value = chave;
  await loadRequestAdminProjects();
  resetRequestAdminRegistrationState({ preserveKey: true });
  if (requestAdminModal) {
    requestAdminModal.classList.add("hidden");
    requestAdminModal.setAttribute("aria-hidden", "true");
  }
  requestAdminRegistrationModal.classList.remove("hidden");
  requestAdminRegistrationModal.setAttribute("aria-hidden", "false");
  syncRequestAdminRegistrationFormState();
  if (requestAdminRegistrationNomeInput) {
    requestAdminRegistrationNomeInput.focus();
  }
}

function returnToRequestAdminLookupModal() {
  const chave = requestAdminRegistrationChaveInput ? requestAdminRegistrationChaveInput.value : "";
  closeRequestAdminRegistrationModal();
  if (!requestAdminModal) {
    return;
  }
  requestAdminModal.classList.remove("hidden");
  requestAdminModal.setAttribute("aria-hidden", "false");
  if (requestAdminChaveInput) {
    requestAdminChaveInput.value = chave;
    requestAdminChaveInput.focus();
    if (typeof requestAdminChaveInput.select === "function") {
      requestAdminChaveInput.select();
    }
  }
  setRequestAdminStatus("Corrija a chave ou informe outra para continuar.");
}

async function submitRequestAdminKnownUser(chave, requestToken) {
  if (requestAdminSelfServiceInProgress) {
    return;
  }

  requestAdminSelfServiceInProgress = true;
  try {
    const payload = await postJson("/api/admin/auth/request-access/self-service", { chave });
    if (requestToken !== requestAdminLookupRequestToken || !requestAdminModal || requestAdminModal.classList.contains("hidden")) {
      return;
    }

    setRequestAdminStatus(payload.message, "success");
    setAuthStatus(payload.message, "success");
    window.setTimeout(() => {
      if (requestToken !== requestAdminLookupRequestToken) {
        return;
      }
      closeRequestAdminModal();
    }, 700);
  } finally {
    requestAdminSelfServiceInProgress = false;
  }
}

async function lookupRequestAdminChave(chave, requestToken) {
  if (requestToken !== requestAdminLookupRequestToken || !requestAdminModal || requestAdminModal.classList.contains("hidden")) {
    return;
  }

  setRequestAdminStatus("Verificando chave...");
  const payload = await fetchJson(`/api/admin/auth/request-access/status?chave=${encodeURIComponent(chave)}`);
  if (requestToken !== requestAdminLookupRequestToken || !requestAdminModal || requestAdminModal.classList.contains("hidden")) {
    return;
  }

  if (!payload.found) {
    await openRequestAdminRegistrationModal(chave);
    setRequestAdminRegistrationStatus(payload.message);
    return;
  }

  if (payload.is_admin || payload.has_pending_request || !payload.has_password) {
    const kind = payload.has_pending_request ? "info" : "error";
    setRequestAdminStatus(payload.message, kind);
    return;
  }

  setRequestAdminStatus("Chave cadastrada. Enviando solicitacao...");
  await submitRequestAdminKnownUser(chave, requestToken);
}

function scheduleRequestAdminLookup() {
  if (!requestAdminChaveInput) {
    return;
  }

  const chave = normalizeAdminChave(requestAdminChaveInput.value);
  if (requestAdminChaveInput.value !== chave) {
    requestAdminChaveInput.value = chave;
  }

  if (requestAdminLookupTimeout) {
    window.clearTimeout(requestAdminLookupTimeout);
    requestAdminLookupTimeout = null;
  }

  setRequestAdminStatus("");
  if (!chave) {
    return;
  }
  if (!/^[A-Z0-9]{0,4}$/.test(chave)) {
    setRequestAdminStatus("A chave deve ter 4 caracteres alfanumericos.", "error");
    return;
  }
  if (!isAdminRequestKeyValid(chave)) {
    setRequestAdminStatus("Digite os 4 caracteres da chave para continuar.");
    return;
  }

  const requestToken = ++requestAdminLookupRequestToken;
  requestAdminLookupTimeout = window.setTimeout(() => {
    lookupRequestAdminChave(chave, requestToken).catch((error) => {
      if (requestToken !== requestAdminLookupRequestToken) {
        return;
      }
      setRequestAdminStatus(error.message, "error");
    });
  }, ADMIN_REQUEST_LOOKUP_DEBOUNCE_MS);
}

function updateUserTitle(targetId, totalRows, totalRegistered) {
  if (targetId === "checkinBody") {
    document.getElementById("checkinTitle").textContent = `Usuários em Check-In (${totalRows}/${totalRegistered})`;
    return;
  }
  if (targetId === "checkoutBody") {
    document.getElementById("checkoutTitle").textContent = `Usuários em Check-Out (${totalRows}/${totalRegistered})`;
  }
}

function updateInactiveTitle(totalRows) {
  document.getElementById("inactiveTitle").textContent = `Usuários Inativos (${totalRows})`;
}

function updateMissingCheckoutTitle(totalRows) {
  document.getElementById("missingCheckoutTitle").textContent = `Usuários com Check-in e sem Check-Out (${totalRows})`;
}

function countRenderedDataRows(bodyId) {
  return document.querySelectorAll(`#${bodyId} tr:not(.empty-state-row)`).length;
}

function syncUserTitles() {
  updateUserTitle("checkinBody", countRenderedDataRows("checkinBody"), registeredUsersTotal);
  updateUserTitle("checkoutBody", countRenderedDataRows("checkoutBody"), registeredUsersTotal);
  updateDashboardSummary();
}

function getCalendarDayDiff(value, timezoneName = DEFAULT_DISPLAY_TIMEZONE) {
  const eventDayKey = getDayKey(value, timezoneName);
  return getCalendarDayDiffFromDayKey(eventDayKey, timezoneName);
}

function getCalendarDayDiffFromDayKey(dayKey, timezoneName = DEFAULT_DISPLAY_TIMEZONE) {
  const normalizedDayKey = String(dayKey ?? "").trim();
  const todayKey = getDayKey(undefined, timezoneName);
  if (!normalizedDayKey || !todayKey) {
    return 0;
  }

  const eventMidnightUtcMs = Date.parse(`${normalizedDayKey}T00:00:00Z`);
  const todayMidnightUtcMs = Date.parse(`${todayKey}T00:00:00Z`);
  if (Number.isNaN(eventMidnightUtcMs) || Number.isNaN(todayMidnightUtcMs)) {
    return 0;
  }

  const diffDays = Math.floor((todayMidnightUtcMs - eventMidnightUtcMs) / (24 * 60 * 60 * 1000));
  return Math.max(0, diffDays);
}

function formatElapsedDays(days) {
  return days === 1 ? "há 1 dia" : `há ${days} dias`;
}

function formatUserTableTime(value, timezoneName = DEFAULT_DISPLAY_TIMEZONE) {
  const formatted = formatDateTime(value, timezoneName);
  const calendarDayDiff = getCalendarDayDiff(value, timezoneName);
  if (!calendarDayDiff) {
    return { formatted, elapsedDays: 0, isStale: false };
  }

  return {
    formatted: `${formatted} (${formatElapsedDays(calendarDayDiff)})`,
    elapsedDays: calendarDayDiff,
    isStale: true,
  };
}

function formatTimeZoneLabel(timezoneLabel) {
  return resolveDisplayTimeZoneLabel(timezoneLabel);
}

function getPresenceActivityDateLabel(row) {
  const normalizedLabel = String(row?.activity_date_label || "").trim();
  if (normalizedLabel) {
    return normalizedLabel;
  }

  const formatted = formatDateTimeLines(row?.time, row?.timezone_name);
  return formatted.date || "-";
}

function getPresenceActivityTimeLabel(row) {
  const normalizedLabel = String(row?.activity_time_label || "").trim();
  if (normalizedLabel) {
    return normalizedLabel;
  }

  const formatted = formatDateTimeLines(row?.time, row?.timezone_name);
  return formatted.time || "";
}

function getPresenceActivityDayKey(row) {
  const normalizedDayKey = String(row?.activity_day_key || "").trim();
  if (normalizedDayKey) {
    return normalizedDayKey;
  }
  return getDayKey(row?.time, row?.timezone_name) || "";
}

function buildPresencePrimaryDisplayParts(row, options = {}) {
  const { includeElapsedDays = false } = options;
  const baseDateLabel = getPresenceActivityDateLabel(row) || "-";
  const responsiveVariant = options.responsiveVariant || "desktop";
  const timeLabel = responsiveVariant === "desktop" ? getPresenceActivityTimeLabel(row) : "";
  const elapsedDays = includeElapsedDays
    ? getCalendarDayDiffFromDayKey(getPresenceActivityDayKey(row), row?.timezone_name)
    : 0;
  const dateLabel = elapsedDays
    ? `${baseDateLabel} (${formatElapsedDays(elapsedDays)})`
    : baseDateLabel;

  return {
    dateLabel,
    timeLabel,
    elapsedDays,
    isStale: elapsedDays > 0,
  };
}

function buildPresencePrimaryDisplay(row, options = {}) {
  const displayParts = buildPresencePrimaryDisplayParts(row, options);
  const baseValue = displayParts.timeLabel
    ? `${displayParts.dateLabel} ${displayParts.timeLabel}`
    : displayParts.dateLabel;

  if (!displayParts.elapsedDays) {
    return { formatted: baseValue || "-", elapsedDays: 0, isStale: false };
  }

  return {
    formatted: baseValue || "-",
    elapsedDays: displayParts.elapsedDays,
    isStale: displayParts.isStale,
  };
}

function shouldUseInlinePresenceDateTime(displayParts, options = {}) {
  return options.responsiveVariant === "desktop" && Boolean(displayParts?.timeLabel);
}

function buildPresencePrimaryCell(row, options = {}) {
  const displayParts = buildPresencePrimaryDisplayParts(row, options);
  const responsiveVariant = options.responsiveVariant || "desktop";
  return {
    html: makeEventDateTimeCellFromParts(displayParts.dateLabel, displayParts.timeLabel, {
      inline: shouldUseInlinePresenceDateTime(displayParts, { responsiveVariant }),
    }),
    elapsedDays: displayParts.elapsedDays,
    isStale: displayParts.isStale,
  };
}

function buildPresenceMobileMetadata(row, options = {}) {
  return "";
}

function buildLimitedPresenceMobileCard(row, timeCell) {
  const localLabel = escapeHtml(formatLocal(row.local));
  return `<article class="presence-mobile-card presence-mobile-card--limited"><div class="presence-mobile-card-primary">${timeCell.html}</div><p class="presence-mobile-card-main"><span class="presence-mobile-card-name">${escapeHtml(row.nome)}</span><span class="presence-mobile-card-context"> @ </span><span class="presence-mobile-card-local">${localLabel}</span></p></article>`;
}

function buildPresenceMobileCard(row, timeCell, options = {}) {
  if (options.responsiveVariant === "mobile-limited") {
    return buildLimitedPresenceMobileCard(row, timeCell);
  }

  const localLabel = escapeHtml(formatLocal(row.local));
  buildPresenceMobileMetadata(row, options);
  return `<article class="presence-mobile-card presence-mobile-card--compact"><div class="presence-mobile-card-primary">${timeCell.html}</div><p class="presence-mobile-card-main"><span class="presence-mobile-card-name">${escapeHtml(row.nome)}</span><span class="presence-mobile-card-context"> @ </span><span class="presence-mobile-card-local">${localLabel}</span></p></article>`;
}

function buildPresenceRow(row, options = {}) {
  const { highlightMissingCheckout = false, includeElapsedDays = false, responsiveVariant = "desktop" } = options;
  const tr = document.createElement("tr");
  tr.dataset.userId = String(row.id);
  const timeCell = buildPresencePrimaryCell(row, { includeElapsedDays, responsiveVariant });
  const projectsLabel = formatUserMembershipProjects(row);
  const staleCheckin = timeCell.elapsedDays > 0;
  if (highlightMissingCheckout && staleCheckin) {
    tr.classList.add("attention-user-row");
  }

  if (responsiveVariant !== "desktop") {
    tr.classList.add("presence-mobile-row");
    tr.innerHTML = `<td colspan="7" class="presence-mobile-card-cell">${buildPresenceMobileCard(row, timeCell, { responsiveVariant })}</td>`;
    return tr;
  }

  tr.innerHTML = `<td>${timeCell.html}</td><td>${escapeHtml(row.nome)}</td><td>${escapeHtml(row.chave)}</td><td title="${escapeHtml(projectsLabel)}">${escapeHtml(projectsLabel)}</td><td>${escapeHtml(formatTimeZoneLabel(row.timezone_label))}</td><td>${escapeHtml(row.assiduidade ?? "Normal")}</td><td>${escapeHtml(formatLocal(row.local))}</td>`;
  return tr;
}

function renderEmptyStateRow(bodyId, columnCount, message) {
  const body = document.getElementById(bodyId);
  body.innerHTML = "";
  const emptyRow = document.createElement("tr");
  emptyRow.className = "empty-state-row";
  emptyRow.innerHTML = `<td colspan="${columnCount}" class="empty-state-cell">${escapeHtml(message || "Nenhum registro encontrado.")}</td>`;
  body.appendChild(emptyRow);
  applyResponsiveLabels(bodyId);
}

function getPresenceTableState(tableKey) {
  return presenceTableStates[tableKey] || null;
}

function getPresenceDefaultSortDirection(sortKey) {
  if (["time", "latest_time", "inactivity_days"].includes(sortKey)) {
    return "desc";
  }
  return "asc";
}

function getPresenceRowDisplayValue(tableKey, row, key) {
  if (tableKey === "inactive") {
    if (key === "nome") {
      return row.nome || "";
    }
    if (key === "chave") {
      return row.chave || "";
    }
    if (key === "projetos") {
      return formatUserMembershipProjects(row);
    }
    if (key === "latest_time") {
      return `${formatAction(row.latest_action)} - ${formatDateTime(row.latest_time, row.timezone_name)}`;
    }
    if (key === "inactivity_days") {
      return formatInactivityDays(row.inactivity_days);
    }
    return "";
  }

  if (tableKey === "missingCheckout") {
    if (key === "time") {
      return formatUserTableTime(row.time, row.timezone_name).formatted;
    }
    if (key === "nome") {
      return row.nome || "";
    }
    if (key === "chave") {
      return row.chave || "";
    }
    return "";
  }

  if (key === "time") {
    return buildPresencePrimaryDisplay(row, {
      includeElapsedDays: tableKey === "checkin",
      responsiveVariant: getPresenceResponsiveVariant(tableKey),
    }).formatted;
  }
  if (key === "nome") {
    return row.nome || "";
  }
  if (key === "chave") {
    return row.chave || "";
  }
  if (key === "projetos") {
    return formatUserMembershipProjects(row);
  }
  if (key === "assiduidade") {
    return row.assiduidade || "Normal";
  }
  if (key === "local") {
    return formatLocal(row.local);
  }
  return "";
}

function getPresenceRowSortValue(tableKey, row, key) {
  if (tableKey === "inactive") {
    if (key === "latest_time") {
      const parsedTime = Date.parse(row.latest_time || "");
      return Number.isNaN(parsedTime) ? 0 : parsedTime;
    }
    if (key === "inactivity_days") {
      return Number(row.inactivity_days || 0);
    }
    return getPresenceRowDisplayValue(tableKey, row, key);
  }

  if (key === "time") {
    const parsedTime = Date.parse(row.time || "");
    if (!Number.isNaN(parsedTime)) {
      return parsedTime;
    }

    const activityDayKey = getPresenceActivityDayKey(row);
    const parsedDay = Date.parse(activityDayKey ? `${activityDayKey}T00:00:00Z` : "");
    return Number.isNaN(parsedDay) ? 0 : parsedDay;
  }
  return getPresenceRowDisplayValue(tableKey, row, key);
}

function hasActivePresenceFilters(tableKey) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return false;
  }
  return getVisiblePresenceFilterKeys(tableKey)
    .some((key) => String(state.filters[key] || "").trim());
}

function getPresenceEmptyMessage(tableKey) {
  if (hasActivePresenceFilters(tableKey)) {
    return "Nenhum registro encontrado com os filtros atuais.";
  }
  if (tableKey === "inactive") {
    return "Nenhum usuário inativo no momento.";
  }
  if (tableKey === "missingCheckout") {
    return "Nenhum usuário com check-in pendente de check-out no momento.";
  }
  return tableKey === "checkin"
    ? "Nenhum usuário em check-in no momento."
    : "Nenhum usuário em check-out no momento.";
}

function filterPresenceRows(tableKey, rows, filters) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return rows;
  }
  const visibleFilterKeys = getVisiblePresenceFilterKeys(tableKey);
  return rows.filter((row) => visibleFilterKeys.every((key) => {
    const rawFilterValue = String(filters[key] || "").trim();
    if (!rawFilterValue) {
      return true;
    }
    const searchableValue = String(getPresenceRowDisplayValue(tableKey, row, key) || "").toLocaleLowerCase();
    return searchableValue === rawFilterValue.toLocaleLowerCase();
  }));
}

function getPresenceFilterOptions(tableKey, key, rows) {
  const sortedRows = sortPresenceRows(tableKey, rows, key, getPresenceDefaultSortDirection(key));
  const uniqueOptions = new Map();
  sortedRows.forEach((row) => {
    const displayValue = String(getPresenceRowDisplayValue(tableKey, row, key) || "").trim();
    if (!displayValue || uniqueOptions.has(displayValue)) {
      return;
    }
    uniqueOptions.set(displayValue, displayValue);
  });
  return [...uniqueOptions.values()];
}

function refreshPresenceFilterOptions(tableKey) {
  const state = getPresenceTableState(tableKey);
  const container = document.querySelector(`.presence-controls[data-presence-table="${tableKey}"]`);
  if (!state || !container) {
    return;
  }

  container.querySelectorAll("[data-presence-filter]").forEach((control) => {
    const key = control.dataset.presenceFilter;
    const options = getPresenceFilterOptions(tableKey, key, state.rawRows);
    const currentValue = String(state.filters[key] || "");
    const fragment = document.createDocumentFragment();
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "Todos";
    fragment.appendChild(defaultOption);
    options.forEach((optionValue) => {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionValue;
      fragment.appendChild(option);
    });
    control.replaceChildren(fragment);
    if (options.includes(currentValue)) {
      control.value = currentValue;
      return;
    }
    state.filters[key] = "";
    control.value = "";
  });
}

function sortPresenceRows(tableKey, rows, sortKey, sortDirection) {
  const direction = sortDirection === "asc" ? 1 : -1;
  return [...rows].sort((rowA, rowB) => {
    if (["time", "latest_time", "inactivity_days"].includes(sortKey)) {
      const timeDifference = getPresenceRowSortValue(tableKey, rowA, sortKey) - getPresenceRowSortValue(tableKey, rowB, sortKey);
      if (timeDifference !== 0) {
        return timeDifference * direction;
      }
      return String(rowA.nome || "").localeCompare(String(rowB.nome || ""), "pt-BR", {
        sensitivity: "base",
        numeric: true,
      }) * direction;
    }

    return String(getPresenceRowSortValue(tableKey, rowA, sortKey)).localeCompare(
      String(getPresenceRowSortValue(tableKey, rowB, sortKey)),
      "pt-BR",
      { sensitivity: "base", numeric: true },
    ) * direction;
  });
}

function syncPresenceControls(tableKey) {
  const state = getPresenceTableState(tableKey);
  const container = document.querySelector(`.presence-controls[data-presence-table="${tableKey}"]`);
  if (!state || !container) {
    return;
  }

  container.querySelectorAll("[data-presence-filter]").forEach((control) => {
    const key = control.dataset.presenceFilter;
    control.value = state.filters[key] || "";
  });

  syncPresenceResponsiveControls(tableKey);
}

function syncPresenceSortHeaders(tableKey) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return;
  }

  const visibleSortKeys = new Set(getVisiblePresenceSortKeys(tableKey));

  document.querySelectorAll(`.sortable-header[data-sort-table="${tableKey}"]`).forEach((button) => {
    const isVisible = visibleSortKeys.has(button.dataset.sortKey);
    const isActive = button.dataset.sortKey === state.sortKey;
    button.hidden = !isVisible;
    button.disabled = !isVisible;
    button.classList.toggle("hidden", !isVisible);
    button.tabIndex = isVisible ? 0 : -1;
    button.setAttribute("aria-hidden", String(!isVisible));
    button.classList.toggle("is-active", isActive);
    const indicator = button.querySelector(".sort-indicator");
    if (indicator) {
      indicator.textContent = isActive ? (state.sortDirection === "asc" ? "↑" : "↓") : "↕";
    }
    const parentHeader = button.closest("th");
    if (parentHeader) {
      parentHeader.hidden = !isVisible;
      parentHeader.classList.toggle("hidden", !isVisible);
      parentHeader.setAttribute("aria-sort", isActive ? (state.sortDirection === "asc" ? "ascending" : "descending") : "none");
    }
  });
}

function resetPresenceControls(tableKey) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return;
  }
  state.filters = createPresenceFilterState(state.filterColumns);
  state.sortKey = state.defaultSortKey;
  state.sortDirection = state.defaultSortDirection;
  syncPresenceControls(tableKey);
  syncPresenceSortHeaders(tableKey);
}

function applyPresenceTableState(tableKey) {
  const state = getPresenceTableState(tableKey);
  if (!state) {
    return;
  }

  sanitizePresenceSortState(tableKey);
  refreshPresenceFilterOptions(tableKey);
  syncPresenceResponsiveControls(tableKey);
  const filteredRows = filterPresenceRows(tableKey, state.rawRows, state.filters);
  const sortedRows = sortPresenceRows(tableKey, filteredRows, state.sortKey, state.sortDirection);
  if (tableKey === "inactive") {
    renderInactiveTable(sortedRows, { emptyMessage: getPresenceEmptyMessage(tableKey) });
  } else if (tableKey === "missingCheckout") {
    renderMissingCheckoutTable(sortedRows, { emptyMessage: getPresenceEmptyMessage(tableKey) });
  } else {
    renderPresenceTable(state.bodyId, sortedRows, {
      ...state.renderOptions,
      responsiveVariant: getPresenceResponsiveVariant(tableKey),
      emptyMessage: getPresenceEmptyMessage(tableKey),
    });
  }
  syncPresenceSortHeaders(tableKey);
}

function renderPresenceTable(bodyId, rows, options = {}) {
  if (!rows.length) {
    renderEmptyStateRow(bodyId, 7, options.emptyMessage || "Nenhum registro encontrado.");
    updateUserTitle(bodyId, 0, registeredUsersTotal);
    return;
  }
  const body = document.getElementById(bodyId);
  body.innerHTML = "";
  rows.forEach((row) => body.appendChild(buildPresenceRow(row, options)));
  applyResponsiveLabels(bodyId);
  updateUserTitle(bodyId, rows.length, registeredUsersTotal);
}

function formatInactivityDays(days) {
  return days === 1 ? "1 dia" : `${days} dias`;
}

function buildInactiveMobileCard(row) {
  const latestActivityLabel = `${formatAction(row.latest_action)} - ${formatDateTime(row.latest_time, row.timezone_name)}`;
  const projectsLabel = formatUserMembershipProjects(row);
  return `<article class="admin-mobile-card inactive-mobile-card"><strong class="admin-mobile-card-title admin-mobile-card-title--alert">${escapeHtml(row.nome)}</strong><div class="admin-mobile-card-grid"><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Chave</span><span class="admin-mobile-card-value">${escapeHtml(row.chave)}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Projetos</span><span class="admin-mobile-card-value">${escapeHtml(projectsLabel)}</span></div><div class="admin-mobile-card-field admin-mobile-card-field--wide"><span class="admin-mobile-card-label">Última Atividade</span><span class="admin-mobile-card-value">${escapeHtml(latestActivityLabel)}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Inatividade</span><span class="admin-mobile-card-value">${escapeHtml(formatInactivityDays(row.inactivity_days))}</span></div></div><div class="admin-mobile-card-actions"><button type="button" data-user-remove="${escapeHtml(row.id)}">Remover</button></div></article>`;
}

function buildInactiveRow(row, options = {}) {
  const tr = document.createElement("tr");
  tr.dataset.userId = String(row.id);
  tr.classList.add("inactive-user-row");
  const projectsLabel = formatUserMembershipProjects(row);

  if (options.mobile) {
    tr.classList.add("inactive-mobile-row");
    tr.innerHTML = `<td colspan="7" class="inactive-mobile-card-cell">${buildInactiveMobileCard(row)}</td>`;
    return tr;
  }

  tr.innerHTML = `
    <td>${escapeHtml(row.nome)}</td>
    <td>${escapeHtml(row.chave)}</td>
    <td title="${escapeHtml(projectsLabel)}">${escapeHtml(projectsLabel)}</td>
    <td>${escapeHtml(formatTimeZoneLabel(row.timezone_label))}</td>
    <td>${escapeHtml(`${formatAction(row.latest_action)} - ${formatDateTime(row.latest_time, row.timezone_name)}`)}</td>
    <td>${escapeHtml(formatInactivityDays(row.inactivity_days))}</td>
    <td class="user-table-actions"><button type="button" data-user-remove="${escapeHtml(row.id)}">Remover</button></td>
  `;
  return tr;
}

function renderInactiveTable(rows, options = {}) {
  if (!rows.length) {
    renderEmptyStateRow("inactiveBody", 7, options.emptyMessage || "Nenhum registro encontrado.");
    updateInactiveTitle(0);
    return;
  }

  const body = document.getElementById("inactiveBody");
  const mobile = isMobileAdminViewport();
  body.innerHTML = "";
  rows.forEach((row) => body.appendChild(buildInactiveRow(row, { mobile })));
  applyResponsiveLabels("inactiveBody");
  updateInactiveTitle(rows.length);
}

function buildMissingCheckoutRow(row) {
  const tr = document.createElement("tr");
  tr.dataset.userId = String(row.id);
  const timeDisplay = formatUserTableTime(row.time);
  tr.innerHTML = `
    <td>${escapeHtml(row.nome)}</td>
    <td>${escapeHtml(row.chave)}</td>
    <td>${escapeHtml(timeDisplay.formatted)}</td>
    <td class="user-table-actions"><button type="button" data-user-remove="${escapeHtml(row.id)}">Remover</button></td>
  `;
  return tr;
}

function renderMissingCheckoutTable(rows, options = {}) {
  if (!rows.length) {
    renderEmptyStateRow("missingCheckoutBody", 4, options.emptyMessage || "Nenhum registro encontrado.");
    updateMissingCheckoutTitle(0);
    return;
  }

  const body = document.getElementById("missingCheckoutBody");
  body.innerHTML = "";
  rows.forEach((row) => body.appendChild(buildMissingCheckoutRow(row)));
  applyResponsiveLabels("missingCheckoutBody");
  updateMissingCheckoutTitle(rows.length);
}

function buildFormsMobileCard(row, options = {}) {
  const canViewTime = options.canViewTime !== false;
  const receivedAtHtml = makeEventDateTimeCellFromParts(row.recebimento_date_label, row.recebimento_time_label);
  const eventDateTimeHtml = makeEventDateTimeCellFromParts(row.data ?? "-", canViewTime ? (row.hora ?? "") : "");
  const eventDateTimeLabel = canViewTime ? "Data e Hora" : "Data";
  const informeValue = String(row.informe ?? "-").trim() || "-";

  return `<article class="admin-mobile-card forms-mobile-card"><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Recebimento</span><div class="admin-mobile-card-datetime">${receivedAtHtml}</div></div><strong class="admin-mobile-card-title">${escapeHtml(row.nome ?? "-")}</strong><div class="admin-mobile-card-grid"><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Atividade</span><span class="admin-mobile-card-value">${escapeHtml(row.atividade ?? "-")}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Projeto</span><span class="admin-mobile-card-value">${escapeHtml(row.projeto ?? "-")}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Chave</span><span class="admin-mobile-card-value">${escapeHtml(row.chave ?? "-")}</span></div><div class="admin-mobile-card-field admin-mobile-card-field--wide"><span class="admin-mobile-card-label">${eventDateTimeLabel}</span><div class="admin-mobile-card-datetime">${eventDateTimeHtml}</div></div></div><div class="admin-mobile-card-field admin-mobile-card-field--wide"><span class="admin-mobile-card-label">Informe</span><p class="forms-mobile-card-copy">${escapeHtml(informeValue)}</p></div></article>`;
}

function buildFormsRow(row, options = {}) {
  const canViewTime = options.canViewTime !== false;
  const tr = document.createElement("tr");

  if (options.mobile) {
    tr.classList.add("forms-mobile-row");
    tr.innerHTML = `<td colspan="${getFormsColumnCount(canViewTime)}" class="forms-mobile-card-cell">${buildFormsMobileCard(row, { canViewTime })}</td>`;
    return tr;
  }

  const cells = [
    `<td>${makeEventDateTimeCellFromParts(row.recebimento_date_label, row.recebimento_time_label)}</td>`,
    `<td>${makeEventCell(row.chave ?? "-")}</td>`,
    `<td>${makeEventCell(row.nome ?? "-", "event-cell-left")}</td>`,
    `<td>${makeEventCell(row.projeto ?? "-")}</td>`,
    `<td>${makeEventCell(formatTimeZoneLabel(row.timezone_label))}</td>`,
    `<td>${makeEventCell(row.atividade ?? "-")}</td>`,
    `<td>${makeEventCell(row.informe ?? "-")}</td>`,
    `<td>${makeEventCell(row.data ?? "-")}</td>`,
  ];
  if (canViewTime) {
    cells.push(`<td>${makeEventCell(row.hora ?? "-")}</td>`);
  }
  tr.innerHTML = cells.join("");
  return tr;
}

function renderFormsTable(rows, options = {}) {
  const body = document.getElementById("formsBody");
  if (!body) {
    return false;
  }

  const canViewTime = options.canViewTime !== false;
  const mobile = isMobileAdminViewport();
  body.innerHTML = "";

  if (!rows.length) {
    renderEmptyStateRow("formsBody", getFormsColumnCount(canViewTime), "Nenhum evento do provider encontrado no historico sincronizado.");
    return true;
  }

  rows.forEach((row) => body.appendChild(buildFormsRow(row, { canViewTime, mobile })));
  applyResponsiveLabels("formsBody");
  return true;
}

function createLocationCoordinateEntry(value = "", overrides = {}) {
  return {
    id: overrides.id ?? `coord-${nextLocationCoordinateDraftId++}`,
    value: String(value ?? ""),
  };
}

function normalizeLocationCoordinateEntries(entries) {
  if (!Array.isArray(entries) || !entries.length) {
    return [createLocationCoordinateEntry("")];
  }

  return entries.map((entry) => {
    if (typeof entry === "string") {
      return createLocationCoordinateEntry(entry);
    }

    return createLocationCoordinateEntry(entry?.value ?? "", { id: entry?.id });
  });
}

function createLocationRow(overrides = {}) {
  const row = {
    id: overrides.id ?? `draft-${nextLocationDraftId++}`,
    local: "",
    coordinates: [createLocationCoordinateEntry("")],
    projects: [],
    projectPickerOpen: false,
    tolerance: "",
    isEditing: false,
    ...overrides,
  };
  row.coordinates = normalizeLocationCoordinateEntries(overrides.coordinates);
  row.projects = normalizeProjectNames(overrides.projects);
  return row;
}

function isPersistedLocationRowId(rowId) {
  return /^\d+$/.test(String(rowId ?? "").trim());
}

function getLocationRowById(rowId) {
  return locationRows.find((row) => String(row.id) === String(rowId));
}

function getLocationRowElement(rowId) {
  return document.querySelector(`#locationsBody tr[data-location-id="${CSS.escape(String(rowId))}"]`);
}

function captureLocationRowDraft(rowId) {
  const row = getLocationRowById(rowId);
  const rowElement = getLocationRowElement(rowId);
  if (!row || !rowElement) {
    return row;
  }

  row.local = rowElement.querySelector(".location-name")?.value ?? row.local;
  row.tolerance = rowElement.querySelector(".location-tolerance")?.value ?? row.tolerance;
  const coordinateInputs = Array.from(rowElement.querySelectorAll(".location-coordinate-input"));
  row.coordinates = coordinateInputs.length
    ? coordinateInputs.map((input, index) =>
        createLocationCoordinateEntry(input.value, {
          id: input.dataset.coordinateId || row.coordinates[index]?.id,
        })
      )
    : [createLocationCoordinateEntry("")];
  const projectInputs = Array.from(rowElement.querySelectorAll("input[data-location-project-option]"));
  if (projectInputs.length) {
    row.projects = normalizeProjectNames(
      projectInputs.filter((input) => input.checked).map((input) => input.value)
    );
  }
  return row;
}

function isBlankLocationRow(row) {
  return !String(row.local || "").trim()
    && !(row.coordinates || []).some((coordinate) => String(coordinate.value || "").trim())
    && !String(row.tolerance || "").trim();
}

function hasBlankLocationRow() {
  return locationRows.some((row) => isBlankLocationRow(row));
}

function getLocationAccuracyThresholdInput() {
  return document.getElementById("locationAccuracyThresholdMeters");
}

function getMixedZoneIntervalInput() {
  return document.getElementById("mixedZoneIntervalMinutes");
}

function getLocationSettingsSaveButton() {
  return document.getElementById("saveLocationSettingsButton");
}

const LOCATION_SETTINGS_PENDING_STATUS = "Alterações pendentes nas configurações de localização. Clique em Salvar para registrar.";

function normalizeLocationAccuracyThreshold(value) {
  const normalized = String(value ?? "").trim();
  if (!/^\d+$/.test(normalized)) {
    throw new Error("O erro máximo para considerar a coordenada do usuário deve ser um inteiro em metros.");
  }

  const meters = Number(normalized);
  if (!Number.isInteger(meters) || meters < 1 || meters > 9999) {
    throw new Error("O erro máximo para considerar a coordenada do usuário deve ser um inteiro entre 1 e 9999 metros.");
  }
  return String(meters);
}

function normalizeMixedZoneIntervalMinutes(value) {
  const normalized = String(value ?? "").trim();
  if (!/^\d+$/.test(normalized)) {
    throw new Error("O intervalo de tempo para Zona Mista deve ser um inteiro em minutos.");
  }

  const minutes = Number(normalized);
  if (!Number.isInteger(minutes) || minutes < 1) {
    throw new Error("O intervalo de tempo para Zona Mista deve ser um inteiro maior que zero em minutos.");
  }
  return String(minutes);
}

function normalizeLocationName(value) {
  const normalized = String(value || "").trim().replace(/\s+/g, " ");
  if (!normalized) {
    throw new Error("Informe a descrição do local.");
  }
  if (normalized.length > 40) {
    throw new Error("O local deve ter no máximo 40 caracteres.");
  }
  if (!/^[\p{L}\p{N} ]+$/u.test(normalized)) {
    throw new Error("O local deve conter apenas letras, números e espaços.");
  }
  return normalized;
}

function normalizeCoordinates(value) {
  const normalized = String(value || "").trim().replace(/\s+/g, " ");
  const match = /^(-?\d{1,3}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)$/.exec(normalized);
  if (!match) {
    throw new Error("As coordenadas devem estar no formato latitude, longitude.");
  }

  const latitude = Number(match[1]);
  const longitude = Number(match[2]);
  if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
    throw new Error("A latitude deve estar entre -90 e 90.");
  }
  if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
    throw new Error("A longitude deve estar entre -180 e 180.");
  }

  return `${latitude}, ${longitude}`;
}

function normalizeTolerance(value) {
  const normalized = String(value ?? "").trim();
  if (!/^\d{1,4}$/.test(normalized)) {
    throw new Error("A tolerância deve ter de 1 a 4 algarismos inteiros.");
  }

  const tolerance = Number(normalized);
  if (!Number.isInteger(tolerance) || tolerance < 1 || tolerance > 9999) {
    throw new Error("A tolerância deve ser um inteiro entre 1 e 9999 metros.");
  }
  return String(tolerance);
}

function isLocationCoordinateFilled(coordinate) {
  return Boolean(String(coordinate?.value ?? "").trim());
}

function getLocationCoordinateFilledCount(row) {
  if (!Array.isArray(row?.coordinates)) {
    return 0;
  }
  return row.coordinates.filter((coordinate) => isLocationCoordinateFilled(coordinate)).length;
}

function canRemoveLocationCoordinate(row, coordinateId) {
  if (!Array.isArray(row?.coordinates)) {
    return false;
  }

  const coordinate = row.coordinates.find((entry) => String(entry.id) === String(coordinateId));
  if (!coordinate) {
    return false;
  }

  if (!isLocationCoordinateFilled(coordinate)) {
    return row.coordinates.length > 1;
  }

  return getLocationCoordinateFilledCount(row) > 3;
}

function validateLocationCoordinates(row) {
  const coordinates = Array.isArray(row?.coordinates) ? row.coordinates : [];
  const firstFilledIndex = coordinates.findIndex((coordinate) => isLocationCoordinateFilled(coordinate));
  let lastFilledIndex = -1;

  coordinates.forEach((coordinate, index) => {
    if (isLocationCoordinateFilled(coordinate)) {
      lastFilledIndex = index;
    }
  });

  if (firstFilledIndex !== -1) {
    const hasBlankWithinSequence = coordinates
      .slice(firstFilledIndex, lastFilledIndex + 1)
      .some((coordinate) => !isLocationCoordinateFilled(coordinate));
    if (hasBlankWithinSequence) {
      throw new Error("Preencha os vértices em sequência, sem deixar linhas em branco entre V1 e o último vértice.");
    }
  }

  const hasBlankDrafts = coordinates.some((coordinate) => !isLocationCoordinateFilled(coordinate));
  if (hasBlankDrafts && lastFilledIndex !== -1) {
    throw new Error("Preencha ou remova os vértices em branco antes de salvar o polígono.");
  }

  const normalizedCoordinates = coordinates
    .filter((coordinate) => isLocationCoordinateFilled(coordinate))
    .map((coordinate) => normalizeCoordinates(coordinate.value));

  if (
    normalizedCoordinates.length >= 2
    && normalizedCoordinates[0] === normalizedCoordinates[normalizedCoordinates.length - 1]
  ) {
    throw new Error("Não repita o V1 no final; o polígono fecha automaticamente ligando o último vértice de volta ao primeiro.");
  }

  return normalizedCoordinates;
}

function getLocationCoordinateClosureCopy(row) {
  const filledCount = getLocationCoordinateFilledCount(row);
  if (filledCount < 2) {
    return "O polígono será fechado automaticamente quando houver ao menos 3 vértices.";
  }
  return `Fechamento implícito: V${filledCount} conecta de volta ao V1.`;
}

function normalizeLocationSaveErrorMessage(message) {
  const normalized = String(message ?? "").trim();
  const comparable = normalized.toLowerCase();

  if (comparable.includes("informe ao menos 3 coordenadas distintas")) {
    return "Informe ao menos 3 vértices distintos e preenchidos em ordem para formar a área poligonal do local.";
  }
  if (comparable.includes("nao repita a primeira coordenada no final")) {
    return "Não repita o V1 no final; o polígono fecha automaticamente ligando o último vértice de volta ao primeiro.";
  }
  if (comparable.includes("auto-interseccao")) {
    return "Os vértices informados se cruzam. Reordene a sequência para contornar a área sem auto-interseção.";
  }
  if (comparable.includes("area zero")) {
    return "Os vértices informados não formam uma área válida. Revise pontos repetidos, colineares ou muito próximos.";
  }

  return normalized;
}

function getLocationCoordinateValues(row) {
  if (!Array.isArray(row?.coordinates)) {
    return [];
  }

  return row.coordinates
    .map((coordinate) => String(coordinate?.value ?? coordinate ?? "").trim())
    .filter((value) => value);
}

function formatLocationCoordinateCount(count) {
  return count === 1 ? "1 vértice" : `${count} vértices`;
}

function makeLocationCoordinateSummary(row) {
  const coordinates = getLocationCoordinateValues(row);
  if (!coordinates.length) {
    return '<span class="location-empty-copy">Sem coordenadas</span>';
  }

  const primaryCoordinate = coordinates[0];
  const extraCoordinates = Math.max(0, coordinates.length - 1);
  const tooltip = coordinates
    .map((coordinate, index) => `V${index + 1}: ${coordinate}`)
    .join(" | ");

  return `
    <div class="location-coordinate-summary" title="${escapeHtml(tooltip)}">
      <span class="location-coordinate-pill-index">V1</span>
      <span class="location-coordinate-summary-primary">${escapeHtml(primaryCoordinate)}</span>
      ${extraCoordinates > 0 ? `<span class="location-coordinate-summary-count">+${extraCoordinates}</span>` : ""}
      <span class="location-coordinate-summary-closure">fecha em V1</span>
    </div>
  `;
}

function makeLocationCoordinateLines(row) {
  return row.coordinates.map((coordinate, index) => {
    const canRemove = canRemoveLocationCoordinate(row, coordinate.id);
    const isFirstVertex = index === 0;
    const isLastVertex = index === row.coordinates.length - 1;

    return `
      <div class="location-coordinate-line">
        <span class="location-coordinate-index">V${index + 1}</span>
        <input
          class="inline location-coordinate-input"
          data-coordinate-id="${escapeHtml(String(coordinate.id))}"
          maxlength="40"
          placeholder="Latitude, longitude do vértice"
          value="${escapeHtml(coordinate.value)}"
          ${row.isEditing ? "" : "disabled"}
        />
        ${row.isEditing ? `
          <div class="location-coordinate-actions">
            <button
              type="button"
              class="secondary-button location-coordinate-move-button"
              data-location-coordinate-move="${row.id}"
              data-direction="up"
              data-coordinate-id="${escapeHtml(String(coordinate.id))}"
              ${isFirstVertex ? 'disabled title="Este já é o primeiro vértice."' : ""}
            >Subir</button>
            <button
              type="button"
              class="secondary-button location-coordinate-move-button"
              data-location-coordinate-move="${row.id}"
              data-direction="down"
              data-coordinate-id="${escapeHtml(String(coordinate.id))}"
              ${isLastVertex ? 'disabled title="Este já é o último vértice."' : ""}
            >Descer</button>
            <button
              type="button"
              class="secondary-button location-coordinate-remove-button"
              data-location-coordinate-remove="${row.id}"
              data-coordinate-id="${escapeHtml(String(coordinate.id))}"
              ${canRemove ? "" : 'disabled title="Mantenha ao menos 3 vértices preenchidos no polígono."'}
            >Remover</button>
          </div>
        ` : ""}
      </div>
    `;
  }).join("");
}

function formatLocationProjectSummary(row) {
  const projectNames = normalizeProjectNames(row?.projects);
  if (!projectNames.length) {
    return "Nenhum projeto selecionado";
  }
  return projectNames.join(", ");
}

function makeLocationProjectOptions(row) {
  const selectedProjectNames = normalizeProjectNames(row.projects);
  const selectedProjectSet = new Set(selectedProjectNames);
  return getLocationProjectOptions(selectedProjectNames)
    .map((projectName) => `
      <label class="location-project-option">
        <input
          type="checkbox"
          data-location-project-option="${row.id}"
          value="${escapeHtml(projectName)}"
          ${selectedProjectSet.has(projectName) ? "checked" : ""}
        />
        <span>${escapeHtml(projectName)}</span>
      </label>
    `)
    .join("");
}

function focusLocationProjectPicker(rowId) {
  const row = getLocationRowElement(rowId);
  if (!row) {
    return;
  }
  row.querySelector("input[data-location-project-option]")?.focus();
}

function makeLocationRow(row) {
  const tr = document.createElement("tr");
  tr.className = row.isEditing ? "location-row location-row-editing" : "location-row";
  tr.dataset.locationId = String(row.id);

  const toleranceValue = String(row.tolerance ?? "").trim();
  const coordinateValues = getLocationCoordinateValues(row);
  const coordinateCountLabel = formatLocationCoordinateCount(coordinateValues.length || 0);
  const projectOptionsMarkup = makeLocationProjectOptions(row);
  const projectsCell = `
    <div class="location-cell-stack location-projects-cell">
      <button
        type="button"
        class="secondary-button location-projects-button"
        data-location-projects-toggle="${row.id}"
        aria-expanded="${row.projectPickerOpen ? "true" : "false"}"
        ${row.isEditing ? "" : 'disabled title="Clique em Editar antes de alterar os projetos desta localização."'}
      >Projetos</button>
      <span class="location-projects-summary">${escapeHtml(formatLocationProjectSummary(row))}</span>
      ${row.projectPickerOpen ? `
        <div class="location-projects-panel">
          ${projectOptionsMarkup || '<span class="location-empty-copy">Nenhum projeto cadastrado.</span>'}
        </div>
      ` : ""}
    </div>
  `;
  const locationCell = row.isEditing
    ? `
      <div class="location-cell-stack">
        <input class="inline location-name" maxlength="100" value="${escapeHtml(row.local)}" />
      </div>
    `
    : `
      <div class="location-cell-stack">
        <span class="location-static-value">${escapeHtml(row.local || "-")}</span>
        <span class="location-static-meta">${escapeHtml(coordinateCountLabel)}</span>
      </div>
    `;

  const coordinatesCell = row.isEditing
    ? `
      <div class="location-coordinates-stack">
        ${makeLocationCoordinateLines(row)}
        <span class="location-coordinate-note">${escapeHtml(getLocationCoordinateClosureCopy(row))}</span>
      </div>
    `
    : `<div class="location-coordinates-stack">${makeLocationCoordinateSummary(row)}</div>`;

  const toleranceCell = row.isEditing
    ? `
      <div class="location-cell-stack">
        <input class="inline location-tolerance" type="number" min="1" max="9999" inputmode="numeric" value="${escapeHtml(row.tolerance)}" />
      </div>
    `
    : `
      <div class="location-cell-stack">
        <span class="location-tolerance-badge">${escapeHtml(toleranceValue ? `${toleranceValue} m` : "-")}</span>
      </div>
    `;

  const actionsCell = row.isEditing
    ? `
      <button type="button" class="location-action-primary" data-location-edit="${row.id}">Salvar</button>
      <button type="button" class="secondary-button location-action-secondary" data-location-add-coordinate="${row.id}">+ Vértice</button>
      <button type="button" class="location-action-danger" data-location-remove="${row.id}">Remover</button>
    `
    : `
      <button type="button" class="location-action-primary" data-location-edit="${row.id}">Editar</button>
      <button type="button" class="secondary-button location-action-secondary" data-location-remove="${row.id}">Remover</button>
    `;

  tr.innerHTML = `
    <td class="location-cell">
        ${projectsCell}
      </td>
      <td class="location-cell">
      ${locationCell}
    </td>
    <td class="location-cell location-coordinates-cell">
      ${coordinatesCell}
    </td>
    <td class="location-cell">
      ${toleranceCell}
    </td>
    <td class="location-actions">
      ${actionsCell}
    </td>
  `;
  return tr;
}

function renderLocations() {
  const body = document.getElementById("locationsBody");
  const addButton = document.getElementById("addLocationButton");
  body.innerHTML = "";
  locationRows.forEach((row) => body.appendChild(makeLocationRow(row)));
  applyResponsiveLabels("locationsBody");
  addButton.disabled = hasBlankLocationRow();
}

function makeProjectMinimumCheckoutDistanceRow(row) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${escapeHtml(row.projectName)}</td>
    <td>
      <input
        class="inline project-minimum-checkout-distance-input"
        type="number"
        min="1"
        max="999999"
        inputmode="numeric"
        data-project-name="${escapeHtml(row.projectName)}"
        value="${escapeHtml(String(row.minimumCheckoutDistanceMeters))}"
      />
    </td>
  `;
  return tr;
}

function renderProjectMinimumCheckoutDistanceRows() {
  const body = document.getElementById("projectMinimumCheckoutDistancesBody");
  if (!body) {
    return;
  }

  body.innerHTML = "";
  if (!projectMinimumCheckoutDistanceRows.length) {
    renderEmptyStateRow("projectMinimumCheckoutDistancesBody", 2, "Nenhum projeto cadastrado.");
    return;
  }

  projectMinimumCheckoutDistanceRows.forEach((row) => body.appendChild(makeProjectMinimumCheckoutDistanceRow(row)));
  applyResponsiveLabels("projectMinimumCheckoutDistancesBody");
}

function renderLocationSettings() {
  const accuracyInput = getLocationAccuracyThresholdInput();
  if (accuracyInput) {
    const normalizedAccuracy = String(locationAccuracyThresholdMeters);
    accuracyInput.value = normalizedAccuracy;
    accuracyInput.dataset.persistedValue = normalizedAccuracy;
  }
  const mixedZoneInput = getMixedZoneIntervalInput();
  if (mixedZoneInput) {
    const normalizedMixedZoneInterval = String(mixedZoneIntervalMinutes);
    mixedZoneInput.value = normalizedMixedZoneInterval;
    mixedZoneInput.dataset.persistedValue = normalizedMixedZoneInterval;
  }
  locationSettingsDirty = false;
  updateLocationSettingsSaveButton();
}

function updateLocationSettingsSaveButton() {
  const saveButton = getLocationSettingsSaveButton();
  if (saveButton) {
    saveButton.disabled = !locationSettingsDirty;
  }
}

function haveLocationSettingsChanged() {
  const accuracyInput = getLocationAccuracyThresholdInput();
  const mixedZoneInput = getMixedZoneIntervalInput();
  if (!accuracyInput && !mixedZoneInput) {
    return false;
  }

  let changed = false;

  if (accuracyInput) {
    const persistedAccuracy = accuracyInput.dataset.persistedValue ?? String(locationAccuracyThresholdMeters);

    try {
      changed = normalizeLocationAccuracyThreshold(accuracyInput.value) !== persistedAccuracy;
    } catch {
      changed = String(accuracyInput.value ?? "").trim() !== persistedAccuracy;
    }
  }

  if (changed) {
    return true;
  }

  if (!mixedZoneInput) {
    return false;
  }

  const persistedMixedZoneInterval = mixedZoneInput.dataset.persistedValue ?? String(mixedZoneIntervalMinutes);

  try {
    return normalizeMixedZoneIntervalMinutes(mixedZoneInput.value) !== persistedMixedZoneInterval;
  } catch {
    return String(mixedZoneInput.value ?? "").trim() !== persistedMixedZoneInterval;
  }
}

function refreshLocationSettingsDirtyState() {
  locationSettingsDirty = haveLocationSettingsChanged();
  updateLocationSettingsSaveButton();
}

function handleLocationSettingsInputChange() {
  refreshLocationSettingsDirtyState();
  if (locationSettingsDirty) {
    setStatus(LOCATION_SETTINGS_PENDING_STATUS, true);
    return;
  }

  if (statusLine.textContent === LOCATION_SETTINGS_PENDING_STATUS) {
    clearStatus();
  }
}

function handleLocationSettingsInputKeydown(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    discardLocationSettingsDraft();
    event.currentTarget.blur();
    return;
  }

  if (event.key !== "Enter") {
    return;
  }

  event.preventDefault();
  refreshLocationSettingsDirtyState();
  if (!locationSettingsDirty) {
    return;
  }

  saveLocationSettings().catch((error) => setStatus(error.message, false));
}

function discardLocationSettingsDraft() {
  renderLocationSettings();
  setStatus("Alterações nas configurações de localização descartadas.", true);
}

function focusLocationRow(rowId, coordinateId = null) {
  const row = getLocationRowElement(rowId);
  if (!row) {
    return;
  }

  if (coordinateId !== null) {
    row.querySelector(`.location-coordinate-input[data-coordinate-id="${CSS.escape(String(coordinateId))}"]`)?.focus();
    return;
  }

  row.querySelector(".location-name")?.focus();
}

function setLocationEditingState(rowId, editing) {
  const row = getLocationRowById(rowId);
  if (!row) {
    return;
  }

  if (row.isEditing) {
    captureLocationRowDraft(rowId);
  }
  row.isEditing = editing;
  if (!editing) {
    row.projectPickerOpen = false;
  }
  renderLocations();
  if (editing) {
    focusLocationRow(rowId);
  }
}

function addLocationRow() {
  if (hasBlankLocationRow()) {
    setStatus("Finalize ou remova a linha em branco antes de adicionar outra localização.", false);
    renderLocations();
    return;
  }

  const row = createLocationRow({ isEditing: true });
  locationRows.push(row);
  renderLocations();
  focusLocationRow(row.id);
  setStatus("Nova localização pronta para preenchimento.", true);
}

function addLocationCoordinate(rowId) {
  const row = getLocationRowById(rowId);
  if (!row) {
    return;
  }

  captureLocationRowDraft(rowId);
  if (!row.isEditing) {
    row.isEditing = true;
  }
  const blankCoordinate = row.coordinates.find((coordinate) => !String(coordinate.value || "").trim());
  if (blankCoordinate) {
    focusLocationRow(rowId, blankCoordinate.id);
    setStatus("Preencha ou remova o vértice em branco antes de adicionar outro.", false);
    return;
  }
  const coordinate = createLocationCoordinateEntry("");
  row.coordinates.push(coordinate);
  renderLocations();
  focusLocationRow(rowId, coordinate.id);
}

function moveLocationCoordinate(rowId, coordinateId, direction) {
  const row = getLocationRowById(rowId);
  if (!row) {
    return;
  }

  captureLocationRowDraft(rowId);
  const currentIndex = row.coordinates.findIndex((coordinate) => String(coordinate.id) === String(coordinateId));
  if (currentIndex === -1) {
    return;
  }

  const targetIndex = direction === "up" ? currentIndex - 1 : currentIndex + 1;
  if (targetIndex < 0 || targetIndex >= row.coordinates.length) {
    return;
  }

  const [coordinate] = row.coordinates.splice(currentIndex, 1);
  row.coordinates.splice(targetIndex, 0, coordinate);
  renderLocations();
  focusLocationRow(rowId, coordinate.id);
}

function removeLocationCoordinate(rowId, coordinateId) {
  const row = getLocationRowById(rowId);
  if (!row) {
    return;
  }

  captureLocationRowDraft(rowId);
  if (!canRemoveLocationCoordinate(row, coordinateId)) {
    setStatus("Mantenha ao menos 3 vértices preenchidos no polígono. Adicione outro vértice antes de remover este.", false);
    focusLocationRow(rowId, coordinateId);
    return;
  }

  row.coordinates = row.coordinates.filter((coordinate) => String(coordinate.id) !== String(coordinateId));
  if (!row.coordinates.length) {
    row.coordinates = [createLocationCoordinateEntry("")];
  }

  renderLocations();
  focusLocationRow(rowId, row.coordinates[Math.max(0, row.coordinates.length - 1)]?.id ?? null);
}

async function saveLocationRow(rowId) {
  const row = captureLocationRowDraft(rowId);
  if (!row) {
    return;
  }

  const local = normalizeLocationName(row.local);
  const tolerance = normalizeTolerance(row.tolerance);
  const projects = normalizeProjectNames(row.projects);
  const normalizedCoordinates = validateLocationCoordinates(row);
  if (!projects.length) {
    throw new Error("Selecione ao menos um projeto para a localização.");
  }
  if (normalizedCoordinates.length < 3) {
    throw new Error("Informe ao menos 3 vértices distintos e preenchidos em ordem para formar a área poligonal do local.");
  }

  const coordinatesPayload = normalizedCoordinates.map((value) => {
    const [latitude, longitude] = value.split(",").map((part) => Number(part.trim()));
    return { latitude, longitude };
  });
  const primaryCoordinate = coordinatesPayload[0];
  const payload = {
    local,
    latitude: primaryCoordinate.latitude,
    longitude: primaryCoordinate.longitude,
    coordinates: coordinatesPayload,
    projects,
    tolerance_meters: Number(tolerance),
  };
  if (isPersistedLocationRowId(rowId)) {
    payload.location_id = Number(rowId);
  }

  try {
    const response = await postJson("/api/admin/locations", payload);
    await loadLocations();
    setStatus(response.message, true);
  } catch (error) {
    throw new Error(normalizeLocationSaveErrorMessage(error.message));
  }
}

async function removeLocationRow(rowId) {
  const row = getLocationRowById(rowId);
  if (!row) {
    return;
  }

  captureLocationRowDraft(rowId);

  if (!isPersistedLocationRowId(rowId)) {
    locationRows = locationRows.filter((item) => String(item.id) !== String(rowId));
    renderLocations();
    setStatus(`Localização ${row.local || "em branco"} removida.`, true);
    return;
  }

  const confirmed = window.confirm(`Deseja remover a localização ${row.local}?`);
  if (!confirmed) {
    return;
  }

  const response = await deleteJson(`/api/admin/locations/${rowId}`);
  await loadLocations();
  setStatus(response.message, true);
}

async function saveLocationSettings() {
  const accuracyInput = getLocationAccuracyThresholdInput();
  const mixedZoneInput = getMixedZoneIntervalInput();
  const saveButton = getLocationSettingsSaveButton();
  if (!accuracyInput || !mixedZoneInput) {
    locationSettingsDirty = false;
    updateLocationSettingsSaveButton();
    return;
  }

  const normalizedAccuracy = normalizeLocationAccuracyThreshold(accuracyInput.value);
  const normalizedMixedZoneInterval = normalizeMixedZoneIntervalMinutes(mixedZoneInput.value);
  accuracyInput.value = normalizedAccuracy;
  mixedZoneInput.value = normalizedMixedZoneInterval;
  if (
    normalizedAccuracy === String(locationAccuracyThresholdMeters)
    && normalizedMixedZoneInterval === String(mixedZoneIntervalMinutes)
  ) {
    locationSettingsDirty = false;
    updateLocationSettingsSaveButton();
    return;
  }

  accuracyInput.disabled = true;
  mixedZoneInput.disabled = true;
  if (saveButton) {
    saveButton.disabled = true;
  }
  try {
    const response = await postJson("/api/admin/locations/settings", {
      location_accuracy_threshold_meters: Number(normalizedAccuracy),
      mixed_zone_interval_minutes: Number(normalizedMixedZoneInterval),
    });
    locationAccuracyThresholdMeters = response.location_accuracy_threshold_meters;
    mixedZoneIntervalMinutes = response.mixed_zone_interval_minutes;
    renderLocationSettings();
    setStatus(response.message, true);
  } catch (error) {
    refreshLocationSettingsDirtyState();
    throw error;
  } finally {
    accuracyInput.disabled = false;
    mixedZoneInput.disabled = false;
    updateLocationSettingsSaveButton();
  }
}

async function loadLocations() {
  const [locationsResponse, checkoutDistancesResponse] = await Promise.all([
    fetchJson("/api/admin/locations"),
    fetchJson("/api/admin/locations/auto-checkout-distances"),
  ]);
  locationAccuracyThresholdMeters = locationsResponse.location_accuracy_threshold_meters;
  mixedZoneIntervalMinutes = locationsResponse.mixed_zone_interval_minutes ?? mixedZoneIntervalMinutes;
  locationRows = locationsResponse.items.map((row) =>
    createLocationRow({
      id: row.id,
      local: row.local,
      coordinates: (Array.isArray(row.coordinates) && row.coordinates.length
        ? row.coordinates
        : [{ latitude: row.latitude, longitude: row.longitude }]
      ).map((coordinate) => `${coordinate.latitude}, ${coordinate.longitude}`),
      projects: Array.isArray(row.projects) ? row.projects : [],
      tolerance: String(row.tolerance_meters),
      isEditing: false,
    })
  );
  projectMinimumCheckoutDistanceRows = (checkoutDistancesResponse.items || []).map((row) => ({
    projectName: row.project_name,
    minimumCheckoutDistanceMeters: row.minimum_checkout_distance_meters,
  }));
  renderLocations();
  renderLocationSettings();
  renderProjectMinimumCheckoutDistanceRows();
  updateDashboardSummary();
}

function makePendingRow(row) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${escapeHtml(row.rfid)}</td>
    <td><input class="inline" id="nome-${row.id}" disabled /></td>
    <td><input class="inline" id="chave-${row.id}" maxlength="4" disabled /></td>
    <td>
      ${makeProjectMembershipCell({ kind: "pending", rowId: row.id, selectedProjects: [] })}
    </td>
    <td class="pending-actions">
      <button data-edit="${row.id}">Editar</button>
      <button data-remove="${row.id}">Remover</button>
      <button data-save="${row.id}" data-rfid="${escapeHtml(row.rfid)}" disabled>Salvar</button>
    </td>
  `;
  const projectEditor = tr.querySelector(`[data-project-membership-editor="${CSS.escape(getProjectMembershipEditorKey("pending", row.id))}"]`);
  setStoredProjectMembershipSelection(projectEditor, []);
  return tr;
}

function makeRegisteredUserRow(user) {
  const selectedProjects = normalizeUserProjectMemberships(user.projetos, user.projeto);
  const tr = document.createElement("tr");
  tr.className = "user-row";
  tr.dataset.userId = String(user.id);
  tr.innerHTML = `
    <td><input class="inline user-rfid" maxlength="64" value="${escapeHtml(user.rfid ?? "")}" title="${escapeHtml(user.rfid ?? "")}" disabled /></td>
    <td><input class="inline user-nome" maxlength="180" value="${escapeHtml(user.nome)}" title="${escapeHtml(user.nome)}" disabled /></td>
    <td><input class="inline user-chave" maxlength="4" value="${escapeHtml(user.chave)}" title="${escapeHtml(user.chave)}" disabled /></td>
    <td><input class="inline user-perfil" type="number" min="0" max="999" value="${escapeHtml(user.perfil ?? 0)}" title="${escapeHtml(user.perfil ?? 0)}" disabled /></td>
    <td>
      ${makeProjectMembershipCell({ kind: "user", rowId: user.id, selectedProjects })}
    </td>
    <td><input class="inline user-end-rua" maxlength="255" value="${escapeHtml(user.end_rua ?? "")}" title="${escapeHtml(user.end_rua ?? "")}" disabled /></td>
    <td><input class="inline user-zip" maxlength="10" value="${escapeHtml(user.zip ?? "")}" title="${escapeHtml(user.zip ?? "")}" disabled /></td>
    <td><input class="inline user-cargo" maxlength="255" value="${escapeHtml(user.cargo ?? "")}" title="${escapeHtml(user.cargo ?? "")}" disabled /></td>
    <td><input class="inline user-email" type="email" maxlength="255" value="${escapeHtml(user.email ?? "")}" title="${escapeHtml(user.email ?? "")}" spellcheck="false" disabled /></td>
    <td class="pending-actions user-actions">
      <button data-user-edit="${user.id}">Editar</button>
      <button data-user-save="${user.id}" disabled>Salvar</button>
      <button type="button" class="secondary-button" data-user-password-reset="${user.id}" title="Remove a senha atual para que o usuario cadastre uma nova.">Senha</button>
      <button data-user-remove="${user.id}">Remover</button>
    </td>
  `;
  const projectEditor = tr.querySelector(`[data-project-membership-editor="${CSS.escape(getProjectMembershipEditorKey("user", user.id))}"]`);
  setStoredProjectMembershipSelection(projectEditor, selectedProjects);
  return tr;
}

function makeProjectRow(project) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${escapeHtml(project.name)}</td>
    <td>${escapeHtml(project.country_name || "-")}</td>
    <td>${escapeHtml(project.address || "-")}</td>
    <td>${escapeHtml(project.zip_code || "-")}</td>
    <td>${escapeHtml(formatTimeZoneLabel(project.timezone_label))}</td>
    <td class="pending-actions user-actions">
      <button type="button" class="secondary-button" data-project-edit="${project.id}">Editar</button>
      <button type="button" class="secondary-button" data-project-remove="${project.id}">Remover</button>
    </td>
  `;
  return tr;
}

function getAdministratorProjectNames(row) {
  return normalizeUserProjectMemberships(row?.projects);
}

function getAdministratorProjectsSummary(row) {
  const projectNames = getAdministratorProjectNames(row);
  return projectNames.length ? projectNames.join(", ") : "Nenhum projeto real vinculado";
}

function makeAdministratorProjectOptions(row) {
  const administratorProjectNames = getAdministratorProjectNames(row);
  const administratorProjectSet = new Set(administratorProjectNames);
  return getLocationProjectOptions(administratorProjectNames)
    .map((projectName) => `
      <label class="admin-project-option">
        <input
          type="checkbox"
          data-admin-project-option="${row.id}"
          value="${escapeHtml(projectName)}"
          ${administratorProjectSet.has(projectName) ? "checked" : ""}
        />
        <span>${escapeHtml(projectName)}</span>
      </label>
    `)
    .join("");
}

function makeAdministratorProjectsCell(row) {
  if (row.row_type === "request") {
    return `
      <div class="admin-projects-cell admin-projects-cell-readonly">
        <span class="admin-projects-readonly-copy">O projeto solicitado semeia apenas o projeto inicial. Defina os vinculos reais apos aprovar o administrador.</span>
      </div>
    `;
  }

  const projectsSummary = getAdministratorProjectsSummary(row);
  const projectOptionsMarkup = makeAdministratorProjectOptions(row);
  return `
    <div class="admin-projects-cell" title="Edite os projetos reais vinculados a este administrador.">
      <div class="admin-projects-summary">
        <strong class="admin-projects-summary-label">Projetos reais</strong>
        <span class="admin-projects-summary-value" title="${escapeHtml(projectsSummary)}">${escapeHtml(projectsSummary)}</span>
      </div>
      <span class="admin-projects-help-copy">Esses vinculos definem o escopo real do administrador.</span>
      <div class="admin-projects-panel">
        ${projectOptionsMarkup || '<span class="location-empty-copy">Nenhum projeto cadastrado.</span>'}
      </div>
    </div>
  `;
}

function makeAdministratorRow(row) {
  const tr = document.createElement("tr");
  const isRequestRow = row.row_type === "request";
  const profileValue = Number.parseInt(row.perfil, 10);
  const normalizedProfileValue = Number.isFinite(profileValue) ? profileValue : 0;
  const projectsCell = makeAdministratorProjectsCell(row);
  const actionButtons = isRequestRow
    ? `
      ${row.can_approve ? `<button data-admin-approve="${row.id}">Aprovar</button>` : ""}
      ${row.can_reject ? `<button type="button" class="secondary-button" data-admin-reject="${row.id}">Rejeitar</button>` : ""}
    `
    : `
      <button data-admin-profile-save="${row.id}">Salvar Perfil</button>
      ${row.can_revoke ? `<button type="button" class="secondary-button" data-admin-revoke="${row.id}">Revogar</button>` : ""}
    `;
  tr.classList.toggle("admin-row-pending", isRequestRow);
  tr.innerHTML = `
    <td>${escapeHtml(row.chave)}</td>
    <td>${escapeHtml(row.nome)}</td>
    <td>
      <input
        class="inline admin-profile-input"
        data-admin-profile-input="${row.id}"
        type="number"
        min="0"
        max="999"
        inputmode="numeric"
        value="${escapeHtml(normalizedProfileValue)}"
      />
    </td>
    <td>${projectsCell}</td>
    <td><span class="admin-status-badge${isRequestRow ? " is-pending" : ""}">${escapeHtml(row.status_label)}</span></td>
    <td class="pending-actions user-actions">${actionButtons}</td>
  `;
  return tr;
}

function hasPendingEditInProgress() {
  return locationRows.some((row) => row.isEditing)
    || locationSettingsDirty
    || Array.from(document.querySelectorAll("#pendingBody input, #pendingBody select, #usersBody input, #usersBody select")).some((field) => !field.disabled);
}

function setPendingEditingState(id, editing) {
  const nome = document.getElementById(`nome-${id}`);
  const chave = document.getElementById(`chave-${id}`);
  const projectEditor = getProjectMembershipEditor("pending", id);
  const saveButton = document.querySelector(`button[data-save="${id}"]`);
  const editButton = document.querySelector(`button[data-edit="${id}"]`);

  if (!nome || !chave || !projectEditor || !saveButton || !editButton) {
    return;
  }

  nome.disabled = !editing;
  chave.disabled = !editing;
  syncProjectMembershipToggleState(projectEditor, editing);
  saveButton.disabled = !editing;
  editButton.disabled = editing;
  if (editing) {
    nome.focus();
  }
}

function setRegisteredUserEditingState(userId, editing) {
  const row = document.querySelector(`#usersBody tr[data-user-id="${CSS.escape(String(userId))}"]`);
  if (!row) {
    return;
  }

  row.classList.toggle("user-row-editing", editing);

  const rfid = row.querySelector(".user-rfid");
  const nome = row.querySelector(".user-nome");
  const chave = row.querySelector(".user-chave");
  const perfil = row.querySelector(".user-perfil");
  const projectEditor = getProjectMembershipEditor("user", userId);
  const endRua = row.querySelector(".user-end-rua");
  const zip = row.querySelector(".user-zip");
  const cargo = row.querySelector(".user-cargo");
  const email = row.querySelector(".user-email");
  const saveButton = row.querySelector(`[data-user-save="${userId}"]`);
  const editButton = row.querySelector(`[data-user-edit="${userId}"]`);
  const passwordButton = row.querySelector(`[data-user-password-reset="${userId}"]`);

  rfid.disabled = !editing;
  nome.disabled = !editing;
  chave.disabled = !editing;
  perfil.disabled = !editing;
  syncProjectMembershipToggleState(projectEditor, editing);
  endRua.disabled = !editing;
  zip.disabled = !editing;
  cargo.disabled = !editing;
  email.disabled = !editing;
  saveButton.disabled = !editing;
  editButton.disabled = editing;
  if (passwordButton) {
    passwordButton.disabled = editing;
  }
  scheduleUserFieldTextareaRefresh();
  if (editing) {
    nome.focus();
    if (typeof nome.select === "function") {
      nome.select();
    }
  }
}

function toggleAdminPasswordEditor(id, active) {
  const editor = document.getElementById(`admin-password-editor-${id}`);
  if (!editor) {
    return;
  }
  editor.classList.toggle("active", active);
  const input = document.getElementById(`admin-password-input-${id}`);
  if (!input) {
    return;
  }
  if (active) {
    input.focus();
  } else {
    input.value = "";
  }
}

function readAdministratorProfileValue(id) {
  const input = document.querySelector(`[data-admin-profile-input="${CSS.escape(String(id))}"]`);
  if (!(input instanceof HTMLInputElement)) {
    throw new Error("Perfil do administrador nao encontrado.");
  }

  const normalized = String(input.value || "").trim();
  if (!/^\d{1,3}$/.test(normalized)) {
    throw new Error("Informe um perfil numerico entre 0 e 999.");
  }
  return Number.parseInt(normalized, 10);
}

function readAdministratorProjects(id) {
  const inputs = Array.from(
    document.querySelectorAll(`input[data-admin-project-option="${CSS.escape(String(id))}"]`)
  ).filter((input) => input instanceof HTMLInputElement);

  if (!inputs.length) {
    throw new Error("Projetos do administrador nao encontrados.");
  }

  const projects = normalizeProjectNames(
    inputs
      .filter((input) => input.checked)
      .map((input) => input.value)
  );

  if (!projects.length) {
    inputs[0].focus();
    throw new Error("Selecione ao menos um projeto para o administrador.");
  }

  return projects;
}

async function loadCheckin() {
  const rows = await fetchJson("/api/admin/checkin");
  presenceTableStates.checkin.rawRows = Array.isArray(rows) ? rows : [];
  applyPresenceTableState("checkin");
  updateDashboardSummary();
}

async function loadCheckout() {
  const rows = await fetchJson("/api/admin/checkout");
  presenceTableStates.checkout.rawRows = Array.isArray(rows) ? rows : [];
  if (presenceTableStates.missingCheckout) {
    presenceTableStates.missingCheckout.rawRows = [];
  }
  applyPresenceTableState("checkout");
  updateDashboardSummary();
}

async function loadInactive() {
  const rows = await fetchJson("/api/admin/inactive");
  presenceTableStates.inactive.rawRows = Array.isArray(rows) ? rows : [];
  applyPresenceTableState("inactive");
  updateDashboardSummary();
}

async function loadPending() {
  const rows = await fetchJson("/api/admin/pending");
  pendingUsersTotal = Array.isArray(rows) ? rows.length : 0;
  const body = document.getElementById("pendingBody");
  body.innerHTML = "";
  rows.forEach((row) => body.appendChild(makePendingRow(row)));
  applyResponsiveLabels("pendingBody");
  updateDashboardSummary();
}

async function loadAdministrators() {
  if (!projectCatalog.length) {
    await loadProjects();
  }

  const rows = await fetchJson("/api/admin/administrators");
  const normalizedRows = Array.isArray(rows) ? rows : [];
  const adminRows = normalizedRows.filter((row) => row.row_type === "admin");
  const currentAdminRow = adminRows.find((row) => String(row?.chave ?? "").trim().toUpperCase() === currentAdminChave);
  currentAdminProjectNames = getAdministratorProjectNames(currentAdminRow);
  currentAdminProjectScopeResolved = true;
  administratorsTotal = adminRows.length;
  const body = document.getElementById("administratorsBody");
  body.innerHTML = "";
  if (normalizedRows.length === 0) {
    renderEmptyStateRow("administratorsBody", 6, "Nenhum administrador ou solicitacao pendente encontrada.");
  } else {
    normalizedRows.forEach((row) => body.appendChild(makeAdministratorRow(row)));
  }
  applyResponsiveLabels("administratorsBody");
  updateDashboardSummary();
}

async function loadAdministratorsWithProjectCatalog() {
  await loadProjects();
  await loadAdministrators();
}

async function loadProjects() {
  const rows = await fetchJson("/api/admin/projects");
  setProjectCatalog(rows);
  syncProjectEditorState();
  if (locationRows.length > 0) {
    renderLocations();
  }

  const body = document.getElementById("projectsBody");
  if (!body) {
    return rows;
  }

  body.innerHTML = "";
  if (!rows.length) {
    renderEmptyStateRow("projectsBody", 6, "Nenhum projeto cadastrado.");
    return rows;
  }

  rows.forEach((project) => body.appendChild(makeProjectRow(project)));
  applyResponsiveLabels("projectsBody");
  return rows;
}

async function loadRegisteredUsers() {
  const rows = await fetchJson("/api/admin/users");
  registeredUsersTotal = rows.length;
  populateReportsSearchOptions(rows);
  const body = document.getElementById("usersBody");
  body.innerHTML = "";
  rows.forEach((user) => body.appendChild(makeRegisteredUserRow(user)));
  applyResponsiveLabels("usersBody");
  syncUserTitles();
  updateDashboardSummary();
  scheduleUserFieldTextareaRefresh();
}

async function saveProject() {
  if (hasPendingEditInProgress()) {
    setStatus("Salve ou cancele as edições pendentes antes de alterar os projetos.", false);
    return;
  }

  const projectName = String(projectNameInput ? projectNameInput.value : "").trim();
  const projectAddress = normalizeProjectMetadataText(projectAddressInput ? projectAddressInput.value : "");
  const projectZipCode = normalizeProjectMetadataText(projectZipCodeInput ? projectZipCodeInput.value : "");
  const customCountryName = normalizeProjectCountryName(projectCustomCountryInput ? projectCustomCountryInput.value : "");
  const selectedCountry = getSelectedProjectCountryOption();
  const countryName = customCountryName || normalizeProjectCountryName(selectedCountry ? selectedCountry.name : "");
  const timezoneName = normalizeProjectTimezoneName(projectTimezoneInput ? projectTimezoneInput.value : "");
  const countryCode = customCountryName
    ? deriveProjectCountryCode(countryName)
    : normalizeProjectCountryCode(selectedCountry ? selectedCountry.code : "") || deriveProjectCountryCode(countryName);

  if (!projectName) {
    setStatus("Informe o nome do projeto.", false);
    if (projectNameInput) {
      projectNameInput.focus();
    }
    return;
  }

  if (!countryName) {
    setStatus("Selecione o país do projeto ou informe um novo país.", false);
    if (projectCustomCountryInput) {
      projectCustomCountryInput.focus();
    } else if (projectCountrySelect) {
      projectCountrySelect.focus();
    }
    return;
  }

  if (!timezoneName) {
    setStatus("Informe o fuso horário do projeto.", false);
    if (projectTimezoneInput) {
      projectTimezoneInput.focus();
    }
    return;
  }

  const projectPayload = {
    name: projectName,
    address: projectAddress,
    zip_code: projectZipCode,
    country_code: countryCode,
    country_name: countryName,
    timezone_name: timezoneName,
  };

  if (projectEditorProjectId === null) {
    await postJson("/api/admin/projects", projectPayload);
    setStatus("Projeto adicionado com sucesso", true);
  } else {
    const normalizedProjectId = requireIntegerId(projectEditorProjectId, "Projeto");
    await putJson(`/api/admin/projects/${normalizedProjectId}`, projectPayload);
    setStatus("Projeto atualizado com sucesso", true);
  }

  resetProjectEditor();
  await loadProjects();
  await Promise.all([loadAdministrators(), loadPending(), loadRegisteredUsers()]);
}

async function removeProject(projectId) {
  if (hasPendingEditInProgress()) {
    setStatus("Salve ou cancele as edições pendentes antes de alterar os projetos.", false);
    return;
  }

  const normalizedProjectId = requireIntegerId(projectId, "Projeto");
  const confirmed = window.confirm("Deseja remover este projeto?");
  if (!confirmed) {
    return;
  }

  await deleteJson(`/api/admin/projects/${normalizedProjectId}`);
  if (String(projectEditorProjectId ?? "") === normalizedProjectId) {
    resetProjectEditor();
  }
  setStatus("Projeto removido com sucesso", true);
  await loadProjects();
  await Promise.all([loadAdministrators(), loadPending(), loadRegisteredUsers()]);
}

async function loadEvents() {
  const canViewTime = syncEventsPrimaryColumnLabel();
  const rows = await fetchJson("/api/admin/events");
  eventsRows = Array.isArray(rows) ? rows : [];
  eventsTotal = eventsRows.length;
  renderEventsTable(eventsRows, { canViewTime });
  updateDashboardSummary();
}

async function loadForms() {
  const canViewTime = syncFormsTimeColumnVisibility();
  const body = document.getElementById("formsBody");
  if (!body) {
    formsTotal = 0;
    formsRows = null;
    updateFormsClearButtonState();
    updateDashboardSummary();
    return;
  }

  const rows = await fetchJson("/api/admin/forms");
  formsRows = Array.isArray(rows) ? rows : [];
  formsTotal = formsRows.length;
  setTextContentIfPresent("formsTitle", `Forms (${formsTotal})`);
  updateFormsClearButtonState();
  renderFormsTable(formsRows, { canViewTime });
  updateDashboardSummary();
}

async function clearForms() {
  if (formsTotal === 0) {
    return;
  }

  const confirmed = window.confirm("Deseja remover todos os registros da tabela Forms?");
  if (!confirmed) {
    return;
  }

  const payload = await deleteJson("/api/admin/forms");
  await loadForms();
  markDashboardRefreshed();
  setStatus(payload?.message || "Registros de Forms removidos com sucesso.", true);
}

function resetReportsView(options = {}) {
  const { focusPrimary = false } = options;
  reportsSearchInProgress = false;
  reportsExportInProgress = false;
  reportsHasLoadedResult = false;
  reportsExportQueryString = "";
  reportsResultsPayload = null;
  if (reportsSearchChaveInput) {
    reportsSearchChaveInput.value = "";
  }
  if (reportsSearchNomeInput) {
    reportsSearchNomeInput.value = "";
  }
  setReportsStatus("");
  setTextContentIfPresent("reportsPersonTitle", "Nenhuma busca realizada");
  setTextContentIfPresent("reportsPersonMeta", "Selecione uma chave ou um nome para carregar o relatório.");
  const body = document.getElementById("reportsResultsBody");
  if (body) {
    body.innerHTML = "";
  }
  syncReportsSearchInputs();
  if (focusPrimary && reportsSearchChaveInput) {
    reportsSearchChaveInput.focus();
  }
}

function updateReportsActionButtons() {
  const hasCriteria = getSelectedReportSearchKey().length > 0;
  const hasExportableResult = reportsHasLoadedResult && reportsExportQueryString.length > 0;

  if (reportsSearchButton) {
    reportsSearchButton.disabled = reportsSearchInProgress || reportsExportInProgress || !hasCriteria;
  }
  if (reportsClearButton) {
    reportsClearButton.disabled = reportsSearchInProgress || reportsExportInProgress || (!hasCriteria && !reportsHasLoadedResult);
  }
  if (reportsExportButton) {
    reportsExportButton.classList.toggle("hidden", !hasExportableResult);
    reportsExportButton.disabled = reportsSearchInProgress || reportsExportInProgress || !hasExportableResult;
  }
  if (reportsExportAllButton) {
    reportsExportAllButton.disabled = reportsSearchInProgress || reportsExportInProgress;
  }
}

function syncReportsSearchInputs(source = null) {
  const selectedKey = getSelectedReportSearchKey(source);
  const selectedUser = getReportSearchUserByChave(selectedKey);
  const normalizedSelectedKey = selectedUser ? selectedUser.chave : "";

  if (reportsSearchChaveInput instanceof HTMLSelectElement) {
    reportsSearchChaveInput.value = hasSelectOption(reportsSearchChaveInput, normalizedSelectedKey) ? normalizedSelectedKey : "";
  }
  if (reportsSearchNomeInput instanceof HTMLSelectElement) {
    reportsSearchNomeInput.value = hasSelectOption(reportsSearchNomeInput, normalizedSelectedKey) ? normalizedSelectedKey : "";
  }

  updateReportsActionButtons();
}

function renderReportsState(title, message) {
  reportsHasLoadedResult = false;
  reportsExportQueryString = "";
  reportsResultsPayload = null;
  setTextContentIfPresent("reportsPersonTitle", title);
  setTextContentIfPresent("reportsPersonMeta", message);
  const body = document.getElementById("reportsResultsBody");
  if (body) {
    body.innerHTML = "";
  }
  updateReportsActionButtons();
}

function getReportEventTimeLine(row) {
  return row.event_time_label
    || formatDateTimeLines(row.event_time, row.timezone_name).time
    || formatDateTime(row.event_time, row.timezone_name)
    || "-";
}

function getReportsResultTableColumns(includeTime = canCurrentAdminViewActivityTime()) {
  const columns = [];
  if (includeTime) {
    columns.push({
      header: "Horário",
      colClass: "reports-col-time",
      getValue: (row) => getReportEventTimeLine(row),
    });
  }

  columns.push(
    {
      header: "Ação",
      colClass: "reports-col-action",
      getValue: (row) => row.action_label || formatAction(row.action),
    },
    {
      header: "Origem",
      colClass: "reports-col-source",
      getValue: (row) => row.source_label || row.source || "-",
    },
    {
      header: "Local",
      colClass: "reports-col-local",
      getValue: (row) => row.local_label || formatLocal(row.local),
    },
    {
      header: "Projeto",
      colClass: "reports-col-project",
      getValue: (row) => row.projeto ?? "-",
    },
    {
      header: "Fuso horário",
      colClass: "reports-col-timezone",
      getValue: (row) => formatTimeZoneLabel(row.timezone_label),
    },
    {
      header: "Assiduidade",
      colClass: "reports-col-assiduidade",
      getValue: (row) => row.assiduidade ?? "Normal",
    },
  );

  return columns;
}

function buildReportsResultMobileCardMarkup(row, options = {}) {
  const includeTime = options.includeTime ?? canCurrentAdminViewActivityTime();
  const timeMarkup = includeTime
    ? `<div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Horário</span><span class="admin-mobile-card-value">${escapeHtml(getReportEventTimeLine(row))}</span></div>`
    : "";

  return `<article class="admin-mobile-card reports-result-card"><strong class="admin-mobile-card-title">${escapeHtml(row.action_label || formatAction(row.action))}</strong><div class="admin-mobile-card-grid">${timeMarkup}<div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Origem</span><span class="admin-mobile-card-value">${escapeHtml(row.source_label || row.source || "-")}</span></div><div class="admin-mobile-card-field admin-mobile-card-field--wide"><span class="admin-mobile-card-label">Local</span><span class="admin-mobile-card-value">${escapeHtml(row.local_label || formatLocal(row.local))}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Projeto</span><span class="admin-mobile-card-value">${escapeHtml(row.projeto ?? "-")}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Assiduidade</span><span class="admin-mobile-card-value">${escapeHtml(row.assiduidade ?? "Normal")}</span></div><div class="admin-mobile-card-field admin-mobile-card-field--wide"><span class="admin-mobile-card-label">Fuso horário</span><span class="admin-mobile-card-value">${escapeHtml(formatTimeZoneLabel(row.timezone_label))}</span></div></div></article>`;
}

function buildReportsResultCardsMarkup(rows, options = {}) {
  return `<div class="reports-results-cards">${rows.map((row) => buildReportsResultMobileCardMarkup(row, options)).join("")}</div>`;
}

function buildReportsResultRowMarkup(row, columns) {
  return `<tr>${columns.map((column) => `<td>${escapeHtml(column.getValue(row))}</td>`).join("")}</tr>`;
}

function buildReportsResultTableMarkup(tbodyId, rows, options = {}) {
  const includeTime = options.includeTime ?? canCurrentAdminViewActivityTime();
  const columns = getReportsResultTableColumns(includeTime);
  const tableClasses = ["responsive-table", "reports-results-table"];
  if (!includeTime) {
    tableClasses.push("reports-results-table--without-time");
  }

  const colgroupMarkup = columns.map((column) => `<col class="${column.colClass}">`).join("");
  const headerMarkup = columns.map((column) => `<th>${escapeHtml(column.header)}</th>`).join("");
  const rowsMarkup = rows.map((row) => buildReportsResultRowMarkup(row, columns)).join("");

  return `<div class="table-wrap"><table class="${tableClasses.join(" ")}"><colgroup>${colgroupMarkup}</colgroup><thead><tr>${headerMarkup}</tr></thead><tbody id="${escapeHtml(tbodyId)}">${rowsMarkup}</tbody></table></div>`;
}

function buildReportsResultGroupMarkup(group, groupIndex, options = {}) {
  const includeTime = options.includeTime ?? canCurrentAdminViewActivityTime();
  const mobile = options.mobile === true;
  const contentMarkup = mobile
    ? buildReportsResultCardsMarkup(group.rows, { includeTime })
    : buildReportsResultTableMarkup(`reportsGroupBody${groupIndex}`, group.rows, { includeTime });
  const groupLabel = group.rows.length === 1 ? "1 evento" : `${group.rows.length} eventos`;
  return `<section class="reports-group"><div class="section-header reports-group-header"><h4>${escapeHtml(group.date)}</h4><span class="reports-group-count">${escapeHtml(groupLabel)}</span></div>${contentMarkup}</section>`;
}

function renderReportsResults(payload) {
  const body = document.getElementById("reportsResultsBody");
  if (!body) {
    return false;
  }

  reportsResultsPayload = payload;

  const person = payload?.person || {};
  const events = Array.isArray(payload?.events) ? payload.events : [];
  const eventsLabel = events.length === 1 ? "1 evento" : `${events.length} eventos`;
  const personProjectsLabel = formatUserMembershipProjects(person);
  setTextContentIfPresent("reportsPersonTitle", `${person.nome || "-"} (${person.chave || "-"})`);
  setTextContentIfPresent(
    "reportsPersonMeta",
    `Projetos: ${personProjectsLabel} | Projeto ativo: ${person.projeto || "-"} | RFID: ${person.rfid || "-"} | Fuso horário: ${formatTimeZoneLabel(person.timezone_label)} | ${eventsLabel}`,
  );

  if (!events.length) {
    body.innerHTML = `<p class="section-header-copy">Nenhum evento encontrado para a pessoa informada.</p>`;
    return false;
  }

  const groups = [];
  const groupsByDate = new Map();
  const canViewTime = canCurrentAdminViewActivityTime();
  const mobile = isMobileAdminViewport();
  events.forEach((row) => {
    const groupKey = row.event_date || formatDateTimeLines(row.event_time, row.timezone_name).date;
    if (!groupsByDate.has(groupKey)) {
      const group = { date: groupKey, rows: [] };
      groupsByDate.set(groupKey, group);
      groups.push(group);
    }
    groupsByDate.get(groupKey).rows.push(row);
  });

  body.innerHTML = groups.map((group, groupIndex) => buildReportsResultGroupMarkup(group, groupIndex, {
    includeTime: canViewTime,
    mobile,
  })).join("");

  if (!mobile) {
    groups.forEach((_, groupIndex) => {
      applyResponsiveLabels(`reportsGroupBody${groupIndex}`);
    });
  }
  return true;
}

async function downloadReportsExport() {
  if (!(reportsExportButton instanceof HTMLButtonElement) || reportsExportQueryString.length === 0 || reportsExportInProgress) {
    return;
  }

  const idleLabel = reportsExportButton.dataset.idleLabel || "Exportar";
  reportsExportInProgress = true;
  reportsExportButton.disabled = true;
  reportsExportButton.classList.add("is-loading");
  reportsExportButton.setAttribute("aria-busy", "true");
  reportsExportButton.textContent = "Exportando...";
  updateReportsActionButtons();
  setReportsStatus("");
  try {
    const { blob, fileName } = await fetchBlob(`/api/admin/reports/events/export?${reportsExportQueryString}`, "relatorio.xlsx");
    downloadBlob(blob, fileName);
    setReportsStatus("Relatório exportado com sucesso.", "success");
  } catch (error) {
    setReportsStatus(error.message || "Não foi possível exportar o relatório.", "error");
  } finally {
    reportsExportInProgress = false;
    reportsExportButton.classList.remove("is-loading");
    reportsExportButton.setAttribute("aria-busy", "false");
    reportsExportButton.textContent = idleLabel;
    updateReportsActionButtons();
  }
}

async function downloadReportsExportAll() {
  if (!(reportsExportAllButton instanceof HTMLButtonElement) || reportsExportInProgress) {
    return;
  }

  const idleLabel = reportsExportAllButton.dataset.idleLabel || "Exportar Tudo";
  reportsExportInProgress = true;
  reportsExportAllButton.disabled = true;
  reportsExportAllButton.classList.add("is-loading");
  reportsExportAllButton.setAttribute("aria-busy", "true");
  reportsExportAllButton.textContent = "Exportando...";
  updateReportsActionButtons();
  setReportsStatus("");
  try {
    const { blob, fileName } = await fetchBlob("/api/admin/reports/events/export-all", "relatorio-todos.xlsx");
    downloadBlob(blob, fileName);
    setReportsStatus("Relatório completo exportado com sucesso.", "success");
  } catch (error) {
    setReportsStatus(error.message || "Não foi possível exportar o relatório completo.", "error");
  } finally {
    reportsExportInProgress = false;
    reportsExportAllButton.classList.remove("is-loading");
    reportsExportAllButton.setAttribute("aria-busy", "false");
    reportsExportAllButton.textContent = idleLabel;
    updateReportsActionButtons();
  }
}

async function submitReportsSearch() {
  if (!(reportsSearchButton instanceof HTMLButtonElement)) {
    return;
  }

  const normalizedChave = getSelectedReportSearchKey();
  syncReportsSearchInputs();

  if (!normalizedChave) {
    setReportsStatus("Selecione a chave ou o nome para buscar o relatório.", "error");
    renderReportsState("Nenhuma busca realizada", "Selecione um critério antes de consultar o relatório.");
    syncReportsSearchInputs();
    return;
  }

  const idleLabel = reportsSearchButton.dataset.idleLabel || "Buscar";
  const query = new URLSearchParams();
  query.set("chave", normalizedChave);

  reportsSearchInProgress = true;
  reportsSearchButton.classList.add("is-loading");
  reportsSearchButton.setAttribute("aria-busy", "true");
  reportsSearchButton.textContent = "Buscando...";
  updateReportsActionButtons();
  setReportsStatus("");
  try {
    const payload = await fetchJson(`/api/admin/reports/events?${query.toString()}`);
    reportsResultsPayload = payload;
    reportsHasLoadedResult = renderReportsResults(payload);
    reportsExportQueryString = reportsHasLoadedResult ? query.toString() : "";
    updateReportsActionButtons();
    setReportsStatus("Relatório carregado com sucesso.", "success");
  } catch (error) {
    renderReportsState("Busca não concluída", error.message || "Não foi possível carregar o relatório.");
    setReportsStatus(error.message || "Não foi possível carregar o relatório.", "error");
  } finally {
    reportsSearchInProgress = false;
    reportsSearchButton.classList.remove("is-loading");
    reportsSearchButton.setAttribute("aria-busy", "false");
    reportsSearchButton.textContent = idleLabel;
    syncReportsSearchInputs();
  }
}

function buildEventMobileCard(row, options = {}) {
  const canViewTime = options.canViewTime !== false;
  const eventDetails = {
    message: row.message ?? "-",
    details: formatEventDetails(row.details),
  };
  const eventDateTime = formatDateTimeLines(row.event_time, row.timezone_name);
  const eventDateLabel = row.event_date_label || eventDateTime.date;
  const eventTimeLabel = canViewTime ? (row.event_time_label || eventDateTime.time) : "";
  return {
    markup: `<article class="admin-mobile-card events-mobile-card"><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">${canViewTime ? "Horário" : "Data"}</span><div class="admin-mobile-card-datetime">${makeEventDateTimeCellFromParts(eventDateLabel, eventTimeLabel)}</div></div><strong class="admin-mobile-card-title">${escapeHtml(formatAction(row.action))}</strong><div class="admin-mobile-card-grid"><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Origem</span><span class="admin-mobile-card-value">${escapeHtml(row.source ?? "-")}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Status</span><span class="admin-mobile-card-value">${escapeHtml(row.status ?? "-")}</span></div><div class="admin-mobile-card-field admin-mobile-card-field--wide"><span class="admin-mobile-card-label">Local</span><span class="admin-mobile-card-value">${escapeHtml(formatLocal(row.local))}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">ID</span><span class="admin-mobile-card-value">${escapeHtml(row.id)}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Chave</span><span class="admin-mobile-card-value">${escapeHtml(row.chave ?? "-")}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Projeto</span><span class="admin-mobile-card-value">${escapeHtml(row.project ?? "-")}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Device</span><span class="admin-mobile-card-value">${escapeHtml(row.device_id ?? "-")}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">RFID</span><span class="admin-mobile-card-value">${escapeHtml(row.rfid ?? "-")}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">HTTP</span><span class="admin-mobile-card-value">${escapeHtml(row.http_status ?? "-")}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Tentativas</span><span class="admin-mobile-card-value">${escapeHtml(row.retry_count ?? 0)}</span></div><div class="admin-mobile-card-field"><span class="admin-mobile-card-label">Ontime</span><span class="admin-mobile-card-value">${escapeHtml(formatOntime(row.ontime))}</span></div><div class="admin-mobile-card-field admin-mobile-card-field--wide"><span class="admin-mobile-card-label">Fuso horário</span><span class="admin-mobile-card-value">${escapeHtml(formatTimeZoneLabel(row.timezone_label))}</span></div></div><div class="admin-mobile-card-actions"><button type="button" class="event-details-button">Detalhes</button></div></article>`,
    details: eventDetails,
  };
}

function buildEventRow(row, options = {}) {
  const canViewTime = options.canViewTime !== false;
  const tr = document.createElement("tr");
  const eventDetails = {
    message: row.message ?? "-",
    details: formatEventDetails(row.details),
  };
  const eventDateTime = formatDateTimeLines(row.event_time, row.timezone_name);
  const eventDateLabel = row.event_date_label || eventDateTime.date;
  const eventTimeLabel = canViewTime ? (row.event_time_label || eventDateTime.time) : "";

  if (options.mobile) {
    const mobileCard = buildEventMobileCard(row, { canViewTime });
    tr.classList.add("events-mobile-row");
    tr.innerHTML = `<td colspan="15" class="events-mobile-card-cell">${mobileCard.markup}</td>`;
    tr.querySelector(".event-details-button").addEventListener("click", () => openEventDetails(mobileCard.details));
    return tr;
  }

  tr.innerHTML = `<td>${makeEventCell(row.id)}</td><td>${makeEventDateTimeCellFromParts(eventDateLabel, eventTimeLabel)}</td><td>${makeEventCell(row.source)}</td><td>${makeEventCell(formatAction(row.action))}</td><td>${makeEventCell(row.status)}</td><td>${makeEventCell(row.device_id ?? "-")}</td><td>${makeEventCell(formatLocal(row.local))}</td><td>${makeEventCell(row.rfid ?? "-")}</td><td>${makeEventCell(row.chave ?? "-")}</td><td>${makeEventCell(row.project ?? "-")}</td><td>${makeEventCell(formatTimeZoneLabel(row.timezone_label))}</td><td>${makeEventCell(formatOntime(row.ontime))}</td><td>${makeEventCell(row.http_status ?? "-")}</td><td>${makeEventCell(row.retry_count ?? 0)}</td><td>${makeEventDetailsButton()}</td>`;
  tr.querySelector(".event-details-button").addEventListener("click", () => openEventDetails(eventDetails));
  return tr;
}

function renderEventsTable(rows, options = {}) {
  const body = document.getElementById("eventsBody");
  if (!body) {
    return false;
  }

  const mobile = isMobileAdminViewport();
  const canViewTime = options.canViewTime !== false;
  body.innerHTML = "";
  if (!rows.length) {
    renderEmptyStateRow("eventsBody", 15, "Nenhum evento encontrado.");
    return true;
  }

  rows.forEach((row) => body.appendChild(buildEventRow(row, { mobile, canViewTime })));
  if (!mobile) {
    applyResponsiveLabels("eventsBody");
  }
  return true;
}

function updateFormsClearButtonState() {
  const clearButton = document.getElementById("clearFormsButton");
  if (!clearButton) {
    return;
  }
  clearButton.disabled = formsTotal === 0;
}

async function runFormsClear(button) {
  if (!(button instanceof HTMLButtonElement) || button.disabled) {
    return;
  }

  const idleLabel = String(button.dataset.idleLabel || button.textContent || "Limpar").trim() || "Limpar";
  button.dataset.idleLabel = idleLabel;
  button.disabled = true;
  button.classList.add("is-loading");
  button.setAttribute("aria-busy", "true");
  button.textContent = "Limpando...";

  try {
    await clearForms();
  } finally {
    updateFormsClearButtonState();
    button.classList.remove("is-loading");
    button.setAttribute("aria-busy", "false");
    button.textContent = idleLabel;
  }
}

async function refreshActiveTab() {
  if (activeTab === "checkin") {
    await loadCheckin();
    markDashboardRefreshed();
    return;
  }
  if (activeTab === "checkout") {
    await loadCheckout();
    markDashboardRefreshed();
    return;
  }
  if (activeTab === "forms") {
    return;
  }
  if (activeTab === "relatorios") {
    return;
  }
  if (activeTab === "inactive") {
    return;
  }
  if (activeTab === "cadastro") {
    if (!hasPendingEditInProgress()) {
      await loadProjects();
      await Promise.all([loadAdministrators(), loadPending(), loadLocations()]);
      markDashboardRefreshed();
    }
    return;
  }
  if (activeTab === "banco-dados") {
    await loadDatabaseEvents();
    markDashboardRefreshed();
    return;
  }
}

async function refreshAllTables() {
  const jobs = [];
  if (isAdminTabAllowed("checkin")) {
    jobs.push(loadCheckin());
  }
  if (isAdminTabAllowed("checkout")) {
    jobs.push(loadCheckout());
  }
  if (isAdminTabAllowed("forms")) {
    jobs.push(loadForms());
  }
  if (isAdminTabAllowed("inactive")) {
    jobs.push(loadInactive());
  }
  if (isAdminTabAllowed("eventos")) {
    jobs.push(loadEvents());
  }
  if (isAdminTabAllowed("cadastro") && hasPendingEditInProgress()) {
    jobs.push(loadAdministrators());
  }
  if (databaseEventsLoaded && isAdminTabAllowed("banco-dados")) {
    jobs.push(loadDatabaseEvents());
  }
  if (isAdminTabAllowed("cadastro") && !hasPendingEditInProgress()) {
    await loadProjects();
    jobs.push(loadAdministrators());
    jobs.push(loadPending());
    jobs.push(loadRegisteredUsers());
    jobs.push(loadLocations());
  }
  await Promise.all(jobs);
  markDashboardRefreshed();
}

async function refreshAutomaticTables() {
  const jobs = [];
  const scrollSnapshot = capturePresencePageScroll();
  if (isAdminTabAllowed("checkin")) {
    jobs.push(loadCheckin());
  }
  if (isAdminTabAllowed("checkout")) {
    jobs.push(loadCheckout());
  }
  if (databaseEventsLoaded && isAdminTabAllowed("banco-dados")) {
    jobs.push(loadDatabaseEvents());
  }
  if (isAdminTabAllowed("cadastro") && !hasPendingEditInProgress()) {
    // Background refresh keeps the administrator grid stable. The grid depends on
    // the current project catalog and should only rerender in the explicit loaders.
    await loadProjects();
    jobs.push(loadPending());
    jobs.push(loadLocations());
  }
  await Promise.all(jobs);
  restorePresencePageScroll(scrollSnapshot);
  markDashboardRefreshed();
}

function startAutoRefresh() {
  stopAutoRefresh();
  autoRefreshHandle = window.setInterval(() => {
    if (document.hidden || realtimeConnected || !isAuthenticated) {
      return;
    }
    refreshAutomaticTables().catch((error) => setStatus(error.message, false));
  }, AUTO_REFRESH_MS);
}

function stopAutoRefresh() {
  if (autoRefreshHandle !== null) {
    window.clearInterval(autoRefreshHandle);
    autoRefreshHandle = null;
  }
}

function requestRefreshAllTables() {
  if (refreshAllTimer !== null) {
    window.clearTimeout(refreshAllTimer);
  }
  refreshAllTimer = window.setTimeout(() => {
    refreshAutomaticTables().catch((error) => setStatus(error.message, false));
    refreshAllTimer = null;
  }, REALTIME_DEBOUNCE_MS);
}

function startRealtimeUpdates() {
  stopRealtimeUpdates();
  eventStream = new EventSource("/api/admin/stream");
  eventStream.onopen = () => {
    realtimeConnected = true;
    updateOperationalChrome();
  };
  eventStream.onmessage = () => {
    realtimeConnected = true;
    updateOperationalChrome();
    requestRefreshAllTables();
  };
  eventStream.onerror = () => {
    realtimeConnected = false;
    updateOperationalChrome();
  };
}

function stopRealtimeUpdates() {
  if (eventStream) {
    eventStream.close();
    eventStream = null;
  }
  realtimeConnected = false;
  updateOperationalChrome();
}

function parseDownloadFileName(contentDisposition, fallbackName) {
  const match = /filename="?([^";]+)"?/i.exec(contentDisposition || "");
  return match ? match[1] : fallbackName;
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  const decimals = unitIndex === 0 ? 0 : size >= 10 ? 1 : 2;
  return `${size.toFixed(decimals)} ${units[unitIndex]}`;
}

function downloadBlob(blob, fileName) {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

async function fetchBlob(url, fallbackName) {
  const res = await fetch(url, { credentials: "same-origin" });
  if (!res.ok) {
    const message = await parseErrorResponse(res);
    if (res.status === 401) {
      await handleUnauthorized(message);
    }
    throw new Error(message);
  }
  const blob = await res.blob();
  return {
    blob,
    fileName: parseDownloadFileName(res.headers.get("Content-Disposition"), fallbackName),
  };
}

async function loadEventArchives() {
  const params = new URLSearchParams({
    page: String(eventArchivesPage),
    page_size: String(ARCHIVE_PAGE_SIZE),
  });
  if (eventArchivesFilterQuery.trim()) {
    params.set("q", eventArchivesFilterQuery.trim());
  }
  const payload = await fetchJson(`/api/admin/events/archives?${params.toString()}`);
  renderEventArchives(payload);
  return payload;
}

function updateArchivePagination() {
  const prevButton = document.getElementById("eventArchivesPrev");
  const nextButton = document.getElementById("eventArchivesNext");
  const pageInfo = document.getElementById("eventArchivesPageInfo");
  prevButton.disabled = eventArchivesPage <= 1 || eventArchivesTotal === 0;
  nextButton.disabled = eventArchivesPage >= eventArchivesTotalPages || eventArchivesTotal === 0;
  pageInfo.textContent = `Página ${eventArchivesTotal === 0 ? 0 : eventArchivesPage} de ${eventArchivesTotal === 0 ? 0 : eventArchivesTotalPages}`;
}

function updateArchiveSummary() {
  const summary = document.getElementById("eventArchivesSummary");
  const storageSummary = document.getElementById("eventArchivesStorage");
  summary.textContent = eventArchivesFilterQuery.trim() ? `${eventArchives.length} de ${eventArchivesTotal} logs` : `${eventArchivesTotal} logs`;
  storageSummary.textContent = `Espaço total usado: ${formatBytes(eventArchivesTotalSizeBytes)}`;
}

function renderEventArchives(payload) {
  eventArchives = payload.items || [];
  eventArchivesTotal = payload.total || 0;
  eventArchivesTotalSizeBytes = payload.total_size_bytes || 0;
  eventArchivesPage = payload.page || 1;
  eventArchivesTotalPages = payload.total_pages || 0;
  const body = document.getElementById("eventArchivesBody");
  const emptyState = document.getElementById("eventArchivesEmpty");
  const downloadAllButton = document.getElementById("downloadAllEventArchives");
  body.innerHTML = "";
  updateArchiveSummary();
  updateArchivePagination();
  if (!eventArchives.length) {
    emptyState.classList.remove("hidden");
    downloadAllButton.disabled = true;
    return;
  }

  emptyState.classList.add("hidden");
  downloadAllButton.disabled = false;
  eventArchives.forEach((archive) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><span class="archive-period">${escapeHtml(archive.period)}</span></td>
      <td><span class="archive-record-count">${escapeHtml(archive.record_count)}</span></td>
      <td><span class="archive-size">${escapeHtml(formatBytes(archive.size_bytes))}</span></td>
      <td>
        <div class="archive-actions">
          <button type="button" class="archive-download-button" data-archive-download="${escapeHtml(archive.file_name)}">Baixar</button>
          <button type="button" class="archive-delete-button" data-archive-delete="${escapeHtml(archive.file_name)}">Excluir</button>
        </div>
      </td>
    `;
    body.appendChild(row);
  });
}

async function downloadEventArchive(fileName) {
  const { blob, fileName: resolvedName } = await fetchBlob(`/api/admin/events/archives/${encodeURIComponent(fileName)}`, fileName);
  downloadBlob(blob, resolvedName);
}

async function downloadAllEventArchives() {
  const { blob, fileName } = await fetchBlob("/api/admin/events/archives/download-all", "eventos-archives.zip");
  downloadBlob(blob, fileName);
}

async function deleteEventArchive(fileName) {
  await deleteJson(`/api/admin/events/archives/${encodeURIComponent(fileName)}`);
  const archives = await loadEventArchives();
  setStatus(`Arquivo ${fileName} excluído com sucesso.`, true);
  if (!archives.total) {
    setStatus("Todos os logs salvos foram excluídos.", true);
  }
}

async function archiveAndClearEvents() {
  const confirmed = window.confirm("Deseja salvar os eventos atuais em CSV e limpar a lista de eventos?\n\nOs arquivos antigos continuarão disponíveis para download.");
  if (!confirmed) {
    return;
  }

  const payload = await postJson("/api/admin/events/archive");
  eventArchivesPage = 1;
  renderEventArchives(payload.archives || {});
  openEventArchivesModal();
  await loadEvents();
  if (databaseEventsLoaded) {
    await loadDatabaseEvents();
  }

  if (payload.created && payload.archive) {
    setStatus(`Eventos salvos em ${payload.archive.period} e limpos (${payload.cleared_count} registros).`, true);
    return;
  }
  setStatus("Não havia eventos novos para salvar. Logs já salvos exibidos na janela.", true);
}

async function refreshManualTable(loader) {
  await loader();
  markDashboardRefreshed();
}

async function runManualRefresh(button, loader) {
  if (!(button instanceof HTMLButtonElement) || button.disabled) {
    return;
  }

  const idleLabel = String(button.dataset.idleLabel || button.textContent || "Atualizar").trim() || "Atualizar";
  button.dataset.idleLabel = idleLabel;
  button.disabled = true;
  button.classList.add("is-loading");
  button.setAttribute("aria-busy", "true");
  button.textContent = "Atualizando...";

  try {
    await refreshManualTable(loader);
  } finally {
    button.disabled = false;
    button.classList.remove("is-loading");
    button.setAttribute("aria-busy", "false");
    button.textContent = idleLabel;
  }
}

function bindManualRefreshButton(button, loader) {
  if (!(button instanceof HTMLButtonElement)) {
    return;
  }

  button.dataset.idleLabel = String(button.textContent || "Atualizar").trim() || "Atualizar";
  button.addEventListener("click", () => {
    runManualRefresh(button, loader).catch((error) => setStatus(error.message, false));
  });
}

async function savePending(id, rfid) {
  const nome = document.getElementById(`nome-${id}`).value.trim();
  const chave = document.getElementById(`chave-${id}`).value.trim().toUpperCase();
  const projetos = getProjectMembershipSelectionForSubmit("pending", id);
  if (!nome || chave.length !== 4) {
    setStatus("Preencha nome e chave de 4 caracteres", false);
    return;
  }
  if (!projetos.length) {
    setStatus("Selecione ao menos um projeto para este cadastro pendente.", false);
    return;
  }
  const payload = await postJson("/api/admin/users", { rfid, nome, chave, projetos });
  if (payload?.linked_existing_user) {
    setStatus("Cadastro salvo com sucesso e RFID vinculado ao usuário já existente pela chave.", true);
  } else {
    setStatus("Cadastro salvo com sucesso", true);
  }
  await Promise.all([loadPending(), loadRegisteredUsers()]);
}

async function removePending(id) {
  await deleteJson(`/api/admin/pending/${id}`);
  setStatus("Pendência removida com sucesso", true);
  await loadPending();
}

async function saveRegisteredUser(userId) {
  const normalizedUserId = requireIntegerId(userId, "Usuário");
  const row = document.querySelector(`#usersBody tr[data-user-id="${CSS.escape(normalizedUserId)}"]`);
  if (!row) {
    return;
  }
  const rfidValue = row.querySelector(".user-rfid").value.trim();
  const nome = row.querySelector(".user-nome").value.trim();
  const chave = row.querySelector(".user-chave").value.trim().toUpperCase();
  const perfilValue = row.querySelector(".user-perfil").value.trim();
  const projetos = getProjectMembershipSelectionForSubmit("user", normalizedUserId);
  const endRua = row.querySelector(".user-end-rua").value.trim();
  const zip = row.querySelector(".user-zip").value.trim();
  const cargo = row.querySelector(".user-cargo").value.trim();
  const email = row.querySelector(".user-email").value.trim().toLowerCase();
  if (!nome || chave.length !== 4) {
    setStatus("Preencha nome e chave de 4 caracteres", false);
    return;
  }
  if (!/^\d{1,3}$/.test(perfilValue)) {
    setStatus("Informe um perfil numérico entre 0 e 999.", false);
    return;
  }
  if (!projetos.length) {
    setStatus("Selecione ao menos um projeto para este usuário.", false);
    return;
  }
  await postJson("/api/admin/users", {
    user_id: Number(normalizedUserId),
    rfid: rfidValue || null,
    nome,
    chave,
    perfil: Number(perfilValue),
    projetos,
    end_rua: endRua || null,
    zip: zip || null,
    cargo: cargo || null,
    email: email || null,
  });
  setStatus("Usuário salvo com sucesso", true);
  await loadRegisteredUsers();
}

async function removeRegisteredUser(userId) {
  const normalizedUserId = requireIntegerId(userId, "Usuário");
  await deleteJson(`/api/admin/users/${normalizedUserId}`);
  setStatus("Usuário removido com sucesso", true);
  await Promise.all([loadRegisteredUsers(), loadCheckin(), loadCheckout(), loadInactive()]);
}

async function resetRegisteredUserPassword(userId) {
  const normalizedUserId = requireIntegerId(userId, "Usuário");
  const confirmed = window.confirm(
    "Deseja remover a senha deste usuário?\n\nDepois disso, ele precisará cadastrar uma nova senha para voltar a acessar a área web.",
  );
  if (!confirmed) {
    return;
  }

  const payload = await postJson(`/api/admin/users/${normalizedUserId}/reset-password`);
  setStatus(payload.message, true);
  await loadRegisteredUsers();
}

async function approveAdministrator(id) {
  const profile = readAdministratorProfileValue(id);
  const payload = await postJson(`/api/admin/administrators/requests/${id}/approve`, { perfil: profile });
  setStatus(payload.message, true);
  await loadAdministrators();
}

async function rejectAdministrator(id) {
  const payload = await postJson(`/api/admin/administrators/requests/${id}/reject`);
  setStatus(payload.message, true);
  await loadAdministrators();
}

async function revokeAdministrator(id) {
  const confirmed = window.confirm("Deseja revogar o acesso deste administrador?");
  if (!confirmed) {
    return;
  }
  const payload = await postJson(`/api/admin/administrators/${id}/revoke`);
  setStatus(payload.message, true);
  await loadAdministrators();
}

async function saveAdministratorProfile(id) {
  const profile = readAdministratorProfileValue(id);
  const projects = readAdministratorProjects(id);
  const payload = await postJson(`/api/admin/administrators/${id}/profile`, {
    perfil: profile,
    projects,
  });
  setStatus(payload.message, true);
  await loadAdministrators();
}

async function saveAdministratorPassword(id) {
  const input = document.getElementById(`admin-password-input-${id}`);
  const novaSenha = input.value;
  if (novaSenha.length < 3 || novaSenha.length > 20) {
    setStatus("A nova senha deve ter entre 3 e 20 caracteres.", false);
    return;
  }
  const payload = await postJson(`/api/admin/administrators/${id}/set-password`, { nova_senha: novaSenha });
  toggleAdminPasswordEditor(id, false);
  setStatus(payload.message, true);
  await loadAdministrators();
}

async function submitLogin() {
  const chave = normalizeAdminChave(loginChaveInput ? loginChaveInput.value : "");
  const senha = loginSenhaInput ? loginSenhaInput.value : "";
  if (loginChaveInput) {
    loginChaveInput.value = chave;
  }
  if (chave.length !== 4 || !/^[A-Z0-9]{4}$/i.test(chave)) {
    setAuthStatus("A chave deve ter 4 caracteres alfanuméricos.", "error");
    return;
  }
  if (senha.length < 3 || senha.length > 20) {
    setAuthStatus("A senha deve ter entre 3 e 20 caracteres.", "error");
    return;
  }

  const payload = await postJson("/api/admin/auth/login", { chave, senha });
  setAuthStatus(payload.message, "success");
  if (loginSenhaInput) {
    loginSenhaInput.value = "";
  }
  await bootstrapAdmin();
}

async function submitRequestAdminRegistration() {
  const chave = normalizeAdminChave(requestAdminRegistrationChaveInput ? requestAdminRegistrationChaveInput.value : "");
  const nomeCompleto = requestAdminRegistrationNomeInput ? requestAdminRegistrationNomeInput.value.trim() : "";
  const projeto = requestAdminRegistrationProjetoSelect ? requestAdminRegistrationProjetoSelect.value.trim() : "";
  const senha = requestAdminRegistrationSenhaInput ? requestAdminRegistrationSenhaInput.value : "";
  const confirmarSenha = requestAdminRegistrationConfirmInput ? requestAdminRegistrationConfirmInput.value : "";

  if (!isAdminRequestKeyValid(chave)) {
    setRequestAdminRegistrationStatus("A chave deve ter 4 caracteres alfanumericos.", "error");
    return;
  }
  if (nomeCompleto.length < 3) {
    setRequestAdminRegistrationStatus("Informe o nome completo.", "error");
    return;
  }
  if (projeto.length < 2) {
    setRequestAdminRegistrationStatus("Selecione o projeto do usuario.", "error");
    return;
  }
  if (!isAdminRequestPasswordValid(senha)) {
    setRequestAdminRegistrationStatus("A senha deve ter entre 3 e 10 caracteres.", "error");
    return;
  }
  if (senha !== confirmarSenha) {
    setRequestAdminRegistrationStatus("A confirmacao de senha nao confere.", "error");
    return;
  }

  requestAdminRegistrationSaveInProgress = true;
  syncRequestAdminRegistrationFormState();
  try {
    const payload = await postJson("/api/admin/auth/request-access/self-service", {
      chave,
      nome_completo: nomeCompleto,
      projeto,
      senha,
      confirmar_senha: confirmarSenha,
    });
    setRequestAdminRegistrationStatus(payload.message, "success");
    setAuthStatus(payload.message, "success");
    window.setTimeout(() => {
      closeRequestAdminRegistrationModal();
      closeRequestAdminModal();
    }, 700);
  } finally {
    requestAdminRegistrationSaveInProgress = false;
    syncRequestAdminRegistrationFormState();
  }
}

async function submitPasswordReset() {
  const chave = document.getElementById("loginChave").value.trim().toUpperCase();
  if (!chave) {
    setAuthStatus("Informe sua chave antes de solicitar o recadastro da senha.", "error");
    return;
  }
  if (chave.length !== 4 || !/^[A-Z0-9]{4}$/i.test(chave)) {
    setAuthStatus("A chave deve ter 4 caracteres alfanuméricos.", "error");
    return;
  }

  const payload = await postJson("/api/admin/auth/request-password-reset", { chave });
  document.getElementById("loginSenha").value = "";
  setAuthStatus(payload.message, "success");
}

async function logout() {
  await postJson("/api/admin/auth/logout");
  showAuthShell("Sessão encerrada com sucesso.", "success");
}

async function bootstrapAdmin() {
  const session = await fetchJson("/api/admin/auth/session");
  if (!session.authenticated || !session.admin) {
    showAuthShell("", "info");
    return;
  }

  showAdminShell(session.admin);
  startAutoRefresh();
  startRealtimeUpdates();
  await refreshAllTables();
  syncAdminResponsiveState({ force: true });
  setStatus("Painel administrativo carregado.", true);
}

function bindLocationSettingsInput(inputId) {
  const input = document.getElementById(inputId);
  if (!input) {
    return;
  }

  input.addEventListener("input", handleLocationSettingsInputChange);
  input.addEventListener("change", handleLocationSettingsInputChange);
  input.addEventListener("keydown", handleLocationSettingsInputKeydown);
}

function bindActions() {
  document.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  document.querySelectorAll("[data-filter-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      toggleAdminMobileFilterPanel(button.dataset.filterToggle);
    });
  });

  document.querySelectorAll(".presence-controls").forEach((container) => {
    const tableKey = container.dataset.presenceTable;

    const handlePresenceFilterChange = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement) || !target.dataset.presenceFilter) {
        return;
      }
      const state = getPresenceTableState(tableKey);
      if (!state) {
        return;
      }
      state.filters[target.dataset.presenceFilter] = target.value;
      applyPresenceTableState(tableKey);
    };

    container.addEventListener("input", handlePresenceFilterChange);
    container.addEventListener("change", handlePresenceFilterChange);

    container.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLButtonElement) || target.dataset.presenceClear === undefined) {
        return;
      }
      resetPresenceControls(tableKey);
      applyPresenceTableState(tableKey);
      setStatus("Filtros limpos com sucesso.", true);
    });
  });

  const databaseTab = document.getElementById("tab-banco-dados");
  if (databaseTab) {
    const handleDatabaseFilterChange = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement) || !target.dataset.databaseEventFilter) {
        return;
      }

      const filterKey = target.dataset.databaseEventFilter;
      let nextValue = target.value;

      if (filterKey === "chave") {
        nextValue = nextValue.replace(/\s+/g, "").toUpperCase().slice(0, 4);
        target.value = nextValue;
      } else if (filterKey === "project") {
        nextValue = nextValue.toUpperCase();
      } else if (["action", "source", "status"].includes(filterKey)) {
        nextValue = nextValue.toLowerCase();
      }

      databaseEventsState.filters[filterKey] = nextValue;
      databaseEventsState.page = 1;

      const shouldDebounce = event.type === "input" && (target.type === "search" || target.type === "text");
      scheduleDatabaseEventsRefresh(shouldDebounce ? REALTIME_DEBOUNCE_MS : 0);
    };

    databaseTab.addEventListener("input", handleDatabaseFilterChange);
    databaseTab.addEventListener("change", handleDatabaseFilterChange);

    const clearDatabaseFiltersButton = document.getElementById("databaseEventsClearFilters");
    if (clearDatabaseFiltersButton) {
      clearDatabaseFiltersButton.addEventListener("click", () => {
        resetDatabaseEventFilters();
        scheduleDatabaseEventsRefresh(0);
        setStatus("Filtros do banco de dados limpos com sucesso.", true);
      });
    }

    const previousButton = document.getElementById("databaseEventsPrev");
    if (previousButton) {
      previousButton.addEventListener("click", () => {
        if (databaseEventsState.page <= 1) {
          return;
        }
        databaseEventsState.page -= 1;
        loadDatabaseEvents().catch((error) => setStatus(error.message, false));
      });
    }

    const nextButton = document.getElementById("databaseEventsNext");
    if (nextButton) {
      nextButton.addEventListener("click", () => {
        if (databaseEventsState.page >= databaseEventsState.totalPages) {
          return;
        }
        databaseEventsState.page += 1;
        loadDatabaseEvents().catch((error) => setStatus(error.message, false));
      });
    }
  }

  document.querySelector("main").addEventListener("click", (event) => {
    const target = event.target;
    const sortButton = target instanceof Element ? target.closest(".sortable-header") : null;
    if (!sortButton) {
      return;
    }

    const tableKey = sortButton.dataset.sortTable;
    const sortKey = sortButton.dataset.sortKey;
    if (tableKey === "databaseEvents") {
      applyDatabaseEventSort(sortKey);
      loadDatabaseEvents().catch((error) => setStatus(error.message, false));
      return;
    }
    const state = getPresenceTableState(tableKey);
    if (!state || !sortKey) {
      return;
    }

    if (state.sortKey === sortKey) {
      state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
    } else {
      state.sortKey = sortKey;
      state.sortDirection = getPresenceDefaultSortDirection(sortKey);
    }

    applyPresenceTableState(tableKey);
  });

  document.getElementById("loginButton").addEventListener("click", () => {
    submitLogin().catch((error) => setAuthStatus(error.message, "error"));
  });
  if (loginChaveInput) {
    loginChaveInput.addEventListener("input", () => {
      const normalized = normalizeAdminChave(loginChaveInput.value);
      if (normalized !== loginChaveInput.value) {
        loginChaveInput.value = normalized;
      }
      if (isChangePasswordModalOpen()) {
        scheduleChangePasswordVerification();
        syncChangePasswordFormState();
      }
    });
  }
  document.getElementById("loginSenha").addEventListener("keydown", (event) => {
        setChangePasswordStatus("");
  });
  document.getElementById("logoutButton").addEventListener("click", () => {
    logout().catch((error) => setAuthStatus(error.message, "error"));
  });

  const changePasswordButton = document.getElementById("changePasswordButton");
  const refreshFormsButton = document.getElementById("refreshFormsButton");
  const clearFormsButton = document.getElementById("clearFormsButton");
  const refreshInactiveButton = document.getElementById("refreshInactiveButton");
  const refreshAdministratorsButton = document.getElementById("refreshAdministratorsButton");
  const refreshUsersButton = document.getElementById("refreshUsersButton");
  const refreshEventsButton = document.getElementById("refreshEventsButton");
  if (changePasswordButton) {
    changePasswordButton.addEventListener("click", openChangePasswordModal);
  }
  bindManualRefreshButton(refreshFormsButton, loadForms);
  if (clearFormsButton instanceof HTMLButtonElement) {
    clearFormsButton.dataset.idleLabel = String(clearFormsButton.textContent || "Limpar").trim() || "Limpar";
    clearFormsButton.addEventListener("click", () => {
      runFormsClear(clearFormsButton).catch((error) => setStatus(error.message, false));
    });
    updateFormsClearButtonState();
  }
  bindManualRefreshButton(refreshInactiveButton, loadInactive);
  bindManualRefreshButton(refreshAdministratorsButton, loadAdministratorsWithProjectCatalog);
  bindManualRefreshButton(refreshUsersButton, loadRegisteredUsers);
  bindManualRefreshButton(refreshEventsButton, loadEvents);
  if (reportsSearchButton) {
    reportsSearchButton.dataset.idleLabel = String(reportsSearchButton.textContent || "Buscar").trim() || "Buscar";
    reportsSearchButton.addEventListener("click", () => {
      submitReportsSearch();
    });
  }
  if (reportsClearButton) {
    reportsClearButton.addEventListener("click", () => {
      resetReportsView({ focusPrimary: true });
    });
  }
  if (reportsExportButton) {
    reportsExportButton.dataset.idleLabel = String(reportsExportButton.textContent || "Exportar").trim() || "Exportar";
    reportsExportButton.addEventListener("click", () => {
      downloadReportsExport();
    });
  }
  if (reportsExportAllButton) {
    reportsExportAllButton.dataset.idleLabel = String(reportsExportAllButton.textContent || "Exportar Tudo").trim() || "Exportar Tudo";
    reportsExportAllButton.addEventListener("click", () => {
      downloadReportsExportAll();
    });
  }
  [reportsSearchChaveInput, reportsSearchNomeInput].filter(Boolean).forEach((input) => {
    input.addEventListener("change", () => {
      setReportsStatus("");
      syncReportsSearchInputs(input === reportsSearchNomeInput ? "nome" : "chave");
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitReportsSearch();
      }
    });
  });
  resetReportsView();
  if (changePasswordForm) {
    changePasswordForm.addEventListener("submit", (event) => {
      event.preventDefault();
      submitChangePassword().catch((error) => setChangePasswordStatus(error.message, "error"));
    });
  }
  [changePasswordCurrentInput, changePasswordNewInput, changePasswordConfirmInput].filter(Boolean).forEach((input) => {
    input.addEventListener("input", () => {
      if (input === changePasswordCurrentInput) {
        scheduleChangePasswordVerification();
      } else {
        syncChangePasswordFormState();
      }
    });
  });
  if (changePasswordBackButton) {
    changePasswordBackButton.addEventListener("click", closeChangePasswordModal);
  }
  if (changePasswordModal) {
    changePasswordModal.addEventListener("click", (event) => {
      if (event.target.id === "changePasswordModal") {
        closeChangePasswordModal();
      }
    });
  }
  if (requestAdminModal) {
    requestAdminModal.addEventListener("click", (event) => {
      if (event.target.id === "requestAdminModal") {
        closeRequestAdminModal();
      }
    });
  }
  if (requestAdminButton) {
    requestAdminButton.addEventListener("click", openRequestAdminModal);
  }
  if (requestAdminBackButton) {
    requestAdminBackButton.addEventListener("click", closeRequestAdminModal);
  }
  if (requestAdminChaveInput) {
    requestAdminChaveInput.addEventListener("input", scheduleRequestAdminLookup);
  }
  if (requestAdminRegistrationForm) {
    requestAdminRegistrationForm.addEventListener("submit", (event) => {
      event.preventDefault();
      submitRequestAdminRegistration().catch((error) => {
        setRequestAdminRegistrationStatus(error.message, "error");
      });
    });
  }
  [
    requestAdminRegistrationNomeInput,
    requestAdminRegistrationProjetoSelect,
    requestAdminRegistrationSenhaInput,
    requestAdminRegistrationConfirmInput,
  ].filter(Boolean).forEach((input) => {
    input.addEventListener("input", syncRequestAdminRegistrationFormState);
    input.addEventListener("change", syncRequestAdminRegistrationFormState);
  });
  if (requestAdminRegistrationBackButton) {
    requestAdminRegistrationBackButton.addEventListener("click", returnToRequestAdminLookupModal);
  }
  if (requestAdminRegistrationModal) {
    requestAdminRegistrationModal.addEventListener("click", (event) => {
      if (event.target.id === "requestAdminRegistrationModal") {
        returnToRequestAdminLookupModal();
      }
    });
  }

  document.getElementById("clearEvents").addEventListener("click", () => {
    archiveAndClearEvents().catch((error) => setStatus(error.message, false));
  });
  document.getElementById("closeEventDetails").addEventListener("click", closeEventDetails);
  document.getElementById("closeEventArchives").addEventListener("click", closeEventArchivesModal);
  document.getElementById("closeEventArchivesFooter").addEventListener("click", closeEventArchivesModal);
  document.getElementById("downloadAllEventArchives").addEventListener("click", () => {
    downloadAllEventArchives().catch((error) => setStatus(error.message, false));
  });
  document.getElementById("eventArchivesFilter").addEventListener("input", (event) => {
    eventArchivesFilterQuery = event.target.value || "";
    eventArchivesPage = 1;
    loadEventArchives().catch((error) => setStatus(error.message, false));
  });
  document.getElementById("eventArchivesPrev").addEventListener("click", () => {
    if (eventArchivesPage > 1) {
      eventArchivesPage -= 1;
      loadEventArchives().catch((error) => setStatus(error.message, false));
    }
  });
  document.getElementById("eventArchivesNext").addEventListener("click", () => {
    if (eventArchivesPage < eventArchivesTotalPages) {
      eventArchivesPage += 1;
      loadEventArchives().catch((error) => setStatus(error.message, false));
    }
  });
  document.getElementById("eventDetailsModal").addEventListener("click", (event) => {
    if (event.target.id === "eventDetailsModal") {
      closeEventDetails();
    }
  });
  document.getElementById("eventArchivesModal").addEventListener("click", (event) => {
    if (event.target.id === "eventArchivesModal") {
      closeEventArchivesModal();
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && isAuthenticated) {
      requestRefreshAllTables();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeEventDetails();
      closeEventArchivesModal();
      closeChangePasswordModal();
      const requestAdminRegistrationOpen = requestAdminRegistrationModal && !requestAdminRegistrationModal.classList.contains("hidden");
      if (requestAdminRegistrationOpen) {
        returnToRequestAdminLookupModal();
        return;
      }
      if (requestAdminModal && !requestAdminModal.classList.contains("hidden")) {
        closeRequestAdminModal();
      }
    }
  });
  const handleAdminResponsiveViewportChange = () => {
    scheduleUserFieldTextareaRefresh();
    scheduleAdminResponsiveSync();
  };

  window.addEventListener("resize", handleAdminResponsiveViewportChange);
  window.addEventListener("orientationchange", () => {
    scheduleAdminResponsiveSync({ force: true });
  });

  const adminViewportMediaQuery = getAdminViewportMediaQueryList();
  if (adminViewportMediaQuery) {
    const handleViewportMediaQueryChange = () => {
      scheduleAdminResponsiveSync({ force: true });
    };

    if (typeof adminViewportMediaQuery.addEventListener === "function") {
      adminViewportMediaQuery.addEventListener("change", handleViewportMediaQueryChange);
    } else if (typeof adminViewportMediaQuery.addListener === "function") {
      adminViewportMediaQuery.addListener(handleViewportMediaQueryChange);
    }
  }

  document.getElementById("eventArchivesBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName === "BUTTON" && target.dataset.archiveDownload) {
      downloadEventArchive(target.dataset.archiveDownload).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.archiveDelete) {
      const fileName = target.dataset.archiveDelete;
      const confirmed = window.confirm(`Deseja excluir permanentemente o arquivo ${fileName}?`);
      if (!confirmed) {
        return;
      }
      deleteEventArchive(fileName).catch((error) => setStatus(error.message, false));
    }
  });

  document.getElementById("pendingBody").addEventListener("click", (event) => {
    const target = event.target;
    const button = target instanceof Element ? target.closest("button") : null;
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }
    if (button.dataset.projectMembershipToggle) {
      openProjectMembershipPanelByKey(button.dataset.projectMembershipToggle).catch((error) => setStatus(error.message, false));
      return;
    }
    if (button.dataset.projectMembershipBack) {
      closeProjectMembershipPanel(getProjectMembershipEditorByKey(button.dataset.projectMembershipBack));
      return;
    }
    if (button.dataset.projectMembershipApply) {
      applyProjectMembershipPanelByKey(button.dataset.projectMembershipApply);
      return;
    }
    if (button.dataset.edit) {
      setPendingEditingState(button.dataset.edit, true);
      return;
    }
    if (button.dataset.remove) {
      removePending(button.dataset.remove).catch((error) => setStatus(error.message, false));
      return;
    }
    if (button.dataset.save) {
      savePending(button.dataset.save, button.dataset.rfid).catch((error) => setStatus(error.message, false));
    }
  });

  document.getElementById("addLocationButton").addEventListener("click", addLocationRow);
  document.getElementById("saveLocationSettingsButton").addEventListener("click", () => {
    saveLocationSettings().catch((error) => setStatus(error.message, false));
  });
  bindLocationSettingsInput("locationAccuracyThresholdMeters");
  bindLocationSettingsInput("mixedZoneIntervalMinutes");

  document.getElementById("locationsBody").addEventListener("click", (event) => {
    const body = event.currentTarget;
    const target = event.target;
    const button = target instanceof Element ? target.closest("button") : null;
    if (!(body instanceof Element) || !button || !body.contains(button)) {
      return;
    }
    if (button.dataset.locationProjectsToggle) {
      const row = getLocationRowById(button.dataset.locationProjectsToggle);
      if (!row) {
        return;
      }

      if (!row.isEditing) {
        setStatus("Clique em Editar antes de alterar os projetos da localização.", false);
        return;
      }

      if (row.projectPickerOpen) {
        saveLocationRow(row.id).catch((error) => setStatus(error.message, false));
        return;
      }

      captureLocationRowDraft(row.id);
      row.projectPickerOpen = true;
      renderLocations();
      if (row.projectPickerOpen) {
        focusLocationProjectPicker(row.id);
      }
      return;
    }
    if (button.dataset.locationEdit) {
      const row = getLocationRowById(button.dataset.locationEdit);
      if (!row) {
        return;
      }
      if (row.isEditing) {
        saveLocationRow(button.dataset.locationEdit).catch((error) => setStatus(error.message, false));
        return;
      }
      setLocationEditingState(button.dataset.locationEdit, true);
      return;
    }
    if (button.dataset.locationAddCoordinate) {
      addLocationCoordinate(button.dataset.locationAddCoordinate);
      return;
    }
    if (button.dataset.locationCoordinateMove) {
      moveLocationCoordinate(
        button.dataset.locationCoordinateMove,
        button.dataset.coordinateId,
        button.dataset.direction,
      );
      return;
    }
    if (button.dataset.locationCoordinateRemove) {
      removeLocationCoordinate(
        button.dataset.locationCoordinateRemove,
        button.dataset.coordinateId,
      );
      return;
    }
    if (button.dataset.locationRemove) {
      removeLocationRow(button.dataset.locationRemove).catch((error) => setStatus(error.message, false));
    }
  });

  document.getElementById("usersBody").addEventListener("click", (event) => {
    const target = event.target;
    const button = target instanceof Element ? target.closest("button") : null;
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }
    if (button.dataset.projectMembershipToggle) {
      openProjectMembershipPanelByKey(button.dataset.projectMembershipToggle).catch((error) => setStatus(error.message, false));
      return;
    }
    if (button.dataset.projectMembershipBack) {
      closeProjectMembershipPanel(getProjectMembershipEditorByKey(button.dataset.projectMembershipBack));
      return;
    }
    if (button.dataset.projectMembershipApply) {
      applyProjectMembershipPanelByKey(button.dataset.projectMembershipApply);
      return;
    }
    if (button.dataset.userEdit) {
      setRegisteredUserEditingState(button.dataset.userEdit, true);
      return;
    }
    if (button.dataset.userSave) {
      saveRegisteredUser(button.dataset.userSave).catch((error) => setStatus(error.message, false));
      return;
    }
    if (button.dataset.userPasswordReset) {
      resetRegisteredUserPassword(button.dataset.userPasswordReset).catch((error) => setStatus(error.message, false));
      return;
    }
    if (button.dataset.userRemove) {
      removeRegisteredUser(button.dataset.userRemove).catch((error) => setStatus(error.message, false));
    }
  });

  if (addProjectButton) {
    addProjectButton.addEventListener("click", () => {
      resetProjectEditor({ focus: true });
    });
  }

  if (saveProjectButton) {
    saveProjectButton.addEventListener("click", () => {
      saveProject().catch((error) => setStatus(error.message, false));
    });
  }

  if (cancelProjectEditButton) {
    cancelProjectEditButton.addEventListener("click", () => {
      resetProjectEditor({ focus: true });
    });
  }

  if (projectCountrySelect) {
    projectCountrySelect.addEventListener("change", () => {
      const selectedCountry = getSelectedProjectCountryOption();
      syncProjectTimezoneInput(
        selectedCountry ? selectedCountry.timezone_name : DEFAULT_PROJECT_TIMEZONE,
        selectedCountry ? selectedCountry.name : DEFAULT_PROJECT_COUNTRY_NAME,
      );
      if (projectCustomCountryInput) {
        projectCustomCountryInput.value = "";
      }
    });
  }

  if (projectTimezoneInput) {
    projectTimezoneInput.addEventListener("input", () => {
      syncProjectTimezoneSuggestions(projectTimezoneInput.value);
    });
  }

  const projectsBody = document.getElementById("projectsBody");
  if (projectsBody) {
    projectsBody.addEventListener("click", (event) => {
      const target = event.target;
      if (target.tagName === "BUTTON" && target.dataset.projectEdit) {
        startProjectEdit(target.dataset.projectEdit);
        return;
      }
      if (target.tagName === "BUTTON" && target.dataset.projectRemove) {
        removeProject(target.dataset.projectRemove).catch((error) => setStatus(error.message, false));
      }
    });
  }

  syncProjectEditorState();

  document.getElementById("inactiveBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName === "BUTTON" && target.dataset.userRemove) {
      removeRegisteredUser(target.dataset.userRemove).catch((error) => setStatus(error.message, false));
    }
  });

  const missingCheckoutBody = document.getElementById("missingCheckoutBody");
  if (missingCheckoutBody) {
    missingCheckoutBody.addEventListener("click", (event) => {
      const target = event.target;
      if (target.tagName === "BUTTON" && target.dataset.userRemove) {
        removeRegisteredUser(target.dataset.userRemove).catch((error) => setStatus(error.message, false));
      }
    });
  }

  document.getElementById("administratorsBody").addEventListener("click", (event) => {
    const target = event.target;
    if (target.tagName === "BUTTON" && target.dataset.adminApprove) {
      approveAdministrator(target.dataset.adminApprove).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.adminReject) {
      rejectAdministrator(target.dataset.adminReject).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.adminProfileSave) {
      saveAdministratorProfile(target.dataset.adminProfileSave).catch((error) => setStatus(error.message, false));
      return;
    }
    if (target.tagName === "BUTTON" && target.dataset.adminRevoke) {
      revokeAdministrator(target.dataset.adminRevoke).catch((error) => setStatus(error.message, false));
    }
  });

  Object.keys(presenceTableStates).forEach((tableKey) => {
    syncPresenceControls(tableKey);
    syncPresenceSortHeaders(tableKey);
  });
}

async function bootstrap() {
  bindActions();
  syncAdminResponsiveState({ force: true });
  updateOperationalChrome();
  updateDashboardSummary();
  try {
    await bootstrapAdmin();
  } catch (error) {
    showAuthShell(error.message, "error");
  }
}

bootstrap();
