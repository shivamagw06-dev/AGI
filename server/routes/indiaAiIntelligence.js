import { Router } from 'express';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { AiEnablersLiveRuntime } from '../services/aiEnablersLiveRuntime.js';
import { liquidityForUniverse, volumeBaselines } from '../services/aiEnablersLiquidity.js';
import { getHistoricalCandles } from '../providers/upstox.js';
import { isUpstoxConfigured } from '../providers/upstox.js';

const UNIVERSE_PATH = fileURLToPath(new URL('../config/india-ai-enablers.universe.json', import.meta.url));

let universeCache = null;
export async function loadUniverse({ path = UNIVERSE_PATH, refresh = false } = {}) {
  if (universeCache && !refresh) return universeCache;
  universeCache = JSON.parse(await readFile(path, 'utf8'));
  return universeCache;
}

let runtime = null;

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

  return router;
}
