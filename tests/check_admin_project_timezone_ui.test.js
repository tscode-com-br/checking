const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const adminHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/index.html'),
  'utf8'
);

const adminJs = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/app.js'),
  'utf8'
);

test('admin tables expose country and timezone columns for project-aware rendering', () => {
  assert.match(adminHtml, /<tr><th>Recebimento<\/th><th>Chave<\/th><th>Nome<\/th><th>Projeto<\/th><th>Fuso horário<\/th><th>Atividade<\/th><th>Informe<\/th><th>Data<\/th><th>Hora<\/th><\/tr>/);
  assert.match(adminHtml, /id="projectNameInput"/);
  assert.match(adminHtml, /id="projectCountrySelect"/);
  assert.match(adminHtml, /id="projectTimezoneInput"/);
  assert.match(adminHtml, /id="projectCustomCountryInput"/);
  assert.match(adminHtml, /id="projectTimezoneOptions"/);
  assert.match(adminHtml, /id="saveProjectButton"/);
  assert.match(adminHtml, /id="cancelProjectEditButton"/);
  assert.match(adminHtml, /<tr><th>Nome do Projeto<\/th><th>País<\/th><th>Fuso horário<\/th><th>Ações<\/th><\/tr>/);
  assert.match(adminHtml, /<tr><th>ID<\/th><th>Horário<\/th><th>Origem<\/th><th>Ação<\/th><th>Status<\/th><th>Device<\/th><th>Local<\/th><th>RFID<\/th><th>Chave<\/th><th>Projeto<\/th><th>Fuso horário<\/th><th>Ontime<\/th><th>HTTP<\/th><th>Tentativas<\/th><th>Detalhes<\/th><\/tr>/);
  assert.match(adminHtml, /data-sort-table="checkin"[\s\S]*<th>Fuso horário<\/th>[\s\S]*data-sort-table="checkout"/);
  assert.match(adminHtml, /data-sort-table="inactive"[\s\S]*<th>Fuso horário<\/th>[\s\S]*<span>Última Atividade<\/span>/);
});

test('admin javascript formats and renders timestamps using per-row timezone metadata', () => {
  assert.match(adminJs, /function resolveDisplayTimeZoneName\(timezoneName\) \{/);
  assert.match(adminJs, /function formatDateTime\(value, timezoneName = DEFAULT_DISPLAY_TIMEZONE\) \{/);
  assert.match(adminJs, /function formatDateTimeLines\(value, timezoneName = DEFAULT_DISPLAY_TIMEZONE\) \{/);
  assert.match(adminJs, /function getDayKey\(value, timezoneName = DEFAULT_DISPLAY_TIMEZONE\) \{/);
  assert.match(adminJs, /function getCalendarDayDiff\(value, timezoneName = DEFAULT_DISPLAY_TIMEZONE\) \{/);
  assert.match(adminJs, /function formatTimeZoneLabel\(timezoneLabel\) \{/);
  assert.match(adminJs, /const SUPPORTED_PROJECT_COUNTRIES = Object\.freeze\(\[/);
  assert.match(adminJs, /code: "BR", name: "Brasil", timezone_name: "America\/Sao_Paulo"/);
  assert.match(adminJs, /code: "CN", name: "China", timezone_name: "Asia\/Shanghai"/);
  assert.match(adminJs, /code: "SG", name: "Singapura", timezone_name: "Asia\/Singapore"/);
  assert.match(adminJs, /function syncProjectEditorState\(options = \{\}\) \{/);
  assert.match(adminJs, /function resetProjectEditor\(options = \{\}\) \{/);
  assert.match(adminJs, /function startProjectEdit\(projectId\) \{/);
  assert.match(adminJs, /async function saveProject\(\) \{/);
  assert.match(adminJs, /async function putJson\(url, body\) \{/);
  assert.match(adminJs, /function deriveProjectCountryCode\(countryName, fallbackCode = ""\) \{/);
  assert.match(adminJs, /function syncProjectTimezoneInput\(selectedValue = "", preferredCountryName = DEFAULT_PROJECT_COUNTRY_NAME\) \{/);
  assert.match(adminJs, /formatDateTime\(row\.time, row\.timezone_name\)/);
  assert.match(adminJs, /formatDateTime\(row\.latest_time, row\.timezone_name\)/);
  assert.match(adminJs, /makeEventDateTimeCell\(row\.event_time, row\.timezone_name\)/);
  assert.match(adminJs, /makeEventDateTimeCell\(row\.recebimento, row\.timezone_name\)/);
  assert.match(adminJs, /formatTimeZoneLabel\(row\.timezone_label\)/);
  assert.match(adminJs, /project\.country_name \|\| "-"/);
  assert.match(adminJs, /data-project-edit="\$\{project\.id\}"/);
  assert.match(adminJs, /const customCountryName = normalizeProjectCountryName\(projectCustomCountryInput \? projectCustomCountryInput\.value : ""\);/);
  assert.match(adminJs, /const timezoneName = normalizeProjectTimezoneName\(projectTimezoneInput \? projectTimezoneInput\.value : ""\);/);
  assert.match(adminJs, /const projectPayload = \{[\s\S]*country_code: countryCode,[\s\S]*country_name: countryName,[\s\S]*timezone_name: timezoneName,[\s\S]*\};/);
  assert.match(adminJs, /await postJson\("\/api\/admin\/projects", projectPayload\)/);
  assert.match(adminJs, /await putJson\(`\/api\/admin\/projects\/\$\{normalizedProjectId\}`, projectPayload\)/);
  assert.match(adminJs, /projectCountrySelect\.addEventListener\("change", \(\) => \{/);
  assert.doesNotMatch(adminJs, /window\.prompt\("Informe o nome do projeto\."\)/);
  assert.doesNotMatch(adminJs, /function getSingaporeDayKey\(/);
  assert.doesNotMatch(adminJs, /function getSingaporeCalendarDayDiff\(/);
});