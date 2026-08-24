/**
 * AGI Market Intelligence API routes
 * Always returns 200 with data — stale cache or fallback on upstream errors.
 */

import { Router } from 'express';
import { getAgiIntelligence, getDashboardFromIntelligence } from '../services/intelligenceService.js';
import { getDashboardData, getTickerData } from '../services/marketDataService.js';
import { MARKET_REFRESH_MS } from '../config/marketRefresh.js';
import { getGrowwHealth } from '../services/growwHealth.js';
import { getUpstoxCapabilities, getUpstoxHealth } from '../services/upstoxHealth.js';
import { getMarketBriefing, startMarketBriefingScheduler } from '../services/marketBriefingService.js';
import { getMacroBriefing, askMacroEconomist, startMacroBriefingScheduler } from '../services/macroBriefingService.js';
import { getPreMarketBriefing, startPreMarketBriefingScheduler } from '../services/preMarketBriefingService.js';
import { fetchYahooIndices } from '../providers/yahooIndices.js';
import { fetchFxIntelligence } from '../services/fxIntelligenceService.js';

const CACHE_CONTROL = `public, max-age=${Math.floor(MARKET_REFRESH_MS / 1000)}, stale-while-revalidate=60`;

function sendJson(res, data) {
  if (!res.get('Cache-Control')) res.set('Cache-Control', CACHE_CONTROL);
  return res.status(200).json(data);
}

export default function createMarketRouter(env = {}) {
  startMarketBriefingScheduler();
  startMacroBriefingScheduler();
  startPreMarketBriefingScheduler();
  const router = Router();

  router.get('/groww-health', async (_req, res) => {
    const health = await getGrowwHealth();
    return res.status(health.ok ? 200 : 502).json(health);
  });

  // Safe status for Mission Control / ops — no quote payloads, no secrets
  router.get('/groww-status', async (_req, res) => {
    try {
      const health = await getGrowwHealth();
      return res.status(200).json({
        configured: Boolean(health.configured),
        ok: Boolean(health.ok),
        authMode: health.authMode || null,
        passed: health.passed ?? 0,
        total: health.total ?? 0,
        message: health.message || null,
        tests: (health.tests || []).map((t) => ({
          name: t.name,
          ok: Boolean(t.ok),
          error: t.ok ? undefined : t.error,
        })),
        checkedAt: health.checkedAt || new Date().toISOString(),
      });
    } catch (err) {
      return res.status(200).json({
        configured: false,
        ok: false,
        message: err?.message || 'Groww status unavailable',
        checkedAt: new Date().toISOString(),
      });
    }
  });

  router.get('/groww-sector-rotation/status', async (_req, res) => {
    const { getGrowwSectorRotationSchedulerStatus } = await import('../services/growwSectorRotationScheduler.js');
    return res.status(200).json({ ok: true, ...getGrowwSectorRotationSchedulerStatus() });
  });

  router.post('/groww-sector-rotation/run', async (_req, res) => {
    try {
      const { triggerGrowwSectorRotationRun } = await import('../services/growwSectorRotationScheduler.js');
      const result = await triggerGrowwSectorRotationRun({ force: true });
      return res.status(result.ok === false ? 502 : 200).json(result);
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'groww_sector_rotation_run_failed' });
    }
  });

  router.get('/groww-equity-opportunity/status', async (_req, res) => {
    const { getGrowwEquityOpportunitySchedulerStatus } = await import('../services/growwEquityOpportunityScheduler.js');
    return res.status(200).json({ ok: true, ...getGrowwEquityOpportunitySchedulerStatus() });
  });

  router.post('/groww-equity-opportunity/run', async (_req, res) => {
    try {
      const { triggerGrowwEquityOpportunityRun } = await import('../services/growwEquityOpportunityScheduler.js');
      const result = await triggerGrowwEquityOpportunityRun({ force: true });
      return res.status(result.ok === false ? 502 : 200).json(result);
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'groww_equity_opportunity_run_failed' });
    }
  });

  router.get('/upstox-feed/verify', async (_req, res) => {
    try {
      const { authorizeMarketFeed } = await import('../services/upstoxMarketFeedV3.js');
      const url = await authorizeMarketFeed();
      return res.status(200).json({ ok: true, authorized: Boolean(url), checkedAt: new Date().toISOString() });
    } catch (err) {
      return res.status(200).json({
        ok: false,
        authorized: false,
        error: err?.message || 'upstox_feed_verify_failed',
        code: err?.code || null,
        hint: 'Refresh UPSTOX_ACCESS_TOKEN on Render (Upstox developer dashboard daily token).',
        checkedAt: new Date().toISOString(),
      });
    }
  });

  router.post('/upstox-feed/restart', async (_req, res) => {
    try {
      const { restartLiveAlphaRuntime } = await import('../services/liveAlphaRuntime.js');
      const status = await restartLiveAlphaRuntime();
      return res.status(200).json({ ok: true, ...status });
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'upstox_feed_restart_failed' });
    }
  });

  // Operational status only: confirms whether Hedge Fund candidates are being
  // refreshed from Groww without exposing quotes or credentials.
  router.get('/hedge-fund-live-quotes/status', async (_req, res) => {
    const { getHedgeFundLiveQuoteStatus } = await import('../services/hedgeFundLiveQuoteScheduler.js');
    return res.status(200).json({ ok: true, ...getHedgeFundLiveQuoteStatus() });
  });

  router.get('/hedge-fund-terminal-snapshot/status', async (_req, res) => {
    const { getHflTerminalSnapshotSchedulerStatus } = await import('../services/hflTerminalSnapshotScheduler.js');
    return res.status(200).json({ ok: true, ...getHflTerminalSnapshotSchedulerStatus() });
  });

  router.get('/valuation-company-pack/status', async (_req, res) => {
    const { getValuationCompanyPackSchedulerStatus } = await import('../services/valuationCompanyPackScheduler.js');
    return res.status(200).json({ ok: true, ...getValuationCompanyPackSchedulerStatus() });
  });

  router.get('/hedge-fund-upstox-candles/status', async (_req, res) => {
    const { getHedgeFundUpstoxCandleStatus } = await import('../services/hedgeFundUpstoxCandleScheduler.js');
    return res.status(200).json({ ok: true, ...getHedgeFundUpstoxCandleStatus() });
  });

  // Upstox fundamentals probe — corporate-actions pull (no secrets in response)
  router.get('/upstox-status', async (req, res) => {
    try {
      const isin = typeof req.query.isin === 'string' ? req.query.isin : undefined;
      const health = await getUpstoxHealth({ isin });
      return res.status(200).json(health);
    } catch (err) {
      return res.status(200).json({
        provider: 'upstox',
        configured: false,
        ok: false,
        message: err?.message || 'Upstox status unavailable',
        checkedAt: new Date().toISOString(),
      });
    }
  });

  // What Upstox can actually serve for one ISIN — endpoint availability + shapes
  router.get('/upstox-capabilities', async (req, res) => {
    try {
      const isin = typeof req.query.isin === 'string' ? req.query.isin : undefined;
      return res.status(200).json(await getUpstoxCapabilities({ isin }));
    } catch (err) {
      return res.status(200).json({
        provider: 'upstox',
        ok: false,
        message: err?.message || 'Upstox capabilities probe unavailable',
        checkedAt: new Date().toISOString(),
      });
    }
  });

  // Fetch Upstox FII/DII and persist to warehouse via intelligence engine.
  // Prefer the daily EOD scheduler (18:05 IST); this route is admin/manual fallback.
  router.post('/upstox-flows/refresh', async (req, res) => {
    try {
      const { refreshUpstoxInstitutionalFlows } = await import('../services/upstoxFlowRefresh.js');
      const result = await refreshUpstoxInstitutionalFlows({
        dataTypes: req.body?.dataTypes,
        dataType: req.body?.dataType,
        interval: req.body?.interval || '1D',
        from: req.body?.from,
      });
      return res.status(result.status || (result.ok ? 200 : 502)).json(result);
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'upstox_flows_refresh_failed' });
    }
  });

  router.post('/upstox-flows/backfill', async (req, res) => {
    try { const { backfillUpstoxInstitutionalFlows } = await import('../services/upstoxFlowRefresh.js'); const result = await backfillUpstoxInstitutionalFlows({ from: req.body?.from || '2026-04-01', interval: req.body?.interval || '1D', maxWindows: Number(req.body?.maxWindows) || 12 }); return res.status(result.ok ? 200 : 502).json(result); }
    catch (err) { return res.status(502).json({ ok: false, error: err?.message || 'upstox_flows_backfill_failed' }); }
  });

  router.get('/upstox-flows/status', async (_req, res) => {
    try {
      const { getInstitutionalFlowSchedulerStatus } = await import('../services/institutionalFlowScheduler.js');
      return res.status(200).json({
        ok: true,
        scheduler: getInstitutionalFlowSchedulerStatus(),
        note: 'FII/DII is ingested daily after close into warehouse.institutional_flow',
      });
    } catch (err) {
      return res.status(200).json({ ok: false, error: err?.message || 'status_unavailable' });
    }
  });

  // Fill company_master.isin from Upstox NSE EQ instruments (required for key-ratios)
  router.post('/company-isin/backfill', async (req, res) => {
    try {
      const { backfillCompanyIsins } = await import('../services/companyIsinBackfill.js');
      const result = await backfillCompanyIsins({
        dryRun: !!req.body?.dry_run,
        forceNode: !!req.body?.force_node,
      });
      return res.status(result.ok ? 200 : (result.status || 502)).json(result);
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'company_isin_backfill_failed' });
    }
  });

  // Upstox key-ratios → warehouse.valuation_ratios (admin / scheduler)
  router.post('/upstox-valuation-ratios/refresh', async (req, res) => {
    try {
      const { refreshUpstoxValuationRatios } = await import('../services/upstoxValuationRatiosRefresh.js');
      const result = await refreshUpstoxValuationRatios({
        limit: req.body?.limit,
        symbols: req.body?.symbols,
        concurrency: req.body?.concurrency,
        backfillIsins: req.body?.backfill_isins !== false,
      });
      return res.status(result.status || (result.ok ? 200 : 502)).json(result);
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'upstox_valuation_ratios_refresh_failed' });
    }
  });

  router.get('/upstox-valuation-ratios/status', async (_req, res) => {
    try {
      const { getValuationRatiosSchedulerStatus } = await import('../services/valuationRatiosScheduler.js');
      return res.status(200).json({
        ok: true,
        scheduler: getValuationRatiosSchedulerStatus(),
        note: 'Upstox key-ratios ingested daily at 18:15 IST into warehouse.valuation_ratios',
      });
    } catch (err) {
      return res.status(200).json({ ok: false, error: err?.message || 'status_unavailable' });
    }
  });

  // Phase 7.4d — one-shot full-universe Upstox valuation bootstrap
  router.get('/upstox-bootstrap/status', async (_req, res) => {
    try {
      const { getUpstoxBootstrapStatus } = await import('../services/upstoxBootstrapEngine.js');
      return res.status(200).json(getUpstoxBootstrapStatus());
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'bootstrap_status_failed' });
    }
  });

  router.get('/upstox-bootstrap/missing-isin', async (req, res) => {
    try {
      const { getUpstoxBootstrapMissingIsin } = await import('../services/upstoxBootstrapEngine.js');
      return res.status(200).json(getUpstoxBootstrapMissingIsin({
        limit: Number(req.query?.limit) || 500,
      }));
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'missing_isin_failed' });
    }
  });

  router.get('/upstox-bootstrap/failures', async (req, res) => {
    try {
      const { getUpstoxBootstrapFailures } = await import('../services/upstoxBootstrapEngine.js');
      return res.status(200).json(getUpstoxBootstrapFailures({
        limit: Number(req.query?.limit) || 200,
      }));
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'failures_failed' });
    }
  });

  router.post('/upstox-bootstrap/start', async (req, res) => {
    try {
      const { startUpstoxBootstrap } = await import('../services/upstoxBootstrapEngine.js');
      const result = await startUpstoxBootstrap({
        reset: !!req.body?.reset,
        batchSize: req.body?.batchSize ?? req.body?.batch_size,
        concurrency: req.body?.concurrency,
        pauseMs: req.body?.pauseMs ?? req.body?.pause_ms,
      });
      return res.status(result.ok ? 200 : 409).json(result);
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'bootstrap_start_failed' });
    }
  });

  router.post('/upstox-bootstrap/stop', async (_req, res) => {
    try {
      const { stopUpstoxBootstrap } = await import('../services/upstoxBootstrapEngine.js');
      return res.status(200).json(await stopUpstoxBootstrap());
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'bootstrap_stop_failed' });
    }
  });

  router.post('/upstox-bootstrap/reset', async (_req, res) => {
    try {
      const { resetUpstoxBootstrap } = await import('../services/upstoxBootstrapEngine.js');
      const result = await resetUpstoxBootstrap();
      return res.status(result.ok ? 200 : 409).json(result);
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'bootstrap_reset_failed' });
    }
  });

  // ---- Phase 7.4E UIFI — also exposed under /api/upstox/* via alias below ----
  router.post('/upstox/profile/bootstrap', async (req, res) => {
    try {
      const { startUifiBootstrap } = await import('../services/uifiBootstrapEngine.js');
      return res.status(200).json(await startUifiBootstrap({
        dataset: 'profile', reset: !!req.body?.reset,
        batchSize: req.body?.batchSize, concurrency: req.body?.concurrency,
      }));
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'uifi_profile_bootstrap_failed' });
    }
  });
  router.post('/upstox/statements/bootstrap', async (req, res) => {
    try {
      const { startUifiBootstrap } = await import('../services/uifiBootstrapEngine.js');
      return res.status(200).json(await startUifiBootstrap({
        dataset: 'statements', reset: !!req.body?.reset,
        batchSize: req.body?.batchSize, concurrency: req.body?.concurrency,
      }));
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'uifi_statements_bootstrap_failed' });
    }
  });
  router.post('/upstox/shareholding/bootstrap', async (req, res) => {
    try {
      const { startUifiBootstrap } = await import('../services/uifiBootstrapEngine.js');
      return res.status(200).json(await startUifiBootstrap({
        dataset: 'share-holdings', reset: !!req.body?.reset,
        batchSize: req.body?.batchSize, concurrency: req.body?.concurrency,
      }));
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'uifi_shareholding_bootstrap_failed' });
    }
  });
  router.post('/upstox/competitors/bootstrap', async (req, res) => {
    try {
      const { startUifiBootstrap } = await import('../services/uifiBootstrapEngine.js');
      return res.status(200).json(await startUifiBootstrap({
        dataset: 'competitors', reset: !!req.body?.reset,
        batchSize: req.body?.batchSize, concurrency: req.body?.concurrency,
      }));
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'uifi_competitors_bootstrap_failed' });
    }
  });
  router.post('/upstox/corporate-actions/bootstrap', async (req, res) => {
    try {
      const { startUifiBootstrap } = await import('../services/uifiBootstrapEngine.js');
      return res.status(200).json(await startUifiBootstrap({
        dataset: 'corporate-actions', reset: !!req.body?.reset,
        batchSize: req.body?.batchSize, concurrency: req.body?.concurrency,
      }));
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'uifi_ca_bootstrap_failed' });
    }
  });
  router.post('/upstox/bootstrap/start', async (req, res) => {
    try {
      const { startUifiBootstrap } = await import('../services/uifiBootstrapEngine.js');
      return res.status(200).json(await startUifiBootstrap({
        dataset: req.body?.dataset || 'all',
        reset: !!req.body?.reset,
        batchSize: req.body?.batchSize,
        concurrency: req.body?.concurrency,
      }));
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'uifi_bootstrap_start_failed' });
    }
  });
  router.post('/upstox/bootstrap/stop', async (_req, res) => {
    try {
      const { stopUifiBootstrap } = await import('../services/uifiBootstrapEngine.js');
      return res.status(200).json(await stopUifiBootstrap());
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'uifi_bootstrap_stop_failed' });
    }
  });
  router.get('/upstox/bootstrap/status', async (_req, res) => {
    try {
      const { getUifiBootstrapStatus } = await import('../services/uifiBootstrapEngine.js');
      return res.status(200).json(getUifiBootstrapStatus());
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'uifi_bootstrap_status_failed' });
    }
  });
  router.get('/upstox/coverage', async (_req, res) => {
    try {
      const { getUifiCoverage } = await import('../services/upstoxFundamentalsRefresh.js');
      return res.status(200).json(await getUifiCoverage());
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'uifi_coverage_failed' });
    }
  });
  router.get('/upstox/failures', async (_req, res) => {
    try {
      const { getUifiFailures } = await import('../services/upstoxFundamentalsRefresh.js');
      return res.status(200).json(await getUifiFailures());
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'uifi_failures_failed' });
    }
  });
  router.get('/upstox/scheduler', async (_req, res) => {
    try {
      const { getUifiSchedulerStatus } = await import('../services/uifiScheduler.js');
      return res.status(200).json(getUifiSchedulerStatus());
    } catch (err) {
      return res.status(200).json({ ok: false, error: err?.message || 'scheduler_unavailable' });
    }
  });
  router.post('/upstox/refresh', async (req, res) => {
    try {
      const { refreshUpstoxFundamentals } = await import('../services/upstoxFundamentalsRefresh.js');
      const result = await refreshUpstoxFundamentals({
        dataset: req.body?.dataset || 'profile',
        limit: req.body?.limit,
        concurrency: req.body?.concurrency,
        symbols: req.body?.symbols,
        annualOnly: req.body?.annual_only === true || req.body?.annualOnly === true,
      });
      return res.status(result.status || (result.ok ? 200 : 502)).json(result);
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'uifi_refresh_failed' });
    }
  });

  // Read-only operator view: confirms the post-close fundamentals refresh is
  // active without exposing provider credentials or raw responses.
  router.get('/upstox/statements/status', async (_req, res) => {
    const { getUpstoxStatementSchedulerStatus } = await import('../services/upstoxStatementScheduler.js');
    return res.status(200).json({ ok: true, scheduler: getUpstoxStatementSchedulerStatus() });
  });

  // Upstox-first EMPTY statement fill (prefer over Yahoo on Render)
  router.get('/upstox/statements/fill-empty/status', async (_req, res) => {
    try {
      const { getUpstoxEmptyFillStatus } = await import('../services/upstoxEmptyFill.js');
      return res.status(200).json(getUpstoxEmptyFillStatus());
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'upstox_fill_status_failed' });
    }
  });
  router.post('/upstox/statements/fill-empty', async (req, res) => {
    try {
      const { startUpstoxEmptyFill } = await import('../services/upstoxEmptyFill.js');
      return res.status(200).json(await startUpstoxEmptyFill({
        batchSize: req.body?.batch || req.body?.batchSize,
        concurrency: req.body?.concurrency,
        pauseMs: req.body?.pause_ms || req.body?.pauseMs,
        includeThin: req.body?.include_thin !== false,
      }));
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'upstox_fill_start_failed' });
    }
  });
  router.post('/upstox/statements/fill-empty/stop', async (_req, res) => {
    try {
      const { stopUpstoxEmptyFill } = await import('../services/upstoxEmptyFill.js');
      return res.status(200).json(await stopUpstoxEmptyFill());
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'upstox_fill_stop_failed' });
    }
  });
  router.post('/upstox/statements/fill-empty/run', async (req, res) => {
    try {
      const { runUpstoxEmptyFillBatch } = await import('../services/upstoxEmptyFill.js');
      return res.status(200).json(await runUpstoxEmptyFillBatch({
        batchSize: req.body?.batch || req.body?.batchSize || 10,
        symbols: req.body?.symbols,
      }));
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'upstox_fill_run_failed' });
    }
  });

  // Never proxy these to IndianAPI — that path 429s from Render and blanks desks.
  router.get('/overview', async (_req, res) => {
    try {
      const [ticker, dashboard] = await Promise.all([
        getTickerData(env).catch(() => ({ items: [], source: 'unavailable', updatedAt: new Date().toISOString() })),
        getDashboardData(env).catch(() => null),
      ]);
      const items = Array.isArray(ticker?.items) ? ticker.items : [];
      return sendJson(res, {
        ok: true,
        items,
        data: items,
        indices: items,
        gainers: dashboard?.gainers || [],
        losers: dashboard?.losers || [],
        pulse: dashboard?.pulse || null,
        outlook: dashboard?.outlook || null,
        source: ticker?.source || 'groww+nse+yahoo',
        updatedAt: ticker?.updatedAt || new Date().toISOString(),
        stale: items.length === 0,
      });
    } catch (err) {
      console.error('[market/overview]', err?.message || err);
      return sendJson(res, {
        ok: false,
        items: [],
        data: [],
        error: err?.message || 'overview_unavailable',
        stale: true,
        updatedAt: new Date().toISOString(),
      });
    }
  });

  router.get('/global-snapshot', async (_req, res) => {
    try {
      const wanted = ['NASDAQ', 'S&P', 'Dow', 'Gold', 'Silver', 'Brent', 'Bitcoin', 'USDINR'];
      const rows = await fetchYahooIndices(wanted).catch(() => []);
      return sendJson(res, {
        ok: true,
        items: rows,
        data: rows,
        source: 'yahoo',
        updatedAt: new Date().toISOString(),
        stale: rows.length === 0,
      });
    } catch (err) {
      console.error('[market/global-snapshot]', err?.message || err);
      return sendJson(res, {
        ok: false,
        items: [],
        data: [],
        error: err?.message || 'global_snapshot_unavailable',
        stale: true,
        updatedAt: new Date().toISOString(),
      });
    }
  });

  router.get('/fx-intelligence', async (_req, res) => {
    try {
      const data = await fetchFxIntelligence();
      res.set('Cache-Control', 'public, max-age=30, stale-while-revalidate=30');
      return sendJson(res, data);
    } catch (err) {
      console.error('[market/fx-intelligence]', err?.message || err);
      res.set('Cache-Control', 'public, max-age=15, stale-while-revalidate=15');
      return sendJson(res, {
        ok: false,
        pairs: [],
        drivers: [],
        strength: { d1: [], w1: [], m1: [] },
        error: err?.message || 'fx_reference_unavailable',
        delayed: true,
        asOf: new Date().toISOString(),
      });
    }
  });

  router.get('/intelligence', async (_req, res) => {
    // Warm Groww/NSE ticker in the same 30-min cycle as AGI outlook.
    void getTickerData(env).catch(() => null);
    const data = await getAgiIntelligence(env);
    return sendJson(res, data);
  });

  router.get('/dashboard', async (_req, res) => {
    try {
      const data = await getDashboardFromIntelligence(env);
      return sendJson(res, data);
    } catch (err) {
      console.error('[market/dashboard]', err?.message);
      const fallback = await getAgiIntelligence(env);
      return sendJson(res, {
        pulse: fallback.pulse,
        outlook: fallback.outlook,
        gainers: fallback.stocksInFocus?.filter((s) => s.trend === 'Bullish') || [],
        losers: [],
        breadth: fallback.breadth,
        stocksInFocus: fallback.stocksInFocus || [],
        sectors: fallback.sectors || [],
        summary: fallback.summary,
        insightStrip: fallback.insightStrip,
        stale: true,
      });
    }
  });

  router.get('/pulse', async (_req, res) => {
    const data = await getAgiIntelligence(env);
    return sendJson(res, { pulse: data.pulse, outlook: data.outlook, summary: data.summary });
  });

  router.get('/ticker', async (_req, res) => {
    const data = await getAgiIntelligence(env);
    return sendJson(res, {
      items: data.insightStrip || [],
      source: data.source || 'agi-intelligence',
      disclaimer: data.disclaimer,
      updatedAt: data.updatedAt,
      stale: data.stale || false,
    });
  });

  router.get('/briefing', async (_req, res) => {
    const data = await getMarketBriefing();
    res.set('Cache-Control', 'public, max-age=60, stale-while-revalidate=300');
    return res.status(200).json(data);
  });

  router.get('/macro-briefing', async (_req, res) => {
    const data = await getMacroBriefing();
    res.set('Cache-Control', 'public, max-age=300, stale-while-revalidate=1800');
    return res.status(200).json(data);
  });

  router.post('/macro-ask', async (req, res) => {
    try {
      const data = await askMacroEconomist(req.body?.query || req.body?.question || '');
      res.set('Cache-Control', 'no-store');
      return res.status(200).json(data);
    } catch (error) {
      const status = error.status || 500;
      return res.status(status).json({ error: error.message || 'Macro ask failed' });
    }
  });

  router.get('/pre-market-briefing', async (_req, res) => {
    const data = await getPreMarketBriefing();
    res.set('Cache-Control', 'public, max-age=120, stale-while-revalidate=600');
    return res.status(200).json(data);
  });

  // Live Alpha / Upstox V3 market-data feed ops (research-only; no order placement).
  router.get('/upstox-feed/verify', async (_req, res) => {
    try {
      const { authorizeMarketFeed } = await import('../services/upstoxMarketFeedV3.js');
      const url = await authorizeMarketFeed();
      return res.status(200).json({ ok: true, authorized: Boolean(url), checkedAt: new Date().toISOString() });
    } catch (err) {
      return res.status(200).json({
        ok: false,
        authorized: false,
        error: err?.message || 'upstox_feed_verify_failed',
        code: err?.code || null,
        hint: 'Refresh UPSTOX_ACCESS_TOKEN on Render (Upstox developer dashboard daily token).',
        checkedAt: new Date().toISOString(),
      });
    }
  });

  router.post('/upstox-feed/restart', async (_req, res) => {
    try {
      const { restartLiveAlphaRuntime } = await import('../services/liveAlphaRuntime.js');
      const status = await restartLiveAlphaRuntime();
      return res.status(200).json({ ok: true, ...status });
    } catch (err) {
      return res.status(502).json({ ok: false, error: err?.message || 'upstox_feed_restart_failed' });
    }
  });

  router.get('/live-alpha/status', async (_req, res) => {
    try {
      const { getLiveAlphaRuntimeStatus } = await import('../services/liveAlphaRuntime.js');
      return res.status(200).json({ ok: true, ...getLiveAlphaRuntimeStatus() });
    } catch (err) {
      return res.status(200).json({ ok: false, error: err?.message || 'live_alpha_status_unavailable' });
    }
  });

  return router;
}
