import express from 'express';
import crypto from 'node:crypto';
import { IngestError, ingestPayload, verifySignature } from '../services/researchSignalIngest.js';

function bearerToken(req) {
  const value = String(req.get('authorization') || '');
  return value.startsWith('Bearer ') ? value.slice(7).trim() : '';
}

function sameSecret(left, right) {
  if (!left || !right) return false;
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

export default function createResearchSignalsRouter({ repository } = {}) {
  const router = express.Router();
  router.post('/ingest', async (req, res) => {
    const token = String(process.env.RESEARCH_SIGNALS_INGEST_TOKEN || '').trim();
    const secret = String(process.env.RESEARCH_SIGNALS_INGEST_SECRET || '').trim();
    if (!token || !secret) return res.status(503).json({ ok: false, code: 'NOT_CONFIGURED', error: 'Research signal ingestion is not configured.' });
    if (!sameSecret(bearerToken(req), token)) return res.status(401).json({ ok: false, code: 'UNAUTHORIZED', error: 'Invalid ingestion credentials.' });
    const rawBody = req.rawBody || Buffer.from(JSON.stringify(req.body || {}));
    if (!verifySignature(rawBody, req.get('x-agi-signature'), secret)) {
      return res.status(401).json({ ok: false, code: 'INVALID_SIGNATURE', error: 'Invalid payload signature.' });
    }
    try {
      const configuredMaxAge = Number(process.env.RESEARCH_SIGNALS_MAX_AGE_HOURS || 48);
      const maxAgeHours = Number.isFinite(configuredMaxAge) && configuredMaxAge > 0 ? configuredMaxAge : 48;
      const result = await ingestPayload(req.body, rawBody, { repository, maxAgeHours });
      return res.status(result.duplicate ? 200 : 202).json({ ok: true, ...result });
    } catch (error) {
      if (error instanceof IngestError) return res.status(error.status).json({ ok: false, code: error.code, error: error.message });
      if (error?.storageCode === '23505') return res.status(200).json({ ok: true, duplicate: true, runId: req.body?.run_id, accepted: 0 });
      console.error('[research-signals] ingest failed:', error?.message || error);
      return res.status(500).json({ ok: false, code: 'INGEST_FAILED', error: 'Research signal ingestion failed.' });
    }
  });
  return router;
}
