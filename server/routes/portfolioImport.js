/**
 * CAS upload, review and confirmation.
 *
 * The confirm step accepts an import id and a list of row ids. It does not
 * accept holdings, and would not believe them if it did: a client who can post
 * arbitrary rows to a confirm endpoint can write any position into a
 * portfolio. The authoritative plan is the one the server stored.
 *
 * Nothing about the uploaded document survives the request. The bytes are held
 * in memory, passed to the engine, and dropped. The password is never written
 * anywhere and never appears in a log line or an error body — every failure
 * here is a code from a fixed list, so no underlying message can leak the
 * input by being helpful.
 *
 * The upload is JSON with a base64 document rather than multipart, which keeps
 * the password in the body (a header can be logged by a proxy) and avoids
 * adding a file-upload dependency for a single endpoint.
 */

import express from 'express';
import rateLimit from 'express-rate-limit';

import {
  CLIENT_SAFE_ERRORS, MAX_BODY_BYTES, PARSE_TIMEOUT_MS, PLAN_TTL_MINUTES,
  cleanSelection, decodeUpload,
} from './portfolioImportGuards.js';

/** Codes are returned; underlying messages never are. */
function fail(res, status, code) {
  return res.status(status).json({ ok: false, error: code });
}

export function createPortfolioImportRouter({ requireUser, engineFetch, db }) {
  const router = express.Router();

  // Per authenticated user, not per address: a shared office NAT would
  // otherwise rate-limit a whole firm because one person re-uploaded.
  const uploadLimiter = rateLimit({
    windowMs: 60_000,
    limit: 5,
    standardHeaders: true,
    legacyHeaders: false,
    keyGenerator: (req) => req.user?.id || req.ip,
    handler: (_req, res) => fail(res, 429, 'too_many_uploads'),
  });

  const json = express.json({ limit: MAX_BODY_BYTES });

  /** Parse a statement and store the plan. Writes no holdings. */
  router.post('/portfolio/import/cas', requireUser, uploadLimiter, json,
    async (req, res) => {
      const userId = req.user?.id;
      if (!userId) return fail(res, 401, 'authentication_required');

      const decoded = decodeUpload(req.body);
      if (!decoded.ok) {
        return fail(res, decoded.error === 'file_too_large' ? 413 : 415, decoded.error);
      }

      // Read once. Never stored, never logged, never echoed.
      const password = typeof req.body?.password === 'string' ? req.body.password : '';
      const portfolioId = typeof req.body?.portfolio_id === 'string'
        ? req.body.portfolio_id : null;

      let parsed;
      try {
        parsed = await engineFetch('/v1/portfolio-import/cas/parse', {
          method: 'POST',
          timeoutMs: PARSE_TIMEOUT_MS,
          body: {
            pdf_base64: decoded.buffer.toString('base64'),
            password: password || null,
            user_id: userId,
            portfolio_id: portfolioId,
          },
        });
      } catch (error) {
        if (error?.name === 'AbortError') return fail(res, 504, 'parse_timeout');
        return fail(res, 502, 'parse_failed');
      }

      if (!parsed?.ok) {
        const code = CLIENT_SAFE_ERRORS.has(parsed?.error) ? parsed.error : 'parse_failed';
        return fail(res, code === 'password_required' ? 401 : 422, code);
      }

      const expiresAt = new Date(Date.now() + PLAN_TTL_MINUTES * 60_000).toISOString();
      let saved;
      try {
        saved = await db.insertImportPlan({
          userId,
          portfolioId,
          sourceType: parsed.provider || 'UNKNOWN',
          statementDate: parsed.statement_date || null,
          // Keyed HMAC computed in the engine. Stored, never returned.
          statementFingerprint: parsed.fingerprint,
          planSummary: parsed.plan,
          matchedCount: (parsed.plan?.counts?.add || 0) + (parsed.plan?.counts?.update || 0),
          unmatchedCount: parsed.plan?.counts?.review || 0,
          warningCount: (parsed.plan?.warnings || []).length,
          expiresAt,
        });
      } catch (error) {
        if (error?.code === 'duplicate_statement') {
          return fail(res, 409, 'already_imported');
        }
        return fail(res, 500, 'plan_not_saved');
      }

      // The fingerprint identifies the document; it does not travel to a browser.
      const { statement_fingerprint: _omit, ...plan } = parsed.plan || {};
      return res.json({
        ok: true,
        import_plan_id: saved.id,
        expires_at: expiresAt,
        provider: parsed.provider,
        statement_date: parsed.statement_date,
        accounts: parsed.accounts || [],
        plan,
      });
    });

  /** Apply a selection. The body carries ids only. */
  router.post('/portfolio/import/:importId/confirm', requireUser, json,
    async (req, res) => {
      const userId = req.user?.id;
      if (!userId) return fail(res, 401, 'authentication_required');

      const selected = cleanSelection(req.body?.selected_row_ids);
      if (!selected.length) return fail(res, 400, 'nothing_selected');

      try {
        // The write happens in one transaction inside db.confirmImport, so a
        // partial failure leaves the portfolio exactly as it was. Ownership is
        // re-checked there against the stored plan rather than trusted here.
        const result = await db.confirmImport({
          importId: req.params.importId,
          userId,
          selectedRowIds: selected,
        });
        return res.json({ ok: true, ...result });
      } catch (error) {
        if (CLIENT_SAFE_ERRORS.has(error?.code)) {
          return fail(res, 409, error.code);
        }
        return fail(res, 500, 'confirm_failed');
      }
    });

  router.delete('/portfolio/import/:importId', requireUser, async (req, res) => {
    try {
      await db.discardImport({ importId: req.params.importId, userId: req.user?.id });
      return res.json({ ok: true });
    } catch {
      return fail(res, 500, 'discard_failed');
    }
  });

  return router;
}

export default createPortfolioImportRouter;
