import { Router } from 'express';
import { requireStrategyLabAdmin } from '../services/strategyLabAdminAuth.js';
import {
  latestLowPeSnapshot,
  parseLowPeTables,
  publishLowPeSnapshot,
  validateAsOf,
} from '../services/manualLowPeScreener.js';
import {
  latestPromoterSnapshot,
  parsePromoterTables,
  publishPromoterSnapshot,
} from '../services/manualPromoterScreener.js';
import {
  latestPiotroskiSnapshot,
  parsePiotroskiTables,
  publishPiotroskiSnapshot,
} from '../services/manualPiotroskiScreener.js';

import { latestCashFlowSnapshot, parseCashFlowTables, publishCashFlowSnapshot } from '../services/manualCashFlowScreener.js';

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

  router.get('/promoter-holdings', async (_req, res) => {
    try {
      const snapshot = await latestPromoterSnapshot();
      res.set('Cache-Control', 'no-store');
      return res.json({ snapshot });
    } catch (error) {
      console.error('[manual-promoter] read:', error.message);
      return res.status(503).json({ error: 'The screener is temporarily unavailable.' });
    }
  });

  router.post('/promoter-holdings/preview', requireStrategyLabAdmin, (req, res) => {
    try {
      const asOf = validateAsOf(req.body?.asOf);
      const rows = parsePromoterTables(req.body?.tables, asOf);
      return res.json({ asOf, rowCount: rows.length, rows });
    } catch (error) {
      return res.status(400).json({ error: error.message });
    }
  });

  router.post('/promoter-holdings/publish', requireStrategyLabAdmin, async (req, res) => {
    try {
      const asOf = validateAsOf(req.body?.asOf);
      const rows = parsePromoterTables(req.body?.tables, asOf);
      const snapshot = await publishPromoterSnapshot({ asOf, rows, actorId: req.strategyLabActor.id });
      return res.json({ snapshot });
    } catch (error) {
      if (/^(Choose|Paste|Table|Row|Duplicate|No stock|A publication)/.test(error.message)) {
        return res.status(400).json({ error: error.message });
      }
      console.error('[manual-promoter] publish:', error.message);
      return res.status(503).json({ error: 'The screener could not be published. Try again.' });
    }
  });

  router.get('/piotroski', async (_req, res) => {
    try {
      const snapshot = await latestPiotroskiSnapshot();
      res.set('Cache-Control', 'no-store');
      return res.json({ snapshot });
    } catch (error) {
      console.error('[manual-piotroski] read:', error.message);
      return res.status(503).json({ error: 'The screener is temporarily unavailable.' });
    }
  });

  router.post('/piotroski/preview', requireStrategyLabAdmin, (req, res) => {
    try {
      const asOf = validateAsOf(req.body?.asOf);
      const rows = parsePiotroskiTables(req.body?.tables);
      return res.json({ asOf, rowCount: rows.length, rows });
    } catch (error) {
      return res.status(400).json({ error: error.message });
    }
  });

  router.post('/piotroski/publish', requireStrategyLabAdmin, async (req, res) => {
    try {
      const asOf = validateAsOf(req.body?.asOf);
      const rows = parsePiotroskiTables(req.body?.tables);
      const snapshot = await publishPiotroskiSnapshot({ asOf, rows, actorId: req.strategyLabActor.id });
      return res.json({ snapshot });
    } catch (error) {
      if (/^(Choose|Paste|Table|Row|Duplicate|No stock|A publication)/.test(error.message)) {
        return res.status(400).json({ error: error.message });
      }
      console.error('[manual-piotroski] publish:', error.message);
      return res.status(503).json({ error: 'The screener could not be published. Try again.' });
    }
  });

  router.get('/cash-flow', async (_req, res) => {
    try {
      const snapshot = await latestCashFlowSnapshot();
      res.set('Cache-Control', 'no-store');
      return res.json({ snapshot });
    } catch (error) {
      console.error('[manual-cash-flow] read:', error.message);
      return res.status(503).json({ error: 'The screener is temporarily unavailable.' });
    }
  });

  router.post('/cash-flow/preview', requireStrategyLabAdmin, (req, res) => {
    try {
      const asOf = validateAsOf(req.body?.asOf);
      const rows = parseCashFlowTables(req.body?.tables);
      return res.json({ asOf, rowCount: rows.length, rows });
    } catch (error) {
      return res.status(400).json({ error: error.message });
    }
  });

  router.post('/cash-flow/publish', requireStrategyLabAdmin, async (req, res) => {
    try {
      const asOf = validateAsOf(req.body?.asOf);
      const rows = parseCashFlowTables(req.body?.tables);
      const snapshot = await publishCashFlowSnapshot({ asOf, rows, actorId: req.strategyLabActor.id });
      return res.json({ snapshot });
    } catch (error) {
      if (/^(Choose|Paste|Table|Row|Duplicate|No stock|A publication)/.test(error.message)) {
        return res.status(400).json({ error: error.message });
      }
      console.error('[manual-cash-flow] publish:', error.message);
      return res.status(503).json({ error: 'The screener could not be published. Try again.' });
    }
  });

  return router;
}
