import { Router } from 'express';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { AiEnablersLiveRuntime } from '../services/aiEnablersLiveRuntime.js';
import { liquidityForUniverse, volumeBaselines } from '../services/aiEnablersLiquidity.js';
import {
  getFundamentals, getHistoricalCandles, getIntradayCandles, isUpstoxConfigured,
} from '../providers/upstox.js';
import { sizeForUniverse } from '../services/aiEnablersSize.js';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import {
  fundamentalsForUniverse, intensityForUniverse, stageThreeFromInputs,
} from '../services/aiEnablersFundamentals.js';
import { stageThree, stageTwo } from '../services/aiEnablersScreen.js';
import {
  latestUniversePassRun, publicRow, readUniversePass, referenceQualifiers, summariseUniversePass,
} from '../services/aiEnablersUniversePass.js';
import { exitabilityForUniverse } from '../services/aiEnablersExitability.js';
import { closesFrom, dailyIndex, dilutiveExDates } from '../services/aiEnablersHistory.js';
import {
  canonicalSector, filedSizeRows, lastCloseThrough, marketValueRows, SECTOR_ALIASES, totalsBy,
} from '../services/aiEnablersMarketValue.js';

const UNIVERSE_PATH = fileURLToPath(new URL('../config/india-ai-enablers.universe.json', import.meta.url));
const FACTS_PATH = fileURLToPath(new URL('../config/india-ai-enablers.disclosed-facts.json', import.meta.url));
const INTENSITY_PATH = fileURLToPath(new URL('../config/india-ai-enablers.intensity-inputs.json', import.meta.url));
const SHARES_PATH = fileURLToPath(new URL('../config/india-ai-enablers.shares.json', import.meta.url));
const OPERATING_PATH = fileURLToPath(new URL('../config/india-ai-enablers.operating-data.json', import.meta.url));
const ESTIMATES_PATH = fileURLToPath(new URL('../config/india-ai-enablers.estimates.json', import.meta.url));
const SCORING_PATH = fileURLToPath(new URL('../config/india-ai-enablers.scoring.json', import.meta.url));

let universeCache = null;
export async function loadUniverse({ path = UNIVERSE_PATH, refresh = false } = {}) {
  if (universeCache && !refresh) return universeCache;
  universeCache = JSON.parse(await readFile(path, 'utf8'));
  return universeCache;
}

let runtime = null;
let factClient = null;

/**
 * The fact store client.
 *
 * Lazy, because the service-role key is server-side only and a module-level
 * client would throw at import on any service without it. Returns null rather
 * than throwing so the route can answer 503 with a reason.
 */
function supabaseClient() {
  if (factClient) return factClient;
  try {
    factClient = createSupabaseAdmin();
  } catch {
    factClient = null;
  }
  return factClient;
}

/**
 * The live runtime, started once.
 *
 * Refuses rather than starting a feed with no credentials: a runtime that
 * silently produces an empty basket is indistinguishable on the page from a
 * market where nothing traded.
 */
/**
 * The live runtime, started exactly once.
 *
 * Memoises the start-up promise, not the finished runtime. The earlier version
 * checked `if (runtime)` and only assigned it after awaiting the universe load
 * and seven sequential candle fetches - a window of seconds. Two requests
 * arriving at cold start both saw null, both built a runtime, and both opened
 * a WebSocket. Upstox allows two market-data connections per user, so that is
 * the entire allowance spent on one process. And because the second assignment
 * overwrote the first, the first feed was orphaned: nothing held a reference
 * to it, so shutdownRuntime() could not close it on SIGTERM either. The page
 * polls every thirty seconds, so any two open tabs across a deploy hit this.
 *
 * Refuses rather than starting a feed with no credentials: a runtime that
 * silently produces an empty basket is indistinguishable on the page from a
 * market where nothing traded.
 */
let starting = null;

export async function ensureRuntime({ universe, start = true } = {}) {
  if (runtime) return runtime;
  if (starting) return starting;
  starting = (async () => {
    const loaded = universe || await loadUniverse();
    if (!isUpstoxConfigured()) {
      const error = new Error('Upstox is not configured; set UPSTOX_ACCESS_TOKEN server-side.');
      error.code = 'UPSTOX_NOT_CONFIGURED';
      throw error;
    }
    let baselines = {};
    try {
      const today = new Date().toISOString().slice(0, 10);
      const liquidity = await liquidityForUniverse(loaded, {
        fetchCandles: getHistoricalCandles, to: today,
      });
      baselines = volumeBaselines(liquidity);
    } catch {
      // A missing baseline costs the volume ratio and nothing else; the basket
      // still computes, and volumeRatio reports NO_BASELINE rather than zero.
      baselines = {};
    }
    const built = new AiEnablersLiveRuntime({
      universe: loaded,
      volumeBaselines: baselines,
      // Read at start and again whenever the exchange day rolls, so a bonus
      // or split is excluded on its ex-date rather than printed as a loss.
      fetchCorporateActions: (isin) => getFundamentals(isin, 'corporate-actions', {}),
      // The session so far, so a restart does not wipe the chart to one point.
      fetchIntradayCandles: (key) => getIntradayCandles(key, { unit: 'minutes', interval: 1 }),
      // A fortnight back covers a long holiday; the replay takes the last
      // close strictly before the session.
      fetchDailyCandles: (key, { sessionDate }) => {
        const day = (offset) => new Date(Date.parse(`${sessionDate}T00:00:00Z`) + offset * 86_400_000)
          .toISOString().slice(0, 10);
        return getHistoricalCandles(key, { unit: 'days', interval: 1, to: day(-1), from: day(-14) });
      },
    });
    if (start) await built.start();
    runtime = built;
    return built;
  })();
  try {
    return await starting;
  } finally {
    // Cleared on success and failure alike. On success `runtime` now answers
    // every later call; on failure the next request may try again rather than
    // being handed the same rejected promise forever.
    starting = null;
  }
}

export function resetRuntimeForTests() {
  runtime = null;
  starting = null;
  universeCache = null;
}

/**
 * Close the market-data socket on shutdown.
 *
 * Nothing used to call this. The process handled SIGTERM by closing the HTTP
 * server and exiting, which abandoned the WebSocket without a close frame -
 * so every redeploy left a connection that the provider still considered
 * open. Upstox caps concurrent market-data connections per application, and
 * after enough deploys in a day the cap is reached and every new handshake is
 * refused with a 403 while REST keeps working on the same token. That is
 * exactly the state this service reached after nineteen deploys.
 */
export async function shutdownRuntime() {
  if (!runtime) return { stopped: false, reason: 'no runtime started' };
  try {
    await runtime.stop();
    runtime = null;
    return { stopped: true };
  } catch (error) {
    runtime = null;
    return { stopped: false, reason: String(error?.message || error) };
  }
}

export default function createIndiaAiIntelligenceRouter() {
  const router = Router();

  /** The universe itself: members, candidates, and why each was admitted. */
  router.get('/universe', async (req, res) => {
    try {
      const universe = await loadUniverse({ refresh: req.query.refresh === '1' });
      res.json({
        ok: true,
        status: universe.status,
        version: universe.version,
        note: universe.note,
        construction: universe.construction,
        thresholds: universe.thresholds,
        members: universe.members,
        candidates: universe.candidates,
        excluded: universe.excluded || [],
        // Symbols only: the list was a reading queue, and its other content is not used.
        reportedList: (universe.externalLeads || []).flatMap((one) => one.symbols || []),
      });
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  /**
   * Order books and data-centre capacity, each figure quoted from the
   * company's own document (config/india-ai-enablers.operating-data.json).
   */
  /**
   * AGI's estimates: model definitions, each input marked disclosed (with its
   * document) or assumption (with its range and reason). Computed on the page.
   */
  router.get('/estimates', async (req, res) => {
    try {
      res.json({ ok: true, ...JSON.parse(await readFile(ESTIMATES_PATH, 'utf8')) });
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  /** Filed cash-flow, capital and quarter figures behind the five factors. */
  router.get('/scoring', async (req, res) => {
    try {
      res.json({ ok: true, ...JSON.parse(await readFile(SCORING_PATH, 'utf8')) });
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  router.get('/operating-data', async (req, res) => {
    try {
      res.json({ ok: true, ...JSON.parse(await readFile(OPERATING_PATH, 'utf8')) });
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  /**
   * The facts read out of filings, and what they were read from.
   *
   * Served separately from the universe because provenance differs per
   * company: some entries were read from the primary document by this system
   * and carry page numbers, others were relayed and carry only a source. The
   * page has to be able to tell those apart, so the distinction travels.
   */
  router.get('/filed-facts', async (req, res) => {
    try {
      const facts = JSON.parse(await readFile(FACTS_PATH, 'utf8'));
      res.json({ ok: true, ...facts });
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  /** The basket right now, refusals included. */
  router.get('/live', async (req, res) => {
    try {
      const live = await ensureRuntime();
      res.json({ ok: true, ...live.current(), runtime: live.status() });
    } catch (error) {
      const code = error?.code === 'UPSTOX_NOT_CONFIGURED' ? 503 : 500;
      res.status(code).json({ ok: false, error: String(error?.message || error), code: error?.code || null });
    }
  });

  /** The minute snapshots taken so far this session. */
  router.get('/snapshots', async (req, res) => {
    try {
      const live = await ensureRuntime();
      res.json({ ok: true, snapshots: live.history(), history_rebuild: live.historyRebuild });
    } catch (error) {
      const code = error?.code === 'UPSTOX_NOT_CONFIGURED' ? 503 : 500;
      res.status(code).json({ ok: false, error: String(error?.message || error), code: error?.code || null });
    }
  });

  /**
   * The fundamentals behind the basket, from the fact store.
   *
   * Every figure arrives with the filing row it came from or the arithmetic
   * that produced it. A company nothing has been ingested for says so, and
   * says it differently from a company whose filings are silent.
   */
  router.get('/fundamentals', async (req, res) => {
    try {
      const client = supabaseClient();
      if (!client) return res.status(503).json({ ok: false, error: 'Fact store is not reachable from this service.', code: 'NO_FACT_STORE' });
      const universe = await loadUniverse();
      const period_end = String(req.query.period_end || '').trim() || null;
      if (!period_end) return res.status(400).json({ ok: false, error: 'period_end is required, as YYYY-MM-DD.' });
      const result = await fundamentalsForUniverse(client, universe, { period_end });
      res.json({ ok: true, period_end, ...result });
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  /**
   * Stage 3 of the screen, run over fact-store inputs.
   *
   * This is the join: investment intensity stops being numbers somebody typed
   * and becomes a derivation over cited filing rows.
   */
  router.get('/screen/intensity', async (req, res) => {
    try {
      const client = supabaseClient();
      if (!client) return res.status(503).json({ ok: false, error: 'Fact store is not reachable from this service.', code: 'NO_FACT_STORE' });
      const universe = await loadUniverse();
      const { rows, detail } = await intensityForUniverse(client, universe);
      res.json({ ok: true, screen: stageThree(rows), detail });
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  /**
   * The basket against Nifty 50 since admission: daily equal weight, one
   * point per finished session, each member from the close of its decision
   * day. Cached for ten minutes: every page view would otherwise cost one
   * candle request and one corporate-actions request per member.
   */
  let historyCache = null;
  router.get('/index/history', async (req, res) => {
    try {
      if (historyCache && Date.now() - historyCache.at < 10 * 60_000) return res.json(historyCache.body);
      if (!isUpstoxConfigured()) {
        return res.status(503).json({ ok: false, error: 'Upstox is not configured; set UPSTOX_ACCESS_TOKEN server-side.', code: 'UPSTOX_NOT_CONFIGURED' });
      }
      const universe = await loadUniverse();
      const members = (universe.members || []).filter((one) => one.admitted !== false);
      const starts = members.map((one) => one.membershipStart).filter(Boolean).sort();
      if (!starts.length) return res.json({ ok: true, base: null, points: [], reason: 'NO_MEMBERSHIP_DATES' });
      const day = (iso, offset) => new Date(Date.parse(`${iso}T00:00:00Z`) + offset * 86_400_000).toISOString().slice(0, 10);
      const nowIst = new Date(Date.now() + 330 * 60_000);
      const todayIst = nowIst.toISOString().slice(0, 10);
      // A session counts once it has closed (15:30 IST); before that the
      // intraday chart covers today.
      const closedThrough = nowIst.getUTCHours() * 60 + nowIst.getUTCMinutes() >= 15 * 60 + 30 ? todayIst : day(todayIst, -1);
      const from = day(starts[0], -7);
      const candles = (key) => getHistoricalCandles(key, { unit: 'days', interval: 1, to: closedThrough, from });
      const trim = (map) => new Map([...map].filter(([date]) => date <= closedThrough));
      const closes = {};
      const exDates = {};
      const failures = [];
      for (const member of members) {
        try {
          closes[member.symbol] = trim(closesFrom(await candles(member.instrumentKey)));
        } catch (error) {
          failures.push({ symbol: member.symbol, error: String(error?.message || error) });
        }
        try {
          exDates[member.symbol] = dilutiveExDates(await getFundamentals(member.isin, 'corporate-actions', {}));
        } catch {
          exDates[member.symbol] = new Set();
        }
      }
      const benchmark = trim(closesFrom(await candles(universe.benchmarkKey)));
      const series = dailyIndex({ members, closes, benchmark, exDates });
      const body = {
        ok: true,
        construction: 'daily equal weight; each member from the close of its membershipStart day; bonus, split and rights ex-dates excluded',
        benchmark: 'Nifty 50 (price index)',
        closedThrough,
        ...series,
        failures,
      };
      historyCache = { at: Date.now(), body };
      res.json(body);
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  /**
   * Market value of the members, by layer and by sector, at the last closed
   * session: close x filed shares, P/B x book beside it as a check. Sector is
   * Upstox's profile sector as the universe pass stored it. Whole-company
   * value, not AI exposure. Cached for ten minutes, as the history is.
   */
  // One computation serves the market-value panel and Stage 2, so both see
  // the same closes, counts and floats. The promise is cached, not the
  // result, so two requests at a cold start share one round of fetches.
  let marketValueCache = null;
  const marketValue = () => {
    if (marketValueCache && Date.now() - marketValueCache.at < 10 * 60_000) return marketValueCache.promise;
    const promise = computeMarketValue();
    marketValueCache = { at: Date.now(), promise };
    promise.catch(() => { if (marketValueCache?.promise === promise) marketValueCache = null; });
    return promise;
  };

  async function computeMarketValue() {
    const universe = await loadUniverse();
    const members = (universe.members || []).filter((one) => one.admitted !== false);
    const file = JSON.parse(await readFile(SHARES_PATH, 'utf8'));
    const nowIst = new Date(Date.now() + 330 * 60_000);
    const todayIst = nowIst.toISOString().slice(0, 10);
    const yesterday = new Date(Date.parse(`${todayIst}T00:00:00Z`) - 86_400_000).toISOString().slice(0, 10);
    const closedThrough = nowIst.getUTCHours() * 60 + nowIst.getUTCMinutes() >= 15 * 60 + 30 ? todayIst : yesterday;
    const from = new Date(Date.parse(`${closedThrough}T00:00:00Z`) - 14 * 86_400_000).toISOString().slice(0, 10);

    const closes = {};
    const exDates = {};
    const failures = [];
    for (const member of members) {
      try {
        const found = lastCloseThrough(closesFrom(await getHistoricalCandles(member.instrumentKey, {
          unit: 'days', interval: 1, to: closedThrough, from,
        })), closedThrough);
        if (found) closes[member.symbol] = found;
      } catch (error) {
        failures.push({ symbol: member.symbol, error: String(error?.message || error) });
      }
      try {
        exDates[member.symbol] = dilutiveExDates(await getFundamentals(member.isin, 'corporate-actions', {}));
      } catch {
        exDates[member.symbol] = new Set();
      }
    }
    // P/B x book, and the promoter share. No independent cap is passed, so
    // sizeForUniverse marks every row unusable as a size, but it still
    // returns the P/B x book product (the check figure here) and the float.
    const sizes = await sizeForUniverse({ members }, { fetchFundamentals: getFundamentals }).catch(() => ({}));
    const pbMarketCaps = {};
    const floats = {};
    for (const [symbol, one] of Object.entries(sizes?.bySymbol || {})) {
      pbMarketCaps[symbol] = one?.marketCap ?? null;
      floats[symbol] = {
        ratio: one?.freeFloatRatio ?? null,
        asOf: one?.lineage?.inputs?.promoter_share?.asOf ?? null,
        reason: one?.freeFloatReason ?? null,
        source: 'Upstox share-holdings',
      };
    }
    // The member's own shareholding pattern, where read, replaces it: the
    // same filing and date as the share count.
    for (const [symbol, one] of Object.entries(file.shares || {})) {
      if (!Number.isFinite(one.promoterPct)) continue;
      floats[symbol] = {
        ratio: Number((1 - one.promoterPct / 100).toFixed(6)),
        asOf: one.promoterAsOf || one.asOf,
        reason: null,
        source: 'BSE shareholding pattern',
      };
    }

    let sectors = {};
    const db = supabaseClient();
    const runId = db ? await latestUniversePassRun(db).catch(() => null) : null;
    if (runId) {
      const { data } = await db.from('ai_enabler_universe_pass').select('symbol, sector')
        .eq('run_id', runId).in('symbol', members.map((one) => one.symbol));
      sectors = Object.fromEntries((data || []).map((row) => [row.symbol, row.sector]));
    }
    // A member the stored pass has no sector for (its profile failed that
    // run, or it was read under a retired ISIN) is asked for directly.
    const sectorFrom = {};
    for (const member of members) {
      if (sectors[member.symbol]) { sectorFrom[member.symbol] = 'universe pass'; continue; }
      try {
        const profile = await getFundamentals(member.isin, 'profile', {});
        const sector = String(profile?.data?.sector || '').trim();
        if (sector) { sectors[member.symbol] = sector; sectorFrom[member.symbol] = 'Upstox profile, live'; }
      } catch {
        // Stays unstated, and the page says so.
      }
    }

    const rows = marketValueRows({ members, shares: file.shares, closes, exDates, pbMarketCaps })
      .map((row) => ({
        ...row,
        sector: canonicalSector(sectors[row.symbol]),
        sectorUpstox: sectors[row.symbol] || null,
        sectorFrom: sectorFrom[row.symbol] || null,
      }));
    // The session the figures are priced at. Before the day's candle is
    // published this is the previous session, not closedThrough.
    const closeDates = [...new Set(rows.map((row) => row.closeDate).filter(Boolean))].sort();
    const body = {
      ok: true,
      formula: 'market value = last close x equity shares outstanding (filed)',
      scope: 'whole-company market value; not the value of any AI business',
      closedThrough,
      closeDate: closeDates.at(-1) || null,
      closeDates,
      sectorSource: runId ? `Upstox profile sector, universe pass ${runId}` : null,
      sectorAliases: SECTOR_ALIASES,
      byLayer: totalsBy(rows, (row) => row.layer),
      bySector: totalsBy(rows, (row) => row.sector),
      rows,
      failures,
    };
    return { body, floats };
  }

  /**
   * Market value of the members, by layer and by sector, at the last closed
   * session: close x filed shares, P/B x book beside it as a check. Sector is
   * Upstox's profile sector, with its duplicate spellings merged. Whole-company
   * value, not AI exposure. Cached for ten minutes, as the history is.
   */
  router.get('/screen/market-value', async (req, res) => {
    try {
      if (!isUpstoxConfigured()) {
        return res.status(503).json({ ok: false, error: 'Upstox is not configured; set UPSTOX_ACCESS_TOKEN server-side.', code: 'UPSTOX_NOT_CONFIGURED' });
      }
      res.json((await marketValue()).body);
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  /**
   * Stage 3 from the checked-in inputs file: every figure carries its source
   * there. Context beside each company; membership is decided by evidence.
   */
  router.get('/screen/stage3', async (req, res) => {
    try {
      const file = JSON.parse(await readFile(INTENSITY_PATH, 'utf8'));
      res.json({ ok: true, ...stageThreeFromInputs(file, { stageThree }) });
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  /**
   * Stage 2 of the screen: size and tradability.
   *
   * Free-float size is close x filed shares x (1 - promoter share), from the
   * same computation as the market-value panel. It replaced P/B x book,
   * which missed the filed-share figure by more than five times for one
   * member and in both directions across six; that route is still returned,
   * under pbBook, for reference and never screened on.
   *
   * No thresholds are applied unless they are passed in (size in crore,
   * turnover in rupees). The distribution is always returned, because a
   * floor chosen without seeing the spread is a floor nobody can defend.
   */
  router.get('/screen/size', async (req, res) => {
    try {
      if (!isUpstoxConfigured()) {
        return res.status(503).json({ ok: false, error: 'Upstox is not configured; set UPSTOX_ACCESS_TOKEN server-side.', code: 'UPSTOX_NOT_CONFIGURED' });
      }
      const universe = await loadUniverse();
      const today = new Date().toISOString().slice(0, 10);
      const from = new Date(Date.now() - 200 * 24 * 3600 * 1000).toISOString().slice(0, 10);

      const [{ body, floats }, liquidity] = await Promise.all([
        marketValue(),
        liquidityForUniverse(universe, { fetchCandles: getHistoricalCandles, to: today, from, sessions: 120 }),
      ]);

      const turnover = Object.fromEntries(Object.entries(liquidity.bySymbol)
        .map(([symbol, one]) => [symbol, one.medianDailyTurnover]));
      const minFreeFloatMarketCap = Number(req.query.minFreeFloatMarketCap) || null;
      const minMedianDailyTurnover = Number(req.query.minMedianDailyTurnover) || null;
      const rows = filedSizeRows(body.rows, { floats, turnover });

      res.json({
        ok: true,
        sizeBasis: 'free-float market value = last close x filed equity shares x (1 - promoter share); crore',
        closeDate: body.closeDate,
        screen: stageTwo(rows, { minFreeFloatMarketCap, minMedianDailyTurnover }),
        rows,
        pbBook: Object.fromEntries(body.rows.map((row) => [row.symbol, row.crossCheck || null])),
        liquidityFailures: liquidity.failures,
      });
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  /**
   * How large a position each member can carry, against the universe policy.
   *
   * Normal turnover is the lower of the 20- and 60-session medians of daily
   * traded value, from Upstox daily candles. A member below the target stays
   * a member; it is listed in belowTarget with its maximum executable size.
   */
  let exitabilityCache = null;
  router.get('/screen/exitability', async (req, res) => {
    try {
      // Cached for ten minutes: the monitor view opens with this column, and
      // each run reads a candle series per member.
      if (exitabilityCache && Date.now() - exitabilityCache.at < 10 * 60_000) return res.json(exitabilityCache.body);
      if (!isUpstoxConfigured()) {
        return res.status(503).json({ ok: false, error: 'Upstox is not configured; set UPSTOX_ACCESS_TOKEN server-side.', code: 'UPSTOX_NOT_CONFIGURED' });
      }
      const universe = await loadUniverse();
      const to = new Date().toISOString().slice(0, 10);
      const from = new Date(Date.now() - 120 * 24 * 3600 * 1000).toISOString().slice(0, 10);
      const body = { ok: true, ...(await exitabilityForUniverse(universe, { fetchCandles: getHistoricalCandles, to, from })) };
      exitabilityCache = { at: Date.now(), body };
      res.json(body);
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  /**
   * Stage 1 over the whole exchange, as the last run stored it.
   *
   * Written by scripts/aiEnablersUniversePass.mjs from the Render shell.
   * Returns the summary and the nominated companies with the words that
   * nominated them and their reading priority; ?all=1 returns every row.
   * The stored description is Upstox's text and is stripped from every row.
   * ?tier=1 narrows the list to one reading tier.
   */
  router.get('/screen/universe-pass', async (req, res) => {
    try {
      const db = supabaseClient();
      if (!db) return res.status(503).json({ ok: false, error: 'Supabase is not configured on this service.' });
      const runId = String(req.query.run || '') || await latestUniversePassRun(db);
      if (!runId) return res.json({ ok: true, run: null, summary: null, rows: [] });
      const rows = await readUniversePass(db, runId);
      const universe = await loadUniverse();
      const reference = referenceQualifiers(universe);
      res.json({
        ok: true,
        run: runId,
        summary: summariseUniversePass(rows, { reference }),
        rows: rows
          .filter((one) => req.query.all || one.disposition === 'NOMINATED')
          .map(publicRow)
          .filter((one) => !req.query.tier || String(one.priority?.tier) === String(req.query.tier)),
      });
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  return router;
}
