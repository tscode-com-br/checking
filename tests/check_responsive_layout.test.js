const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const checkCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/styles.css'),
  'utf8'
);
const checkAppScript = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/app.js'),
  'utf8'
);

test('main check shell uses dynamic viewport and measured header height to fit the device', () => {
  assert.match(
    checkCss,
    /:root\s*\{[\s\S]*--app-viewport-width:\s*100vw;[\s\S]*--app-viewport-height:\s*100vh;[\s\S]*--app-viewport-height:\s*100svh;[\s\S]*--app-viewport-height:\s*100dvh;[\s\S]*--app-header-height:/
  );
  assert.match(
    checkCss,
    /\.check-shell\s*\{[\s\S]*width:\s*100%;[\s\S]*min-height:\s*calc\(var\(--app-viewport-height\) - var\(--app-header-height\)\);[\s\S]*align-items:\s*stretch;/
  );
  assert.match(
    checkCss,
    /\.check-card\s*\{[\s\S]*margin:\s*0 auto;/
  );
});

test('main check card expands more on larger screens without losing mobile full-width behavior', () => {
  assert.match(
    checkCss,
    /:root\s*\{[\s\S]*--card-max-width:\s*680px;/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 640px\)\s*\{[\s\S]*\.check-card\s*\{[\s\S]*--card-max-width:\s*760px;/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 1024px\)\s*\{[\s\S]*\.check-card\s*\{[\s\S]*--card-max-width:\s*920px;/
  );
});

test('web app script synchronizes viewport css variables during mobile viewport changes', () => {
  assert.match(
    checkAppScript,
    /function syncViewportLayoutMetrics\(\)\s*\{[\s\S]*setProperty\('--app-viewport-width', `\$\{metrics\.viewportWidth\}px`\);[\s\S]*setProperty\('--app-viewport-height', `\$\{metrics\.viewportHeight\}px`\);[\s\S]*setProperty\('--app-header-height', `\$\{metrics\.headerHeight\}px`\);/
  );
  assert.match(
    checkAppScript,
    /window\.addEventListener\('resize', scheduleViewportLayoutMetricsSync\);/
  );
  assert.match(
    checkAppScript,
    /window\.addEventListener\('orientationchange', \(\) => \{[\s\S]*scheduleViewportLayoutMetricsSync\(\);[\s\S]*realignViewport\(\);[\s\S]*\}\);/
  );
  assert.match(
    checkAppScript,
    /window\.visualViewport\.addEventListener\('resize', scheduleViewportLayoutMetricsSync\);/
  );
});