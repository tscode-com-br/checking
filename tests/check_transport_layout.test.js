const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const checkCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/styles.css'),
  'utf8'
);

test('transport scheduling screen card fills the available viewport height within the dialog padding', () => {
  assert.match(
    checkCss,
    /\.transport-screen\s*\{[\s\S]*--transport-screen-card-height:\s*calc\(var\(--app-viewport-height\) - \(2 \* var\(--page-padding-block\)\)\);/
  );
  assert.match(
    checkCss,
    /\.transport-screen-card\s*\{[\s\S]*min-height:\s*var\(--transport-screen-card-height\);[\s\S]*height:\s*var\(--transport-screen-card-height\);[\s\S]*max-height:\s*var\(--transport-screen-card-height\);/
  );
});

test('transport request history grows into the remaining transport screen space', () => {
  assert.match(
    checkCss,
    /\.transport-request-history-section\s*\{[\s\S]*display:\s*flex;[\s\S]*flex:\s*1 1 auto;[\s\S]*min-height:\s*0;/
  );
  assert.match(
    checkCss,
    /\.transport-request-history-list\s*\{[\s\S]*flex:\s*1 1 auto;[\s\S]*min-height:\s*0;[\s\S]*max-height:\s*none;/
  );
});