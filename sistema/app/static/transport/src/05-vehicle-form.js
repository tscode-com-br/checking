  function normalizeVehicleSeatCountSetting(value, fallbackValue) {
    const parsed = Number.parseInt(String(value), 10);
    if (!Number.isFinite(parsed) || parsed < 1 || parsed > 99) {
      return fallbackValue;
    }
    return parsed;
  }

  function resolveTransportVehicleSeatDefaults(source, fallbackValues) {
    const fallbackSeatDefaults = fallbackValues || DEFAULT_VEHICLE_SEAT_COUNT;
    return {
      carro: normalizeVehicleSeatCountSetting(
        source && (source.carro !== undefined ? source.carro : source.default_car_seats),
        fallbackSeatDefaults.carro
      ),
      minivan: normalizeVehicleSeatCountSetting(
        source && (source.minivan !== undefined ? source.minivan : source.default_minivan_seats),
        fallbackSeatDefaults.minivan
      ),
      van: normalizeVehicleSeatCountSetting(
        source && (source.van !== undefined ? source.van : source.default_van_seats),
        fallbackSeatDefaults.van
      ),
      onibus: normalizeVehicleSeatCountSetting(
        source && (source.onibus !== undefined ? source.onibus : source.default_bus_seats),
        fallbackSeatDefaults.onibus
      ),
    };
  }

  function applyTransportVehicleSeatDefaults(nextValues) {
    vehicleDefaultSeatCount = resolveTransportVehicleSeatDefaults(nextValues, vehicleDefaultSeatCount);
    return Object.assign({}, vehicleDefaultSeatCount);
  }

  function normalizeTransportCurrencyCode(value) {
    return String(value || "")
      .toUpperCase()
      .replace(/\s+/g, "")
      .trim();
  }

  function isValidTransportCurrencyCode(value) {
    return TRANSPORT_CURRENCY_CODE_PATTERN.test(normalizeTransportCurrencyCode(value));
  }

  function normalizeTransportCurrencyLabel(value) {
    const normalizedValue = String(value || "").trim();
    return normalizedValue || "";
  }

  function resolveTransportCurrencyOptions(sourceOptions) {
    const rows = Array.isArray(sourceOptions) ? sourceOptions : [];
    const seenCodes = new Set();

    return rows.reduce(function (resolvedRows, row) {
      const code = normalizeTransportCurrencyCode(row && row.code);
      if (!code || !isValidTransportCurrencyCode(code) || seenCodes.has(code)) {
        return resolvedRows;
      }

      seenCodes.add(code);
      resolvedRows.push({
        code,
        display_label: normalizeTransportCurrencyLabel(row && row.display_label) || null,
      });
      return resolvedRows;
    }, []).sort(function (left, right) {
      return left.code.localeCompare(right.code);
    });
  }

  function formatTransportCurrencyOptionLabel(option) {
    if (!option) {
      return "";
    }
    return option.display_label ? `${option.code} - ${option.display_label}` : option.code;
  }

  function normalizeTransportPriceRateUnit(value, fallbackValue) {
    const normalizedValue = String(value || "").trim().toLowerCase();
    if (!TRANSPORT_PRICE_RATE_UNITS.includes(normalizedValue)) {
      return fallbackValue;
    }
    return normalizedValue;
  }

  function getTransportPriceRateUnitLabel(value, fallbackValue) {
    const normalizedUnit = normalizeTransportPriceRateUnit(value, "");
    if (!normalizedUnit) {
      return fallbackValue || "";
    }

    return {
      hour: translateTransportAiReviewText("settings.perHour", "Per hour"),
      day: translateTransportAiReviewText("settings.perDay", "Per day"),
      week: translateTransportAiReviewText("settings.perWeek", "Per week"),
      month: translateTransportAiReviewText("settings.perMonth", "Per month"),
    }[normalizedUnit] || fallbackValue || normalizedUnit;
  }

  function normalizeTransportPriceSetting(value, fallbackValue) {
    if (value === null || value === undefined) {
      return null;
    }

    const normalizedValue = String(value).trim();
    if (!normalizedValue) {
      return null;
    }

    const parsedValue = Number(normalizedValue);
    if (!Number.isFinite(parsedValue) || parsedValue < 0 || parsedValue > MAX_TRANSPORT_PRICE_VALUE) {
      return fallbackValue;
    }

    return Math.round(parsedValue * 100) / 100;
  }

  function resolveTransportVehiclePriceDefaults(source, fallbackValues) {
    const fallbackPriceDefaults = fallbackValues || DEFAULT_VEHICLE_PRICE_DEFAULTS;
    return {
      carro: normalizeTransportPriceSetting(
        source && (source.carro !== undefined ? source.carro : source.default_car_price),
        fallbackPriceDefaults.carro
      ),
      minivan: normalizeTransportPriceSetting(
        source && (source.minivan !== undefined ? source.minivan : source.default_minivan_price),
        fallbackPriceDefaults.minivan
      ),
      van: normalizeTransportPriceSetting(
        source && (source.van !== undefined ? source.van : source.default_van_price),
        fallbackPriceDefaults.van
      ),
      onibus: normalizeTransportPriceSetting(
        source && (source.onibus !== undefined ? source.onibus : source.default_bus_price),
        fallbackPriceDefaults.onibus
      ),
    };
  }

  function formatTransportPriceInputValue(value) {
    if (value === null || value === undefined || value === "") {
      return "";
    }

    const parsedValue = Number(value);
    if (!Number.isFinite(parsedValue)) {
      return "";
    }

    return parsedValue.toFixed(2);
  }

  function normalizeVehicleToleranceSetting(value, fallbackValue) {
    const parsed = Number.parseInt(String(value), 10);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > 240) {
      return fallbackValue;
    }
    return parsed;
  }

  function applyTransportVehicleToleranceDefault(nextValue) {
    vehicleDefaultToleranceMinutes = normalizeVehicleToleranceSetting(nextValue, vehicleDefaultToleranceMinutes);
    return vehicleDefaultToleranceMinutes;
  }

  function getDefaultVehicleSeatCount(vehicleType) {
    return vehicleDefaultSeatCount[vehicleType] || DEFAULT_VEHICLE_SEAT_COUNT.carro;
  }

  function getDefaultVehicleToleranceMinutes() {
    return vehicleDefaultToleranceMinutes;
  }

  function getDefaultVehicleFormValues(vehicleType) {
    const normalizedVehicleType = Object.prototype.hasOwnProperty.call(DEFAULT_VEHICLE_SEAT_COUNT, vehicleType)
      ? vehicleType
      : "carro";

    return {
      tipo: normalizedVehicleType,
      lugares: getDefaultVehicleSeatCount(normalizedVehicleType),
      tolerance: getDefaultVehicleToleranceMinutes(),
    };
  }

  function normalizeVehicleScope(scope) {
    const normalizedScope = String(scope || "").trim().toLowerCase();
    if (normalizedScope === "regular" || normalizedScope === "weekend" || normalizedScope === "extra") {
      return normalizedScope;
    }
    return "regular";
  }

  function resolveVehicleForm(formElement) {
    if (formElement && formElement.elements) {
      return formElement;
    }

    if (typeof document === "undefined") {
      return null;
    }

    const resolvedForm = document.querySelector("[data-vehicle-form]");
    if (!resolvedForm || !resolvedForm.elements) {
      return null;
    }

    return resolvedForm;
  }

  function applyVehicleSeatDefault(vehicleType, formElement) {
    const resolvedForm = resolveVehicleForm(formElement);
    if (!resolvedForm || !resolvedForm.elements.lugares) {
      return;
    }
    resolvedForm.elements.lugares.value = String(getDefaultVehicleSeatCount(vehicleType));
  }

  function normalizeOptionalVehicleFormTextValue(value) {
    const normalizedValue = String(value || '').trim();
    return normalizedValue || null;
  }

  function normalizeOptionalVehicleFormIntegerValue(value) {
    const normalizedValue = String(value || '').trim();
    if (!normalizedValue) {
      return null;
    }

    const parsedValue = Number(normalizedValue);
    return Number.isFinite(parsedValue) ? parsedValue : null;
  }

  function buildVehicleBasePayload(formData) {
    return {
      tipo: normalizeOptionalVehicleFormTextValue(formData.get("tipo")),
      placa: normalizeOptionalVehicleFormTextValue(formData.get("placa")),
      color: normalizeOptionalVehicleFormTextValue(formData.get("color")),
      lugares: normalizeOptionalVehicleFormIntegerValue(formData.get("lugares")),
      tolerance: normalizeOptionalVehicleFormIntegerValue(formData.get("tolerance")),
    };
  }

  function resolveVehicleEditFocusField(vehicle) {
    const resolvedVehicle = vehicle || {};
    const pendingFields = Array.isArray(resolvedVehicle.pending_fields) ? resolvedVehicle.pending_fields : [];
    const pendingField = VEHICLE_BASE_FIELD_ORDER.find(function (fieldName) {
      return pendingFields.includes(fieldName);
    });

    if (pendingField) {
      return pendingField;
    }

    const firstEmptyField = VEHICLE_BASE_FIELD_ORDER.find(function (fieldName) {
      const fieldValue = resolvedVehicle[fieldName];
      return fieldValue === null || fieldValue === undefined || String(fieldValue).trim() === "";
    });

    return firstEmptyField || "tipo";
  }

  function syncVehicleTypeDependentDefaults(vehicleType, formElement) {
    const resolvedForm = resolveVehicleForm(formElement);
    if (!resolvedForm) {
      return;
    }

    const normalizedVehicleType = String(vehicleType || '').trim().toLowerCase();

    if (!Object.prototype.hasOwnProperty.call(DEFAULT_VEHICLE_SEAT_COUNT, normalizedVehicleType)) {
      if (resolvedForm.elements.tipo) {
        resolvedForm.elements.tipo.value = '';
      }
      return;
    }

    if (resolvedForm.elements.tipo) {
      resolvedForm.elements.tipo.value = normalizedVehicleType;
    }

    applyVehicleSeatDefault(normalizedVehicleType, resolvedForm);

    if (resolvedForm.elements.tolerance) {
      resolvedForm.elements.tolerance.value = String(getDefaultVehicleToleranceMinutes());
    }
  }

  function applyVehicleFormDefaults(vehicleType, formElement) {
    const resolvedForm = resolveVehicleForm(formElement);
    if (!resolvedForm) {
      return;
    }

    const defaults = getDefaultVehicleFormValues(vehicleType);

    if (resolvedForm.elements.tipo) {
      resolvedForm.elements.tipo.value = defaults.tipo;
    }
    if (resolvedForm.elements.lugares) {
      resolvedForm.elements.lugares.value = String(defaults.lugares);
    }
    if (resolvedForm.elements.tolerance) {
      resolvedForm.elements.tolerance.value = String(defaults.tolerance);
    }
  }

  function buildVehicleCreatePayload(formData, serviceDate, selectedRouteKind) {
    const serviceScope = normalizeVehicleScope(formData.get("service_scope") || "regular");
    const payload = Object.assign({
      service_scope: serviceScope,
      service_date: String(serviceDate || ""),
    }, buildVehicleBasePayload(formData));

    if (serviceScope === "extra") {
      payload.service_date = String(formData.get("service_date") || "").trim();
      payload.route_kind = String(formData.get("route_kind") || selectedRouteKind || "home_to_work");
      payload.departure_time = String(formData.get("departure_time") || "").trim();
      return payload;
    }

    if (serviceScope === "weekend") {
      payload.every_saturday = Boolean(formData.get("every_saturday"));
      payload.every_sunday = Boolean(formData.get("every_sunday"));
      return payload;
    }

    payload.every_monday = Boolean(formData.get("every_monday"));
    payload.every_tuesday = Boolean(formData.get("every_tuesday"));
    payload.every_wednesday = Boolean(formData.get("every_wednesday"));
    payload.every_thursday = Boolean(formData.get("every_thursday"));
    payload.every_friday = Boolean(formData.get("every_friday"));

    return payload;
  }

  function resolveVehicleModalOpenState(scope, currentServiceDate) {
    const normalizedScope = normalizeVehicleScope(scope);
    return {
      serviceDateValue: normalizedScope === "extra" ? String(currentServiceDate || "").trim() : "",
      departureTimeValue: "",
      initialFocusField: normalizedScope === "extra" ? "service_date" : null,
      fallbackFocusField: normalizedScope === "extra" ? "departure_time" : null,
    };
  }

  function resolveVehicleCreateValidationError(payload) {
    if (!payload || typeof payload !== "object") {
      return null;
    }

    if (payload.service_scope === "extra" && !String(payload.service_date || "").trim()) {
      return {
        messageKey: "warnings.extraServiceDateRequired",
        focusField: "service_date",
      };
    }

    if (payload.service_scope === "extra" && !String(payload.departure_time || "").trim()) {
      return {
        messageKey: "warnings.extraDepartureRequired",
        focusField: "departure_time",
      };
    }

    if (payload.service_scope === "weekend" && !payload.every_saturday && !payload.every_sunday) {
      return {
        messageKey: "warnings.weekendPersistence",
        focusField: null,
      };
    }

    if (
      payload.service_scope === "regular"
      && !payload.every_monday
      && !payload.every_tuesday
      && !payload.every_wednesday
      && !payload.every_thursday
      && !payload.every_friday
    ) {
      return {
        messageKey: "warnings.regularPersistence",
        focusField: null,
      };
    }

    return null;
  }

  function resolveVehicleSaveReloadDate(payload, fallbackDate) {
    const normalizedFallbackDate = fallbackDate instanceof Date
      ? startOfLocalDay(fallbackDate)
      : parseStoredTransportDate(fallbackDate);
    const resolvedFallbackDate = normalizedFallbackDate || startOfLocalDay(new Date());

    if (!payload || payload.service_scope !== "extra") {
      return resolvedFallbackDate;
    }

    return parseStoredTransportDate(payload.service_date) || resolvedFallbackDate;
  }

  function mapVehicleTypeLabel(value) {
    const normalizedValue = String(value || "").trim();
    const translatedValue = t(`vehicleTypes.${normalizedValue}`);
    return translatedValue === `vehicleTypes.${normalizedValue}` ? normalizedValue : translatedValue;
  }

  function formatVehicleTypeTableValue(value) {
    if (isPendingVehicleField(value)) {
      return getWaitingLabel();
    }

    return String(mapVehicleTypeLabel(value) || value || "").toLowerCase();
  }

  function formatRouteTableValue(routeKind) {
    return getRouteKindLabel(routeKind).toLowerCase();
  }

  function isTemporaryVehiclePlaceholderPlate(value) {
    const normalizedValue = String(value || "").trim().toUpperCase().replace(/\s+/g, " ");
    return VEHICLE_TEMPORARY_PLACEHOLDER_PATTERN.test(normalizedValue);
  }

  function hasVehicleAdministrativeIncompleteness(vehicle) {
    if (!vehicle || typeof vehicle !== "object" || Array.isArray(vehicle)) {
      return false;
    }

    const pendingFields = Array.isArray(vehicle.pending_fields) ? vehicle.pending_fields : [];
    return pendingFields.includes("placa")
      || pendingFields.includes("color")
      || isPendingVehicleField(vehicle.placa)
      || isPendingVehicleField(vehicle.color);
  }

  function shouldUseTemporaryVehicleIcon(vehicle) {
    if (!vehicle || typeof vehicle !== "object" || Array.isArray(vehicle)) {
      return false;
    }

    return isTemporaryVehiclePlaceholderPlate(vehicle.placa)
      || hasVehicleAdministrativeIncompleteness(vehicle);
  }

  function mapVehicleIconPath(value) {
    const vehicle = value && typeof value === "object" && !Array.isArray(value) ? value : null;
    const vehicleType = vehicle ? vehicle.tipo : value;
    const iconPaths = shouldUseTemporaryVehicleIcon(vehicle)
      ? VEHICLE_TEMPORARY_ICON_PATHS
      : VEHICLE_ICON_PATHS;
    return iconPaths[vehicleType] || iconPaths.carro;
  }

  function formatVehicleOccupancyLabel(vehicle, assignedCount) {
    const occupiedSeats = Math.max(0, Number(assignedCount) || 0);
    const totalSeats = isPendingVehicleField(vehicle && vehicle.lugares)
      ? getWaitingLabel()
      : Math.max(0, Number(vehicle && vehicle.lugares) || 0);
    return `${formatPendingVehicleField(vehicle && vehicle.placa)} (${occupiedSeats}/${totalSeats})`;
  }

  function formatVehicleOccupancyCount(vehicle, assignedCount) {
    const occupiedSeats = Math.max(0, Number(assignedCount) || 0);
    const totalSeats = isPendingVehicleField(vehicle && vehicle.lugares)
      ? getWaitingLabel()
      : Math.max(0, Number(vehicle && vehicle.lugares) || 0);
    return `${occupiedSeats}/${totalSeats}`;
  }

  function parseTransportTimeToMinutes(value) {
    const normalizedValue = String(value || "").trim();
    const match = normalizedValue.match(/^(\d{2}):(\d{2})$/);
    if (!match) {
      return null;
    }

    const hours = Number(match[1]);
    const minutes = Number(match[2]);
    if (
      !Number.isInteger(hours)
      || !Number.isInteger(minutes)
      || hours < 0
      || hours > 23
      || minutes < 0
      || minutes > 59
    ) {
      return null;
    }

    return (hours * 60) + minutes;
  }

