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

test('check controller highlights the history item that matches the latest recorded activity', () => {
  assert.match(
    checkAppScript,
    /const lastCheckinItem = lastCheckinValue \? lastCheckinValue\.closest\('\.history-item'\) : null;/
  );
  assert.match(
    checkAppScript,
    /const lastCheckoutItem = lastCheckoutValue \? lastCheckoutValue\.closest\('\.history-item'\) : null;/
  );
  assert.match(
    checkAppScript,
    /function resolveLatestHistoryAction\(state\) \{[\s\S]*return lastCheckinAt >= lastCheckoutAt \? 'checkin' : 'checkout';[\s\S]*if \(lastCheckinAt\) \{[\s\S]*return 'checkin';[\s\S]*if \(lastCheckoutAt\) \{[\s\S]*return 'checkout';[\s\S]*return null;[\s\S]*\}/
  );
  assert.match(
    checkAppScript,
    /function syncLatestHistoryHighlight\(state\) \{[\s\S]*lastCheckinItem\.classList\.toggle\('is-latest-activity', latestAction === 'checkin'\);[\s\S]*lastCheckoutItem\.classList\.toggle\('is-latest-activity', latestAction === 'checkout'\);[\s\S]*\}/
  );
  assert.match(
    checkAppScript,
    /function applyHistoryState\(state\) \{[\s\S]*renderHistoryValue\(lastCheckinValue, state && state\.last_checkin_at\);[\s\S]*renderHistoryValue\(lastCheckoutValue, state && state\.last_checkout_at\);[\s\S]*syncLatestHistoryHighlight\(state\);[\s\S]*applySuggestedActionFromHistory\(state\);[\s\S]*\}/
  );
});

test('check history card styles the latest activity with a rounded green frame', () => {
  assert.match(
    checkCss,
    /\.history-item\s*\{[\s\S]*padding:\s*clamp\(6px, 1\.1vw, 8px\);[\s\S]*border:\s*1px solid transparent;[\s\S]*border-radius:\s*calc\(var\(--control-radius\) \+ 1px\);/
  );
  assert.match(
    checkCss,
    /\.history-item\.is-latest-activity\s*\{[\s\S]*border-color:\s*rgba\(22, 163, 74, 0\.42\);[\s\S]*background:\s*rgba\(220, 252, 231, 0\.76\);/
  );
});