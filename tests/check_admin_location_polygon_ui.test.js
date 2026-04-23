const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const adminHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/index.html'),
  'utf8'
);

const adminJs = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/app.js'),
  'utf8'
);

const adminCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin/styles.css'),
  'utf8'
);

test('locations section explains polygon semantics and implicit closure', () => {
  assert.match(adminHtml, /Cada localização forma um polígono fechado\.[\s\S]*último vértice de volta ao V1\./);
  assert.match(adminJs, /function formatLocationCoordinateCount\(count\) \{[\s\S]*1 vértice[\s\S]*`\$\{count\} vértices`/);
  assert.match(adminJs, /function getLocationCoordinateClosureCopy\(row\) \{[\s\S]*Fechamento implícito: V\$\{filledCount\} conecta de volta ao V1\./);
  assert.match(adminJs, /class="location-coordinate-summary-closure">fecha em V1<\/span>/);
});

test('locations rows support safe vertex reordering and blank guards', () => {
  assert.match(adminJs, /data-location-coordinate-move="\$\{row\.id\}"[\s\S]*data-direction="up"[\s\S]*>Subir<\/button>/);
  assert.match(adminJs, /data-location-coordinate-move="\$\{row\.id\}"[\s\S]*data-direction="down"[\s\S]*>Descer<\/button>/);
  assert.match(adminJs, /function moveLocationCoordinate\(rowId, coordinateId, direction\) \{/);
  assert.match(adminJs, /Preencha ou remova o vértice em branco antes de adicionar outro\./);
  assert.match(adminJs, /Preencha os vértices em sequência, sem deixar linhas em branco entre V1 e o último vértice\./);
  assert.match(adminJs, /Preencha ou remova os vértices em branco antes de salvar o polígono\./);
  assert.match(adminJs, /Mantenha ao menos 3 vértices preenchidos no polígono\. Adicione outro vértice antes de remover este\./);
  assert.match(adminCss, /\.location-coordinate-actions \{[\s\S]*flex-wrap: wrap;/);
  assert.match(adminCss, /\.location-coordinate-note \{/);
});

test('locations save messaging explains polygon geometry failures', () => {
  assert.match(adminJs, /Não repita o V1 no final; o polígono fecha automaticamente ligando o último vértice de volta ao primeiro\./);
  assert.match(adminJs, /Os vértices informados se cruzam\. Reordene a sequência para contornar a área sem auto-interseção\./);
  assert.match(adminJs, /Os vértices informados não formam uma área válida\. Revise pontos repetidos, colineares ou muito próximos\./);
  assert.match(adminJs, /Informe ao menos 3 vértices distintos e preenchidos em ordem para formar a área poligonal do local\./);
});