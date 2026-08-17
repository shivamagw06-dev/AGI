import { Router } from 'express';
import { getPeFirm, getPeOverview, getPeOpportunities, getPeInvestors, getPeInvestor, getPeIntelligence, listPeFirms } from '../services/peIntelligenceService.js';

export default function createPeIntelligenceRouter() {
  const router = Router();

  router.get('/overview', async (req, res) => {
    try {
      return res.json(await getPeOverview({ sector: req.query.sector || null, scope: req.query.scope || 'core', search: req.query.search || '', limit: req.query.limit || 500 }));
    } catch (error) {
      console.error('[pe-intelligence] overview failed', error);
      return res.status(503).json({ error: 'Private Markets evidence is temporarily unavailable.' });
    }
  });

  router.get('/firms', (_req, res) => {
    return res.json({ firms: listPeFirms() });
  });
  router.get('/opportunities', async (req,res)=>{try{return res.json(await getPeOpportunities(req.query))}catch(error){return res.status(503).json({error:error.message})}});
  router.get('/investors', async (req,res)=>{try{return res.json(await getPeInvestors(req.query))}catch(error){return res.status(503).json({error:error.message})}});
  router.get('/investors/:id', async (req,res)=>{try{const row=await getPeInvestor(req.params.id);return row?res.json(row):res.status(404).json({error:'Investor not found'})}catch(error){return res.status(503).json({error:error.message})}});
  router.get('/intelligence', async (_req,res)=>{try{return res.json(await getPeIntelligence())}catch(error){return res.status(503).json({error:error.message})}});

  router.get('/firms/:slug', (req, res) => {
    const firm = getPeFirm(req.params.slug);
    if (!firm) return res.status(404).json({ error: 'Firm not found' });
    return res.json(firm);
  });

  return router;
}
