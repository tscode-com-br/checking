const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const transportPage = require('../sistema/app/static/transport/app.js');

test('formatTransportDate matches the requested English long-date pattern', () => {
  const formatted = transportPage.formatTransportDate(new Date(2026, 3, 17));
  assert.equal(formatted, 'Friday, April 17th, 2026');
});

test('getOrdinalSuffix handles English ordinal edge cases', () => {
  assert.equal(transportPage.getOrdinalSuffix(1), 'st');
  assert.equal(transportPage.getOrdinalSuffix(2), 'nd');
  assert.equal(transportPage.getOrdinalSuffix(3), 'rd');
  assert.equal(transportPage.getOrdinalSuffix(4), 'th');
  assert.equal(transportPage.getOrdinalSuffix(11), 'th');
  assert.equal(transportPage.getOrdinalSuffix(12), 'th');
  assert.equal(transportPage.getOrdinalSuffix(13), 'th');
  assert.equal(transportPage.getOrdinalSuffix(21), 'st');
  assert.equal(transportPage.getOrdinalSuffix(22), 'nd');
  assert.equal(transportPage.getOrdinalSuffix(23), 'rd');
});

test('getTransportDateState classifies past, current, and future dates', () => {
  const today = new Date(2026, 3, 17);

  assert.equal(transportPage.getTransportDateState(new Date(2026, 3, 16), today), 'past');
  assert.equal(transportPage.getTransportDateState(new Date(2026, 3, 17), today), 'today');
  assert.equal(transportPage.getTransportDateState(new Date(2026, 3, 18), today), 'future');
});

test('createTransportDateStore shares one selected date across subscribers', () => {
  const dateStore = transportPage.createTransportDateStore(new Date(2026, 3, 17));
  const firstSubscriberDates = [];
  const secondSubscriberDates = [];

  dateStore.subscribe((dateValue) => {
    firstSubscriberDates.push(transportPage.formatTransportDate(dateValue));
  });
  dateStore.subscribe((dateValue) => {
    secondSubscriberDates.push(transportPage.formatTransportDate(dateValue));
  });

  dateStore.shiftValue(-1);
  dateStore.setValue(new Date(2026, 3, 19));

  assert.deepEqual(firstSubscriberDates, [
    'Friday, April 17th, 2026',
    'Thursday, April 16th, 2026',
    'Sunday, April 19th, 2026',
  ]);
  assert.deepEqual(secondSubscriberDates, firstSubscriberDates);
});

test('resolveStoredTransportDate always falls back to the current reference date on reload', () => {
  const originalLocalStorage = global.localStorage;
  global.localStorage = {
    getItem(key) {
      return key === 'checking.transport.dashboard.selectedDate' ? '2026-04-19' : null;
    },
    setItem() {},
  };

  try {
    const restoredDate = transportPage.resolveStoredTransportDate(new Date(2026, 3, 17));
    assert.equal(transportPage.formatIsoDate(restoredDate), '2026-04-17');
  } finally {
    global.localStorage = originalLocalStorage;
  }
});

test('resolveStoredTransportDate falls back to the reference date for invalid storage values', () => {
  const originalLocalStorage = global.localStorage;
  global.localStorage = {
    getItem() {
      return '2026-99-99';
    },
    setItem() {},
  };

  try {
    const restoredDate = transportPage.resolveStoredTransportDate(new Date(2026, 3, 17));
    assert.equal(transportPage.formatIsoDate(restoredDate), '2026-04-17');
  } finally {
    global.localStorage = originalLocalStorage;
  }
});

test('setStoredTransportDate clears the persisted dashboard date so reload starts from today', () => {
  const originalLocalStorage = global.localStorage;
  const writes = [];
  global.localStorage = {
    getItem() {
      return null;
    },
    removeItem(key) {
      writes.push(key);
    },
  };

  try {
    transportPage.setStoredTransportDate(new Date(2026, 3, 20));
    assert.deepEqual(writes, ['checking.transport.dashboard.selectedDate']);
  } finally {
    global.localStorage = originalLocalStorage;
  }
});

test('resolvePanelSizes clamps resize positions to the configured limits', () => {
  assert.deepEqual(
    transportPage.resolvePanelSizes({
      containerSize: 805,
      dividerSize: 5,
      pointerOffset: 40,
      minFirstSize: 100,
      minSecondSize: 120,
    }),
    { firstSize: 100, secondSize: 700 }
  );

  assert.deepEqual(
    transportPage.resolvePanelSizes({
      containerSize: 805,
      dividerSize: 5,
      pointerOffset: 760,
      minFirstSize: 100,
      minSecondSize: 120,
    }),
    { firstSize: 680, secondSize: 120 }
  );
});

test('resolveVehicleDetailsPosition keeps the vehicle passenger table inside the viewport', () => {
  assert.deepEqual(
    transportPage.resolveVehicleDetailsPosition({
      anchorRect: { left: 480, top: 0, right: 584, bottom: 96, width: 104, height: 96 },
      panelWidth: 264,
      panelHeight: 240,
      viewportWidth: 600,
      viewportHeight: 400,
      offset: 10,
      viewportMargin: 12,
    }),
    { left: 206, top: 12, horizontalDirection: 'left' }
  );

  assert.deepEqual(
    transportPage.resolveVehicleDetailsPosition({
      anchorRect: { left: 8, top: 340, right: 112, bottom: 436, width: 104, height: 96 },
      panelWidth: 264,
      panelHeight: 240,
      viewportWidth: 320,
      viewportHeight: 440,
      offset: 10,
      viewportMargin: 12,
    }),
    { left: 12, top: 188, horizontalDirection: 'center' }
  );
});

test('mapVehicleIconPath resolves each transport vehicle type to its icon asset', () => {
  assert.equal(transportPage.mapVehicleIconPath('carro'), '../assets/icons/car.svg');
  assert.equal(transportPage.mapVehicleIconPath('minivan'), '../assets/icons/minivan.svg');
  assert.equal(transportPage.mapVehicleIconPath('van'), '../assets/icons/van.svg');
  assert.equal(transportPage.mapVehicleIconPath('onibus'), '../assets/icons/bus.svg');
});

test('formatVehicleOccupancyLabel shows the current and total allocated seats', () => {
  assert.equal(
    transportPage.formatVehicleOccupancyLabel({ placa: 'SGX1234A', lugares: 7 }, 3),
    'SGX1234A (3/7)'
  );
});

test('formatVehicleOccupancyCount shows only the allocated and total seats', () => {
  assert.equal(
    transportPage.formatVehicleOccupancyCount({ placa: 'SGX1234A', lugares: 7 }, 3),
    '3/7'
  );
});

test('getEffectiveWorkToHomeDepartureTime prefers the dashboard override and falls back safely', () => {
  assert.equal(
    transportPage.getEffectiveWorkToHomeDepartureTime({ work_to_home_departure_time: '18:10' }, '16:45'),
    '18:10'
  );
  assert.equal(
    transportPage.getEffectiveWorkToHomeDepartureTime({ work_to_home_departure_time: '' }, '17:00'),
    '17:00'
  );
  assert.equal(
    transportPage.getEffectiveWorkToHomeDepartureTime(null, 'bad-value'),
    '16:45'
  );
});

test('getVehicleDepartureTime returns only valid departure times', () => {
  assert.equal(transportPage.getVehicleDepartureTime({ departure_time: '17:20' }), '17:20');
  assert.equal(transportPage.getVehicleDepartureTime({ departure_time: '17h20' }), '');
  assert.equal(transportPage.getVehicleDepartureTime({}), '');
});

test('getDefaultVehicleSeatCount matches the configured defaults for each vehicle type', () => {
  assert.equal(transportPage.getDefaultVehicleSeatCount('carro'), 3);
  assert.equal(transportPage.getDefaultVehicleSeatCount('minivan'), 6);
  assert.equal(transportPage.getDefaultVehicleSeatCount('van'), 10);
  assert.equal(transportPage.getDefaultVehicleSeatCount('onibus'), 40);
  assert.equal(transportPage.getDefaultVehicleSeatCount('unknown'), 3);
});

test('getDefaultVehicleFormValues returns the prefilled create-modal defaults', () => {
  assert.deepEqual(transportPage.getDefaultVehicleFormValues('carro'), {
    tipo: 'carro',
    lugares: 3,
    tolerance: 5,
  });
  assert.deepEqual(transportPage.getDefaultVehicleFormValues('minivan'), {
    tipo: 'minivan',
    lugares: 6,
    tolerance: 5,
  });
  assert.deepEqual(transportPage.getDefaultVehicleFormValues('van'), {
    tipo: 'van',
    lugares: 10,
    tolerance: 5,
  });
  assert.deepEqual(transportPage.getDefaultVehicleFormValues('onibus'), {
    tipo: 'onibus',
    lugares: 40,
    tolerance: 5,
  });
  assert.deepEqual(transportPage.getDefaultVehicleFormValues('unknown'), {
    tipo: 'carro',
    lugares: 3,
    tolerance: 5,
  });
});

test('vehicle modal markup includes the default places and tolerance values', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );

  assert.match(transportHtml, /<option value="carro" selected>Car<\/option>/);
  assert.match(transportHtml, /<input type="number" name="lugares" class="transport-number-input transport-number-input-spinnerless" min="1" max="99" value="3" required \/>/);
  assert.match(transportHtml, /<input type="number" name="tolerance" class="transport-number-input transport-number-input-spinnerless" min="0" max="240" value="5" required \/>/);
});

test('syncVehicleTypeDependentDefaults updates the vehicle type, places, and tolerance fields together', () => {
  const formStub = {
    elements: {
      tipo: { value: 'carro' },
      lugares: { value: '3' },
      tolerance: { value: '5' },
    },
  };

  transportPage.syncVehicleTypeDependentDefaults('minivan', formStub);
  assert.deepEqual(formStub.elements, {
    tipo: { value: 'minivan' },
    lugares: { value: '6' },
    tolerance: { value: '5' },
  });

  transportPage.syncVehicleTypeDependentDefaults('van', formStub);
  assert.equal(formStub.elements.tipo.value, 'van');
  assert.equal(formStub.elements.lugares.value, '10');
  assert.equal(formStub.elements.tolerance.value, '5');

  transportPage.syncVehicleTypeDependentDefaults('onibus', formStub);
  assert.equal(formStub.elements.tipo.value, 'onibus');
  assert.equal(formStub.elements.lugares.value, '40');
  assert.equal(formStub.elements.tolerance.value, '5');
});

test('getPassengerAwarenessState defaults to pending until the webapp acknowledgement signal exists', () => {
  assert.equal(transportPage.getPassengerAwarenessState({ nome: 'Alice Rider' }), 'pending');
  assert.equal(transportPage.getPassengerAwarenessState({ nome: 'Bob Rider', awareness_status: 'aware' }), 'aware');
});

test('shouldHighlightRequestName marks unassigned and cancelled rows for red-name attention', () => {
  assert.equal(transportPage.shouldHighlightRequestName('pending'), true);
  assert.equal(transportPage.shouldHighlightRequestName('cancelled'), true);
  assert.equal(transportPage.shouldHighlightRequestName('rejected'), true);
  assert.equal(transportPage.shouldHighlightRequestName('confirmed'), false);
});

test('buildVehiclePassengerAwarenessRows pads the vehicle details table to five lines', () => {
  assert.deepEqual(
    transportPage.buildVehiclePassengerAwarenessRows(
      [
        { nome: 'Alice Rider' },
        { nome: 'Bob Rider', awareness_status: 'aware' },
      ],
      5
    ),
    [
      { name: 'Alice Rider', awarenessState: 'pending' },
      { name: 'Bob Rider', awarenessState: 'aware' },
      { name: '', awarenessState: null },
      { name: '', awarenessState: null },
      { name: '', awarenessState: null },
    ]
  );
});

test('buildVehiclePassengerAwarenessRows keeps overflow passengers while preserving the first five visible rows', () => {
  assert.deepEqual(
    transportPage.buildVehiclePassengerAwarenessRows(
      [
        { nome: 'Alice Rider' },
        { nome: 'Bob Rider', awareness_status: 'aware' },
        { nome: 'Carol Rider' },
        { nome: 'Daniel Rider' },
        { nome: 'Evelyn Rider' },
        { nome: 'Frank Rider' },
      ],
      5
    ),
    [
      { name: 'Alice Rider', awarenessState: 'pending' },
      { name: 'Bob Rider', awarenessState: 'aware' },
      { name: 'Carol Rider', awarenessState: 'pending' },
      { name: 'Daniel Rider', awarenessState: 'pending' },
      { name: 'Evelyn Rider', awarenessState: 'pending' },
      { name: 'Frank Rider', awarenessState: 'pending' },
    ]
  );
});

test('transport page request section titles are rendered as links that control each user list', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );

  assert.match(transportHtml, /data-toggle-request-section="extra"/);
  assert.match(transportHtml, /data-toggle-request-section="weekend"/);
  assert.match(transportHtml, /data-toggle-request-section="regular"/);
  assert.match(transportHtml, /id="transportRequestScopeExtra"/);
  assert.match(transportHtml, /id="transportRequestScopeWeekend"/);
  assert.match(transportHtml, /id="transportRequestScopeRegular"/);
});

test('transport topbar removes route controls and keeps only the selected-date time field', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.doesNotMatch(transportHtml, /data-route-select/);
  assert.doesNotMatch(transportHtml, /type="radio"\s+name="transport_route_kind"/);
  assert.match(transportHtml, /data-route-time-label/);
  assert.match(transportHtml, /data-route-time-input/);
  assert.doesNotMatch(transportScript, /const routeSelect = document\.querySelector\("\[data-route-select\]"\);/);
  assert.match(transportScript, /const shouldShowRouteTime = state\.isAuthenticated;/);
  assert.match(transportScript, /routeTimePopover\.hidden = !shouldShowRouteTime;/);
  assert.match(transportCss, /\.transport-route-inline-time-label\s*\{[\s\S]*text-transform:\s*uppercase;[\s\S]*white-space:\s*nowrap;/);
});

test('transport vehicle route badges are rendered only for extra vehicles', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(
    transportScript,
    /const routeLabel = scope === "extra" && vehicle\.route_kind[\s\S]*createNode\("span", "transport-vehicle-route", getRouteKindLabel\(vehicle\.route_kind\)\)/
  );
  assert.match(
    transportScript,
    /if \(scope === "extra" && vehicle\.route_kind\) \{[\s\S]*vehicleButton\.title = `\$\{vehicleButton\.title\} \| \$\{getRouteKindLabel\(vehicle\.route_kind\)\}`;/
  );
});

test('transport vehicle list headers keep the add button visible when titles need to shrink or wrap', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(
    transportCss,
    /\.transport-pane-title-row\s*\{[\s\S]*justify-content:\s*space-between;[\s\S]*flex-wrap:\s*wrap;[\s\S]*min-width:\s*0;/
  );
  assert.match(
    transportCss,
    /\.transport-pane-title\s*\{[\s\S]*flex:\s*1 1 auto;[\s\S]*min-width:\s*0;/
  );
  assert.match(
    transportCss,
    /\.transport-add-button\s*\{[\s\S]*flex:\s*0 0 auto;[\s\S]*width:\s*38px;/
  );
});

test('transport frontend uses base-relative asset and API paths so the /checking prefix keeps working', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportScript, /const TRANSPORT_ASSETS_PREFIX = "\.\.\/assets";/);
  assert.match(transportScript, /const TRANSPORT_API_PREFIX = "\.\.\/api\/transport";/);
  assert.match(transportScript, /new globalScope\.EventSource\(`\$\{TRANSPORT_API_PREFIX\}\/stream`\);/);
  assert.match(transportScript, /requestJson\(`\$\{TRANSPORT_API_PREFIX\}\/vehicles`, \{/);
  assert.match(transportScript, /requestJson\(`\$\{TRANSPORT_API_PREFIX\}\/assignments`, \{/);
  assert.match(transportScript, /requestJson\(`\$\{TRANSPORT_API_PREFIX\}\/requests\/reject`, \{/);
  assert.match(transportScript, /requestJson\(`\$\{TRANSPORT_API_PREFIX\}\/auth\/session`\)/);
  assert.doesNotMatch(transportScript, /"\/api\/transport/);
  assert.doesNotMatch(transportScript, /"\/assets\/icons/);
});

test('transport request sections size themselves by their own content instead of sharing equal-height rows', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(
    transportCss,
    /\.transport-request-sections\s*\{[\s\S]*display:\s*flex;[\s\S]*flex-direction:\s*column;[\s\S]*overflow:\s*auto;/
  );
  assert.match(
    transportCss,
    /\.transport-request-section\s*\{[\s\S]*flex:\s*0 0 auto;/
  );
  assert.doesNotMatch(
    transportCss,
    /\.transport-request-sections\s*\{[\s\S]*grid-template-rows:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\);/
  );
});

test('transport request rows animate collapsed content instead of reflowing abruptly', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(
    transportCss,
    /\.transport-request-row\s*\{[\s\S]*transition:[\s\S]*min-height 220ms ease,[\s\S]*padding 220ms ease,[\s\S]*gap 220ms ease;/
  );
  assert.match(
    transportCss,
    /\.transport-request-secondary\s*\{[\s\S]*max-height:\s*3\.2em;[\s\S]*transition:\s*max-height 220ms ease, opacity 180ms ease, transform 180ms ease, margin-top 180ms ease;/
  );
  assert.match(
    transportCss,
    /\.transport-request-row\.is-collapsed \.transport-request-secondary,[\s\S]*max-height:\s*0;[\s\S]*opacity:\s*0;/
  );
});

test('transport vehicle details panel inserts the delete button before the passenger table shell', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportScript, /detailsPanel\.insertBefore\(deleteButton, passengerTableShell\);/);
});

test('transport vehicle details render in a fixed overlay layer above the layout', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(
    transportCss,
    /\.transport-vehicle-details-layer\s*\{[\s\S]*position:\s*fixed;[\s\S]*inset:\s*0;[\s\S]*z-index:\s*360;[\s\S]*pointer-events:\s*none;[\s\S]*background:\s*transparent;/
  );
  assert.match(
    transportCss,
    /\.transport-vehicle-details-layer\.is-active\s*\{[\s\S]*pointer-events:\s*auto;[\s\S]*background:\s*rgba\(4, 5, 7, 0\.18\);/
  );
  assert.match(
    transportCss,
    /\.transport-vehicle-details\s*\{[\s\S]*position:\s*absolute;[\s\S]*pointer-events:\s*auto;/
  );
  assert.match(
    transportScript,
    /vehicleDetailsOverlayHost\.appendChild\(tileElement\.expandedDetailsPanel\);/
  );
  assert.match(
    transportScript,
    /vehicleDetailsOverlayHost\.classList\.toggle\("is-active", hasExpandedDetailsPanel\);/
  );
  assert.match(
    transportScript,
    /vehicleDetailsOverlayHost\.addEventListener\("click", function \(event\) \{[\s\S]*closeExpandedVehicleDetails\(\{ restoreFocus: true \}\);/
  );
  assert.match(
    transportScript,
    /document\.addEventListener\("keydown", function \(event\) \{[\s\S]*event\.key !== "Escape"[\s\S]*closeExpandedVehicleDetails\(\{ restoreFocus: true \}\);/
  );
});

test('buildVehiclePassengerPreviewRows keeps the dragged passenger visible in the preview table', () => {
  assert.deepEqual(
    transportPage.buildVehiclePassengerPreviewRows(
      [
        { id: 1, nome: 'Alice Rider' },
        { id: 2, nome: 'Bob Rider' },
        { id: 3, nome: 'Carol Rider' },
      ],
      { id: 99, nome: 'Dragged Rider' },
      3
    ),
    [
      { id: 99, nome: 'Dragged Rider' },
      { id: 1, nome: 'Alice Rider' },
      { id: 2, nome: 'Bob Rider' },
    ]
  );
});

test('groupAssignedRequestsByVehicleForDate only includes confirmed passengers for the selected service date', () => {
  assert.deepEqual(
    transportPage.groupAssignedRequestsByVehicleForDate(
      [
        {
          id: 1,
          nome: 'Monday Rider',
          service_date: '2026-04-21',
          assignment_status: 'confirmed',
          assigned_vehicle: { id: 77, placa: 'REG1001' },
        },
        {
          id: 2,
          nome: 'Wednesday Rider',
          service_date: '2026-04-22',
          assignment_status: 'confirmed',
          assigned_vehicle: { id: 77, placa: 'REG1001' },
        },
        {
          id: 3,
          nome: 'Pending Rider',
          service_date: '2026-04-21',
          assignment_status: 'pending',
          assigned_vehicle: { id: 77, placa: 'REG1001' },
        },
        {
          id: 4,
          nome: 'Other Vehicle Rider',
          service_date: '2026-04-21',
          assignment_status: 'confirmed',
          assigned_vehicle: { id: 88, placa: 'REG2002' },
        },
      ],
      '2026-04-21'
    ),
    {
      '77': [
        {
          id: 1,
          nome: 'Monday Rider',
          service_date: '2026-04-21',
          assignment_status: 'confirmed',
          assigned_vehicle: { id: 77, placa: 'REG1001' },
        },
      ],
      '88': [
        {
          id: 4,
          nome: 'Other Vehicle Rider',
          service_date: '2026-04-21',
          assignment_status: 'confirmed',
          assigned_vehicle: { id: 88, placa: 'REG2002' },
        },
      ],
    }
  );
});

test('groupAssignedRequestsByVehicleForDate keeps weekend passengers out of the vehicle on off-days', () => {
  assert.deepEqual(
    transportPage.groupAssignedRequestsByVehicleForDate(
      [
        {
          id: 11,
          nome: 'Sunday Rider',
          request_kind: 'weekend',
          service_date: '2026-04-19',
          assignment_status: 'confirmed',
          assigned_vehicle: { id: 99, placa: 'WKD1001' },
        },
        {
          id: 12,
          nome: 'Saturday Rider',
          request_kind: 'weekend',
          service_date: '2026-04-18',
          assignment_status: 'confirmed',
          assigned_vehicle: { id: 99, placa: 'WKD1001' },
        },
      ],
      '2026-04-18'
    ),
    {
      '99': [
        {
          id: 12,
          nome: 'Saturday Rider',
          request_kind: 'weekend',
          service_date: '2026-04-18',
          assignment_status: 'confirmed',
          assigned_vehicle: { id: 99, placa: 'WKD1001' },
        },
      ],
    }
  );
});

test('canRequestBeDroppedOnVehicle only accepts compatible scope combinations and lets extra vehicles carry their own route', () => {
  assert.equal(
    transportPage.canRequestBeDroppedOnVehicle(
      { id: 10, request_kind: 'regular' },
      'regular',
      { id: 8, route_kind: null },
      'home_to_work'
    ),
    true
  );
  assert.equal(
    transportPage.canRequestBeDroppedOnVehicle(
      { id: 10, request_kind: 'regular' },
      'weekend',
      { id: 8, route_kind: null },
      'home_to_work'
    ),
    false
  );
  assert.equal(
    transportPage.canRequestBeDroppedOnVehicle(
      { id: 10, request_kind: 'extra', assigned_vehicle: { id: 8 } },
      'extra',
      { id: 8, route_kind: 'work_to_home' },
      'work_to_home'
    ),
    false
  );
  assert.equal(
    transportPage.canRequestBeDroppedOnVehicle(
      { id: 10, request_kind: 'extra' },
      'extra',
      { id: 8, route_kind: 'work_to_home' },
      'home_to_work'
    ),
    true
  );
});

test('buildVehicleCreatePayload sends weekend persistence and extra departure time only for extra vehicles', () => {
  const regularFormData = new FormData();
  regularFormData.set('service_scope', 'regular');
  regularFormData.set('tipo', 'carro');
  regularFormData.set('placa', 'ABC1234');
  regularFormData.set('color', 'Black');
  regularFormData.set('lugares', '4');
  regularFormData.set('tolerance', '12');
  regularFormData.set('route_kind', 'work_to_home');

  assert.deepEqual(
    transportPage.buildVehicleCreatePayload(regularFormData, '2026-04-18', 'home_to_work'),
    {
      service_scope: 'regular',
      service_date: '2026-04-18',
      tipo: 'carro',
      placa: 'ABC1234',
      color: 'Black',
      lugares: 4,
      tolerance: 12,
    }
  );

  const weekendFormData = new FormData();
  weekendFormData.set('service_scope', 'weekend');
  weekendFormData.set('tipo', 'minivan');
  weekendFormData.set('placa', 'WKD9000');
  weekendFormData.set('color', 'Silver');
  weekendFormData.set('lugares', '6');
  weekendFormData.set('tolerance', '14');
  weekendFormData.set('every_saturday', 'on');

  assert.deepEqual(
    transportPage.buildVehicleCreatePayload(weekendFormData, '2026-04-18', 'home_to_work'),
    {
      service_scope: 'weekend',
      service_date: '2026-04-18',
      tipo: 'minivan',
      placa: 'WKD9000',
      color: 'Silver',
      lugares: 6,
      tolerance: 14,
      every_saturday: true,
      every_sunday: false,
    }
  );

  const extraFormData = new FormData();
  extraFormData.set('service_scope', 'extra');
  extraFormData.set('tipo', 'van');
  extraFormData.set('placa', 'XYZ9000');
  extraFormData.set('color', 'White');
  extraFormData.set('lugares', '10');
  extraFormData.set('tolerance', '18');
  extraFormData.set('departure_time', '17:45');
  extraFormData.set('route_kind', 'work_to_home');

  assert.deepEqual(
    transportPage.buildVehicleCreatePayload(extraFormData, '2026-04-18', 'home_to_work'),
    {
      service_scope: 'extra',
      service_date: '2026-04-18',
      tipo: 'van',
      placa: 'XYZ9000',
      color: 'White',
      lugares: 10,
      tolerance: 18,
      departure_time: '17:45',
      route_kind: 'work_to_home',
    }
  );
});

test('formatApiErrorMessage extracts readable messages from FastAPI validation payloads', () => {
  assert.equal(
    transportPage.formatApiErrorMessage(
      {
        detail: [
          {
            type: 'value_error',
            loc: ['body'],
            msg: 'Value error, route_kind is only allowed for extra vehicles',
          },
        ],
      },
      422
    ),
    'Value error, route_kind is only allowed for extra vehicles'
  );

  assert.equal(
    transportPage.formatApiErrorMessage({ detail: 'Vehicle already exists.' }, 409),
    'Vehicle already exists.'
  );
});
