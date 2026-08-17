import { Router } from 'express';
import { getPeFirm, getPeOverview, listPeFirms } from '../services/peIntelligenceService.js';

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

  router.get('/firms/:slug', (req, res) => {
    const firm = getPeFirm(req.params.slug);
    if (!firm) return res.status(404).json({ error: 'Firm not found' });
    return res.json(firm);
  });

  return router;
}
