const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const adminHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/index.html'),
  'utf8'
);

const adminCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/styles.css'),
  'utf8'
);

const adminJs = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/app.js'),
  'utf8'
);

test('check-in and check-out tables share the same fixed-width class', () => {
  assert.match(adminHtml, /id="tab-checkin"[\s\S]*class="responsive-table presence-users-table"/);
  assert.match(adminHtml, /id="tab-checkout"[\s\S]*class="responsive-table presence-users-table"/);
  assert.match(adminHtml, /data-filter-toggle="checkin"[\s\S]*aria-controls="checkinFilters"/);
  assert.match(adminHtml, /data-filter-toggle="checkout"[\s\S]*aria-controls="checkoutFilters"/);
  assert.match(adminHtml, /data-presence-name-filter-label="checkin">Filtrar Nome</);
  assert.match(adminHtml, /data-presence-name-filter-label="checkout">Filtrar Nome</);
  assert.match(adminHtml, /data-presence-primary-filter-label="checkin">Filtrar Horário</);
  assert.match(adminHtml, /data-presence-primary-filter-label="checkout">Filtrar Horário</);
  assert.match(adminHtml, /data-presence-primary-header-label="checkin">Horário</);
  assert.match(adminHtml, /data-presence-primary-header-label="checkout">Horário</);
  assert.match(adminHtml, /data-presence-name-header-label="checkin">Nome</);
  assert.match(adminHtml, /data-presence-name-header-label="checkout">Nome</);
  assert.match(adminHtml, /id="checkinFilters" class="presence-controls" data-presence-table="checkin" data-filter-panel="checkin"/);
  assert.match(adminHtml, /id="checkoutFilters" class="presence-controls" data-presence-table="checkout" data-filter-panel="checkout"/);
  assert.match(adminCss, /\.presence-users-table \{[\s\S]*width:\s*100%;[\s\S]*min-width:\s*0;[\s\S]*table-layout:\s*fixed;/);
  assert.match(adminCss, /\.presence-users-table th:nth-child\(2\),[\s\S]*\.presence-users-table td:nth-child\(2\) \{[\s\S]*width:\s*20%;/);
  assert.match(adminCss, /\.presence-users-table th,\s*[\r\n]+\.presence-users-table td \{[\s\S]*font-size:\s*12px;[\s\S]*line-height:\s*1\.2;/);
  assert.match(adminCss, /\.presence-users-table tbody td \{[\s\S]*font-weight:\s*400;/);
});

test('admin mobile shell exposes a scrollable tab strip and collapsible filter panels for dense sections', () => {
  assert.match(adminHtml, /data-filter-toggle="inactive"[\s\S]*aria-controls="inactiveFilters"/);
  assert.match(adminHtml, /data-filter-toggle="relatorios"[\s\S]*aria-controls="reportsSearchPanel"/);
  assert.match(adminHtml, /id="inactiveFilters" class="presence-controls" data-presence-table="inactive" data-filter-panel="inactive"/);
  assert.match(adminHtml, /id="reportsSearchPanel" class="project-editor-panel reports-search-panel" data-filter-panel="relatorios"/);
  assert.match(adminHtml, /class="secondary-button filter-toggle-button hidden"/);
  assert.match(adminCss, /\.filter-toggle-button \{[\s\S]*min-width:\s*152px;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.session-bar \{[\s\S]*justify-content:\s*space-between;[\s\S]*background:\s*rgba\(255, 255, 255, 0\.14\);/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.tabs \{[\s\S]*display:\s*flex;[\s\S]*overflow-x:\s*auto;[\s\S]*scroll-snap-type:\s*x proximity;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.tabs button \{[\s\S]*flex:\s*0 0 auto;[\s\S]*border-radius:\s*999px;[\s\S]*white-space:\s*nowrap;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.section-header-actions \{[\s\S]*display:\s*grid;[\s\S]*grid-template-columns:\s*repeat\(auto-fit, minmax\(0, 1fr\)\);/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.section-header-actions--mobile-tools \{[\s\S]*grid-template-columns:\s*1fr;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.presence-controls-grid \{[\s\S]*grid-template-columns:\s*1fr;/);
});

test('presence tables expose explicit viewport helpers and responsive render state', () => {
  assert.match(adminJs, /const ADMIN_MOBILE_VIEWPORT_QUERY = "\(max-width: 800px\)";/);
  assert.match(adminJs, /function getAdminViewportMediaQueryList\(\) \{/);
  assert.match(adminJs, /function isMobileAdminViewport\(\) \{/);
  assert.match(adminJs, /function isLimitedMobileAdminView\(\) \{/);
  assert.match(adminJs, /function getPresenceResponsiveVariant\(tableKey\) \{/);
  assert.match(adminJs, /return "mobile-limited";/);
  assert.match(adminJs, /return isMobileAdminViewport\(\) \? "mobile" : "desktop";/);
  assert.match(adminJs, /function syncAdminResponsiveDatasets\(snapshot = buildAdminResponsiveStateSnapshot\(\)\) \{/);
  assert.match(adminJs, /element\.dataset\.adminViewport = snapshot\.viewport;/);
  assert.match(adminJs, /controls\.dataset\.presenceRenderVariant = variant;/);
  assert.match(adminJs, /table\.dataset\.presenceRenderVariant = variant;/);
  assert.match(adminJs, /function syncAdminResponsiveState\(options = \{\}\) \{/);
  assert.match(adminJs, /syncPresenceTimeLabels\(\);/);
  assert.match(adminJs, /syncFormsTimeColumnVisibility\(\);/);
  assert.match(adminJs, /syncEventsPrimaryColumnLabel\(\);/);
  assert.match(adminJs, /applyPresenceTableState\(tableKey\);/);
  assert.match(adminJs, /function scheduleAdminResponsiveSync\(options = \{\}\) \{/);
  assert.match(adminJs, /window\.requestAnimationFrame\(\(\) => \{/);
});

test('presence tables use safe activity-time helpers and dynamic labels', () => {
  assert.match(adminJs, /let adminCanViewActivityTime = true;/);
  assert.match(adminJs, /function isLimitedMobilePresenceVariant\(tableKey, responsiveVariant = getPresenceResponsiveVariant\(tableKey\)\) \{/);
  assert.match(adminJs, /function syncPresenceTimeLabels\(\) \{/);
  assert.match(adminJs, /function buildPresencePrimaryDisplayParts\(row, options = \{\}\) \{/);
  assert.match(adminJs, /function buildPresencePrimaryDisplay\(row, options = \{\}\) \{/);
  assert.match(adminJs, /function buildPresencePrimaryCell\(row, options = \{\}\) \{/);
  assert.match(adminJs, /function buildPresenceMobileMetadata\(row, options = \{\}\) \{/);
  assert.match(adminJs, /function buildLimitedPresenceMobileCard\(row, timeCell\) \{/);
  assert.match(adminJs, /function buildPresenceMobileCard\(row, timeCell, options = \{\}\) \{/);
  assert.match(adminJs, /activity_date_label/);
  assert.match(adminJs, /activity_time_label/);
  assert.match(adminJs, /activity_day_key/);
  assert.match(adminJs, /if \(getPresenceResponsiveVariant\(tableKey\) !== "desktop"\) \{[\s\S]*return "Data";[\s\S]*\}/);
  assert.match(adminJs, /if \(getPresenceResponsiveVariant\(tableKey\) !== "desktop"\) \{[\s\S]*return "Filtrar Data";[\s\S]*\}/);
  assert.match(adminJs, /return canCurrentAdminViewActivityTime\(\) \? "Filtrar Horário" : "Filtrar Data";/);
  assert.match(adminJs, /const filterLabel = document\.querySelector\(`\[data-presence-primary-filter-label="\$\{tableKey\}"\]`\);/);
  assert.match(adminJs, /filterLabel\.textContent = getPresencePrimaryFilterLabel\(tableKey\);/);
  assert.match(adminJs, /const nameHeaderLabel = document\.querySelector\(`\[data-presence-name-header-label="\$\{tableKey\}"\]`\);/);
  assert.match(adminJs, /nameHeaderLabel\.textContent = getPresenceNameColumnLabel\(tableKey\);/);
  assert.match(adminJs, /const nameFilterLabel = document\.querySelector\(`\[data-presence-name-filter-label="\$\{tableKey\}"\]`\);/);
  assert.match(adminJs, /nameFilterLabel\.textContent = getPresenceNameFilterLabel\(tableKey\);/);
  assert.match(adminJs, /querySelector\("\.sortable-header span"\)\?\.textContent\?\.trim\(\)/);
  assert.match(adminJs, /function shouldUseInlinePresenceDateTime\(displayParts, options = \{\}\) \{/);
  assert.match(adminJs, /return options\.responsiveVariant === "desktop" && Boolean\(displayParts\?\.timeLabel\);/);
  assert.match(adminJs, /const responsiveVariant = options\.responsiveVariant \|\| "desktop";/);
  assert.match(adminJs, /const timeLabel = responsiveVariant === "desktop" \? getPresenceActivityTimeLabel\(row\) : "";/);
  assert.match(adminJs, /inline: shouldUseInlinePresenceDateTime\(displayParts, \{ responsiveVariant \}\),/);
  assert.match(adminJs, /const \{ highlightMissingCheckout = false, includeElapsedDays = false, responsiveVariant = "desktop" \} = options;/);
  assert.match(adminJs, /const timeCell = buildPresencePrimaryCell\(row, \{ includeElapsedDays, responsiveVariant \}\);/);
  assert.match(adminJs, /if \(responsiveVariant !== "desktop"\) \{[\s\S]*tr\.classList\.add\("presence-mobile-row"\);[\s\S]*colspan="7" class="presence-mobile-card-cell"[\s\S]*buildPresenceMobileCard\(row, timeCell, \{ responsiveVariant \}\)[\s\S]*return tr;[\s\S]*\}/);
  assert.match(adminJs, /responsiveVariant: getPresenceResponsiveVariant\(tableKey\),/);
  assert.match(adminJs, /tr\.innerHTML = `<td>\$\{timeCell\.html\}<\/td><td>\$\{escapeHtml\(row\.nome\)\}<\/td>/);
  assert.match(adminJs, /const parsedDay = Date\.parse\(activityDayKey \? `\$\{activityDayKey\}T00:00:00Z` : ""\);/);
  assert.match(adminJs, /renderEmptyStateRow\(bodyId, 7, options\.emptyMessage \|\| "Nenhum registro encontrado\."\);/);
});

test('presence tables aggregate plural memberships for project display, sorting and filtering', () => {
  assert.match(adminJs, /function getUserMembershipProjectNames\(row\) \{/);
  assert.match(adminJs, /function formatUserMembershipProjects\(row, emptyLabel = "-"\) \{/);
  assert.match(adminJs, /filterColumns: \["time", "nome", "chave", "projetos", "assiduidade", "local"\],/);
  assert.match(adminJs, /filterColumns: \["nome", "chave", "projetos", "latest_time", "inactivity_days"\],/);
  assert.match(adminJs, /const projectsLabel = formatUserMembershipProjects\(row\);/);
  assert.match(adminJs, /if \(key === "projetos"\) \{[\s\S]*return formatUserMembershipProjects\(row\);/);
  assert.match(adminJs, /<span class="admin-mobile-card-label">Projetos<\/span><span class="admin-mobile-card-value">\$\{escapeHtml\(projectsLabel\)\}<\/span>/);
});

test('presence tables use dedicated mobile cards instead of the generic stacked td label layout', () => {
  assert.match(adminJs, /if \(options\.responsiveVariant === "mobile-limited"\) \{[\s\S]*return buildLimitedPresenceMobileCard\(row, timeCell\);[\s\S]*\}/);
  assert.match(adminJs, /return `<article class="presence-mobile-card presence-mobile-card--compact"><div class="presence-mobile-card-primary">\$\{timeCell\.html\}<\/div><p class="presence-mobile-card-main"><span class="presence-mobile-card-name">\$\{escapeHtml\(row\.nome\)\}<\/span><span class="presence-mobile-card-context"> @ <\/span><span class="presence-mobile-card-local">\$\{localLabel\}<\/span><\/p><\/article>`;/);
  assert.match(adminJs, /return `<article class="presence-mobile-card presence-mobile-card--limited"><div class="presence-mobile-card-primary">\$\{timeCell\.html\}<\/div><p class="presence-mobile-card-main"><span class="presence-mobile-card-name">\$\{escapeHtml\(row\.nome\)\}<\/span><span class="presence-mobile-card-context"> @ <\/span><span class="presence-mobile-card-local">\$\{localLabel\}<\/span><\/p><\/article>`;/);
  assert.match(adminCss, /\.presence-mobile-card \{[\s\S]*display:\s*grid;[\s\S]*width:\s*100%;[\s\S]*box-sizing:\s*border-box;[\s\S]*padding:\s*8px 10px;[\s\S]*border-radius:\s*10px;[\s\S]*box-shadow:\s*none;/);
  assert.match(adminCss, /\.presence-mobile-card--limited \{[\s\S]*gap:\s*4px;/);
  assert.match(adminCss, /\.presence-mobile-card-primary \.event-cell,[\s\S]*\.presence-mobile-card-primary \.event-datetime-cell \{[\s\S]*text-align:\s*left;[\s\S]*align-items:\s*flex-start;/);
  assert.match(adminCss, /\.presence-mobile-card-primary \.event-datetime-line \{[\s\S]*font-size:\s*12px;[\s\S]*font-weight:\s*500;/);
  assert.match(adminCss, /\.presence-mobile-card-main \{[\s\S]*font-size:\s*12px;[\s\S]*line-height:\s*1\.2;[\s\S]*overflow-wrap:\s*anywhere;/);
  assert.match(adminCss, /\.presence-mobile-card-name \{[\s\S]*display:\s*inline;[\s\S]*font-size:\s*inherit;[\s\S]*font-weight:\s*400;/);
  assert.match(adminCss, /\.presence-mobile-card-context \{[\s\S]*color:\s*#334155;[\s\S]*font-weight:\s*400;/);
  assert.match(adminCss, /\.presence-mobile-card-local \{[\s\S]*font-size:\s*inherit;[\s\S]*font-weight:\s*400;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.presence-users-table\[data-presence-render-variant="mobile"\] tr\.presence-mobile-row,[\s\S]*\.presence-users-table\[data-presence-render-variant="mobile-limited"\] tr\.presence-mobile-row \{[\s\S]*border:\s*0;[\s\S]*background:\s*transparent;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.presence-users-table\[data-presence-render-variant="mobile"\] td\.presence-mobile-card-cell,[\s\S]*\.presence-users-table\[data-presence-render-variant="mobile-limited"\] td\.presence-mobile-card-cell \{[\s\S]*display:\s*block;[\s\S]*width:\s*100%;[\s\S]*padding:\s*0;[\s\S]*text-align:\s*left;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.presence-users-table\[data-presence-render-variant="mobile"\] td\.presence-mobile-card-cell::before,[\s\S]*\.presence-users-table\[data-presence-render-variant="mobile-limited"\] td\.presence-mobile-card-cell::before \{[\s\S]*content:\s*none;/);
});

test('limited mobile presence keeps only Data, Nome do Usuario and Local with coherent filters', () => {
  assert.match(adminJs, /function getVisiblePresenceFilterKeys\(tableKey\) \{[\s\S]*if \(isLimitedMobilePresenceVariant\(tableKey\)\) \{[\s\S]*return \["time", "nome", "local"\];[\s\S]*\}[\s\S]*return state\.filterColumns;[\s\S]*\}/);
  assert.match(adminJs, /function syncPresenceResponsiveControls\(tableKey\) \{[\s\S]*field\.hidden = !isVisible;[\s\S]*field\.classList\.toggle\("hidden", !isVisible\);[\s\S]*if \(!isVisible\) \{[\s\S]*state\.filters\[key\] = "";[\s\S]*control\.value = "";[\s\S]*\}[\s\S]*\}/);
  assert.match(adminJs, /return isLimitedMobilePresenceVariant\(tableKey\) \? "Nome do Usuário" : "Nome";/);
  assert.match(adminJs, /return isLimitedMobilePresenceVariant\(tableKey\) \? "Filtrar Nome do Usuário" : "Filtrar Nome";/);
  assert.match(adminJs, /if \(key === "time"\) \{[\s\S]*responsiveVariant: getPresenceResponsiveVariant\(tableKey\),[\s\S]*\}/);
  assert.match(adminJs, /refreshPresenceFilterOptions\(tableKey\);[\s\S]*syncPresenceResponsiveControls\(tableKey\);[\s\S]*const filteredRows = filterPresenceRows\(tableKey, state\.rawRows, state\.filters\);/);
});

test('presence responsive sync sanitizes hidden sort state and empty-state filters by active variant', () => {
  assert.match(adminJs, /function getVisiblePresenceSortKeys\(tableKey\) \{[\s\S]*if \(isLimitedMobilePresenceVariant\(tableKey\)\) \{[\s\S]*return \["time", "nome", "local"\];[\s\S]*\}[\s\S]*return state\.filterColumns;[\s\S]*\}/);
  assert.match(adminJs, /function sanitizePresenceSortState\(tableKey\) \{[\s\S]*if \(visibleSortKeys\.includes\(state\.sortKey\)\) \{[\s\S]*return;[\s\S]*\}[\s\S]*const fallbackSortKey = visibleSortKeys\.includes\(state\.defaultSortKey\)[\s\S]*state\.sortKey = fallbackSortKey;[\s\S]*state\.sortDirection = getPresenceDefaultSortDirection\(fallbackSortKey\);[\s\S]*\}/);
  assert.match(adminJs, /sanitizePresenceSortState\(tableKey\);[\s\S]*const visibleFilterKeys = new Set\(getVisiblePresenceFilterKeys\(tableKey\)\);/);
  assert.match(adminJs, /control\.disabled = !isVisible;[\s\S]*control\.setAttribute\("aria-hidden", String\(!isVisible\)\);/);
  assert.match(adminJs, /const clearButton = container\.querySelector\("\[data-presence-clear\]"\);[\s\S]*clearButton\.disabled = !hasVisibleActiveFilters;/);
  assert.match(adminJs, /return getVisiblePresenceFilterKeys\(tableKey\)[\s\S]*\.some\(\(key\) => String\(state\.filters\[key\] \|\| ""\)\.trim\(\)\);/);
  assert.match(adminJs, /const visibleFilterKeys = getVisiblePresenceFilterKeys\(tableKey\);[\s\S]*return rows\.filter\(\(row\) => visibleFilterKeys\.every/);
  assert.match(adminJs, /container\.querySelectorAll\("\[data-presence-filter\]"\)\.forEach\(\(control\) => \{[\s\S]*control\.value = state\.filters\[key\] \|\| "";[\s\S]*\}\);[\s\S]*syncPresenceResponsiveControls\(tableKey\);/);
  assert.match(adminJs, /const visibleSortKeys = new Set\(getVisiblePresenceSortKeys\(tableKey\)\);[\s\S]*button\.hidden = !isVisible;[\s\S]*button\.disabled = !isVisible;[\s\S]*button\.tabIndex = isVisible \? 0 : -1;[\s\S]*parentHeader\.hidden = !isVisible;/);
  assert.match(adminJs, /sanitizePresenceSortState\(tableKey\);[\s\S]*refreshPresenceFilterOptions\(tableKey\);[\s\S]*syncPresenceResponsiveControls\(tableKey\);[\s\S]*const filteredRows = filterPresenceRows\(tableKey, state\.rawRows, state\.filters\);/);
});

test('admin table variants stay limited to the slices that really lose a time column', () => {
  assert.match(adminCss, /\.forms-table--without-time \{/);
  assert.doesNotMatch(adminCss, /\.presence-users-table--without-time\b/);
  assert.doesNotMatch(adminCss, /\.events-table--without-time\b/);
  assert.match(adminJs, /function makeEventDateTimeCellFromParts\(dateLabel, timeLabel, options = \{\}\) \{/);
  assert.match(adminJs, /const inline = Boolean\(options\.inline && normalizedTime\);/);
  assert.match(adminJs, /const className = inline[\s\S]*"event-cell event-datetime-cell event-datetime-cell--inline"[\s\S]*"event-cell event-datetime-cell";/);
  assert.match(adminJs, /normalizedTime \? `<span class="event-datetime-line">\$\{escapeHtml\(normalizedTime\)\}<\/span>` : ""/);
  assert.match(adminCss, /\.event-datetime-cell \{[\s\S]*display:\s*flex;[\s\S]*flex-direction:\s*column;[\s\S]*align-items:\s*center;/);
  assert.match(adminCss, /\.event-datetime-line \{[\s\S]*display:\s*block;[\s\S]*white-space:\s*nowrap;/);
  assert.match(adminCss, /\.presence-users-table \.event-datetime-cell--inline \{[\s\S]*flex-direction:\s*row;[\s\S]*gap:\s*6px;/);
  assert.match(adminCss, /\.presence-users-table \.event-datetime-cell--inline \.event-datetime-line \{[\s\S]*display:\s*inline-block;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.presence-users-table \.event-datetime-cell--inline \{[\s\S]*flex-direction:\s*column;/);
});

test('inactive table uses dedicated mobile cards without losing remove actions', () => {
  assert.match(adminHtml, /class="responsive-table inactive-users-table"/);
  assert.match(adminJs, /function buildInactiveMobileCard\(row\) \{/);
  assert.match(adminJs, /if \(options\.mobile\) \{[\s\S]*tr\.classList\.add\("inactive-mobile-row"\);[\s\S]*colspan="7" class="inactive-mobile-card-cell"[\s\S]*buildInactiveMobileCard\(row\)[\s\S]*return tr;[\s\S]*\}/);
  assert.match(adminJs, /const mobile = isMobileAdminViewport\(\);[\s\S]*rows\.forEach\(\(row\) => body\.appendChild\(buildInactiveRow\(row, \{ mobile \}\)\)\);/);
  assert.match(adminCss, /\.inactive-user-row:not\(\.inactive-mobile-row\) td \{/);
  assert.match(adminCss, /\.inactive-mobile-card \{[\s\S]*background:\s*linear-gradient\(180deg, #fff7f7 0%, #ffffff 100%\);/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.inactive-users-table tr\.inactive-mobile-row,[\s\S]*\.forms-table tr\.forms-mobile-row \{[\s\S]*border:\s*0;[\s\S]*background:\s*transparent;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.inactive-users-table td\.inactive-mobile-card-cell,[\s\S]*\.forms-table td\.forms-mobile-card-cell \{[\s\S]*padding:\s*0;[\s\S]*text-align:\s*left;/);
});

test('reports and events switch to dedicated mobile cards and reuse cached results on responsive rerender', () => {
  assert.match(adminJs, /let eventsRows = null;/);
  assert.match(adminJs, /let reportsResultsPayload = null;/);
  assert.match(adminJs, /eventsTable\.dataset\.eventsRenderVariant = snapshot\.viewport === "mobile" \? "mobile" : "desktop";/);
  assert.match(adminJs, /const canViewEventsTime = syncEventsPrimaryColumnLabel\(\);[\s\S]*if \(eventsRows !== null\) \{[\s\S]*renderEventsTable\(eventsRows, \{ canViewTime: canViewEventsTime \}\);[\s\S]*\}[\s\S]*if \(reportsResultsPayload !== null\) \{[\s\S]*renderReportsResults\(reportsResultsPayload\);[\s\S]*\}/);
  assert.match(adminJs, /function buildReportsResultMobileCardMarkup\(row, options = \{\}\) \{/);
  assert.match(adminJs, /function buildReportsResultCardsMarkup\(rows, options = \{\}\) \{/);
  assert.match(adminJs, /function buildReportsResultGroupMarkup\(group, groupIndex, options = \{\}\) \{[\s\S]*const mobile = options\.mobile === true;/);
  assert.match(adminJs, /const contentMarkup = mobile[\s\S]*\? buildReportsResultCardsMarkup\(group\.rows, \{ includeTime \}\)[\s\S]*: buildReportsResultTableMarkup\(/);
  assert.match(adminJs, /const mobile = isMobileAdminViewport\(\);[\s\S]*body\.innerHTML = groups\.map\(\(group, groupIndex\) => buildReportsResultGroupMarkup\(group, groupIndex, \{[\s\S]*mobile,[\s\S]*\}\)\)\.join\(""\);/);
  assert.match(adminJs, /function buildEventMobileCard\(row, options = \{\}\) \{/);
  assert.match(adminJs, /function buildEventRow\(row, options = \{\}\) \{[\s\S]*if \(options\.mobile\) \{[\s\S]*tr\.classList\.add\("events-mobile-row"\);[\s\S]*colspan="15" class="events-mobile-card-cell"[\s\S]*mobileCard\.details[\s\S]*return tr;[\s\S]*\}/);
  assert.match(adminJs, /function renderEventsTable\(rows, options = \{\}\) \{[\s\S]*const mobile = isMobileAdminViewport\(\);[\s\S]*renderEmptyStateRow\("eventsBody", 15, "Nenhum evento encontrado\."\);[\s\S]*rows\.forEach\(\(row\) => body\.appendChild\(buildEventRow\(row, \{ mobile, canViewTime \}\)\)\);/);
  assert.match(adminJs, /eventsRows = Array\.isArray\(rows\) \? rows : \[\];[\s\S]*renderEventsTable\(eventsRows, \{ canViewTime \}\);/);
  assert.match(adminCss, /\.reports-group-header \{[\s\S]*align-items:\s*flex-start;[\s\S]*gap:\s*10px;/);
  assert.match(adminCss, /\.reports-group-count \{[\s\S]*font-weight:\s*700;[\s\S]*color:\s*#0f766e;/);
  assert.match(adminCss, /\.reports-results-cards \{[\s\S]*display:\s*grid;[\s\S]*gap:\s*12px;/);
  assert.match(adminCss, /\.events-mobile-card \{[\s\S]*border-color:\s*rgba\(14, 116, 144, 0\.18\);/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.reports-group-header \{[\s\S]*flex-direction:\s*column;[\s\S]*align-items:\s*flex-start;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.events-table\[data-events-render-variant="mobile"\] tr\.events-mobile-row \{[\s\S]*border:\s*0;[\s\S]*background:\s*transparent;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.events-table\[data-events-render-variant="mobile"\] td\.events-mobile-card-cell \{[\s\S]*padding:\s*0;[\s\S]*text-align:\s*left;/);
});

test('admin shell centralizes the sensitive-time access state and responsive sync on auth transitions', () => {
  assert.match(adminJs, /let adminCanViewActivityTime = true;/);
  assert.match(adminJs, /function setAdminAccessState\(admin\) \{[\s\S]*adminAccessScope = admin\?\.access_scope === "limited" \? "limited" : "full";[\s\S]*allowedAdminTabs = normalizeAllowedAdminTabs\(admin\?\.allowed_tabs, adminAccessScope\);[\s\S]*adminCanViewActivityTime = Boolean\(admin\?\.can_view_activity_time\);[\s\S]*applyAdminTabVisibility\(\);[\s\S]*syncAdminResponsiveState\(\{ force: true \}\);[\s\S]*\}/);
  assert.match(adminJs, /function resetAdminAccessState\(\) \{[\s\S]*adminAccessScope = "full";[\s\S]*allowedAdminTabs = getDefaultAllowedTabsForScope\(adminAccessScope\);[\s\S]*adminCanViewActivityTime = true;[\s\S]*applyAdminTabVisibility\(\);[\s\S]*syncAdminResponsiveState\(\{ force: true \}\);[\s\S]*\}/);
  assert.match(adminJs, /function canCurrentAdminViewActivityTime\(\) \{[\s\S]*return adminCanViewActivityTime;[\s\S]*\}/);
  assert.match(adminJs, /function showAuthShell\(message = "", kind = "info"\) \{[\s\S]*resetAdminAccessState\(\);[\s\S]*eventsRows = null;[\s\S]*formsRows = null;[\s\S]*reportsResultsPayload = null;[\s\S]*syncAdminResponsiveState\(\{ force: true \}\);[\s\S]*\}/);
  assert.match(adminJs, /function showAdminShell\(admin\) \{[\s\S]*setAdminAccessState\(admin\);[\s\S]*syncAdminResponsiveState\(\{ force: true \}\);[\s\S]*\}/);
  assert.match(adminJs, /async function handleUnauthorized\(message\) \{[\s\S]*showAuthShell\(message \|\| "Sua sessão expirou\. Faça login novamente\.", "error"\);[\s\S]*\}/);
  assert.match(adminJs, /async function logout\(\) \{[\s\S]*showAuthShell\("Sessão encerrada com sucesso\.", "success"\);[\s\S]*\}/);
  assert.match(adminJs, /async function bootstrapAdmin\(\) \{[\s\S]*if \(!session\.authenticated \|\| !session\.admin\) \{[\s\S]*showAuthShell\("", "info"\);[\s\S]*return;[\s\S]*\}[\s\S]*showAdminShell\(session\.admin\);[\s\S]*await refreshAllTables\(\);[\s\S]*syncAdminResponsiveState\(\{ force: true \}\);[\s\S]*\}/);
  assert.match(adminJs, /window\.addEventListener\("resize", handleAdminResponsiveViewportChange\);/);
  assert.match(adminJs, /window\.addEventListener\("orientationchange", \(\) => \{[\s\S]*scheduleAdminResponsiveSync\(\{ force: true \}\);[\s\S]*\}\);/);
  assert.match(adminJs, /syncAdminResponsiveDatasets\(snapshot\);[\s\S]*syncAdminShellResponsiveState\(snapshot\);/);
  assert.match(adminJs, /const canViewFormsTime = syncFormsTimeColumnVisibility\(\);[\s\S]*const canViewEventsTime = syncEventsPrimaryColumnLabel\(\);[\s\S]*if \(formsRows !== null\) \{[\s\S]*renderFormsTable\(formsRows, \{ canViewTime: canViewFormsTime \}\);[\s\S]*\}[\s\S]*if \(eventsRows !== null\) \{[\s\S]*renderEventsTable\(eventsRows, \{ canViewTime: canViewEventsTime \}\);[\s\S]*\}[\s\S]*if \(reportsResultsPayload !== null\) \{[\s\S]*renderReportsResults\(reportsResultsPayload\);[\s\S]*\}/);
  assert.match(adminJs, /function switchTab\(tab\) \{[\s\S]*targetTab\.classList\.add\("active"\);[\s\S]*syncAdminTabStrip\(\);[\s\S]*updateOperationalChrome\(\);/);
  assert.match(adminJs, /if \(typeof adminViewportMediaQuery\.addEventListener === "function"\) \{[\s\S]*adminViewportMediaQuery\.addEventListener\("change", handleViewportMediaQueryChange\);[\s\S]*\} else if \(typeof adminViewportMediaQuery\.addListener === "function"\) \{[\s\S]*adminViewportMediaQuery\.addListener\(handleViewportMediaQueryChange\);[\s\S]*\}/);
  assert.match(adminJs, /async function bootstrap\(\) \{[\s\S]*bindActions\(\);[\s\S]*syncAdminResponsiveState\(\{ force: true \}\);[\s\S]*\}/);
});

test('forms table assigns explicit widths to every visible column including Hora', () => {
  assert.match(adminHtml, /id="formsTable" class="responsive-table forms-table"/);
  assert.match(adminHtml, /id="refreshFormsButton"[\s\S]*id="clearFormsButton"/);
  assert.match(adminHtml, /<th data-forms-time-column-header>Hora<\/th>/);
  assert.match(adminCss, /\.forms-table th:nth-child\(5\),[\s\S]*\.forms-table td:nth-child\(5\) \{[\s\S]*width:\s*136px;/);
  assert.match(adminCss, /\.forms-table th:nth-child\(9\),[\s\S]*\.forms-table td:nth-child\(9\) \{[\s\S]*width:\s*88px;/);
  assert.match(adminCss, /\.forms-table--without-time \{[\s\S]*min-width:\s*892px;/);
  assert.match(adminCss, /\.forms-table--without-time th\[data-forms-time-column-header\],[\s\S]*\.forms-table--without-time td:nth-child\(9\) \{[\s\S]*display:\s*none;/);
});

test('forms table renders safe received-time fields separately from raw timestamps', () => {
  assert.match(adminJs, /let formsRows = null;/);
  assert.match(adminJs, /function makeEventDateTimeCellFromParts\(dateLabel, timeLabel, options = \{\}\) \{/);
  assert.match(adminJs, /function getFormsColumnCount\(includeTime = canCurrentAdminViewActivityTime\(\)\) \{/);
  assert.match(adminJs, /function syncFormsTimeColumnVisibility\(\) \{/);
  assert.match(adminJs, /function buildFormsMobileCard\(row, options = \{\}\) \{/);
  assert.match(adminJs, /function buildFormsRow\(row, options = \{\}\) \{/);
  assert.match(adminJs, /function renderFormsTable\(rows, options = \{\}\) \{/);
  assert.match(adminJs, /formsTable\.classList\.toggle\("forms-table--without-time", !canViewTime\);/);
  assert.match(adminJs, /formsTimeHeader\.hidden = !canViewTime;/);
  assert.match(adminJs, /const canViewTime = syncFormsTimeColumnVisibility\(\);/);
  assert.match(adminJs, /makeEventDateTimeCellFromParts\(row\.recebimento_date_label, row\.recebimento_time_label\)/);
  assert.match(adminJs, /const eventDateTimeHtml = makeEventDateTimeCellFromParts\(row\.data \?\? "-", canViewTime \? \(row\.hora \?\? ""\) : ""\);/);
  assert.match(adminJs, /const eventDateTimeLabel = canViewTime \? "Data e Hora" : "Data";/);
  assert.match(adminJs, /renderEmptyStateRow\("formsBody", getFormsColumnCount\(canViewTime\), "Nenhum evento do provider encontrado no historico sincronizado\."\);/);
  assert.match(adminJs, /formsRows = Array\.isArray\(rows\) \? rows : \[\];/);
  assert.match(adminJs, /renderFormsTable\(formsRows, \{ canViewTime \}\);/);
  assert.match(adminJs, /if \(canViewTime\) \{[\s\S]*cells\.push\(`<td>\$\{makeEventCell\(row\.hora \?\? "-"\)\}<\/td>`\);[\s\S]*\}/);
  assert.match(adminJs, /makeEventCell\(row\.hora \?\? "-"\)/);
  assert.match(adminCss, /\.admin-mobile-card \{[\s\S]*display:\s*grid;[\s\S]*padding:\s*16px;[\s\S]*border-radius:\s*16px;/);
  assert.match(adminCss, /\.forms-mobile-card-copy \{[\s\S]*white-space:\s*pre-wrap;[\s\S]*-webkit-line-clamp:\s*4;/);
  assert.match(adminCss, /\.admin-mobile-card-datetime \.event-cell,[\s\S]*\.admin-mobile-card-datetime \.event-datetime-cell \{[\s\S]*text-align:\s*left;[\s\S]*align-items:\s*flex-start;/);
});

test('forms tab wires the clear button to delete only the Forms records and refresh the table state', () => {
  assert.match(adminJs, /async function clearForms\(\) \{/);
  assert.match(adminJs, /window\.confirm\("Deseja remover todos os registros da tabela Forms\?"\)/);
  assert.match(adminJs, /deleteJson\("\/api\/admin\/forms"\)/);
  assert.match(adminJs, /const clearFormsButton = document\.getElementById\("clearFormsButton"\);/);
  assert.match(adminJs, /runFormsClear\(clearFormsButton\)/);
  assert.match(adminJs, /updateFormsClearButtonState\(\);/);
});