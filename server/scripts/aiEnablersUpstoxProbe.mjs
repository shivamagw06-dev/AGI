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

/** A compact description of a payload's shape, a few levels deep. */
function shape(value, depth = 0) {
  if (depth > 2) return '…';
  if (Array.isArray(value)) {
    return value.length ? [`array(${value.length}) of`, shape(value[0], depth + 1)] : 'array(0)';
  }
  if (isObject(value)) {
    const out = {};
    for (const [key, one] of Object.entries(value).slice(0, 14)) out[key] = shape(one, depth + 1);
    const extra = Object.keys(value).length - 14;
    if (extra > 0) out[`…${extra} more`] = '';
    return out;
  }
  if (value === null) return 'null';
  return typeof value;
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

      if (endpoint === 'income-statement' || endpoint === 'cash-flow') {
        const labels = [...new Set(lineItems(payload))];
        const wanted = labels.filter((one) => /capex|capital expenditure|revenue|operations|property|plant|equipment|intangible/i.test(one));
        console.log(`\n  ${labels.length} line items; ones that look like capex or revenue:`);
        for (const one of wanted.slice(0, 14)) console.log(`    ${one}`);
        if (!wanted.length) console.log('    (none matched - naming differs, see the shape above)');
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
