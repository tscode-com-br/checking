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

test('manual refresh buttons exist for the heavy admin tables and the missing-checkout table is removed', () => {
  assert.match(adminHtml, /id="refreshAdministratorsButton"/);
  assert.match(adminHtml, /id="refreshUsersButton"/);
  assert.match(adminHtml, /id="refreshEventsButton"/);
  assert.match(adminHtml, /id="refreshInactiveButton"/);
  assert.match(adminHtml, /id="refreshFormsButton"/);
  assert.doesNotMatch(adminHtml, /id="missingCheckoutBody"/);
  assert.doesNotMatch(adminHtml, /Usuários com Check-in e sem Check-Out/);
});

test('automatic refresh excludes the heavy tables and manual buttons reload them explicitly', () => {
  assert.match(adminJs, /async function refreshAutomaticTables\(\) \{[\s\S]*if \(isAdminTabAllowed\("checkin"\)\) \{[\s\S]*jobs\.push\(loadCheckin\(\)\);[\s\S]*if \(isAdminTabAllowed\("checkout"\)\) \{[\s\S]*jobs\.push\(loadCheckout\(\)\);[\s\S]*\}/);
  assert.match(adminJs, /startAutoRefresh\(\) \{[\s\S]*refreshAutomaticTables\(\)\.catch/);
  assert.match(adminJs, /requestRefreshAllTables\(\) \{[\s\S]*refreshAutomaticTables\(\)\.catch/);
  assert.doesNotMatch(adminJs, /fetchJson\("\/api\/admin\/missing-checkout"\)/);
  assert.match(adminJs, /if \(isAdminTabAllowed\("cadastro"\) && !hasPendingEditInProgress\(\)\) \{/);
  assert.match(adminJs, /async function runManualRefresh\(button, loader\) \{[\s\S]*button\.textContent = "Atualizando\.\.\.";[\s\S]*button\.textContent = idleLabel;/);
  assert.match(adminJs, /button\.classList\.add\("is-loading"\);/);
  assert.match(adminJs, /button\.setAttribute\("aria-busy", "true"\);/);
  assert.match(adminJs, /bindManualRefreshButton\(refreshFormsButton, loadForms\);/);
  assert.match(adminJs, /bindManualRefreshButton\(refreshInactiveButton, loadInactive\);/);
  assert.match(adminJs, /bindManualRefreshButton\(refreshAdministratorsButton, loadAdministrators\);/);
  assert.match(adminJs, /bindManualRefreshButton\(refreshUsersButton, loadRegisteredUsers\);/);
  assert.match(adminJs, /bindManualRefreshButton\(refreshEventsButton, loadEvents\);/);
  assert.match(adminJs, /if \(activeTab === "forms"\) \{\s*return;/);
  assert.match(adminJs, /if \(activeTab === "inactive"\) \{\s*return;/);
});