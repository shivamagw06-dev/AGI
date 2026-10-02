import { readIndiaTracking } from '../services/indiaPortfolioTracking.js';
import { Router } from 'express';
import { requireStrategyLabAdmin } from '../services/strategyLabAdminAuth.js';
import { createPortfolioStore, validatePortfolio } from '../services/portfolioCatalog.js';
export default function createPortfolioRouter({ store, admin = requireStrategyLabAdmin } = {}) {
  const router = Router();
  const repository = () => store || createPortfolioStore();
  router.get('/', async (_req,res) => {
    try { res.set('Cache-Control', 'no-store').json({ portfolios: await repository().list() }); }
    catch { res.status(503).json({ error: 'Portfolios are temporarily unavailable. Please try again.' }); }
  });
  router.get('/india-tracking', async (_req,res) => {
    try { res.set('Cache-Control','no-store').json(await readIndiaTracking(await repository().list())); }
    catch { res.status(503).json({error:'India tracking is temporarily unavailable. No returns have been estimated.'}); }
  });
  router.put('/:id', admin, async (req,res) => {
    if (!/^[a-z0-9-]{1,100}$/.test(req.params.id)) return res.status(400).json({error:'Invalid portfolio ID.'});
    try { validatePortfolio(req.body); } catch (e) { return res.status(400).json({ error: e.message }); }
    try { res.json({ portfolio: await repository().save(req.params.id, req.body, req.strategyLabActor.id) }); }
    catch(e) { res.status(e.status || 503).json({error: e.status === 409 ? e.message : 'Could not save the portfolio. Your changes have not been published.'}); }
  });
  return router;
}
