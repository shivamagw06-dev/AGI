import { Router } from 'express';
import { requireStrategyLabAdmin } from '../services/strategyLabAdminAuth.js';
import {
  latestLowPeSnapshot,
  parseLowPeTables,
  publishLowPeSnapshot,
  validateAsOf,
} from '../services/manualLowPeScreener.js';

export default function createManualScreenersRouter() {
  const router = Router();

  router.get('/low-pe', async (_req, res) => {
    try {
      const snapshot = await latestLowPeSnapshot();
      res.set('Cache-Control', 'no-store');
      return res.json({ snapshot });
    } catch (error) {
      console.error('[manual-low-pe] read:', error.message);
      return res.status(503).json({ error: 'The screener is temporarily unavailable.' });
    }
  });

  router.post('/low-pe/preview', requireStrategyLabAdmin, (req, res) => {
    try {
      const asOf = validateAsOf(req.body?.asOf);
      const rows = parseLowPeTables(req.body?.tables);
      return res.json({ asOf, rowCount: rows.length, rows });
    } catch (error) {
      return res.status(400).json({ error: error.message });
    }
  });

  router.post('/low-pe/publish', requireStrategyLabAdmin, async (req, res) => {
    try {
      const asOf = validateAsOf(req.body?.asOf);
      const rows = parseLowPeTables(req.body?.tables);
      const snapshot = await publishLowPeSnapshot({ asOf, rows, actorId: req.strategyLabActor.id });
      return res.json({ snapshot });
    } catch (error) {
      if (/^(Choose|Paste|Table|Row|Duplicate|No stock|A publication)/.test(error.message)) {
        return res.status(400).json({ error: error.message });
      }
      console.error('[manual-low-pe] publish:', error.message);
      return res.status(503).json({ error: 'The screener could not be published. Try again.' });
    }
  });

  return router;
}
