const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const transportI18nModulePath = path.join(__dirname, '../sistema/app/static/transport/i18n.js');
const transportIndexPath = path.join(__dirname, '../sistema/app/static/transport/index.html');
const transportAppPath = path.join(__dirname, '../sistema/app/static/transport/app.js');
const REQUIRED_LANGUAGES = ['en', 'pt', 'zh', 'ms', 'tl'];

const INDEX_LITERAL_ALLOWLIST = Object.freeze({
  providers: new Set([
    'OpenAI',
    'DeepSeek',
    'OpenAI -> gpt-5.4-2026-03-05 | reasoning: high',
  ]),
  domainValues: new Set([
    'Tamer Salmem (HR70)',
    'Work to Home Time',
    'Car default places:',
    'Car default price:',
    'Minivan default places:',
    'Minivan default price:',
    'Van default places:',
    'Van default price:',
    'Bus default places:',
    'Bus default price:',
    'Regular vehicles are created for both routes and remain active from Monday to Friday.',
  ]),
  technicalIds: new Set([]),
  nonTranslatableFormats: new Set(['×']),
});

const APP_LITERAL_ALLOWLIST = Object.freeze({
  providers: new Set([
    'The configured Transport AI LLM provider is no longer supported. Select OpenAI or DeepSeek and save the AI settings again.',
  ]),
  domainValues: new Set([
    'Home To Work',
    'Work To Home',
    'A confirmed transport assignment is required to update boarding_time.',
    'Manual boarding_time is only available for confirmed home_to_work assignments.',
    'Regular vehicles must be persistent. Select at least one weekday',
    'Currency code already exists.',
  ]),
  technicalIds: new Set([
    'Transport page controller test helper is unavailable.',
  ]),
  nonTranslatableFormats: new Set([
    '(max-width: 860px)',
  ]),
  backendContractFallbacks: new Set([
    'Sessao de transporte invalida ou expirada',
    'The selected currency is not available.',
    'The selected vehicle is not ready for allocation.',
    'The transport AI suggestion can no longer be applied.',
    'The transport AI suggestion can no longer be cancelled.',
    'The transport AI suggestion can no longer be saved.',
    'The transport AI suggestion cannot be applied because its payload is invalid.',
    'The transport AI suggestion cannot be saved because its payload is invalid.',
    'The transport AI suggestion could not be materialized for apply.',
    'The transport AI suggestion was already applied and cannot be cancelled.',
    'The user already has a confirmed extra transport override for this date and route',
    'Transport AI API key is required when changing the LLM provider.',
    'Transport AI API key is required when creating LLM settings.',
    'Transport AI API key is required when no encrypted key has been stored yet.',
    'Transport AI API key is required.',
    'Transport AI baseline restore requires manual review.',
    'Transport AI project does not exist.',
    'Transport AI project is required.',
    'Transport boarding time saved successfully.',
    'Transport request rejected successfully.',
  ]),
});

function loadTransportI18nRuntime() {
  delete global.CheckingTransportI18n;
  delete require.cache[require.resolve(transportI18nModulePath)];
  require(transportI18nModulePath);
  return global.CheckingTransportI18n;
}

function describeType(value) {
  if (value === null) {
    return 'null';
  }
  if (Array.isArray(value)) {
    return 'array';
  }
  return typeof value;
}

function collectObjectShape(value, basePath, output) {
  const currentType = describeType(value);
  if (basePath) {
    output.set(basePath, currentType);
  }

  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return;
  }

  Object.keys(value).forEach((key) => {
    const nextPath = basePath ? `${basePath}.${key}` : key;
    collectObjectShape(value[key], nextPath, output);
  });
}

function collectDictionaryStrings(value, output) {
  if (typeof value === 'string') {
    const normalized = value.trim();
    if (normalized) {
      output.add(normalized);
    }
    return;
  }

  if (!value || typeof value !== 'object') {
    return;
  }

  Object.values(value).forEach((childValue) => {
    collectDictionaryStrings(childValue, output);
  });
}

function decodeHtmlEntities(value) {
  return String(value || '')
    .replace(/&gt;/g, '>')
    .replace(/&lt;/g, '<')
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim();
}

function collectIndexAdminLiteralCandidates(htmlSource) {
  const candidates = new Set();
  const textNodeRegex = /<([a-z0-9-]+)([^>]*)>([^<]*[A-Za-z\u00C0-\u024F\u4E00-\u9FFF][^<]*)<\/\1>/gim;
  let textMatch = textNodeRegex.exec(htmlSource);

  while (textMatch) {
    const attributes = textMatch[2] || '';
    const literal = decodeHtmlEntities(textMatch[3]);
    if (literal && !/\bdata-i18n-(?:text|option)\s*=/.test(attributes)) {
      candidates.add(literal);
    }
    textMatch = textNodeRegex.exec(htmlSource);
  }

  const tagRegex = /<([a-z0-9-]+)([^>]*)>/gim;
  let tagMatch = tagRegex.exec(htmlSource);
  while (tagMatch) {
    const attributes = tagMatch[2] || '';
    const attributeLiteralRegex = /(aria-label|title|placeholder)="([^"]*[A-Za-z\u00C0-\u024F\u4E00-\u9FFF][^"]*)"/gi;
    let attributeMatch = attributeLiteralRegex.exec(attributes);
    while (attributeMatch) {
      const attributeName = attributeMatch[1];
      const literal = decodeHtmlEntities(attributeMatch[2]);
      if (literal && !attributes.includes(`data-i18n-${attributeName}`)) {
        candidates.add(literal);
      }
      attributeMatch = attributeLiteralRegex.exec(attributes);
    }
    tagMatch = tagRegex.exec(htmlSource);
  }

  return candidates;
}

function collectAppAdminLiteralCandidates(appSource) {
  const candidates = new Set();
  const stringLiteralRegex = /(["'])((?:\\.|(?!\1)[^\\\n\r])*?)\1/gm;
  let literalMatch = stringLiteralRegex.exec(appSource);

  while (literalMatch) {
    const literal = String(literalMatch[2] || '').trim();
    if (!literal) {
      literalMatch = stringLiteralRegex.exec(appSource);
      continue;
    }

    const hasAlphabet = /[A-Za-z]/.test(literal);
    const hasWhitespace = /\s/.test(literal);
    const isI18nKeyPath = /^[a-z0-9]+(?:\.[a-z0-9_]+)+$/i.test(literal);
    const isSelector = /^[#.\[]/.test(literal);
    const isLowercaseClassLike = /^[a-z0-9_\- ]+$/i.test(literal) && !/[A-Z]/.test(literal);
    const looksLikeSentenceOrTemplate = /[A-Z]/.test(literal) || /[{}:,.!?|#]/.test(literal);

    if (
      hasAlphabet
      && hasWhitespace
      && !isI18nKeyPath
      && !isSelector
      && !isLowercaseClassLike
      && looksLikeSentenceOrTemplate
    ) {
      candidates.add(literal);
    }

    literalMatch = stringLiteralRegex.exec(appSource);
  }

  return candidates;
}

function flattenAllowlist(allowlistByCategory) {
  const literalSet = new Set();
  Object.values(allowlistByCategory).forEach((categorySet) => {
    categorySet.forEach((literal) => literalSet.add(literal));
  });
  return literalSet;
}

function listUnexpectedLiterals(candidateSet, dictionaryStrings, allowlistByCategory) {
  const allowlist = flattenAllowlist(allowlistByCategory);
  return Array.from(candidateSet)
    .filter((literal) => !dictionaryStrings.has(literal) && !allowlist.has(literal))
    .sort((left, right) => left.localeCompare(right));
}

function previewList(items, maxItems = 20) {
  if (!items.length) {
    return '(none)';
  }
  const preview = items.slice(0, maxItems);
  const suffix = items.length > maxItems ? `\n... and ${items.length - maxItems} more` : '';
  return `${preview.join('\n')}${suffix}`;
}

test('transport i18n dictionaries keep full structural parity across en, pt, zh, ms, and tl', () => {
  const runtime = loadTransportI18nRuntime();
  const dictionaries = runtime && runtime.dictionaries ? runtime.dictionaries : null;

  assert.ok(dictionaries, 'CheckingTransportI18n.dictionaries must be available for parity validation.');

  REQUIRED_LANGUAGES.forEach((languageCode) => {
    assert.ok(dictionaries[languageCode], `Language dictionary "${languageCode}" must exist.`);
  });

  const referenceShape = new Map();
  collectObjectShape(dictionaries.en, '', referenceShape);

  REQUIRED_LANGUAGES
    .filter((languageCode) => languageCode !== 'en')
    .forEach((languageCode) => {
      const currentShape = new Map();
      collectObjectShape(dictionaries[languageCode], '', currentShape);

      const missingKeys = [];
      const typeMismatches = [];
      const extraKeys = [];

      referenceShape.forEach((referenceType, keyPath) => {
        if (!currentShape.has(keyPath)) {
          missingKeys.push(keyPath);
          return;
        }
        const currentType = currentShape.get(keyPath);
        if (currentType !== referenceType) {
          typeMismatches.push(`${keyPath} (expected ${referenceType}, got ${currentType})`);
        }
      });

      currentShape.forEach((_, keyPath) => {
        if (!referenceShape.has(keyPath)) {
          extraKeys.push(keyPath);
        }
      });

      const problems = [];
      if (missingKeys.length) {
        problems.push(`Missing keys (${missingKeys.length}):\n${previewList(missingKeys)}`);
      }
      if (typeMismatches.length) {
        problems.push(`Type mismatches (${typeMismatches.length}):\n${previewList(typeMismatches)}`);
      }
      if (extraKeys.length) {
        problems.push(`Unexpected extra keys (${extraKeys.length}):\n${previewList(extraKeys)}`);
      }

      assert.equal(
        problems.length,
        0,
        `Dictionary "${languageCode}" diverges from "en" structural contract.\n${problems.join('\n\n')}`
      );
    });
});

test('index.html guardrail blocks new admin literals outside i18n and respects explicit allowlist categories', () => {
  const runtime = loadTransportI18nRuntime();
  const englishDictionaryStrings = new Set();
  collectDictionaryStrings(runtime.dictionaries.en, englishDictionaryStrings);

  const indexHtml = fs.readFileSync(transportIndexPath, 'utf8');
  const candidates = collectIndexAdminLiteralCandidates(indexHtml);
  const unexpectedLiterals = listUnexpectedLiterals(candidates, englishDictionaryStrings, INDEX_LITERAL_ALLOWLIST);

  assert.equal(
    unexpectedLiterals.length,
    0,
    [
      'Found index.html admin literals outside i18n dictionary coverage and explicit allowlist categories.',
      'Allowed categories: providers, domainValues, technicalIds, nonTranslatableFormats.',
      `Unexpected literals (${unexpectedLiterals.length}):`,
      previewList(unexpectedLiterals),
    ].join('\n')
  );
});

test('app.js guardrail blocks new admin literals outside i18n and respects explicit allowlist categories', () => {
  const runtime = loadTransportI18nRuntime();
  const englishDictionaryStrings = new Set();
  collectDictionaryStrings(runtime.dictionaries.en, englishDictionaryStrings);

  const transportAppSource = fs.readFileSync(transportAppPath, 'utf8');
  const candidates = collectAppAdminLiteralCandidates(transportAppSource);
  const unexpectedLiterals = listUnexpectedLiterals(candidates, englishDictionaryStrings, APP_LITERAL_ALLOWLIST);

  assert.equal(
    unexpectedLiterals.length,
    0,
    [
      'Found app.js admin literals outside i18n dictionary coverage and explicit allowlist categories.',
      'Allowed categories: providers, domainValues, technicalIds, nonTranslatableFormats, backendContractFallbacks.',
      `Unexpected literals (${unexpectedLiterals.length}):`,
      previewList(unexpectedLiterals),
    ].join('\n')
  );
});
