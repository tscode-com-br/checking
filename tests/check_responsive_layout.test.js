const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const checkCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/styles.css'),
  'utf8'
);
const checkHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/index.html'),
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
    /@media \(min-width: 1024px\)\s*\{[\s\S]*\.check-card\s*\{[\s\S]*--card-max-width:\s*1040px;/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 1180px\)\s*\{[\s\S]*\.check-card\s*\{[\s\S]*--card-max-width:\s*1160px;/
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

test('low-height landscape layout reorganizes the main form without reintroducing scroll blockers', () => {
  assert.match(checkHtml, /<fieldset id="registrationField" class="check-group">/);
  assert.match(
    checkCss,
    /@media \(orientation: landscape\) and \(max-height: 540px\)\s*\{[\s\S]*\.check-card\s*\{[\s\S]*width:\s*min\(100%, 960px\);[\s\S]*align-self:\s*start;[\s\S]*\}[\s\S]*\.check-form\s*\{[\s\S]*grid-template-columns:\s*minmax\(220px, 0\.92fr\) minmax\(0, 1\.08fr\);[\s\S]*grid-template-areas:[\s\S]*"history auth"[\s\S]*"location submit";[\s\S]*align-items:\s*start;/
  );
  assert.match(
    checkCss,
    /@media \(orientation: landscape\) and \(max-height: 540px\)\s*\{[\s\S]*\.check-form > \*\s*\{[\s\S]*min-width:\s*0;[\s\S]*\}[\s\S]*\.check-form > #registrationField\s*\{[\s\S]*grid-area:\s*registration;/
  );
  assert.match(
    checkCss,
    /@media \(orientation: landscape\) and \(max-height: 540px\)\s*\{[\s\S]*\.password-dialog,[\s\S]*\.transport-screen\s*\{[\s\S]*align-items:\s*flex-start;[\s\S]*padding-top:\s*max\(10px, env\(safe-area-inset-top\)\);/
  );
});

test('desktop layout keeps the shell contained while reorganizing form and transport surfaces', () => {
  assert.match(
    checkCss,
    /@media \(min-width: 1024px\)\s*\{[\s\S]*\.transport-screen-card\s*\{[\s\S]*width:\s*min\(100%, 900px\);[\s\S]*min-height:\s*auto;[\s\S]*height:\s*auto;[\s\S]*gap:\s*14px;[\s\S]*\}[\s\S]*\.transport-option-buttons\s*\{[\s\S]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\);/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 1180px\)\s*\{[\s\S]*\.check-form\s*\{[\s\S]*grid-template-columns:\s*minmax\(300px, 0\.88fr\) minmax\(0, 1\.12fr\);[\s\S]*grid-template-areas:[\s\S]*"history auth"[\s\S]*"location submit";[\s\S]*align-items:\s*start;/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 1180px\)\s*\{[\s\S]*\.check-field-compact\s*\{[\s\S]*flex:\s*0 0 148px;[\s\S]*width:\s*148px;[\s\S]*min-width:\s*148px;/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 1180px\)\s*\{[\s\S]*\.transport-request-history-list\s*\{[\s\S]*grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\);[\s\S]*align-content:\s*start;/
  );
});