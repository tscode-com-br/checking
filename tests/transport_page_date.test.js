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

function toStylePropertyName(propertyName) {
  const normalizedName = String(propertyName || '');
  if (normalizedName.startsWith('--')) {
    return normalizedName;
  }
  return normalizedName.replace(/-([a-z])/g, (_, character) => character.toUpperCase());
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
        this[toStylePropertyName(name)] = value;
      },
      removeProperty(name) {
        delete this[toStylePropertyName(name)];
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

function withFakeComputedStyle(styleMap, callback) {
  const previousGetComputedStyle = global.getComputedStyle;
  global.getComputedStyle = function () {
    return Object.assign({ rowGap: '0px', gap: '0px' }, styleMap || {});
  };

  try {
    return callback();
  } finally {
    if (previousGetComputedStyle === undefined) {
      delete global.getComputedStyle;
    } else {
      global.getComputedStyle = previousGetComputedStyle;
    }
  }
}

function appendVehicleGrid(parentElement, options) {
  const nextOptions = options || {};
  const gridElement = appendFakeElement(parentElement, 'div', {
    className: nextOptions.className
      ? `transport-vehicle-grid ${nextOptions.className}`
      : 'transport-vehicle-grid',
    attributes: { 'data-vehicle-scope': nextOptions.scope || 'extra' },
  });

  if (nextOptions.vehicleView) {
    gridElement.dataset.vehicleView = nextOptions.vehicleView;
  }

  gridElement.clientHeight = Number(nextOptions.clientHeight) || 0;

  const itemCount = nextOptions.itemCount === undefined ? 1 : Number(nextOptions.itemCount);
  const itemWidth = Number(nextOptions.itemWidth) || 120;
  const itemHeight = Number(nextOptions.itemHeight) || 60;

  for (let index = 0; index < itemCount; index += 1) {
    const button = appendFakeElement(gridElement, 'button', {
      className: 'transport-vehicle-button',
      type: 'button',
    });
    button.getBoundingClientRect = () => ({
      left: 0,
      top: 0,
      right: itemWidth,
      bottom: itemHeight,
      width: itemWidth,
      height: itemHeight,
    });
  }

  return gridElement;
}

function createTransportPageTestDocument() {
  const document = new FakeDocument();
  const body = document.body;

  document.visibilityState = 'visible';
  document.hidden = false;

  appendFakeElement(body, 'div', {
    textContent: 'Transport dashboard ready.',
    attributes: {
      'data-status-message': '',
      'data-i18n-text': 'status.ready',
    },
  });

  const transportTopbar = appendFakeElement(body, 'div', {
    attributes: { 'data-transport-topbar': '' },
  });
  appendFakeElement(transportTopbar, 'button', {
    type: 'button',
    textContent: 'Dashboard Settings',
    attributes: {
      'data-open-settings-modal': '',
      'data-i18n-text': 'settings.dashboardLink',
      'data-i18n-aria-label': 'settings.openAria',
      'data-i18n-title': 'settings.openAria',
    },
  });
  appendFakeElement(transportTopbar, 'span', {
    textContent: 'Work to Home Time:',
    attributes: {
      'data-route-time-label': '',
      'data-i18n-text': 'settings.workToHomeTime',
    },
  });
  const routeTimePopover = appendFakeElement(transportTopbar, 'div', {
    attributes: { 'data-route-time-popover': '' },
  });
  appendFakeElement(routeTimePopover, 'input', {
    type: 'time',
    value: '16:45',
    attributes: { 'data-route-time-input': '' },
  });

  const authKeyShell = appendFakeElement(body, 'div', {
    className: 'is-logged-out',
    attributes: { 'data-transport-auth-shell': 'key' },
  });
  appendFakeElement(authKeyShell, 'input', {
    type: 'text',
    value: '',
    attributes: { 'data-transport-auth-key': '' },
  });
  appendFakeElement(authKeyShell, 'button', {
    type: 'button',
    attributes: {
      'data-request-user-link': '',
      'data-i18n-aria-label': 'layout.requestUserCreation',
      'data-i18n-title': 'layout.requestUserCreation',
    },
  });

  const authPasswordShell = appendFakeElement(body, 'div', {
    className: 'is-logged-out',
    attributes: { 'data-transport-auth-shell': 'password' },
  });
  appendFakeElement(authPasswordShell, 'input', {
    type: 'password',
    value: '',
    attributes: { 'data-transport-auth-password': '' },
  });

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

  const settingsModal = appendFakeElement(body, 'div', {
    hidden: true,
    attributes: { 'data-settings-modal': '', 'aria-busy': 'false' },
  });
  appendFakeElement(settingsModal, 'h2', {
    textContent: 'SETTINGS',
    attributes: {
      id: 'transport-settings-modal-title',
      'data-i18n-text': 'settings.title',
    },
  });
  appendFakeElement(settingsModal, 'button', {
    type: 'button',
    className: 'transport-modal-close',
    attributes: {
      'data-close-settings-modal': '',
      'data-i18n-aria-label': 'settings.closeAria',
      'data-i18n-title': 'settings.closeAria',
    },
  });
  appendFakeElement(settingsModal, 'span', {
    textContent: 'Preferences',
    attributes: {
      'data-settings-preferences-title': '',
      'data-i18n-text': 'settings.preferences',
    },
  });
  appendFakeElement(settingsModal, 'span', {
    textContent: 'Languages:',
    attributes: {
      'data-settings-language-label': '',
      'data-i18n-text': 'settings.languages',
    },
  });
  appendFakeElement(settingsModal, 'select', {
    value: 'en',
    attributes: { 'data-settings-language-select': '' },
  });
  appendFakeElement(settingsModal, 'span', {
    textContent: 'Arrive at Work:',
    attributes: {
      'data-settings-arrive-at-work-label': '',
      'data-i18n-text': 'settings.arriveAtWorkTime',
    },
  });
  appendFakeElement(settingsModal, 'input', {
    type: 'time',
    value: '07:45',
    attributes: {
      'data-settings-arrive-at-work-time': '',
      'data-i18n-aria-label': 'settings.arriveAtWorkTime',
    },
  });
  appendFakeElement(settingsModal, 'span', {
    textContent: 'Work to Home Time:',
    attributes: {
      'data-settings-time-label': '',
      'data-i18n-text': 'settings.workToHomeTime',
    },
  });
  appendFakeElement(settingsModal, 'input', {
    type: 'time',
    value: '16:45',
    attributes: {
      'data-settings-work-to-home-time': '',
      'data-i18n-aria-label': 'settings.workToHomeTime',
    },
  });
  appendFakeElement(settingsModal, 'span', {
    textContent: 'Extra Car Tolerance:',
    attributes: {
      'data-settings-extra-car-tolerance-label': '',
      'data-i18n-text': 'settings.extraCarTolerance',
    },
  });
  appendFakeElement(settingsModal, 'input', {
    type: 'number',
    value: '30',
    attributes: {
      'data-settings-extra-car-tolerance': '',
      'data-i18n-aria-label': 'settings.extraCarTolerance',
    },
  });
  appendFakeElement(settingsModal, 'span', {
    textContent: 'Last Update Time:',
    attributes: {
      'data-settings-last-update-label': '',
      'data-i18n-text': 'settings.lastUpdateTime',
    },
  });
  appendFakeElement(settingsModal, 'input', {
    type: 'time',
    value: '16:00',
    attributes: {
      'data-settings-last-update-time': '',
      'data-i18n-aria-label': 'settings.lastUpdateTime',
    },
  });
  appendFakeElement(settingsModal, 'p', {
    attributes: { 'data-settings-time-note': '' },
  });
  appendFakeElement(settingsModal, 'span', {
    textContent: 'Standard Tolerance:',
    attributes: {
      'data-settings-default-tolerance-label': '',
      'data-i18n-text': 'settings.standardTolerance',
    },
  });
  appendFakeElement(settingsModal, 'input', {
    type: 'number',
    value: '5',
    attributes: {
      'data-settings-default-tolerance': '',
      'data-i18n-aria-label': 'settings.standardTolerance',
    },
  });
  appendFakeElement(settingsModal, 'button', {
    type: 'button',
    textContent: 'Close',
    attributes: {
      'data-settings-close-button': '',
      'data-close-settings-modal': '',
      'data-i18n-text': 'settings.close',
    },
  });

  const aiSettingsModal = appendFakeElement(body, 'div', {
    hidden: true,
    attributes: { 'data-ai-settings-modal': '', 'aria-busy': 'false' },
  });
  appendFakeElement(aiSettingsModal, 'h2', {
    textContent: 'AI Settings',
    attributes: {
      id: 'transport-ai-settings-modal-title',
      'data-i18n-text': 'ai.settingsTitle',
    },
  });
  appendFakeElement(aiSettingsModal, 'button', {
    type: 'button',
    className: 'transport-modal-close',
    attributes: {
      'data-close-ai-settings-modal': '',
      'data-i18n-aria-label': 'ai.settingsCloseAria',
      'data-i18n-title': 'ai.settingsCloseAria',
    },
  });
  appendFakeElement(aiSettingsModal, 'span', {
    textContent: 'Project:',
    attributes: {
      'data-ai-settings-project-label': '',
      'data-i18n-text': 'ai.settingsProject',
    },
  });
  appendFakeElement(aiSettingsModal, 'select', {
    value: '',
    attributes: { 'data-ai-settings-project': '' },
  });
  appendFakeElement(aiSettingsModal, 'span', {
    textContent: 'Provider:',
    attributes: {
      'data-ai-settings-provider-label': '',
      'data-i18n-text': 'ai.settingsProvider',
    },
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
    textContent: 'API Key:',
    attributes: {
      'data-ai-settings-api-key-label': '',
      'data-i18n-text': 'ai.settingsApiKey',
    },
  });
  appendFakeElement(aiSettingsModal, 'input', {
    type: 'password',
    value: '',
    attributes: {
      'data-ai-settings-api-key': '',
      'data-i18n-aria-label': 'ai.settingsApiKey',
      'data-i18n-placeholder': 'ai.settingsApiKeyPlaceholder',
    },
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
    textContent: 'Cancel',
    attributes: {
      'data-ai-settings-cancel': '',
      'data-close-ai-settings-modal': '',
      'data-i18n-text': 'ai.settingsCancel',
    },
  });
  appendFakeElement(aiSettingsModal, 'button', {
    type: 'button',
    textContent: 'Save',
    attributes: {
      'data-ai-settings-save': '',
      'data-i18n-text': 'ai.settingsSave',
    },
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
  appendFakeElement(aiAgentModal, 'input', {
    type: 'checkbox',
    checked: true,
    attributes: { 'data-ai-agent-request-kind': 'extra' },
    value: 'extra',
  });
  appendFakeElement(aiAgentModal, 'input', {
    type: 'checkbox',
    checked: true,
    attributes: { 'data-ai-agent-request-kind': 'weekend' },
    value: 'weekend',
  });
  appendFakeElement(aiAgentModal, 'input', {
    type: 'checkbox',
    checked: true,
    attributes: { 'data-ai-agent-request-kind': 'regular' },
    value: 'regular',
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
    attributes: {
      'data-close-ai-changes-modal': '',
      'data-i18n-aria-label': 'ai.changesCloseAria',
      'data-i18n-title': 'ai.changesCloseAria',
    },
  });
  appendFakeElement(aiChangesModal, 'h2', {
    textContent: 'Changes',
    attributes: {
      'data-ai-changes-title': '',
      'data-i18n-text': 'ai.changesTitle',
    },
  });
  appendFakeElement(aiChangesModal, 'div', {
    hidden: true,
    attributes: { 'data-ai-changes-status': '' },
  });
  appendFakeElement(aiChangesModal, 'div', { attributes: { 'data-ai-changes-summary-grid': '' } });
  appendFakeElement(aiChangesModal, 'div', { attributes: { 'data-ai-changes-summary-panel': '' } });
  appendFakeElement(aiChangesModal, 'div', { attributes: { 'data-ai-changes-vehicles': '' } });
  appendFakeElement(aiChangesModal, 'div', { attributes: { 'data-ai-changes-passengers': '' } });
  appendFakeElement(aiChangesModal, 'div', { attributes: { 'data-ai-changes-routes': '' } });
  appendFakeElement(aiChangesModal, 'div', { attributes: { 'data-ai-changes-audit': '' } });
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

function extractDeclarativeI18nKeyPathsFromHtml(html) {
  const keyPaths = new Set();
  const normalizedHtml = String(html || '');
  const pattern = /data-i18n-(?:text|aria-label|placeholder|title|option)="([^"]+)"/g;
  let match = pattern.exec(normalizedHtml);

  while (match) {
    keyPaths.add(match[1]);
    match = pattern.exec(normalizedHtml);
  }

  return Array.from(keyPaths);
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

function createTransportProjectRow(id, name, overrides) {
  return Object.assign(
    {
      id,
      name,
      country_code: 'SG',
      country_name: 'Singapore',
      timezone_name: 'Asia/Singapore',
      timezone_label: 'SGT',
      address: `${name} Avenue`,
      zip_code: '018989',
    },
    overrides || {}
  );
}

function createFetchMock(options) {
  const nextOptions = options || {};
  const calls = [];
  const authSessionResponse = nextOptions.authSessionResponse || {
    authenticated: true,
    user: { chave: 'OPS-100', nome: 'Transport Ops' },
  };
  const authVerifyResponse = Object.prototype.hasOwnProperty.call(nextOptions, 'authVerifyResponse')
    ? nextOptions.authVerifyResponse
    : {
      authenticated: true,
      user: { chave: 'OPS-100', nome: 'Transport Ops' },
      message: 'Transport access granted.',
    };
  const authVerifyHandler = typeof nextOptions.authVerifyHandler === 'function'
    ? nextOptions.authVerifyHandler
    : null;
  const settingsResponse = nextOptions.settingsResponse || {
    arrive_at_work_time: '07:45',
    work_to_home_time: '16:15',
    last_update_time: '16:00',
    extra_car_tolerance_minutes: 30,
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
  const settingsPutHandler = typeof nextOptions.settingsPutHandler === 'function'
    ? nextOptions.settingsPutHandler
    : null;
  const settingsPutError = nextOptions.settingsPutError || null;
  const settingsPutResponse = Object.prototype.hasOwnProperty.call(nextOptions, 'settingsPutResponse')
    ? nextOptions.settingsPutResponse
    : settingsResponse;
  const dashboardResponse = nextOptions.dashboardResponse || {
    selected_route: 'home_to_work',
    selected_date: '2026-06-13',
    projects: [
      createTransportProjectRow(101, 'Project Atlas'),
      createTransportProjectRow(202, 'Project Borealis', { zip_code: '018990' }),
    ],
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
    workplaces: [],
  };
  const projectListResponse = Object.prototype.hasOwnProperty.call(nextOptions, 'projectListResponse')
    ? nextOptions.projectListResponse
    : (Array.isArray(dashboardResponse.projects) ? dashboardResponse.projects : []);
  const projectListError = nextOptions.projectListError || null;
  const projectListHandler = typeof nextOptions.projectListHandler === 'function'
    ? nextOptions.projectListHandler
    : null;
  const latestSuggestionResponse = nextOptions.latestSuggestionResponse;
  const commandResponses = nextOptions.commandResponses || {};
  const aiSettingsResponse = Object.prototype.hasOwnProperty.call(nextOptions, 'aiSettingsResponse')
    ? nextOptions.aiSettingsResponse
    : {
      project_id: 101,
      project_name: 'Project Atlas',
      provider: 'openai',
      resolved_model: 'gpt-5.4-2026-03-05',
      reasoning_effort: 'high',
      has_api_key: true,
      api_key_hint: '***1234',
    };
  const aiSettingsGetHandler = typeof nextOptions.aiSettingsGetHandler === 'function'
    ? nextOptions.aiSettingsGetHandler
    : null;
  const aiSettingsGetError = nextOptions.aiSettingsGetError || null;
  const aiSettingsPutError = nextOptions.aiSettingsPutError || null;
  const aiSettingsPutResponse = Object.prototype.hasOwnProperty.call(nextOptions, 'aiSettingsPutResponse')
    ? nextOptions.aiSettingsPutResponse
    : aiSettingsResponse;
  const aiSettingsPutHandler = typeof nextOptions.aiSettingsPutHandler === 'function'
    ? nextOptions.aiSettingsPutHandler
    : null;
  const routeCalculationStartHandler = typeof nextOptions.routeCalculationStartHandler === 'function'
    ? nextOptions.routeCalculationStartHandler
    : null;
  const routeCalculationStartError = nextOptions.routeCalculationStartError || null;
  const routeCalculationStartResponse = Object.prototype.hasOwnProperty.call(nextOptions, 'routeCalculationStartResponse')
    ? nextOptions.routeCalculationStartResponse
    : null;
  const routeCalculationStatusHandler = typeof nextOptions.routeCalculationStatusHandler === 'function'
    ? nextOptions.routeCalculationStatusHandler
    : null;
  const routeCalculationStatusError = nextOptions.routeCalculationStatusError || null;
  const routeCalculationStatusResponse = Object.prototype.hasOwnProperty.call(nextOptions, 'routeCalculationStatusResponse')
    ? nextOptions.routeCalculationStatusResponse
    : null;
  const assignmentPostHandler = typeof nextOptions.assignmentPostHandler === 'function'
    ? nextOptions.assignmentPostHandler
    : null;
  const assignmentPostError = nextOptions.assignmentPostError || null;
  const assignmentPostResponse = Object.prototype.hasOwnProperty.call(nextOptions, 'assignmentPostResponse')
    ? nextOptions.assignmentPostResponse
    : { ok: true, message: 'Transport assignment saved successfully.' };
  const assignmentBoardingTimePutHandler = typeof nextOptions.assignmentBoardingTimePutHandler === 'function'
    ? nextOptions.assignmentBoardingTimePutHandler
    : null;
  const assignmentBoardingTimePutError = nextOptions.assignmentBoardingTimePutError || null;
  const assignmentBoardingTimePutResponse = Object.prototype.hasOwnProperty.call(nextOptions, 'assignmentBoardingTimePutResponse')
    ? nextOptions.assignmentBoardingTimePutResponse
    : { ok: true, message: 'Transport boarding time saved successfully.' };

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
    if (request.method === 'POST' && request.url.includes('/auth/verify')) {
      if (authVerifyHandler) {
        return authVerifyHandler(request);
      }
      return createFetchResponse(authVerifyResponse, 200);
    }
    if (request.method === 'POST' && request.url.includes('/auth/logout')) {
      return createFetchResponse({ ok: true }, 200);
    }
    if (request.method === 'GET' && request.url.includes('/projects')) {
      if (projectListHandler) {
        return projectListHandler(request);
      }
      if (projectListError) {
        return createFetchResponse(projectListError.payload, projectListError.status);
      }
      return createFetchResponse(projectListResponse, 200);
    }
    if (request.method === 'GET' && request.url.includes('/ai/settings')) {
      if (aiSettingsGetHandler) {
        return aiSettingsGetHandler(request);
      }
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
    if (request.method === 'POST' && request.url.includes('/ai/route-calculations')) {
      if (routeCalculationStartHandler) {
        return routeCalculationStartHandler(request);
      }
      if (routeCalculationStartError) {
        return createFetchResponse(routeCalculationStartError.payload, routeCalculationStartError.status);
      }
      if (routeCalculationStartResponse) {
        return createFetchResponse(routeCalculationStartResponse, 200);
      }
    }
    if (request.method === 'GET' && request.url.includes('/ai/route-calculations/')) {
      if (routeCalculationStatusHandler) {
        return routeCalculationStatusHandler(request);
      }
      if (routeCalculationStatusError) {
        return createFetchResponse(routeCalculationStatusError.payload, routeCalculationStatusError.status);
      }
      if (routeCalculationStatusResponse) {
        return createFetchResponse(routeCalculationStatusResponse, 200);
      }
    }
    if (request.method === 'PUT' && request.url.includes('/settings')) {
      if (settingsPutHandler) {
        return settingsPutHandler(request);
      }
      if (settingsPutError) {
        return createFetchResponse(settingsPutError.payload, settingsPutError.status);
      }
      return createFetchResponse(settingsPutResponse, 200);
    }
    if (request.method === 'GET' && request.url.includes('/settings')) {
      return createFetchResponse(settingsResponse, 200);
    }
    if (request.method === 'PUT' && request.url.includes('/assignments/boarding-time')) {
      if (assignmentBoardingTimePutHandler) {
        return assignmentBoardingTimePutHandler(request);
      }
      if (assignmentBoardingTimePutError) {
        return createFetchResponse(assignmentBoardingTimePutError.payload, assignmentBoardingTimePutError.status);
      }
      return createFetchResponse(assignmentBoardingTimePutResponse, 200);
    }
    if (request.method === 'POST' && request.url.includes('/assignments')) {
      if (assignmentPostHandler) {
        return assignmentPostHandler(request);
      }
      if (assignmentPostError) {
        return createFetchResponse(assignmentPostError.payload, assignmentPostError.status);
      }
      return createFetchResponse(assignmentPostResponse, 200);
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

function createScheduledTimerHarness() {
  let nextTimerId = 1;
  let currentTimeMs = 0;
  const activeTimers = new Map();

  function getDueTimers(targetTimeMs) {
    return Array.from(activeTimers.entries())
      .filter(([, timer]) => timer.runAt <= targetTimeMs)
      .sort((left, right) => {
        if (left[1].runAt !== right[1].runAt) {
          return left[1].runAt - right[1].runAt;
        }
        return left[0] - right[0];
      });
  }

  return {
    setTimeout(callback, delayMs) {
      const timerId = nextTimerId;
      const normalizedDelayMs = Number.isFinite(Number(delayMs)) ? Math.max(0, Number(delayMs)) : 0;
      nextTimerId += 1;
      activeTimers.set(timerId, {
        callback,
        runAt: currentTimeMs + normalizedDelayMs,
      });
      return timerId;
    },
    clearTimeout(timerId) {
      activeTimers.delete(timerId);
    },
    getPendingTimerCount() {
      return activeTimers.size;
    },
    getCurrentTime() {
      return currentTimeMs;
    },
    async advanceTime(delayMs) {
      const normalizedDelayMs = Number.isFinite(Number(delayMs)) ? Math.max(0, Number(delayMs)) : 0;
      const targetTimeMs = currentTimeMs + normalizedDelayMs;

      while (true) {
        const dueTimers = getDueTimers(targetTimeMs);
        if (!dueTimers.length) {
          break;
        }

        currentTimeMs = dueTimers[0][1].runAt;

        dueTimers.forEach(([timerId, timer]) => {
          if (!activeTimers.has(timerId)) {
            return;
          }
          activeTimers.delete(timerId);
          timer.callback();
        });
        await flushAsyncWork(4);
      }

      currentTimeMs = targetTimeMs;
    },
  };
}

function createFakeEventSourceHarness(timers, options) {
  const nextOptions = options || {};
  const events = [];
  const errorDelayMs = Number.isFinite(Number(nextOptions.errorDelayMs)) ? Math.max(0, Number(nextOptions.errorDelayMs)) : 0;

  class FakeEventSource {
    constructor(url) {
      this.url = String(url);
      this.readyState = 0;
      this.onopen = null;
      this.onmessage = null;
      this.onerror = null;
      this._closed = false;
      this._record = {
        url: this.url,
        openedAt: typeof timers.getCurrentTime === 'function' ? timers.getCurrentTime() : 0,
        erroredAt: null,
        closedAt: null,
      };
      events.push(this._record);

      this._errorTimerId = timers.setTimeout(() => {
        if (this._closed) {
          return;
        }
        this._record.erroredAt = typeof timers.getCurrentTime === 'function' ? timers.getCurrentTime() : 0;
        if (typeof this.onerror === 'function') {
          this.onerror(createFakeEvent('error', { target: this }));
        }
      }, errorDelayMs);
    }

    close() {
      if (this._closed) {
        return;
      }
      this._closed = true;
      this.readyState = 2;
      timers.clearTimeout(this._errorTimerId);
      this._record.closedAt = typeof timers.getCurrentTime === 'function' ? timers.getCurrentTime() : 0;
    }
  }

  return {
    EventSource: FakeEventSource,
    events,
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
      audit: {
        planning_input_hash: 'a'.repeat(64),
        extra_car_tolerance_minutes: 30,
        extra_clusters: [
          {
            partition_key: 'extra:P80:SG',
            cluster_key: 'cluster:extra:morning:1',
            anchor_requested_time: '07:20',
            earliest_requested_time: '07:00',
            latest_requested_time: '07:20',
            request_ids: [301],
            request_count: 1,
          },
        ],
      },
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
        vehicle_review_tables: [
          {
            vehicle_ref: 'existing:11',
            vehicle_label: 'SGX1234',
            service_scope: 'extra',
            vehicle_type: 'van',
            route_kind: 'home_to_work',
            vehicle_id: 11,
            client_vehicle_key: 'existing:11',
            plate: 'SGX1234',
            estimated_cost: 24,
            action_type: 'update',
            action_key: 'vehicle:update:11',
            action_rationale: 'Upgrade the vehicle and keep the existing route grouped.',
            header_badges: [
              { text: 'Extra', tone: 'info' },
              { text: 'Home To Work', tone: 'neutral' },
              { text: 'Update', tone: 'warning' },
            ],
            rows: [
              {
                request_id: 301,
                user_id: 501,
                request_kind: 'extra',
                pickup_order: 0,
                user_name: 'Alice Tan',
                user_address: '7 Garden Street',
                home_to_work_boarding: '07:05',
                home_to_work_boarding_is_placeholder: false,
                work_to_home_dropoff: null,
                work_to_home_dropoff_is_placeholder: true,
              },
            ],
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
              route_kind: 'home_to_work',
              departure_time: '07:45',
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
      getPendingTimerCount() {
        return typeof timers.getPendingTimerCount === 'function' ? timers.getPendingTimerCount() : 0;
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

async function withTransportPageControlledHarness(options, callback) {
  const nextOptions = options || {};
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
  const timers = nextOptions.timerHarness || createImmediateTimerHarness();
  const fetchMock = createFetchMock(nextOptions.fetchOptions || nextOptions);

  document.visibilityState = nextOptions.initialVisibilityState === 'hidden' ? 'hidden' : 'visible';
  document.hidden = document.visibilityState === 'hidden';

  global.document = document;
  global.fetch = fetchMock.fetch;
  global.addEventListener = windowEvents.addEventListener.bind(windowEvents);
  global.removeEventListener = windowEvents.removeEventListener.bind(windowEvents);
  global.dispatchEvent = windowEvents.dispatchEvent.bind(windowEvents);
  global.setTimeout = timers.setTimeout.bind(timers);
  global.clearTimeout = timers.clearTimeout.bind(timers);
  global.EventSource = nextOptions.eventSourceHarness ? nextOptions.eventSourceHarness.EventSource : undefined;

  try {
    const localizedTransportPage = loadTransportPageWithI18n();
    document.dispatchEvent(createFakeEvent('DOMContentLoaded', { target: document }));
    await flushAsyncWork();
    return await callback({
      document,
      fetchCalls: fetchMock.calls,
      transportPageApi: localizedTransportPage,
      flushAsyncWork,
      timers,
      async advanceTime(delayMs) {
        if (typeof timers.advanceTime !== 'function') {
          throw new Error('The active timer harness does not support time control.');
        }
        await timers.advanceTime(delayMs);
        await flushAsyncWork();
      },
      async setVisibility(nextVisibilityState) {
        document.visibilityState = nextVisibilityState === 'hidden' ? 'hidden' : 'visible';
        document.hidden = document.visibilityState === 'hidden';
        document.dispatchEvent(createFakeEvent('visibilitychange', { target: document }));
        await flushAsyncWork();
      },
      getElement(selector) {
        const element = document.querySelector(selector);
        assert.ok(element, `Expected to find element matching ${selector}`);
        return element;
      },
      getPendingTimerCount() {
        return typeof timers.getPendingTimerCount === 'function' ? timers.getPendingTimerCount() : 0;
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

async function renderVehicleDetailsPanelForTest(vehicle, options) {
  return withTransportPageHarness({}, async ({ transportPageApi }) => {
    return transportPageApi.__testCreateVehicleDetailsPanel(vehicle, [], options || {});
  });
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

test('getDefaultVehiclePanelHeight returns conservative defaults for each vehicle scope', () => {
  assert.equal(transportPage.getDefaultVehiclePanelHeight('extra'), 288);
  assert.equal(transportPage.getDefaultVehiclePanelHeight('weekend'), 272);
  assert.equal(transportPage.getDefaultVehiclePanelHeight('regular'), 256);
  assert.equal(transportPage.getDefaultVehiclePanelHeight('unknown'), 260);
});

test('resolveVehiclePanelExplicitHeight clamps requested heights and falls back to per-scope defaults', () => {
  assert.equal(
    transportPage.resolveVehiclePanelExplicitHeight({
      scope: 'extra',
      requestedHeight: 0,
      minHeight: 220,
    }),
    288
  );

  assert.equal(
    transportPage.resolveVehiclePanelExplicitHeight({
      scope: 'regular',
      requestedHeight: 120,
      minHeight: 220,
    }),
    220
  );

  assert.equal(
    transportPage.resolveVehiclePanelExplicitHeight({
      scope: 'weekend',
      requestedHeight: 330.4,
      minHeight: 220,
    }),
    330
  );
});

test('resolveVehiclePanelResizedHeight applies pointer deltas to only the target panel height', () => {
  assert.equal(
    transportPage.resolveVehiclePanelResizedHeight({
      scope: 'extra',
      startHeight: 288,
      pointerDelta: 42,
      minHeight: 220,
    }),
    330
  );

  assert.equal(
    transportPage.resolveVehiclePanelResizedHeight({
      scope: 'weekend',
      startHeight: 272,
      pointerDelta: -100,
      minHeight: 220,
    }),
    220
  );
});

test('isVehiclePanelResizeEnabledForViewport disables manual pane resizing at and below 1180px', () => {
  assert.equal(transportPage.isVehiclePanelResizeEnabledForViewport(1440), true);
  assert.equal(transportPage.isVehiclePanelResizeEnabledForViewport(1181), true);
  assert.equal(transportPage.isVehiclePanelResizeEnabledForViewport(1180), false);
  assert.equal(transportPage.isVehiclePanelResizeEnabledForViewport(960), false);
});

test('updateVehicleGridLayout recalculates row density from the live pane height', () => {
  withFakeComputedStyle({ rowGap: '8px', gap: '8px' }, () => {
    const document = new FakeDocument();
    const gridElement = appendVehicleGrid(document.body, {
      scope: 'extra',
      itemCount: 6,
      clientHeight: 60,
      itemWidth: 120,
      itemHeight: 60,
    });

    transportPage.updateVehicleGridLayout(gridElement);
    assert.equal(gridElement.style.gridAutoColumns, '120px');
    assert.equal(gridElement.style.gridTemplateRows, 'repeat(1, 60px)');

    gridElement.clientHeight = 272;
    transportPage.updateVehicleGridLayout(gridElement);
    assert.equal(gridElement.style.gridTemplateRows, 'repeat(4, 60px)');
  });
});

test('updateVehicleGridLayout clears inline sizing for table-like vehicle views', () => {
  withFakeComputedStyle({ rowGap: '8px', gap: '8px' }, () => {
    const document = new FakeDocument();
    const tableGridElement = appendVehicleGrid(document.body, {
      scope: 'weekend',
      itemCount: 4,
      clientHeight: 180,
      vehicleView: 'table',
    });
    tableGridElement.style.gridTemplateRows = 'repeat(3, 60px)';
    tableGridElement.style.gridAutoColumns = '120px';

    transportPage.updateVehicleGridLayout(tableGridElement);
    assert.equal(tableGridElement.style.gridTemplateRows, undefined);
    assert.equal(tableGridElement.style.gridAutoColumns, undefined);

    const managementGridElement = appendVehicleGrid(document.body, {
      scope: 'regular',
      itemCount: 4,
      clientHeight: 180,
      className: 'is-management-table',
    });
    managementGridElement.style.gridTemplateRows = 'repeat(3, 60px)';
    managementGridElement.style.gridAutoColumns = '120px';

    transportPage.updateVehicleGridLayout(managementGridElement);
    assert.equal(managementGridElement.style.gridTemplateRows, undefined);
    assert.equal(managementGridElement.style.gridAutoColumns, undefined);
  });
});

test('updateVehicleGridLayouts can refresh only the affected vehicle panel subtree', () => {
  withFakeComputedStyle({ rowGap: '8px', gap: '8px' }, () => {
    const document = new FakeDocument();
    const vehiclePanelsRoot = appendFakeElement(document.body, 'div');
    const extraPanel = appendFakeElement(vehiclePanelsRoot, 'section', { className: 'transport-pane' });
    const weekendPanel = appendFakeElement(vehiclePanelsRoot, 'section', { className: 'transport-pane' });
    const extraGridElement = appendVehicleGrid(extraPanel, {
      scope: 'extra',
      itemCount: 6,
      clientHeight: 272,
    });
    const weekendGridElement = appendVehicleGrid(weekendPanel, {
      scope: 'weekend',
      itemCount: 6,
      clientHeight: 60,
    });

    transportPage.updateVehicleGridLayouts(extraPanel);

    assert.equal(extraGridElement.style.gridTemplateRows, 'repeat(4, 60px)');
    assert.equal(weekendGridElement.style.gridTemplateRows, undefined);
  });
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

test('mapVehicleIconPath resolves dedicated orange assets only for temporary or administratively incomplete vehicles', () => {
  assert.equal(transportPage.mapVehicleIconPath('carro'), '../assets/icons/car.svg');
  assert.equal(transportPage.mapVehicleIconPath('minivan'), '../assets/icons/minivan.svg');
  assert.equal(transportPage.mapVehicleIconPath('van'), '../assets/icons/van.svg');
  assert.equal(transportPage.mapVehicleIconPath('onibus'), '../assets/icons/bus.svg');

  assert.equal(
    transportPage.mapVehicleIconPath({
      tipo: 'carro',
      placa: 'SGX1234A',
      color: 'White',
      pending_fields: [],
    }),
    '../assets/icons/car.svg'
  );
  assert.equal(
    transportPage.mapVehicleIconPath({
      tipo: 'carro',
      placa: 'Plate 001',
      color: 'White',
      pending_fields: [],
    }),
    '../assets/icons/car-orange.svg'
  );
  assert.equal(
    transportPage.mapVehicleIconPath({
      tipo: 'van',
      placa: 'SGX2345B',
      color: null,
      pending_fields: ['color'],
    }),
    '../assets/icons/van-orange.svg'
  );
  assert.equal(
    transportPage.mapVehicleIconPath({
      tipo: 'onibus',
      placa: '',
      color: 'White',
      pending_fields: ['placa'],
    }),
    '../assets/icons/bus-orange.svg'
  );

  [
    '../assets/icons/car.svg',
    '../assets/icons/minivan.svg',
    '../assets/icons/van.svg',
    '../assets/icons/bus.svg',
    '../assets/icons/car-orange.svg',
    '../assets/icons/minivan-orange.svg',
    '../assets/icons/van-orange.svg',
    '../assets/icons/bus-orange.svg',
  ].forEach((assetPath) => {
    assert.equal(fs.existsSync(path.join(__dirname, assetPath)), true);
  });
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

test('extra vehicle reference helpers derive ETA and ETD from route kind while preserving a raw fallback for legacy rows', () => {
  assert.equal(
    transportPage.formatExtraVehicleReferenceLabel('home_to_work', '07:45'),
    'ETA 07:45h'
  );
  assert.equal(
    transportPage.formatExtraVehicleReferenceLabel('work_to_home', '19:20'),
    'ETD 19:20h'
  );
  assert.equal(
    transportPage.formatExtraVehicleReferenceLabel('', '19:20'),
    '19:20'
  );
  assert.equal(
    transportPage.getVehicleReferenceLabel(
      'extra',
      { departure_time: '07:45' },
      null,
      '07:45',
      7 * 60,
      '16:45',
      'home_to_work'
    ),
    'ETA 07:45h'
  );
  assert.equal(
    transportPage.getVehicleReferenceLabel(
      'extra',
      { departure_time: '19:20' },
      null,
      '07:45',
      19 * 60,
      '16:45',
      'work_to_home'
    ),
    'ETD 19:20h'
  );
  assert.equal(
    transportPage.getVehicleReferenceLabel(
      'regular',
      { departure_time: '' },
      { work_to_home_departure_time: '18:10' },
      '07:45',
      9 * 60,
      '16:45',
      ''
    ),
    'ETD 18:10h'
  );
});

test('vehicle reference mode helper reuses the shared ETA and ETD decision across routine and extra scopes', () => {
  assert.equal(
    transportPage.resolveVehicleReferenceMode(
      'regular',
      { work_to_home_departure_time: '18:10' },
      '07:45',
      9 * 60,
      '16:45',
      ''
    ),
    'etd'
  );
  assert.equal(
    transportPage.resolveVehicleReferenceMode(
      'extra',
      null,
      '07:45',
      7 * 60,
      '16:45',
      'home_to_work'
    ),
    'eta'
  );
  assert.equal(
    transportPage.resolveVehicleReferenceMode(
      'extra',
      null,
      '07:45',
      19 * 60,
      '16:45',
      'work_to_home'
    ),
    'etd'
  );
});

test('vehicle passenger operational time keeps ETD vehicle-derived and ETA bound to boarding_time instead of requested_time', () => {
  assert.deepEqual(
    transportPage.resolveVehiclePassengerOperationalTime(
      'regular',
      { service_scope: 'regular', departure_time: '' },
      { boarding_time: '06:50', requested_time: '07:15' },
      { work_to_home_departure_time: '18:10' },
      '07:45',
      9 * 60,
      '16:45',
      ''
    ),
    { mode: 'etd', time: '18:10', timeField: null }
  );
  assert.deepEqual(
    transportPage.resolveVehiclePassengerOperationalTime(
      'extra',
      { service_scope: 'extra', departure_time: '07:45' },
      { boarding_time: '06:50', requested_time: '07:20' },
      null,
      '07:45',
      7 * 60,
      '16:45',
      'home_to_work'
    ),
    { mode: 'eta', time: '06:50', timeField: 'boarding_time' }
  );
  assert.deepEqual(
    transportPage.resolveVehiclePassengerOperationalTime(
      'extra',
      { service_scope: 'extra', departure_time: '07:45' },
      { requested_time: '07:20' },
      null,
      '07:45',
      7 * 60,
      '16:45',
      'home_to_work'
    ),
    { mode: 'eta', time: '', timeField: 'boarding_time' }
  );
});

test('extra vehicle modal time-field copy keys follow the selected route semantics', () => {
  assert.equal(transportPage.getExtraVehicleDepartureFieldKey('home_to_work'), 'modal.fields.etaTime');
  assert.equal(transportPage.getExtraVehicleDepartureFieldKey('work_to_home'), 'modal.fields.etdTime');
  assert.equal(transportPage.getExtraVehicleDepartureFieldKey(''), 'modal.fields.departureTime');
});

test('transport reference clock follows the server timestamp and resolves the next ETA/ETD switch without browser timezone drift', () => {
  const clock = transportPage.createTransportReferenceClock('2026-06-13T07:50:00+08:00', { clientNowMs: 1000 });

  assert.ok(clock);
  assert.equal(clock.offsetMinutes, 8 * 60);
  assert.equal(
    transportPage.resolveTransportReferenceNow(clock, { clientNowMs: 61_000 }),
    Date.parse('2026-06-12T23:51:00.000Z')
  );
  assert.equal(
    transportPage.resolveRoutineVehicleReferenceMode((7 * 60) + 50, '07:45', '16:15'),
    'eta'
  );
  assert.equal(
    transportPage.resolveRoutineVehicleReferenceMode((8 * 60) + 16, '07:45', '16:15'),
    'etd'
  );
  assert.equal(
    transportPage.resolveNextRoutineVehicleReferenceDelayMs(clock, '07:45', '16:15', { clientNowMs: 1000 }),
    25 * 60 * 1000
  );
});

test('resolveRoutineVehicleReferenceMode flips on the exact ETA and ETD switch boundaries', () => {
  assert.equal(
    transportPage.resolveRoutineVehicleReferenceMode((8 * 60) + 14, '07:45', '16:45'),
    'eta'
  );
  assert.equal(
    transportPage.resolveRoutineVehicleReferenceMode((8 * 60) + 15, '07:45', '16:45'),
    'etd'
  );
  assert.equal(
    transportPage.resolveRoutineVehicleReferenceMode((17 * 60) + 14, '07:45', '16:45'),
    'etd'
  );
  assert.equal(
    transportPage.resolveRoutineVehicleReferenceMode((17 * 60) + 15, '07:45', '16:45'),
    'eta'
  );
});

test('resolveRoutineVehicleReferenceMode keeps the ETD window correct when the switch interval wraps across midnight', () => {
  assert.equal(
    transportPage.resolveRoutineVehicleReferenceMode((22 * 60) + 59, '22:30', '05:00'),
    'eta'
  );
  assert.equal(
    transportPage.resolveRoutineVehicleReferenceMode(23 * 60, '22:30', '05:00'),
    'etd'
  );
  assert.equal(
    transportPage.resolveRoutineVehicleReferenceMode((5 * 60) + 29, '22:30', '05:00'),
    'etd'
  );
  assert.equal(
    transportPage.resolveRoutineVehicleReferenceMode((5 * 60) + 30, '22:30', '05:00'),
    'eta'
  );
});

test('routine vehicle reference helpers format ETA and ETD labels from global and date-specific values', () => {
  assert.equal(
    transportPage.formatRoutineVehicleReferenceLabel('eta', '07:45', '16:45'),
    'ETA 07:45h'
  );
  assert.equal(
    transportPage.formatRoutineVehicleReferenceLabel('etd', '07:45', '18:10'),
    'ETD 18:10h'
  );
  assert.equal(
    transportPage.getRoutineVehicleReferenceLabel({ work_to_home_departure_time: '18:10' }, '07:45', 9 * 60, '16:45'),
    'ETD 18:10h'
  );
  assert.equal(
    transportPage.getRoutineVehicleReferenceLabel({ work_to_home_departure_time: '18:10' }, '07:45', 7 * 60, '16:45'),
    'ETA 07:45h'
  );
  assert.equal(
    transportPage.getRoutineVehicleReferenceLabel({ work_to_home_departure_time: '' }, '07:45', 9 * 60, '16:45'),
    'ETD 16:45h'
  );
});

test('getRoutineVehicleReferenceLabel accepts the synchronized server clock object directly', () => {
  const clock = transportPage.createTransportReferenceClock('2026-06-13T18:39:00+08:00', { clientNowMs: 0 });

  assert.equal(
    transportPage.getRoutineVehicleReferenceLabel(
      { work_to_home_departure_time: '18:10' },
      '07:45',
      clock,
      '16:45',
      { clientNowMs: 0 }
    ),
    'ETD 18:10h'
  );
  assert.equal(
    transportPage.getRoutineVehicleReferenceLabel(
      { work_to_home_departure_time: '18:10' },
      '07:45',
      clock,
      '16:45',
      { clientNowMs: 61 * 1000 }
    ),
    'ETA 07:45h'
  );
});

test('transport vehicle reference scheduler recalculates the next switch after a pause using the same server clock', () => {
  const clock = transportPage.createTransportReferenceClock('2026-06-13T07:50:00+08:00', { clientNowMs: 1000 });

  assert.equal(
    transportPage.resolveNextRoutineVehicleReferenceDelayMs(clock, '07:45', '16:15', { clientNowMs: 1000 }),
    25 * 60 * 1000
  );
  assert.equal(
    transportPage.resolveNextRoutineVehicleReferenceDelayMs(clock, '07:45', '16:15', { clientNowMs: 5 * 60 * 1000 + 1000 }),
    20 * 60 * 1000
  );
});

test('transport vehicle reference scheduler finds the next switch correctly even when the ETD window crosses midnight', () => {
  const clock = transportPage.createTransportReferenceClock('2026-06-13T22:59:00+08:00', { clientNowMs: 1000 });

  assert.equal(
    transportPage.resolveNextRoutineVehicleReferenceDelayMs(clock, '22:30', '05:00', { clientNowMs: 1000 }),
    60 * 1000
  );
  assert.equal(
    transportPage.resolveNextRoutineVehicleReferenceDelayMs(clock, '22:30', '05:00', { clientNowMs: (6 * 60 * 60 * 1000) + (30 * 60 * 1000) + 1000 }),
    60 * 1000
  );
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

  assert.match(transportHtml, /<option value="" data-i18n-option="modal\.options\.blankType"><\/option>/);
  assert.match(transportHtml, /<option value="carro" selected data-i18n-option="modal\.options\.car">Car<\/option>/);
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

test('transport page controller keeps the topbar handle and now applies shell translations through the declarative sweep', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportScript, /const transportTopbar = document\.querySelector\("\[data-transport-topbar\]"\);/);
  assert.match(transportScript, /function applyInitialDeclarativeTranslations\(\) \{[\s\S]*applyDocumentLanguageMetadata\(\);[\s\S]*applyDeclarativeTranslations\(document\);/);
  assert.doesNotMatch(transportScript, /transportTopbar\.setAttribute\("aria-label", t\("layout\.quickActions"\)\)/);
});

test('transport settings modal includes editable default seat counts, pricing controls, and currency actions', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );

  assert.match(transportHtml, /class="transport-settings-section-body transport-settings-preferences-grid"/);
  assert.match(transportHtml, /data-settings-arrive-at-work-label/);
  assert.match(transportHtml, /data-settings-arrive-at-work-time/);
  assert.match(transportHtml, /data-settings-extra-car-tolerance-label/);
  assert.match(transportHtml, /data-settings-extra-car-tolerance/);
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
  assert.match(transportHtml, /id="transportSettingsArriveAtWorkTime"[\s\S]*value="07:45"/);
  assert.match(transportHtml, /id="transportSettingsExtraCarTolerance"[\s\S]*value="30"/);
  assert.match(transportHtml, /data-settings-default-tolerance-label/);
  assert.match(transportHtml, /data-settings-default-tolerance/);
  assert.match(transportHtml, /id="transportSettingsCarSeats"[\s\S]*value="3"/);
  assert.match(transportHtml, /id="transportSettingsBusSeats"[\s\S]*value="40"/);
  assert.match(transportHtml, /id="transportSettingsDefaultTolerance"[\s\S]*value="5"/);
  assert.match(transportHtml, /id="transportSettingsCarPrice"/);
  assert.match(transportHtml, /id="transportSettingsBusPrice"/);
  assert.match(transportHtml, /data-i18n-text="settings\.arriveAtWorkTime"/);
  assert.match(transportHtml, /data-i18n-aria-label="settings\.arriveAtWorkTime"/);
  assert.match(transportHtml, /data-i18n-text="settings\.extraCarTolerance"/);
  assert.match(transportHtml, /data-i18n-aria-label="settings\.extraCarTolerance"/);
  assert.match(transportHtml, /data-i18n-text="settings\.addCurrency"/);
  assert.match(transportHtml, /data-i18n-text="settings\.saveCurrency"/);
  assert.match(transportHtml, /data-i18n-text="settings\.close"/);
  assert.match(
    transportScript,
    /const settingsArriveAtWorkInput = document\.querySelector\("\[data-settings-arrive-at-work-time\]"\);/
  );
  assert.match(
    transportScript,
    /const settingsExtraCarToleranceInput = document\.querySelector\("\[data-settings-extra-car-tolerance\]"\);/
  );
  assert.match(
    transportScript,
    /applyDeclarativeTranslations\(document\);/
  );
  assert.match(
    transportScript,
    /if \(settingsArriveAtWorkInput\) \{[\s\S]*settingsArriveAtWorkInput\.placeholder = DEFAULT_ARRIVE_AT_WORK_TIME;/
  );
  assert.match(
    transportScript,
    /if \(settingsExtraCarToleranceInput\) \{[\s\S]*settingsExtraCarToleranceInput\.placeholder = String\(DEFAULT_EXTRA_CAR_TOLERANCE_MINUTES\);/
  );
  assert.match(transportI18n, /priceVariables:\s*"Price Variables"/);
  assert.match(transportI18n, /arriveAtWorkTime:\s*"Arrive at Work:"/);
  assert.match(transportI18n, /extraCarTolerance:\s*"Extra Car Tolerance:"/);
  assert.equal((transportI18n.match(/extraCarTolerance:/g) || []).length, 5);
  assert.match(transportI18n, /defaultPriceLabel:\s*"\{type\} default price:"/);
  assert.match(transportI18n, /couldNotAddCurrency:\s*"Could not add currency\./);
  assert.match(transportI18n, /currencyAlreadyExists:\s*"This currency code already exists\./);
});

test('transport vehicle renderers consume the unified reference helper so EXTRA also receives ETA/ETD semantics', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(
    transportScript,
    /function createVehicleIconButton\(scope, vehicle, assignedRows\) \{[\s\S]*const departureTime = getVehicleReferenceLabel\([\s\S]*vehicle && vehicle\.route_kind[\s\S]*\);/
  );
  assert.match(
    transportScript,
    /function createVehicleManagementTable\(scope, registryRows\) \{[\s\S]*const departureTime = getVehicleReferenceLabel\([\s\S]*rowData && rowData\.route_kind[\s\S]*\);/
  );
});

test('transport vehicle buttons resolve icon paths from full vehicle metadata so temporary rows can use orange assets', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportScript, /iconImage\.src = mapVehicleIconPath\(vehicle\);/);
  assert.doesNotMatch(transportScript, /iconImage\.src = mapVehicleIconPath\(vehicle\.tipo\);/);
});

test('transport vehicle modal keeps a dedicated extra time-label hook and route-sensitive ETA/ETD copy wiring', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );

  assert.match(transportHtml, /data-extra-departure-label/);
  assert.match(transportScript, /function getExtraVehicleDepartureFieldKey\(routeKind\) \{/);
  assert.match(transportScript, /function syncExtraVehicleDepartureFieldCopy\(scope\) \{/);
  assert.match(transportScript, /vehicleForm\.elements\.route_kind\.addEventListener\("change", function \(\) \{[\s\S]*syncVehicleModalFields\(/);
  assert.match(transportScript, /vehicleForm\.elements\.route_kind\.value = Object\.prototype\.hasOwnProperty\.call\(ROUTE_KIND_KEYS, currentRouteKind\)[\s\S]*currentRouteKind[\s\S]*getSelectedRouteKind\(\);/);
  assert.match(transportI18n, /etaTime:/);
  assert.match(transportI18n, /etdTime:/);
  assert.match(transportI18n, /extraHomeToWork:/);
  assert.match(transportI18n, /extraWorkToHome:/);
});

test('transport vehicle buttons keep title and aria-label aligned with the full route and reference copy', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(
    transportScript,
    /function createVehicleIconButton\(scope, vehicle, assignedRows\) \{[\s\S]*vehicleButton\.title = t\("misc\.vehicleButtonTitle", \{[\s\S]*if \(scope === "extra" && vehicle\.route_kind\) \{[\s\S]*vehicleButton\.title = `\$\{vehicleButton\.title\} \| \$\{getRouteKindLabel\(vehicle\.route_kind\)\}`;[\s\S]*if \(departureLabel\) \{[\s\S]*vehicleButton\.title = `\$\{vehicleButton\.title\} \| \$\{departureTime\}`;[\s\S]*if \(pendingAllocationMessage\) \{[\s\S]*vehicleButton\.title = `\$\{vehicleButton\.title\} \| \$\{pendingAllocationMessage\}`;[\s\S]*vehicleButton\.setAttribute\("aria-label", vehicleButton\.title\);/
  );
});

test('transport settings syncs the arrive-at-work field with load and save without touching the inline route time control', async () => {
  const savedSettingsBodies = [];

  await withTransportPageHarness(
    {
      settingsResponse: {
        arrive_at_work_time: '07:35',
        work_to_home_time: '16:15',
        last_update_time: '16:00',
        extra_car_tolerance_minutes: 30,
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
      },
      settingsPutHandler(request) {
        const payload = JSON.parse(request.body || '{}');
        savedSettingsBodies.push(payload);
        return createFetchResponse(
          {
            arrive_at_work_time: payload.arrive_at_work_time,
            work_to_home_time: payload.work_to_home_time,
            last_update_time: payload.last_update_time,
            extra_car_tolerance_minutes: payload.extra_car_tolerance_minutes,
            price_currency_code: payload.price_currency_code,
            price_rate_unit: payload.price_rate_unit,
            available_currencies: [{ code: 'USD', display_label: 'US Dollar' }],
            default_car_seats: payload.default_car_seats,
            default_minivan_seats: payload.default_minivan_seats,
            default_van_seats: payload.default_van_seats,
            default_bus_seats: payload.default_bus_seats,
            default_car_price: payload.default_car_price,
            default_minivan_price: payload.default_minivan_price,
            default_van_price: payload.default_van_price,
            default_bus_price: payload.default_bus_price,
            default_tolerance_minutes: payload.default_tolerance_minutes,
          },
          200
        );
      },
    },
    async ({ getElement, flushAsyncWork, fetchCalls }) => {
      const arriveAtWorkInput = getElement('[data-settings-arrive-at-work-time]');
      const routeTimeInput = getElement('[data-route-time-input]');

      assert.equal(arriveAtWorkInput.value, '07:35');
      assert.equal(arriveAtWorkInput.disabled, false);
      assert.equal(arriveAtWorkInput.getAttribute('aria-label'), 'Arrive at Work:');
      assert.equal(arriveAtWorkInput.placeholder, '07:45');
      assert.equal(arriveAtWorkInput.title, '07:35');
      assert.equal(routeTimeInput.value, '16:15');

      arriveAtWorkInput.value = '07:50';
      arriveAtWorkInput.dispatchEvent(createFakeEvent('change', { target: arriveAtWorkInput }));
      await flushAsyncWork();

      assert.equal(savedSettingsBodies.length, 1);
      assert.equal(savedSettingsBodies[0].arrive_at_work_time, '07:50');
      assert.equal(savedSettingsBodies[0].work_to_home_time, '16:15');
      assert.equal(savedSettingsBodies[0].last_update_time, '16:00');
      assert.equal(savedSettingsBodies[0].extra_car_tolerance_minutes, 30);
      assert.ok(
        fetchCalls.some((call) => call.method === 'PUT' && call.url.includes('/settings') && !call.url.includes('/ai/settings'))
      );
      assert.equal(routeTimeInput.value, '16:15');
      assert.equal(arriveAtWorkInput.value, '07:50');
      assert.equal(arriveAtWorkInput.title, '07:50');
    }
  );
});

test('transport settings syncs the extra car tolerance field with load and save as a dedicated preference', async () => {
  const savedSettingsBodies = [];

  await withTransportPageHarness(
    {
      settingsResponse: {
        arrive_at_work_time: '07:35',
        work_to_home_time: '16:15',
        last_update_time: '16:00',
        extra_car_tolerance_minutes: 35,
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
      },
      settingsPutHandler(request) {
        const payload = JSON.parse(request.body || '{}');
        savedSettingsBodies.push(payload);
        return createFetchResponse(
          {
            arrive_at_work_time: payload.arrive_at_work_time,
            work_to_home_time: payload.work_to_home_time,
            last_update_time: payload.last_update_time,
            extra_car_tolerance_minutes: payload.extra_car_tolerance_minutes,
            price_currency_code: payload.price_currency_code,
            price_rate_unit: payload.price_rate_unit,
            available_currencies: [{ code: 'USD', display_label: 'US Dollar' }],
            default_car_seats: payload.default_car_seats,
            default_minivan_seats: payload.default_minivan_seats,
            default_van_seats: payload.default_van_seats,
            default_bus_seats: payload.default_bus_seats,
            default_car_price: payload.default_car_price,
            default_minivan_price: payload.default_minivan_price,
            default_van_price: payload.default_van_price,
            default_bus_price: payload.default_bus_price,
            default_tolerance_minutes: payload.default_tolerance_minutes,
          },
          200
        );
      },
    },
    async ({ getElement, flushAsyncWork, fetchCalls }) => {
      const extraCarToleranceInput = getElement('[data-settings-extra-car-tolerance]');

      assert.equal(extraCarToleranceInput.value, '35');
      assert.equal(extraCarToleranceInput.disabled, false);
      assert.equal(extraCarToleranceInput.getAttribute('aria-label'), 'Extra Car Tolerance:');
      assert.equal(extraCarToleranceInput.placeholder, '30');
      assert.equal(extraCarToleranceInput.title, '35');

      extraCarToleranceInput.value = '42';
      extraCarToleranceInput.dispatchEvent(createFakeEvent('change', { target: extraCarToleranceInput }));
      await flushAsyncWork();

      assert.equal(savedSettingsBodies.length, 1);
      assert.equal(savedSettingsBodies[0].extra_car_tolerance_minutes, 42);
      assert.equal(savedSettingsBodies[0].default_tolerance_minutes, 5);
      assert.ok(
        fetchCalls.some((call) => call.method === 'PUT' && call.url.includes('/settings') && !call.url.includes('/ai/settings'))
      );
      assert.equal(extraCarToleranceInput.value, '42');
      assert.equal(extraCarToleranceInput.title, '42');
    }
  );
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
  assert.match(transportHtml, /data-ai-agent-request-kinds-legend/);
  assert.match(
    transportHtml,
    /data-ai-agent-request-kind="extra"[\s\S]*checked[\s\S]*data-ai-agent-request-kind="weekend"[\s\S]*checked[\s\S]*data-ai-agent-request-kind="regular"[\s\S]*checked/
  );
  assert.match(transportHtml, /data-ai-agent-feedback/);
  assert.match(transportHtml, /data-ai-agent-cancel/);
  assert.match(transportHtml, /data-ai-agent-submit/);
  assert.doesNotMatch(
    transportHtml,
    /<div class="transport-modal-actions transport-ai-agent-actions">\s*<button type="button" class="transport-secondary-button" data-close-ai-agent-modal>Fechar<\/button>\s*<\/div>/
  );
});

test('transport ai agent settings modal actions keep dedicated translation hooks', () => {
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

  assert.match(transportI18n, /agentSettingsCancel:/);
  assert.match(transportI18n, /agentSettingsSubmit:/);
  assert.match(transportI18n, /agentSettingsRequestKindsLegend:/);
  assert.match(transportScript, /data-ai-agent-cancel/);
  assert.match(transportScript, /t\("ai\.agentSettingsCancel"\)/);
  assert.match(transportScript, /data-ai-agent-submit/);
  assert.match(transportScript, /t\("ai\.agentSettingsSubmit"\)/);
  assert.match(transportHtml, /data-i18n-text="requests\.labels\.extra"/);
  assert.match(transportHtml, /data-i18n-text="requests\.labels\.weekend"/);
  assert.match(transportHtml, /data-i18n-text="requests\.labels\.regular"/);
  assert.doesNotMatch(transportScript, /data-ai-agent-request-kind-label/);
  assert.doesNotMatch(transportScript, /t\(`requests\.labels\.\$\{requestKind\}`\)/);
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
  assert.match(transportHtml, /data-ai-settings-project/);
  assert.match(transportHtml, /data-ai-settings-provider/);
  assert.match(transportHtml, /data-ai-settings-api-key/);
  assert.match(transportHtml, /data-ai-settings-api-key-hint/);
  assert.match(transportHtml, /data-ai-settings-feedback/);
  assert.match(transportHtml, /data-ai-settings-save/);
  assert.match(transportI18n, /settingsMenuLabel:/);
  assert.match(transportI18n, /settingsSave:/);
  assert.match(transportI18n, /settingsProject:/);
  assert.match(transportI18n, /settingsProviderChangeRequiresKey:/);
  assert.match(transportScript, /function openAiSettingsModal\(\) \{/);
  assert.match(transportScript, /function saveTransportAiSettings\(\) \{/);
  assert.match(transportScript, /function buildTransportAiSettingsUrl\(projectId\) \{/);
  assert.match(transportScript, /project_id: normalizedDraft\.projectId/);
  assert.match(transportCss, /\.transport-ai-settings-modal/);
  assert.match(transportCss, /\.transport-ai-settings-api-key-hint\[data-tone="warning"\]/);
});

test('transport dashboard project visibility uses membership intersection with legacy fallback', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(
    transportScript,
    /function getRequestRowProjects\(requestRow\) \{[\s\S]*Array\.isArray\(requestRow\.projects\) && requestRow\.projects\.length[\s\S]*: \[requestRow\.projeto\];[\s\S]*return normalizedProjectNames;[\s\S]*\}/
  );
  assert.match(
    transportScript,
    /function isRequestVisibleForProjects\(requestRow\) \{[\s\S]*if \(!requestProjectNames\.length\) \{[\s\S]*return true;[\s\S]*\}[\s\S]*return requestProjectNames\.some\(function \(projectName\) \{[\s\S]*return isProjectVisible\(projectName\);[\s\S]*\}\);[\s\S]*\}/
  );
  assert.match(
    transportScript,
    /function getVisibleRequestsForKind\(kind\) \{[\s\S]*return isRequestVisibleForProjects\(requestRow\);[\s\S]*\}/
  );
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
    'ai.settingsProject',
    'ai.settingsSelectProject',
    'ai.settingsNoProjectsAvailable',
    'ai.settingsProviderChangeRequiresKey',
    'ai.agentSettingsCancel',
    'ai.agentSettingsSubmit',
    'ai.agentSettingsSubmitting',
    'ai.agentSettingsSubmittingSingleRequestKind',
    'ai.agentSettingsInvalidTimes',
    'ai.agentSettingsNoRequestKindsSelected',
    'ai.agentSettingsReadyForReview',
    'ai.routeCalculationFailed',
    'ai.errors.configurationError',
    'ai.errors.emptyScopeError',
    'ai.errors.capacityError',
    'ai.errors.solverError',
    'ai.errors.geocodingError',
    'ai.errors.routeProviderError',
    'ai.errors.llmInvokeError',
    'ai.errors.llmResponseError',
    'ai.errors.deterministicValidationError',
    'ai.errors.unexpectedError',
    'ai.errors.baselineRestored',
    'ai.errors.baselineRestoreError',
    'ai.review.passengers.pendingRequest',
    'ai.review.passengers.empty',
    'ai.review.passengers.allocatedTitle',
    'ai.review.passengers.unallocatedTitle',
    'ai.review.passengers.fields.project',
    'ai.review.passengers.fields.requestKind',
    'ai.review.passengers.fields.vehicle',
    'ai.review.passengers.fields.pickupOrder',
    'ai.review.passengers.fields.pickup',
    'ai.review.passengers.fields.arrival',
    'ai.review.routes.empty',
    'ai.review.routes.emptyStops',
    'ai.review.routes.fields.project',
    'ai.review.routes.fields.duration',
    'ai.review.routes.fields.cost',
    'ai.review.audit.summary.promptVersion',
    'ai.review.audit.summary.routeProvider',
    'ai.review.audit.summary.model',
    'ai.review.audit.summary.planningInput',
    'ai.review.audit.anchorBadge',
    'ai.review.audit.windowNote',
    'ai.review.audit.extraToleranceNote',
    'ai.review.audit.emptyClusters',
    'ai.review.units.minuteShort',
    'ai.review.counts.request.other',
    'ai.review.statuses.proposed',
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
  assert.equal(localizedTransportPage.translateTransportText('ai.settingsMenuLabel'), 'Configurações de IA');
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
    requestKinds: ['extra', 'weekend', 'regular'],
  });

  assert.deepEqual(transportPage.readAiAgentSettingsDraft(undefined), {
    earliestBoardingTime: '06:50',
    arrivalAtWorkTime: '07:45',
    requestKinds: ['extra', 'weekend', 'regular'],
  });
  assert.deepEqual(
    transportPage.readAiAgentSettingsDraft({
      earliestBoardingInput: { value: '06:55' },
      arrivalAtWorkInput: { value: '07:35' },
      requestKindInputs: [
        {
          checked: false,
          getAttribute() { return 'extra'; },
          value: 'extra',
        },
        {
          checked: true,
          getAttribute() { return 'weekend'; },
          value: 'weekend',
        },
      ],
    }),
    {
      earliestBoardingTime: '06:55',
      arrivalAtWorkTime: '07:35',
      requestKinds: ['weekend'],
    }
  );
  assert.deepEqual(
    transportPage.readAiAgentSettingsDraft({
      earliestBoardingTime: '',
      arrivalAtWorkTime: '07:35',
      requestKinds: [],
    }),
    {
      earliestBoardingTime: '',
      arrivalAtWorkTime: '07:35',
      requestKinds: [],
    }
  );

  assert.deepEqual(
    transportPage.validateAiAgentSettingsDraft({
      earliestBoardingTime: '06:50',
      arrivalAtWorkTime: '07:45',
      requestKinds: ['regular'],
    }),
    {
      ok: true,
      messageKey: '',
      field: '',
      draft: {
        earliestBoardingTime: '06:50',
        arrivalAtWorkTime: '07:45',
        requestKinds: ['regular'],
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

  const noRequestKinds = transportPage.validateAiAgentSettingsDraft({
    earliestBoardingTime: '06:50',
    arrivalAtWorkTime: '07:45',
    requestKinds: [],
  });
  assert.equal(noRequestKinds.ok, false);
  assert.equal(noRequestKinds.field, 'requestKinds');
  assert.equal(noRequestKinds.messageKey, 'ai.agentSettingsNoRequestKindsSelected');
});

test('transport ai route request helpers build the backend payload and only poll active run states', () => {
  const localizedTransportPage = loadTransportPageWithI18n();
  localizedTransportPage.setActiveTransportLanguageCode('en');

  assert.deepEqual(
    localizedTransportPage.buildAiAgentSubmittingFeedbackOptions(['weekend']),
    {
      key: 'ai.agentSettingsSubmittingSingleRequestKind',
      values: {
        requestKind: 'WEEKEND',
      },
    }
  );

  assert.deepEqual(
    localizedTransportPage.buildAiAgentSubmittingFeedbackOptions(['extra', 'regular']),
    {
      key: 'ai.agentSettingsSubmitting',
    }
  );

  assert.deepEqual(
    transportPage.buildTransportAiDashboardScope(
      [
        { id: 9, name: 'P83' },
        { id: 4, name: 'P80' },
        { id: 9, name: 'P83' },
        { id: 12, name: 'P90' },
      ],
      {
        P83: false,
        P80: true,
        P90: true,
      },
      ['extra', 'regular']
    ),
    {
      project_ids: [4, 12],
      request_kinds: ['extra', 'regular'],
    }
  );

  assert.deepEqual(transportPage.buildTransportAiDashboardScope([], {}, ['weekend']), {
    request_kinds: ['weekend'],
  });

  assert.deepEqual(
    transportPage.buildTransportAiRouteCalculationPayload(
      '2026-06-13',
      'home_to_work',
      {
        earliestBoardingTime: '06:50',
        arrivalAtWorkTime: '07:45',
        requestKinds: ['weekend', 'regular'],
      },
      {
        project_ids: [4, 12],
      }
    ),
    {
      service_date: '2026-06-13',
      route_kind: 'home_to_work',
      earliest_boarding_time: '06:50',
      arrival_at_work_time: '07:45',
      request_route_kinds: {
        weekend: 'home_to_work',
        regular: 'home_to_work',
      },
      dashboard_scope: {
        project_ids: [4, 12],
        request_kinds: ['weekend', 'regular'],
      },
    }
  );

  assert.deepEqual(
    transportPage.buildTransportAiRouteCalculationPayload(
      '2026-06-13',
      'work_to_home',
      {
        earliestBoardingTime: '06:50',
        arrivalAtWorkTime: '07:45',
        requestKinds: ['extra', 'regular'],
      },
      {
        project_ids: [4, 12],
      }
    ),
    {
      service_date: '2026-06-13',
      route_kind: 'work_to_home',
      earliest_boarding_time: '06:50',
      arrival_at_work_time: '07:45',
      request_route_kinds: {
        extra: 'work_to_home',
        regular: 'home_to_work',
      },
      dashboard_scope: {
        project_ids: [4, 12],
        request_kinds: ['extra', 'regular'],
      },
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

  assert.equal(
    transportPage.hasRenderableTransportAiReview({
      review_state: 'review_ready',
      suggestion_ready: false,
      suggestion: null,
    }),
    true
  );
  assert.equal(
    transportPage.hasRenderableTransportAiReview({
      review_state: 'review_with_exceptions',
      suggestion_ready: false,
      suggestion: null,
    }),
    true
  );
  assert.equal(
    transportPage.hasRenderableTransportAiReview({
      review_state: 'fatal_error',
      suggestion_ready: true,
      suggestion: { suggestion_key: 'transport-ai-suggestion:stale' },
    }),
    false
  );
  assert.equal(
    transportPage.hasRenderableTransportAiReview({
      suggestion_ready: true,
      suggestion: { suggestion_key: 'transport-ai-suggestion:fallback' },
    }),
    true
  );
});

test('transport ai structured error message resolves failure_category to friendly localized copy', () => {
  const localizedPage = loadTransportPageWithI18n();
  localizedPage.setActiveTransportLanguageCode('en');

  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({ failure_category: 'capacity' }),
    /route plan could not be completed for all passengers/i
  );
  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({ failure_category: 'configuration' }),
    /not enabled or is missing required settings/i
  );
  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({ failure_category: 'empty_scope' }),
    /no eligible requests were found/i
  );
  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({ failure_category: 'solver' }),
    /route solver could not find a valid plan/i
  );
  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({ failure_category: 'geocoding' }),
    /addresses could not be resolved/i
  );
  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({ failure_category: 'route_provider' }),
    /route provider returned an error/i
  );
  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({ failure_category: 'llm_invoke' }),
    /ai model could not be reached/i
  );
  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({ failure_category: 'llm_response' }),
    /ai model returned an unexpected response/i
  );
  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({ failure_category: 'deterministic_validation' }),
    /did not pass validation/i
  );
  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({ failure_category: 'unexpected' }),
    /unexpected error occurred/i
  );
});

test('transport ai structured error message falls back to legacy map then raw message then generic key', () => {
  const localizedPage = loadTransportPageWithI18n();
  localizedPage.setActiveTransportLanguageCode('en');

  assert.equal(
    localizedPage.resolveTransportAiStructuredMessage({ message: 'Invalid key or password.' }),
    'Invalid key or password.'
  );

  assert.equal(
    localizedPage.resolveTransportAiStructuredMessage({ message: 'Some backend-generated friendly message.' }),
    'Some backend-generated friendly message.'
  );

  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({}),
    /route calculation failed/i
  );
});

test('transport ai structured error message respects message_key as primary lookup when key exists in frontend dictionary', () => {
  const localizedPage = loadTransportPageWithI18n();
  localizedPage.setActiveTransportLanguageCode('en');

  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({ message_key: 'ai.errors.capacityError' }),
    /route plan could not be completed for all passengers/i
  );

  assert.match(
    localizedPage.resolveTransportAiStructuredMessage({
      message_key: 'transport_ai.error.unknown_backend_key',
      failure_category: 'solver',
    }),
    /route solver could not find a valid plan/i
  );
});

test('transport ai baseline complement detects restore outcome from message text', () => {
  const localizedPage = loadTransportPageWithI18n();
  localizedPage.setActiveTransportLanguageCode('en');

  assert.match(
    localizedPage.resolveTransportAiBaselineComplement({ message: 'Some error. Baseline restored.' }),
    /baseline was restored successfully/i
  );
  assert.match(
    localizedPage.resolveTransportAiBaselineComplement({ message: 'Some error. Baseline restored successfully.' }),
    /baseline was restored successfully/i
  );
  assert.match(
    localizedPage.resolveTransportAiBaselineComplement({ message: 'Some error. Baseline restore requires manual review.' }),
    /requires manual review/i
  );
  assert.match(
    localizedPage.resolveTransportAiBaselineComplement({ message: 'Some error. Baseline restore raised an unexpected error.' }),
    /requires manual review/i
  );
  assert.equal(
    localizedPage.resolveTransportAiBaselineComplement({ message: 'Some plain error without restore mention.' }),
    null
  );
  assert.equal(
    localizedPage.resolveTransportAiBaselineComplement({}),
    null
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
  assert.match(transportI18n, /agentSettingsNoRequestKindsSelected:/);
  assert.match(transportScript, /function requestAiRoutes\(\) \{/);
  assert.match(
    transportScript,
    /const validation = validateAiAgentSettingsDraft\(draft\);[\s\S]*if \(!validation\.ok\) \{[\s\S]*return Promise\.resolve\(null\);[\s\S]*\}[\s\S]*requestJson\(`\$\{TRANSPORT_API_PREFIX\}\/ai\/route-calculations`/
  );
  assert.match(
    transportScript,
    /buildTransportAiDashboardScope\([\s\S]*getProjectRows\(\),[\s\S]*state\.projectVisibility,[\s\S]*validation\.draft\.requestKinds[\s\S]*buildTransportAiRouteCalculationPayload\([\s\S]*getCurrentServiceDateIso\(\),[\s\S]*getSelectedRouteKind\(\),[\s\S]*validation\.draft/
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
    /setAiChangesSummary\([\s\S]*commandErrorOptions[\s\S]*actionCopy\.errorKey/
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
    /if \(error && Number\(error\.status\) === 404\) \{[\s\S]*setStatus\("", "info", \{ key: "ai\.noSavedSuggestion" \}\);/
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

test('transport ai changes modal freezes review as the primary surface and keeps supporting panels secondary', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(transportHtml, /data-ai-changes-tabs/);
  assert.match(transportHtml, /data-ai-changes-tab="review"/);
  assert.match(transportHtml, /data-ai-changes-tab-role="primary"/);
  assert.match(transportHtml, /data-ai-changes-tab="vehicles"/);
  assert.match(transportHtml, /data-ai-changes-tab="passengers"/);
  assert.match(transportHtml, /data-ai-changes-tab="routes"/);
  assert.match(transportHtml, /data-ai-changes-tab="audit"/);
  assert.match(transportHtml, /data-ai-review-contract/);
  assert.match(transportHtml, /data-ai-review-vehicle-tables/);
  assert.match(transportHtml, /data-ai-review-management/);
  assert.match(transportHtml, /data-ai-review-exceptions/);
  assert.match(transportHtml, /data-ai-review-row-field="request_id"/);
  assert.match(transportHtml, /data-ai-review-row-field="user_name"/);
  assert.match(transportHtml, /data-ai-review-row-field="user_address"/);
  assert.match(transportHtml, /data-ai-review-row-field="home_to_work_boarding"/);
  assert.match(transportHtml, /data-ai-review-row-field="work_to_home_dropoff"/);
  assert.match(transportHtml, /data-ai-review-row-field="pickup_order"/);
  assert.match(transportHtml, /data-ai-review-workspace/);
  assert.match(transportHtml, /data-ai-review-vehicle-table-list/);
  assert.match(transportHtml, /data-ai-review-management-placeholder/);
  assert.match(transportHtml, /data-ai-changes-panel="review"[^>]*data-ai-changes-panel-role="primary"/);
  assert.match(transportHtml, /data-ai-changes-panel="passengers"[^>]*data-ai-changes-panel-role="supporting-detail"/);
  assert.match(transportHtml, /data-ai-changes-panel="routes"[^>]*data-ai-changes-panel-role="supporting-detail"/);
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
  assert.match(transportCss, /\.transport-ai-review-contract,\s*[\s\S]*\.transport-ai-review-contract-section\s*\{[\s\S]*display:\s*grid/);
  assert.match(transportCss, /\.transport-ai-review-workspace,\s*[\s\S]*\.transport-ai-review-vehicle-table-list,\s*[\s\S]*\.transport-ai-review-vehicle-head\s*\{[\s\S]*display:\s*grid/);
  assert.match(transportCss, /\.transport-ai-review-contract-field-list\s*\{[\s\S]*padding-left:\s*18px/);
  assert.match(transportCss, /\.transport-ai-changes-panel\[data-ai-changes-panel-role="primary"\]\s*\{[\s\S]*linear-gradient/);
  assert.match(
    transportCss,
    /@media \(max-width: 860px\) \{[\s\S]*\.transport-ai-changes-hero,[\s\S]*\.transport-ai-changes-panels\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/
  );
  assert.match(
    transportCss,
    /@media \(max-width: 640px\) \{[\s\S]*\.transport-ai-changes-actions\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/
  );
});

test('transport ai review contract freezes per-vehicle tables, management metrics, and exception handling before consolidation lands', () => {
  const contract = transportPage.getTransportAiReviewTargetContract();

  assert.equal(contract.primaryPanelKey, 'review');
  assert.deepEqual(contract.primarySurface, ['vehicle_tables', 'management_table', 'exceptions']);
  assert.deepEqual(contract.canonicalRow.internalFields, ['request_id', 'pickup_order']);
  assert.deepEqual(
    contract.canonicalRow.visibleFields,
    ['user_name', 'user_address', 'home_to_work_boarding', 'work_to_home_dropoff']
  );
  assert.equal(contract.ordering.primaryRouteKind, 'home_to_work');
  assert.equal(contract.ordering.primaryField, 'pickup_order');
  assert.equal(contract.ordering.fallbackField, 'scheduled_pickup_time');
  assert.equal(contract.addressSource.joinKey, 'request_id');
  assert.equal(contract.addressSource.sourceCollection, 'route_itineraries.stops');
  assert.equal(contract.addressSource.field, 'address');
  assert.equal(contract.addressSource.forbidFormattedUiText, true);
  assert.equal(contract.deferredPopulation.work_to_home_dropoff.allowPlaceholder, true);
  assert.equal(contract.deferredPopulation.work_to_home_dropoff.dependency, 'modification_11');
  assert.strictEqual(contract.bidirectionalPlanning, transportPage.getTransportAiBidirectionalPlanContract());
  assert.deepEqual(contract.supportingPanels, ['vehicles', 'passengers', 'routes']);
  assert.equal(contract.auditPanelKey, 'audit');
});

test('transport ai bidirectional plan contract freezes derived return semantics before planner changes land', () => {
  const contract = transportPage.getTransportAiBidirectionalPlanContract();

  assert.equal(contract.regularWeekend.outboundSourceOfTruth, 'home_to_work');
  assert.equal(contract.regularWeekend.returnLegMode, 'derived_from_outbound');
  assert.equal(contract.regularWeekend.sameVehicleRequired, true);
  assert.equal(contract.regularWeekend.samePassengersRequired, true);
  assert.equal(contract.regularWeekend.returnStopOrder, 'reverse_outbound_stops');
  assert.equal(contract.regularWeekend.returnDurationStrategy, 'recalculate_work_to_home');
  assert.equal(contract.extra.directionMode, 'actual_request_direction');
  assert.equal(contract.extra.forbidProjectDestinationOnWorkToHome, true);
  assert.equal(contract.fields.canonicalReturnTime, 'scheduled_dropoff_time');
  assert.equal(contract.fields.outboundBoardingTime, 'boarding_time');
  assert.equal(contract.review.workToHomeSource, 'backend_plan');
  assert.equal(contract.review.forbidLocalReturnReconstruction, true);
  assert.equal(contract.vehicleRef.allowsMultipleRealLegs, true);
  assert.equal(contract.vehicleRef.groupingKey, 'vehicle_ref');
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
        audit: {
          planning_input_hash: 'b'.repeat(64),
          extra_car_tolerance_minutes: 30,
          extra_clusters: [
            {
              partition_key: 'extra:P80:SG',
              cluster_key: 'cluster:night:1',
              anchor_requested_time: '19:20',
              earliest_requested_time: '19:00',
              latest_requested_time: '19:20',
              request_ids: [101, 102],
              request_count: 2,
            },
            {
              partition_key: 'extra:P80:SG',
              cluster_key: 'cluster:night:2',
              anchor_requested_time: '19:45',
              earliest_requested_time: '19:45',
              latest_requested_time: '19:45',
              request_ids: [103],
              request_count: 1,
            },
          ],
        },
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
          vehicle_actions: [
            {
              action_type: 'update',
              vehicle_id: 11,
              before: {
                vehicle_type: 'carro',
                capacity: 4,
                plate: 'SGX1234',
                service_scope: 'extra',
                estimated_cost: 120,
              },
              after: {
                vehicle_type: 'van',
                capacity: 12,
                plate: 'SGX1234',
                service_scope: 'extra',
                estimated_cost: 95,
              },
            },
          ],
          vehicle_review_tables: [
            {
              vehicle_ref: 'existing:11',
              vehicle_label: 'SGX1234',
              service_scope: 'extra',
              vehicle_type: 'van',
              route_kind: 'home_to_work',
              vehicle_id: 11,
              estimated_cost: 95,
              action_type: 'update',
              action_key: 'vehicle:update:11',
              action_rationale: 'Keep the stable route and swap to the cheaper vehicle profile.',
              header_badges: [
                { text: 'Extra', tone: 'info' },
                { text: 'Update', tone: 'warning' },
              ],
              rows: [
                {
                  request_id: 101,
                  user_id: 501,
                  request_kind: 'extra',
                  pickup_order: 0,
                  user_name: 'Alice Tan',
                  user_address: '7 Garden Street',
                  home_to_work_boarding: '07:05',
                  work_to_home_dropoff: null,
                  work_to_home_dropoff_is_placeholder: true,
                },
              ],
            },
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
  assert.equal(summaryModel.passengers.allocatedText, '2 allocated passengers');
  assert.equal(summaryModel.passengers.issueText, '1 issue');
  assert.equal(summaryModel.window.displayText, '06:50 -> 07:45');
  assert.equal(summaryModel.runtime.promptVersionText, 'transport_ai_route_planner_v1');
  assert.equal(summaryModel.runtime.routeProviderText, '--');
  assert.equal(summaryModel.runtime.modelText, '--');
  assert.equal(summaryModel.audit.extraToleranceText, '30 min');
  assert.equal(summaryModel.audit.extraClusterCountText, '2 clusters');
  assert.equal(summaryModel.audit.extraClusterAnchorText, '19:20, 19:45');
  assert.equal(summaryModel.review.items.length, 1);
  assert.equal(summaryModel.review.items[0].titleText, 'SGX1234');
  assert.equal(summaryModel.review.items[0].metaItems.find((item) => item.label === 'Seats').value, '12');
  assert.equal(summaryModel.review.items[0].rows[0].userAddressText, '7 Garden Street');
  assert.equal(summaryModel.review.items[0].rows[0].workToHomeDropoffText, 'Not planned for this route');
  assert.equal(summaryModel.review.management.titleText, 'Management Table');
  assert.deepEqual(summaryModel.review.management.columns, {
    metric: 'Metric',
    current: 'Current',
    suggested: 'Suggested',
    delta: 'Delta',
    notes: 'Notes',
  });
  assert.equal(summaryModel.review.management.rows.length, 6);
  const managementRowsByKey = Object.fromEntries(
    summaryModel.review.management.rows.map((row) => [row.key, row])
  );
  assert.match(managementRowsByKey.total_cost.currentText, /120\.00/);
  assert.match(managementRowsByKey.total_cost.suggestedText, /95\.00/);
  assert.match(managementRowsByKey.total_cost.deltaText, /25\.00/);
  assert.equal(managementRowsByKey.vehicles.currentText, '2');
  assert.equal(managementRowsByKey.vehicles.suggestedText, '1');
  assert.equal(managementRowsByKey.actions.suggestedText, '2');
  assert.equal(managementRowsByKey.passengers.suggestedText, '2');
  assert.equal(managementRowsByKey.routes.suggestedText, '1');
  assert.equal(managementRowsByKey.issues.suggestedText, '1');
  assert.equal(managementRowsByKey.issues.deltaText, '1');
  assert.equal(summaryModel.statusBadges[0].text, 'Run Proposed');
  assert.match(summaryModel.cost.suggestedText, /95\.00/);
  assert.equal(summaryModel.topCards[0].badges[0].text, 'Savings $25.00');
  assert.ok(summaryModel.detailItems.some((item) => item.label === 'Extra Tolerance' && item.value === '30 min'));
});

test('transport ai review workspace uses one consolidated table per vehicle from vehicle_review_tables', () => {
  const summaryModel = transportPage.renderAiChangesSummary({
    runStatusResponse: {
      status: 'proposed',
      route_kind: 'home_to_work',
      suggestion: {
        plan: {
          route_kind: 'home_to_work',
          earliest_boarding_time: '06:50',
          arrival_at_work_time: '07:45',
          passenger_allocations: [],
          route_itineraries: [],
          vehicle_actions: [
            {
              action_type: 'keep',
              vehicle_id: 11,
              before: {
                vehicle_type: 'van',
                capacity: 10,
                plate: 'SGX1234',
                service_scope: 'extra',
                estimated_cost: 24,
              },
              after: {
                vehicle_type: 'van',
                capacity: 10,
                plate: 'SGX1234',
                service_scope: 'extra',
                estimated_cost: 24,
              },
            },
            {
              action_type: 'create',
              client_vehicle_key: 'solver-created-2',
              before: {},
              after: {
                vehicle_type: 'minivan',
                capacity: 6,
                service_scope: 'extra',
                estimated_cost: 40,
              },
            },
          ],
          vehicle_review_tables: [
            {
              vehicle_ref: 'existing:11',
              vehicle_label: 'SGX1234',
              service_scope: 'extra',
              vehicle_type: 'van',
              route_kind: 'home_to_work',
              vehicle_id: 11,
              estimated_cost: 24,
              action_type: 'keep',
              header_badges: [{ text: 'Extra', tone: 'info' }],
              rows: [
                {
                  request_id: 301,
                  user_id: 501,
                  request_kind: 'extra',
                  pickup_order: 0,
                  user_name: 'Alice Tan',
                  user_address: '7 Garden Street',
                  home_to_work_boarding: '07:05',
                  home_to_work_boarding_is_placeholder: false,
                  work_to_home_dropoff: null,
                  work_to_home_dropoff_is_placeholder: true,
                },
              ],
            },
            {
              vehicle_ref: 'new:solver-created-2',
              vehicle_label: 'solver-created-2',
              service_scope: 'extra',
              vehicle_type: 'minivan',
              route_kind: 'home_to_work',
              client_vehicle_key: 'solver-created-2',
              estimated_cost: 40,
              action_type: 'create',
              header_badges: [{ text: 'Create', tone: 'success' }],
              rows: [
                {
                  request_id: 302,
                  user_id: 502,
                  request_kind: 'extra',
                  pickup_order: 0,
                  user_name: 'Bob Lee',
                  user_address: '88 Hill Street',
                  home_to_work_boarding: '07:15',
                  home_to_work_boarding_is_placeholder: false,
                  work_to_home_dropoff: null,
                  work_to_home_dropoff_is_placeholder: true,
                },
              ],
            },
          ],
          cost_summary: {
            price_currency_code: 'USD',
            price_rate_unit: 'day',
            current_total_estimated_cost: 120,
            suggested_total_estimated_cost: 64,
            estimated_cost_delta: -56,
            current_vehicle_count: 2,
            suggested_vehicle_count: 2,
          },
          change_summary: {
            total_vehicle_actions: 2,
            keep_count: 1,
            create_count: 1,
            update_count: 0,
            remove_from_day_count: 0,
            by_vehicle_type: [],
          },
          validation_issues: [],
        },
      },
    },
    fallbackCurrencyCode: 'USD',
  });

  assert.deepEqual(
    summaryModel.review.items.map((item) => item.vehicleRef),
    ['existing:11', 'new:solver-created-2']
  );
  assert.equal(summaryModel.review.items[0].rows[0].userNameText, 'Alice Tan');
  assert.equal(summaryModel.review.items[1].rows[0].userNameText, 'Bob Lee');
  assert.equal(summaryModel.review.columns.userName, 'User Name');
  assert.equal(summaryModel.review.columns.workToHomeDropoff, 'Work to Home - Dropoff');
  assert.equal(summaryModel.review.items[0].rows[0].workToHomeDropoffText, 'Not planned for this route');
});

test('transport ai review keeps a single row when bidirectional timings are already consolidated', () => {
  const summaryModel = transportPage.renderAiChangesSummary({
    runStatusResponse: {
      status: 'proposed',
      route_kind: 'home_to_work',
      suggestion: {
        plan: {
          route_kind: 'home_to_work',
          earliest_boarding_time: '06:50',
          arrival_at_work_time: '07:45',
          passenger_allocations: [],
          route_itineraries: [],
          vehicle_actions: [],
          vehicle_review_tables: [
            {
              vehicle_ref: 'new:solver-1',
              vehicle_label: 'SGX1234',
              service_scope: 'regular',
              vehicle_type: 'van',
              route_kind: null,
              estimated_cost: 60,
              rows: [
                {
                  request_id: 301,
                  user_id: 501,
                  request_kind: 'regular',
                  pickup_order: 0,
                  user_name: 'Alice Tan',
                  user_address: '7 Garden Street',
                  home_to_work_boarding: '07:05',
                  home_to_work_boarding_is_placeholder: false,
                  work_to_home_dropoff: '18:40',
                  work_to_home_dropoff_is_placeholder: false,
                },
              ],
            },
          ],
          cost_summary: {},
          change_summary: {},
          validation_issues: [],
        },
      },
    },
    fallbackCurrencyCode: 'USD',
  });

  assert.equal(summaryModel.review.items.length, 1);
  assert.equal(summaryModel.review.items[0].rows.length, 1);
  assert.equal(summaryModel.review.items[0].rows[0].homeToWorkBoardingText, '07:05');
  assert.equal(summaryModel.review.items[0].rows[0].homeToWorkBoardingIsPlaceholder, false);
  assert.equal(summaryModel.review.items[0].rows[0].workToHomeDropoffText, '18:40');
  assert.equal(summaryModel.review.items[0].rows[0].workToHomeDropoffIsPlaceholder, false);
});

test('transport ai review uses route placeholder for extra work-to-home-only rows', () => {
  const summaryModel = transportPage.renderAiChangesSummary({
    runStatusResponse: {
      status: 'proposed',
      route_kind: 'work_to_home',
      suggestion: {
        plan: {
          route_kind: 'work_to_home',
          earliest_boarding_time: '06:50',
          arrival_at_work_time: '07:45',
          passenger_allocations: [],
          route_itineraries: [],
          vehicle_actions: [],
          vehicle_review_tables: [
            {
              vehicle_ref: 'new:solver-2',
              vehicle_label: 'SGY7788',
              service_scope: 'extra',
              vehicle_type: 'van',
              route_kind: 'work_to_home',
              estimated_cost: 32,
              rows: [
                {
                  request_id: 302,
                  user_id: 502,
                  request_kind: 'extra',
                  pickup_order: 0,
                  user_name: 'Bob Lim',
                  user_address: null,
                  home_to_work_boarding: null,
                  home_to_work_boarding_is_placeholder: true,
                  work_to_home_dropoff: '18:55',
                  work_to_home_dropoff_is_placeholder: false,
                },
              ],
            },
          ],
          cost_summary: {},
          change_summary: {},
          validation_issues: [],
        },
      },
    },
    fallbackCurrencyCode: 'USD',
  });

  assert.equal(summaryModel.review.items[0].rows[0].homeToWorkBoardingText, 'Not planned for this route');
  assert.equal(summaryModel.review.items[0].rows[0].homeToWorkBoardingIsPlaceholder, true);
  assert.equal(summaryModel.review.items[0].rows[0].workToHomeDropoffText, '18:55');
  assert.equal(summaryModel.review.items[0].rows[0].workToHomeDropoffIsPlaceholder, false);
});

test('transport ai review uses a neutral legacy placeholder for rows without return-leg data', () => {
  const summaryModel = transportPage.renderAiChangesSummary({
    runStatusResponse: {
      status: 'proposed',
      route_kind: 'home_to_work',
      suggestion: {
        plan: {
          route_kind: 'home_to_work',
          earliest_boarding_time: '06:50',
          arrival_at_work_time: '07:45',
          passenger_allocations: [],
          route_itineraries: [],
          vehicle_actions: [],
          vehicle_review_tables: [
            {
              vehicle_ref: 'existing:22',
              vehicle_label: 'SGR5522',
              service_scope: 'regular',
              vehicle_type: 'van',
              route_kind: 'home_to_work',
              estimated_cost: 20,
              rows: [
                {
                  request_id: 401,
                  user_id: 601,
                  request_kind: 'regular',
                  pickup_order: 0,
                  user_name: 'Carol Ng',
                  user_address: '9 River Valley',
                  boarding_time: '18:44',
                  home_to_work_boarding: '07:00',
                  home_to_work_boarding_is_placeholder: false,
                  work_to_home_dropoff: null,
                  work_to_home_dropoff_is_placeholder: true,
                },
              ],
            },
          ],
          cost_summary: {},
          change_summary: {},
          validation_issues: [],
        },
      },
    },
    fallbackCurrencyCode: 'USD',
  });

  assert.equal(summaryModel.review.items[0].rows[0].workToHomeDropoffText, 'Unavailable in this plan');
  assert.equal(summaryModel.review.items[0].rows[0].workToHomeDropoffIsPlaceholder, true);
});

test('transport ai review directs missing return-leg rows with issues to the exceptions section', () => {
  const summaryModel = transportPage.renderAiChangesSummary({
    runStatusResponse: {
      status: 'proposed',
      route_kind: 'home_to_work',
      suggestion: {
        plan: {
          route_kind: 'home_to_work',
          earliest_boarding_time: '06:50',
          arrival_at_work_time: '07:45',
          passenger_allocations: [],
          route_itineraries: [],
          vehicle_actions: [],
          vehicle_review_tables: [
            {
              vehicle_ref: 'existing:33',
              vehicle_label: 'SGR5533',
              service_scope: 'regular',
              vehicle_type: 'van',
              route_kind: 'home_to_work',
              estimated_cost: 20,
              rows: [
                {
                  request_id: 501,
                  user_id: 701,
                  request_kind: 'regular',
                  pickup_order: 0,
                  user_name: 'Diana Koh',
                  user_address: '31 Legacy Street',
                  home_to_work_boarding: '07:02',
                  home_to_work_boarding_is_placeholder: false,
                  work_to_home_dropoff: null,
                  work_to_home_dropoff_is_placeholder: true,
                },
              ],
            },
          ],
          cost_summary: {},
          change_summary: {},
          validation_issues: [
            {
              code: 'transport_ai_return_leg_missing',
              message: 'Return leg still requires manual review.',
              blocking: false,
              request_id: 501,
            },
          ],
        },
      },
    },
    fallbackCurrencyCode: 'USD',
  });

  assert.equal(summaryModel.review.items[0].rows[0].workToHomeDropoffText, 'See exceptions');
  assert.equal(summaryModel.review.items[0].rows[0].workToHomeDropoffIsPlaceholder, true);
  assert.equal(summaryModel.review.exceptions.items.length, 1);
  assert.equal(summaryModel.review.exceptions.items[0].titleText, 'Request #501');
});

test('transport ai review exceptions keep not routed requests and blocking issues outside the vehicle tables', () => {
  const summaryModel = transportPage.renderAiChangesSummary({
    runStatusResponse: {
      status: 'proposed',
      route_kind: 'home_to_work',
      suggestion: {
        plan: {
          route_kind: 'home_to_work',
          earliest_boarding_time: '06:50',
          arrival_at_work_time: '07:45',
          passenger_allocations: [
            {
              request_id: 301,
              user_id: 501,
              vehicle_ref: 'existing:11',
              route_kind: 'home_to_work',
              request_kind: 'extra',
              nome: 'Alice Tan',
              scheduled_pickup_time: '07:05',
              projected_arrival_time: '07:45',
              pickup_order: 0,
            },
          ],
          route_itineraries: [],
          vehicle_actions: [],
          vehicle_review_tables: [
            {
              vehicle_ref: 'existing:11',
              vehicle_label: 'SGX1234',
              rows: [
                {
                  request_id: 301,
                  user_name: 'Alice Tan',
                  user_address: '7 Garden Street',
                  home_to_work_boarding: '07:05',
                  home_to_work_boarding_is_placeholder: false,
                  work_to_home_dropoff: null,
                  work_to_home_dropoff_is_placeholder: true,
                },
              ],
            },
          ],
          cost_summary: {},
          change_summary: {},
          validation_issues: [
            {
              code: 'transport_ai_request_unallocated',
              message: 'Passenger still needs manual review.',
              blocking: true,
              request_id: 203,
            },
            {
              code: 'transport_ai_capacity_violation',
              message: 'Vehicle capacity exceeds the available seats.',
              blocking: true,
            },
          ],
        },
      },
    },
    fallbackCurrencyCode: 'USD',
  });

  assert.equal(summaryModel.review.items.length, 1);
  assert.equal(summaryModel.review.exceptions.titleText, 'Exceptions / Not Routed');
  assert.equal(summaryModel.review.exceptions.items.length, 2);
  assert.equal(summaryModel.review.exceptions.items[0].titleText, 'Request #203');
  assert.equal(summaryModel.review.exceptions.items[0].badges[0].text, 'Not Routed');
  assert.equal(summaryModel.review.exceptions.items[1].titleText, 'Blocking Issue');
  assert.equal(summaryModel.review.exceptions.items[1].badges[0].text, 'Blocking Issue');
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
          route_itineraries: [
            {
              route_key: 'route:draft:1',
              partition_key: 'extra:P80:SG',
              vehicle_ref: 'draft:1',
              client_vehicle_key: 'draft:1',
              service_scope: 'extra',
              route_kind: 'home_to_work',
              vehicle_type: 'van',
              project_name: 'P80',
              country_code: 'SG',
              country_name: 'Singapore',
              estimated_cost: 32,
              total_duration_seconds: 1800,
              total_distance_meters: 8000,
              projected_arrival_time: '07:45',
              stops: [
                {
                  stop_order: 0,
                  stop_type: 'pickup',
                  scheduled_time: '07:20',
                },
              ],
            },
          ],
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
                route_kind: 'home_to_work',
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
  const routeField = actionItem.fieldRows.find((fieldRow) => fieldRow.label === 'Route');
  const etaField = actionItem.fieldRows.find((fieldRow) => fieldRow.label === 'ETA');
  const costField = actionItem.fieldRows.find((fieldRow) => fieldRow.label === 'Cost');

  assert.equal(actionItem.actionLabel, 'Add');
  assert.equal(actionItem.actionTone, 'success');
  assert.equal(actionItem.badges[1].text, 'Extra List');
  assert.equal(typeField.valueText, '-- -> Van');
  assert.equal(seatsField.valueText, '-- -> 15');
  assert.equal(identifierField.valueText, '-- -> NEW1234');
  assert.equal(listField.valueText, '-- -> Extra List');
  assert.equal(routeField.valueText, '-- -> Home To Work');
  assert.equal(etaField.valueText, '-- -> ETA 07:45h');
  assert.match(costField.valueText, /\$0\.00 -> \$32\.00/);
  assert.equal(costField.note, 'Delta +$32.00');
});

test('transport ai vehicle changes render contextualizes extra reference time as etd for return routes', () => {
  const vehicleChangesModel = transportPage.renderAiVehicleChanges({
    runStatusResponse: {
      route_kind: 'work_to_home',
      suggestion: {
        plan: {
          cost_summary: {
            price_currency_code: 'USD',
          },
          route_itineraries: [
            {
              route_key: 'route:draft:return',
              partition_key: 'extra:P80:SG',
              vehicle_ref: 'draft:return',
              client_vehicle_key: 'draft:return',
              service_scope: 'extra',
              route_kind: 'work_to_home',
              vehicle_type: 'van',
              project_name: 'P80',
              country_code: 'SG',
              country_name: 'Singapore',
              estimated_cost: 28,
              total_duration_seconds: 1200,
              total_distance_meters: 6200,
              projected_arrival_time: '19:40',
              stops: [
                {
                  stop_order: 0,
                  stop_type: 'pickup',
                  scheduled_time: '19:20',
                },
              ],
            },
          ],
          vehicle_actions: [
            {
              action_key: 'vehicle:create:return',
              action_type: 'create',
              service_scope: 'extra',
              client_vehicle_key: 'draft:return',
              after: {
                vehicle_type: 'van',
                capacity: 12,
                plate: 'RET1234',
                service_scope: 'extra',
                route_kind: 'work_to_home',
                estimated_cost: 28,
              },
              rationale: 'Create the consolidated extra return route.',
              cost_delta: 28,
            },
          ],
        },
      },
    },
  });

  const actionItem = vehicleChangesModel.items[0];
  const etdField = actionItem.fieldRows.find((fieldRow) => fieldRow.label === 'ETD');

  assert.equal(etdField.valueText, '-- -> ETD 19:20h');
  assert.match(etdField.note, /Route completion 19:40/);
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
  const referenceField = routeItem.fieldRows.find((fieldRow) => fieldRow.label === 'ETA');
  const durationField = routeItem.fieldRows.find((fieldRow) => fieldRow.label === 'Duration');
  const costField = routeItem.fieldRows.find((fieldRow) => fieldRow.label === 'Cost');

  assert.equal(routeItem.titleText, 'ROUTE123');
  assert.deepEqual(routeItem.stopItems.map((stopItem) => stopItem.stopType), ['pickup', 'pickup', 'destination']);
  assert.equal(routeItem.stopItems[0].titleText, 'Alice Tan');
  assert.equal(routeItem.stopItems[2].isDestination, true);
  assert.equal(referenceField.valueText, 'ETA 07:45h');
  assert.equal(referenceField.note, 'Home To Work');
  assert.equal(durationField.valueText, '35 min');
  assert.equal(durationField.note, '12 km');
  assert.match(costField.valueText, /\$28\.00/);
});

test('transport ai changes audit render exposes extra tolerance and temporal clusters', () => {
  const auditModel = transportPage.renderAiChangesAudit({
    runStatusResponse: getSampleLatestSuggestionResponse(),
  });

  assert.equal(auditModel.summaryItems.find((item) => item.label === 'Planning Input').note, 'Extra tolerance 30 min');
  assert.equal(auditModel.clusterItems[0].titleText, 'cluster:extra:morning:1');
  assert.equal(auditModel.clusterItems[0].subtitleText, 'extra:P80:SG');
  assert.equal(auditModel.clusterItems[0].windowText, '07:00 -> 07:20');
  assert.equal(auditModel.clusterItems[0].requestText, 'Requests #301');
  assert.match(auditModel.clusterItems[0].badges[0].text, /Anchor 07:20h/);
});

test('transport ai dynamic renderers switch language for passenger, route, and audit view models', () => {
  const localizedTransportPage = loadTransportPageWithI18n();
  const runStatusResponse = {
    suggestion: {
      plan: {
        passenger_allocations: [
          {
            request_id: 901,
            request_kind: 'extra',
            service_date: '2026-06-13',
            route_kind: 'home_to_work',
            vehicle_ref: 'existing:99',
            nome: 'Alice Tan',
            project_name: 'P80',
            pickup_order: 0,
            scheduled_pickup_time: '07:05',
            projected_arrival_time: '07:45',
            rationale: 'Keep grouped allocation.',
          },
        ],
        route_itineraries: [
          {
            route_key: 'route:existing:99',
            partition_key: 'extra:P80:SG',
            vehicle_ref: 'existing:99',
            service_scope: 'extra',
            route_kind: 'home_to_work',
            plate: 'SGX9999',
            project_name: 'P80',
            estimated_cost: 24,
            total_duration_seconds: 1800,
            total_distance_meters: 8200,
            projected_arrival_time: '07:45',
            stops: [],
          },
        ],
        validation_issues: [
          {
            code: 'transport_ai_request_unallocated',
            message: 'Needs manual review.',
            blocking: true,
            request_id: 902,
          },
        ],
        cost_summary: {
          price_currency_code: 'USD',
        },
      },
      audit: {
        planning_input_hash: 'a'.repeat(64),
        extra_car_tolerance_minutes: 30,
        extra_clusters: [
          {
            partition_key: 'extra:P80:SG',
            cluster_key: 'cluster:extra:morning:1',
            anchor_requested_time: '07:20',
            earliest_requested_time: '07:00',
            latest_requested_time: '07:20',
            request_ids: [301],
            request_count: 1,
          },
        ],
      },
      prompt_version: 'transport_ai_route_planner_v4',
    },
    route_kind: 'home_to_work',
    route_provider: 'mock-provider',
    llm_provider: 'OpenAI',
    llm_model: 'gpt-5.4-2026-03-05',
    llm_reasoning_effort: 'high',
  };

  localizedTransportPage.setActiveTransportLanguageCode('en');
  const enPassenger = localizedTransportPage.renderAiPassengerAllocations({ runStatusResponse });
  const enRoute = localizedTransportPage.renderAiRouteItineraries({ runStatusResponse, fallbackCurrencyCode: 'USD' });
  const enAudit = localizedTransportPage.renderAiChangesAudit({ runStatusResponse });

  localizedTransportPage.setActiveTransportLanguageCode('pt');
  const ptPassenger = localizedTransportPage.renderAiPassengerAllocations({ runStatusResponse });
  const ptRoute = localizedTransportPage.renderAiRouteItineraries({ runStatusResponse, fallbackCurrencyCode: 'USD' });
  const ptAudit = localizedTransportPage.renderAiChangesAudit({ runStatusResponse });

  assert.equal(enPassenger.allocatedTitle, 'Allocated Passengers');
  assert.equal(ptPassenger.allocatedTitle, 'Passageiros Alocados');
  assert.equal(ptPassenger.unallocatedItems[0].badges[0].text, 'Não Roteado');
  assert.equal(enRoute.items[0].fieldRows[0].label, 'Project');
  assert.equal(ptRoute.items[0].fieldRows[0].label, 'Projeto');
  assert.deepEqual(
    ptRoute.items[0].fieldRows.map((fieldRow) => fieldRow.label),
    ['Projeto', 'ETA', 'Duração', 'Custo']
  );
  assert.equal(enAudit.summaryItems[0].label, 'Prompt Version');
  assert.equal(ptAudit.summaryItems[0].label, 'Versão do Prompt');
  assert.equal(ptAudit.summaryItems[3].note, 'Tolerância extra 30 min');
  assert.equal(ptAudit.clusterItems[0].badges[0].text, 'Âncora 07:20h');
});

test('transport ai review and vehicle details use i18n mappings instead of inline admin literals in touched renderers', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );
  const passengerBlock = transportScript
    .split('function buildAiPassengerAllocationsViewModel(runStatusResponse) {')[1]
    .split('function renderAiPassengerAllocations(options) {')[0];
  const routeBlock = transportScript
    .split('function buildAiRouteItinerariesViewModel(runStatusResponse, fallbackCurrencyCode) {')[1]
    .split('function renderAiRouteItineraries(options) {')[0];
  const auditBlock = transportScript
    .split('function buildAiChangesAuditViewModel(runStatusResponse) {')[1]
    .split('function renderAiChangesAudit(options) {')[0];
  const vehicleDetailsBlock = transportScript
    .split('function createVehicleDetailsTableHead(columns) {')[1]
    .split('function createVehicleDetailsTableRow(columns, rowViewModel) {')[0];

  assert.match(passengerBlock, /getTransportAiDynamicLabel\("passengerFields", "project"\)/);
  assert.match(passengerBlock, /translateTransportAiDefinition\(TRANSPORT_AI_DYNAMIC_TEXT\.passengerAllocationsEmpty\)/);
  assert.doesNotMatch(passengerBlock, /label:\s*"Project"/);
  assert.doesNotMatch(passengerBlock, /emptyMessage:\s*"Passenger allocations will appear in this panel once the review data is rendered\."/);
  assert.match(routeBlock, /getTransportAiDynamicLabel\("routeFields", "project"\)/);
  assert.match(routeBlock, /translateTransportAiDefinition\(TRANSPORT_AI_DYNAMIC_TEXT\.routeItinerariesEmpty\)/);
  assert.doesNotMatch(routeBlock, /label:\s*"Duration"/);
  assert.match(auditBlock, /getTransportAiDynamicLabel\("auditFields", "promptVersion"\)/);
  assert.match(auditBlock, /translateTransportAiDefinition\(TRANSPORT_AI_DYNAMIC_TEXT\.extraTolerance/);
  assert.doesNotMatch(auditBlock, /label:\s*"Prompt Version"/);
  assert.match(vehicleDetailsBlock, /t\(column\.headerKey\)/);
  assert.doesNotMatch(vehicleDetailsBlock, /Passenger|Boarding|Departure/);
});

test('transport ai review workspace markup and styles build the consolidated per-vehicle primary surface', () => {
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
  assert.match(transportHtml, /data-ai-review-workspace/);
  assert.match(transportHtml, /data-ai-review-vehicle-table-list/);
  assert.match(transportHtml, /data-ai-review-exceptions-placeholder/);
  assert.match(transportHtml, /data-ai-review-management-placeholder/);
  assert.match(transportScript, /function createTransportAiReviewTableElement\(reviewItem, columnLabels\) \{/);
  assert.match(transportScript, /function createTransportAiReviewExceptionsElement\(exceptionsViewModel\) \{/);
  assert.match(transportScript, /function createTransportAiManagementTableElement\(managementViewModel\) \{/);
  assert.match(transportScript, /function renderAiChangesSummary\(options\) \{/);
  assert.match(
    transportScript,
    /renderAiChangesSummary\(\{[\s\S]*summaryGridElement: aiChangesSummaryGrid,[\s\S]*summaryPanelElement: aiChangesSummaryPanel/
  );
  assert.match(transportScript, /summaryGridElement\.hidden\s*=\s*true/);
  assert.match(transportCss, /\.transport-ai-changes-objective-summary,[\s\S]*overflow-wrap:\s*anywhere/);
  assert.match(transportCss, /\.transport-ai-review-vehicle-panel\s*\{[\s\S]*padding:\s*14px/);
  assert.match(transportCss, /\.transport-ai-review-table\s*\{[\s\S]*min-width:\s*640px/);
  assert.match(transportCss, /\.transport-ai-review-exceptions-panel\s*\{[\s\S]*display:\s*grid/);
  assert.match(transportCss, /\.transport-ai-review-management-panel\s*\{[\s\S]*display:\s*grid/);
  assert.match(transportCss, /\.transport-ai-review-management-table\s*\{[\s\S]*min-width:\s*720px/);
  assert.match(transportCss, /\.transport-ai-review-management-placeholder\s*\{[\s\S]*border:\s*1px dashed/);
  assert.match(transportCss, /@media \(max-width: 860px\) \{[\s\S]*\.transport-ai-review-vehicle-meta-grid\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/);
  assert.match(transportCss, /@media \(max-width: 640px\) \{[\s\S]*\.transport-ai-review-vehicle-meta-grid\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
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

test('transport ai passenger and route panels keep dedicated render hooks as supporting detail surfaces', () => {
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

  assert.match(transportHtml, /data-ai-changes-tab="passengers"[^>]*data-ai-changes-tab-role="supporting-detail"/);
  assert.match(transportHtml, /data-ai-changes-tab="routes"[^>]*data-ai-changes-tab-role="supporting-detail"/);
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

test('transport ai audit panel keeps a dedicated render hook and cluster card styles', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportScript, /const aiChangesAuditPanel = document\.querySelector\("\[data-ai-changes-audit\]"\);/);
  assert.match(transportScript, /function renderAiChangesAudit\(options\) \{/);
  assert.match(transportScript, /function syncAiChangesAuditRender\(\) \{[\s\S]*auditPanelElement: aiChangesAuditPanel,/);
  assert.match(transportCss, /\.transport-ai-changes-audit-cluster-list\s*\{[\s\S]*display:\s*grid/);
  assert.match(transportCss, /\.transport-ai-changes-audit-cluster\s*\{[\s\S]*border-radius:\s*12px/);
  assert.match(transportCss, /\.transport-ai-agent-request-kinds-grid\s*\{[\s\S]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\)/);
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
    assert.equal(getElement('[data-ai-agent-request-kind="extra"]').checked, true);
    assert.equal(getElement('[data-ai-agent-request-kind="weekend"]').checked, true);
    assert.equal(getElement('[data-ai-agent-request-kind="regular"]').checked, true);
    assert.equal(getElement('[data-ai-agent-submit]').textContent, 'Request Routes');

    getElement('[data-ai-agent-request-kind="extra"]').checked = false;
    getElement('[data-ai-agent-cancel]').click();
    assert.equal(getElement('[data-ai-agent-modal]').hidden, true);

    calculateRoutesButton.click();
    assert.equal(getElement('[data-ai-agent-modal]').hidden, false);
    assert.equal(getElement('[data-ai-agent-request-kind="extra"]').checked, true);
    assert.equal(getElement('[data-ai-agent-request-kind="weekend"]').checked, true);
    assert.equal(getElement('[data-ai-agent-request-kind="regular"]').checked, true);
  });
});

test('transport ai route submit sends the selected request kinds in dashboard_scope', async () => {
  await withTransportPageHarness(
    {
      routeCalculationStartResponse: {
        ok: true,
        run_key: 'transport-ai-run:start-001',
        status: 'requested',
        message: 'Transport AI request accepted.',
      },
      routeCalculationStatusResponse: Object.assign({}, getSampleLatestSuggestionResponse(), {
        ok: true,
        suggestion_ready: true,
      }),
    },
    async ({ getElement, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="calculate-routes"]').click();

      const weekendCheckbox = getElement('[data-ai-agent-request-kind="weekend"]');
      const regularCheckbox = getElement('[data-ai-agent-request-kind="regular"]');
      weekendCheckbox.checked = false;
      weekendCheckbox.dispatchEvent(createFakeEvent('change', { target: weekendCheckbox }));
      regularCheckbox.checked = false;
      regularCheckbox.dispatchEvent(createFakeEvent('change', { target: regularCheckbox }));

      getElement('[data-ai-agent-submit]').click();
      await flushAsyncWork(3);

      const startCall = fetchCalls.find(
        (call) => call.method === 'POST' && call.url.includes('/ai/route-calculations')
      );
      assert.ok(startCall);

      const requestPayload = JSON.parse(startCall.body);
      assert.deepEqual(requestPayload.dashboard_scope, {
        project_ids: [101, 202],
        request_kinds: ['extra'],
      });
      assert.equal(getElement('[data-ai-changes-modal]').hidden, false);
    }
  );
});

test('transport ai route polling keeps fatal responses out of the review modal even with stale suggestion data', async () => {
  await withTransportPageHarness(
    {
      routeCalculationStartResponse: {
        ok: true,
        run_key: 'transport-ai-run:fatal-001',
        status: 'requested',
        message: 'Transport AI request accepted.',
      },
      routeCalculationStatusResponse: Object.assign({}, getSampleLatestSuggestionResponse(), {
        ok: false,
        status: 'failed',
        message: 'Transport AI planning validation failed after resetting eligible requests. Baseline restored.',
        error_code: 'transport_ai_planning_input_invalid',
        failure_category: 'capacity',
        review_state: 'fatal_error',
        suggestion_ready: true,
        can_save: false,
        can_apply: false,
        can_cancel_restore: false,
      }),
    },
    async ({ getElement, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="calculate-routes"]').click();
      getElement('[data-ai-agent-submit]').click();
      await flushAsyncWork(3);

      assert.equal(getElement('[data-ai-changes-modal]').hidden, true);
      const feedbackText = getElement('[data-ai-agent-feedback]').textContent;
      assert.match(feedbackText, /route plan could not be completed for all passengers/i);
      assert.match(feedbackText, /baseline was restored successfully/i);
    }
  );
});

test('transport ai route polling opens review modal for suggestion with exceptions and does not show fatal error state', async () => {
  await withTransportPageHarness(
    {
      routeCalculationStartResponse: {
        ok: true,
        run_key: 'transport-ai-run:exceptions-001',
        status: 'requested',
        message: 'Transport AI request accepted.',
      },
      routeCalculationStatusResponse: Object.assign({}, getSampleLatestSuggestionResponse(), {
        ok: true,
        status: 'proposed',
        review_state: 'review_with_exceptions',
        suggestion_ready: true,
        can_save: true,
        can_apply: true,
        message: 'Transport AI suggestion is ready for review.',
      }),
    },
    async ({ getElement, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="calculate-routes"]').click();
      getElement('[data-ai-agent-submit]').click();
      await flushAsyncWork(3);

      assert.equal(getElement('[data-ai-changes-modal]').hidden, false);
      assert.equal(getElement('[data-ai-agent-modal]').hidden, true);
    }
  );
});

test('transport ai route submit blocks empty request kind selection before fetching', async () => {
  await withTransportPageHarness({}, async ({ getElement, fetchCalls, flushAsyncWork }) => {
    getElement('[data-ai-menu-action="calculate-routes"]').click();

    ['extra', 'weekend', 'regular'].forEach((requestKind) => {
      const checkbox = getElement(`[data-ai-agent-request-kind="${requestKind}"]`);
      checkbox.checked = false;
      checkbox.dispatchEvent(createFakeEvent('change', { target: checkbox }));
    });

    getElement('[data-ai-agent-submit]').click();
    await flushAsyncWork();

    assert.equal(
      fetchCalls.filter((call) => call.url.includes('/ai/route-calculations')).length,
      0
    );
    assert.equal(getElement('[data-ai-agent-modal]').hidden, false);
    assert.match(getElement('[data-ai-agent-feedback]').textContent, /Select at least one user list/i);
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
    const projectField = getElement('[data-ai-settings-project]');
    const providerField = getElement('[data-ai-settings-provider]');
    const apiKeyField = getElement('[data-ai-settings-api-key]');

    const settingsGetCall = fetchCalls.find(
      (call) => call.method === 'GET' && call.url.includes('/ai/settings?project_id=101')
    );
    assert.ok(settingsGetCall);
    assert.equal(getElement('[data-ai-settings-modal]').hidden, false);
    assert.equal(projectField.tagName, 'SELECT');
    assert.equal(projectField.value, '101');
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

test('transport ai settings modal shows bootstrap dashboard projects while the authoritative catalog is still loading', async () => {
  const deferredProjectList = createDeferred();

  await withTransportPageHarness(
    {
      dashboardResponse: {
        selected_route: 'home_to_work',
        selected_date: '2026-06-13',
        projects: [
          createTransportProjectRow(101, 'Project Atlas'),
          createTransportProjectRow(202, 'Project Borealis'),
        ],
        regular_requests: [],
        weekend_requests: [],
        extra_requests: [],
        regular_vehicles: [],
        weekend_vehicles: [],
        extra_vehicles: [],
        regular_vehicle_registry: [],
        weekend_vehicle_registry: [],
        extra_vehicle_registry: [],
        workplaces: [],
      },
      projectListHandler() {
        return deferredProjectList.promise;
      },
      aiSettingsGetHandler(request) {
        const requestUrl = new URL(request.url, 'https://example.test');
        const projectId = Number(requestUrl.searchParams.get('project_id'));
        return createFetchResponse(
          {
            project_id: projectId,
            project_name: 'Project Atlas',
            provider: 'openai',
            resolved_model: 'gpt-5.4-2026-03-05',
            reasoning_effort: 'high',
            has_api_key: true,
            api_key_hint: '***1010',
          },
          200,
        );
      },
    },
    async ({ getElement, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      const projectField = getElement('[data-ai-settings-project]');
      assert.equal(projectField.value, '101');
      assert.deepEqual(
        projectField.children.map((element) => element.value),
        ['', '101', '202'],
      );
      assert.equal(getElement('[data-ai-settings-provider]').disabled, true);
      assert.equal(getElement('[data-ai-settings-save]').disabled, true);
      assert.equal(
        fetchCalls.filter((call) => call.method === 'GET' && call.url.includes('/projects')).length,
        1,
      );
      assert.equal(
        fetchCalls.filter((call) => call.method === 'GET' && call.url.includes('/ai/settings?project_id=')).length,
        0,
      );

      deferredProjectList.resolve(
        createFetchResponse(
          [
            createTransportProjectRow(101, 'Project Atlas'),
            createTransportProjectRow(303, 'Project Ceres'),
          ],
          200,
        )
      );
      await flushAsyncWork();

      assert.deepEqual(
        projectField.children.map((element) => element.value),
        ['', '101', '303'],
      );
      assert.equal(projectField.value, '101');
      assert.ok(fetchCalls.some((call) => call.method === 'GET' && call.url.includes('/ai/settings?project_id=101')));
      assert.equal(getElement('[data-ai-settings-provider]').disabled, false);
      assert.equal(getElement('[data-ai-settings-save]').disabled, false);
    },
  );
});

test('transport ai settings modal refreshes the project catalog authoritatively and preserves the selected project when it still exists', async () => {
  await withTransportPageHarness(
    {
      dashboardResponse: {
        selected_route: 'home_to_work',
        selected_date: '2026-06-13',
        projects: [
          createTransportProjectRow(101, 'Project Atlas'),
          createTransportProjectRow(202, 'Project Borealis'),
        ],
        regular_requests: [],
        weekend_requests: [],
        extra_requests: [],
        regular_vehicles: [],
        weekend_vehicles: [],
        extra_vehicles: [],
        regular_vehicle_registry: [],
        weekend_vehicle_registry: [],
        extra_vehicle_registry: [],
        workplaces: [],
      },
      projectListResponse: [
        createTransportProjectRow(101, 'Project Atlas'),
        createTransportProjectRow(303, 'Project Ceres'),
      ],
      aiSettingsGetHandler(request) {
        const requestUrl = new URL(request.url, 'https://example.test');
        const projectId = Number(requestUrl.searchParams.get('project_id'));
        return createFetchResponse(
          {
            project_id: projectId,
            project_name: projectId === 303 ? 'Project Ceres' : 'Project Atlas',
            provider: 'openai',
            resolved_model: 'gpt-5.4-2026-03-05',
            reasoning_effort: 'high',
            has_api_key: true,
            api_key_hint: projectId === 303 ? '***3030' : '***1010',
          },
          200,
        );
      },
    },
    async ({ getElement, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      const projectCalls = fetchCalls.filter((call) => call.method === 'GET' && call.url.includes('/projects'));
      assert.equal(projectCalls.length, 1);

      const projectField = getElement('[data-ai-settings-project]');
      assert.equal(projectField.value, '101');
      assert.deepEqual(
        projectField.children.map((element) => element.value),
        ['', '101', '303'],
      );

      const settingsGetCall = fetchCalls.find(
        (call) => call.method === 'GET' && call.url.includes('/ai/settings?project_id=101'),
      );
      assert.ok(settingsGetCall);
      assert.match(getElement('[data-ai-settings-api-key-hint]').textContent, /\*\*\*1010/);
    },
  );
});

test('transport ai settings modal recovers when dashboard projects are empty but the projects endpoint returns valid items', async () => {
  await withTransportPageHarness(
    {
      dashboardResponse: {
        selected_route: 'home_to_work',
        selected_date: '2026-06-13',
        projects: [],
        regular_requests: [],
        weekend_requests: [],
        extra_requests: [],
        regular_vehicles: [],
        weekend_vehicles: [],
        extra_vehicles: [],
        regular_vehicle_registry: [],
        weekend_vehicle_registry: [],
        extra_vehicle_registry: [],
        workplaces: [],
      },
      projectListResponse: [
        createTransportProjectRow(101, 'Project Atlas'),
        createTransportProjectRow(202, 'Project Borealis'),
      ],
      aiSettingsGetHandler(request) {
        const requestUrl = new URL(request.url, 'https://example.test');
        const projectId = Number(requestUrl.searchParams.get('project_id'));
        return createFetchResponse(
          {
            project_id: projectId,
            project_name: projectId === 202 ? 'Project Borealis' : 'Project Atlas',
            provider: projectId === 202 ? 'deepseek' : 'openai',
            resolved_model: projectId === 202 ? 'deepseek-v4-pro' : 'gpt-5.4-2026-03-05',
            reasoning_effort: 'high',
            has_api_key: true,
            api_key_hint: projectId === 202 ? '***2020' : '***1010',
          },
          200,
        );
      },
    },
    async ({ getElement, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      const projectField = getElement('[data-ai-settings-project]');
      assert.deepEqual(
        projectField.children.map((element) => element.value),
        ['', '101', '202'],
      );
      assert.equal(projectField.value, '101');
      assert.ok(fetchCalls.some((call) => call.method === 'GET' && call.url.includes('/projects')));
      assert.ok(fetchCalls.some((call) => call.method === 'GET' && call.url.includes('/ai/settings?project_id=101')));
      assert.equal(getElement('[data-ai-settings-provider]').value, 'openai');
      assert.match(getElement('[data-ai-settings-api-key-hint]').textContent, /\*\*\*1010/);
      assert.equal(getElement('[data-ai-settings-feedback]').hidden, true);
      assert.equal(getElement('[data-ai-settings-save]').disabled, false);
    },
  );
});

test('transport ai settings save flow updates the provider note, posts the trimmed payload, and closes on success', async () => {
  await withTransportPageHarness(
    {
      aiSettingsPutResponse: {
        project_id: 101,
        project_name: 'Project Atlas',
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
        project_id: 101,
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
      assert.notEqual(
        getElement('[data-ai-settings-feedback]').textContent,
        'Transport AI could not load the available projects.'
      );
    }
  );
});

test('transport ai settings save stays blocked when no valid project is selected', async () => {
  await withTransportPageHarness({}, async ({ getElement, fetchCalls, flushAsyncWork }) => {
    getElement('[data-ai-menu-action="settings"]').click();
    await flushAsyncWork();

    const projectField = getElement('[data-ai-settings-project]');
    projectField.value = '';
    projectField.dispatchEvent(createFakeEvent('change', { target: projectField }));
    await flushAsyncWork();

    const saveButton = getElement('[data-ai-settings-save]');
    assert.equal(saveButton.disabled, true);

    saveButton.click();
    await flushAsyncWork();

    assert.equal(
      fetchCalls.filter((call) => call.method === 'PUT' && call.url.includes('/ai/settings')).length,
      0,
    );
    assert.equal(
      getElement('[data-ai-settings-feedback]').textContent,
      'Select a valid project before saving.',
    );
  });
});

test('transport ai settings save surfaces the missing project_id validation without generic field required text', async () => {
  await withTransportPageHarness(
    {
      aiSettingsPutError: {
        status: 422,
        payload: {
          detail: [
            {
              type: 'missing',
              loc: ['body', 'project_id'],
              msg: 'Field required',
            },
          ],
        },
      },
    },
    async ({ getElement, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      getElement('[data-ai-settings-save]').click();
      await flushAsyncWork();

      assert.equal(getElement('[data-ai-settings-modal]').hidden, false);
      assert.equal(
        getElement('[data-ai-settings-feedback]').textContent,
        'Select a valid project before saving.',
      );
    }
  );
});

test('transport ai settings save differentiates a removed project from provider validation failures', async () => {
  await withTransportPageHarness(
    {
      aiSettingsPutError: {
        status: 404,
        payload: {
          detail: 'Transport AI project does not exist.',
        },
      },
    },
    async ({ getElement, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      getElement('[data-ai-settings-save]').click();
      await flushAsyncWork();

      assert.equal(getElement('[data-ai-settings-modal]').hidden, false);
      assert.equal(
        getElement('[data-ai-settings-feedback]').textContent,
        'The selected project was removed before the AI settings could be saved. Reload the project catalog and choose another project.',
      );
      assert.equal(getElement('[data-ai-settings-save]').disabled, true);
      assert.notEqual(
        getElement('[data-ai-settings-feedback]').textContent,
        'Changing provider requires a new API key.'
      );
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

test('transport ai settings load surfaces the encryption-unavailable error before save', async () => {
  await withTransportPageHarness(
    {
      aiSettingsGetError: {
        status: 503,
        payload: {
          detail: 'Transport AI settings encryption is unavailable.',
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
        'Transport AI settings encryption is unavailable.'
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
            project_id: 101,
            project_name: 'Project Atlas',
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

test('transport ai settings modal switches projects, reloads isolated hints, and sends the selected project_id on save', async () => {
  await withTransportPageHarness(
    {
      aiSettingsGetHandler(request) {
        const requestUrl = new URL(request.url, 'https://example.test');
        const projectId = Number(requestUrl.searchParams.get('project_id'));
        if (projectId === 202) {
          return createFetchResponse(
            {
              project_id: 202,
              project_name: 'Project Borealis',
              provider: 'deepseek',
              resolved_model: 'deepseek-v4-pro',
              reasoning_effort: 'high',
              has_api_key: true,
              api_key_hint: '***2020',
            },
            200
          );
        }

        return createFetchResponse(
          {
            project_id: 101,
            project_name: 'Project Atlas',
            provider: 'openai',
            resolved_model: 'gpt-5.4-2026-03-05',
            reasoning_effort: 'high',
            has_api_key: true,
            api_key_hint: '***1010',
          },
          200
        );
      },
      aiSettingsPutResponse: {
        project_id: 202,
        project_name: 'Project Borealis',
        provider: 'deepseek',
        resolved_model: 'deepseek-v4-pro',
        reasoning_effort: 'high',
        has_api_key: true,
        api_key_hint: '***8888',
      },
    },
    async ({ getElement, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      const projectField = getElement('[data-ai-settings-project]');
      assert.equal(projectField.value, '101');
      assert.match(getElement('[data-ai-settings-api-key-hint]').textContent, /\*\*\*1010/);

      projectField.value = '202';
      projectField.dispatchEvent(createFakeEvent('change', { target: projectField }));
      await flushAsyncWork();

      assert.equal(getElement('[data-ai-settings-provider]').value, 'deepseek');
      assert.match(getElement('[data-ai-settings-provider-note]').textContent, /deepseek-v4-pro/i);
      assert.match(getElement('[data-ai-settings-api-key-hint]').textContent, /\*\*\*2020/);

      const apiKeyField = getElement('[data-ai-settings-api-key]');
      apiKeyField.value = '  sk-project-202  ';
      apiKeyField.dispatchEvent(createFakeEvent('input', { target: apiKeyField }));

      getElement('[data-ai-settings-save]').click();
      await flushAsyncWork();

      const projectGetCalls = fetchCalls.filter(
        (call) => call.method === 'GET' && call.url.includes('/ai/settings?project_id=')
      );
      assert.equal(projectGetCalls.length, 2);
      assert.ok(projectGetCalls.some((call) => call.url.includes('project_id=101')));
      assert.ok(projectGetCalls.some((call) => call.url.includes('project_id=202')));

      const saveCall = fetchCalls.find((call) => call.method === 'PUT' && call.url.includes('/ai/settings'));
      assert.ok(saveCall);
      assert.deepEqual(JSON.parse(saveCall.body), {
        project_id: 202,
        provider: 'deepseek',
        api_key: 'sk-project-202',
      });
    }
  );
});

test('transport ai settings modal isolates provider, api key hint, and unsaved draft when switching projects', async () => {
  await withTransportPageHarness(
    {
      aiSettingsGetHandler(request) {
        const requestUrl = new URL(request.url, 'https://example.test');
        const projectId = Number(requestUrl.searchParams.get('project_id'));
        if (projectId === 202) {
          return createFetchResponse(
            {
              project_id: 202,
              project_name: 'Project Borealis',
              provider: 'deepseek',
              resolved_model: 'deepseek-v4-pro',
              reasoning_effort: 'high',
              has_api_key: true,
              api_key_hint: '***2020',
            },
            200,
          );
        }

        return createFetchResponse(
          {
            project_id: 101,
            project_name: 'Project Atlas',
            provider: 'openai',
            resolved_model: 'gpt-5.4-2026-03-05',
            reasoning_effort: 'high',
            has_api_key: true,
            api_key_hint: '***1010',
          },
          200,
        );
      },
    },
    async ({ getElement, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      const projectField = getElement('[data-ai-settings-project]');
      const providerField = getElement('[data-ai-settings-provider]');
      const apiKeyField = getElement('[data-ai-settings-api-key]');

      assert.equal(projectField.value, '101');
      assert.equal(providerField.value, 'openai');
      assert.match(getElement('[data-ai-settings-api-key-hint]').textContent, /\*\*\*1010/);

      apiKeyField.value = 'sk-atlas-draft';
      apiKeyField.dispatchEvent(createFakeEvent('input', { target: apiKeyField }));

      projectField.value = '202';
      projectField.dispatchEvent(createFakeEvent('change', { target: projectField }));
      await flushAsyncWork();

      assert.equal(projectField.value, '202');
      assert.equal(providerField.value, 'deepseek');
      assert.match(getElement('[data-ai-settings-provider-note]').textContent, /deepseek-v4-pro/i);
      assert.match(getElement('[data-ai-settings-api-key-hint]').textContent, /\*\*\*2020/);
      assert.equal(apiKeyField.value, '');

      apiKeyField.value = 'sk-borealis-draft';
      apiKeyField.dispatchEvent(createFakeEvent('input', { target: apiKeyField }));

      projectField.value = '101';
      projectField.dispatchEvent(createFakeEvent('change', { target: projectField }));
      await flushAsyncWork();

      assert.equal(projectField.value, '101');
      assert.equal(providerField.value, 'openai');
      assert.match(getElement('[data-ai-settings-provider-note]').textContent, /gpt-5\.4-2026-03-05/i);
      assert.match(getElement('[data-ai-settings-api-key-hint]').textContent, /\*\*\*1010/);
      assert.equal(apiKeyField.value, '');
    },
  );
});

test('transport ai settings modal keeps the selected project and shows controlled feedback when a project switch load fails', async () => {
  await withTransportPageHarness(
    {
      aiSettingsGetHandler(request) {
        const requestUrl = new URL(request.url, 'https://example.test');
        const projectId = Number(requestUrl.searchParams.get('project_id'));
        if (projectId === 202) {
          return createFetchResponse({}, 500);
        }

        return createFetchResponse(
          {
            project_id: 101,
            project_name: 'Project Atlas',
            provider: 'openai',
            resolved_model: 'gpt-5.4-2026-03-05',
            reasoning_effort: 'high',
            has_api_key: true,
            api_key_hint: '***1010',
          },
          200
        );
      },
    },
    async ({ getElement, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      const projectField = getElement('[data-ai-settings-project]');
      assert.equal(projectField.value, '101');
      assert.match(getElement('[data-ai-settings-api-key-hint]').textContent, /\*\*\*1010/);

      projectField.value = '202';
      projectField.dispatchEvent(createFakeEvent('change', { target: projectField }));
      await flushAsyncWork();

      assert.equal(getElement('[data-ai-settings-modal]').hidden, false);
      assert.equal(projectField.value, '202');
      assert.equal(getElement('[data-ai-settings-provider]').value, 'openai');
      assert.equal(getElement('[data-ai-settings-feedback]').hidden, false);
      assert.match(
        getElement('[data-ai-settings-feedback]').textContent,
        /Transport AI could not load the current AI settings\./i
      );
      assert.doesNotMatch(getElement('[data-ai-settings-api-key-hint]').textContent, /\*\*\*1010/);
      assert.doesNotMatch(getElement('[data-ai-settings-api-key-hint]').textContent, /\*\*\*2020/);

      const projectGetCalls = fetchCalls.filter(
        (call) => call.method === 'GET' && call.url.includes('/ai/settings?project_id=')
      );
      assert.equal(projectGetCalls.length, 2);
      assert.ok(projectGetCalls.some((call) => call.url.includes('project_id=101')));
      assert.ok(projectGetCalls.some((call) => call.url.includes('project_id=202')));
    }
  );
});

test('transport ai settings modal keeps bootstrap projects visible but blocks save when the authoritative project catalog fails', async () => {
  await withTransportPageHarness(
    {
      projectListError: {
        status: 500,
        payload: {},
      },
    },
    async ({ getElement, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      const projectCalls = fetchCalls.filter((call) => call.method === 'GET' && call.url.includes('/projects'));
      const settingsGetCalls = fetchCalls.filter(
        (call) => call.method === 'GET' && call.url.includes('/ai/settings?project_id='),
      );
      assert.equal(projectCalls.length, 1);
      assert.equal(settingsGetCalls.length, 0);

      const projectField = getElement('[data-ai-settings-project]');
      assert.equal(projectField.disabled, false);
      assert.equal(projectField.value, '101');
      assert.deepEqual(
        projectField.children.map((element) => element.value),
        ['', '101', '202'],
      );
      assert.equal(getElement('[data-ai-settings-provider]').disabled, true);
      assert.equal(getElement('[data-ai-settings-api-key]').disabled, true);
      assert.equal(getElement('[data-ai-settings-save]').disabled, true);
      assert.equal(
        getElement('[data-ai-settings-feedback]').textContent,
        'Transport AI could not load the available projects.',
      );
    },
  );
});

test('transport ai settings modal falls back to the projects endpoint and shows a controlled warning when no projects exist', async () => {
  await withTransportPageHarness(
    {
      dashboardResponse: {
        selected_route: 'home_to_work',
        selected_date: '2026-06-13',
        projects: [],
        regular_requests: [],
        weekend_requests: [],
        extra_requests: [],
        regular_vehicles: [],
        weekend_vehicles: [],
        extra_vehicles: [],
        regular_vehicle_registry: [],
        weekend_vehicle_registry: [],
        extra_vehicle_registry: [],
        workplaces: [],
      },
      projectListResponse: [],
    },
    async ({ getElement, fetchCalls, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="settings"]').click();
      await flushAsyncWork();

      assert.ok(fetchCalls.some((call) => call.method === 'GET' && call.url.includes('/projects')));
      assert.equal(getElement('[data-ai-settings-project]').value, '');
      assert.equal(getElement('[data-ai-settings-provider]').disabled, true);
      assert.equal(getElement('[data-ai-settings-save]').disabled, true);
      assert.equal(
        getElement('[data-ai-settings-feedback]').textContent,
        'No projects are available yet. Create a project before configuring AI settings.'
      );
    }
  );
});

test('transport ai settings fetch mock handles /ai/settings before the generic /settings route', async () => {
  const aiSettingsPayload = {
    project_id: 101,
    project_name: 'Project Atlas',
    provider: 'openai',
    resolved_model: 'gpt-5.4-2026-03-05',
    reasoning_effort: 'high',
    has_api_key: true,
    api_key_hint: '***1234',
  };
  const settingsPayload = {
    work_to_home_time: '17:15',
    last_update_time: '16:30',
  };

  const { fetch } = createFetchMock({
    aiSettingsResponse: aiSettingsPayload,
    settingsResponse: settingsPayload,
  });

  const aiSettingsResponse = await fetch('../api/transport/ai/settings?project_id=101');
  const settingsResponse = await fetch('../api/transport/settings');

  assert.deepEqual(JSON.parse(await aiSettingsResponse.text()), aiSettingsPayload);
  assert.deepEqual(JSON.parse(await settingsResponse.text()), settingsPayload);
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
      assert.equal(getElement('[data-ai-changes-summary-grid]').children.length, 0);
      assert.equal(getElement('[data-ai-changes-summary-grid]').hidden, true);
      assert.equal(global.document.querySelectorAll('[data-ai-review-vehicle-table]').length, 1);
      assert.equal(global.document.querySelectorAll('[data-ai-review-management-table]').length, 1);
      assert.match(getElement('[data-ai-changes-summary-panel]').textContent, /Management Table/i);
      assert.match(getElement('[data-ai-review-management-metric="total_cost"]').textContent, /120\.00/);
      assert.match(getElement('[data-ai-review-management-metric="total_cost"]').textContent, /100\.00/);
      assert.match(getElement('[data-ai-review-management-metric="total_cost"]').textContent, /20\.00/);
      assert.match(getElement('[data-ai-review-management-metric="vehicles"]').textContent, /2/);
      assert.match(getElement('[data-ai-review-management-metric="vehicles"]').textContent, /1/);
      assert.match(getElement('[data-ai-review-management-metric="issues"]').textContent, /No blocking issues/);
      assert.match(getElement('[data-ai-changes-summary-panel]').textContent, /Cut costs while keeping one route stable/i);
      assert.match(getElement('[data-ai-changes-summary-panel]').textContent, /SGX1234/);
      assert.match(getElement('[data-ai-changes-summary-panel]').textContent, /Alice Tan/);
      assert.match(getElement('[data-ai-changes-summary-panel]').textContent, /Not planned for this route/);
      assert.match(getElement('[data-ai-changes-vehicles]').textContent, /SGX1234/);
      assert.match(getElement('[data-ai-changes-passengers]').textContent, /Alice Tan/);
      assert.match(getElement('[data-ai-changes-routes]').textContent, /Industrial Road/);
      assert.match(getElement('[data-ai-changes-audit]').textContent, /30 min/);
      assert.match(getElement('[data-ai-changes-audit]').textContent, /cluster:extra:morning:1/);
    }
  );
});

test('transport ai review keeps not routed requests visible in a compact exceptions section', async () => {
  const latestSuggestionResponse = getSampleLatestSuggestionResponse();
  latestSuggestionResponse.suggestion.plan.validation_issues = [
    {
      code: 'transport_ai_request_unallocated',
      message: 'Passenger still needs manual review.',
      blocking: true,
      request_id: 999,
    },
  ];

  await withTransportPageHarness(
    {
      latestSuggestionResponse,
    },
    async ({ getElement, flushAsyncWork }) => {
      getElement('[data-ai-menu-action="implement-modifications"]').click();
      await flushAsyncWork();

      const vehicleTableElement = getElement('[data-ai-review-vehicle-table]');
      const exceptionsSectionElement = getElement('[data-ai-review-exceptions-section]');
      const reviewPanelText = getElement('[data-ai-changes-summary-panel]').textContent;

      assert.equal(global.document.querySelectorAll('[data-ai-review-vehicle-table]').length, 1);
      assert.equal(global.document.querySelectorAll('[data-ai-review-exception-item]').length, 1);
      assert.match(exceptionsSectionElement.textContent, /Exceptions\s*\/\s*Not Routed/i);
      assert.match(exceptionsSectionElement.textContent, /Request #999/);
      assert.match(exceptionsSectionElement.textContent, /Passenger still needs manual review/i);
      assert.doesNotMatch(vehicleTableElement.textContent, /Request #999/);
      assert.ok(reviewPanelText.indexOf('Request #999') < reviewPanelText.indexOf('Management Table'));
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
      assert.ok(countFetchCalls('/dashboard?') >= dashboardRequestCount + 1);
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
      assert.ok(countFetchCalls('/dashboard?') >= dashboardRequestCount + 1);
      assert.equal(getElement('[data-ai-changes-modal]').hidden, true);
      assert.match(getElement('[data-status-message]').textContent, /cancelled/i);
    }
  );
});

test('transport multi-tab validation bounds stream retries and avoids transport ai requests without user action', async () => {
  const perTabMetrics = [];

  for (let tabIndex = 0; tabIndex < 3; tabIndex += 1) {
    const timers = createScheduledTimerHarness();
    const eventSourceHarness = createFakeEventSourceHarness(timers);

    await withTransportPageControlledHarness(
      {
        timerHarness: timers,
        eventSourceHarness,
      },
      async ({ countFetchCalls, fetchCalls, advanceTime }) => {
        assert.equal(countFetchCalls('/auth/session'), 1);
        assert.equal(countFetchCalls('/dashboard?'), 1);
        assert.equal(countFetchCalls('/auth/verify'), 0);
        assert.equal(eventSourceHarness.events.length, 1);

        await advanceTime(7500);

        assert.equal(countFetchCalls('/dashboard?'), 1);
        assert.equal(countFetchCalls('/auth/verify'), 0);
        assert.equal(fetchCalls.filter((call) => call.url.includes('/api/transport/ai/')).length, 0);
        assert.deepEqual(
          eventSourceHarness.events.map((event) => event.openedAt),
          [0, 1000, 3000, 7000]
        );

        perTabMetrics.push({
          streamAttempts: eventSourceHarness.events.length,
          dashboardRequests: countFetchCalls('/dashboard?'),
          authVerifyRequests: countFetchCalls('/auth/verify'),
          aiRequests: fetchCalls.filter((call) => call.url.includes('/api/transport/ai/')).length,
        });
      }
    );
  }

  assert.deepEqual(perTabMetrics, [
    { streamAttempts: 4, dashboardRequests: 1, authVerifyRequests: 0, aiRequests: 0 },
    { streamAttempts: 4, dashboardRequests: 1, authVerifyRequests: 0, aiRequests: 0 },
    { streamAttempts: 4, dashboardRequests: 1, authVerifyRequests: 0, aiRequests: 0 },
  ]);
});

test('transport auth validation only verifies on commit and keeps the session during partial edits', async () => {
  const timers = createScheduledTimerHarness();
  const eventSourceHarness = createFakeEventSourceHarness(timers);

  await withTransportPageControlledHarness(
    {
      timerHarness: timers,
      eventSourceHarness,
    },
    async ({ getElement, countFetchCalls, fetchCalls, advanceTime }) => {
      const authKeyInput = getElement('[data-transport-auth-key]');
      const authPasswordInput = getElement('[data-transport-auth-password]');
      const authKeyShell = getElement('[data-transport-auth-shell="key"]');
      const requestUserButton = getElement('[data-request-user-link]');

      assert.equal(countFetchCalls('/auth/verify'), 0);
      assert.equal(requestUserButton.hidden, true);
      assert.equal(authKeyShell.classList.contains('is-authenticated'), true);

      authKeyInput.value = 'hr70';
      authKeyInput.dispatchEvent(createFakeEvent('input', { target: authKeyInput }));
      authPasswordInput.value = 'n';
      authPasswordInput.dispatchEvent(createFakeEvent('input', { target: authPasswordInput }));
      await advanceTime(700);

      assert.equal(countFetchCalls('/auth/verify'), 0);
      assert.equal(fetchCalls.filter((call) => call.url.includes('/auth/logout')).length, 0);
      assert.equal(authKeyShell.classList.contains('is-authenticated'), true);

      authPasswordInput.value = 'new-secret';
      authPasswordInput.dispatchEvent(createFakeEvent('blur', { target: authPasswordInput }));
      await advanceTime(0);

      assert.equal(countFetchCalls('/auth/verify'), 1);
      assert.equal(countFetchCalls('/dashboard?'), 2);
      assert.equal(authKeyShell.classList.contains('is-authenticated'), true);

      authPasswordInput.value = '';
      authPasswordInput.dispatchEvent(createFakeEvent('input', { target: authPasswordInput }));
      await advanceTime(700);

      assert.equal(countFetchCalls('/auth/verify'), 1);
      assert.equal(fetchCalls.filter((call) => call.url.includes('/auth/logout')).length, 0);
      assert.equal(authKeyShell.classList.contains('is-authenticated'), true);
      assert.equal(requestUserButton.hidden, true);
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
    /\.transport-settings-preferences-grid\s*\{[\s\S]*grid-template-columns:\s*minmax\(0, 1fr\);/
  );
  assert.match(
    transportCss,
    /\.transport-settings-row--compact\s*\{[\s\S]*grid-template-columns:\s*max-content minmax\(118px, 1fr\);/
  );
  assert.match(
    transportCss,
    /\.transport-settings-section-preferences \.transport-settings-label\s*\{[\s\S]*white-space:\s*nowrap;/
  );
  assert.match(
    transportCss,
    /@media \(max-width: 960px\) \{[\s\S]*\.transport-settings-row,[\s\S]*\.transport-settings-dual-row,[\s\S]*\.transport-settings-inline-controls,[\s\S]*\.transport-settings-add-currency-fields,[\s\S]*\.transport-vehicle-details-actions[\s\S]*grid-template-columns:\s*1fr;/
  );
  assert.match(
    transportCss,
    /@media \(max-width: 960px\) \{[\s\S]*\.transport-settings-section-preferences \.transport-settings-label\s*\{[\s\S]*white-space:\s*normal;/
  );
});

test('transport frontend uses base-relative asset and API paths so the /checking prefix keeps working', () => {
  const transportIndex = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportIndex, /href="styles\.css\?v=\d{8}[a-z]"/);
  assert.match(transportIndex, /src="i18n\.js\?v=\d{8}[a-z]"/);
  assert.match(transportIndex, /src="app\.js\?v=\d{8}[a-z]"/);
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

test('independent vehicle panel heights replace the shared right-column row grid with right-column scroll behavior', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(
    transportCss,
    /\.tela01main_dir\s*\{[\s\S]*display:\s*flex;[\s\S]*flex-direction:\s*column;[\s\S]*overflow(?:-y)?:\s*auto;/
  );
  assert.doesNotMatch(
    transportCss,
    /\.tela01main_dir\s*\{[\s\S]*grid-template-rows:\s*minmax\(0,\s*[^;]+\)\s*var\(--transport-divider-size\)\s*minmax\(0,\s*[^;]+\)\s*var\(--transport-divider-size\)\s*minmax\(0,\s*[^;]+\);/
  );
});

test('independent vehicle panel heights require per-panel resize ownership hooks in the vehicle column markup', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportHtml, /data-panel-resize-handle="extra"/);
  assert.match(transportHtml, /data-panel-resize-handle="weekend"/);
  assert.match(transportHtml, /data-panel-resize-handle="regular"/);
  assert.match(transportHtml, /<button\s+type="button"\s+class="transport-panel-resize-handle"[\s\S]*data-panel-resize-handle="extra"[\s\S]*aria-controls="transportVehicleScopeExtra"[\s\S]*aria-hidden="true"[\s\S]*disabled[\s\S]*><\/button>/);
  assert.match(transportScript, /\[data-panel-resize-handle\]/);
  assert.match(transportScript, /function enableVehiclePanelResizeHandle\(handleElement\)/);
  assert.match(transportScript, /document\.querySelectorAll\("\[data-panel-resize-handle\]"\)\.forEach\(enableVehiclePanelResizeHandle\);/);
  assert.match(transportScript, /function enableVehiclePanelResizeHandle\(handleElement\) \{[\s\S]*updateVehicleGridLayouts\(panelElement\);/);
});

test('independent vehicle panel heights disable manual pane resizing below 1180px while keeping the one-column layout navigable', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(
    transportCss,
    /@media \(max-width: 1180px\) \{[\s\S]*\.tela01main\s*\{[\s\S]*grid-template-columns:\s*1fr;[\s\S]*\.tela01main > \.transport-divider-vertical,[\s\S]*\.transport-panel-resize-handle,[\s\S]*display:\s*none;[\s\S]*\.tela01main_dir\s*\{[\s\S]*overflow:\s*visible;[\s\S]*padding-right:\s*0;[\s\S]*border-top:\s*1px solid var\(--transport-border\);[\s\S]*\.tela01main_dir > \.transport-pane\s*\{[\s\S]*height:\s*auto !important;/
  );
});

test('transport vehicle panel resize handles use translated desktop labels and keyboard-safe runtime guards', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );

  assert.match(transportScript, /function isVehiclePanelResizeEnabledForViewport\(viewportWidth\)/);
  assert.match(transportScript, /function syncVehiclePanelResizeHandleState\(rootElement\)/);
  assert.match(transportScript, /t\("layout\.resizeVehiclePanel", \{ scope: mapScopeTitle\(scope\) \}\)/);
  assert.match(transportScript, /handleElement\.addEventListener\("keydown", function \(event\) \{/);
  assert.match(transportScript, /if \(!isVehiclePanelResizeEnabled\(\) \|\| handleElement\.disabled\) \{/);
  assert.match(transportScript, /syncVehiclePanelResizeHandleState\(carPanels \|\| document\);/);
  assert.match(transportI18n, /resizeVehiclePanel:/);
});

test('independent vehicle panel heights final cleanup removes stale shared vehicle-divider labels while preserving the top-level divider path', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );
  const transportI18n = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/i18n.js'),
    'utf8'
  );

  const horizontalResizeDividerCount = (transportHtml.match(/data-resize="horizontal"/g) || []).length;
  const verticalResizeDividerCount = (transportHtml.match(/data-resize="vertical"/g) || []).length;

  assert.equal(horizontalResizeDividerCount, 1);
  assert.equal(verticalResizeDividerCount, 1);
  assert.match(transportHtml, /data-resize="vertical"[\s\S]*role="separator"[\s\S]*aria-orientation="vertical"/);
  assert.match(transportHtml, /data-i18n-aria-label="layout\.resizeColumns"/);
  assert.match(transportScript, /document\.querySelectorAll\("\[data-resize\]"\)\.forEach\(enableResizableDivider\);/);
  assert.doesNotMatch(transportScript, /resizeExtraWeekend|resizeWeekendRegular/);
  assert.doesNotMatch(transportI18n, /resizeExtraWeekend:|resizeWeekendRegular:/);
});

test('independent vehicle panel heights require right-column scroll behavior without shared horizontal sibling resizing', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const horizontalResizeDividerCount = (transportHtml.match(/data-resize="horizontal"/g) || []).length;

  assert.equal(horizontalResizeDividerCount, 1);
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

test('transport vehicle details use allocation readiness instead of pending_fields length for the restricted edit path', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  assert.match(transportScript, /function openVehicleEditModal\(vehicle\) \{/);
  assert.match(
    transportScript,
    /requestJson\(`\$\{TRANSPORT_API_PREFIX\}\/vehicles\/\$\{encodeURIComponent\(String\(vehicleId\)\)\}`, \{[\s\S]*method:\s*"PUT"/
  );
  assert.match(transportScript, /if \(!isVehicleReadyForAllocation\(vehicle\)\) \{/);
  assert.doesNotMatch(transportScript, /Array\.isArray\(vehicle\.pending_fields\) && vehicle\.pending_fields\.length/);
  assert.match(transportScript, /openVehicleEditModal\(vehicle\);/);
});

test('transport vehicle details keep the normal detail path for allocation-ready vehicles with only administrative pending fields', async () => {
  const detailsPanel = await renderVehicleDetailsPanelForTest({
    id: 81,
    tipo: 'carro',
    lugares: 4,
    tolerance: 5,
    is_ready_for_allocation: true,
    pending_fields: ['placa', 'color'],
  });

  assert.equal(detailsPanel.childNodes[0].className, 'transport-vehicle-delete-button');
  assert.equal(detailsPanel.childNodes[1].className, 'transport-vehicle-passenger-table-shell');
  assert.equal(detailsPanel.querySelector('.transport-vehicle-details-actions'), null);
});

test('transport vehicle details keep the restricted edit path for vehicles that are not ready for allocation', async () => {
  const detailsPanel = await renderVehicleDetailsPanelForTest({
    id: 82,
    tipo: null,
    lugares: 4,
    tolerance: 5,
    is_ready_for_allocation: false,
    pending_fields: ['tipo', 'placa', 'color'],
  });

  const actionRow = detailsPanel.querySelector('.transport-vehicle-details-actions');

  assert.ok(actionRow);
  assert.equal(detailsPanel.childNodes[0], actionRow);
  assert.equal(detailsPanel.childNodes[1].className, 'transport-vehicle-passenger-table-shell');
  assert.ok(actionRow.querySelector('.transport-vehicle-edit-button'));
  assert.ok(actionRow.querySelector('.transport-vehicle-delete-button'));
});

test('transport vehicle details render ETA boarding inputs with passenger-specific values and placeholder', async () => {
  await withTransportPageHarness({}, async ({ transportPageApi }) => {
    const detailsPanel = transportPageApi.__testCreateVehicleDetailsPanel(
      {
        id: 83,
        service_scope: 'extra',
        route_kind: 'home_to_work',
        departure_time: '07:45',
        is_ready_for_allocation: true,
        pending_fields: ['placa', 'color'],
      },
      [
        {
          id: 301,
          nome: 'Alice Tan',
          service_date: '2026-06-13',
          route_kind: 'home_to_work',
          assignment_status: 'confirmed',
          boarding_time: '06:50',
        },
        {
          id: 302,
          nome: 'Bob Tan',
          service_date: '2026-06-13',
          route_kind: 'home_to_work',
          assignment_status: 'confirmed',
          boarding_time: null,
        },
      ],
      {
        scope: 'extra',
        routeKind: 'home_to_work',
      }
    );

    const timeInputs = detailsPanel.querySelectorAll('.transport-vehicle-passenger-time-input');

    assert.equal(detailsPanel.querySelector('.transport-vehicle-passenger-time-header').textContent, 'Boarding');
    assert.equal(timeInputs.length, 2);
    assert.equal(timeInputs[0].value, '06:50');
    assert.equal(timeInputs[1].value, '');
    assert.equal(timeInputs[1].getAttribute('placeholder'), 'HH:MM');
    assert.ok(detailsPanel.querySelector('.transport-passenger-remove-button'));
    assert.equal(detailsPanel.querySelector('.transport-vehicle-details-actions'), null);
  });
});

test('transport vehicle details render ETD as a shared read-only departure time', async () => {
  await withTransportPageHarness({}, async ({ transportPageApi }) => {
    const detailsPanel = transportPageApi.__testCreateVehicleDetailsPanel(
      {
        id: 84,
        service_scope: 'extra',
        route_kind: 'work_to_home',
        departure_time: '18:10',
        is_ready_for_allocation: true,
        pending_fields: [],
      },
      [
        {
          id: 401,
          nome: 'Charlie Lim',
          service_date: '2026-06-13',
          route_kind: 'work_to_home',
          assignment_status: 'confirmed',
          boarding_time: '06:45',
        },
      ],
      {
        scope: 'extra',
        routeKind: 'work_to_home',
      }
    );

    assert.equal(detailsPanel.querySelector('.transport-vehicle-passenger-time-header').textContent, 'Departure');
    assert.equal(detailsPanel.querySelectorAll('.transport-vehicle-passenger-time-input').length, 0);
    assert.equal(detailsPanel.querySelector('.transport-vehicle-passenger-time-value').textContent, '18:10');
  });
});

test('transport vehicle details save ETA boarding time inline through the dedicated endpoint', async () => {
  let requestPayload = null;

  await withTransportPageHarness(
    {
      assignmentBoardingTimePutHandler(request) {
        requestPayload = JSON.parse(request.body);
        return createFetchResponse({ ok: true, message: 'Transport boarding time saved successfully.' }, 200);
      },
    },
    async ({ transportPageApi, fetchCalls, flushAsyncWork }) => {
      const detailsPanel = transportPageApi.__testCreateVehicleDetailsPanel(
        {
          id: 85,
          service_scope: 'extra',
          route_kind: 'home_to_work',
          departure_time: '07:45',
          is_ready_for_allocation: true,
          pending_fields: [],
        },
        [
          {
            id: 501,
            nome: 'Dana Koh',
            service_date: '2026-06-13',
            route_kind: 'home_to_work',
            assignment_status: 'confirmed',
            boarding_time: '06:50',
          },
        ],
        {
          scope: 'extra',
          routeKind: 'home_to_work',
        }
      );

      const timeInput = detailsPanel.querySelector('.transport-vehicle-passenger-time-input');

      timeInput.value = '07:05';
      timeInput.dispatchEvent(createFakeEvent('input', { target: timeInput }));
      timeInput.dispatchEvent(createFakeEvent('blur', { target: timeInput }));
      await flushAsyncWork();

      assert.deepEqual(requestPayload, {
        request_id: 501,
        service_date: '2026-06-13',
        route_kind: 'home_to_work',
        boarding_time: '07:05',
      });
      assert.ok(fetchCalls.some((call) => call.method === 'PUT' && call.url.includes('/assignments/boarding-time')));
      assert.ok(fetchCalls.some((call) => call.method === 'GET' && call.url.includes('/dashboard?')));
    }
  );
});

test('transport vehicle details keep the remove action working with the new time column', async () => {
  let requestPayload = null;

  await withTransportPageHarness(
    {
      assignmentPostHandler(request) {
        requestPayload = JSON.parse(request.body);
        return createFetchResponse({ ok: true, message: 'Transport assignment saved successfully.' }, 200);
      },
    },
    async ({ transportPageApi, fetchCalls, flushAsyncWork }) => {
      const detailsPanel = transportPageApi.__testCreateVehicleDetailsPanel(
        {
          id: 86,
          service_scope: 'extra',
          route_kind: 'home_to_work',
          departure_time: '07:45',
          is_ready_for_allocation: true,
          pending_fields: ['placa'],
        },
        [
          {
            id: 601,
            nome: 'Erin Goh',
            service_date: '2026-06-13',
            route_kind: 'home_to_work',
            assignment_status: 'confirmed',
            boarding_time: '06:55',
          },
        ],
        {
          scope: 'extra',
          routeKind: 'home_to_work',
        }
      );

      const removeButton = detailsPanel.querySelector('.transport-passenger-remove-button');

      removeButton.click();
      await flushAsyncWork();

      assert.deepEqual(requestPayload, {
        request_id: 601,
        service_date: '2026-06-13',
        route_kind: 'home_to_work',
        status: 'pending',
      });
      assert.ok(fetchCalls.some((call) => call.method === 'POST' && call.url.includes('/assignments')));
    }
  );
});

test('transport vehicle details expose stable column keys and time sort metadata for future extensions', async () => {
  await withTransportPageHarness({}, async ({ transportPageApi }) => {
    const detailsPanel = transportPageApi.__testCreateVehicleDetailsPanel(
      {
        id: 87,
        service_scope: 'extra',
        route_kind: 'home_to_work',
        departure_time: '07:45',
        is_ready_for_allocation: true,
        pending_fields: [],
      },
      [
        {
          id: 701,
          nome: 'Fiona Yap',
          service_date: '2026-06-13',
          route_kind: 'home_to_work',
          assignment_status: 'confirmed',
          boarding_time: '06:50',
        },
        {
          id: 702,
          nome: 'Gabe Lee',
          service_date: '2026-06-13',
          route_kind: 'home_to_work',
          assignment_status: 'confirmed',
          boarding_time: null,
        },
      ],
      {
        scope: 'extra',
        routeKind: 'home_to_work',
      }
    );

    const headerRow = detailsPanel.querySelector('.transport-vehicle-passenger-header-row');
    const passengerRows = detailsPanel.querySelectorAll('.transport-vehicle-passenger-row');
    const firstTimeCell = passengerRows[0].childNodes[1];
    const secondTimeCell = passengerRows[1].childNodes[1];

    assert.deepEqual(
      headerRow.childNodes.map((headerCell) => headerCell.dataset.columnKey),
      ['passenger', 'operational-time', 'action']
    );
    assert.equal(passengerRows[0].dataset.timeMode, 'eta');
    assert.equal(firstTimeCell.dataset.columnKey, 'operational-time');
    assert.equal(firstTimeCell.dataset.timeField, 'boarding_time');
    assert.equal(firstTimeCell.dataset.sortValue, '0410');
    assert.equal(secondTimeCell.dataset.sortValue, '9999');
  });
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

test('transport vehicle details styles include the new time column and inline ETA editor states', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(transportCss, /\.transport-vehicle-passenger-table-head th\s*\{/);
  assert.match(transportCss, /\.transport-vehicle-passenger-time-input\s*\{/);
  assert.match(transportCss, /\.transport-vehicle-passenger-time-value\.is-placeholder\s*\{/);
});

test('transport vehicle detail styles keep time and action column widths isolated for future columns', () => {
  const transportCss = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/styles.css'),
    'utf8'
  );

  assert.match(transportCss, /--transport-vehicle-details-time-column-width:\s*78px;/);
  assert.match(transportCss, /--transport-vehicle-details-action-column-width:\s*32px;/);
  assert.match(
    transportCss,
    /width:\s*calc\(100% - \(var\(--transport-vehicle-details-time-column-width\) \+ var\(--transport-vehicle-details-action-column-width\)\)\);/
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
    transportPage.isVehicleReadyForAllocation({ tipo: 'carro', placa: null, color: null, lugares: 4, tolerance: 5 }),
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
    transportPage.formatApiErrorMessage(
      {
        detail: [
          {
            type: 'missing',
            loc: ['body', 'project_id'],
            msg: 'Field required',
          },
        ],
      },
      422
    ),
    'Transport AI project is required.'
  );

  assert.equal(
    transportPage.formatApiErrorMessage({ detail: 'Vehicle already exists.' }, 409),
    'Vehicle already exists.'
  );
});

test('generic transport api structured resolver prioritizes detail.message_key over raw message', () => {
  const localizedPage = loadTransportPageWithI18n();
  localizedPage.setActiveTransportLanguageCode('en');

  assert.equal(
    localizedPage.resolveTransportApiStructuredMessage({
      detail: {
        message: 'Transport request not found.',
        message_key: 'status.couldNotUpdateAllocation',
        message_params: {},
        error_code: 'transport_request_not_found',
      },
    }),
    'Could not update the transport allocation.'
  );

  assert.equal(
    localizedPage.resolveTransportApiStructuredMessage({
      message: 'Vehicle updated successfully.',
      message_key: 'status.vehicleUpdated',
    }),
    'Vehicle updated successfully.'
  );
});

test('formatApiErrorMessage prioritizes structured backend contracts with message_key and params', () => {
  const localizedPage = loadTransportPageWithI18n();
  localizedPage.setActiveTransportLanguageCode('en');

  assert.equal(
    localizedPage.formatApiErrorMessage(
      {
        detail: {
          message: 'Transport request not found.',
          message_key: 'status.couldNotUpdateAllocation',
          message_params: {},
          error_code: 'transport_request_not_found',
        },
      },
      404
    ),
    'Could not update the transport allocation.'
  );

  assert.equal(
    localizedPage.formatApiErrorMessage(
      {
        detail: {
          message: 'The user already has a confirmed extra transport override for this date and route.',
          message_key: 'warnings.extraOverrideConflict',
          message_params: { route: 'Home to Work' },
          error_code: 'transport_assignment_save_failed',
        },
      },
      409
    ),
    'The user already has a confirmed extra transport override for: Home to Work.'
  );
});

test('localizeTransportApiMessage translates confirmed extra override conflicts with route labels', () => {
  const localizedTransportPage = loadTransportPageWithI18n();

  localizedTransportPage.setActiveTransportLanguageCode('pt');
  assert.equal(
    localizedTransportPage.localizeTransportApiMessage(
      'The user already has a confirmed extra transport override for this date and route: home_to_work, work_to_home.'
    ),
    'O usuário já possui um override extra de transporte confirmado para: Casa para o trabalho, Trabalho para casa.'
  );

  assert.equal(
    localizedTransportPage.localizeTransportApiMessage(
      'The user already has a confirmed extra transport override for this date and route.'
    ),
    'O usuário já possui um override extra de transporte confirmado para a data selecionada.'
  );
});

test('declarative i18n sweep attributes cover top bar, modal shell, settings shell, and accessibility hooks in index.html', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );

  // Top bar and shell copy
  assert.match(transportHtml, /data-i18n-text="topbar\.brand"/);
  assert.match(transportHtml, /data-i18n-text="topbar\.allocationBoard"/);
  assert.match(transportHtml, /data-i18n-text="settings\.dashboardLink"/);
  assert.match(transportHtml, /data-i18n-text="ai\.triggerLabel"/);
  assert.match(transportHtml, /data-i18n-text="ai\.calculateRoutes"/);
  assert.match(transportHtml, /data-i18n-text="ai\.implementModifications"/);
  assert.match(transportHtml, /data-i18n-text="ai\.settingsMenuLabel"/);

  // Accessibility/title coverage on shell controls
  assert.match(transportHtml, /data-i18n-aria-label="layout\.transportLayout"/);
  assert.match(transportHtml, /data-i18n-aria-label="layout\.quickActions"/);
  assert.match(transportHtml, /data-i18n-aria-label="layout\.requestUserCreation"/);
  assert.match(transportHtml, /data-i18n-title="layout\.requestUserCreation"/);
  assert.match(transportHtml, /data-i18n-aria-label="vehicles\.addAria\.extra"/);
  assert.match(transportHtml, /data-i18n-title="vehicles\.addAria\.regular"/);

  // Auth labels — replaced positional authLabels[0/1]
  assert.match(transportHtml, /data-i18n-text="auth\.key"/);
  assert.match(transportHtml, /data-i18n-text="auth\.pass"/);

  // Vehicle modal field spans and option values — replaced positional modalFieldLabels/routeOptions/typeOptions
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.type"/);
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.plate"/);
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.color"/);
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.places"/);
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.tolerance"/);
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.departureDate"/);
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.departureTime"/);
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.route"/);
  assert.match(transportHtml, /data-i18n-option="modal\.options\.blankType"/);
  assert.match(transportHtml, /data-i18n-option="modal\.options\.car"/);
  assert.match(transportHtml, /data-i18n-option="routes\.home_to_work"/);
  assert.match(transportHtml, /data-i18n-option="routes\.work_to_home"/);
  assert.match(transportHtml, /data-i18n-aria-label="modal\.closeVehicleAria"/);
  assert.match(transportHtml, /data-i18n-title="modal\.closeVehicleAria"/);

  // Weekend and regular persistence checkboxes — replaced positional weekendLabels/regularLabels
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.everySaturday"/);
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.everySunday"/);
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.everyMonday"/);
  assert.match(transportHtml, /data-i18n-text="modal\.fields\.everyFriday"/);

  // Settings modal labels and placeholder/aria hooks
  assert.match(transportHtml, /data-i18n-text="settings\.title"/);
  assert.match(transportHtml, /data-i18n-text="settings\.preferences"/);
  assert.match(transportHtml, /data-i18n-text="settings\.languages"/);
  assert.match(transportHtml, /data-i18n-text="settings\.arriveAtWorkTime"/);
  assert.match(transportHtml, /data-i18n-text="settings\.vehicleDefaults"/);
  assert.match(transportHtml, /data-i18n-text="settings\.priceVariables"/);
  assert.match(transportHtml, /data-i18n-text="settings\.currencyCode"/);
  assert.match(transportHtml, /data-i18n-text="settings\.saveCurrency"/);
  assert.match(transportHtml, /data-i18n-aria-label="settings\.closeAria"/);

  // Placeholder and title support
  assert.match(transportHtml, /data-i18n-placeholder="ai\.settingsApiKeyPlaceholder"/);
  assert.match(transportHtml, /data-i18n-title="ai\.settingsCloseAria"/);

  // Billing unit options — replaced settingsPriceRateUnitOptions.forEach
  assert.match(transportHtml, /data-i18n-option="settings\.perHour"/);
  assert.match(transportHtml, /data-i18n-option="settings\.perDay"/);
  assert.match(transportHtml, /data-i18n-option="settings\.perWeek"/);
  assert.match(transportHtml, /data-i18n-option="settings\.perMonth"/);
});

test('AI agent modal hardcoded Portuguese strings are replaced with declarative i18n attributes', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );

  // Title, close aria, labels, legend, cancel/submit — all now data-i18n-* driven
  assert.match(transportHtml, /data-i18n-text="ai\.agentSettingsTitle"/);
  assert.match(transportHtml, /data-i18n-aria-label="ai\.agentSettingsCloseAria"/);
  assert.match(transportHtml, /data-i18n-title="ai\.agentSettingsCloseAria"/);
  assert.match(transportHtml, /data-i18n-text="ai\.agentSettingsEarliestBoarding"/);
  assert.match(transportHtml, /data-i18n-text="ai\.agentSettingsArrivalAtWork"/);
  assert.match(transportHtml, /data-i18n-text="ai\.agentSettingsRequestKindsLegend"/);
  assert.match(transportHtml, /data-i18n-text="ai\.agentSettingsCancel"/);
  assert.match(transportHtml, /data-i18n-text="ai\.agentSettingsSubmit"/);
  assert.match(transportHtml, /data-i18n-text="requests\.labels\.extra"/);
  assert.match(transportHtml, /data-i18n-text="requests\.labels\.weekend"/);
  assert.match(transportHtml, /data-i18n-text="requests\.labels\.regular"/);

  // No bare Portuguese hardcoded text in the agent modal buttons
  assert.doesNotMatch(transportHtml, />Cancelar<\/button>[\s\S]*data-ai-agent-submit/);
  assert.doesNotMatch(transportHtml, />Solicitar Rotas<\/button>/);
});

test('AI changes modal hardcoded Portuguese is replaced and new review surface coverage is present', () => {
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );

  // Title and close aria — fix for flash-of-wrong-language
  assert.match(transportHtml, /data-i18n-text="ai\.changesTitle"/);
  assert.match(transportHtml, /data-i18n-aria-label="ai\.changesCloseAria"/);
  assert.match(transportHtml, /data-i18n-title="ai\.changesCloseAria"/);

  // Review kicker and summary heading — new coverage
  assert.match(transportHtml, /data-i18n-text="ai\.review\.kicker"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.summaryHeading"/);

  // Summary card labels — new coverage
  assert.match(transportHtml, /data-i18n-text="ai\.review\.summary\.cost"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.summary\.vehicles"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.summary\.passengers"/);

  // Review contract aside and contract section titles — new coverage
  assert.match(transportHtml, /data-i18n-aria-label="ai\.review\.surfaceNoteAria"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.contract\.heading"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.contract\.vehicleTables\.title"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.contract\.managementTable\.title"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.contract\.exceptions\.title"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.contract\.canonicalRow\.title"/);

  // Canonical row fields — new coverage
  assert.match(transportHtml, /data-i18n-text="ai\.review\.contract\.canonicalRow\.requestId"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.contract\.canonicalRow\.userName"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.contract\.canonicalRow\.homeToWork"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.contract\.canonicalRow\.workToHome"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.contract\.canonicalRow\.pickupOrder"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.contract\.canonicalRow\.note"/);

  // Tabs aria and tab buttons — new coverage
  assert.match(transportHtml, /data-i18n-aria-label="ai\.review\.tabsAria"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.tabs\.review"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.tabs\.vehicles"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.tabs\.passengers"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.tabs\.routes"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.tabs\.audit"/);

  // Panel headings and empty states — new coverage
  assert.match(transportHtml, /data-i18n-text="ai\.review\.panels\.reviewPlan"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.panels\.reviewEmptyState"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.panels\.vehicleDetails"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.panels\.vehiclesEmptyState"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.panels\.passengerDetails"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.panels\.passengersEmptyState"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.panels\.routeDetails"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.panels\.routesEmptyState"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.panels\.audit"/);
  assert.match(transportHtml, /data-i18n-text="ai\.review\.panels\.auditEmptyState"/);
  assert.match(transportHtml, /data-i18n-text="ai\.changesCancel"/);
  assert.match(transportHtml, /data-i18n-text="ai\.changesSave"/);
  assert.match(transportHtml, /data-i18n-text="ai\.changesApply"/);
});

test('declarative i18n sweep code is present in app.js and positional indexing is removed', () => {
  const transportScript = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/app.js'),
    'utf8'
  );

  // Declarative sweeps must cover text, aria-label, placeholder, title, and option content
  assert.match(transportScript, /querySelectorAll\("\[data-i18n-text\]"\)\.forEach/);
  assert.match(transportScript, /querySelectorAll\("\[data-i18n-aria-label\]"\)\.forEach/);
  assert.match(transportScript, /querySelectorAll\("\[data-i18n-aria\]"\)\.forEach/);
  assert.match(transportScript, /querySelectorAll\("\[data-i18n-placeholder\]"\)\.forEach/);
  assert.match(transportScript, /querySelectorAll\("\[data-i18n-title\]"\)\.forEach/);
  assert.match(transportScript, /querySelectorAll\("\[data-i18n-option\]"\)\.forEach/);

  // Positional indexing patterns must be gone
  assert.doesNotMatch(transportScript, /authLabels\[0\]/);
  assert.doesNotMatch(transportScript, /authLabels\[1\]/);
  assert.doesNotMatch(transportScript, /modalFieldLabels\[0\]/);
  assert.doesNotMatch(transportScript, /weekendLabels\[0\]/);
  assert.doesNotMatch(transportScript, /regularLabels\[0\]/);
  assert.doesNotMatch(transportScript, /requestSectionTitles\[0\]/);
  assert.doesNotMatch(transportScript, /paneLinks\[0\]/);
  assert.doesNotMatch(transportScript, /routeOptions\[0\]/);
  assert.doesNotMatch(transportScript, /routeOptions\[1\]/);

  // Static close/cancel shell copy must no longer be translated through bespoke selector loops
  assert.doesNotMatch(
    transportScript,
    /querySelectorAll\("\[data-close-ai-settings-modal\]"\)\.forEach[\s\S]*settingsCloseAria/
  );

  // settingsPriceRateUnitOptions forEach must be gone (now data-i18n-option)
  assert.doesNotMatch(transportScript, /settingsPriceRateUnitOptions\.forEach/);
  assert.doesNotMatch(transportScript, /typeOptions\.forEach/);
});

test('all declarative i18n key paths used in index.html resolve in all five languages', () => {
  const localizedTransportPage = loadTransportPageWithI18n();
  const langs = ['en', 'pt', 'zh', 'ms', 'tl'];
  const transportHtml = fs.readFileSync(
    path.join(__dirname, '../sistema/app/static/transport/index.html'),
    'utf8'
  );
  const keyPaths = extractDeclarativeI18nKeyPathsFromHtml(transportHtml);

  assert.ok(keyPaths.length > 0, 'Expected index.html to expose declarative i18n key paths.');

  for (const code of langs) {
    for (const keyPath of keyPaths) {
      const result = localizedTransportPage.translateTransportText(keyPath, undefined, code);
      assert.notEqual(result, keyPath, `Key "${keyPath}" must resolve for language "${code}"`);
    }
  }
});

test('stored language is applied to declarative shell copy before DOMContentLoaded', () => {
  const previousGlobals = {
    document: global.document,
    localStorage: global.localStorage,
  };
  const document = createTransportPageTestDocument();
  const storageKey = 'checking.transport.dashboard.language';

  document.readyState = 'loading';
  global.document = document;
  global.localStorage = {
    getItem(key) {
      return key === storageKey ? 'pt' : null;
    },
    setItem() {},
    removeItem() {},
  };

  try {
    const localizedTransportPage = loadTransportPageWithI18n();

    assert.equal(document.documentElement.lang, 'pt');
    assert.equal(document.title, localizedTransportPage.translateTransportText('document.title', undefined, 'pt'));
    assert.equal(
      document.querySelector('[data-open-settings-modal]').textContent,
      localizedTransportPage.translateTransportText('settings.dashboardLink', undefined, 'pt')
    );
    assert.equal(
      document.querySelector('[data-open-settings-modal]').getAttribute('aria-label'),
      localizedTransportPage.translateTransportText('settings.openAria', undefined, 'pt')
    );
    assert.equal(
      document.querySelector('[data-open-settings-modal]').getAttribute('title'),
      localizedTransportPage.translateTransportText('settings.openAria', undefined, 'pt')
    );
    assert.equal(
      document.querySelector('[data-ai-settings-api-key]').getAttribute('placeholder'),
      localizedTransportPage.translateTransportText('ai.settingsApiKeyPlaceholder', undefined, 'pt')
    );
    assert.equal(
      document.getElementById('transport-ai-settings-modal-title').textContent,
      localizedTransportPage.translateTransportText('ai.settingsTitle', undefined, 'pt')
    );
    assert.equal(
      document.querySelector('[data-ai-changes-title]').textContent,
      localizedTransportPage.translateTransportText('ai.changesTitle', undefined, 'pt')
    );
  } finally {
    delete global.CheckingTransportI18n;
    delete global.CheckingTransportPage;
    delete global.CheckingTransportPageController;
    if (previousGlobals.document === undefined) {
      delete global.document;
    } else {
      global.document = previousGlobals.document;
    }
    if (previousGlobals.localStorage === undefined) {
      delete global.localStorage;
    } else {
      global.localStorage = previousGlobals.localStorage;
    }
  }
});

test('switching language reapplies declarative text, aria-label, placeholder, and title for hidden shell content', async () => {
  const previousLocalStorage = global.localStorage;
  const storageKey = 'checking.transport.dashboard.language';
  const writes = [];

  global.localStorage = {
    getItem(key) {
      return key === storageKey ? 'pt' : null;
    },
    setItem(key, value) {
      writes.push([key, value]);
    },
    removeItem() {},
  };

  try {
    await withTransportPageHarness({}, async ({ getElement, flushAsyncWork, transportPageApi, document }) => {
      const settingsTrigger = getElement('[data-open-settings-modal]');
      const requestUserButton = getElement('[data-request-user-link]');
      const apiKeyInput = getElement('[data-ai-settings-api-key]');
      const aiSettingsTitle = getElement('#transport-ai-settings-modal-title');
      const aiChangesTitle = getElement('[data-ai-changes-title]');
      const languageSelect = getElement('[data-settings-language-select]');

      assert.equal(settingsTrigger.textContent, transportPageApi.translateTransportText('settings.dashboardLink', undefined, 'pt'));
      assert.equal(settingsTrigger.getAttribute('aria-label'), transportPageApi.translateTransportText('settings.openAria', undefined, 'pt'));
      assert.equal(settingsTrigger.getAttribute('title'), transportPageApi.translateTransportText('settings.openAria', undefined, 'pt'));
      assert.equal(requestUserButton.getAttribute('aria-label'), transportPageApi.translateTransportText('layout.requestUserCreation', undefined, 'pt'));
      assert.equal(requestUserButton.getAttribute('title'), transportPageApi.translateTransportText('layout.requestUserCreation', undefined, 'pt'));
      assert.equal(apiKeyInput.getAttribute('placeholder'), transportPageApi.translateTransportText('ai.settingsApiKeyPlaceholder', undefined, 'pt'));
      assert.equal(aiSettingsTitle.textContent, transportPageApi.translateTransportText('ai.settingsTitle', undefined, 'pt'));
      assert.equal(aiChangesTitle.textContent, transportPageApi.translateTransportText('ai.changesTitle', undefined, 'pt'));
      assert.equal(document.documentElement.lang, 'pt');

      languageSelect.value = 'en';
      languageSelect.dispatchEvent(createFakeEvent('change', { target: languageSelect }));
      await flushAsyncWork(8);

      assert.equal(settingsTrigger.textContent, transportPageApi.translateTransportText('settings.dashboardLink', undefined, 'en'));
      assert.equal(settingsTrigger.getAttribute('aria-label'), transportPageApi.translateTransportText('settings.openAria', undefined, 'en'));
      assert.equal(settingsTrigger.getAttribute('title'), transportPageApi.translateTransportText('settings.openAria', undefined, 'en'));
      assert.equal(requestUserButton.getAttribute('aria-label'), transportPageApi.translateTransportText('layout.requestUserCreation', undefined, 'en'));
      assert.equal(requestUserButton.getAttribute('title'), transportPageApi.translateTransportText('layout.requestUserCreation', undefined, 'en'));
      assert.equal(apiKeyInput.getAttribute('placeholder'), transportPageApi.translateTransportText('ai.settingsApiKeyPlaceholder', undefined, 'en'));
      assert.equal(aiSettingsTitle.textContent, transportPageApi.translateTransportText('ai.settingsTitle', undefined, 'en'));
      assert.equal(aiChangesTitle.textContent, transportPageApi.translateTransportText('ai.changesTitle', undefined, 'en'));
      assert.equal(document.documentElement.lang, 'en');
      assert.equal(document.title, transportPageApi.translateTransportText('document.title', undefined, 'en'));
      assert.ok(
        writes.some(([key, value]) => key === storageKey && value === 'en'),
        'Expected the selected language to be persisted after switching.'
      );
    });
  } finally {
    delete global.CheckingTransportPageController;
    if (previousLocalStorage === undefined) {
      delete global.localStorage;
    } else {
      global.localStorage = previousLocalStorage;
    }
  }
});

test('node:test helper fallback stays minimal without i18n bootstrap while interface harness bootstraps explicitly', async () => {
  assert.equal(transportPage.translateTransportText('status.ready'), 'status.ready');

  const localizedTransportPage = loadTransportPageWithI18n();
  assert.notEqual(localizedTransportPage.translateTransportText('status.ready', undefined, 'en'), 'status.ready');

  await withTransportPageHarness({}, async ({ transportPageApi }) => {
    assert.notEqual(transportPageApi.translateTransportText('status.ready', undefined, 'en'), 'status.ready');
  });
});

test('switching language rerenders active status, open settings, open ai review, and expanded vehicle detail', async () => {
  const previousGetComputedStyle = global.getComputedStyle;
  const dashboardResponse = {
    selected_route: 'home_to_work',
    selected_date: '2026-06-13',
    projects: [createTransportProjectRow(101, 'Project Atlas')],
    project_rows: [],
    regular_requests: [
      {
        id: 501,
        nome: 'Alice Tan',
        end_rua: '7 Garden Street',
        zip: '100001',
        request_kind: 'regular',
        route_kind: 'home_to_work',
        service_date: '2026-06-13',
        assignment_status: 'confirmed',
        boarding_time: '07:05',
        assigned_vehicle: { id: 77, placa: 'REG1001', route_kind: 'home_to_work' },
      },
    ],
    weekend_requests: [],
    extra_requests: [],
    regular_vehicles: [
      {
        id: 77,
        schedule_id: 77,
        tipo: 'van',
        placa: 'REG1001',
        lugares: 12,
        assigned_count: 1,
        service_date: '2026-06-13',
        service_scope: 'regular',
        route_kind: 'home_to_work',
        is_ready_for_allocation: true,
      },
    ],
    weekend_vehicles: [],
    extra_vehicles: [],
    regular_vehicle_registry: [],
    weekend_vehicle_registry: [],
    extra_vehicle_registry: [],
    workplaces: [],
  };
  const latestSuggestionResponse = Object.assign({}, getSampleLatestSuggestionResponse(), {
    message_key: 'ai.agentSettingsReadyForReview',
    message_params: {},
  });

  global.getComputedStyle = function () {
    return {
      rowGap: '0px',
      gap: '0px',
      width: '264px',
      height: '248px',
    };
  };

  try {
    await withTransportPageHarness(
      { dashboardResponse, latestSuggestionResponse },
      async ({ getElement, document, flushAsyncWork, transportPageApi }) => {
      const settingsTrigger = getElement('[data-open-settings-modal]');
      settingsTrigger.dispatchEvent(createFakeEvent('click', { target: settingsTrigger }));
      await flushAsyncWork();

      const vehicleButton = document.querySelector('[data-vehicle-id]');
      assert.ok(
        vehicleButton,
        `Expected one vehicle tile to be rendered before opening details. Current status: "${getElement('[data-status-message]').textContent}".`
      );
      vehicleButton.dispatchEvent(createFakeEvent('click', { target: vehicleButton }));
      await flushAsyncWork();

      const aiMenuTrigger = getElement('[data-ai-menu-trigger]');
      aiMenuTrigger.dispatchEvent(createFakeEvent('click', { target: aiMenuTrigger }));
      const aiImplementButton = getElement('[data-ai-menu-action="implement-modifications"]');
      aiImplementButton.dispatchEvent(createFakeEvent('click', { target: aiImplementButton }));
      await flushAsyncWork(10);

      assert.equal(getElement('[data-settings-modal]').hidden, false);
      assert.equal(getElement('[data-ai-changes-modal]').hidden, false);
      assert.equal(
        getElement('[data-status-message]').textContent,
        transportPageApi.translateTransportText('ai.agentSettingsReadyForReview', undefined, 'en')
      );
      assert.equal(
        getElement('[data-ai-changes-status]').textContent,
        transportPageApi.translateTransportText('ai.agentSettingsReadyForReview', undefined, 'en')
      );
      assert.equal(
        getElement('[data-settings-language-label]').textContent,
        transportPageApi.translateTransportText('settings.languages', undefined, 'en')
      );

      const englishTimeHeader = document.querySelector('.transport-vehicle-passenger-time-header');
      assert.ok(englishTimeHeader, 'Expected expanded vehicle detail header to be visible before language switch.');
      assert.equal(
        englishTimeHeader.textContent,
        transportPageApi.translateTransportText('vehicleDetails.boardingHeader', undefined, 'en')
      );

      const languageSelect = getElement('[data-settings-language-select]');
      languageSelect.value = 'pt';
      languageSelect.dispatchEvent(createFakeEvent('change', { target: languageSelect }));
      await flushAsyncWork(10);

      assert.equal(getElement('[data-settings-modal]').hidden, false);
      assert.equal(getElement('[data-ai-changes-modal]').hidden, false);
      assert.equal(
        getElement('[data-status-message]').textContent,
        transportPageApi.translateTransportText('ai.agentSettingsReadyForReview', undefined, 'pt')
      );
      assert.equal(
        getElement('[data-ai-changes-status]').textContent,
        transportPageApi.translateTransportText('ai.agentSettingsReadyForReview', undefined, 'pt')
      );
      assert.equal(
        getElement('[data-settings-language-label]').textContent,
        transportPageApi.translateTransportText('settings.languages', undefined, 'pt')
      );

      const localizedTimeHeader = document.querySelector('.transport-vehicle-passenger-time-header');
      assert.ok(localizedTimeHeader, 'Expected expanded vehicle detail header to remain visible after language switch.');
      assert.equal(
        localizedTimeHeader.textContent,
        transportPageApi.translateTransportText('vehicleDetails.boardingHeader', undefined, 'pt')
      );
      }
    );
  } finally {
    if (previousGetComputedStyle === undefined) {
      delete global.getComputedStyle;
    } else {
      global.getComputedStyle = previousGetComputedStyle;
    }
  }
});
