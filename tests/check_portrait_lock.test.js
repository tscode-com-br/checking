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

test('check webapp includes a portrait-only orientation guard overlay', () => {
  assert.match(checkHtml, /id="orientationLockScreen"/);
  assert.match(checkHtml, /Use o aparelho em retrato/);
  assert.match(checkHtml, /Este webapp foi otimizado somente para visualização vertical/);
});

test('portrait-only orientation guard hides the app chrome while the landscape overlay is active', () => {
  assert.match(
    checkCss,
    /body\.portrait-lock-active\s*\{[\s\S]*overflow:\s*hidden;/
  );
  assert.match(
    checkCss,
    /body\.portrait-lock-active > header,[\s\S]*body\.portrait-lock-active > \.check-shell\s*\{[\s\S]*visibility:\s*hidden;[\s\S]*pointer-events:\s*none;/
  );
  assert.match(
    checkCss,
    /\.orientation-lock-screen\s*\{[\s\S]*position:\s*fixed;[\s\S]*inset:\s*0;[\s\S]*z-index:\s*40;/
  );
});

test('portrait-only orientation guard script attempts portrait lock and refreshes on viewport changes', () => {
  assert.match(checkAppScript, /function requestPortraitOrientationLock\(\)\s*\{[\s\S]*orientationApi\.lock\('portrait'\);/);
  assert.match(checkAppScript, /function syncPortraitLockState\(\)\s*\{[\s\S]*classList\.toggle\('portrait-lock-active', isLandscape\);/);
  assert.match(checkAppScript, /window\.addEventListener\('resize', syncPortraitLockState\);/);
  assert.match(checkAppScript, /window\.addEventListener\('orientationchange', \(\) => \{[\s\S]*syncPortraitLockState\(\);[\s\S]*realignViewport\(\);[\s\S]*\}\);/);
});