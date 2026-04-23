const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const adminJs = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/app.js'),
  'utf8'
);

test('admin locations allow zero tolerance in the UI', () => {
  assert.match(adminJs, /function normalizeTolerance\(value\) \{[\s\S]*tolerance < 0 \|\| tolerance > 9999[\s\S]*inteiro entre 0 e 9999 metros\./);
  assert.match(adminJs, /class="inline location-tolerance" type="number" min="0" max="9999" inputmode="numeric"/);
});