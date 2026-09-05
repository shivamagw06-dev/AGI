import { Router } from 'express';
import {
  getInstitutionalAdmin,
  getInstitutionalFund,
  getInstitutionalOverview,
  getInstitutionalStock,
  markInstitutionalAlert,
  refreshInstitutionalFilings,
  saveSecurityMapping,
  updateInstitutionalManager,
} from '../services/institutionalHoldingsService.js';

async function requireAdmin(req, res, next) {
  try {
    const token = String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
    const url = String(process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '').replace(/\/$/, '');
    const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '');
    if (!token || !url || !key) return res.status(401).json({ error: 'Unauthorized' });
    const response = await fetch(`${url}/auth/v1/user`, { headers: { apikey: key, Authorization: `Bearer ${token}` } });
    const user = await response.json();
    const ids = [process.env.ADMIN_ID, process.env.VITE_ADMIN_ID, 'c56e4d07-273c-49c9-86a5-a4445e687ece'].filter(Boolean);
    const emails = [...String(process.env.ADMIN_EMAILS || '').split(','), ...String(process.env.VITE_ADMIN_EMAILS || '').split(',')].map((value) => value.trim().toLowerCase()).filter(Boolean);
    if (!response.ok || (!ids.includes(user.id) && !emails.includes(String(user.email || '').toLowerCase()))) return res.status(403).json({ error: 'Admin access required' });
    req.adminUser = user;
    return next();
  } catch {
    return res.status(401).json({ error: 'Authorization failed' });
  }
}

function sendError(res, error, status = 503) {
  return res.status(status).json({ error: error?.message || 'Institutional Holdings request failed' });
}

export default function createInstitutionalHoldingsRouter() {
  const router = Router();
  router.get('/overview', async (_req, res) => { try { return res.json(await getInstitutionalOverview()); } catch (error) { return sendError(res, error); } });
  router.get('/funds/:slug', async (req, res) => { try { const data = await getInstitutionalFund(req.params.slug); return data ? res.json(data) : res.status(404).json({ error: 'Tracked fund not found' }); } catch (error) { return sendError(res, error); } });
  router.get('/stocks/:key', async (req, res) => { try { const data = await getInstitutionalStock(req.params.key); return data ? res.json(data) : res.status(404).json({ error: 'No tracked fund currently holds this security' }); } catch (error) { return sendError(res, error); } });
  router.get('/admin', requireAdmin, async (_req, res) => { try { return res.json(await getInstitutionalAdmin()); } catch (error) { return sendError(res, error); } });
  router.post('/admin/refresh', requireAdmin, async (req, res) => { try { return res.json(await refreshInstitutionalFilings(req.body || {})); } catch (error) { return sendError(res, error, 400); } });
  router.post('/admin/security-mappings', requireAdmin, async (req, res) => { try { return res.json(await saveSecurityMapping({ ...req.body, actor: req.adminUser?.email || 'admin' })); } catch (error) { return sendError(res, error, 400); } });
  router.patch('/admin/managers/:id', requireAdmin, async (req, res) => { try { return res.json(await updateInstitutionalManager(req.params.id, req.body || {}, req.adminUser?.email || 'admin')); } catch (error) { return sendError(res, error, 400); } });
  router.patch('/admin/alerts/:id', requireAdmin, async (req, res) => { try { return res.json(await markInstitutionalAlert(req.params.id, req.body?.is_read !== false)); } catch (error) { return sendError(res, error, 400); } });
  return router;
}
