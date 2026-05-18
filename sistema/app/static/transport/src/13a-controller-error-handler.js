  function handleProtectedRequestError(error, fallbackMessage) {
    if (error && Number(error.status) === 401) {
      clearTransportSession(getTransportSessionExpiredMessage());
      return true;
    }
    const resolvedErrorMessage = resolveTransportApiStructuredMessage(error && error.payload)
      || localizeTransportApiMessage(error && error.message)
      || fallbackMessage;
    setStatus(resolvedErrorMessage, "error", resolveTransportApiStructuredMessageOptions(error && error.payload));
    if (error && (Number(error.status) === 404 || Number(error.status) === 409)) {
      requestDashboardRefresh({ announce: false });
    }
    return false;
  }

    function openUserCreationRequest() {
      if (typeof globalScope.open === "function") {
        globalScope.open("../admin", "_blank", "noopener");
      }
      setStatus("", "info", { key: "status.openAdminToRequestUser" });
    }

    function loadTransportSettings(options) {
      const nextOptions = options || {};
      if (!state.isAuthenticated) {
        state.arriveAtWorkTime = normalizeTransportTimeValue(state.arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME);
        state.workToHomeTime = state.workToHomeTime || DEFAULT_WORK_TO_HOME_TIME;
        state.lastUpdateTime = state.lastUpdateTime || DEFAULT_LAST_UPDATE_TIME;
        state.extraCarToleranceMinutes = normalizeVehicleToleranceSetting(
          state.extraCarToleranceMinutes,
          DEFAULT_EXTRA_CAR_TOLERANCE_MINUTES
        );
        state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(state.vehicleSeatDefaults);
        state.vehiclePriceDefaults = resolveTransportVehiclePriceDefaults(
          state.vehiclePriceDefaults,
          DEFAULT_VEHICLE_PRICE_DEFAULTS
        );
        state.vehicleToleranceDefaultMinutes = applyTransportVehicleToleranceDefault(state.vehicleToleranceDefaultMinutes);
        state.priceCurrencyCode = normalizeTransportCurrencyCode(state.priceCurrencyCode);
        state.priceRateUnit = normalizeTransportPriceRateUnit(state.priceRateUnit, DEFAULT_TRANSPORT_PRICE_RATE_UNIT);
        state.availableCurrencies = resolveTransportCurrencyOptions(state.availableCurrencies);
        syncSettingsControls();
        return Promise.resolve(null);
      }

      state.settingsLoading = true;
      syncSettingsControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/settings`)
        .then(function (response) {
          state.settingsLoaded = true;
          state.arriveAtWorkTime = normalizeTransportTimeValue(
            response && response.arrive_at_work_time,
            normalizeTransportTimeValue(state.arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME)
          );
          state.workToHomeTime = String(
            response && response.work_to_home_time ? response.work_to_home_time : DEFAULT_WORK_TO_HOME_TIME
          );
          state.lastUpdateTime = String(
            response && response.last_update_time ? response.last_update_time : DEFAULT_LAST_UPDATE_TIME
          );
          state.extraCarToleranceMinutes = normalizeVehicleToleranceSetting(
            response && response.extra_car_tolerance_minutes,
            normalizeVehicleToleranceSetting(
              state.extraCarToleranceMinutes,
              DEFAULT_EXTRA_CAR_TOLERANCE_MINUTES
            )
          );
          state.priceCurrencyCode = normalizeTransportCurrencyCode(response && response.price_currency_code);
          state.priceRateUnit = normalizeTransportPriceRateUnit(
            response && response.price_rate_unit,
            DEFAULT_TRANSPORT_PRICE_RATE_UNIT
          );
          state.availableCurrencies = resolveTransportCurrencyOptions(response && response.available_currencies);
          state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(response);
          state.vehiclePriceDefaults = resolveTransportVehiclePriceDefaults(
            response,
            state.vehiclePriceDefaults
          );
          state.vehicleToleranceDefaultMinutes = applyTransportVehicleToleranceDefault(
            response && response.default_tolerance_minutes !== undefined
              ? response.default_tolerance_minutes
              : state.vehicleToleranceDefaultMinutes
          );
          return response;
        })
        .catch(function (error) {
          handleProtectedRequestError(error, t("status.couldNotLoadSettings"));
          if (nextOptions.silent) {
            return null;
          }
          return null;
        })
        .finally(function () {
          state.settingsLoading = false;
          syncSettingsControls();
          syncRouteTimeControls();
        });
    }

    function saveTransportSettings(nextValues) {
      const previousArriveAtWorkTime = state.arriveAtWorkTime;
      const previousWorkToHomeTime = state.workToHomeTime;
      const previousLastUpdateTime = state.lastUpdateTime;
      const previousExtraCarToleranceMinutes = state.extraCarToleranceMinutes;
      const previousPriceCurrencyCode = state.priceCurrencyCode;
      const previousPriceRateUnit = state.priceRateUnit;
      const previousVehicleSeatDefaults = Object.assign({}, state.vehicleSeatDefaults);
      const previousVehiclePriceDefaults = Object.assign({}, state.vehiclePriceDefaults);
      const previousAvailableCurrencies = resolveTransportCurrencyOptions(state.availableCurrencies);
      const previousVehicleToleranceDefaultMinutes = state.vehicleToleranceDefaultMinutes;
      const normalizedArriveAtWorkTime = normalizeTransportTimeValue(
        nextValues && nextValues.arriveAtWorkTime,
        normalizeTransportTimeValue(state.arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME)
      );
      const normalizedTime = normalizeTransportTimeValue(
        nextValues && nextValues.workToHomeTime,
        normalizeTransportTimeValue(state.workToHomeTime, DEFAULT_WORK_TO_HOME_TIME)
      );
      const normalizedLastUpdateTime = normalizeTransportTimeValue(
        nextValues && nextValues.lastUpdateTime,
        normalizeTransportTimeValue(state.lastUpdateTime, DEFAULT_LAST_UPDATE_TIME)
      );
      const normalizedExtraCarToleranceMinutes = normalizeVehicleToleranceSetting(
        nextValues && nextValues.extraCarToleranceMinutes,
        normalizeVehicleToleranceSetting(
          state.extraCarToleranceMinutes,
          DEFAULT_EXTRA_CAR_TOLERANCE_MINUTES
        )
      );
      const normalizedSeatDefaults = resolveTransportVehicleSeatDefaults(
        {
          default_car_seats: nextValues && nextValues.defaultCarSeats,
          default_minivan_seats: nextValues && nextValues.defaultMinivanSeats,
          default_van_seats: nextValues && nextValues.defaultVanSeats,
          default_bus_seats: nextValues && nextValues.defaultBusSeats,
        },
        state.vehicleSeatDefaults
      );
      const normalizedPriceCurrencyCode = normalizeTransportCurrencyCode(nextValues && nextValues.priceCurrencyCode);
      const normalizedPriceRateUnit = normalizeTransportPriceRateUnit(
        nextValues && nextValues.priceRateUnit,
        state.priceRateUnit || DEFAULT_TRANSPORT_PRICE_RATE_UNIT
      );
      const normalizedPriceDefaults = resolveTransportVehiclePriceDefaults(
        {
          default_car_price: nextValues && nextValues.defaultCarPrice,
          default_minivan_price: nextValues && nextValues.defaultMinivanPrice,
          default_van_price: nextValues && nextValues.defaultVanPrice,
          default_bus_price: nextValues && nextValues.defaultBusPrice,
        },
        state.vehiclePriceDefaults
      );
      const normalizedToleranceDefault = normalizeVehicleToleranceSetting(
        nextValues && nextValues.defaultToleranceMinutes,
        state.vehicleToleranceDefaultMinutes
      );
      if (
        !isValidTransportTimeValue(normalizedArriveAtWorkTime)
        || !isValidTransportTimeValue(normalizedTime)
        || !isValidTransportTimeValue(normalizedLastUpdateTime)
      ) {
        syncSettingsControls();
        return Promise.resolve(null);
      }
      if (
        normalizedPriceCurrencyCode
        && !state.availableCurrencies.some(function (currencyOption) {
          return currencyOption.code === normalizedPriceCurrencyCode;
        })
      ) {
        setStatus("", "warning", { key: "warnings.currencyNotAvailable" });
        syncSettingsControls();
        return Promise.resolve(null);
      }
      if (!state.isAuthenticated) {
        setStatus("", "warning", { key: "status.locked" });
        syncSettingsControls();
        return Promise.resolve(null);
      }

      state.arriveAtWorkTime = normalizedArriveAtWorkTime;
      state.workToHomeTime = normalizedTime;
      state.lastUpdateTime = normalizedLastUpdateTime;
      state.extraCarToleranceMinutes = normalizedExtraCarToleranceMinutes;
      state.priceCurrencyCode = normalizedPriceCurrencyCode;
      state.priceRateUnit = normalizedPriceRateUnit;
      state.vehicleSeatDefaults = Object.assign({}, normalizedSeatDefaults);
      state.vehiclePriceDefaults = Object.assign({}, normalizedPriceDefaults);
      state.vehicleToleranceDefaultMinutes = normalizedToleranceDefault;
      state.availableCurrencies = previousAvailableCurrencies;
      applyTransportVehicleSeatDefaults(state.vehicleSeatDefaults);
      applyTransportVehicleToleranceDefault(state.vehicleToleranceDefaultMinutes);
      state.settingsSaving = true;
      syncSettingsControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/settings`, {
        method: "PUT",
        body: JSON.stringify({
          arrive_at_work_time: normalizedArriveAtWorkTime,
          work_to_home_time: normalizedTime,
          last_update_time: normalizedLastUpdateTime,
          extra_car_tolerance_minutes: normalizedExtraCarToleranceMinutes,
          default_car_seats: normalizedSeatDefaults.carro,
          default_minivan_seats: normalizedSeatDefaults.minivan,
          default_van_seats: normalizedSeatDefaults.van,
          default_bus_seats: normalizedSeatDefaults.onibus,
          price_currency_code: normalizedPriceCurrencyCode || null,
          price_rate_unit: normalizedPriceRateUnit,
          default_car_price: normalizedPriceDefaults.carro,
          default_minivan_price: normalizedPriceDefaults.minivan,
          default_van_price: normalizedPriceDefaults.van,
          default_bus_price: normalizedPriceDefaults.onibus,
          default_tolerance_minutes: normalizedToleranceDefault,
        }),
      })
        .then(function (response) {
          state.settingsLoaded = true;
          state.arriveAtWorkTime = normalizeTransportTimeValue(
            response && response.arrive_at_work_time,
            normalizedArriveAtWorkTime
          );
          state.workToHomeTime = String(
            response && response.work_to_home_time ? response.work_to_home_time : normalizedTime
          );
          state.lastUpdateTime = String(
            response && response.last_update_time ? response.last_update_time : normalizedLastUpdateTime
          );
          state.extraCarToleranceMinutes = normalizeVehicleToleranceSetting(
            response && response.extra_car_tolerance_minutes,
            normalizedExtraCarToleranceMinutes
          );
          state.priceCurrencyCode = normalizeTransportCurrencyCode(response && response.price_currency_code);
          state.priceRateUnit = normalizeTransportPriceRateUnit(
            response && response.price_rate_unit,
            normalizedPriceRateUnit
          );
          state.availableCurrencies = resolveTransportCurrencyOptions(
            response && response.available_currencies
          );
          state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(response);
          state.vehiclePriceDefaults = resolveTransportVehiclePriceDefaults(
            response,
            normalizedPriceDefaults
          );
          state.vehicleToleranceDefaultMinutes = applyTransportVehicleToleranceDefault(
            response && response.default_tolerance_minutes !== undefined
              ? response.default_tolerance_minutes
              : normalizedToleranceDefault
          );
          return loadDashboard(dateStore.getValue(), { announce: false }).then(function () {
            setStatus("", "success", { key: "status.settingsSaved" });
            return response;
          });
        })
        .catch(function (error) {
          state.arriveAtWorkTime = previousArriveAtWorkTime;
          state.workToHomeTime = previousWorkToHomeTime;
          state.lastUpdateTime = previousLastUpdateTime;
          state.extraCarToleranceMinutes = previousExtraCarToleranceMinutes;
          state.priceCurrencyCode = previousPriceCurrencyCode;
          state.priceRateUnit = previousPriceRateUnit;
          state.vehicleSeatDefaults = previousVehicleSeatDefaults;
          state.vehiclePriceDefaults = previousVehiclePriceDefaults;
          state.availableCurrencies = previousAvailableCurrencies;
          state.vehicleToleranceDefaultMinutes = previousVehicleToleranceDefaultMinutes;
          applyTransportVehicleSeatDefaults(previousVehicleSeatDefaults);
          applyTransportVehicleToleranceDefault(previousVehicleToleranceDefaultMinutes);
          handleProtectedRequestError(error, t("status.couldNotSaveSettings"));
          return null;
        })
        .finally(function () {
          state.settingsSaving = false;
          syncSettingsControls();
        });
    }

    function saveTransportCurrencyOption() {
      const normalizedCurrencyCode = normalizeTransportCurrencyCode(
        settingsNewCurrencyCodeInput ? settingsNewCurrencyCodeInput.value : ""
      );
      const normalizedCurrencyLabel = normalizeTransportCurrencyLabel(
        settingsNewCurrencyLabelInput ? settingsNewCurrencyLabelInput.value : ""
      );

      if (!state.isAuthenticated) {
        setStatus("", "warning", { key: "status.locked" });
        return Promise.resolve(null);
      }

      if (!isValidTransportCurrencyCode(normalizedCurrencyCode)) {
        setStatus("", "warning", { key: "warnings.invalidCurrencyCode" });
        if (settingsNewCurrencyCodeInput && typeof settingsNewCurrencyCodeInput.focus === "function") {
          settingsNewCurrencyCodeInput.focus();
        }
        return Promise.resolve(null);
      }

      state.currencyCreateSaving = true;
      syncSettingsControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/settings/currencies`, {
        method: "POST",
        body: JSON.stringify({
          code: normalizedCurrencyCode,
          display_label: normalizedCurrencyLabel || null,
        }),
      })
        .then(function (response) {
          state.availableCurrencies = resolveTransportCurrencyOptions(
            state.availableCurrencies.concat([response || {}])
          );
          state.priceCurrencyCode = normalizeTransportCurrencyCode(response && response.code);
          closeCurrencyCreatePanel();
          return saveTransportSettings(
            Object.assign({}, readTransportSettingsDraft(), {
              priceCurrencyCode: state.priceCurrencyCode,
            })
          );
        })
        .catch(function (error) {
          handleProtectedRequestError(error, t("status.couldNotAddCurrency"));
          return null;
        })
        .finally(function () {
          state.currencyCreateSaving = false;
          syncSettingsControls();
        });
    }

    function switchTransportLanguage(nextLanguageCode) {
      const resolvedCode = resolveLanguageCode(nextLanguageCode);
      const previousStatusDescriptor = {
        key: state.statusMessageKey,
        values: state.statusMessageValues && typeof state.statusMessageValues === "object"
          ? Object.assign({}, state.statusMessageValues)
          : null,
        message: state.statusMessageText,
        tone: state.statusMessageTone,
      };
      state.languageLoading = true;
      syncSettingsControls();
      setStatus("", "info", { key: "status.switchingLanguage", preserveState: true });

      return new Promise(function (resolve) {
        const finishSwitch = function () {
          setActiveLanguageCode(resolvedCode);
          applyStaticTranslations();
          if (state.dashboard) {
            renderDashboard();
          } else {
            clearDashboard();
          }
          state.languageLoading = false;
          syncSettingsControls();
          syncRouteTimeControls();
          syncStatusMessageCopy(previousStatusDescriptor);
          resolve();
        };

        if (typeof globalScope.requestAnimationFrame === "function") {
          globalScope.requestAnimationFrame(finishSwitch);
          return;
        }

        finishSwitch();
      });
    }

    function verifyTransportCredentials(requestToken, signature) {
      const credentials = readTransportAuthCredentials();
      if (!credentials.signature) {
        return Promise.resolve(null);
      }

      const currentSignature = signature || credentials.signature;
      if (state.isAuthenticated && currentSignature === state.lastVerifiedAuthSignature) {
        return Promise.resolve(null);
      }

      const authVerifyRequestController = typeof globalScope.AbortController === "function"
        ? new globalScope.AbortController()
        : null;
      state.authVerifyRequestController = authVerifyRequestController;

      return requestJson(`${TRANSPORT_API_PREFIX}/auth/verify`, {
        method: "POST",
        body: JSON.stringify({ chave: credentials.chave, senha: credentials.senha }),
        signal: authVerifyRequestController ? authVerifyRequestController.signal : undefined,
      })
        .then(function (response) {
          if (requestToken !== state.authVerifyToken) {
            return null;
          }

          if (response && response.authenticated && response.user) {
            state.lastVerifiedAuthSignature = currentSignature;
            setAuthenticationState(true, response.user, {});
            const structuredAccessGrantedMessage = resolveTransportApiStructuredMessage(response)
              || String(response && response.message || "").trim();
            const accessGrantedMessage = structuredAccessGrantedMessage || t("status.accessGranted");
            const accessGrantedOptions = resolveTransportApiStructuredMessageOptions(response)
              || (structuredAccessGrantedMessage ? undefined : { key: "status.accessGranted" });
            setStatus(accessGrantedMessage, "success", accessGrantedOptions);
            return Promise.all([
              loadDashboard(dateStore.getValue(), { announce: false }),
              loadTransportSettings({ silent: true }),
            ]);
          }

          state.lastVerifiedAuthSignature = "";
          setAuthenticationState(false, null, {});
          const structuredLockedMessage = resolveTransportApiStructuredMessage(response)
            || String(response && response.message || "").trim();
          const lockedMessage = structuredLockedMessage || getTransportLockedMessage();
          const lockedOptions = resolveTransportApiStructuredMessageOptions(response)
            || (structuredLockedMessage ? undefined : { key: "status.locked" });
          setStatus(lockedMessage, "warning", lockedOptions);
          return null;
        })
        .catch(function (error) {
          if (requestToken !== state.authVerifyToken) {
            return null;
          }
          if (error && error.name === "AbortError") {
            return null;
          }
          const structuredVerifyErrorMessage = resolveTransportApiStructuredMessage(error && error.payload)
            || localizeTransportApiMessage(error && error.message);
          const verifyErrorMessage = structuredVerifyErrorMessage || t("status.couldNotVerify");
          const verifyErrorOptions = resolveTransportApiStructuredMessageOptions(error && error.payload)
            || (structuredVerifyErrorMessage ? undefined : { key: "status.couldNotVerify" });
          setStatus(verifyErrorMessage, "error", verifyErrorOptions);
          return null;
        })
        .finally(function () {
          if (state.authVerifyRequestController === authVerifyRequestController) {
            state.authVerifyRequestController = null;
          }
        });
    }

    function scheduleTransportVerification(options) {
      const nextOptions = options || {};
      const verifySource = String(nextOptions.source || "input").trim().toLowerCase();
      const shouldVerifyImmediately = nextOptions.immediate === true;
      clearPendingAuthVerification();
      clearActiveAuthVerificationRequest();
      const credentials = readTransportAuthCredentials();
      const signature = credentials.signature;
      const previousSignature = state.authVerifySignature;
      if (!signature) {
        state.authVerifyToken += 1;
        state.authVerifySignature = "";
        if (!state.isAuthenticated && !state.sessionBootstrapPending) {
          setAuthenticationState(false, null, {});
          setStatus("", "warning", { key: "status.locked" });
        }
        return;
      }

      if (state.isAuthenticated && signature === state.lastVerifiedAuthSignature) {
        state.authVerifySignature = signature;
        return;
      }

      state.authVerifySignature = signature;

      if (state.sessionBootstrapPending && verifySource !== "bootstrap") {
        return;
      }

      if (verifySource === "input" && state.isAuthenticated && !shouldVerifyImmediately) {
        return;
      }

      if (signature === previousSignature && !shouldVerifyImmediately) {
        return;
      }

      state.authVerifyToken += 1;
      const requestToken = state.authVerifyToken;
      state.authVerifyTimer = globalScope.setTimeout(function () {
        state.authVerifyTimer = null;
        verifyTransportCredentials(requestToken, signature);
      }, shouldVerifyImmediately ? 0 : TRANSPORT_AUTH_VERIFY_DELAY_MS);
    }

