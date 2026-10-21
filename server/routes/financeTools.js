import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import { requireStrategyLabAdmin } from '../services/strategyLabAdminAuth.js';

export async function verifyToolsMember(req, res, next) {
  const token = /^Bearer\s+(\S+)$/i.exec(req.get('authorization') || '')?.[1];
  if (!token) return res.status(401).json({ error: 'Sign in to submit your company.' });
  const url = (process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '').replace(/\/$/, '');
  const key = process.env.SUPABASE_ANON_KEY || process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return res.status(503).json({ error: 'Account verification unavailable.' });
  try {
    const response = await fetch(`${url}/auth/v1/user`, { headers: { apikey: key, Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(10000) });
    if (!response.ok) return res.status(401).json({ error: 'Please sign in again.' });
    const user = await response.json();
    if (!user.id || user.is_anonymous || !user.email_confirmed_at) return res.status(403).json({ error: 'A verified email account is required.' });
    req.toolsMember = { id: user.id, email: user.email };
    next();
  } catch { return res.status(503).json({ error: 'Account verification unavailable.' }); }
}

export default function financeTools(engineFetch, { member = verifyToolsMember, admin = requireStrategyLabAdmin } = {}) {
  const router = Router();
  router.use((req, res, next) => { res.set('Cache-Control', 'no-store'); next(); });
  // No client or admin input can manufacture a paid placement. Gateway activation is a separate release.
  router.get('/board', (req, res) => res.json({ ok: true, checkoutEnabled: false, listings: [], currency: 'INR' }));
  const proxy = async (res, path, options) => {
    try {
      const r = await engineFetch(path, options);
      res.status(r.status).json(r.data);
    } catch { res.status(503).json({ error: 'Submissions are temporarily unavailable. Please try again.' }); }
  };
  router.post('/applications', rateLimit({ windowMs: 60000, max: 5, standardHeaders: true, legacyHeaders: false }), member, (req, res) => {
    if (JSON.stringify(req.body || {}).length > 4000) return res.status(413).json({ error: 'Submission too large.' });
    const { name, url, description, category, budget, authorized } = req.body || {};
    return proxy(res, '/v1/finance-tools/applications', { method: 'POST', body: { name, url, description, category, budget, authorized, owner: req.toolsMember.id, email: req.toolsMember.email } });
  });
  router.get('/mine', member, (req, res) => proxy(res, `/v1/finance-tools/applications?owner=${encodeURIComponent(req.toolsMember.id)}`));
  router.get('/admin', admin, (req, res) => proxy(res, '/v1/finance-tools/applications'));
  router.patch('/admin/:id', admin, (req, res) => {
    if (!/^[a-f0-9-]{36}$/.test(req.params.id)) return res.status(400).json({ error: 'Invalid application.' });
    return proxy(res, `/v1/finance-tools/applications/${req.params.id}`, { method: 'PATCH', body: { status: req.body?.status, actor: req.strategyLabActor.id } });
  });
  return router;
}
