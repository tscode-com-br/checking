const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const adminHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/index.html'),
  'utf8'
);

test('admin uses the new official site icon asset', () => {
  assert.match(adminHtml, /rel="icon" type="image\/png" sizes="512x512" href="\/assets\/img\/new_icon_512\.png\?v=1"/);
  assert.match(adminHtml, /rel="shortcut icon" type="image\/png" href="\/assets\/img\/new_icon_512\.png\?v=1"/);
  assert.match(adminHtml, /rel="apple-touch-icon" href="\/assets\/img\/new_icon_512\.png\?v=1"/);
});