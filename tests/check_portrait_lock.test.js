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

test('check webapp no longer renders a portrait-only orientation guard overlay', () => {
  assert.doesNotMatch(checkHtml, /id="orientationLockScreen"/);
  assert.doesNotMatch(checkHtml, /Use o aparelho em retrato/);
  assert.doesNotMatch(checkHtml, /Este webapp foi otimizado somente para visualização vertical/);
});

test('check webapp no longer hides the chrome behind portrait-only landscape classes', () => {
  assert.doesNotMatch(checkCss, /body\.portrait-lock-active/);
  assert.doesNotMatch(checkCss, /\.orientation-lock-screen/);
  assert.doesNotMatch(checkCss, /\.orientation-lock-card/);
});

test('check webapp stops forcing portrait orientation but keeps viewport metric sync on viewport changes', () => {
  assert.doesNotMatch(checkAppScript, /function requestPortraitOrientationLock\(/);
  assert.doesNotMatch(checkAppScript, /function syncPortraitLockState\(/);
  assert.doesNotMatch(checkAppScript, /window\.addEventListener\('resize', syncPortraitLockState\);/);
  assert.match(checkAppScript, /window\.addEventListener\('resize', scheduleViewportLayoutMetricsSync\);/);
  assert.match(checkAppScript, /window\.addEventListener\('orientationchange', \(\) => \{[\s\S]*scheduleViewportLayoutMetricsSync\(\);[\s\S]*realignViewport\(\);[\s\S]*\}\);/);
  assert.match(checkAppScript, /window\.visualViewport\.addEventListener\('resize', scheduleViewportLayoutMetricsSync\);/);
});