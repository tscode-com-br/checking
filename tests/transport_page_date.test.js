const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const transportPage = require('../sistema/app/static/transport/app.js');

function loadTransportPageWithI18n() {
  const appModulePath = require.resolve('../sistema/app/static/transport/app.js');
  const i18nModulePath = require.resolve('../sistema/app/static/transport/i18n.js');

  delete global.CheckingTransportI18n;
  delete global.CheckingTransportPage;
  delete global.CheckingTransportPageController;
  delete require.cache[appModulePath];
  delete require.cache[i18nModulePath];

  require(i18nModulePath);
  return require(appModulePath);
}

function toDatasetKey(attributeName) {
  return String(attributeName || '')
    .replace(/^data-/, '')
    .split('-')
    .filter(Boolean)
    .map((segment, index) => {
      if (index === 0) {
        return segment;
      }
      return `${segment.charAt(0).toUpperCase()}${segment.slice(1)}`;
    })
    .join('');
}

function toDataAttributeName(datasetKey) {
  return `data-${String(datasetKey || '').replace(/[A-Z]/g, (match) => `-${match.toLowerCase()}`)}`;
}

function createFakeEvent(type, properties) {
  return Object.assign(
    {
      type,
      defaultPrevented: false,
      propagationStopped: false,
      preventDefault() {
        this.defaultPrevented = true;
      },
      stopPropagation() {
        this.propagationStopped = true;
      },
    },
    properties || {}
  );
}

function parseAttributeSelector(selector) {
  const match = String(selector || '').trim().match(/^\[([^=\]]+)(?:=(?:"([^"]*)"|'([^']*)'|([^\]]+)))?\]$/);
  if (!match) {
    return null;
  }

  return {
    name: match[1],
    value: match[2] ?? match[3] ?? match[4] ?? null,
  };
}

function matchesSingleSelector(element, selector) {
  const normalizedSelector = String(selector || '').trim();
  if (!normalizedSelector || !element || typeof element.tagName !== 'string') {
    return false;
  }

  if (normalizedSelector.startsWith('#')) {
    return String(element.id || '') === normalizedSelector.slice(1);
  }

  if (normalizedSelector.startsWith('.')) {
    return normalizedSelector
      .split('.')
      .filter(Boolean)
      .every((className) => element.classList.contains(className));
  }

  if (normalizedSelector.startsWith('[')) {
    const parsedSelector = parseAttributeSelector(normalizedSelector);
    if (!parsedSelector) {
      return false;
    }
    if (!element.hasAttribute(parsedSelector.name)) {
      return false;
    }
    if (parsedSelector.value === null) {
      return true;
    }
    return String(element.getAttribute(parsedSelector.name) || '') === parsedSelector.value;
  }

  const tagAndAttributeMatch = normalizedSelector.match(/^([a-z0-9_-]+)(\[.+\])$/i);
  if (tagAndAttributeMatch) {
    return element.tagName.toLowerCase() === tagAndAttributeMatch[1].toLowerCase()
      && matchesSingleSelector(element, tagAndAttributeMatch[2]);
  }

  const tagAndClassMatch = normalizedSelector.match(/^([a-z0-9_-]+)(\.[a-z0-9_-]+)+$/i);
  if (tagAndClassMatch) {
    return element.tagName.toLowerCase() === tagAndClassMatch[1].toLowerCase()
      && tagAndClassMatch[2]
        .split('.')
        .filter(Boolean)
        .every((className) => element.classList.contains(className));
  }

  return element.tagName.toLowerCase() === normalizedSelector.toLowerCase();
}

function matchesSelector(element, selector) {
  const normalizedSelector = String(selector || '').trim();
  if (!normalizedSelector) {
    return false;
  }

  if (!normalizedSelector.includes(' ')) {
    return matchesSingleSelector(element, normalizedSelector);
  }

  const selectorParts = normalizedSelector.split(/\s+/).filter(Boolean);
  if (!selectorParts.length || !matchesSingleSelector(element, selectorParts[selectorParts.length - 1])) {
    return false;
  }

  let ancestor = element.parentNode;
  for (let index = selectorParts.length - 2; index >= 0; index -= 1) {
    while (ancestor && !matchesSingleSelector(ancestor, selectorParts[index])) {
      ancestor = ancestor.parentNode;
    }
    if (!ancestor) {
      return false;
    }
    ancestor = ancestor.parentNode;
  }

  return true;
}

function collectMatchingElements(rootNodes, selector) {
  const matches = [];

  function visit(node) {
    if (!node || typeof node.tagName !== 'string') {
      return;
    }

    if (matchesSelector(node, selector)) {
      matches.push(node);
    }

    node.childNodes.forEach(visit);
  }

  rootNodes.forEach(visit);
  return matches;
}

class FakeEventTarget {
  constructor() {
    this.listeners = new Map();
  }

  addEventListener(type, listener) {
    if (typeof listener !== 'function') {
      return;
    }
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type).push(listener);
  }

  removeEventListener(type, listener) {
    if (!this.listeners.has(type)) {
      return;
    }
    this.listeners.set(
      type,
      this.listeners.get(type).filter((registeredListener) => registeredListener !== listener)
    );
  }

  dispatchEvent(event) {
    const nextEvent = event || createFakeEvent('event');
    if (!nextEvent.target) {
      nextEvent.target = this;
    }
    nextEvent.currentTarget = this;
    const registeredListeners = this.listeners.has(nextEvent.type)
      ? Array.from(this.listeners.get(nextEvent.type))
      : [];
    registeredListeners.forEach((listener) => {
      listener.call(this, nextEvent);
    });
    return !nextEvent.defaultPrevented;
  }
}

class FakeClassList {
  constructor(element) {
    this.element = element;
    this.tokens = new Set();
  }

  syncFromString(value) {
    this.tokens = new Set(String(value || '').split(/\s+/).filter(Boolean));
    this.syncElement();
  }

  syncElement() {
    this.element._className = Array.from(this.tokens).join(' ');
    if (this.element._className) {
      this.element.attributes.set('class', this.element._className);
      return;
    }
    this.element.attributes.delete('class');
  }

  add(...tokens) {
    tokens.filter(Boolean).forEach((token) => {
      this.tokens.add(String(token));
    });
    this.syncElement();
  }

  remove(...tokens) {
    tokens.filter(Boolean).forEach((token) => {
      this.tokens.delete(String(token));
    });
    this.syncElement();
  }

  contains(token) {
    return this.tokens.has(String(token));
  }

  toggle(token, force) {
    const normalizedToken = String(token);
    if (force === true) {
      this.tokens.add(normalizedToken);
      this.syncElement();
      return true;
    }
    if (force === false) {
      this.tokens.delete(normalizedToken);
      this.syncElement();
      return false;
    }
    if (this.tokens.has(normalizedToken)) {
      this.tokens.delete(normalizedToken);
      this.syncElement();
      return false;
    }
    this.tokens.add(normalizedToken);
    this.syncElement();
    return true;
  }
}

class FakeElement extends FakeEventTarget {
  constructor(tagName, ownerDocument) {
    super();
    this.tagName = String(tagName || 'div').toUpperCase();
    this.ownerDocument = ownerDocument || null;
    this.parentNode = null;
    this.childNodes = [];
    this.attributes = new Map();
    this._datasetStore = {};
    this.dataset = new Proxy(this._datasetStore, {
      get: (target, property) => target[property],
      set: (target, property, value) => {
        const normalizedValue = String(value);
        target[property] = normalizedValue;
        this.attributes.set(toDataAttributeName(property), normalizedValue);
        return true;
      },
      deleteProperty: (target, property) => {
        delete target[property];
        this.attributes.delete(toDataAttributeName(property));
        return true;
      },
    });
    this.style = {
      setProperty(name, value) {
        this[name] = value;
      },
      removeProperty(name) {
        delete this[name];
      },
    };
    this.hidden = false;
    this.disabled = false;
    this.value = '';
    this.checked = false;
    this.type = '';
    this.id = '';
    this.title = '';
    this.tabIndex = 0;
    this.draggable = false;
    this._className = '';
    this._textContent = '';
    this.classList = new FakeClassList(this);
  }

  get className() {
    return this._className;
  }

  set className(value) {
    this.classList.syncFromString(value);
  }

  get textContent() {
    return `${this._textContent}${this.childNodes.map((childNode) => childNode.textContent).join('')}`;
  }

  set textContent(value) {
    this._textContent = value === undefined || value === null ? '' : String(value);
    this.childNodes = [];
  }

  get firstChild() {
    return this.childNodes[0] || null;
  }

  get children() {
    return this.childNodes;
  }

  appendChild(childNode) {
    if (!childNode) {
      return null;
    }
    if (childNode.parentNode) {
      childNode.parentNode.removeChild(childNode);
    }
    childNode.parentNode = this;
    this.childNodes.push(childNode);
    return childNode;
  }

  insertBefore(childNode, referenceNode) {
    if (!referenceNode || !this.childNodes.includes(referenceNode)) {
      return this.appendChild(childNode);
    }
    if (childNode.parentNode) {
      childNode.parentNode.removeChild(childNode);
    }
    childNode.parentNode = this;
    const referenceIndex = this.childNodes.indexOf(referenceNode);
    this.childNodes.splice(referenceIndex, 0, childNode);
    return childNode;
  }

  removeChild(childNode) {
    const childIndex = this.childNodes.indexOf(childNode);
    if (childIndex === -1) {
      return null;
    }
    this.childNodes.splice(childIndex, 1);
    childNode.parentNode = null;
    return childNode;
  }

  setAttribute(name, value) {
    const normalizedName = String(name);
    const normalizedValue = value === undefined || value === null ? '' : String(value);
    if (normalizedName === 'class') {
      this.className = normalizedValue;
      return;
    }
    if (normalizedName === 'hidden') {
      this.hidden = true;
    }
    if (normalizedName === 'value') {
      this.value = normalizedValue;
    }
    if (normalizedName === 'type') {
      this.type = normalizedValue;
    }
    if (normalizedName === 'id') {
      this.id = normalizedValue;
    }
    this.attributes.set(normalizedName, normalizedValue);
    if (normalizedName.startsWith('data-')) {
      this._datasetStore[toDatasetKey(normalizedName)] = normalizedValue;
    }
  }

  getAttribute(name) {
    const normalizedName = String(name);
    if (normalizedName === 'class') {
      return this.className || null;
    }
    if (normalizedName === 'value') {
      return this.value;
    }
    if (normalizedName === 'type') {
      return this.type || null;
    }
    if (normalizedName === 'id') {
      return this.id || null;
    }
    if (normalizedName === 'hidden') {
      return this.hidden ? '' : null;
    }
    return this.attributes.has(normalizedName) ? this.attributes.get(normalizedName) : null;
  }

  hasAttribute(name) {
    const normalizedName = String(name);
    if (normalizedName === 'hidden') {
      return this.hidden;
    }
    if (normalizedName === 'class') {
      return Boolean(this.className);
    }
    if (normalizedName === 'id') {
      return Boolean(this.id);
    }
    return this.attributes.has(normalizedName);
  }

  removeAttribute(name) {
    const normalizedName = String(name);
    if (normalizedName === 'hidden') {
      this.hidden = false;
      return;
    }
    if (normalizedName === 'class') {
      this.className = '';
      return;
    }
    if (normalizedName === 'id') {
      this.id = '';
      return;
    }
    this.attributes.delete(normalizedName);
    if (normalizedName.startsWith('data-')) {
      delete this._datasetStore[toDatasetKey(normalizedName)];
    }
  }

  contains(node) {
    if (node === this) {
      return true;
    }
    return this.childNodes.some((childNode) => childNode.contains(node));
  }

  focus() {
    if (this.ownerDocument) {
      this.ownerDocument.activeElement = this;
    }
  }

  click() {
    this.dispatchEvent(createFakeEvent('click', { target: this }));
  }

  getBoundingClientRect() {
    return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
  }

  matches(selector) {
    return matchesSelector(this, selector);
  }

  closest(selector) {
    let currentElement = this;
    while (currentElement) {
      if (currentElement.matches(selector)) {
        return currentElement;
      }
      currentElement = currentElement.parentNode;
    }
    return null;
  }

  querySelectorAll(selector) {
    return collectMatchingElements(this.childNodes, selector);
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
}

class FakeDocument extends FakeEventTarget {
  constructor() {
    super();
    this.readyState = 'loading';
    this.activeElement = null;
    this.documentElement = new FakeElement('html', this);
    this.body = new FakeElement('body', this);
    this.documentElement.appendChild(this.body);
  }

  createElement(tagName) {
    return new FakeElement(tagName, this);
  }

  querySelectorAll(selector) {
    const matches = [];
    if (matchesSelector(this.documentElement, selector)) {
      matches.push(this.documentElement);
    }
    if (matchesSelector(this.body, selector)) {
      matches.push(this.body);
    }
    return matches.concat(collectMatchingElements(this.body.childNodes, selector));
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }

  getElementById(elementId) {
    return this.querySelector(`#${elementId}`);
  }
}

function appendFakeElement(parentElement, tagName, options) {
  const element = parentElement.ownerDocument.createElement(tagName);
  const nextOptions = options || {};

  if (nextOptions.className) {
    element.className = nextOptions.className;
  }
  if (nextOptions.attributes) {
    Object.entries(nextOptions.attributes).forEach(([name, value]) => {
      element.setAttribute(name, value);
    });
  }
  if (nextOptions.value !== undefined) {
    element.value = String(nextOptions.value);
    element.setAttribute('value', String(nextOptions.value));
  }
  if (nextOptions.textContent !== undefined) {
    element.textContent = nextOptions.textContent;
  }
  if (nextOptions.hidden) {
    element.hidden = true;
  }
  if (nextOptions.type) {
    element.type = nextOptions.type;
    element.setAttribute('type', nextOptions.type);
  }

  parentElement.appendChild(element);
  return element;
}

function createTransportPageTestDocument() {
  const document = new FakeDocument();
  const body = document.body;

  appendFakeElement(body, 'div', { attributes: { 'data-status-message': '' } });

  const aiMenuShell = appendFakeElement(body, 'div', { attributes: { 'data-ai-menu-shell': '' } });
  appendFakeElement(aiMenuShell, 'button', {
    type: 'button',
    attributes: { 'data-ai-menu-trigger': '', 'aria-expanded': 'false' },
  });
  const aiMenu = appendFakeElement(aiMenuShell, 'div', {
    attributes: { 'data-ai-menu': '', role: 'menu' },
  });
  appendFakeElement(aiMenu, 'button', {
    type: 'button',
    attributes: { 'data-ai-menu-action': 'calculate-routes', role: 'menuitem' },
  });
  appendFakeElement(aiMenu, 'button', {
    type: 'button',
    attributes: { 'data-ai-menu-action': 'implement-modifications', role: 'menuitem' },
  });
  appendFakeElement(aiMenu, 'button', {
    type: 'button',
    attributes: { 'data-ai-menu-action': 'settings', role: 'menuitem' },
  });

  const aiSettingsModal = appendFakeElement(body, 'div', {
    hidden: true,
    attributes: { 'data-ai-settings-modal': '', 'aria-busy': 'false' },
  });
  appendFakeElement(aiSettingsModal, 'h2', {
    attributes: { id: 'transport-ai-settings-modal-title' },
  });
  appendFakeElement(aiSettingsModal, 'button', {
    type: 'button',
    className: 'transport-modal-close',
    attributes: { 'data-close-ai-settings-modal': '' },
  });
  appendFakeElement(aiSettingsModal, 'span', {
    attributes: { 'data-ai-settings-provider-label': '' },
  });
  const aiSettingsProvider = appendFakeElement(aiSettingsModal, 'select', {
    value: 'openai',
    attributes: { 'data-ai-settings-provider': '' },
  });
  appendFakeElement(aiSettingsProvider, 'option', { value: 'openai', textContent: 'OpenAI' });
  appendFakeElement(aiSettingsProvider, 'option', { value: 'deepseek', textContent: 'DeepSeek' });
  appendFakeElement(aiSettingsModal, 'p', {
    attributes: { 'data-ai-settings-provider-note': '', id: 'transport-ai-settings-modal-note' },
  });
  appendFakeElement(aiSettingsModal, 'span', {
    attributes: { 'data-ai-settings-api-key-label': '' },
  });
  appendFakeElement(aiSettingsModal, 'input', {
    type: 'password',
    value: '',
    attributes: { 'data-ai-settings-api-key': '' },
  });
  appendFakeElement(aiSettingsModal, 'p', {
    hidden: true,
    attributes: { 'data-ai-settings-api-key-hint': '' },
  });
  appendFakeElement(aiSettingsModal, 'div', {
    hidden: true,
    attributes: { 'data-ai-settings-feedback': '', id: 'transport-ai-settings-modal-feedback' },
  });
  appendFakeElement(aiSettingsModal, 'button', {
    type: 'button',
    attributes: { 'data-ai-settings-cancel': '', 'data-close-ai-settings-modal': '' },
  });
  appendFakeElement(aiSettingsModal, 'button', {
    type: 'button',
    attributes: { 'data-ai-settings-save': '' },
  });

  const aiAgentModal = appendFakeElement(body, 'div', {
    hidden: true,
    attributes: { 'data-ai-agent-modal': '', 'aria-busy': 'false' },
  });
  appendFakeElement(aiAgentModal, 'p', { attributes: { id: 'transport-ai-agent-modal-note' } });
  appendFakeElement(aiAgentModal, 'div', {
    hidden: true,
    attributes: { 'data-ai-agent-feedback': '' },
  });
  appendFakeElement(aiAgentModal, 'input', {
    type: 'time',
    value: '06:50',
    attributes: { 'data-ai-agent-earliest-boarding': '' },
  });
  appendFakeElement(aiAgentModal, 'input', {
    type: 'time',
    value: '07:45',
    attributes: { 'data-ai-agent-arrival-at-work': '' },
  });
  appendFakeElement(aiAgentModal, 'button', {
    type: 'button',
    attributes: { 'data-ai-agent-cancel': '', 'data-close-ai-agent-modal': '' },
  });
  appendFakeElement(aiAgentModal, 'button', {
    type: 'button',
    attributes: { 'data-ai-agent-submit': '' },
  });

  const aiChangesModal = appendFakeElement(body, 'div', {
    hidden: true,
    attributes: { 'data-ai-changes-modal': '', 'aria-busy': 'false' },
  });
  appendFakeElement(aiChangesModal, 'button', {
    type: 'button',
    className: 'transport-modal-close',
    attributes: { 'data-close-ai-changes-modal': '' },
  });
  appendFakeElement(aiChangesModal, 'h2', { attributes: { 'data-ai-changes-title': '' } });
  appendFakeElement(aiChangesModal, 'div', {
    hidden: true,
    attributes: { 'data-ai-changes-status': '' },
  });
  appendFakeElement(aiChangesModal, 'div', { attributes: { 'data-ai-changes-summary-grid': '' } });
  appendFakeElement(aiChangesModal, 'div', { attributes: { 'data-ai-changes-summary-panel': '' } });
  appendFakeElement(aiChangesModal, 'div', { attributes: { 'data-ai-changes-vehicles': '' } });
  appendFakeElement(aiChangesModal, 'div', { attributes: { 'data-ai-changes-passengers': '' } });
  appendFakeElement(aiChangesModal, 'div', { attributes: { 'data-ai-changes-routes': '' } });
  appendFakeElement(aiChangesModal, 'button', {
    type: 'button',
    attributes: { 'data-ai-changes-cancel': '' },
  });
  appendFakeElement(aiChangesModal, 'button', {
    type: 'button',
    attributes: { 'data-ai-changes-save': '' },
  });
  appendFakeElement(aiChangesModal, 'button', {
    type: 'button',
    attributes: { 'data-ai-changes-apply': '' },
  });

  ['regular', 'weekend', 'extra'].forEach((kind) => {
    appendFakeElement(body, 'div', { attributes: { 'data-request-kind': kind } });
    appendFakeElement(body, 'div', { attributes: { 'data-vehicle-scope': kind } });
  });

  return document;
}

function createFetchResponse(payload, status) {
  const responseStatus = Number.isInteger(status) ? status : 200;
  const body = payload === undefined || payload === null
    ? ''
    : typeof payload === 'string'
      ? payload
      : JSON.stringify(payload);

  return {
    ok: responseStatus >= 200 && responseStatus < 300,
    status: responseStatus,
    text() {
      return Promise.resolve(body);
    },
  };
}

function createFetchMock(options) {
  const nextOptions = options || {};
  const calls = [];
  const authSessionResponse = nextOptions.authSessionResponse || {
    authenticated: true,
    user: { chave: 'OPS-100', nome: 'Transport Ops' },
  };
  const settingsResponse = nextOptions.settingsResponse || {
    work_to_home_time: '16:15',
    last_update_time: '16:00',
    price_currency_code: 'USD',
    price_rate_unit: 'day',
    available_currencies: [{ code: 'USD', display_label: 'US Dollar' }],
    default_car_seats: 3,
    default_minivan_seats: 6,
    default_van_seats: 12,
    default_bus_seats: 40,
    default_car_price: 10,
    default_minivan_price: 18,
    default_van_price: 24,
    default_bus_price: 50,
    default_tolerance_minutes: 5,
  };
  const dashboardResponse = nextOptions.dashboardResponse || {
    selected_route: 'home_to_work',
    selected_date: '2026-06-13',
    project_rows: [],
    regular_requests: [],
    weekend_requests: [],
    extra_requests: [],
    regular_vehicles: [],
    weekend_vehicles: [],
    extra_vehicles: [],
    regular_vehicle_registry: [],
    weekend_vehicle_registry: [],
    extra_vehicle_registry: [],
  };
  const latestSuggestionResponse = nextOptions.latestSuggestionResponse;
  const commandResponses = nextOptions.commandResponses || {};
  const aiSettingsResponse = Object.prototype.hasOwnProperty.call(nextOptions, 'aiSettingsResponse')
    ? nextOptions.aiSettingsResponse
    : {
      provider: 'openai',
      resolved_model: 'gpt-5.4-2026-03-05',
      reasoning_effort: 'high',
      has_api_key: true,
      api_key_hint: '***1234',
    };
  const aiSettingsGetError = nextOptions.aiSettingsGetError || null;
  const aiSettingsPutError = nextOptions.aiSettingsPutError || null;
  const aiSettingsPutResponse = Object.prototype.hasOwnProperty.call(nextOptions, 'aiSettingsPutResponse')
    ? nextOptions.aiSettingsPutResponse
    : aiSettingsResponse;
  const aiSettingsPutHandler = typeof nextOptions.aiSettingsPutHandler === 'function'
    ? nextOptions.aiSettingsPutHandler
    : null;

  async function fetch(url, requestOptions) {
    const normalizedOptions = requestOptions || {};
    const request = {
      url: String(url),
      method: String(normalizedOptions.method || 'GET').toUpperCase(),
      body: normalizedOptions.body || '',
    };
    calls.push(request);

    if (request.method === 'GET' && request.url.includes('/auth/session')) {
      return createFetchResponse(authSessionResponse, 200);
    }
    if (request.method === 'GET' && request.url.includes('/ai/settings')) {
      if (aiSettingsGetError) {
        return createFetchResponse(aiSettingsGetError.payload, aiSettingsGetError.status);
      }
      return createFetchResponse(aiSettingsResponse, 200);
    }
    if (request.method === 'PUT' && request.url.includes('/ai/settings')) {
      if (aiSettingsPutHandler) {
        return aiSettingsPutHandler(request);
      }
      if (aiSettingsPutError) {
        return createFetchResponse(aiSettingsPutError.payload, aiSettingsPutError.status);
      }
      return createFetchResponse(aiSettingsPutResponse, 200);
    }
    if (request.method === 'GET' && request.url.includes('/settings')) {
      return createFetchResponse(settingsResponse, 200);
    }
    if (request.method === 'GET' && request.url.includes('/dashboard?')) {
      return createFetchResponse(dashboardResponse, 200);
    }
    if (request.method === 'GET' && request.url.includes('/ai/suggestions/latest')) {
      if (!latestSuggestionResponse) {
        throw new Error(`Unexpected fetch: ${request.method} ${request.url}`);
      }
      return createFetchResponse(latestSuggestionResponse, 200);
    }
    if (request.method === 'POST' && request.url.includes('/ai/suggestions/') && request.url.endsWith('/cancel')) {
      return createFetchResponse(commandResponses.cancel, 200);
    }
    if (request.method === 'POST' && request.url.includes('/ai/suggestions/') && request.url.endsWith('/save')) {
      return createFetchResponse(commandResponses.save, 200);
    }
    if (request.method === 'POST' && request.url.includes('/ai/suggestions/') && request.url.endsWith('/apply')) {
      return createFetchResponse(commandResponses.apply, 200);
    }

    throw new Error(`Unexpected fetch: ${request.method} ${request.url}`);
  }

  return { fetch, calls };
}

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });

  return { promise, resolve, reject };
}

function createImmediateTimerHarness() {
  let nextTimerId = 1;
  const activeTimers = new Map();

  return {
    setTimeout(callback) {
      const timerId = nextTimerId;
      nextTimerId += 1;
      activeTimers.set(timerId, true);
      Promise.resolve().then(() => {
        if (!activeTimers.has(timerId)) {
          return;
        }
        activeTimers.delete(timerId);
        callback();
      });
      return timerId;
    },
    clearTimeout(timerId) {
      activeTimers.delete(timerId);
    },
  };
}

async function flushAsyncWork(iterations) {
  const passes = Number.isInteger(iterations) ? iterations : 6;
  for (let index = 0; index < passes; index += 1) {
    await Promise.resolve();
    await new Promise((resolve) => setImmediate(resolve));
  }
}

function getSampleLatestSuggestionResponse() {
  return {
    run_key: 'transport-ai-run:latest-001',
    suggestion_key: 'transport-ai-suggestion:latest-001',
    can_save: true,
    can_apply: true,
    can_cancel_restore: true,
    status: 'proposed',
    route_kind: 'home_to_work',
    service_date: '2026-06-13',
    message: 'Transport AI suggestion is ready for review.',
    suggestion: {
      suggestion_key: 'transport-ai-suggestion:latest-001',
      status: 'shown',
      prompt_version: 'transport_ai_route_planner_v1',
      plan: {
        objective_summary: 'Cut costs while keeping one route stable for the morning shift.',
        route_kind: 'home_to_work',
        earliest_boarding_time: '06:50',
        arrival_at_work_time: '07:45',
        passenger_allocations: [
          {
            request_id: 301,
            request_kind: 'extra',
            service_date: '2026-06-13',
            route_kind: 'home_to_work',
            vehicle_ref: 'existing:11',
            user_id: 501,
            chave: 'USR501',
            nome: 'Alice Tan',
            project_name: 'P80',
            pickup_order: 0,
            scheduled_pickup_time: '07:05',
            projected_arrival_time: '07:45',
            rationale: 'Keep the closest passenger on the shared route.',
          },
        ],
        route_itineraries: [
          {
            route_key: 'route:existing:11',
            partition_key: 'extra:P80:SG',
            vehicle_ref: 'existing:11',
            service_scope: 'extra',
            route_kind: 'home_to_work',
            vehicle_type: 'van',
            vehicle_id: 11,
            plate: 'SGX1234',
            project_name: 'P80',
            country_code: 'SG',
            country_name: 'Singapore',
            estimated_cost: 24,
            total_duration_seconds: 2400,
            total_distance_meters: 9800,
            projected_arrival_time: '07:45',
            stops: [
              {
                stop_order: 0,
                stop_type: 'pickup',
                request_id: 301,
                user_id: 501,
                passenger_name: 'Alice Tan',
                project_name: 'P80',
                address: '7 Garden Street',
                zip_code: '100001',
                country_code: 'SG',
                longitude: 103.81,
                latitude: 1.31,
                scheduled_time: '07:05',
                duration_from_previous_seconds: 0,
                distance_from_previous_meters: 0,
              },
              {
                stop_order: 1,
                stop_type: 'destination',
                project_name: 'P80 HQ',
                address: '1 Industrial Road',
                zip_code: '123456',
                country_code: 'SG',
                longitude: 103.8,
                latitude: 1.3,
                scheduled_time: '07:45',
                duration_from_previous_seconds: 720,
                distance_from_previous_meters: 6800,
              },
            ],
          },
        ],
        vehicle_actions: [
          {
            action_key: 'vehicle:update:11',
            action_type: 'update',
            service_scope: 'extra',
            vehicle_id: 11,
            before: {
              vehicle_type: 'carro',
              capacity: 4,
              plate: 'SGX1234',
              service_scope: 'extra',
              estimated_cost: 30,
            },
            after: {
              vehicle_type: 'van',
              capacity: 12,
              plate: 'SGX1234',
              service_scope: 'extra',
              estimated_cost: 24,
            },
            rationale: 'Upgrade the vehicle and keep the existing route grouped.',
            cost_delta: -6,
          },
        ],
        cost_summary: {
          price_currency_code: 'USD',
          price_rate_unit: 'day',
          current_total_estimated_cost: 120,
          suggested_total_estimated_cost: 100,
          estimated_cost_delta: -20,
          current_vehicle_count: 2,
          suggested_vehicle_count: 1,
        },
        change_summary: {
          total_vehicle_actions: 1,
          keep_count: 0,
          create_count: 0,
          update_count: 1,
          remove_from_day_count: 0,
          by_vehicle_type: [],
        },
        validation_issues: [],
      },
    },
  };
}

function getSuggestionCommandSuccessResponse(actionName) {
  const latestSuggestionResponse = getSampleLatestSuggestionResponse();
  const actionCopy = {
    cancel: { message: 'Transport AI suggestion was cancelled.', status: 'cancelled' },
    save: { message: 'Transport AI suggestion was saved.', status: 'saved' },
    apply: { message: 'Transport AI suggestion was applied.', status: 'applied' },
  };
  const resolvedAction = actionCopy[actionName];

  return Object.assign({}, latestSuggestionResponse, {
    status: resolvedAction.status,
    message: resolvedAction.message,
    can_save: actionName === 'save',
    can_apply: actionName === 'save',
    can_cancel_restore: actionName === 'save',
  });
}

async function withTransportPageHarness(options, callback) {
  const previousGlobals = {
    document: global.document,
    fetch: global.fetch,
    addEventListener: global.addEventListener,
    removeEventListener: global.removeEventListener,
    dispatchEvent: global.dispatchEvent,
    setTimeout: global.setTimeout,
    clearTimeout: global.clearTimeout,
    EventSource: global.EventSource,
  };
  const document = createTransportPageTestDocument();
  const windowEvents = new FakeEventTarget();
  const timers = createImmediateTimerHarness();
  const fetchMock = createFetchMock(options);

  global.document = document;
  global.fetch = fetchMock.fetch;
  global.addEventListener = windowEvents.addEventListener.bind(windowEvents);
  global.removeEventListener = windowEvents.removeEventListener.bind(windowEvents);
  global.dispatchEvent = windowEvents.dispatchEvent.bind(windowEvents);
  global.setTimeout = timers.setTimeout.bind(timers);
  global.clearTimeout = timers.clearTimeout.bind(timers);
  global.EventSource = undefined;

  try {
    const localizedTransportPage = loadTransportPageWithI18n();
    document.dispatchEvent(createFakeEvent('DOMContentLoaded', { target: document }));
    await flushAsyncWork();
    return await callback({
      document,
      fetchCalls: fetchMock.calls,
      transportPageApi: localizedTransportPage,
      flushAsyncWork,
      getElement(selector) {
        const element = document.querySelector(selector);
        assert.ok(element, `Expected to find element matching ${selector}`);
        return element;
      },
      countFetchCalls(fragment) {
        return fetchMock.calls.filter((call) => call.url.includes(fragment)).length;
      },
    });
  } finally {
    if (previousGlobals.document === undefined) {
      delete global.document;
    } else {
      global.document = previousGlobals.document;
    }
    global.fetch = previousGlobals.fetch;
    global.addEventListener = previousGlobals.addEventListener;
    global.removeEventListener = previousGlobals.removeEventListener;
    global.dispatchEvent = previousGlobals.dispatchEvent;
    global.setTimeout = previousGlobals.setTimeout;
    global.clearTimeout = previousGlobals.clearTimeout;
    global.EventSource = previousGlobals.EventSource;
  }
}

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

test('createTransportDateStore can update the selected date silently without notifying subscribers', () => {
  const dateStore = transportPage.createTransportDateStore(new Date(2026, 3, 17));
  const notifiedDates = [];

  dateStore.subscribe((dateValue) => {
    notifiedDates.push(transportPage.formatIsoDate(dateValue));
  });

  dateStore.setValue(new Date(2026, 3, 20), { notify: false });

  assert.deepEqual(notifiedDates, ['2026-04-17']);
  assert.equal(transportPage.formatIsoDate(dateStore.getValue()), '2026-04-20');
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

  assert.equal(
    transportPage.formatVehicleOccupancyLabel({ placa: '', lugares: null }, 3),
    'Waiting (3/Waiting)'
  );
});

test('formatVehicleOccupancyCount shows only the allocated and total seats', () => {
  assert.equal(
    transportPage.formatVehicleOccupancyCount({ placa: 'SGX1234A', lugares: 7 }, 3),
    '3/7'
  );

  assert.equal(
    transportPage.formatVehicleOccupancyCount({ placa: 'SGX1234A', lugares: null }, 3),
    '3/Waiting'
  );
});

test('pending vehicle helpers localize missing text fields as Waiting without treating numeric zero as blank', () => {
  assert.equal(transportPage.isPendingVehicleField(null), true);
  assert.equal(transportPage.isPendingVehicleField('   '), true);
  assert.equal(transportPage.isPendingVehicleField('SGX1234A'), false);
  assert.equal(transportPage.isPendingVehicleField(0), false);
  assert.equal(transportPage.formatPendingVehicleField(''), 'Waiting');
  assert.equal(
    transportPage.formatPendingVehicleField('van', (value) => String(value).toUpperCase()),
    'VAN'
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

test('getVehicleDepartureTime prefers the vehicle time and falls back to the topbar time for regular and weekend rows', () => {
  assert.equal(transportPage.getVehicleDepartureTime({ departure_time: '17:20' }), '17:20');
  assert.equal(
    transportPage.getVehicleDepartureTime({ departure_time: '17h20', service_scope: 'regular' }, '18:10'),
    '18:10'
  );
  assert.equal(
    transportPage.getVehicleDepartureTime({ service_scope: 'weekend' }, '16:45'),
    '16:45'
  );
  assert.equal(
    transportPage.getVehicleDepartureTime({ departure_time: '', service_scope: 'extra' }, '18:10'),
    ''
  );
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

test('buildVehicleBasePayload keeps empty edit fields nullable without inventing defaults', () => {
  const formData = new FormData();
  formData.set('tipo', '');
  formData.set('placa', '');
  formData.set('color', 'Blue');
  formData.set('lugares', '');
  formData.set('tolerance', '0');

  assert.deepEqual(transportPage.buildVehicleBasePayload(formData), {
    tipo: null,
    placa: null,
    color: 'Blue',
    lugares: null,
    tolerance: 0,
  });
});

test('resolveVehicleEditFocusField prioritizes pending base fields and then the first blank value', () => {
  assert.equal(
    transportPage.resolveVehicleEditFocusField({
      pending_fields: ['lugares', 'placa'],
      placa: null,
      lugares: null,
    }),
    'placa'
  );

  assert.equal(
    transportPage.resolveVehicleEditFocusField({
      tipo: 'carro',
      placa: 'ABC1234',
      color: null,
      lugares: 3,
      tolerance: 5,
    }),
    'color'
  );
});

test('vehicle modal markup keeps default places and tolerance values while allowing partial base fields', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );

  assert.match(transportHtml, /<option value=""><\/option>/);
  assert.match(transportHtml, /<option value="carro" selected>Car<\/option>/);
  assert.match(transportHtml, /<input type="text" name="placa" maxlength="15" autocomplete="off" \/>/);
  assert.match(transportHtml, /<input type="number" name="lugares" class="transport-number-input transport-number-input-spinnerless" min="1" max="99" value="3" \/>/);
  assert.match(transportHtml, /<input type="number" name="tolerance" class="transport-number-input transport-number-input-spinnerless" min="0" max="240" value="5" \/>/);
  assert.match(transportHtml, /<input type="checkbox" name="every_monday" checked \/>/);
  assert.match(transportHtml, /<input type="checkbox" name="every_friday" checked \/>/);
});

test('transport pending placeholder translations and CSS are defined for vehicle fields', () => {
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(transportI18n, /waiting:\s*"Waiting"/);
  assert.match(transportI18n, /waitingAria:\s*"Vehicle field pending completion"/);
  assert.match(transportCss, /\.transport-pending-value\s*\{[\s\S]*color:\s*var\(--transport-danger\);/);
});

test('transport topbar uses an inline red dashboard settings link below the allocation board title', () => {
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

  assert.match(
    transportHtml,
    /<a[\s\S]*class="transport-settings-link"[\s\S]*data-open-settings-modal[\s\S]*>\s*Dashboard Settings\s*<\/a>/
  );
  assert.doesNotMatch(transportHtml, /<button[\s\S]*class="transport-settings-trigger"/);
  assert.match(
    transportCss,
    /\.transport-settings-link\s*\{[\s\S]*align-self:\s*center;[\s\S]*color:\s*var\(--transport-danger\);/
  );
  assert.doesNotMatch(transportScript, /settingsRouteAnchor|scheduleSettingsTriggerPositionSync|syncSettingsTriggerPosition/);
});

test('transport auth inputs do not clear the session on click anymore', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.doesNotMatch(transportScript, /function resetAuthenticatedTransportField\(/);
  assert.doesNotMatch(transportScript, /authKeyInput\.addEventListener\("pointerdown",\s*resetAuthenticatedTransportField\)/);
  assert.doesNotMatch(transportScript, /authPasswordInput\.addEventListener\("pointerdown",\s*resetAuthenticatedTransportField\)/);
});

test('transport page controller declares the topbar element before applying translations', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportScript, /const transportTopbar = document\.querySelector\("\[data-transport-topbar\]"\);/);
  assert.match(transportScript, /if \(transportTopbar\) \{[\s\S]*transportTopbar\.setAttribute\("aria-label", t\("layout\.quickActions"\)\);/);
});

test('transport settings modal includes editable default seat counts, pricing controls, and currency actions', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );

  assert.match(transportHtml, /data-settings-vehicle-defaults-title/);
  assert.match(transportHtml, /data-settings-price-variables-label/);
  assert.match(transportHtml, /data-settings-price-currency/);
  assert.match(transportHtml, /data-settings-price-rate-unit/);
  assert.match(transportHtml, /data-settings-add-currency-button/);
  assert.match(transportHtml, /data-settings-new-currency-code/);
  assert.match(transportHtml, /data-settings-new-currency-label/);
  assert.match(transportHtml, /data-settings-save-currency-button/);
  assert.match(transportHtml, /data-settings-default-seat="carro"/);
  assert.match(transportHtml, /data-settings-default-seat="minivan"/);
  assert.match(transportHtml, /data-settings-default-seat="van"/);
  assert.match(transportHtml, /data-settings-default-seat="onibus"/);
  assert.match(transportHtml, /data-settings-default-price="carro"/);
  assert.match(transportHtml, /data-settings-default-price="minivan"/);
  assert.match(transportHtml, /data-settings-default-price="van"/);
  assert.match(transportHtml, /data-settings-default-price="onibus"/);
  assert.match(transportHtml, /data-settings-default-tolerance-label/);
  assert.match(transportHtml, /data-settings-default-tolerance/);
  assert.match(transportHtml, /id="transportSettingsCarSeats"[\s\S]*value="3"/);
  assert.match(transportHtml, /id="transportSettingsBusSeats"[\s\S]*value="40"/);
  assert.match(transportHtml, /id="transportSettingsDefaultTolerance"[\s\S]*value="5"/);
  assert.match(transportHtml, /id="transportSettingsCarPrice"/);
  assert.match(transportHtml, /id="transportSettingsBusPrice"/);
  assert.match(transportI18n, /priceVariables:\s*"Price Variables"/);
  assert.match(transportI18n, /defaultPriceLabel:\s*"\{type\} default price:"/);
  assert.match(transportI18n, /couldNotAddCurrency:\s*"Could not add currency\./);
  assert.match(transportI18n, /currencyAlreadyExists:\s*"This currency code already exists\./);
});

test('transport ai agent settings modal includes default times, feedback region, and action buttons', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );

  assert.match(
    transportHtml,
    /aria-describedby="transport-ai-agent-modal-note transport-ai-agent-modal-feedback"/
  );
  assert.match(transportHtml, /data-ai-agent-earliest-boarding[\s\S]*value="06:50"/);
  assert.match(transportHtml, /data-ai-agent-arrival-at-work[\s\S]*value="07:45"/);
  assert.match(transportHtml, /data-ai-agent-feedback/);
  assert.match(transportHtml, /data-ai-agent-cancel/);
  assert.match(transportHtml, /data-ai-agent-submit/);
  assert.doesNotMatch(
    transportHtml,
    /<div class="transport-modal-actions transport-ai-agent-actions">\s*<button type="button" class="transport-secondary-button" data-close-ai-agent-modal>Fechar<\/button>\s*<\/div>/
  );
});

test('transport ai agent settings modal actions keep dedicated translation hooks', () => {
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportI18n, /agentSettingsCancel:/);
  assert.match(transportI18n, /agentSettingsSubmit:/);
  assert.match(transportScript, /data-ai-agent-cancel/);
  assert.match(transportScript, /t\("ai\.agentSettingsCancel"\)/);
  assert.match(transportScript, /data-ai-agent-submit/);
  assert.match(transportScript, /t\("ai\.agentSettingsSubmit"\)/);
});

test('transport ai settings modal keeps dedicated menu, request, and feedback hooks', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(
    transportHtml,
    /data-ai-menu-action="calculate-routes"[\s\S]*data-ai-menu-action="implement-modifications"[\s\S]*data-ai-menu-action="settings"/
  );
  assert.match(transportHtml, /data-ai-menu-action="settings"/);
  assert.match(transportHtml, /data-ai-settings-modal/);
  assert.match(transportHtml, /data-ai-settings-provider/);
  assert.match(transportHtml, /data-ai-settings-api-key/);
  assert.match(transportHtml, /data-ai-settings-api-key-hint/);
  assert.match(transportHtml, /data-ai-settings-feedback/);
  assert.match(transportHtml, /data-ai-settings-save/);
  assert.match(transportI18n, /settingsMenuLabel:/);
  assert.match(transportI18n, /settingsSave:/);
  assert.match(transportI18n, /settingsProviderChangeRequiresKey:/);
  assert.match(transportScript, /function openAiSettingsModal\(\) \{/);
  assert.match(transportScript, /function saveTransportAiSettings\(\) \{/);
  assert.match(transportScript, /requestJson\(`\$\{TRANSPORT_API_PREFIX\}\/ai\/settings`\)/);
  assert.match(transportCss, /\.transport-ai-settings-modal/);
  assert.match(transportCss, /\.transport-ai-settings-api-key-hint\[data-tone="warning"\]/);
});

test('transport ai settings translations exist for every supported language including success and failure feedback copy', () => {
  const localizedTransportPage = loadTransportPageWithI18n();
  const transportI18nRuntime = global.CheckingTransportI18n;
  const requiredAiKeyPaths = [
    'ai.settingsMenuLabel',
    'ai.settingsSave',
    'ai.settingsLoading',
    'ai.settingsSaving',
    'ai.settingsSaved',
    'ai.settingsProviderChangeRequiresKey',
    'ai.agentSettingsCancel',
    'ai.agentSettingsSubmit',
    'ai.agentSettingsSubmitting',
    'ai.agentSettingsInvalidTimes',
    'ai.agentSettingsReadyForReview',
    'ai.routeCalculationFailed',
  ];

  assert.ok(Array.isArray(transportI18nRuntime.languages));
  assert.ok(transportI18nRuntime.languages.length > 0);
  transportI18nRuntime.languages.forEach(({ code }) => {
    requiredAiKeyPaths.forEach((keyPath) => {
      assert.notEqual(localizedTransportPage.translateTransportText(keyPath, undefined, code), keyPath);
    });
  });
});

test('transport ai settings translation helpers follow the active language and keep safe fallback behavior', () => {
  const localizedTransportPage = loadTransportPageWithI18n();
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  localizedTransportPage.setActiveTransportLanguageCode('pt');
  assert.equal(localizedTransportPage.getActiveTransportLanguageCode(), 'pt');
  assert.equal(localizedTransportPage.translateTransportText('ai.settingsMenuLabel'), 'IA Settings');
  assert.equal(localizedTransportPage.translateTransportText('ai.agentSettingsCancel'), 'Cancelar');
  assert.equal(localizedTransportPage.translateTransportText('ai.agentSettingsSubmit'), 'Solicitar Rotas');

  localizedTransportPage.setActiveTransportLanguageCode('en');
  assert.equal(localizedTransportPage.getActiveTransportLanguageCode(), 'en');
  assert.equal(localizedTransportPage.translateTransportText('ai.settingsSave'), 'Save');
  assert.equal(localizedTransportPage.translateTransportText('ai.agentSettingsCancel'), 'Cancel');
  assert.equal(localizedTransportPage.translateTransportText('ai.routeCalculationFailed'), 'Transport AI route calculation failed.');
  assert.equal(localizedTransportPage.translateTransportText('ai.missingKeyForTest'), 'ai.missingKeyForTest');
  assert.equal(localizedTransportPage.translateTransportText('ai.agentSettingsSubmit', undefined, 'invalid'), 'Request Routes');
  assert.match(
    transportScript,
    /buttonElement\.textContent = t\("ai\.agentSettingsCancel"\)/
  );
  assert.match(
    transportScript,
    /buttonElement\.textContent = hasActiveRun[\s\S]*t\("ai\.agentSettingsSubmitting"\)[\s\S]*t\("ai\.agentSettingsSubmit"\)/
  );
  assert.match(
    transportScript,
    /state\.aiAgentFeedbackKey[\s\S]*t\(state\.aiAgentFeedbackKey/
  );
  assert.match(
    transportScript,
    /function syncAiChangesSummaryCopy\(\) \{[\s\S]*t\(state\.aiChangesSummaryKey/
  );
});

test('transport ai agent settings helpers keep defaults, preserve raw edits, and validate time windows', () => {
  assert.deepEqual(transportPage.getDefaultAiAgentSettings(), {
    earliestBoardingTime: '06:50',
    arrivalAtWorkTime: '07:45',
  });

  assert.deepEqual(transportPage.readAiAgentSettingsDraft(undefined), {
    earliestBoardingTime: '06:50',
    arrivalAtWorkTime: '07:45',
  });
  assert.deepEqual(
    transportPage.readAiAgentSettingsDraft({
      earliestBoardingInput: { value: '06:55' },
      arrivalAtWorkInput: { value: '07:35' },
    }),
    {
      earliestBoardingTime: '06:55',
      arrivalAtWorkTime: '07:35',
    }
  );
  assert.deepEqual(
    transportPage.readAiAgentSettingsDraft({
      earliestBoardingTime: '',
      arrivalAtWorkTime: '07:35',
    }),
    {
      earliestBoardingTime: '',
      arrivalAtWorkTime: '07:35',
    }
  );

  assert.deepEqual(
    transportPage.validateAiAgentSettingsDraft({
      earliestBoardingTime: '06:50',
      arrivalAtWorkTime: '07:45',
    }),
    {
      ok: true,
      messageKey: '',
      field: '',
      draft: {
        earliestBoardingTime: '06:50',
        arrivalAtWorkTime: '07:45',
      },
    }
  );

  const invalidFormat = transportPage.validateAiAgentSettingsDraft({
    earliestBoardingTime: '6:50',
    arrivalAtWorkTime: '07:45',
  });
  assert.equal(invalidFormat.ok, false);
  assert.equal(invalidFormat.field, 'earliestBoardingTime');
  assert.equal(invalidFormat.messageKey, 'ai.agentSettingsInvalidTimes');

  const invalidWindow = transportPage.validateAiAgentSettingsDraft({
    earliestBoardingTime: '07:45',
    arrivalAtWorkTime: '07:45',
  });
  assert.equal(invalidWindow.ok, false);
  assert.equal(invalidWindow.field, 'arrivalAtWorkTime');
  assert.equal(invalidWindow.messageKey, 'ai.agentSettingsInvalidTimes');
});

test('transport ai route request helpers build the backend payload and only poll active run states', () => {
  assert.deepEqual(
    transportPage.buildTransportAiRouteCalculationPayload('2026-06-13', 'home_to_work', {
      earliestBoardingTime: '06:50',
      arrivalAtWorkTime: '07:45',
    }),
    {
      service_date: '2026-06-13',
      route_kind: 'home_to_work',
      earliest_boarding_time: '06:50',
      arrival_at_work_time: '07:45',
    }
  );

  assert.equal(
    transportPage.shouldContinuePollingAiRouteRun({
      ok: true,
      run_key: 'transport-ai-run:001',
      status: 'running',
      suggestion_ready: false,
    }),
    true
  );
  assert.equal(
    transportPage.shouldContinuePollingAiRouteRun({
      ok: true,
      run_key: 'transport-ai-run:001',
      status: 'proposed',
      suggestion_ready: true,
    }),
    false
  );
  assert.equal(
    transportPage.shouldContinuePollingAiRouteRun({
      ok: false,
      run_key: 'transport-ai-run:001',
      status: 'failed',
      suggestion_ready: false,
    }),
    false
  );
});

test('transport ai suggestion command helpers keep review actions aligned with the run flags', () => {
  assert.equal(
    transportPage.getTransportAiSuggestionKey({ suggestion_key: 'transport-ai-suggestion:top-level' }),
    'transport-ai-suggestion:top-level'
  );
  assert.equal(
    transportPage.getTransportAiSuggestionKey({
      suggestion: { suggestion_key: 'transport-ai-suggestion:nested' },
    }),
    'transport-ai-suggestion:nested'
  );
  assert.equal(
    transportPage.buildTransportAiSuggestionCommandUrl(
      '/api/transport',
      'transport-ai-suggestion:apply-001',
      'apply'
    ),
    '/api/transport/ai/suggestions/transport-ai-suggestion%3Aapply-001/apply'
  );
  assert.equal(transportPage.shouldRefreshDashboardAfterAiSuggestionCommand('save'), false);
  assert.equal(transportPage.shouldRefreshDashboardAfterAiSuggestionCommand('cancel'), true);
  assert.equal(transportPage.shouldRefreshDashboardAfterAiSuggestionCommand('apply'), true);

  assert.deepEqual(
    transportPage.resolveAiChangesCommandState(
      {
        suggestion_key: 'transport-ai-suggestion:flags-001',
        can_save: true,
        can_apply: true,
        can_cancel_restore: true,
      },
      {
        isAuthenticated: true,
        isPending: false,
        pendingAction: '',
      }
    ),
    {
      suggestionKey: 'transport-ai-suggestion:flags-001',
      isPending: false,
      pendingAction: '',
      canCancel: true,
      canSave: true,
      canApply: true,
    }
  );

  assert.deepEqual(
    transportPage.resolveAiChangesCommandState(
      {
        suggestion_key: 'transport-ai-suggestion:flags-002',
        can_save: true,
        can_apply: true,
        can_cancel_restore: true,
      },
      {
        isAuthenticated: true,
        isPending: true,
        pendingAction: 'apply',
      }
    ),
    {
      suggestionKey: 'transport-ai-suggestion:flags-002',
      isPending: true,
      pendingAction: 'apply',
      canCancel: false,
      canSave: false,
      canApply: false,
    }
  );
});

test('transport ai latest suggestion helper builds the saved-review endpoint for the selected date and route', () => {
  assert.equal(
    transportPage.buildTransportAiLatestSuggestionUrl(
      '/api/transport',
      '2026-06-13',
      'work_to_home'
    ),
    '/api/transport/ai/suggestions/latest?service_date=2026-06-13&route_kind=work_to_home'
  );
  assert.equal(
    transportPage.buildTransportAiLatestSuggestionUrl('/api/transport', '', 'home_to_work'),
    ''
  );
});

test('transport ai settings request flow validates before fetching, posts the start payload, and polls the run status endpoint', () => {
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportI18n, /agentSettingsSubmitting:/);
  assert.match(transportI18n, /agentSettingsInvalidTimes:/);
  assert.match(transportScript, /function requestAiRoutes\(\) \{/);
  assert.match(
    transportScript,
    /const validation = validateAiAgentSettingsDraft\(draft\);[\s\S]*if \(!validation\.ok\) \{[\s\S]*return Promise\.resolve\(null\);[\s\S]*\}[\s\S]*requestJson\(`\$\{TRANSPORT_API_PREFIX\}\/ai\/route-calculations`/
  );
  assert.match(
    transportScript,
    /buildTransportAiRouteCalculationPayload\([\s\S]*getCurrentServiceDateIso\(\),[\s\S]*getSelectedRouteKind\(\),[\s\S]*validation\.draft/
  );
  assert.match(transportScript, /function pollAiRouteRun\(runKey\) \{/);
  assert.match(
    transportScript,
    /requestJson\(`\$\{TRANSPORT_API_PREFIX\}\/ai\/route-calculations\/\$\{encodeURIComponent\(normalizedRunKey\)\}`\)/
  );
  assert.match(transportScript, /openAiChangesModal\(response\);/);
  assert.match(
    transportScript,
    /document\.querySelectorAll\("\[data-ai-agent-submit\]"\)\.forEach\(function \(buttonElement\) \{[\s\S]*void requestAiRoutes\(\);/
  );
  assert.match(
    transportScript,
    /document\.querySelectorAll\("\[data-close-ai-agent-modal\]"\)\.forEach\(function \(buttonElement\) \{[\s\S]*buttonElement\.addEventListener\("click", closeAiAgentSettingsModal\);/
  );
});

test('transport ai modal feedback uses the dedicated modal feedback styling including the info tone', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(transportHtml, /class="transport-modal-feedback transport-ai-agent-modal-feedback"/);
  assert.match(transportCss, /\.transport-modal-feedback\[data-tone="info"\]/);
});

test('transport ai route success opens the changes modal shell', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportHtml, /data-ai-changes-modal/);
  assert.match(transportHtml, /data-ai-changes-title/);
  assert.match(transportHtml, /data-ai-changes-summary/);
  assert.match(transportHtml, /data-ai-changes-status/);
  assert.match(transportI18n, /changesTitle:/);
  assert.match(transportI18n, /changesCloseAria:/);
  assert.match(
    transportScript,
    /function openAiChangesModal\(runStatusResponse\) \{[\s\S]*aiChangesModal\.hidden = false;/
  );
  assert.match(
    transportScript,
    /function closeAiChangesModal\(options\) \{[\s\S]*aiChangesModal\.hidden = true;/
  );
});

test('transport ai changes actions keep dedicated command wiring and modal-scoped failure feedback', () => {
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportI18n, /changesCancel:/);
  assert.match(transportI18n, /changesSave:/);
  assert.match(transportI18n, /changesApply:/);
  assert.match(transportI18n, /changesCancelling:/);
  assert.match(transportI18n, /changesSaving:/);
  assert.match(transportI18n, /changesApplying:/);
  assert.match(transportScript, /function runAiSuggestionCommand\(actionName\) \{/);
  assert.match(transportScript, /function cancelAiSuggestion\(\) \{[\s\S]*runAiSuggestionCommand\("cancel"\)/);
  assert.match(transportScript, /function saveAiSuggestion\(\) \{[\s\S]*runAiSuggestionCommand\("save"\)/);
  assert.match(transportScript, /function applyAiSuggestion\(\) \{[\s\S]*runAiSuggestionCommand\("apply"\)/);
  assert.match(
    transportScript,
    /requestJson\([\s\S]*buildTransportAiSuggestionCommandUrl\(TRANSPORT_API_PREFIX, commandState\.suggestionKey, normalizedAction\),[\s\S]*method: "POST"/
  );
  assert.match(
    transportScript,
    /document\.querySelectorAll\("\[data-ai-changes-cancel\]"\)\.forEach\(function \(buttonElement\) \{[\s\S]*void cancelAiSuggestion\(\);/
  );
  assert.match(
    transportScript,
    /document\.querySelectorAll\("\[data-ai-changes-save\]"\)\.forEach\(function \(buttonElement\) \{[\s\S]*void saveAiSuggestion\(\);/
  );
  assert.match(
    transportScript,
    /document\.querySelectorAll\("\[data-ai-changes-apply\]"\)\.forEach\(function \(buttonElement\) \{[\s\S]*void applyAiSuggestion\(\);/
  );
  assert.match(
    transportScript,
    /function syncAiChangesControls\(\) \{[\s\S]*aiChangesCancelButton\.disabled = !commandState\.canCancel;[\s\S]*aiChangesSaveButton\.disabled = !commandState\.canSave;[\s\S]*aiChangesApplyButton\.disabled = !commandState\.canApply;/
  );
  assert.match(
    transportScript,
    /function closeAiChangesModal\(options\) \{[\s\S]*if \(!closeOptions\.force && state\.aiChangesCommandPending\) \{[\s\S]*return;[\s\S]*\}/
  );
  assert.match(
    transportScript,
    /setAiChangesSummary\(resolvedMessage, "error", resolvedMessage[\s\S]*actionCopy\.errorKey/
  );
  assert.match(
    transportScript,
    /if \(shouldRefreshDashboardAfterAiSuggestionCommand\(normalizedAction\)\) \{[\s\S]*requestDashboardRefresh\(\{ announce: false \}\);/
  );
});

test('transport ai implement modifications reopens the last saved suggestion for the current date and shows footer feedback when none exists', () => {
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportI18n, /noSavedSuggestion:/);
  assert.match(transportI18n, /loadLatestSuggestionFailed:/);
  assert.match(
    transportScript,
    /function loadLatestAiSuggestion\(\) \{[\s\S]*closeAiMenu\(\);[\s\S]*buildTransportAiLatestSuggestionUrl\([\s\S]*TRANSPORT_API_PREFIX,[\s\S]*getCurrentServiceDateIso\(\),[\s\S]*getSelectedRouteKind\(\)[\s\S]*requestJson\(latestSuggestionUrl\)[\s\S]*openAiChangesModal\(response\);/
  );
  assert.match(
    transportScript,
    /if \(error && Number\(error\.status\) === 404\) \{[\s\S]*setStatus\(t\("ai\.noSavedSuggestion"\), "info"\);/
  );
  assert.match(
    transportScript,
    /function syncAiMenuControls\(\) \{[\s\S]*aiImplementModificationsButton\.disabled = !state\.isAuthenticated \|\| state\.aiLatestSuggestionLoading;/
  );
  assert.match(
    transportScript,
    /aiImplementModificationsButton\.addEventListener\("click", function \(event\) \{[\s\S]*void loadLatestAiSuggestion\(\);/
  );
});

test('transport ai changes modal exposes the review layout scaffold and responsive CSS hooks', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(transportHtml, /data-ai-changes-tabs/);
  assert.match(transportHtml, /data-ai-changes-tab="summary"/);
  assert.match(transportHtml, /data-ai-changes-tab="vehicles"/);
  assert.match(transportHtml, /data-ai-changes-tab="passengers"/);
  assert.match(transportHtml, /data-ai-changes-tab="routes"/);
  assert.match(transportHtml, /data-ai-changes-tab="audit"/);
  assert.match(transportHtml, /data-ai-changes-vehicles/);
  assert.match(transportHtml, /data-ai-changes-passengers/);
  assert.match(transportHtml, /data-ai-changes-routes/);
  assert.match(transportHtml, /data-ai-changes-audit/);
  assert.match(transportHtml, /data-ai-changes-cancel/);
  assert.match(transportHtml, /data-ai-changes-save/);
  assert.match(transportHtml, /data-ai-changes-apply/);

  assert.match(transportCss, /\.transport-ai-changes-modal\s*\{[\s\S]*width:\s*min\(100%,\s*1120px\)/);
  assert.match(transportCss, /\.transport-ai-changes-tabs\s*\{[\s\S]*overflow-x:\s*auto/);
  assert.match(transportCss, /\.transport-ai-changes-panels\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/);
  assert.match(
    transportCss,
    /@media \(max-width: 860px\) \{[\s\S]*\.transport-ai-changes-hero,[\s\S]*\.transport-ai-changes-panels\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/
  );
  assert.match(
    transportCss,
    /@media \(max-width: 640px\) \{[\s\S]*\.transport-ai-changes-actions\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/
  );
});

test('transport ai changes summary render formats savings from the suggestion payload without recalculating dashboard state', () => {
  const summaryModel = transportPage.renderAiChangesSummary({
    runStatusResponse: {
      run_key: 'transport-ai-run:summary-savings',
      status: 'proposed',
      route_kind: 'home_to_work',
      service_date: '2026-06-13',
      message: 'Transport AI suggestion is ready for review.',
      suggestion: {
        status: 'shown',
        prompt_version: 'transport_ai_route_planner_v1',
        plan: {
          objective_summary: 'Minimize total transport cost while keeping the operational changes small.',
          route_kind: 'home_to_work',
          earliest_boarding_time: '06:50',
          arrival_at_work_time: '07:45',
          passenger_allocations: [
            { request_id: 101 },
            { request_id: 102 },
          ],
          route_itineraries: [
            { vehicle_ref: 'existing:11' },
          ],
          cost_summary: {
            price_currency_code: 'USD',
            price_rate_unit: 'day',
            current_total_estimated_cost: 120,
            suggested_total_estimated_cost: 95,
            estimated_cost_delta: -25,
            current_vehicle_count: 2,
            suggested_vehicle_count: 1,
          },
          change_summary: {
            total_vehicle_actions: 2,
            keep_count: 0,
            create_count: 0,
            update_count: 1,
            remove_from_day_count: 1,
            by_vehicle_type: [],
          },
          validation_issues: [
            {
              code: 'transport_ai_request_unallocated',
              message: 'One passenger still needs manual review.',
              blocking: true,
            },
          ],
        },
      },
    },
    fallbackCurrencyCode: 'SGD',
  });

  assert.equal(summaryModel.cost.deltaDirection, 'savings');
  assert.equal(summaryModel.cost.deltaLabel, 'Savings');
  assert.equal(summaryModel.vehicles.comparisonText, '2 -> 1');
  assert.equal(summaryModel.passengers.allocatedText, '2 allocated');
  assert.equal(summaryModel.passengers.issueText, '1 issue');
  assert.equal(summaryModel.window.displayText, '06:50 -> 07:45');
  assert.equal(summaryModel.runtime.promptVersionText, 'transport_ai_route_planner_v1');
  assert.equal(summaryModel.runtime.routeProviderText, '--');
  assert.equal(summaryModel.runtime.modelText, '--');
  assert.equal(summaryModel.statusBadges[0].text, 'Run Proposed');
  assert.match(summaryModel.cost.suggestedText, /95\.00/);
  assert.equal(summaryModel.topCards[0].badges[0].text, 'Savings $25.00');
});

test('transport ai changes summary render shows increases and controlled placeholders for missing values', () => {
  const increasedSummaryModel = transportPage.renderAiChangesSummary({
    runStatusResponse: {
      run_key: 'transport-ai-run:summary-increase',
      status: 'saved',
      route_kind: 'home_to_work',
      service_date: '2026-06-20',
      message: 'Transport AI suggestion was saved and is ready to be applied.',
      route_provider: 'mapbox',
      openai_model: 'gpt-5-2025-08-07',
      suggestion: {
        status: 'saved',
        prompt_version: 'transport_ai_route_planner_v1',
        plan: {
          objective_summary: 'Review the operational tradeoff before applying the saved plan.',
          route_kind: 'home_to_work',
          earliest_boarding_time: '06:55',
          arrival_at_work_time: '07:50',
          passenger_allocations: [],
          route_itineraries: [],
          cost_summary: {
            price_currency_code: 'EUR',
            price_rate_unit: 'day',
            current_total_estimated_cost: 80,
            suggested_total_estimated_cost: 120,
            estimated_cost_delta: 40,
            current_vehicle_count: 1,
            suggested_vehicle_count: 2,
          },
          change_summary: {
            total_vehicle_actions: 1,
            keep_count: 0,
            create_count: 1,
            update_count: 0,
            remove_from_day_count: 0,
            by_vehicle_type: [],
          },
          validation_issues: [],
        },
      },
    },
  });

  const placeholderSummaryModel = transportPage.renderAiChangesSummary({
    runStatusResponse: {
      run_key: 'transport-ai-run:summary-placeholder',
      status: 'proposed',
      route_kind: 'home_to_work',
      service_date: '2026-06-21',
      message: '',
      suggestion: {
        status: 'shown',
        prompt_version: '',
        plan: {
          objective_summary: '',
          route_kind: 'home_to_work',
          earliest_boarding_time: '',
          arrival_at_work_time: '',
          passenger_allocations: [],
          route_itineraries: [],
          cost_summary: {},
          change_summary: {},
          validation_issues: [],
        },
      },
    },
  });

  assert.equal(increasedSummaryModel.cost.deltaDirection, 'increase');
  assert.equal(increasedSummaryModel.cost.deltaLabel, 'Increase');
  assert.equal(increasedSummaryModel.runtime.routeProviderText, 'mapbox');
  assert.equal(increasedSummaryModel.runtime.modelText, 'gpt-5-2025-08-07');
  assert.match(increasedSummaryModel.cost.deltaText, /40\.00/);

  assert.equal(placeholderSummaryModel.cost.currentText, '--');
  assert.equal(placeholderSummaryModel.cost.suggestedText, '--');
  assert.equal(placeholderSummaryModel.window.displayText, '-- -> --');
  assert.equal(placeholderSummaryModel.runtime.promptVersionText, '--');
  assert.equal(placeholderSummaryModel.runtime.routeProviderText, '--');
  assert.equal(placeholderSummaryModel.topCards[1].note, '--');
});

test('transport ai vehicle changes render maps create actions to add badges and before-after fields', () => {
  const vehicleChangesModel = transportPage.renderAiVehicleChanges({
    runStatusResponse: {
      suggestion: {
        plan: {
          cost_summary: {
            price_currency_code: 'USD',
          },
          vehicle_actions: [
            {
              action_key: 'vehicle:create:1',
              action_type: 'create',
              service_scope: 'extra',
              client_vehicle_key: 'draft:1',
              after: {
                vehicle_type: 'van',
                capacity: 15,
                plate: 'NEW1234',
                service_scope: 'extra',
                estimated_cost: 32,
              },
              rationale: 'Add overflow capacity for the extra request list.',
              cost_delta: 32,
            },
          ],
        },
      },
    },
  });

  const actionItem = vehicleChangesModel.items[0];
  const typeField = actionItem.fieldRows.find((fieldRow) => fieldRow.label === 'Type');
  const seatsField = actionItem.fieldRows.find((fieldRow) => fieldRow.label === 'Seats');
  const identifierField = actionItem.fieldRows.find((fieldRow) => fieldRow.label === 'Identifier');
  const listField = actionItem.fieldRows.find((fieldRow) => fieldRow.label === 'List');
  const costField = actionItem.fieldRows.find((fieldRow) => fieldRow.label === 'Cost');

  assert.equal(actionItem.actionLabel, 'Add');
  assert.equal(actionItem.actionTone, 'success');
  assert.equal(actionItem.badges[1].text, 'Extra List');
  assert.equal(typeField.valueText, '-- -> Van');
  assert.equal(seatsField.valueText, '-- -> 15');
  assert.equal(identifierField.valueText, '-- -> NEW1234');
  assert.equal(listField.valueText, '-- -> Extra List');
  assert.match(costField.valueText, /\$0\.00 -> \$32\.00/);
  assert.equal(costField.note, 'Delta +$32.00');
});

test('transport ai vehicle changes render highlights update, remove, and keep actions with the expected tones', () => {
  const vehicleChangesModel = transportPage.renderAiVehicleChanges({
    runStatusResponse: {
      suggestion: {
        plan: {
          cost_summary: {
            price_currency_code: 'USD',
          },
          vehicle_actions: [
            {
              action_key: 'vehicle:update:1',
              action_type: 'update',
              service_scope: 'regular',
              vehicle_id: 41,
              before: {
                vehicle_type: 'carro',
                capacity: 4,
                plate: 'UPD1234',
                service_scope: 'regular',
                estimated_cost: 20,
              },
              after: {
                vehicle_type: 'van',
                capacity: 12,
                plate: 'UPD1234',
                service_scope: 'regular',
                estimated_cost: 34,
              },
              rationale: 'Upgrade the assigned vehicle to fit the passenger count.',
              cost_delta: 14,
            },
            {
              action_key: 'vehicle:remove:1',
              action_type: 'remove_from_day',
              service_scope: 'weekend',
              vehicle_id: 52,
              before: {
                vehicle_type: 'minivan',
                capacity: 7,
                plate: 'REM1234',
                service_scope: 'weekend',
                estimated_cost: 18,
              },
              rationale: 'Remove the weekend vehicle because the route is no longer required.',
              cost_delta: -18,
            },
            {
              action_key: 'vehicle:keep:1',
              action_type: 'keep',
              service_scope: 'regular',
              vehicle_id: 63,
              before: {
                vehicle_type: 'carro',
                capacity: 4,
                plate: 'KEEP123',
                service_scope: 'regular',
                estimated_cost: 11,
              },
              after: {
                vehicle_type: 'carro',
                capacity: 4,
                plate: 'KEEP123',
                service_scope: 'regular',
                estimated_cost: 11,
              },
              rationale: 'Keep the current assignment unchanged.',
              cost_delta: 0,
            },
          ],
        },
      },
    },
  });

  const updateItem = vehicleChangesModel.items[0];
  const removeItem = vehicleChangesModel.items[1];
  const keepItem = vehicleChangesModel.items[2];
  const updateTypeField = updateItem.fieldRows.find((fieldRow) => fieldRow.label === 'Type');
  const updateSeatsField = updateItem.fieldRows.find((fieldRow) => fieldRow.label === 'Seats');
  const removeTypeField = removeItem.fieldRows.find((fieldRow) => fieldRow.label === 'Type');

  assert.equal(updateItem.actionTone, 'warning');
  assert.equal(updateItem.isSensitive, true);
  assert.equal(updateTypeField.valueText, 'Car -> Van');
  assert.equal(updateSeatsField.valueText, '4 -> 12');
  assert.equal(updateItem.badges[2].text, 'Sensitive Change');

  assert.equal(removeItem.actionTone, 'error');
  assert.equal(removeItem.isSensitive, true);
  assert.equal(removeTypeField.valueText, 'Minivan -> Removed from selected day');
  assert.equal(removeItem.badges[2].tone, 'error');

  assert.equal(keepItem.actionTone, 'neutral');
  assert.equal(keepItem.isSensitive, false);
  assert.equal(keepItem.badges.some((badge) => badge.text === 'Sensitive Change'), false);
});

test('transport ai passenger allocations render keeps the pickup order and exposes not-routed requests', () => {
  const passengerAllocationsModel = transportPage.renderAiPassengerAllocations({
    runStatusResponse: {
      suggestion: {
        plan: {
          passenger_allocations: [
            {
              request_id: 202,
              request_kind: 'extra',
              service_date: '2026-06-13',
              route_kind: 'home_to_work',
              vehicle_ref: 'existing:11',
              user_id: 402,
              chave: 'USR402',
              nome: 'Bob Lim',
              project_name: 'P80',
              pickup_order: 1,
              scheduled_pickup_time: '07:12',
              projected_arrival_time: '07:45',
              rationale: 'Keep the extra passenger on the shared route.',
            },
            {
              request_id: 201,
              request_kind: 'extra',
              service_date: '2026-06-13',
              route_kind: 'home_to_work',
              vehicle_ref: 'existing:11',
              user_id: 401,
              chave: 'USR401',
              nome: 'Alice Tan',
              project_name: 'P80',
              pickup_order: 0,
              scheduled_pickup_time: '07:05',
              projected_arrival_time: '07:45',
              rationale: 'Pick up the closest passenger first.',
            },
          ],
          route_itineraries: [
            {
              route_key: 'route:existing:11',
              partition_key: 'extra:P80:SG',
              vehicle_ref: 'existing:11',
              service_scope: 'extra',
              route_kind: 'home_to_work',
              vehicle_type: 'van',
              vehicle_id: 11,
              plate: 'SGX1111',
              project_name: 'P80',
              country_code: 'SG',
              country_name: 'Singapore',
              estimated_cost: 24,
              total_duration_seconds: 2400,
              total_distance_meters: 9800,
              projected_arrival_time: '07:45',
              stops: [],
            },
          ],
          validation_issues: [
            {
              code: 'transport_ai_request_unallocated',
              message: 'Passenger still needs manual review.',
              blocking: true,
              request_id: 203,
            },
          ],
        },
      },
    },
  });

  const firstPassenger = passengerAllocationsModel.items[0];
  const secondPassenger = passengerAllocationsModel.items[1];
  const firstVehicleField = firstPassenger.fieldRows.find((fieldRow) => fieldRow.label === 'Vehicle');
  const firstPickupOrderField = firstPassenger.fieldRows.find((fieldRow) => fieldRow.label === 'Pickup Order');

  assert.equal(firstPassenger.titleText, 'Alice Tan');
  assert.equal(secondPassenger.titleText, 'Bob Lim');
  assert.equal(firstPassenger.badges[0].text, 'Extra');
  assert.equal(firstVehicleField.valueText, 'SGX1111');
  assert.equal(firstPickupOrderField.valueText, '#1');
  assert.equal(passengerAllocationsModel.unallocatedItems[0].titleText, 'Request #203');
  assert.equal(passengerAllocationsModel.unallocatedItems[0].badges[0].text, 'Not Routed');
});

test('transport ai route itineraries render preserves stop order and ends at the destination', () => {
  const routeItinerariesModel = transportPage.renderAiRouteItineraries({
    runStatusResponse: {
      suggestion: {
        plan: {
          cost_summary: {
            price_currency_code: 'USD',
          },
          route_itineraries: [
            {
              route_key: 'route:11',
              partition_key: 'extra:P80:SG',
              vehicle_ref: 'existing:11',
              service_scope: 'extra',
              route_kind: 'home_to_work',
              vehicle_type: 'van',
              vehicle_id: 11,
              plate: 'ROUTE123',
              project_name: 'P80',
              country_code: 'SG',
              country_name: 'Singapore',
              estimated_cost: 28,
              total_duration_seconds: 2100,
              total_distance_meters: 12400,
              projected_arrival_time: '07:45',
              stops: [
                {
                  stop_order: 2,
                  stop_type: 'destination',
                  project_name: 'P80',
                  address: '1 Industrial Road',
                  zip_code: '123456',
                  country_code: 'SG',
                  longitude: 103.8,
                  latitude: 1.3,
                  scheduled_time: '07:45',
                  duration_from_previous_seconds: 720,
                  distance_from_previous_meters: 6800,
                },
                {
                  stop_order: 0,
                  stop_type: 'pickup',
                  request_id: 201,
                  user_id: 401,
                  passenger_name: 'Alice Tan',
                  project_name: 'P80',
                  address: '7 Garden Street',
                  zip_code: '100001',
                  country_code: 'SG',
                  longitude: 103.81,
                  latitude: 1.31,
                  scheduled_time: '07:10',
                  duration_from_previous_seconds: 0,
                  distance_from_previous_meters: 0,
                },
                {
                  stop_order: 1,
                  stop_type: 'pickup',
                  request_id: 202,
                  user_id: 402,
                  passenger_name: 'Bob Lim',
                  project_name: 'P80',
                  address: '10 River Drive',
                  zip_code: '100002',
                  country_code: 'SG',
                  longitude: 103.82,
                  latitude: 1.32,
                  scheduled_time: '07:18',
                  duration_from_previous_seconds: 480,
                  distance_from_previous_meters: 5600,
                },
              ],
            },
          ],
        },
      },
    },
  });

  const routeItem = routeItinerariesModel.items[0];
  const durationField = routeItem.fieldRows.find((fieldRow) => fieldRow.label === 'Duration');
  const costField = routeItem.fieldRows.find((fieldRow) => fieldRow.label === 'Cost');

  assert.equal(routeItem.titleText, 'ROUTE123');
  assert.deepEqual(routeItem.stopItems.map((stopItem) => stopItem.stopType), ['pickup', 'pickup', 'destination']);
  assert.equal(routeItem.stopItems[0].titleText, 'Alice Tan');
  assert.equal(routeItem.stopItems[2].isDestination, true);
  assert.equal(durationField.valueText, '35 min');
  assert.equal(durationField.note, '12 km');
  assert.match(costField.valueText, /\$28\.00/);
});

test('transport ai changes summary markup and styles keep a dedicated summary panel with wrapped executive text', () => {
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

  assert.match(transportHtml, /data-ai-changes-summary-panel/);
  assert.match(transportScript, /function renderAiChangesSummary\(options\) \{/);
  assert.match(
    transportScript,
    /renderAiChangesSummary\(\{[\s\S]*summaryGridElement: aiChangesSummaryGrid,[\s\S]*summaryPanelElement: aiChangesSummaryPanel/
  );
  assert.match(transportCss, /\.transport-ai-changes-objective-summary,[\s\S]*overflow-wrap:\s*anywhere/);
  assert.match(transportCss, /\.transport-ai-changes-executive-grid\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/);
  assert.match(transportCss, /@media \(max-width: 860px\) \{[\s\S]*\.transport-ai-changes-executive-grid\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
});

test('transport ai vehicle changes markup and styles keep a dedicated dense vehicle panel', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportScript, /const aiChangesVehiclesPanel = document\.querySelector\("\[data-ai-changes-vehicles\]"\);/);
  assert.match(transportScript, /function renderAiVehicleChanges\(options\) \{/);
  assert.match(transportScript, /function syncAiVehicleChangesRender\(\) \{[\s\S]*vehiclesPanelElement: aiChangesVehiclesPanel,/);
  assert.match(transportCss, /\.transport-ai-changes-vehicle-list\s*\{[\s\S]*display:\s*grid/);
  assert.match(transportCss, /\.transport-ai-changes-vehicle-grid\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/);
  assert.match(transportCss, /@media \(max-width: 860px\) \{[\s\S]*\.transport-ai-changes-vehicle-grid\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
});

test('transport ai passenger and route panels keep dedicated render hooks and responsive styles', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportScript, /const aiChangesPassengersPanel = document\.querySelector\("\[data-ai-changes-passengers\]"\);/);
  assert.match(transportScript, /const aiChangesRoutesPanel = document\.querySelector\("\[data-ai-changes-routes\]"\);/);
  assert.match(transportScript, /function renderAiPassengerAllocations\(options\) \{/);
  assert.match(transportScript, /function renderAiRouteItineraries\(options\) \{/);
  assert.match(transportScript, /function syncAiPassengerAllocationsRender\(\) \{[\s\S]*passengersPanelElement: aiChangesPassengersPanel,/);
  assert.match(transportScript, /function syncAiRouteItinerariesRender\(\) \{[\s\S]*routesPanelElement: aiChangesRoutesPanel,/);
  assert.match(transportCss, /\.transport-ai-changes-passenger-list,\s*[\s\S]*\.transport-ai-changes-route-list\s*\{[\s\S]*display:\s*grid/);
  assert.match(transportCss, /\.transport-ai-changes-stop-list\s*\{[\s\S]*display:\s*grid/);
  assert.match(transportCss, /@media \(max-width: 860px\) \{[\s\S]*\.transport-ai-changes-passenger-grid,[\s\S]*\.transport-ai-changes-vehicle-grid\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
  assert.match(transportCss, /@media \(max-width: 860px\) \{[\s\S]*\.transport-ai-changes-route-grid\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
});

test('transport ai dashboard bootstrap keeps the new ai elements wired and opens the settings modal with default values', async () => {
  await withTransportPageHarness({}, async ({ getElement, fetchCalls }) => {
    assert.ok(global.CheckingTransportPageController);
    assert.ok(fetchCalls.some((call) => call.url.includes('/auth/session')));
    assert.ok(fetchCalls.some((call) => call.url.includes('/dashboard?')));
    assert.ok(fetchCalls.some((call) => call.url.includes('/settings')));

    const calculateRoutesButton = getElement('[data-ai-menu-action="calculate-routes"]');
    assert.equal(calculateRoutesButton.disabled, false);

    calculateRoutesButton.click();

    assert.equal(getElement('[data-ai-agent-modal]').hidden, false);
    assert.equal(getElement('[data-ai-agent-earliest-boarding]').value, '06:50');
    assert.equal(getElement('[data-ai-agent-arrival-at-work]').value, '07:45');
    assert.equal(getElement('[data-ai-agent-submit]').textContent, 'Request Routes');
  });
});

test('transport ai settings modal opens from the AI menu, loads masked state, and cancel closes without save request', async () => {
  await withTransportPageHarness({}, async ({ document, getElement, fetchCalls, flushAsyncWork }) => {
    assert.deepEqual(
      document
        .querySelectorAll('[data-ai-menu-action]')
        .map((element) => element.getAttribute('data-ai-menu-action')),
      ['calculate-routes', 'implement-modifications', 'settings']
    );

    getElement('[data-ai-menu-action="settings"]').click();
    await flushAsyncWork();

    const putCallsBeforeCancel = fetchCalls.filter(
      (call) => call.method === 'PUT' && call.url.includes('/ai/settings')
    ).length;
    const providerField = getElement('[data-ai-settings-provider]');
    const apiKeyField = getElement('[data-ai-settings-api-key]');

    assert.ok(fetchCalls.some((call) => call.method === 'GET' && call.url.includes('/ai/settings')));
    assert.equal(getElement('[data-ai-settings-modal]').hidden, false);
    assert.equal(providerField.tagName, 'SELECT');
    assert.equal(providerField.value, 'openai');
    assert.equal(apiKeyField.tagName, 'INPUT');
    assert.equal(apiKeyField.type, 'password');
    assert.equal(apiKeyField.value, '');
    assert.match(getElement('[data-ai-settings-provider-note]').textContent, /gpt-5\.4-2026-03-05/);
    assert.match(getElement('[data-ai-settings-api-key-hint]').textContent, /\*\*\*1234/);

    getElement('[data-ai-settings-cancel]').click();

    assert.equal(getElement('[data-ai-settings-modal]').hidden, true);
    assert.equal(
      fetchCalls.filter((call) => call.method === 'PUT' && call.url.includes('/ai/settings')).length,
      putCallsBeforeCancel
    );
  });
});

test('transport ai settings save flow updates the provider note, posts the trimmed payload, and closes on success', async () => {
  await withTransportPageHarness(
    {
      aiSettingsPutResponse: {
        provider: 'deepseek',
        resolved_model: 'deepseek-v4-pro',
        reasoning_effort: 'high',
        has_api_key: true,
        api_key_hint: '***9999',
      },
    },
    async ({ getElement, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      const providerField = getElement('[data-ai-settings-provider]');
      providerField.value = 'deepseek';
      providerField.dispatchEvent(createFakeEvent('change', { target: providerField }));
      assert.match(getElement('[data-ai-settings-provider-note]').textContent, /deepseek-v4-pro/i);
      assert.match(getElement('[data-ai-settings-api-key-hint]').textContent, /requires a new api key/i);

      const apiKeyField = getElement('[data-ai-settings-api-key]');
      apiKeyField.value = '  sk-test-9999  ';
      apiKeyField.dispatchEvent(createFakeEvent('input', { target: apiKeyField }));

      getElement('[data-ai-settings-save]').click();
      await flushAsyncWork();

      const saveCall = fetchCalls.find((call) => call.method === 'PUT' && call.url.includes('/ai/settings'));
      assert.ok(saveCall);
      assert.deepEqual(JSON.parse(saveCall.body), {
        provider: 'deepseek',
        api_key: 'sk-test-9999',
      });
      assert.equal(getElement('[data-ai-settings-modal]').hidden, true);
      assert.equal(getElement('[data-status-message]').textContent, 'AI settings saved.');
    }
  );
});

test('transport ai settings save errors keep the modal open with inline feedback', async () => {
  await withTransportPageHarness(
    {
      aiSettingsPutError: {
        status: 409,
        payload: {
          detail: 'Transport AI API key is required when changing the LLM provider.',
        },
      },
    },
    async ({ getElement, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      const providerField = getElement('[data-ai-settings-provider]');
      providerField.value = 'deepseek';
      providerField.dispatchEvent(createFakeEvent('change', { target: providerField }));

      getElement('[data-ai-settings-save]').click();
      await flushAsyncWork();

      assert.equal(getElement('[data-ai-settings-modal]').hidden, false);
      assert.equal(getElement('[data-ai-settings-feedback]').hidden, false);
      assert.match(getElement('[data-ai-settings-feedback]').textContent, /requires a new api key/i);
    }
  );
});

test('transport ai settings modal shows a controlled warning when the session expires during load', async () => {
  await withTransportPageHarness(
    {
      aiSettingsGetError: {
        status: 401,
        payload: {
          detail: 'Sessao de transporte invalida ou expirada',
        },
      },
    },
    async ({ getElement, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      assert.equal(getElement('[data-ai-settings-modal]').hidden, false);
      assert.equal(getElement('[data-ai-settings-feedback]').hidden, false);
      assert.equal(getElement('[data-ai-settings-feedback]').textContent, 'Transport session expired. Enter key and password again.');
      assert.equal(getElement('[data-status-message]').textContent, 'Transport session expired. Enter key and password again.');
    }
  );
});

test('transport ai settings modal keeps a controlled message when the saved provider is no longer supported', async () => {
  await withTransportPageHarness(
    {
      aiSettingsGetError: {
        status: 409,
        payload: {
          detail: 'The configured Transport AI LLM provider is no longer supported. Select OpenAI or DeepSeek and save the AI settings again.',
        },
      },
    },
    async ({ getElement, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      assert.equal(getElement('[data-ai-settings-modal]').hidden, false);
      assert.equal(getElement('[data-ai-settings-provider]').value, 'openai');
      assert.equal(getElement('[data-ai-settings-feedback]').hidden, false);
      assert.equal(
        getElement('[data-ai-settings-feedback]').textContent,
        'The saved AI provider is no longer supported. Select OpenAI or DeepSeek and save again.'
      );
    }
  );
});

test('transport ai settings save surfaces the encryption-unavailable error without closing the modal', async () => {
  await withTransportPageHarness(
    {
      aiSettingsPutError: {
        status: 503,
        payload: {
          detail: 'Transport AI settings encryption is unavailable.',
        },
      },
    },
    async ({ getElement, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      const apiKeyField = getElement('[data-ai-settings-api-key]');
      apiKeyField.value = 'sk-encryption-1234';
      apiKeyField.dispatchEvent(createFakeEvent('input', { target: apiKeyField }));

      getElement('[data-ai-settings-save]').click();
      await flushAsyncWork();

      assert.equal(getElement('[data-ai-settings-modal]').hidden, false);
      assert.equal(getElement('[data-ai-settings-feedback]').hidden, false);
      assert.equal(getElement('[data-ai-settings-feedback]').textContent, 'Transport AI settings encryption is unavailable.');
    }
  );
});

test('transport ai settings modal does not close while a save request is still pending', async () => {
  const pendingSave = createDeferred();

  await withTransportPageHarness(
    {
      aiSettingsPutHandler() {
        return pendingSave.promise;
      },
    },
    async ({ getElement, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      const apiKeyField = getElement('[data-ai-settings-api-key]');
      apiKeyField.value = 'sk-pending-1234';
      apiKeyField.dispatchEvent(createFakeEvent('input', { target: apiKeyField }));

      getElement('[data-ai-settings-save]').click();
      await flushAsyncWork();

      getElement('[data-ai-settings-cancel]').click();
      assert.equal(getElement('[data-ai-settings-modal]').hidden, false);

      const modalElement = getElement('[data-ai-settings-modal]');
      modalElement.dispatchEvent(createFakeEvent('click', { target: modalElement }));
      assert.equal(getElement('[data-ai-settings-modal]').hidden, false);

      pendingSave.resolve(
        createFetchResponse(
          {
            provider: 'openai',
            resolved_model: 'gpt-5.4-2026-03-05',
            reasoning_effort: 'high',
            has_api_key: true,
            api_key_hint: '***1234',
          },
          200
        )
      );
      await flushAsyncWork();

      assert.equal(getElement('[data-ai-settings-modal]').hidden, true);
    }
  );
});

test('transport ai implement modifications renders the latest suggestion into the review modal panels', async () => {
  await withTransportPageHarness(
    {
      latestSuggestionResponse: getSampleLatestSuggestionResponse(),
    },
    async ({ getElement, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="implement-modifications"]').click();
      await flushAsyncWork();

      assert.ok(fetchCalls.some((call) => call.url.includes('/ai/suggestions/latest')));
      assert.equal(getElement('[data-ai-changes-modal]').hidden, false);
      assert.match(getElement('[data-ai-changes-status]').textContent, /ready for review/i);
      assert.ok(getElement('[data-ai-changes-summary-grid]').children.length > 0);
      assert.match(getElement('[data-ai-changes-summary-panel]').textContent, /Cut costs while keeping one route stable/i);
      assert.match(getElement('[data-ai-changes-vehicles]').textContent, /SGX1234/);
      assert.match(getElement('[data-ai-changes-passengers]').textContent, /Alice Tan/);
      assert.match(getElement('[data-ai-changes-routes]').textContent, /Industrial Road/);
    }
  );
});

test('transport ai save command posts the saved review action without refreshing the dashboard', async () => {
  await withTransportPageHarness(
    {
      latestSuggestionResponse: getSampleLatestSuggestionResponse(),
      commandResponses: {
        save: getSuggestionCommandSuccessResponse('save'),
      },
    },
    async ({ getElement, countFetchCalls, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="implement-modifications"]').click();
      await flushAsyncWork();

      const dashboardRequestCount = countFetchCalls('/dashboard?');
      getElement('[data-ai-changes-save]').click();
      await flushAsyncWork();

      assert.ok(fetchCalls.some((call) => call.method === 'POST' && call.url.endsWith('/save')));
      assert.equal(countFetchCalls('/dashboard?'), dashboardRequestCount);
      assert.equal(getElement('[data-ai-changes-modal]').hidden, true);
      assert.match(getElement('[data-status-message]').textContent, /saved/i);
    }
  );
});

test('transport ai apply command posts the apply action and refreshes the dashboard', async () => {
  await withTransportPageHarness(
    {
      latestSuggestionResponse: getSampleLatestSuggestionResponse(),
      commandResponses: {
        apply: getSuggestionCommandSuccessResponse('apply'),
      },
    },
    async ({ getElement, countFetchCalls, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="implement-modifications"]').click();
      await flushAsyncWork();

      const dashboardRequestCount = countFetchCalls('/dashboard?');
      getElement('[data-ai-changes-apply]').click();
      await flushAsyncWork();

      assert.ok(fetchCalls.some((call) => call.method === 'POST' && call.url.endsWith('/apply')));
      assert.equal(countFetchCalls('/dashboard?'), dashboardRequestCount + 1);
      assert.equal(getElement('[data-ai-changes-modal]').hidden, true);
      assert.match(getElement('[data-status-message]').textContent, /applied/i);
    }
  );
});

test('transport ai cancel command posts the cancel action and refreshes the dashboard', async () => {
  await withTransportPageHarness(
    {
      latestSuggestionResponse: getSampleLatestSuggestionResponse(),
      commandResponses: {
        cancel: getSuggestionCommandSuccessResponse('cancel'),
      },
    },
    async ({ getElement, countFetchCalls, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="implement-modifications"]').click();
      await flushAsyncWork();

      const dashboardRequestCount = countFetchCalls('/dashboard?');
      getElement('[data-ai-changes-cancel]').click();
      await flushAsyncWork();

      assert.ok(fetchCalls.some((call) => call.method === 'POST' && call.url.endsWith('/cancel')));
      assert.equal(countFetchCalls('/dashboard?'), dashboardRequestCount + 1);
      assert.equal(getElement('[data-ai-changes-modal]').hidden, true);
      assert.match(getElement('[data-status-message]').textContent, /cancelled/i);
    }
  );
});

test('transport settings pricing helpers normalize currency options and price defaults safely', () => {
  assert.equal(transportPage.normalizeTransportCurrencyCode(' sgd '), 'SGD');
  assert.equal(transportPage.normalizeTransportPriceRateUnit('week', 'day'), 'week');
  assert.equal(transportPage.normalizeTransportPriceRateUnit('invalid', 'day'), 'day');
  assert.deepEqual(
    transportPage.resolveTransportCurrencyOptions([
      { code: 'usd', display_label: 'US Dollar' },
      { code: 'USD', display_label: 'Duplicate USD' },
      { code: '', display_label: 'Ignored' },
    ]),
    [{ code: 'USD', display_label: 'US Dollar' }]
  );
  assert.deepEqual(
    transportPage.resolveTransportVehiclePriceDefaults(
      {
        default_car_price: '12.5',
        default_minivan_price: '',
        default_van_price: null,
        default_bus_price: 99,
      },
      {
        carro: null,
        minivan: 10,
        van: 20,
        onibus: 30,
      }
    ),
    {
      carro: 12.5,
      minivan: null,
      van: null,
      onibus: 99,
    }
  );
  assert.equal(transportPage.formatTransportPriceInputValue(12.5), '12.50');
  assert.equal(transportPage.formatTransportCurrencyOptionLabel({ code: 'SGD', display_label: 'Singapore Dollar' }), 'SGD - Singapore Dollar');
});

test('applyTransportVehicleToleranceDefault updates the shared vehicle form tolerance default', () => {
  assert.equal(transportPage.getDefaultVehicleToleranceMinutes(), 5);
  assert.equal(transportPage.applyTransportVehicleToleranceDefault(9), 9);
  assert.equal(transportPage.getDefaultVehicleToleranceMinutes(), 9);
  assert.equal(transportPage.applyTransportVehicleToleranceDefault(0), 0);
  assert.equal(transportPage.getDefaultVehicleToleranceMinutes(), 0);
  assert.equal(transportPage.applyTransportVehicleToleranceDefault(undefined), 0);
  assert.equal(transportPage.getDefaultVehicleToleranceMinutes(), 0);
  transportPage.applyTransportVehicleToleranceDefault(5);
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

test('buildVehiclePassengerAwarenessRows keeps only assigned passengers without blank filler rows', () => {
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
    ]
  );
});

test('buildVehiclePassengerAwarenessRows caps the visible rows to the requested maximum', () => {
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
    ]
  );
});

test('buildVehiclePassengerAwarenessRows returns an empty list when no passengers are assigned', () => {
  assert.deepEqual(transportPage.buildVehiclePassengerAwarenessRows([], 5), []);
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
  assert.doesNotMatch(transportScript, /\brouteSelect\b/);
  assert.match(transportScript, /const shouldShowRouteTime = true;/);
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

test('transport vehicle modal stays viewport-safe after adding the extra departure date field', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(
    transportCss,
    /\.transport-modal\s*\{[\s\S]*max-height:\s*calc\(100dvh - 48px\);[\s\S]*overflow:\s*auto;[\s\S]*overscroll-behavior:\s*contain;/
  );
  assert.match(
    transportCss,
    /@media \(max-width: 640px\) \{[\s\S]*\.transport-modal\s*\{[\s\S]*max-height:\s*calc\(100dvh - 24px\);/
  );
});

test('transport settings modal widens on desktop and collapses pricing controls earlier on medium widths', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(
    transportCss,
    /\.transport-settings-modal\s*\{[\s\S]*width:\s*min\(100%, 940px\);/
  );
  assert.match(
    transportCss,
    /@media \(max-width: 960px\) \{[\s\S]*\.transport-settings-row,[\s\S]*\.transport-settings-dual-row,[\s\S]*\.transport-settings-inline-controls,[\s\S]*\.transport-settings-add-currency-fields,[\s\S]*\.transport-vehicle-details-actions[\s\S]*grid-template-columns:\s*1fr;/
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

test('transport vehicle modal no longer blocks regular or weekend creation by the selected dashboard date', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(
    transportScript,
    /function canOpenVehicleModal\(scope\) \{[\s\S]*if \(!state\.isAuthenticated\) \{[\s\S]*return false;[\s\S]*\}[\s\S]*return true;[\s\S]*\}/
  );
  assert.doesNotMatch(
    transportScript,
    /function canOpenVehicleModal\(scope\) \{[\s\S]*isWeekendDate\(selectedDate\)/
  );
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

test('transport vehicle details expose a focused edit action for pending vehicles', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportScript, /function openVehicleEditModal\(vehicle\) \{/);
  assert.match(
    transportScript,
    /requestJson\(`\$\{TRANSPORT_API_PREFIX\}\/vehicles\/\$\{encodeURIComponent\(String\(vehicleId\)\)\}`, \{[\s\S]*method:\s*"PUT"/
  );
  assert.match(transportScript, /Array\.isArray\(vehicle\.pending_fields\) && vehicle\.pending_fields\.length/);
  assert.match(transportScript, /openVehicleEditModal\(vehicle\);/);
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

test('transport vehicle details show a compact empty passenger message instead of padded blank rows', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(
    transportScript,
    /createNode\("p", "transport-vehicle-passenger-empty", t\("empty\.noPassengersAssigned"\)\)/
  );
  assert.match(
    transportCss,
    /\.transport-vehicle-passenger-empty\s*\{[\s\S]*text-align:\s*center;/
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
      { id: 8, route_kind: null, is_ready_for_allocation: true },
      'home_to_work'
    ),
    true
  );
  assert.equal(
    transportPage.canRequestBeDroppedOnVehicle(
      { id: 10, request_kind: 'regular' },
      'weekend',
      { id: 8, route_kind: null, is_ready_for_allocation: true },
      'home_to_work'
    ),
    false
  );
  assert.equal(
    transportPage.canRequestBeDroppedOnVehicle(
      { id: 10, request_kind: 'extra', assigned_vehicle: { id: 8 } },
      'extra',
      { id: 8, route_kind: 'work_to_home', is_ready_for_allocation: true },
      'work_to_home'
    ),
    false
  );
  assert.equal(
    transportPage.canRequestBeDroppedOnVehicle(
      { id: 10, request_kind: 'extra' },
      'extra',
      { id: 8, route_kind: 'work_to_home', is_ready_for_allocation: true },
      'home_to_work'
    ),
    true
  );
  assert.equal(
    transportPage.canRequestBeDroppedOnVehicle(
      { id: 10, request_kind: 'regular' },
      'regular',
      { id: 8, route_kind: null, is_ready_for_allocation: false },
      'home_to_work'
    ),
    false
  );
});

test('vehicle allocation readiness helper falls back to required vehicle fields and exposes a stable warning message', () => {
  assert.equal(
    transportPage.isVehicleReadyForAllocation({ is_ready_for_allocation: false, tipo: 'carro', placa: 'SGX1001A', lugares: 4, tolerance: 5 }),
    false
  );
  assert.equal(
    transportPage.isVehicleReadyForAllocation({ tipo: 'carro', placa: 'SGX1001A', lugares: 4, tolerance: 5 }),
    true
  );
  assert.equal(
    transportPage.isVehicleReadyForAllocation({ tipo: null, placa: 'SGX1001A', lugares: 4, tolerance: 5 }),
    false
  );
  assert.equal(
    transportPage.getVehiclePendingAllocationMessage({ is_ready_for_allocation: false }),
    'This vehicle is still missing required allocation data.'
  );
});

test('buildVehicleCreatePayload keeps dashboard dates for regular and weekend vehicles and reads the form service date for extra vehicles', () => {
  const regularFormData = new FormData();
  regularFormData.set('service_scope', 'regular');
  regularFormData.set('tipo', 'carro');
  regularFormData.set('placa', 'ABC-1234.56-DE');
  regularFormData.set('color', 'Black');
  regularFormData.set('lugares', '4');
  regularFormData.set('tolerance', '12');
  regularFormData.set('every_monday', 'on');
  regularFormData.set('every_wednesday', 'on');
  regularFormData.set('route_kind', 'work_to_home');

  assert.deepEqual(
    transportPage.buildVehicleCreatePayload(regularFormData, '2026-04-18', 'home_to_work'),
    {
      service_scope: 'regular',
      service_date: '2026-04-18',
      tipo: 'carro',
      placa: 'ABC-1234.56-DE',
      color: 'Black',
      lugares: 4,
      tolerance: 12,
      every_monday: true,
      every_tuesday: false,
      every_wednesday: true,
      every_thursday: false,
      every_friday: false,
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
  extraFormData.set('service_date', '2026-05-02');
  extraFormData.set('departure_time', '17:45');
  extraFormData.set('route_kind', 'work_to_home');

  assert.deepEqual(
    transportPage.buildVehicleCreatePayload(extraFormData, '2026-04-18', 'home_to_work'),
    {
      service_scope: 'extra',
      service_date: '2026-05-02',
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

test('buildVehicleCreatePayload serializes empty extra base fields as null instead of fallback values', () => {
  const extraFormData = new FormData();
  extraFormData.set('service_scope', 'extra');
  extraFormData.set('tipo', '');
  extraFormData.set('placa', '   ');
  extraFormData.set('color', '');
  extraFormData.set('lugares', '');
  extraFormData.set('tolerance', '');
  extraFormData.set('service_date', '2026-05-02');
  extraFormData.set('departure_time', '17:45');
  extraFormData.set('route_kind', 'work_to_home');

  assert.deepEqual(
    transportPage.buildVehicleCreatePayload(extraFormData, '2026-04-18', 'home_to_work'),
    {
      service_scope: 'extra',
      service_date: '2026-05-02',
      tipo: null,
      placa: null,
      color: null,
      lugares: null,
      tolerance: null,
      departure_time: '17:45',
      route_kind: 'work_to_home',
    }
  );
});

test('buildVehicleCreatePayload serializes empty weekend and regular base fields as null while preserving persistence selections', () => {
  const weekendFormData = new FormData();
  weekendFormData.set('service_scope', 'weekend');
  weekendFormData.set('tipo', '');
  weekendFormData.set('placa', '   ');
  weekendFormData.set('color', '');
  weekendFormData.set('lugares', '');
  weekendFormData.set('tolerance', '');
  weekendFormData.set('every_sunday', 'on');

  assert.deepEqual(
    transportPage.buildVehicleCreatePayload(weekendFormData, '2026-04-18', 'home_to_work'),
    {
      service_scope: 'weekend',
      service_date: '2026-04-18',
      tipo: null,
      placa: null,
      color: null,
      lugares: null,
      tolerance: null,
      every_saturday: false,
      every_sunday: true,
    }
  );

  const regularFormData = new FormData();
  regularFormData.set('service_scope', 'regular');
  regularFormData.set('tipo', '');
  regularFormData.set('placa', '');
  regularFormData.set('color', '');
  regularFormData.set('lugares', '');
  regularFormData.set('tolerance', '');
  regularFormData.set('every_tuesday', 'on');

  assert.deepEqual(
    transportPage.buildVehicleCreatePayload(regularFormData, '2026-04-18', 'home_to_work'),
    {
      service_scope: 'regular',
      service_date: '2026-04-18',
      tipo: null,
      placa: null,
      color: null,
      lugares: null,
      tolerance: null,
      every_monday: false,
      every_tuesday: true,
      every_wednesday: false,
      every_thursday: false,
      every_friday: false,
    }
  );
});

test('syncVehicleTypeDependentDefaults allows the type field to stay blank', () => {
  const vehicleForm = {
    elements: {
      tipo: { value: 'carro' },
      lugares: { value: '3' },
      tolerance: { value: '5' },
    },
  };

  transportPage.syncVehicleTypeDependentDefaults('', vehicleForm);

  assert.equal(vehicleForm.elements.tipo.value, '');
  assert.equal(vehicleForm.elements.lugares.value, '3');
  assert.equal(vehicleForm.elements.tolerance.value, '5');
});

test('resolveVehicleModalOpenState prefills the extra modal service date and targets the date field for focus', () => {
  assert.deepEqual(
    transportPage.resolveVehicleModalOpenState('extra', '2026-05-02'),
    {
      serviceDateValue: '2026-05-02',
      departureTimeValue: '',
      initialFocusField: 'service_date',
      fallbackFocusField: 'departure_time',
    }
  );

  assert.deepEqual(
    transportPage.resolveVehicleModalOpenState('regular', '2026-05-02'),
    {
      serviceDateValue: '',
      departureTimeValue: '',
      initialFocusField: null,
      fallbackFocusField: null,
    }
  );
});

test('resolveVehicleCreateValidationError blocks extra submits without a departure date and focuses the date field', () => {
  assert.deepEqual(
    transportPage.resolveVehicleCreateValidationError({
      service_scope: 'extra',
      service_date: '',
      departure_time: '17:45',
      route_kind: 'home_to_work',
    }),
    {
      messageKey: 'warnings.extraServiceDateRequired',
      focusField: 'service_date',
    }
  );

  assert.equal(
    transportPage.resolveVehicleCreateValidationError({
      service_scope: 'extra',
      service_date: '2026-05-02',
      departure_time: '17:45',
      route_kind: 'home_to_work',
    }),
    null
  );
});

test('resolveVehicleCreateValidationError keeps weekend and regular requirements scoped to persistence selections', () => {
  assert.deepEqual(
    transportPage.resolveVehicleCreateValidationError({
      service_scope: 'weekend',
      tipo: null,
      placa: null,
      color: null,
      lugares: null,
      tolerance: null,
      every_saturday: false,
      every_sunday: false,
    }),
    {
      messageKey: 'warnings.weekendPersistence',
      focusField: null,
    }
  );

  assert.equal(
    transportPage.resolveVehicleCreateValidationError({
      service_scope: 'weekend',
      tipo: null,
      placa: null,
      color: null,
      lugares: null,
      tolerance: null,
      every_saturday: true,
      every_sunday: false,
    }),
    null
  );

  assert.deepEqual(
    transportPage.resolveVehicleCreateValidationError({
      service_scope: 'regular',
      tipo: null,
      placa: null,
      color: null,
      lugares: null,
      tolerance: null,
      every_monday: false,
      every_tuesday: false,
      every_wednesday: false,
      every_thursday: false,
      every_friday: false,
    }),
    {
      messageKey: 'warnings.regularPersistence',
      focusField: null,
    }
  );

  assert.equal(
    transportPage.resolveVehicleCreateValidationError({
      service_scope: 'regular',
      tipo: null,
      placa: null,
      color: null,
      lugares: null,
      tolerance: null,
      every_monday: false,
      every_tuesday: false,
      every_wednesday: false,
      every_thursday: true,
      every_friday: false,
    }),
    null
  );
});

test('resolveVehicleSaveReloadDate keeps the current dashboard date for regular and weekend saves and uses the form date for extra saves', () => {
  const fallbackDate = new Date(2026, 3, 18);

  assert.equal(
    transportPage.formatIsoDate(
      transportPage.resolveVehicleSaveReloadDate({ service_scope: 'regular', service_date: '2026-05-03' }, fallbackDate)
    ),
    '2026-04-18'
  );
  assert.equal(
    transportPage.formatIsoDate(
      transportPage.resolveVehicleSaveReloadDate({ service_scope: 'weekend', service_date: '2026-05-03' }, fallbackDate)
    ),
    '2026-04-18'
  );
  assert.equal(
    transportPage.formatIsoDate(
      transportPage.resolveVehicleSaveReloadDate({ service_scope: 'extra', service_date: '2026-05-03' }, fallbackDate)
    ),
    '2026-05-03'
  );
  assert.equal(
    transportPage.formatIsoDate(
      transportPage.resolveVehicleSaveReloadDate({ service_scope: 'extra', service_date: '' }, fallbackDate)
    ),
    '2026-04-18'
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
