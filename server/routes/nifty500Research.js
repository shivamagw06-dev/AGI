import { Router } from 'express';
import {
  getResearchSummary,
  getResearchUniverse,
  getStockResearch,
  searchResearchSymbols,
} from '../services/nifty500ResearchService.js';
import { getNseScreenerUniverse } from '../services/nseScreenerService.js';
import { getNseScreenerSchedulerStatus } from '../services/nseScreenerScheduler.js';

const CACHE_CONTROL = 'public, max-age=1800, stale-while-revalidate=300';

function sendError(res, error) {
  if (error?.code === 'RESEARCH_NOT_CONFIGURED') {
    return res.status(503).json({
      error: 'Nifty 500 research is not available yet.',
      code: error.code,
    });
  }
  console.error('[nifty500-research]', error?.message || error);
  return res.status(502).json({ error: 'Unable to load Nifty 500 research.' });
}

export default function createNifty500ResearchRouter() {
  const router = Router();

  async function summaryHandler(_req, res) {
    try {
      const data = await getResearchSummary();
      res.set('Cache-Control', CACHE_CONTROL);
      return res.json(data || { run: null, topBullish: [], topBearish: [], neutralWatchlist: [] });
    } catch (error) {
      return sendError(res, error);
    }
  }

  // Root used to 503 via the IndianAPI wildcard; serve summary instead.
  router.get('/', summaryHandler);
  router.get('/summary', summaryHandler);

  router.get('/screeners', async (_req, res) => {
    try {
      const data = await getResearchUniverse();
      res.set('Cache-Control', CACHE_CONTROL);
      return res.json(data);
    } catch (error) {
      return sendError(res, error);
    }
  });

  router.get('/screeners/nse', async (_req, res) => {
    try {
      const data = await getNseScreenerUniverse();
      res.set('Cache-Control', 'public, max-age=60, stale-while-revalidate=60');
      return res.json({ ...data, dailyRefresh: getNseScreenerSchedulerStatus() });
    } catch (error) {
      console.error('[nse-screeners]', error?.message || error);
      return res.status(502).json({ error: 'Unable to load the NSE equity list.' });
    }
  });

  router.get('/search', async (req, res) => {
    try {
      const data = await searchResearchSymbols(req.query.q);
      res.set('Cache-Control', CACHE_CONTROL);
      return res.json(data);
    } catch (error) {
      return sendError(res, error);
    }
  });

  router.get('/stocks/:symbol', async (req, res) => {
    try {
      const data = await getStockResearch(req.params.symbol);
      if (!data.research) return res.status(404).json({ error: 'Research record not found.' });
      res.set('Cache-Control', CACHE_CONTROL);
      return res.json(data);
    } catch (error) {
      return sendError(res, error);
    }
  });

  return router;
}
