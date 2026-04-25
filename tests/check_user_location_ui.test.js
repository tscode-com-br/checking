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
  assert.match(checkScript, /if \(gpsLocationPermissionGranted && isApplicationUnlocked\(\)\) \{[\s\S]*runLifecycleUpdateSequence\(\{[\s\S]*ignoreCooldown: true,[\s\S]*triggerSource: 'automatic_activities_disable',[\s\S]*\}\);/);
  assert.match(checkScript, /if \(isAutomaticActivitiesEnabled\(\)\) \{[\s\S]*Desative Atividades Automáticas para registrar manualmente\./);
});

test('check controller exposes opt-in local measurement support for baseline GPS sessions', () => {
  assert.match(checkScript, /const locationMeasurementStorageKey = 'checking\.web\.location\.measurement\.enabled';/);
  assert.match(checkScript, /window\.CheckingWebLocationMeasurement = Object\.freeze\(\{[\s\S]*enable\(\)[\s\S]*getSessions\(\)[\s\S]*getLatestSession\(\)[\s\S]*summarize\(\)[\s\S]*summarizeByTrigger\(\)[\s\S]*buildReport\(metadata\)[\s\S]*printReport\(metadata\)/);
  assert.match(checkScript, /measurementTrigger: 'manual_refresh'/);
  assert.match(checkScript, /measurementTrigger: 'automatic_activities_enable'/);
});

test('check controller enforces a 3s to 7s watch window for all current GPS acquisition triggers', () => {
  assert.match(checkScript, /const enforcedLocationCapturePlan = Object\.freeze\(\{[\s\S]*minimumWindowMs: 3000,[\s\S]*maxWindowMs: 7000,[\s\S]*\}\);/);
  assert.match(checkScript, /const locationCapturePlansByTrigger = Object\.freeze\(\{[\s\S]*startup:[\s\S]*submit_guard:[\s\S]*manual_refresh:[\s\S]*automatic_activities_enable:[\s\S]*automatic_activities_disable:[\s\S]*visibility:[\s\S]*focus:[\s\S]*pageshow:/);
  assert.match(checkScript, /function buildLocationCapturePlan\(options\) \{[\s\S]*strategy: 'single_attempt'/);
  assert.match(checkScript, /function requestCurrentPositionForPlan\(capturePlan, measurementSession\) \{[\s\S]*capturePlan\.strategy !== 'watch_window'[\s\S]*navigator\.geolocation\.watchPosition/);
  assert.match(checkScript, /function shouldStopLocationWatch\(bestPosition, capturePlan, startedAtMs\) \{[\s\S]*Date\.now\(\) - startedAtMs < capturePlan\.minimumWindowMs/);
  assert.match(checkScript, /const locationPayload = await updateLocationForLifecycleSequence\(settings\);/);
});