const test = require('node:test');
const assert = require('node:assert/strict');

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

test('mapVehicleIconPath resolves each transport vehicle type to its icon asset', () => {
  assert.equal(transportPage.mapVehicleIconPath('carro'), 'icons/car.svg');
  assert.equal(transportPage.mapVehicleIconPath('minivan'), 'icons/minivan.svg');
  assert.equal(transportPage.mapVehicleIconPath('van'), 'icons/van.svg');
  assert.equal(transportPage.mapVehicleIconPath('onibus'), 'icons/bus.svg');
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

test('getPassengerAwarenessState defaults to pending until the webapp acknowledgement signal exists', () => {
  assert.equal(transportPage.getPassengerAwarenessState({ nome: 'Alice Rider' }), 'pending');
  assert.equal(transportPage.getPassengerAwarenessState({ nome: 'Bob Rider', awareness_status: 'aware' }), 'aware');
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

test('buildVehicleCreatePayload only sends route_kind for extra vehicles', () => {
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

  const extraFormData = new FormData();
  extraFormData.set('service_scope', 'extra');
  extraFormData.set('tipo', 'van');
  extraFormData.set('placa', 'XYZ9000');
  extraFormData.set('color', 'White');
  extraFormData.set('lugares', '10');
  extraFormData.set('tolerance', '18');
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
