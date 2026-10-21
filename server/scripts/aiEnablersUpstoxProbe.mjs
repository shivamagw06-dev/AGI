#!/usr/bin/env node
/**
 * What Upstox actually returns for the AI-enabler members.
 *
 * Read-only, writes nothing, and prints shapes rather than full payloads.
 * It exists because two screen stages are blocked on data whose availability
 * I have been guessing at:
 *
 *   Stage 2 needs free-float market cap. share-holdings should give the
 *   promoter/FII/DII/public split, which is the free-float *ratio*; the
 *   shares outstanding to multiply it by is the part nobody has confirmed.
 *   This prints every numeric field on profile and balance-sheet whose name
 *   looks like a share count, so the answer is observed rather than assumed.
 *
 *   Stage 3 needs capex and revenue. cash-flow and income-statement should
 *   carry them, but the line-item naming decides how they are extracted.
 *
 * A provenance note, because it matters more than the plumbing: a figure from
 * this API is not the same class of evidence as a figure from the fact store.
 * The fact store carries a document, a page and a sentence. Upstox carries a
 * number. Using these for screening thresholds is fine. Using them behind a
 * claim like "capex intensity increased" is not - that claim has to resolve
 * to a filing row, which is what Product A is for. Where both exist, a
 * disagreement between them is itself a finding.
 *
 * Run from the Render shell (which opens in ~/project/src/server):
 *   node scripts/aiEnablersUpstoxProbe.mjs
 */
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { FUNDAMENTAL_ENDPOINTS, getFundamentals, isUpstoxConfigured } from '../providers/upstox.js';

const UNIVERSE = fileURLToPath(new URL('../config/india-ai-enablers.universe.json', import.meta.url));

/** Field names that would carry a share count, if one is served at all. */
const SHARE_COUNT = /share|equity|outstanding|float|capital/i;

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

/**
 * A compact description of a payload's shape.
 *
 * Depth 6, not 2. The first version of this truncated at 2 and printed an
 * ellipsis exactly where income_statement's and cash_flow's line items live,
 * so the run reported "0 line items" when in fact it had never looked inside
 * them. A probe that cannot see the thing it was written to find is worse
 * than no probe, because the empty result reads like an answer.
 */
function shape(value, depth = 0) {
  if (depth > 6) return '…';
  if (Array.isArray(value)) {
    return value.length ? [`array(${value.length}) of`, shape(value[0], depth + 1)] : 'array(0)';
  }
  if (isObject(value)) {
    const out = {};
    for (const [key, one] of Object.entries(value).slice(0, 24)) out[key] = shape(one, depth + 1);
    const extra = Object.keys(value).length - 24;
    if (extra > 0) out[`…${extra} more`] = '';
    return out;
  }
  if (value === null) return 'null';
  return typeof value;
}

/** Every key present anywhere in a payload, so nothing hides below a depth cap. */
function allKeys(value, found = new Set()) {
  if (Array.isArray(value)) {
    value.slice(0, 5).forEach((one) => allKeys(one, found));
    return found;
  }
  if (isObject(value)) {
    for (const [key, one] of Object.entries(value)) {
      found.add(key);
      allKeys(one, found);
    }
  }
  return found;
}

/** Every leaf whose key looks like a share count, with its value. */
function shareCandidates(value, path = '', found = []) {
  if (Array.isArray(value)) {
    value.slice(0, 3).forEach((one, i) => shareCandidates(one, `${path}[${i}]`, found));
    return found;
  }
  if (isObject(value)) {
    for (const [key, one] of Object.entries(value)) {
      const next = path ? `${path}.${key}` : key;
      if (SHARE_COUNT.test(key) && (typeof one === 'number' || typeof one === 'string')) {
        found.push({ path: next, value: one });
      }
      shareCandidates(one, next, found);
    }
  }
  return found;
}

/** Line-item labels, for working out how capex and revenue are named. */
function lineItems(value, found = []) {
  if (Array.isArray(value)) {
    value.slice(0, 40).forEach((one) => lineItems(one, found));
    return found;
  }
  if (isObject(value)) {
    for (const key of ['name', 'label', 'title', 'particulars', 'line_item', 'display_name']) {
      if (typeof value[key] === 'string') found.push(value[key]);
    }
    for (const one of Object.values(value)) lineItems(one, found);
  }
  return found;
}

const PARAMS = {
  'income-statement': { type: 'consolidated', time_period: 'yearly', fs: true },
  'balance-sheet': { type: 'consolidated', time_period: 'yearly', fs: true },
  'cash-flow': { type: 'consolidated', time_period: 'yearly', fs: true },
  'share-holdings': {},
  'key-ratios': {},
  profile: {},
  'corporate-actions': {},
};

async function main() {
  if (!isUpstoxConfigured()) {
    console.error('Upstox is not configured. This script only reads; it needs UPSTOX_ACCESS_TOKEN.');
    process.exitCode = 1;
    return;
  }
  const universe = JSON.parse(await readFile(UNIVERSE, 'utf8'));
  const members = (universe.members || []).filter((one) => one.admitted !== false);

  // One member for shapes - the payloads are large and identical in form.
  const [sample] = members;
  console.log(`probing ${sample.symbol} (${sample.isin}) across ${FUNDAMENTAL_ENDPOINTS.length} endpoints\n`);

  const shareHits = [];

  // balance-sheet returned history:array(0) under consolidated/yearly/fs on
  // the first run. That may be the wrong parameter set rather than absent
  // data, and shares outstanding would live there, so the variants are tried
  // before concluding anything.
  // Yahoo's quote endpoint now returns 401, so the independent market cap it
  // was providing is gone. The remaining route to a second opinion is inside
  // Upstox but along a different path: market cap is P/E times net income as
  // well as P/B times book equity, and those use different ratios and
  // different statements. They agree for a single-entity company and diverge
  // for a holding company whose ratios and statements are on different bases,
  // which is exactly the error worth catching.
  //
  // That needs net income, and income-statement came back with history: []
  // under consolidated - the same way balance-sheet did before standalone was
  // tried. So the variants are swept for all three statements, not one.
  console.log('='.repeat(72));
  console.log('statement parameter variants');
  console.log('='.repeat(72));
  for (const endpoint of ['balance-sheet', 'income-statement', 'cash-flow']) {
    console.log(`\n  ${endpoint}`);
    for (const params of [
      { type: 'standalone', time_period: 'yearly', fs: true },
      { type: 'standalone', time_period: 'yearly' },
      { type: 'standalone', time_period: 'quarterly', fs: true },
      { type: 'consolidated', time_period: 'yearly', fs: true },
    ]) {
      try {
        const payload = await getFundamentals(sample.isin, endpoint, params);
        const body = payload?.data || {};
        const rows = body.history || body.income_statement || body.cash_flow || body.full_statement || [];
        const withValues = Array.isArray(rows)
          ? rows.filter((one) => (Array.isArray(one?.history) ? one.history.length : 1) > 0)
          : [];
        console.log(`    ${JSON.stringify(params).padEnd(56)} -> ${Array.isArray(rows) ? rows.length : 0} rows, ${withValues.length} carrying values`);
        if (withValues.length) {
          console.log(`      ${JSON.stringify(withValues[0]).slice(0, 700)}`);
        }
      } catch (error) {
        console.log(`    ${JSON.stringify(params).padEnd(56)} -> ${error?.status || ''} ${String(error?.message || error).slice(0, 50)}`);
      }
    }
  }
  console.log();

  console.log('='.repeat(72));
  console.log('legacy: balance-sheet parameter variants');
  console.log('='.repeat(72));
  for (const params of [
    { type: 'consolidated', time_period: 'yearly', fs: true },
    { type: 'consolidated', time_period: 'yearly' },
    { type: 'standalone', time_period: 'yearly', fs: true },
    { type: 'consolidated', time_period: 'quarterly', fs: true },
    {},
  ]) {
    try {
      const payload = await getFundamentals(sample.isin, 'balance-sheet', params);
      const rows = payload?.data?.history || payload?.data?.full_statement || [];
      console.log(`  ${JSON.stringify(params).padEnd(58)} -> ${Array.isArray(rows) ? rows.length : 0} rows`);
      if (Array.isArray(rows) && rows.length) {
        console.log(`    first: ${JSON.stringify(rows[0]).slice(0, 900)}`);
      }
    } catch (error) {
      console.log(`  ${JSON.stringify(params).padEnd(58)} -> ${error?.status || ''} ${String(error?.message || error).slice(0, 60)}`);
    }
  }
  console.log();

  for (const endpoint of FUNDAMENTAL_ENDPOINTS) {
    console.log('='.repeat(72));
    console.log(endpoint);
    console.log('='.repeat(72));
    try {
      const payload = await getFundamentals(sample.isin, endpoint, PARAMS[endpoint] || {});
      console.log(JSON.stringify(shape(payload), null, 1).slice(0, 1800));

      const hits = shareCandidates(payload);
      if (hits.length) {
        console.log('\n  share-count candidates:');
        for (const hit of hits.slice(0, 12)) console.log(`    ${hit.path} = ${hit.value}`);
        shareHits.push({ endpoint, hits: hits.slice(0, 12) });
      }

      // Every key in the payload, and one whole element verbatim. The labels
      // that matter are whatever Upstox actually calls them, so print them
      // rather than test a guess at them.
      const keys = [...allKeys(payload)].sort();
      console.log(`\n  keys present (${keys.length}): ${keys.join(', ')}`);

      if (endpoint === 'income-statement' || endpoint === 'cash-flow' || endpoint === 'balance-sheet') {
        const rows = payload?.data?.income_statement || payload?.data?.cash_flow
          || payload?.data?.history || payload?.data?.full_statement || [];
        console.log(`  periods returned: ${Array.isArray(rows) ? rows.length : 0}`);
        if (Array.isArray(rows) && rows.length) {
          console.log('  first element verbatim:');
          console.log(`    ${JSON.stringify(rows[0]).slice(0, 1400)}`);
        }
        const labels = [...new Set(lineItems(payload))];
        const wanted = labels.filter((one) => /capex|capital expenditure|revenue|operations|property|plant|equipment|intangible|share/i.test(one));
        if (wanted.length) {
          console.log('  labels that look like capex, revenue or shares:');
          for (const one of wanted.slice(0, 16)) console.log(`    ${one}`);
        }
      }

      if (endpoint === 'share-holdings') {
        const rows = payload?.data || [];
        console.log('  categories and the latest reading:');
        for (const row of Array.isArray(rows) ? rows : []) {
          const history = Array.isArray(row?.history) ? row.history : [];
          console.log(`    ${String(row?.category || '?').padEnd(28)} ${history.length} quarters  latest=${JSON.stringify(history[0] ?? null)}`);
        }
      }

      if (endpoint === 'key-ratios') {
        for (const row of Array.isArray(payload?.data) ? payload.data : []) {
          console.log(`    ${String(row?.name || '?').padEnd(14)} company=${row?.company_value}  sector=${row?.sector_value}`);
        }
      }
    } catch (error) {
      console.log(`  FAILED: ${error?.status || ''} ${String(error?.message || error)}`);
    }
    console.log();
  }

  // Availability across every member, so a gap is a count and not a surprise.
  console.log('='.repeat(72));
  console.log('availability across all admitted members');
  console.log('='.repeat(72));
  for (const member of members) {
    const results = [];
    for (const endpoint of ['profile', 'share-holdings', 'cash-flow', 'income-statement', 'key-ratios']) {
      try {
        const payload = await getFundamentals(member.isin, endpoint, PARAMS[endpoint] || {});
        const empty = !payload || (isObject(payload) && !Object.keys(payload).length);
        results.push(`${endpoint}:${empty ? 'empty' : 'ok'}`);
      } catch (error) {
        results.push(`${endpoint}:${error?.status || 'err'}`);
      }
    }
    console.log(`  ${member.symbol.padEnd(12)} ${results.join('  ')}`);
  }

  console.log('\nWhat this decides:');
  console.log(`  free-float market cap  ${shareHits.length
    ? 'a share count is served - Stage 2 and cap weighting can be wired'
    : 'NO share count found - Stage 2 stays blocked and cap weighting keeps refusing'}`);
  console.log('  Stage 3 inputs         see the capex/revenue line items above');
  console.log('\nUpstox figures carry no document, page or sentence. They are usable for');
  console.log('screening thresholds; a claim like "capex intensity increased" still has to');
  console.log('resolve through the fact store.');
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
