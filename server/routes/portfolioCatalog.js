import {portfolioLedger,ledgerView} from '../services/portfolioRebalanceLedger.js';
import { usaHistory } from '../services/usaPortfolioHistory.js';
import { growthMomentumPortfolio, GROWTH_MOMENTUM_ID } from '../services/growthMomentumPortfolio.js';
import { readIndiaTracking } from '../services/indiaPortfolioTracking.js';
import { Router } from 'express';
import { requireStrategyLabAdmin } from '../services/strategyLabAdminAuth.js';
import { createPortfolioStore, validatePortfolio } from '../services/portfolioCatalog.js';
export default function createPortfolioRouter({ store, admin = requireStrategyLabAdmin, readTracking = readIndiaTracking, ledger = portfolioLedger } = {}) {
  const router = Router();
  const repository = () => store || createPortfolioStore();
  const publicRows = rows => rows.filter(p=>p.visibility!=='admin' && p.id!==GROWTH_MOMENTUM_ID);
  router.get('/admin/growth-momentum', admin, async (_req,res) => {
    res.set('Cache-Control','private, no-store');
    try { const rows=publicRows(await repository().list()); const frozen=await ledger().get(GROWTH_MOMENTUM_ID); const portfolio=frozen?.document.portfolio||growthMomentumPortfolio(rows);
      const tracking=await readTracking([...rows.filter(p=>['in-growth','in-momentum'].includes(p.id)),portfolio]);
      if(frozen){const v=ledgerView(frozen);tracking.portfolios=tracking.portfolios.map(p=>p.id===portfolio.id?{...p,...v,markedAt:v.history.at(-1)?.recordedAt}:p);}
      res.json({portfolio,tracking});
    } catch { res.status(503).json({error:'Private portfolio data is temporarily unavailable.'}); }
  });
  router.get('/', async (_req,res) => {
    try { res.set('Cache-Control', 'no-store').json({ portfolios: publicRows(await repository().list()) }); }
    catch { res.status(503).json({ error: 'Portfolios are temporarily unavailable. Please try again.' }); }
  });
  const ledgerAccess=async(req,res,next)=>{
    try{const row=await ledger().get(req.params.id);if(!row)return res.status(404).json({error:'Tracking baseline not ready'});req.ledgerRow=row;
      if(row.document.portfolio.visibility==='admin'||req.params.id===GROWTH_MOMENTUM_ID)return admin(req,res,next);next();
    }catch{res.status(503).json({error:'Portfolio ledger temporarily unavailable'});}
  };
  router.get('/:id/ledger',ledgerAccess,(req,res)=>{res.set('Cache-Control','no-store').json(ledgerView(req.ledgerRow));});
  router.get('/admin/ledger-catalog',admin,async(_req,res)=>{try{res.set('Cache-Control','private, no-store').json({portfolios:(await ledger().list()).map(ledgerView)});}catch{res.status(503).json({error:'Ledger unavailable'});}});
  router.post('/:id/rebalance',admin,async(req,res)=>{try{const row=await ledger().schedule(req.params.id,req.body,req.strategyLabActor.id);res.json(ledgerView(row));}catch(e){res.status(e.status||503).json({error:e.status?e.message:'Unable to schedule rebalance; no changes applied.'});}});
  router.post('/:id/rebalance/cancel',admin,async(req,res)=>{try{const row=await ledger().cancel(req.params.id,req.body.ledgerRevision,req.strategyLabActor.id);res.json(ledgerView(row));}catch(e){res.status(e.status||503).json({error:e.status?e.message:'Unable to cancel rebalance.'});}});
  router.get('/usa-history', async (_req,res) => {
    try { const data=await usaHistory.read(); const ledgers=(await ledger().list()).filter(r=>r.document.portfolio.market==='usa'&&r.document.portfolio.visibility!=='admin').map(ledgerView);res.set('Cache-Control','no-store').json({...data,ledgers}); }
    catch { res.status(503).json({error:'USA price history temporarily unavailable.'}); }
  });
  router.get('/india-tracking', async (_req,res) => {
    try { const data=await readTracking(publicRows(await repository().list()));const ledgerRows=await ledger().list();data.portfolios=data.portfolios.map(p=>{const row=ledgerRows.find(r=>r.portfolio_id===p.id);if(!row)return p;const v=ledgerView(row);return {...p,...v,positions:v.positions.map(h=>({...p.positions.find(x=>x.symbol===h.symbol),...h})),markedAt:v.history.at(-1)?.recordedAt};});res.set('Cache-Control','no-store').json(data); }
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
