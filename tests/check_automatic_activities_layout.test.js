const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const checkHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/index.html'),
  'utf8'
);
const checkCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/styles.css'),
  'utf8'
);
const checkAppScript = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/app.js'),
  'utf8'
);

test('automatic activities toggle appears above Registro in the legend row', () => {
  assert.match(
    checkHtml,
    /<legend class="check-group-legend-row">[\s\S]*<label id="automaticActivitiesField" class="legend-toggle" for="automaticActivitiesToggle">[\s\S]*<span class="legend-toggle-label">Atividades Automáticas<\/span>[\s\S]*<input id="automaticActivitiesToggle" type="checkbox" \/>[\s\S]*<\/label>[\s\S]*<span>Registro<\/span>[\s\S]*<\/legend>/
  );
  assert.match(
    checkCss,
    /\.check-group-legend-row\s*\{[\s\S]*flex-direction:\s*column;[\s\S]*align-items:\s*flex-start;/
  );
});

test('automatic activities toggle is hidden and cleared when GPS permission is unavailable', () => {
  assert.match(
    checkAppScript,
    /const automaticActivitiesField = document\.getElementById\('automaticActivitiesField'\);/
  );
  assert.match(
    checkAppScript,
    /function canShowAutomaticActivitiesField\(\)\s*\{[\s\S]*return gpsLocationPermissionGranted \|\| readStorageFlag\(locationPermissionGrantedKey\);[\s\S]*\}/
  );
  assert.match(
    checkAppScript,
    /function syncAutomaticActivitiesAvailability\(\)\s*\{[\s\S]*automaticActivitiesField\.classList\.toggle\('is-hidden', !showAutomaticActivitiesField\);[\s\S]*automaticActivitiesField\.setAttribute\('aria-hidden', String\(!showAutomaticActivitiesField\)\);[\s\S]*if \(!showAutomaticActivitiesField && automaticActivitiesToggle\) \{[\s\S]*automaticActivitiesToggle\.checked = false;[\s\S]*\}[\s\S]*\}/
  );
  assert.match(
    checkAppScript,
    /function restorePersistedUserSettingsForChave\(chave\) \{[\s\S]*applyPersistedUserSettings\(chave\);[\s\S]*syncAutomaticActivitiesAvailability\(\);[\s\S]*syncProjectVisibility\(\);[\s\S]*\}/
  );
  assert.match(
    checkAppScript,
    /function setGpsLocationPermissionGranted\(value\) \{[\s\S]*syncAutomaticActivitiesAvailability\(\);[\s\S]*syncProjectVisibility\(\);[\s\S]*syncManualLocationControl\(\);[\s\S]*\}/
  );
});