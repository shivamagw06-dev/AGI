import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import { getWealthEquityResearch, getWealthEvidence } from '../services/wealthResearch.js';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { getWealthUniverse } from '../services/wealthIntelligence.js';

async function verifyUser(token) {
  const client = createSupabaseAdmin();
  if (!client) throw new Error('Authentication unavailable');
  const { data, error } = await client.auth.getUser(token);
  if (error) return null;
  return data?.user || null;
}

export default function createWealthIntelligenceRouter({ authenticate = verifyUser, getUniverse = getWealthUniverse, getResearch = getWealthEquityResearch, getEvidence = getWealthEvidence } = {}) {
  const router = Router();
  router.use(async (req, res, next) => {
    res.set('Cache-Control', 'private, no-store');
    const match = /^Bearer\s+(\S+)$/i.exec(req.headers.authorization || '');
    if (!match) return res.status(401).json({ error: 'Sign in to view Wealth Intelligence.' });
    try {
      const user = await authenticate(match[1]);
      if (!user?.id || user.is_anonymous) return res.status(401).json({ error: 'Your session has expired. Sign in again.' });
      return next();
    } catch {
      return res.status(503).json({ error: 'Authentication is temporarily unavailable.' });
    }
  });
  router.use(rateLimit({ windowMs: 60000, max: 120, standardHeaders: true, legacyHeaders: false }));
  router.get('/research/:symbol', async (req, res) => {
    const symbol = req.params.symbol;
    if (!/^[A-Z0-9&_.-]{1,30}$/.test(symbol)) return res.status(400).json({ error: 'Invalid equity symbol.' });
    try { return res.json(await getResearch(symbol)); } catch { return res.status(503).json({error:'Company research is temporarily unavailable.'}); }
  });
  router.get('/evidence', async (_req, res) => {
    try { return res.json(await getEvidence()); } catch { return res.status(503).json({error:'Evidence feed is temporarily unavailable.'}); }
  });
  router.get('/universe', async (req, res) => {
    const { assetClass = 'equity', q = '', offset = '0', limit = '50' } = req.query;
    if (!['equity', 'mutual_fund'].includes(assetClass) || typeof q !== 'string' || q.length > 120
      || !/^\d+$/.test(String(offset)) || !/^\d+$/.test(String(limit))
      || Number(limit) < 1 || Number(limit) > 100 || Number(offset) > 100000) {
      return res.status(400).json({ error: 'Invalid search, asset class or pagination.' });
    }
    try { return res.json(await getUniverse({ assetClass, q, offset: Number(offset), limit: Number(limit) })); }
    catch { return res.status(503).json({ error: 'Investment data is temporarily unavailable. Try again.' }); }
  });
  return router;
}
