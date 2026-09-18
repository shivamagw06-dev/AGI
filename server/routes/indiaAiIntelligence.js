import { Router } from 'express';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { AiEnablersLiveRuntime } from '../services/aiEnablersLiveRuntime.js';
import { liquidityForUniverse, volumeBaselines } from '../services/aiEnablersLiquidity.js';
import {
  getFundamentals, getHistoricalCandles, getIntradayCandles, isUpstoxConfigured,
} from '../providers/upstox.js';
import { fetchMarketCaps } from '../providers/yahooMarketCap.js';
import { sizeForUniverse, sizeRows } from '../services/aiEnablersSize.js';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { fundamentalsForUniverse, intensityForUniverse } from '../services/aiEnablersFundamentals.js';
import { stageThree, stageTwo } from '../services/aiEnablersScreen.js';

const UNIVERSE_PATH = fileURLToPath(new URL('../config/india-ai-enablers.universe.json', import.meta.url));
const FACTS_PATH = fileURLToPath(new URL('../config/india-ai-enablers.disclosed-facts.json', import.meta.url));

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
      });
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
   * Stage 2 of the screen: size and tradability.
   *
   * Free-float market cap is derived from Upstox P/B and book equity and
   * cross-checked against Yahoo. A member whose two figures disagree is
   * reported unscreened rather than screened on a number nobody verified -
   * which is what happens to a holding company, whose standalone book is the
   * wrong basis for a consolidated P/B.
   *
   * No thresholds are applied unless they are passed in. The distribution is
   * always returned, because a floor chosen without seeing the spread is a
   * floor nobody can defend.
   */
  router.get('/screen/size', async (req, res) => {
    try {
      if (!isUpstoxConfigured()) {
        return res.status(503).json({ ok: false, error: 'Upstox is not configured; set UPSTOX_ACCESS_TOKEN server-side.', code: 'UPSTOX_NOT_CONFIGURED' });
      }
      const universe = await loadUniverse();
      const today = new Date().toISOString().slice(0, 10);
      const from = new Date(Date.now() - 200 * 24 * 3600 * 1000).toISOString().slice(0, 10);

      const [sizes, liquidity] = await Promise.all([
        sizeForUniverse(universe, { fetchFundamentals: getFundamentals, fetchMarketCaps, crossCheckSource: 'yahoo' }),
        liquidityForUniverse(universe, { fetchCandles: getHistoricalCandles, to: today, from, sessions: 120 }),
      ]);

      const turnover = Object.fromEntries(Object.entries(liquidity.bySymbol)
        .map(([symbol, one]) => [symbol, one.medianDailyTurnover]));
      const minFreeFloatMarketCap = Number(req.query.minFreeFloatMarketCap) || null;
      const minMedianDailyTurnover = Number(req.query.minMedianDailyTurnover) || null;

      res.json({
        ok: true,
        screen: stageTwo(sizeRows(sizes, turnover), { minFreeFloatMarketCap, minMedianDailyTurnover }),
        sizes,
        liquidityFailures: liquidity.failures,
      });
    } catch (error) {
      res.status(500).json({ ok: false, error: String(error?.message || error) });
    }
  });

  return router;
}
