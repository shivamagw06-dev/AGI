import { Router } from 'express';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { AiEnablersLiveRuntime } from '../services/aiEnablersLiveRuntime.js';
import { liquidityForUniverse, volumeBaselines } from '../services/aiEnablersLiquidity.js';
import { getHistoricalCandles } from '../providers/upstox.js';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { fundamentalsForUniverse, intensityForUniverse } from '../services/aiEnablersFundamentals.js';
import { stageThree } from '../services/aiEnablersScreen.js';
import { isUpstoxConfigured } from '../providers/upstox.js';

const UNIVERSE_PATH = fileURLToPath(new URL('../config/india-ai-enablers.universe.json', import.meta.url));

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
export async function ensureRuntime({ universe, start = true } = {}) {
  if (runtime) return runtime;
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
  runtime = new AiEnablersLiveRuntime({ universe: loaded, volumeBaselines: baselines });
  if (start) await runtime.start();
  return runtime;
}

export function resetRuntimeForTests() {
  runtime = null;
  universeCache = null;
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
      res.json({ ok: true, snapshots: live.history() });
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

  return router;
}
