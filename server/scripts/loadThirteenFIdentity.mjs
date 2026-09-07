/**
 * Load the parsed quarterly 13F lists into the identity tables.
 *
 *   node scripts/loadThirteenFIdentity.mjs --from 2019q1 --to 2026q2 --apply
 *
 * Dry run by default: it fetches, parses, aggregates and reports, and writes
 * nothing. --apply is what writes.
 *
 * Writes are additive. Nothing is deleted and nothing in institutional_holdings
 * is touched by this script - it populates the reference tables only. Applying
 * a resolved ticker to holdings is a separate step, so a bad load can be
 * inspected and corrected before it reaches anything a client sees.
 */
import { createClient } from '@supabase/supabase-js';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { rowsFromTextItems, securitiesFromRows } from '../services/thirteenFListPdf.js';
import { classifySecurity, chainIdentities } from '../services/thirteenFList.js';

const SEC_USER_AGENT = (process.env.SEC_USER_AGENT
  || 'AGI Institutional Research research@agarwalglobalinvestments.com').trim();
const PATHS = [
  (q) => `https://www.sec.gov/files/investment/13flist${q}.pdf`,
  (q) => `https://www.sec.gov/divisions/investment/13f/13flist${q}.pdf`,
];

const flag = (name, fallback = null) => {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : fallback;
};
const APPLY = process.argv.includes('--apply');

export function quartersBetween(from, to) {
  const parse = (s) => {
    const m = /^(\d{4})q([1-4])$/.exec(String(s || '').toLowerCase());
    if (!m) throw new Error(`quarter must look like 2026q2, got ${JSON.stringify(s)}`);
    return { year: Number(m[1]), q: Number(m[2]) };
  };
  const a = parse(from);
  const b = parse(to);
  const out = [];
  for (let y = a.year, q = a.q; y < b.year || (y === b.year && q <= b.q);) {
    out.push(`${y}q${q}`);
    q += 1;
    if (q > 4) { q = 1; y += 1; }
    if (out.length > 200) break;
  }
  return out;
}

import { aggregateByCusip } from '../services/thirteenFAggregate.js';

async function download(quarter, dir) {
  let lastStatus = null;
  for (const build of PATHS) {
    const url = build(quarter);
    const response = await fetch(url, { headers: { 'User-Agent': SEC_USER_AGENT } });
    if (response.ok) {
      const file = path.join(dir, `${quarter}.pdf`);
      fs.writeFileSync(file, Buffer.from(await response.arrayBuffer()));
      return { file, url };
    }
    lastStatus = response.status;
    await new Promise((r) => setTimeout(r, 350));
  }
  throw new Error(`no list for ${quarter} (last status ${lastStatus})`);
}

async function parsePdf(file, quarter) {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const doc = await pdfjs.getDocument({ data: new Uint8Array(fs.readFileSync(file)), useSystemFonts: true }).promise;
  const rows = [];
  for (let page = 1; page <= doc.numPages; page += 1) {
    const content = await (await doc.getPage(page)).getTextContent();
    rows.push(...securitiesFromRows(rowsFromTextItems(content.items), { quarter }));
  }
  return rows.map((row) => ({ ...row, security_class: classifySecurity(row.description) }));
}

/**
 * Upsert in chunks.
 *
 * Forty thousand rows in one statement is how the identifier backfill spent
 * three runs dying at the two-minute statement timeout. Chunks keep each
 * statement small enough to finish and let a failure name the range it was in.
 */
async function upsertChunks(client, table, rows, conflict, size = 500) {
  let written = 0;
  for (let i = 0; i < rows.length; i += size) {
    const chunk = rows.slice(i, i + size);
    const { error } = await client.from(table).upsert(chunk, { onConflict: conflict });
    if (error) throw new Error(`${table} rows ${i}-${i + chunk.length}: ${error.message}`);
    written += chunk.length;
    if (written % 5000 === 0) console.log(`[identity]   ${table}: ${written.toLocaleString()}/${rows.length.toLocaleString()}`);
  }
  return written;
}

const quarters = quartersBetween(flag('from', '2019q1'), flag('to', '2026q2'));
console.log(`[identity] mode=${APPLY ? 'APPLY' : 'DRY RUN'}  ${quarters.length} quarter(s)`);

const dir = fs.mkdtempSync(path.join(os.tmpdir(), '13f-identity-'));
const all = [];
const loads = [];
try {
  for (const quarter of quarters) {
    const { file, url } = await download(quarter, dir);
    const rows = await parsePdf(file, quarter);
    fs.rmSync(file, { force: true });
    const equities = rows.filter((r) => r.security_class === 'equity').length;
    if (!rows.length) throw new Error(`${quarter} parsed to zero rows`);
    if (equities < 1000) throw new Error(`${quarter} parsed only ${equities} equities`);
    all.push(...rows);
    loads.push({ quarter, source_url: url, rows_parsed: rows.length, equities_parsed: equities });
    console.log(`[identity] ${quarter}: ${rows.length.toLocaleString()} rows, ${equities.toLocaleString()} equity`);
  }
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}

const securities = aggregateByCusip(all);
const chains = chainIdentities(all);
const chainRows = [];
for (const chain of chains) {
  for (const entry of chain.cusips) {
    chainRows.push({
      cusip: entry.cusip,
      security_key: chain.security_key,
      name_key: chain.name_key,
      held_at_edge: chain.held_at_edge,
      chain_length: chain.cusips.length,
    });
  }
}

const byClass = {};
for (const s of securities) byClass[s.security_class] = (byClass[s.security_class] || 0) + 1;
console.log(`\n[identity] distinct CUSIPs: ${securities.length.toLocaleString()}`);
console.log('[identity] by class:', Object.entries(byClass).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${v.toLocaleString()}`).join(', '));
console.log(`[identity] identity chains: ${chains.length.toLocaleString()}`
  + `, renamed ${chains.filter((c) => c.changed_identifier).length.toLocaleString()}`
  + `, held at window edge ${chains.filter((c) => c.held_at_edge).length.toLocaleString()}`);
console.log(`[identity] chain rows: ${chainRows.length.toLocaleString()}`);

if (!APPLY) {
  console.log('\n[identity] dry run. Nothing written. Re-run with --apply.');
  process.exit(0);
}

const url = process.env.SUPABASE_URL;
const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
if (!url || !key) {
  console.error('[identity] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required to apply.');
  process.exit(78);
}
const client = createClient(url, key, { auth: { persistSession: false } });

console.log('\n[identity] writing...');
await upsertChunks(client, 'sec_13f_securities', securities.map((s) => ({ ...s, updated_at: new Date().toISOString() })), 'cusip');
await upsertChunks(client, 'sec_13f_identity_chain', chainRows.map((c) => ({ ...c, updated_at: new Date().toISOString() })), 'cusip');
const { error: loadError } = await client.from('sec_13f_list_loads').insert(loads);
if (loadError) throw new Error(`sec_13f_list_loads: ${loadError.message}`);
console.log(`[identity] done: ${securities.length.toLocaleString()} securities, ${chainRows.length.toLocaleString()} chain rows, ${loads.length} load records.`);
process.exit(0);
