
  function renderAiVehicleChanges(options) {
    const renderOptions = options || {};
    const viewModel = buildAiVehicleChangesViewModel(
      renderOptions.runStatusResponse,
      renderOptions.fallbackCurrencyCode
    );
    if (typeof document === "undefined") {
      return viewModel;
    }

    const vehiclesPanelElement = renderOptions.vehiclesPanelElement;
    if (!vehiclesPanelElement) {
      return viewModel;
    }

    clearElement(vehiclesPanelElement);
    if (!viewModel.items.length) {
      vehiclesPanelElement.appendChild(createNode("p", "transport-ai-changes-empty-state", viewModel.emptyMessage));
      return viewModel;
    }

    const listElement = createNode("div", "transport-ai-changes-vehicle-list");
    viewModel.items.forEach(function (item) {
      const itemElement = createNode(
        "article",
        `transport-ai-changes-vehicle-item${item.isSensitive ? " is-sensitive" : ""}`
      );
      const headElement = createNode("div", "transport-ai-changes-vehicle-head");
      const titleBlockElement = createNode("div", "transport-ai-changes-vehicle-title-block");
      titleBlockElement.appendChild(createNode("h4", "transport-ai-changes-vehicle-title", item.titleText));
      titleBlockElement.appendChild(createNode("p", "transport-ai-changes-vehicle-ref", item.subtitleText));
      headElement.appendChild(titleBlockElement);

      const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
      item.badges.forEach(function (badge) {
        badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
      });
      headElement.appendChild(badgeRowElement);
      itemElement.appendChild(headElement);

      const gridElement = createNode("div", "transport-ai-changes-vehicle-grid");
      item.fieldRows.forEach(function (fieldRow) {
        const fieldElement = createNode("div", "transport-ai-changes-vehicle-field");
        fieldElement.appendChild(createNode("span", "transport-ai-changes-summary-label", fieldRow.label));
        fieldElement.appendChild(
          createNode(
            "strong",
            `transport-ai-changes-vehicle-field-value${fieldRow.changed ? " is-changed" : ""}`,
            fieldRow.valueText
          )
        );
        fieldElement.appendChild(createNode("p", "transport-ai-changes-vehicle-field-note", fieldRow.note || item.actionKey));
        gridElement.appendChild(fieldElement);
      });
      itemElement.appendChild(gridElement);
      itemElement.appendChild(createNode("p", "transport-ai-changes-vehicle-rationale", item.rationaleText));
      listElement.appendChild(itemElement);
    });
    vehiclesPanelElement.appendChild(listElement);
    return viewModel;
  }

  function getTransportAiPassengerRequestKindLabel(requestKind) {
    const normalizedRequestKind = String(requestKind || "").trim().toLowerCase();
    return {
      regular: translateTransportAiReviewText("modal.scope.regular", "Regular"),
      weekend: translateTransportAiReviewText("modal.scope.weekend", "Weekend"),
      extra: translateTransportAiReviewText("modal.scope.extra", "Extra"),
    }[normalizedRequestKind] || humanizeTransportAiStatus(normalizedRequestKind, TRANSPORT_AI_SUMMARY_PLACEHOLDER);
  }

  function getTransportAiRouteKindLabel(routeKind) {
    const normalizedRouteKind = String(routeKind || "").trim().toLowerCase();
    return {
      home_to_work: translateTransportAiReviewText("routes.home_to_work", "Home To Work"),
      work_to_home: translateTransportAiReviewText("routes.work_to_home", "Work To Home"),
    }[normalizedRouteKind] || humanizeTransportAiStatus(normalizedRouteKind, TRANSPORT_AI_SUMMARY_PLACEHOLDER);
  }

  function getTransportAiStopTypeLabel(stopType) {
    const normalizedStopType = String(stopType || "").trim().toLowerCase();
    if (Object.prototype.hasOwnProperty.call(TRANSPORT_AI_DYNAMIC_LABELS.stopTypes, normalizedStopType)) {
      return getTransportAiDynamicLabel("stopTypes", normalizedStopType);
    }
    return humanizeTransportAiStatus(normalizedStopType, TRANSPORT_AI_SUMMARY_PLACEHOLDER);
  }

  function resolveTransportAiReferenceTimeFromStops(stops) {
    const stopList = Array.isArray(stops) ? stops : [];
    const timedStop = stopList.find(function (stop) {
      return Boolean(String(stop && stop.scheduled_time || "").trim());
    });
    return timedStop ? String(timedStop.scheduled_time || "").trim() : "";
  }

  function resolveTransportAiItineraryReferenceTime(itinerary) {
    const normalizedItinerary = itinerary && typeof itinerary === "object" ? itinerary : {};
    const serviceScope = String(normalizedItinerary.service_scope || "").trim().toLowerCase();
    const routeKind = String(normalizedItinerary.route_kind || "").trim().toLowerCase();
    if (serviceScope === "extra") {
      if (routeKind === "home_to_work") {
        return String(normalizedItinerary.projected_arrival_time || "").trim();
      }
      if (routeKind === "work_to_home") {
        const firstTimedStop = resolveTransportAiReferenceTimeFromStops(normalizedItinerary.stops);
        return firstTimedStop || String(normalizedItinerary.projected_arrival_time || "").trim();
      }
    }
    return String(normalizedItinerary.projected_arrival_time || "").trim();
  }

  function getTransportAiReferenceFieldLabel(serviceScope, routeKind) {
    const normalizedScope = String(serviceScope || "").trim().toLowerCase();
    const normalizedRouteKind = String(routeKind || "").trim().toLowerCase();
    if (normalizedScope === "extra") {
      if (normalizedRouteKind === "home_to_work") {
        return translateTransportAiReviewText("ai.review.columns.eta", "ETA");
      }
      if (normalizedRouteKind === "work_to_home") {
        return translateTransportAiReviewText("ai.review.columns.etd", "ETD");
      }
      return getTransportAiDynamicLabel("routeFields", "reference");
    }
    return getTransportAiDynamicLabel("routeFields", "arrival");
  }

  function formatTransportAiReferenceValue(serviceScope, routeKind, referenceTime, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const normalizedReferenceTime = normalizeTransportTimeValue(referenceTime, "");
    if (!isValidTransportTimeValue(normalizedReferenceTime)) {
      return normalizedPlaceholder;
    }
    if (String(serviceScope || "").trim().toLowerCase() === "extra") {
      return formatExtraVehicleReferenceLabel(routeKind, normalizedReferenceTime) || normalizedPlaceholder;
    }
    return normalizedReferenceTime;
  }

  function buildTransportAiReferenceFieldNote(serviceScope, routeKind, projectedArrivalTime, placeholder) {
    const normalizedScope = String(serviceScope || "").trim().toLowerCase();
    const normalizedRouteKind = String(routeKind || "").trim().toLowerCase();
    const routeKindLabel = getTransportAiRouteKindLabel(normalizedRouteKind);
    const completionText = formatTransportAiCompactText(projectedArrivalTime, placeholder);
    if (normalizedScope === "extra" && normalizedRouteKind === "work_to_home" && completionText !== placeholder) {
      return translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.routeCompletion, {
        route: routeKindLabel,
        time: completionText,
      });
    }
    return routeKindLabel;
  }

  function findTransportAiItineraryForVehicleAction(action, routeItineraries) {
    const normalizedAction = action && typeof action === "object" ? action : {};
    const normalizedRouteItineraries = Array.isArray(routeItineraries) ? routeItineraries : [];
    const clientVehicleKey = String(normalizedAction.client_vehicle_key || "").trim();
    const vehicleId = Number(normalizedAction.vehicle_id);
    return normalizedRouteItineraries.find(function (itinerary) {
      const itineraryVehicleRef = String(itinerary && itinerary.vehicle_ref || "").trim();
      const itineraryClientVehicleKey = String(itinerary && itinerary.client_vehicle_key || "").trim();
      if (clientVehicleKey && (itineraryVehicleRef === clientVehicleKey || itineraryClientVehicleKey === clientVehicleKey)) {
        return true;
      }
      return Number.isFinite(vehicleId) && Number(itinerary && itinerary.vehicle_id) === vehicleId;
    }) || null;
  }

  function resolveTransportAiVehicleActionRouteKind(action, itinerary, fallbackRouteKind) {
    const normalizedAction = action && typeof action === "object" ? action : {};
    const beforeState = readTransportAiVehicleActionState(normalizedAction.before);
    const afterState = readTransportAiVehicleActionState(normalizedAction.after);
    const candidates = [
      getTransportAiVehicleActionValue(afterState, "route_kind"),
      getTransportAiVehicleActionValue(beforeState, "route_kind"),
      itinerary && itinerary.route_kind,
      fallbackRouteKind,
    ];
    for (const candidate of candidates) {
      const normalizedCandidate = String(candidate || "").trim().toLowerCase();
      if (normalizedCandidate === "home_to_work" || normalizedCandidate === "work_to_home") {
        return normalizedCandidate;
      }
    }
    return "";
  }

  function formatTransportAiClusterAnchorSummary(extraClusters, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const clusterList = Array.isArray(extraClusters) ? extraClusters : [];
    const anchorTimes = clusterList.map(function (cluster) {
      return formatTransportAiCompactText(cluster && cluster.anchor_requested_time, "");
    }).filter(Boolean);
    if (!anchorTimes.length) {
      return normalizedPlaceholder;
    }
    return anchorTimes.join(", ");
  }

  function buildTransportAiAuditClusterRequestText(requestIds, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const requestIdList = Array.isArray(requestIds)
      ? requestIds.filter(function (requestId) {
        return Number.isFinite(Number(requestId)) && Number(requestId) > 0;
      }).map(function (requestId) {
        return `#${Math.max(1, Math.round(Number(requestId)))}`;
      })
      : [];
    if (!requestIdList.length) {
      return normalizedPlaceholder;
    }
    return translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.requestList, {
      requests: requestIdList.join(", "),
    });
  }

  function formatTransportAiDuration(durationSeconds, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const totalSeconds = Number(durationSeconds);
    if (!Number.isFinite(totalSeconds) || totalSeconds < 0) {
      return normalizedPlaceholder;
    }

    const totalMinutes = Math.max(0, Math.round(totalSeconds / 60));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    const hourLabel = translateTransportAiReviewText("ai.review.units.hourShort", "h");
    const minuteLabel = translateTransportAiReviewText("ai.review.units.minuteShort", "min");
    if (hours && minutes) {
      return `${hours}${hourLabel} ${minutes}${minuteLabel === "min" ? "" : " "}${minuteLabel}`;
    }
    if (hours) {
      return `${hours}${hourLabel}`;
    }
    return `${totalMinutes} ${minuteLabel}`;
  }

  function formatTransportAiDistance(distanceMeters, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const totalMeters = Number(distanceMeters);
    if (!Number.isFinite(totalMeters) || totalMeters < 0) {
      return normalizedPlaceholder;
    }

    const kilometerLabel = translateTransportAiReviewText("ai.review.units.kilometerShort", "km");
    const meterLabel = translateTransportAiReviewText("ai.review.units.meterShort", "m");
    if (totalMeters >= 1000) {
      const kilometers = totalMeters / 1000;
      return `${kilometers.toFixed(kilometers >= 10 ? 0 : 1)} ${kilometerLabel}`;
    }
    return `${Math.round(totalMeters)} ${meterLabel}`;
  }

  function buildTransportAiRouteStopTravelText(stop, placeholder) {
    const normalizedStop = stop && typeof stop === "object" ? stop : {};
    const travelParts = [];
    const durationText = formatTransportAiDuration(
      normalizedStop.duration_from_previous_seconds,
      placeholder
    );
    const distanceText = formatTransportAiDistance(
      normalizedStop.distance_from_previous_meters,
      placeholder
    );
    if (durationText !== placeholder) {
      travelParts.push(durationText);
    }
    if (distanceText !== placeholder) {
      travelParts.push(distanceText);
    }
    return travelParts.length
      ? translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.fromPrevious, {
        segments: travelParts.join(" · "),
      })
      : placeholder;
  }

  function buildAiPassengerAllocationsViewModel(runStatusResponse) {
    const placeholder = TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const response = runStatusResponse && typeof runStatusResponse === "object" ? runStatusResponse : {};
    const suggestion = response.suggestion && typeof response.suggestion === "object" ? response.suggestion : {};
    const plan = suggestion.plan && typeof suggestion.plan === "object" ? suggestion.plan : {};
    const passengerAllocations = Array.isArray(plan.passenger_allocations)
      ? plan.passenger_allocations.filter(Boolean)
      : [];
    const routeItineraries = Array.isArray(plan.route_itineraries)
      ? plan.route_itineraries.filter(Boolean)
      : [];
    const validationIssues = Array.isArray(plan.validation_issues)
      ? plan.validation_issues.filter(Boolean)
      : [];
    const itineraryByVehicleRef = routeItineraries.reduce(function (collection, itinerary) {
      const vehicleRef = String(itinerary && itinerary.vehicle_ref || "").trim();
      if (vehicleRef) {
        collection[vehicleRef] = itinerary;
      }
      return collection;
    }, {});
    const allocatedRequestIds = buildTransportAiAllocatedRequestIdSet(passengerAllocations);
    const passengerFieldLabels = {
      project: getTransportAiDynamicLabel("passengerFields", "project"),
      requestKind: getTransportAiDynamicLabel("passengerFields", "requestKind"),
      vehicle: getTransportAiDynamicLabel("passengerFields", "vehicle"),
      pickupOrder: getTransportAiDynamicLabel("passengerFields", "pickupOrder"),
      pickup: getTransportAiDynamicLabel("passengerFields", "pickup"),
      arrival: getTransportAiDynamicLabel("passengerFields", "arrival"),
    };
    const pendingRequestTitle = translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.pendingRequest);
    const needsReviewBadgeText = translateTransportAiReviewText(
      "ai.review.exceptions.badges.needsReview",
      "Needs Review"
    );
    const notRoutedBadgeText = translateTransportAiReviewText(
      "ai.review.exceptions.badges.notRouted",
      "Not Routed"
    );
    const items = passengerAllocations.slice().sort(function (leftItem, rightItem) {
      const leftPickupTime = String(leftItem && leftItem.scheduled_pickup_time || "").trim();
      const rightPickupTime = String(rightItem && rightItem.scheduled_pickup_time || "").trim();
      if (leftPickupTime !== rightPickupTime) {
        return leftPickupTime.localeCompare(rightPickupTime);
      }
      const leftPickupOrder = Number(leftItem && leftItem.pickup_order);
      const rightPickupOrder = Number(rightItem && rightItem.pickup_order);
      if (leftPickupOrder !== rightPickupOrder) {
        return leftPickupOrder - rightPickupOrder;
      }
      return Number(leftItem && leftItem.request_id) - Number(rightItem && rightItem.request_id);
    }).map(function (allocation) {
      const requestId = Number.isFinite(Number(allocation.request_id))
        ? Math.max(0, Math.round(Number(allocation.request_id)))
        : null;
      const itinerary = itineraryByVehicleRef[String(allocation.vehicle_ref || "").trim()] || null;
      const vehicleText = formatTransportAiVehicleIdentifier(
        itinerary && (itinerary.plate || itinerary.client_vehicle_key || itinerary.vehicle_ref)
          ? itinerary.plate || itinerary.client_vehicle_key || itinerary.vehicle_ref
          : allocation.vehicle_ref,
        placeholder
      );
      const projectName = formatTransportAiCompactText(allocation.project_name, placeholder);
      const requestKindLabel = getTransportAiPassengerRequestKindLabel(allocation.request_kind);
      const routeKindLabel = getTransportAiRouteKindLabel(allocation.route_kind);
      const pickupOrder = Number.isFinite(Number(allocation.pickup_order))
        ? Math.max(0, Math.round(Number(allocation.pickup_order))) + 1
        : null;

      return {
        requestId,
        titleText: formatTransportAiCompactText(allocation.nome, placeholder),
        subtitleText: formatTransportAiCompactText(
          [projectName, formatTransportAiCompactText(allocation.chave, "")].filter(Boolean).join(" · "),
          placeholder
        ),
        rationaleText: formatTransportAiCompactText(allocation.rationale, placeholder),
        badges: [
          { text: requestKindLabel, tone: "neutral" },
          { text: routeKindLabel, tone: "info" },
        ],
        fieldRows: [
          {
            label: passengerFieldLabels.project,
            valueText: projectName,
            note: formatTransportAiRequestReference(requestId, placeholder),
          },
          {
            label: passengerFieldLabels.requestKind,
            valueText: requestKindLabel,
            note: routeKindLabel,
          },
          {
            label: passengerFieldLabels.vehicle,
            valueText: vehicleText,
            note: formatTransportAiCompactText(allocation.vehicle_ref, placeholder),
          },
          {
            label: passengerFieldLabels.pickupOrder,
            valueText: pickupOrder === null ? placeholder : `#${pickupOrder}`,
            note: itinerary && itinerary.route_key
              ? formatTransportAiCompactText(itinerary.route_key, placeholder)
              : placeholder,
          },
          {
            label: passengerFieldLabels.pickup,
            valueText: formatTransportAiCompactText(allocation.scheduled_pickup_time, placeholder),
            note: formatTransportAiCompactText(allocation.service_date, placeholder),
          },
          {
            label: passengerFieldLabels.arrival,
            valueText: formatTransportAiCompactText(allocation.projected_arrival_time, placeholder),
            note: itinerary && itinerary.project_name
              ? formatTransportAiCompactText(itinerary.project_name, placeholder)
              : projectName,
          },
        ],
      };
    });

    const unallocatedItems = validationIssues.filter(function (issue) {
      const requestId = Number(issue && issue.request_id);
      return Number.isFinite(requestId) && !allocatedRequestIds.has(Math.max(0, Math.round(requestId)));
    }).map(function (issue) {
      const requestId = Number.isFinite(Number(issue.request_id))
        ? Math.max(0, Math.round(Number(issue.request_id)))
        : null;
      return {
        requestId,
        titleText: formatTransportAiRequestReference(requestId, pendingRequestTitle),
        subtitleText: formatTransportAiCompactText(issue.code, placeholder),
        messageText: formatTransportAiCompactText(issue.message, placeholder),
        badges: [
          {
            text: issue.blocking === false ? needsReviewBadgeText : notRoutedBadgeText,
            tone: issue.blocking === false ? "warning" : "error",
          },
        ],
      };
    });

    return {
      placeholder,
      emptyMessage: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.passengerAllocationsEmpty),
      allocatedTitle: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.allocatedPassengersTitle),
      unallocatedTitle: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.unallocatedPassengersTitle),
      items,
      unallocatedItems,
    };
  }

  function renderAiPassengerAllocations(options) {
    const renderOptions = options || {};
    const viewModel = buildAiPassengerAllocationsViewModel(renderOptions.runStatusResponse);
    if (typeof document === "undefined") {
      return viewModel;
    }

    const passengersPanelElement = renderOptions.passengersPanelElement;
    if (!passengersPanelElement) {
      return viewModel;
    }

    clearElement(passengersPanelElement);
    if (!viewModel.items.length && !viewModel.unallocatedItems.length) {
      passengersPanelElement.appendChild(createNode("p", "transport-ai-changes-empty-state", viewModel.emptyMessage));
      return viewModel;
    }

    const sectionListElement = createNode("div", "transport-ai-changes-passenger-sections");
    if (viewModel.items.length) {
      const allocatedSectionElement = createNode("section", "transport-ai-changes-passenger-section");
      allocatedSectionElement.appendChild(
        createNode("h4", "transport-ai-changes-panel-subtitle", viewModel.allocatedTitle)
      );
      const allocatedListElement = createNode("div", "transport-ai-changes-passenger-list");
      viewModel.items.forEach(function (item) {
        const itemElement = createNode("article", "transport-ai-changes-passenger-item");
        const headElement = createNode("div", "transport-ai-changes-passenger-head");
        const titleBlockElement = createNode("div", "transport-ai-changes-passenger-title-block");
        titleBlockElement.appendChild(createNode("h4", "transport-ai-changes-passenger-title", item.titleText));
        titleBlockElement.appendChild(createNode("p", "transport-ai-changes-passenger-ref", item.subtitleText));
        headElement.appendChild(titleBlockElement);

        const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
        item.badges.forEach(function (badge) {
          badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
        });
        headElement.appendChild(badgeRowElement);
        itemElement.appendChild(headElement);

        const gridElement = createNode("div", "transport-ai-changes-passenger-grid");
        item.fieldRows.forEach(function (fieldRow) {
          const fieldElement = createNode("div", "transport-ai-changes-passenger-field");
          fieldElement.appendChild(createNode("span", "transport-ai-changes-summary-label", fieldRow.label));
          fieldElement.appendChild(createNode("strong", "transport-ai-changes-passenger-field-value", fieldRow.valueText));
          fieldElement.appendChild(createNode("p", "transport-ai-changes-passenger-field-note", fieldRow.note));
          gridElement.appendChild(fieldElement);
        });
        itemElement.appendChild(gridElement);
        itemElement.appendChild(createNode("p", "transport-ai-changes-passenger-rationale", item.rationaleText));
        allocatedListElement.appendChild(itemElement);
      });
      allocatedSectionElement.appendChild(allocatedListElement);
      sectionListElement.appendChild(allocatedSectionElement);
    }

    if (viewModel.unallocatedItems.length) {
      const unallocatedSectionElement = createNode("section", "transport-ai-changes-passenger-section");
      unallocatedSectionElement.appendChild(
        createNode("h4", "transport-ai-changes-panel-subtitle", viewModel.unallocatedTitle)
      );
      const unallocatedListElement = createNode("div", "transport-ai-changes-passenger-list");
      viewModel.unallocatedItems.forEach(function (item) {
        const itemElement = createNode("article", "transport-ai-changes-passenger-item is-unallocated");
        const headElement = createNode("div", "transport-ai-changes-passenger-head");
        const titleBlockElement = createNode("div", "transport-ai-changes-passenger-title-block");
        titleBlockElement.appendChild(createNode("h4", "transport-ai-changes-passenger-title", item.titleText));
        titleBlockElement.appendChild(createNode("p", "transport-ai-changes-passenger-ref", item.subtitleText));
        headElement.appendChild(titleBlockElement);

        const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
        item.badges.forEach(function (badge) {
          badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
        });
        headElement.appendChild(badgeRowElement);
        itemElement.appendChild(headElement);
        itemElement.appendChild(createNode("p", "transport-ai-changes-passenger-rationale", item.messageText));
        unallocatedListElement.appendChild(itemElement);
      });
      unallocatedSectionElement.appendChild(unallocatedListElement);
      sectionListElement.appendChild(unallocatedSectionElement);
    }

    passengersPanelElement.appendChild(sectionListElement);
    return viewModel;
  }

  function buildAiRouteItinerariesViewModel(runStatusResponse, fallbackCurrencyCode) {
    const placeholder = TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const response = runStatusResponse && typeof runStatusResponse === "object" ? runStatusResponse : {};
    const suggestion = response.suggestion && typeof response.suggestion === "object" ? response.suggestion : {};
    const plan = suggestion.plan && typeof suggestion.plan === "object" ? suggestion.plan : {};
    const routeItineraries = Array.isArray(plan.route_itineraries)
      ? plan.route_itineraries.filter(Boolean)
      : [];
    const priceCurrencyCode = normalizeTransportCurrencyCode(
      (plan.cost_summary && plan.cost_summary.price_currency_code)
      || fallbackCurrencyCode
    );
    const routeFieldLabels = {
      project: getTransportAiDynamicLabel("routeFields", "project"),
      duration: getTransportAiDynamicLabel("routeFields", "duration"),
      cost: getTransportAiDynamicLabel("routeFields", "cost"),
    };
    const items = routeItineraries.slice().sort(function (leftItem, rightItem) {
      const leftArrival = String(leftItem && leftItem.projected_arrival_time || "").trim();
      const rightArrival = String(rightItem && rightItem.projected_arrival_time || "").trim();
      if (leftArrival !== rightArrival) {
        return leftArrival.localeCompare(rightArrival);
      }
      return String(leftItem && leftItem.route_key || "").localeCompare(String(rightItem && rightItem.route_key || ""));
    }).map(function (itinerary) {
      const vehicleTitle = formatTransportAiVehicleIdentifier(
        itinerary.plate || itinerary.client_vehicle_key || itinerary.vehicle_ref,
        placeholder
      );
      const referenceTime = resolveTransportAiItineraryReferenceTime(itinerary);
      const referenceLabel = getTransportAiReferenceFieldLabel(itinerary.service_scope, itinerary.route_kind);
      const referenceValueText = formatTransportAiReferenceValue(
        itinerary.service_scope,
        itinerary.route_kind,
        referenceTime,
        placeholder
      );
      const referenceNoteText = buildTransportAiReferenceFieldNote(
        itinerary.service_scope,
        itinerary.route_kind,
        itinerary.projected_arrival_time,
        placeholder
      );
      const stops = (Array.isArray(itinerary.stops) ? itinerary.stops : []).slice().sort(function (leftStop, rightStop) {
        return Number(leftStop && leftStop.stop_order) - Number(rightStop && rightStop.stop_order);
      }).map(function (stop) {
        const stopAddress = formatTransportAiCompactText(stop.address, placeholder);
        const stopZipCode = formatTransportAiCompactText(stop.zip_code, placeholder);
        return {
          stopOrder: Number.isFinite(Number(stop.stop_order)) ? Math.max(0, Math.round(Number(stop.stop_order))) : null,
          stopType: String(stop.stop_type || "").trim().toLowerCase(),
          stopTypeLabel: getTransportAiStopTypeLabel(stop.stop_type),
          scheduledTimeText: formatTransportAiCompactText(stop.scheduled_time, placeholder),
          titleText: formatTransportAiCompactText(
            stop.stop_type === "destination" ? stop.project_name : stop.passenger_name,
            placeholder
          ),
          subtitleText: formatTransportAiCompactText(`${stopAddress} · ${stopZipCode}`, placeholder),
          metaText: formatTransportAiCompactText(
            [stop.project_name, stop.country_code].filter(Boolean).join(" · "),
            placeholder
          ),
          travelText: buildTransportAiRouteStopTravelText(stop, placeholder),
          isDestination: String(stop.stop_type || "").trim().toLowerCase() === "destination",
        };
      });

      return {
        routeKey: formatTransportAiCompactText(itinerary.route_key, placeholder),
        titleText: vehicleTitle,
        subtitleText: formatTransportAiCompactText(
          [itinerary.project_name, itinerary.country_name || itinerary.country_code].filter(Boolean).join(" · "),
          placeholder
        ),
        badges: [
          { text: getTransportAiVehicleScopeLabel(itinerary.service_scope), tone: "neutral" },
          { text: getTransportAiVehicleTypeLabel(itinerary.vehicle_type), tone: "info" },
        ],
        fieldRows: [
          {
            label: routeFieldLabels.project,
            valueText: formatTransportAiCompactText(itinerary.project_name, placeholder),
            note: formatTransportAiCompactText(itinerary.partition_key, placeholder),
          },
          {
            label: referenceLabel,
            valueText: referenceValueText,
            note: referenceNoteText,
          },
          {
            label: routeFieldLabels.duration,
            valueText: formatTransportAiDuration(itinerary.total_duration_seconds, placeholder),
            note: formatTransportAiDistance(itinerary.total_distance_meters, placeholder),
          },
          {
            label: routeFieldLabels.cost,
            valueText: formatTransportCurrencyAmount(itinerary.estimated_cost, priceCurrencyCode, { placeholder }),
            note: formatTransportAiCompactText(itinerary.vehicle_ref, placeholder),
          },
        ],
        stopItems: stops,
      };
    });

    return {
      placeholder,
      emptyMessage: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.routeItinerariesEmpty),
      emptyStopsMessage: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.routeStopsEmpty),
      items,
    };
  }

  function renderAiRouteItineraries(options) {
    const renderOptions = options || {};
    const viewModel = buildAiRouteItinerariesViewModel(
      renderOptions.runStatusResponse,
      renderOptions.fallbackCurrencyCode
    );
    if (typeof document === "undefined") {
      return viewModel;
    }

    const routesPanelElement = renderOptions.routesPanelElement;
    if (!routesPanelElement) {
      return viewModel;
    }

    clearElement(routesPanelElement);
    if (!viewModel.items.length) {
      routesPanelElement.appendChild(createNode("p", "transport-ai-changes-empty-state", viewModel.emptyMessage));
      return viewModel;
    }

    const listElement = createNode("div", "transport-ai-changes-route-list");
    viewModel.items.forEach(function (item) {
      const itemElement = createNode("article", "transport-ai-changes-route-item");
      const headElement = createNode("div", "transport-ai-changes-route-head");
      const titleBlockElement = createNode("div", "transport-ai-changes-route-title-block");
      titleBlockElement.appendChild(createNode("h4", "transport-ai-changes-route-title", item.titleText));
      titleBlockElement.appendChild(createNode("p", "transport-ai-changes-route-ref", item.subtitleText));
      headElement.appendChild(titleBlockElement);

      const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
      item.badges.forEach(function (badge) {
        badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
      });
      headElement.appendChild(badgeRowElement);
      itemElement.appendChild(headElement);

      const gridElement = createNode("div", "transport-ai-changes-route-grid");
      item.fieldRows.forEach(function (fieldRow) {
        const fieldElement = createNode("div", "transport-ai-changes-route-field");
        fieldElement.appendChild(createNode("span", "transport-ai-changes-summary-label", fieldRow.label));
        fieldElement.appendChild(createNode("strong", "transport-ai-changes-route-field-value", fieldRow.valueText));
        fieldElement.appendChild(createNode("p", "transport-ai-changes-route-field-note", fieldRow.note));
        gridElement.appendChild(fieldElement);
      });
      itemElement.appendChild(gridElement);

      if (!item.stopItems.length) {
        itemElement.appendChild(createNode("p", "transport-ai-changes-route-empty-stops", viewModel.emptyStopsMessage));
      } else {
        const stopListElement = createNode("ol", "transport-ai-changes-stop-list");
        item.stopItems.forEach(function (stopItem) {
          const stopElement = createNode(
            "li",
            `transport-ai-changes-stop-item${stopItem.isDestination ? " is-destination" : ""}`
          );
          stopElement.appendChild(createNode(
            "span",
            "transport-ai-changes-stop-order",
            stopItem.stopOrder === null ? "--" : String(stopItem.stopOrder + 1)
          ));

          const contentElement = createNode("div", "transport-ai-changes-stop-content");
          const topElement = createNode("div", "transport-ai-changes-stop-top");
          topElement.appendChild(createNode("strong", "transport-ai-changes-stop-time", stopItem.scheduledTimeText));
          topElement.appendChild(createAiChangesBadgeElement({
            text: stopItem.stopTypeLabel,
            tone: stopItem.isDestination ? "success" : "neutral",
          }));
          contentElement.appendChild(topElement);
          contentElement.appendChild(createNode("h5", "transport-ai-changes-stop-title", stopItem.titleText));
          contentElement.appendChild(createNode("p", "transport-ai-changes-stop-subtitle", stopItem.subtitleText));
          contentElement.appendChild(createNode("p", "transport-ai-changes-stop-meta", stopItem.metaText));
          contentElement.appendChild(createNode("p", "transport-ai-changes-stop-travel", stopItem.travelText));
          stopElement.appendChild(contentElement);
          stopListElement.appendChild(stopElement);
        });
        itemElement.appendChild(stopListElement);
      }

      listElement.appendChild(itemElement);
    });
    routesPanelElement.appendChild(listElement);
    return viewModel;
  }

  function buildAiChangesAuditViewModel(runStatusResponse) {
    const placeholder = TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const response = runStatusResponse && typeof runStatusResponse === "object" ? runStatusResponse : {};
    const suggestion = response.suggestion && typeof response.suggestion === "object" ? response.suggestion : {};
    const audit = suggestion.audit && typeof suggestion.audit === "object" ? suggestion.audit : {};
    const extraClusters = Array.isArray(audit.extra_clusters) ? audit.extra_clusters.filter(Boolean) : [];
    const extraToleranceNumber = Number(audit.extra_car_tolerance_minutes);
    const extraToleranceText = Number.isFinite(extraToleranceNumber) && extraToleranceNumber >= 0
      ? `${Math.round(extraToleranceNumber)} min`
      : placeholder;
    const planningInputHashText = formatTransportAiCompactText(audit.planning_input_hash, placeholder);
    const promptVersionText = formatTransportAiCompactText(suggestion.prompt_version, placeholder);
    const routeProviderText = formatTransportAiCompactText(response.route_provider || suggestion.route_provider, placeholder);
    const llmProviderText = formatTransportAiCompactText(response.llm_provider, placeholder);
    const modelText = formatTransportAiCompactText(response.openai_model || response.llm_model, placeholder);
    const reasoningText = formatTransportAiCompactText(response.llm_reasoning_effort, placeholder);
    const routeKindText = response.route_kind ? getRouteKindLabel(response.route_kind) : placeholder;
    const auditSummaryLabels = {
      promptVersion: getTransportAiDynamicLabel("auditFields", "promptVersion"),
      routeProvider: getTransportAiDynamicLabel("auditFields", "routeProvider"),
      model: getTransportAiDynamicLabel("auditFields", "model"),
      planningInput: getTransportAiDynamicLabel("auditFields", "planningInput"),
    };
    const clusterItems = extraClusters.map(function (cluster) {
      const requestIds = Array.isArray(cluster.request_ids) ? cluster.request_ids : [];
      const requestCount = Number.isFinite(Number(cluster.request_count)) && Number(cluster.request_count) > 0
        ? Math.max(1, Math.round(Number(cluster.request_count)))
        : requestIds.length;
      const anchorText = formatTransportAiCompactText(cluster.anchor_requested_time, placeholder);
      return {
        titleText: formatTransportAiCompactText(cluster.cluster_key, placeholder),
        subtitleText: formatTransportAiCompactText(cluster.partition_key, placeholder),
        badges: [
          {
            text: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.anchorBadge, {
              time: anchorText === placeholder ? placeholder : `${anchorText}h`,
            }),
            tone: "info",
          },
          {
            text: formatTransportAiCountText(requestCount, "request", placeholder),
            tone: "neutral",
          },
        ],
        windowText: formatTransportAiTimeWindow(
          cluster.earliest_requested_time,
          cluster.latest_requested_time,
          placeholder
        ),
        requestText: buildTransportAiAuditClusterRequestText(requestIds, placeholder),
      };
    });

    return {
      placeholder,
      summaryItems: [
        {
          label: auditSummaryLabels.promptVersion,
          valueText: promptVersionText,
          note: routeKindText,
        },
        {
          label: auditSummaryLabels.routeProvider,
          valueText: routeProviderText,
          note: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.llm, { provider: llmProviderText }),
        },
        {
          label: auditSummaryLabels.model,
          valueText: modelText,
          note: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.reasoning, { effort: reasoningText }),
        },
        {
          label: auditSummaryLabels.planningInput,
          valueText: planningInputHashText,
          note: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.extraTolerance, {
            duration: extraToleranceText,
          }),
        },
      ],
      clusterItems,
      emptyClusterMessage: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.auditEmptyClusters),
    };
  }

  function renderAiChangesAudit(options) {
    const renderOptions = options || {};
    const viewModel = buildAiChangesAuditViewModel(renderOptions.runStatusResponse);
    if (typeof document === "undefined") {
      return viewModel;
    }

    const auditPanelElement = renderOptions.auditPanelElement;
    if (!auditPanelElement) {
      return viewModel;
    }

    clearElement(auditPanelElement);

    const sectionsElement = createNode("div", "transport-ai-changes-audit-sections");
    const summaryGridElement = createNode("div", "transport-ai-changes-executive-grid");
    viewModel.summaryItems.forEach(function (item) {
      const itemElement = createNode("article", "transport-ai-changes-executive-item");
      itemElement.appendChild(createNode("span", "transport-ai-changes-summary-label", item.label));
      itemElement.appendChild(createNode("strong", "transport-ai-changes-executive-value", item.valueText));
      itemElement.appendChild(createNode("p", "transport-ai-changes-executive-note", item.note));
      summaryGridElement.appendChild(itemElement);
    });
    sectionsElement.appendChild(summaryGridElement);

    const clusterSectionElement = createNode("section", "transport-ai-changes-audit-section");
    clusterSectionElement.appendChild(createNode(
      "h4",
      "transport-ai-changes-panel-subtitle",
      translateTransportAiReviewText("ai.review.extraTemporalClusters", "Extra Temporal Clusters")
    ));
    if (!viewModel.clusterItems.length) {
      clusterSectionElement.appendChild(createNode("p", "transport-ai-changes-empty-state", viewModel.emptyClusterMessage));
    } else {
      const clusterListElement = createNode("div", "transport-ai-changes-audit-cluster-list");
      viewModel.clusterItems.forEach(function (item) {
        const itemElement = createNode("article", "transport-ai-changes-audit-cluster");
        const headElement = createNode("div", "transport-ai-changes-audit-head");
        const titleBlockElement = createNode("div", "transport-ai-changes-route-title-block");
        titleBlockElement.appendChild(createNode("h5", "transport-ai-changes-route-title", item.titleText));
        titleBlockElement.appendChild(createNode("p", "transport-ai-changes-route-ref", item.subtitleText));
        headElement.appendChild(titleBlockElement);
        const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
        item.badges.forEach(function (badge) {
          badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
        });
        headElement.appendChild(badgeRowElement);
        itemElement.appendChild(headElement);
        itemElement.appendChild(createNode(
          "p",
          "transport-ai-changes-audit-meta",
          translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.window, { window: item.windowText })
        ));
        itemElement.appendChild(createNode("p", "transport-ai-changes-audit-meta", item.requestText));
        clusterListElement.appendChild(itemElement);
      });
      clusterSectionElement.appendChild(clusterListElement);
    }
    sectionsElement.appendChild(clusterSectionElement);

    auditPanelElement.appendChild(sectionsElement);
    return viewModel;
  }

  function renderAiChangesSummary(options) {
    const renderOptions = options || {};
    const viewModel = buildAiChangesSummaryViewModel(
      renderOptions.runStatusResponse,
      renderOptions.fallbackCurrencyCode
    );
    if (typeof document === "undefined") {
      return viewModel;
    }

    const summaryGridElement = renderOptions.summaryGridElement;
    const summaryPanelElement = renderOptions.summaryPanelElement;

    if (summaryGridElement) {
      clearElement(summaryGridElement);
      summaryGridElement.hidden = true;
    }

    if (summaryPanelElement) {
      clearElement(summaryPanelElement);
      summaryPanelElement.appendChild(createNode("p", "transport-ai-changes-objective-summary", viewModel.objectiveSummary));

      if (viewModel.statusBadges.length) {
        const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
        viewModel.statusBadges.forEach(function (badge) {
          badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
        });
        summaryPanelElement.appendChild(badgeRowElement);
      }

      const reviewWorkspaceElement = createNode("div", "transport-ai-review-workspace");
      reviewWorkspaceElement.dataset.aiReviewWorkspace = "primary";

      const vehicleTableListElement = createNode("div", "transport-ai-review-vehicle-table-list");
      vehicleTableListElement.dataset.aiReviewVehicleTableList = "";
      if (!viewModel.review.items.length) {
        vehicleTableListElement.appendChild(createNode("p", "transport-ai-changes-empty-state", viewModel.review.emptyMessage));
      } else {
        viewModel.review.items.forEach(function (reviewItem) {
          vehicleTableListElement.appendChild(createTransportAiReviewTableElement(reviewItem, viewModel.review.columns));
        });
      }
      reviewWorkspaceElement.appendChild(vehicleTableListElement);

      if (viewModel.review.exceptions && viewModel.review.exceptions.items.length) {
        reviewWorkspaceElement.appendChild(createTransportAiReviewExceptionsElement(viewModel.review.exceptions));
      }

      reviewWorkspaceElement.appendChild(createTransportAiManagementTableElement(viewModel.review.management));
      summaryPanelElement.appendChild(reviewWorkspaceElement);
    }

    return viewModel;
  }
