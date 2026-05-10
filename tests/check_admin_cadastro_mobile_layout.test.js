const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const adminHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/index.html'),
  'utf8'
);

const adminCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/styles.css'),
  'utf8'
);

test('cadastro tab groups each maintenance surface into explicit subsection panels', () => {
  assert.match(adminHtml, /<section id="tab-cadastro" class="tab cadastro-tab">/);
  assert.match(adminHtml, /data-cadastro-section="pendencias"/);
  assert.match(adminHtml, /data-cadastro-section="localizacoes"/);
  assert.match(adminHtml, /data-cadastro-section="checkout-distance"/);
  assert.match(adminHtml, /data-cadastro-section="administradores"/);
  assert.match(adminHtml, /data-cadastro-section="projetos"/);
  assert.match(adminHtml, /data-cadastro-section="usuarios"/);
});

test('cadastro locations settings include a mixed-zone interval input before the accuracy threshold control', () => {
  assert.match(adminHtml, /<div class="locations-settings-panel">[\s\S]*<label for="mixedZoneIntervalMinutes">Intervalo de Tempo para Zona Mista:<\/label>[\s\S]*<input id="mixedZoneIntervalMinutes" type="number" min="1" inputmode="numeric" value="20" \/>[\s\S]*<span>minutos<\/span>[\s\S]*<label for="locationAccuracyThresholdMeters">Erro máximo para considerar a coordenada do usuário:<\/label>/);
});

test('cadastro mobile layout replaces the generic compressed table stack with padded section cards', () => {
  assert.match(adminCss, /\.cadastro-tab \{[\s\S]*gap: 18px;/);
  assert.match(adminCss, /\.cadastro-tab\.active \{[\s\S]*display: grid;/);
  assert.match(adminCss, /\.cadastro-section-panel \{[\s\S]*display: grid;[\s\S]*gap: 14px;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-section-panel \{[\s\S]*padding: 14px;[\s\S]*border-radius: 16px;[\s\S]*background: linear-gradient\(180deg, #ffffff 0%, #f8fafc 100%\);/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-section-panel \.project-editor-panel \{[\s\S]*padding: 0;[\s\S]*border: 0;[\s\S]*background: transparent;[\s\S]*box-shadow: none;/);
});

test('cadastro mobile tables show labels above content and expand maintenance actions to full width', () => {
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-table td \{[\s\S]*display: grid;[\s\S]*gap: 6px;[\s\S]*padding: 12px;[\s\S]*text-align: left;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-table td::before \{[\s\S]*position: static;[\s\S]*display: block;[\s\S]*text-transform: uppercase;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-table \.pending-actions \{[\s\S]*display: grid;[\s\S]*grid-template-columns: 1fr;[\s\S]*width: 100%;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-table \.pending-actions button,[\s\S]*\.cadastro-users-table \.user-actions button,[\s\S]*\.location-actions button,[\s\S]*\.project-editor-actions button,[\s\S]*\.locations-settings-actions button \{[\s\S]*width: 100%;[\s\S]*min-height: 44px;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-users-table \.user-actions \{[\s\S]*grid-template-columns: 1fr;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.membership-projects-button \{[\s\S]*width: 100%;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.membership-projects-panel \{[\s\S]*max-height: none;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.membership-projects-panel-footer \{[\s\S]*display: grid;[\s\S]*grid-template-columns: 1fr;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.membership-projects-panel-footer button \{[\s\S]*width: 100%;[\s\S]*min-height: 44px;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.admin-projects-panel \{[\s\S]*grid-template-columns: 1fr;[\s\S]*max-height: none;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.location-projects-panel \{[\s\S]*max-height: none;/);
});