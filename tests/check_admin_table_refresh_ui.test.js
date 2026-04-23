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
  assert.match(adminJs, /async function refreshAutomaticTables\(\) \{[\s\S]*loadCheckin\(\), loadCheckout\(\)[\s\S]*\}/);
  assert.match(adminJs, /startAutoRefresh\(\) \{[\s\S]*refreshAutomaticTables\(\)\.catch/);
  assert.match(adminJs, /requestRefreshAllTables\(\) \{[\s\S]*refreshAutomaticTables\(\)\.catch/);
  assert.doesNotMatch(adminJs, /fetchJson\("\/api\/admin\/missing-checkout"\)/);
  assert.match(adminJs, /refreshFormsButton\.addEventListener\("click", \(\) => \{[\s\S]*refreshManualTable\(loadForms\)/);
  assert.match(adminJs, /refreshInactiveButton\.addEventListener\("click", \(\) => \{[\s\S]*refreshManualTable\(loadInactive\)/);
  assert.match(adminJs, /refreshAdministratorsButton\.addEventListener\("click", \(\) => \{[\s\S]*refreshManualTable\(loadAdministrators\)/);
  assert.match(adminJs, /refreshUsersButton\.addEventListener\("click", \(\) => \{[\s\S]*refreshManualTable\(loadRegisteredUsers\)/);
  assert.match(adminJs, /refreshEventsButton\.addEventListener\("click", \(\) => \{[\s\S]*refreshManualTable\(loadEvents\)/);
  assert.match(adminJs, /if \(activeTab === "forms"\) \{\s*return;/);
  assert.match(adminJs, /if \(activeTab === "inactive"\) \{\s*return;/);
});