import { usaHistory } from '../services/usaPortfolioHistory.js';
import { growthMomentumPortfolio, GROWTH_MOMENTUM_ID } from '../services/growthMomentumPortfolio.js';
import { readIndiaTracking } from '../services/indiaPortfolioTracking.js';
import { Router } from 'express';
import { requireStrategyLabAdmin } from '../services/strategyLabAdminAuth.js';
import { createPortfolioStore, validatePortfolio } from '../services/portfolioCatalog.js';
export default function createPortfolioRouter({ store, admin = requireStrategyLabAdmin, readTracking = readIndiaTracking } = {}) {
  const router = Router();
  const repository = () => store || createPortfolioStore();
  const publicRows = rows => rows.filter(p=>p.visibility!=='admin' && p.id!==GROWTH_MOMENTUM_ID);
  router.get('/admin/growth-momentum', admin, async (_req,res) => {
    res.set('Cache-Control','private, no-store');
    try { const rows=publicRows(await repository().list()); const portfolio=growthMomentumPortfolio(rows);
      const tracking=await readTracking([...rows.filter(p=>['in-growth','in-momentum'].includes(p.id)),portfolio]);
      res.json({portfolio,tracking});
    } catch { res.status(503).json({error:'Private portfolio data is temporarily unavailable.'}); }
  });
  router.get('/', async (_req,res) => {
    try { res.set('Cache-Control', 'no-store').json({ portfolios: publicRows(await repository().list()) }); }
    catch { res.status(503).json({ error: 'Portfolios are temporarily unavailable. Please try again.' }); }
  });
  router.get('/usa-history', async (_req,res) => {
    try { res.set('Cache-Control','no-store').json(await usaHistory.read()); }
    catch { res.status(503).json({error:'USA price history temporarily unavailable.'}); }
  });
  router.get('/india-tracking', async (_req,res) => {
    try { res.set('Cache-Control','no-store').json(await readTracking(publicRows(await repository().list()))); }
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
