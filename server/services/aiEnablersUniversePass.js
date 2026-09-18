/**
 * Stage 1 over the whole exchange: every listed equity, one outcome each.
 *
 * Reads the NSE equity list, fetches each company's Upstox profile, and
 * records what nomination made of its description. Nothing here admits a
 * company. What it changes is the claim the screen can make: from "we read
 * what a search surfaced" to "we looked at all 2,390 and here is what
 * happened to each".
 *
 * Rules carried over from the key-ratios sweep, for the same reasons:
 *
 *   - One company failing never stops the run. A batch that aborts on its
 *     first bad payload loses every healthy company behind it.
 *   - A failed call is recorded as a failure, never as "not nominated". A
 *     company we could not read is unexamined, and the two must not merge.
 *   - A company with no ISIN cannot be addressed by the endpoint. It is
 *     recorded with that reason and kept out of the coverage denominator.
 *   - Below 95% of what could be fetched, the run is DEGRADED. Half the
 *     exchange is not a screen of the exchange.
 *
 * And two of its own:
 *
 *   - Rate limits are waited out, not recorded. A 429 says nothing about the
 *     company; recording it as a failure would make coverage depend on what
 *     else was calling Upstox that minute.
 *   - An authorisation failure stops the run. Every later call would fail the
 *     same way, and 2,390 identical errors are one error.
 */

import { nominate, readingPriority } from './aiEnablersNomination.js';

export const COVERAGE_OK = 0.95;
export const UNIVERSE_PASS_TABLE = 'ai_enabler_universe_pass';

/** Every stored row for a run, paged past PostgREST's 1,000-row cap. */
export async function readUniversePass(db, runId) {
  const rows = [];
  for (let from = 0; ; from += 1000) {
    const { data, error } = await db.from(UNIVERSE_PASS_TABLE).select('*')
      .eq('run_id', runId).order('symbol').range(from, from + 999);
    if (error) throw new Error(`reading ${UNIVERSE_PASS_TABLE}: ${error.message}`);
    rows.push(...data);
    if (data.length < 1000) break;
  }
  return rows;
}

/** The most recent run id, or null if none has been stored. */
export async function latestUniversePassRun(db) {
  const { data, error } = await db.from(UNIVERSE_PASS_TABLE).select('run_id')
    .order('run_id', { ascending: false }).limit(1);
  if (error) throw new Error(`reading ${UNIVERSE_PASS_TABLE}: ${error.message}`);
  return data?.[0]?.run_id || null;
}

/** Minimal RFC 4180 line split: quoted fields may contain commas. */
function splitCsvLine(line) {
  const out = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"' && line[i + 1] === '"') { field += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { out.push(field); field = ''; }
    else field += ch;
  }
  out.push(field);
  return out;
}

/**
 * An NSE equity list, as companies: EQUITY_L.csv (main board) or
 * SME_EQUITY_L.csv (Emerge).
 *
 * Headers in the main-board file carry leading spaces (" SERIES",
 * " ISIN NUMBER") and the SME file may use underscores ("ISIN_NUMBER"); both
 * are normalised rather than matched literally.
 */
export function parseEquityList(csvText, { board = 'main' } = {}) {
  const lines = String(csvText || '').split(/\r?\n/).filter((one) => one.trim());
  if (!lines.length) return [];
  const header = splitCsvLine(lines[0]).map((one) => one.trim().toUpperCase().replace(/_/g, ' ').replace(/\s+/g, ' '));
  const col = (name) => header.indexOf(name);
  const at = { symbol: col('SYMBOL'), name: col('NAME OF COMPANY'), series: col('SERIES'), isin: col('ISIN NUMBER') };
  if (Object.values(at).some((one) => one < 0)) {
    throw new Error(`EQUITY_L header not recognised: ${header.join(', ')}`);
  }
  const seen = new Set();
  const out = [];
  for (const line of lines.slice(1)) {
    const cells = splitCsvLine(line).map((one) => one.trim());
    const symbol = cells[at.symbol]?.toUpperCase();
    if (!symbol || seen.has(symbol)) continue;
    seen.add(symbol);
    const isin = (cells[at.isin] || '').toUpperCase();
    out.push({
      symbol,
      name: cells[at.name] || null,
      series: cells[at.series] || null,
      isin: /^IN[A-Z0-9]{10}$/.test(isin) ? isin : null,
      board,
    });
  }
  return out;
}

/**
 * At most `perMinute` calls in any minute and `perWindow` in any `windowMs`.
 *
 * Rolling, not fixed buckets: a fixed bucket lets twice the limit through
 * across a boundary, which is exactly when a 429 arrives.
 */
export class PacedLimiter {
  constructor({
    perMinute = 250, perWindow = 1_800, windowMs = 30 * 60_000,
    now = () => Date.now(), sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  } = {}) {
    Object.assign(this, { perMinute, perWindow, windowMs, now, sleep });
    this.calls = [];
  }

  #waitFor(t) {
    this.calls = this.calls.filter((one) => t - one < this.windowMs);
    const inMinute = this.calls.filter((one) => t - one < 60_000);
    let wait = 0;
    if (inMinute.length >= this.perMinute) wait = Math.max(wait, inMinute[inMinute.length - this.perMinute] + 60_000 - t);
    if (this.calls.length >= this.perWindow) wait = Math.max(wait, this.calls[this.calls.length - this.perWindow] + this.windowMs - t);
    return wait;
  }

  async take() {
    for (;;) {
      const wait = this.#waitFor(this.now());
      if (wait <= 0) break;
      await this.sleep(wait);
    }
    this.calls.push(this.now());
  }
}

const statusOf = (error) => error?.status ?? (/\b429\b|too many request/i.test(String(error?.message)) ? 429 : null);

/** One company's recorded outcome. Every row has every key. */
function rowFor(company, runId, { disposition, sector = null, nomination = null, description = null, error = null, at }) {
  return {
    run_id: runId,
    symbol: company.symbol,
    isin: company.isin,
    name: company.name,
    series: company.series,
    board: company.board || 'main',
    disposition,
    sector,
    nomination,
    // Stored so a rule change can be re-scored without refetching 2,390
    // profiles. Upstox's text: kept server-side, never served (publicRow).
    description: description || null,
    description_chars: description ? description.length : null,
    error,
    fetched_at: new Date(at).toISOString(),
  };
}

/**
 * Walk the list, one profile per company, saving in batches.
 *
 * `done` holds symbols already stored for this run, so a run that was
 * interrupted resumes where it stopped instead of starting again.
 */
export async function runUniversePass({
  companies,
  runId,
  fetchProfile,
  save,
  done = new Set(),
  limiter = new PacedLimiter(),
  maxRetries = 6,
  backoffMs = 30_000,
  batchSize = 50,
  now = () => Date.now(),
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  onProgress = () => {},
} = {}) {
  let batch = [];
  let processed = 0;
  const flush = async () => {
    if (!batch.length) return;
    await save(batch);
    batch = [];
  };

  for (const company of companies) {
    if (done.has(company.symbol)) continue;
    if (!company.isin) {
      batch.push(rowFor(company, runId, { disposition: 'NO_ISIN', at: now() }));
    } else {
      let row = null;
      for (let attempt = 0; !row; attempt += 1) {
        await limiter.take();
        try {
          const payload = await fetchProfile(company.isin);
          const data = payload?.data || null;
          const description = String(data?.company_profile || '').trim();
          const sector = String(data?.sector || '').trim() || null;
          if (!data || (!description && !sector)) {
            row = rowFor(company, runId, { disposition: 'NO_PROFILE', at: now() });
          } else {
            const nomination = nominate({ description });
            row = rowFor(company, runId, {
              disposition: nomination.nominated ? 'NOMINATED' : (description ? 'NOT_NOMINATED' : 'NO_PROFILE'),
              sector,
              nomination: nomination.nominated ? nomination.subLayers : null,
              description,
              at: now(),
            });
          }
        } catch (error) {
          const status = statusOf(error);
          if (status === 401 || status === 403 || /auth missing|access token/i.test(String(error?.message))) {
            await flush();
            const stop = new Error(`Upstox authorisation failed (${status ? `HTTP ${status}` : error.message}); stopping - every later call would fail the same way.`);
            stop.code = 'UPSTOX_AUTH';
            throw stop;
          }
          if (status === 429 && attempt < maxRetries) {
            await sleep(backoffMs * 2 ** attempt);
            continue;
          }
          // Upstox has no profile for this ISIN: an absence of data, recorded
          // with the reason, and still outside "examined".
          if (status === 404) {
            row = rowFor(company, runId, { disposition: 'NO_PROFILE', error: 'HTTP 404', at: now() });
            continue;
          }
          row = rowFor(company, runId, {
            disposition: 'PROFILE_ERROR',
            error: status === 429 ? 'RATE_LIMITED_AFTER_RETRIES' : String(error?.message || error).slice(0, 300),
            at: now(),
          });
        }
      }
      batch.push(row);
    }
    processed += 1;
    if (batch.length >= batchSize) await flush();
    onProgress({ processed, symbol: company.symbol });
  }
  await flush();
  return { processed };
}

/**
 * Re-score stored descriptions under the current rules, without fetching.
 *
 * Only rows whose outcome came from a description change. A row that was
 * never examined - no profile, a failed call, no ISIN - stays exactly as it
 * was: re-scoring cannot examine what was never read.
 */
export function renominate(rows) {
  const changed = [];
  for (const row of rows) {
    if (row.disposition !== 'NOMINATED' && row.disposition !== 'NOT_NOMINATED') continue;
    if (!row.description) continue;
    const result = nominate({ description: row.description });
    const disposition = result.nominated ? 'NOMINATED' : 'NOT_NOMINATED';
    const nomination = result.nominated ? result.subLayers : null;
    if (disposition !== row.disposition || JSON.stringify(nomination) !== JSON.stringify(row.nomination)) {
      changed.push({ ...row, disposition, nomination });
    }
  }
  return changed;
}

/**
 * A row as the API serves it: without the provider's description text, and
 * with the reading priority the nomination implies.
 */
export function publicRow(row) {
  const { description, ...rest } = row;
  return { ...rest, priority: readingPriority(row) };
}

/**
 * What the run found, and how much of it can be trusted.
 *
 * `reference` is the set of companies already known to qualify - admitted
 * members and held candidates. Any of them the pass did not nominate is a
 * miss, and the misses are the measured blind spot of description-based
 * nomination.
 */
export function summariseUniversePass(rows, { reference = [], listed = null } = {}) {
  const count = (disposition) => rows.filter((one) => one.disposition === disposition).length;
  const addressable = rows.filter((one) => one.disposition !== 'NO_ISIN').length;
  const examined = count('NOMINATED') + count('NOT_NOMINATED');
  const coverage = addressable ? Number((examined / addressable).toFixed(4)) : 0;

  const bySubLayer = {};
  for (const row of rows) {
    for (const one of row.nomination || []) {
      bySubLayer[one.subLayer] = (bySubLayer[one.subLayer] || 0) + 1;
    }
  }

  const bySymbol = new Map(rows.map((one) => [one.symbol, one]));
  const recall = reference.map((ref) => {
    const row = bySymbol.get(ref.symbol);
    return {
      symbol: ref.symbol,
      kind: ref.kind,
      disposition: row?.disposition || 'NOT_IN_LIST',
      subLayers: (row?.nomination || []).map((one) => one.subLayer),
    };
  });
  const missed = recall.filter((one) => one.disposition !== 'NOMINATED');

  const byTier = { 1: 0, 2: 0, 3: 0 };
  const byBoard = {};
  for (const row of rows) {
    const priority = readingPriority(row);
    if (priority) byTier[priority.tier] += 1;
    const b = (byBoard[row.board || 'main'] ||= { listed: 0, nominated: 0 });
    b.listed += 1;
    if (row.disposition === 'NOMINATED') b.nominated += 1;
  }

  const sectors = {};
  for (const row of rows) {
    if (!row.sector) continue;
    const s = (sectors[row.sector] ||= { examined: 0, nominated: 0 });
    if (row.disposition === 'NOMINATED' || row.disposition === 'NOT_NOMINATED') s.examined += 1;
    if (row.disposition === 'NOMINATED') s.nominated += 1;
  }

  return {
    listed: listed ?? rows.length,
    recorded: rows.length,
    complete: listed === null ? null : rows.length >= listed,
    dispositions: {
      NOMINATED: count('NOMINATED'),
      NOT_NOMINATED: count('NOT_NOMINATED'),
      NO_PROFILE: count('NO_PROFILE'),
      PROFILE_ERROR: count('PROFILE_ERROR'),
      NO_ISIN: count('NO_ISIN'),
    },
    addressable,
    examined,
    coverage,
    status: coverage >= COVERAGE_OK ? 'OK' : 'DEGRADED',
    bySubLayer,
    byTier,
    byBoard,
    recall: {
      reference: reference.length,
      nominated: reference.length - missed.length,
      missed,
      rows: recall,
    },
    sectors,
  };
}
