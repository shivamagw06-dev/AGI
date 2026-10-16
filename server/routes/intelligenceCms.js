import { Router } from 'express';
import { getModule, listModules } from '../services/intelligenceCms/modules.js';
import {
  createRecord,
  deleteRecord,
  exportModuleCsv,
  getDashboardStats,
  getRecord,
  getRecordVersions,
  importModuleCsv,
  listRecords,
  updateRecord,
} from '../services/intelligenceCms/store.js';

export default function createIntelligenceCmsRouter() {
  const router = Router();

  router.get('/modules', (_req, res) => {
    res.json({ modules: listModules() });
  });

  router.get('/dashboard', (_req, res) => {
    res.json(getDashboardStats());
  });

  /** Public — published records for website rendering */
  router.get('/public/:moduleId', (req, res) => {
    const mod = getModule(req.params.moduleId);
    if (!mod) return res.status(404).json({ error: 'Module not found' });
    const records = listRecords(req.params.moduleId, { status: 'published' });
    return res.json({ module: mod.id, records });
  });

  router.get('/modules/:moduleId/records', (req, res) => {
    const mod = getModule(req.params.moduleId);
    if (!mod) return res.status(404).json({ error: 'Module not found' });
    const records = listRecords(req.params.moduleId, {
      status: req.query.status || null,
      q: req.query.q || null,
    });
    return res.json({ module: mod, records });
  });

  router.get('/modules/:moduleId/export', (req, res) => {
    try {
      const csv = exportModuleCsv(req.params.moduleId);
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', `attachment; filename="${req.params.moduleId}.csv"`);
      return res.send(csv);
    } catch (e) {
      return res.status(400).json({ error: e.message });
    }
  });

  router.post('/modules/:moduleId/import', (req, res) => {
    try {
      const csv = req.body?.csv || '';
      const result = importModuleCsv(req.params.moduleId, csv, req.body?.actor || 'admin');
      return res.json(result);
    } catch (e) {
      return res.status(400).json({ error: e.message });
    }
  });

  router.post('/modules/:moduleId/records', (req, res) => {
    try {
      const record = createRecord(req.params.moduleId, req.body || {}, req.body?.actor || 'admin');
      return res.status(201).json(record);
    } catch (e) {
      return res.status(400).json({ error: e.message });
    }
  });

  router.get('/records/:id', (req, res) => {
    const record = getRecord(req.params.id);
    if (!record) return res.status(404).json({ error: 'Not found' });
    const versions = getRecordVersions(record.id);
    return res.json({ record, versions });
  });

  router.patch('/records/:id', (req, res) => {
    const record = updateRecord(req.params.id, req.body || {}, req.body?.actor || 'admin');
    if (!record) return res.status(404).json({ error: 'Not found' });
    return res.json(record);
  });

  router.delete('/records/:id', (req, res) => {
    deleteRecord(req.params.id);
    return res.json({ ok: true });
  });

  router.post('/records/:id/publish', (req, res) => {
    const record = updateRecord(req.params.id, { status: 'published' }, req.body?.actor || 'admin');
    if (!record) return res.status(404).json({ error: 'Not found' });
    return res.json(record);
  });

  return router;
}
