/**
 * Download and parse the SEC's quarterly lists of Section 13(f) securities.
 *
 *   node scripts/fetchThirteenFLists.mjs --from 2019q1 --to 2026q2
 *   node scripts/fetchThirteenFLists.mjs --from 2026q2 --to 2026q2 --out /tmp/q2.json
 *
 * Reads only. Nothing is written to the database by this script; it produces a
 * summary and, with --out, a JSON file for inspection. Loading is a separate
 * step so the parse can be checked before anything is stored.
 *
 * Two things about this data are worth keeping in mind while running it.
 *
 * The list is published as PDF and nothing else. There is no txt, csv or xlsx
 * variant - each returns 404 on both paths the SEC serves these from - so the
 * PDF is not a convenience, it is the only form.
 *
 * The list carries a CUSIP Global Services and American Bankers Association
 * copyright with a "no redistribution without permission" notice. Preparing and
 * processing 13F data is its stated purpose, so parsing it into our own store
 * is within that. The downloaded files are written to a temporary directory and
 * deleted; they are not committed, not served, and not exposed through any API.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { rowsFromTextItems, securitiesFromRows } from '../services/thirteenFListPdf.js';
import { classifySecurity, chainIdentities } from '../services/thirteenFList.js';

const SEC_USER_AGENT = (process.env.SEC_USER_AGENT
  || 'AGI Institutional Research research@agarwalglobalinvestments.com').trim();

// The SEC moved these at some point and did not migrate the archive, so a
// quarter lives on one path or the other with no way to tell which but to ask.
// 2019q1 is only on the old path, 2021q3 only on the new, and 2020q1 on
// neither of the two spellings the new path accepts.
const PATHS = [
  (q) => `https://www.sec.gov/files/investment/13flist${q}.pdf`,
  (q) => `https://www.sec.gov/divisions/investment/13f/13flist${q}.pdf`,
];

function flag(name, fallback = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

/** Every quarter from `from` to `to` inclusive, as '2019q1' style strings. */
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

async function download(quarter, dir) {
  let lastStatus = null;
  for (const build of PATHS) {
    const url = build(quarter);
    const response = await fetch(url, { headers: { 'User-Agent': SEC_USER_AGENT } });
    if (response.ok) {
      const file = path.join(dir, `13flist${quarter}.pdf`);
      fs.writeFileSync(file, Buffer.from(await response.arrayBuffer()));
      return { file, url };
    }
    lastStatus = response.status;
    // The SEC asks for no more than ten requests a second from one address and
    // blocks rather than throttles when that is exceeded. This is nowhere near
    // that, but a miss is immediately followed by another request to the same
    // host, so the pause is worth keeping.
    await new Promise((r) => setTimeout(r, 350));
  }
  throw new Error(`no list found for ${quarter} (last status ${lastStatus})`);
}

async function parsePdf(file, quarter) {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const doc = await pdfjs.getDocument({
    data: new Uint8Array(fs.readFileSync(file)),
    useSystemFonts: true,
  }).promise;
  const rows = [];
  for (let page = 1; page <= doc.numPages; page += 1) {
    const content = await (await doc.getPage(page)).getTextContent();
    rows.push(...securitiesFromRows(rowsFromTextItems(content.items), { quarter }));
  }
  return rows.map((row) => ({ ...row, security_class: classifySecurity(row.description) }));
}

const from = flag('from', '2019q1');
const to = flag('to', '2026q2');
const out = flag('out');
const quarters = quartersBetween(from, to);
const dir = fs.mkdtempSync(path.join(os.tmpdir(), '13flist-'));

console.log(`[13f-list] ${quarters.length} quarter(s): ${quarters[0]} .. ${quarters[quarters.length - 1]}`);
const all = [];
const missing = [];

try {
  for (const quarter of quarters) {
    const started = Date.now();
    let downloaded;
    try {
      downloaded = await download(quarter, dir);
    } catch (error) {
      // A missing quarter is reported and skipped rather than fatal. The
      // archive has real holes, and one hole should not cost the other
      // twenty-nine downloads.
      missing.push(quarter);
      console.warn(`[13f-list] ${quarter}: ${error.message}`);
      continue;
    }
    const rows = await parsePdf(downloaded.file, quarter);
    fs.rmSync(downloaded.file, { force: true });
    const equity = rows.filter((r) => r.security_class === 'equity').length;

    // A quarter that downloads and then parses to nothing is the failure this
    // guard exists for. It happened: 2025Q2 and 2025Q3 returned zero rows and
    // 2025Q4 returned 2,498 equities against about 7,000 in its neighbours,
    // because the column layout had shifted. Nothing errored. The run looked
    // like a success, and the holes silently manufactured 120 false CUSIP
    // renames, because a security absent from a quarter that never parsed
    // looks exactly like a security that was delisted.
    if (!rows.length) throw new Error(`${quarter} downloaded but parsed to zero rows`);
    if (equity < 1000) throw new Error(`${quarter} parsed only ${equity} equities, which is far below any real quarter`);

    all.push(...rows);
    console.log(`[13f-list] ${quarter}: ${rows.length.toLocaleString()} rows`
      + `, ${equity.toLocaleString()} equity  (${((Date.now() - started) / 1000).toFixed(1)}s)`);
  }
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}

if (!all.length) {
  console.error('[13f-list] nothing parsed.');
  process.exit(1);
}

const byClass = {};
for (const row of all) byClass[row.security_class] = (byClass[row.security_class] || 0) + 1;
const chains = chainIdentities(all);
const changed = chains.filter((c) => c.changed_identifier);

console.log(`\n[13f-list] ${all.length.toLocaleString()} rows across ${quarters.length - missing.length} quarter(s)`);
console.log(`[13f-list] distinct CUSIPs: ${new Set(all.map((r) => r.cusip)).size.toLocaleString()}`);
console.log('[13f-list] by class:', Object.entries(byClass)
  .sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${v.toLocaleString()}`).join(', '));
console.log(`[13f-list] equity identity groups: ${chains.length.toLocaleString()}`);
console.log(`[13f-list] groups whose CUSIP changed: ${changed.length.toLocaleString()}`);
if (missing.length) console.log(`[13f-list] quarters unavailable: ${missing.join(', ')}`);

for (const chain of changed.slice(0, 15)) {
  console.log(`   ${chain.issuer_name?.slice(0, 30).padEnd(32)} ${chain.cusips.map((c) => c.cusip).join(' -> ')}`);
}

if (out) {
  fs.writeFileSync(out, JSON.stringify({ quarters, missing, rows: all }, null, 0));
  console.log(`\n[13f-list] wrote ${out}`);
}
process.exit(0);
