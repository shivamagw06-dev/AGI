import { Router } from 'express';
import {
  listRebalanceEvents, getRebalanceEvent, previewPaste, publishRebalance,
} from '../services/indexRebalanceService.js';

/**
 * Index rebalance events.
 *
 * Reads are behind sign-in and writes behind admin, deliberately. The flow
 * estimates on these rows are third-party model output, attributed but not
 * ours to republish openly, and everything here is written for clients rather
 * than for search engines.
 */
async function authenticate(req) {
  const token = String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
  const url = String(process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '').replace(/\/$/, '');
  const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '');
  if (!token || !url || !key) return null;
  const response = await fetch(`${url}/auth/v1/user`, { headers: { apikey: key, Authorization: `Bearer ${token}` } });
  if (!response.ok) return null;
  return response.json();
}

async function requireUser(req, res, next) {
  try {
    const user = await authenticate(req);
    if (!user?.id) return res.status(401).json({ error: 'Sign in to view index rebalance research.' });
    req.user = user;
    return next();
  } catch {
    return res.status(401).json({ error: 'Authorization failed' });
  }
}

async function requireAdmin(req, res, next) {
  try {
    const user = await authenticate(req);
    const ids = [process.env.ADMIN_ID, process.env.VITE_ADMIN_ID, 'c56e4d07-273c-49c9-86a5-a4445e687ece'].filter(Boolean);
    const emails = [...String(process.env.ADMIN_EMAILS || '').split(','), ...String(process.env.VITE_ADMIN_EMAILS || '').split(',')]
      .map((value) => value.trim().toLowerCase()).filter(Boolean);
    if (!user?.id || (!ids.includes(user.id) && !emails.includes(String(user.email || '').toLowerCase()))) {
      return res.status(403).json({ error: 'Admin access required' });
    }
    req.user = user;
    return next();
  } catch {
    return res.status(401).json({ error: 'Authorization failed' });
  }
}

const fail = (res, error) => res.status(500).json({ error: error.message || 'Request failed' });

export default function createIndexRebalanceRouter() {
  const router = Router();

  router.get('/', requireUser, async (_req, res) => {
    try { res.json({ events: await listRebalanceEvents() }); } catch (error) { fail(res, error); }
  });

  router.get('/:eventId', requireUser, async (req, res) => {
    try {
      const payload = await getRebalanceEvent(req.params.eventId);
      if (!payload) return res.status(404).json({ error: 'That rebalance event was not found.' });
      res.json(payload);
    } catch (error) { fail(res, error); }
  });

  // Parses without writing, so the operator confirms what was understood
  // before anything is stored. The rejected rows come back too - a parser that
  // silently drops eight of twenty-five names looks like it worked.
  router.post('/preview', requireAdmin, async (req, res) => {
    try { res.json(previewPaste(String(req.body?.text || ''))); } catch (error) { fail(res, error); }
  });

  router.post('/publish', requireAdmin, async (req, res) => {
    try {
      const event = req.body?.event || {};
      if (!event.provider || !event.index_name || !event.announced_on) {
        return res.status(400).json({ error: 'provider, index_name and announced_on are required.' });
      }
      res.json(await publishRebalance({ event, text: String(req.body?.text || '') }));
    } catch (error) { fail(res, error); }
  });

  return router;
}
