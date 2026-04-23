const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const checkHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/index.html'),
  'utf8'
);

const checkScript = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/app.js'),
  'utf8'
);

test('check page keeps Projeto, Local and Informe controls addressable for toggle-driven visibility', () => {
  assert.match(checkHtml, /id="automaticActivitiesToggle"/);
  assert.match(checkHtml, /id="projectField"/);
  assert.match(checkHtml, /id="locationSelectField"/);
  assert.match(checkHtml, /id="informeField"/);
  assert.match(checkHtml, /id="submitButton"[\s\S]*>Registrar</);
});

test('check controller hides manual controls during automatic mode and reruns lifecycle updates when GPS is available', () => {
  assert.match(checkScript, /if \(actionInputs\.includes\(control\)\) \{[\s\S]*automaticActivitiesEnabled/);
  assert.match(checkScript, /control === submitButton[\s\S]*automaticActivitiesEnabled/);
  assert.match(checkScript, /const hideProjectField = isAutomaticActivitiesEnabled\(\);/);
  assert.match(checkScript, /const hideLocationField = isAutomaticActivitiesEnabled\(\) \|\| gpsLocationPermissionGranted;/);
  assert.match(checkScript, /setGpsLocationPermissionGranted\(value\) \{[\s\S]*syncProjectVisibility\(\);/);
  assert.match(checkScript, /if \(gpsLocationPermissionGranted && isApplicationUnlocked\(\)\) \{[\s\S]*runLifecycleUpdateSequence\(\{ ignoreCooldown: true \}\);/);
  assert.match(checkScript, /if \(isAutomaticActivitiesEnabled\(\)\) \{[\s\S]*Desative Atividades Automáticas para registrar manualmente\./);
});