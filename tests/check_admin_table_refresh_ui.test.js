const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const adminHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin2/index.html'),
  'utf8'
);

const adminJs = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin2/app.js'),
  'utf8'
);

test('manual refresh buttons exist for the heavy admin tables and the missing-checkout table is removed', () => {
  assert.match(adminHtml, /id="refreshAdministratorsButton"/);
  assert.match(adminHtml, /id="refreshEndpointsButton"/);
  assert.match(adminHtml, /id="refreshUsersButton"/);
  assert.match(adminHtml, /id="refreshEventsButton"/);
  assert.match(adminHtml, /id="refreshInactiveButton"/);
  assert.doesNotMatch(adminHtml, /id="missingCheckoutBody"/);
  assert.doesNotMatch(adminHtml, /Usuários com Check-in e sem Check-Out/);
});

test('automatic refresh excludes the heavy tables and manual buttons reload them explicitly', () => {
  assert.match(adminJs, /async function refreshAutomaticTables\(\) \{[\s\S]*if \(isAdminTabAllowed\("checkin"\)\) \{[\s\S]*jobs\.push\(loadCheckin\(\{ silent: true \}\)\);[\s\S]*if \(isAdminTabAllowed\("checkout"\)\) \{[\s\S]*jobs\.push\(loadCheckout\(\{ silent: true \}\)\);[\s\S]*\}/);
  assert.match(adminJs, /startAutoRefresh\(\) \{[\s\S]*refreshAutomaticTables\(\)\.catch/);
  assert.match(adminJs, /requestRefreshAllTables\(\) \{[\s\S]*refreshAutomaticTables\(\)\.catch/);
  assert.doesNotMatch(adminJs, /fetchJson\("\/api\/admin\/missing-checkout"\)/);
  assert.match(adminJs, /function bindPresenceScrollInteractionGuards\(\) \{[\s\S]*window\.addEventListener\("wheel", markPresenceScrollInteraction, \{ passive: true \}\);[\s\S]*window\.addEventListener\("touchstart", markPresenceScrollInteraction, \{ passive: true \}\);[\s\S]*window\.addEventListener\("touchmove", markPresenceScrollInteraction, \{ passive: true \}\);[\s\S]*window\.addEventListener\("keydown", handlePresenceScrollKeyInteraction\);[\s\S]*\}/);
  assert.match(adminJs, /function capturePresencePageScroll\(\) \{[\s\S]*\["checkin", "checkout"\]\.includes\(activeTab\)[\s\S]*x:\s*window\.scrollX,[\s\S]*y:\s*window\.scrollY,[\s\S]*interactionRevision:\s*presenceScrollInteractionRevision,[\s\S]*\}/);
  assert.match(adminJs, /function restorePresencePageScroll\(snapshot\) \{[\s\S]*snapshot\.interactionRevision !== presenceScrollInteractionRevision[\s\S]*const applySnapshot = \(\) => \{[\s\S]*snapshot\.interactionRevision !== presenceScrollInteractionRevision[\s\S]*window\.scrollTo\(snapshot\.x, snapshot\.y\);[\s\S]*\};[\s\S]*window\.requestAnimationFrame\(\(\) => \{[\s\S]*snapshot\.interactionRevision !== presenceScrollInteractionRevision[\s\S]*applySnapshot\(\);[\s\S]*window\.requestAnimationFrame\(\(\) => \{[\s\S]*snapshot\.interactionRevision !== presenceScrollInteractionRevision[\s\S]*applySnapshot\(\);[\s\S]*\}\);[\s\S]*\}\);[\s\S]*\}/);
  assert.match(adminJs, /async function refreshAutomaticTables\(\) \{[\s\S]*const scrollSnapshot = capturePresencePageScroll\(\);[\s\S]*jobs\.push\(loadCheckin\(\{ silent: true \}\)\);[\s\S]*jobs\.push\(loadCheckout\(\{ silent: true \}\)\);[\s\S]*await Promise\.all\(jobs\);[\s\S]*restorePresencePageScroll\(scrollSnapshot\);[\s\S]*markDashboardRefreshed\(\);[\s\S]*\}/);
  assert.match(adminJs, /async function refreshAutomaticTables\(\) \{[\s\S]*Background refresh keeps the administrator grid stable\.[\s\S]*await loadProjects\(\);[\s\S]*jobs\.push\(loadPending\(\{ silent: true \}\)\);[\s\S]*jobs\.push\(loadLocations\(\{ silent: true \}\)\);[\s\S]*\}/);
  assert.doesNotMatch(adminJs, /async function refreshAutomaticTables\(\) \{[\s\S]*jobs\.push\(loadAdministrators\(\)\);[\s\S]*\}/);
  assert.match(adminJs, /async function loadAdministratorsWithProjectCatalog\(\) \{[\s\S]*await loadProjects\(\);[\s\S]*await loadAdministrators\(\);[\s\S]*\}/);
  assert.match(adminJs, /if \(isAdminTabAllowed\("cadastro"\) && !hasPendingEditInProgress\(\)\) \{[\s\S]*await loadProjects\(\);[\s\S]*jobs\.push\(loadAdministrators\(\)\);/);
  assert.match(adminJs, /if \(activeTab === "cadastro"\) \{[\s\S]*await loadProjects\(\);[\s\S]*await Promise\.all\(\[loadAdministrators\(\), loadPending\(\), loadUserPending\(\), loadLocations\(\), loadEndpoints\(\)\]\);/);
  assert.match(adminJs, /async function runManualRefresh\(button, loader\) \{[\s\S]*button\.textContent = "Atualizando\.\.\.";[\s\S]*button\.textContent = idleLabel;/);
  assert.match(adminJs, /button\.classList\.add\("is-loading"\);/);
  assert.match(adminJs, /button\.setAttribute\("aria-busy", "true"\);/);
  assert.match(adminJs, /bindManualRefreshButton\(refreshInactiveButton, loadInactive\);/);
  assert.match(adminJs, /bindManualRefreshButton\(refreshAdministratorsButton, loadAdministratorsWithProjectCatalog\);/);
  assert.match(adminJs, /bindManualRefreshButton\(refreshEndpointsButton, loadEndpoints\);/);
  assert.match(adminJs, /bindManualRefreshButton\(refreshUsersButton, loadRegisteredUsers\);/);
  assert.match(adminJs, /bindManualRefreshButton\(refreshEventsButton, loadDatabaseEvents\);/);
  assert.match(adminJs, /function bindActions\(\) \{[\s\S]*bindPresenceScrollInteractionGuards\(\);[\s\S]*setupCadastroSectionPanels\(\);/);
  assert.match(adminJs, /if \(activeTab === "inactive"\) \{\s*return;/);
});