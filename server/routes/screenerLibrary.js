import { Router } from 'express';
import { createScreenerLibraryStore, libraryDefinition, libraryImport, inputError } from '../services/screenerLibrary.js';
import { createPlusService, plusAdmin, membershipActive } from '../services/agiPlus.js';
export default function createScreenerLibraryRouter({ store = createScreenerLibraryStore(), billing = createPlusService() } = {}) {
  const router = Router();
  router.use((_req, res, next) => { res.set('Cache-Control', 'private, no-store'); next(); });
  let cached = null, expires = 0, inflight;
  const invalidate = () => { cached = null; expires = 0; };
  const fail = (res, error) => res.status(error.status || (error.code === '23505' ? 409 : 503)).json({ error: error.status ? error.message : error.code === '23505' ? 'That screener URL already exists. Choose another name.' : 'Screener service unavailable. Please retry; your saved snapshots are unchanged.' });
  const auth = admin => async (req, res, next) => {
    const token = String(req.get('authorization') || '').match(/^Bearer\s+(.+)$/i)?.[1];
    if (!token) return res.status(401).json({ error: 'Sign in to view screener results.' });
    let user; try { user = await billing.user(token); } catch { return res.status(401).json({ error: 'Your session could not be verified. Please sign in again.' }); }
    req.libraryUser = user;
    if (plusAdmin(user)) return next();
    if (admin) return res.status(403).json({ error: 'Admin access required.' });
    try {
      const [config, membership] = await Promise.all([billing.config(), billing.membership(user.id)]);
      if (config.enabled && !membershipActive(membership)) return res.status(402).json({ error: 'An active AGI Plus membership is required for screener results.' });
      return next();
    } catch (error) { return fail(res, error); }
  };
  router.get('/', async (_req, res) => {
    try {
      if (!cached || expires < Date.now()) {
        if (!inflight) inflight = store.catalogue().then(data => { cached = data; expires = Date.now() + 30000; return data; }).finally(() => { inflight = null; });
        await inflight;
      }
      return res.json({ screens: cached });
    } catch (error) { return fail(res, error); }
  });
  router.get('/admin/catalogue', auth(true), async (_req, res) => {
    try { const screens = await store.catalogue(); cached = screens; expires = Date.now() + 30000; return res.json({ screens }); } catch (error) { return fail(res, error); }
  });
  router.post('/', auth(true), async (req, res) => {
    try { const data = libraryDefinition(req.body, req.body?.slug); const screen = await store.create(data, req.libraryUser.id); invalidate(); return res.status(201).json({ screen }); }
    catch (error) { return fail(res, error); }
  });
  router.patch('/:slug', auth(true), async (req, res) => {
    try {
      if (!await store.definition(req.params.slug)) throw inputError('Screener not found.', 404);
      const screen = await store.update(req.params.slug, libraryDefinition(req.body, req.params.slug)); invalidate(); return res.json({ screen });
    } catch (error) { return fail(res, error); }
  });
  router.get('/:slug/history', auth(false), async (req, res) => {
    try { if (!await store.definition(req.params.slug)) throw inputError('Screener not found.', 404); return res.json({ snapshots: await store.history(req.params.slug) }); }
    catch (error) { return fail(res, error); }
  });
  router.get('/:slug', auth(false), async (req, res) => {
    try {
      const id = req.query.snapshot;
      if (id !== undefined && !/^[1-9]\d{0,15}$/.test(String(id))) throw inputError('Invalid snapshot.');
      const detail = await store.detail(req.params.slug, id); if (!detail) throw inputError('Screener or snapshot not found.', 404);
      return res.json(detail);
    } catch (error) { return fail(res, error); }
  });
  router.post('/:slug/preview', auth(true), async (req, res) => {
    try {
      if (!await store.definition(req.params.slug)) throw inputError('Screener not found.', 404);
      let data; try { data = libraryImport(req.body); } catch (error) { throw inputError(error.message); }
      return res.json(data);
    } catch (error) { return fail(res, error); }
  });
  router.post('/:slug/publish', auth(true), async (req, res) => {
    try {
      if (req.body?.reviewed !== true) throw inputError('Review the preview and confirm publication first.');
      if (!await store.definition(req.params.slug)) throw inputError('Screener not found.', 404);
      let data; try { data = libraryImport(req.body); } catch (error) { throw inputError(error.message); }
      const snapshot = await store.publish(req.params.slug, data, req.libraryUser.id); invalidate(); return res.json({ snapshot });
    } catch (error) { if (error.code === 'P0001') error = inputError(error.message); return fail(res, error); }
  });
  return router;
}
