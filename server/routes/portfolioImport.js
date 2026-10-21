/**
 * CAS upload, review and confirmation.
 *
 * The confirm step accepts an import id and a list of row ids. It does not
 * accept holdings, and would not believe them if it did: a client who can post
 * arbitrary rows to a confirm endpoint can write any position into a
 * portfolio. The authoritative plan is the one the server stored.
 *
 * The document and the password are not persisted and not logged, and their
 * references are discarded promptly. That is the accurate claim: the buffer is
 * overwritten and dereferenced once the engine has answered, but a JavaScript
 * string cannot be reliably zeroed, and neither can copies the runtime may have
 * made. Nothing here guarantees erasure from memory, and it would be wrong to
 * say otherwise.
 *
 * What is guaranteed is that neither reaches storage or a log. Every failure is
 * a code from a fixed list, so no underlying message can leak the input by
 * being helpful.
 *
 * The upload is multipart/form-data. Base64 in JSON was the first design and
 * was wrong: it inflates the document by a third, forces Express to
 * materialise both the JSON string and the decoded bytes, and leaves the
 * document sitting in a request body that APM and body-logging middleware
 * capture by default. Multipart streams the file to a bounded memory buffer
 * and keeps it out of the JSON body entirely. The password is still a form
 * field, so bodies are redacted before anything logs them.
 */

import express from 'express';
import rateLimit from 'express-rate-limit';
import multer from 'multer';

import {
  CLIENT_SAFE_ERRORS, MAX_PDF_BYTES, PARSE_TIMEOUT_MS, PLAN_TTL_MINUTES,
  checkUpload, cleanSelection, redactBody, uploadErrorCode,
} from './portfolioImportGuards.js';

/**
 * Memory storage on purpose. Disk storage would put a client's entire
 * financial position in a temp directory, and deleting that file becomes
 * something to get right on every error path including the ones that throw.
 * The limit is enforced while the body streams, so an oversized upload is cut
 * off rather than buffered and then rejected.
 */
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: MAX_PDF_BYTES,
    files: 1,          // exactly one document
    parts: 4,          // the file plus at most three small fields
    fields: 3,         // password, portfolio_id, and room for one more
    fieldSize: 512,    // a password, not a payload
    fieldNameSize: 64,
    headerPairs: 32,
  },
}).single('statement');

/**
 * Keep the request body away from anything that logs bodies.
 *
 * redactBody is only useful if it runs before a logger sees the object, and
 * APM agents commonly capture req.body from instrumentation that runs ahead of
 * ordinary middleware. So the raw body is replaced on the request itself: by
 * the time any downstream logger or tracer reads req.body, the password is
 * already gone, and there is no ordering to get right.
 */
function scrubRequest(req, _res, next) {
  if (req.body && typeof req.body === 'object') {
    req.body = redactBody(req.body);
  }
  // Marks the request for log processors that honour it, and is harmless
  // where nothing reads it.
  req.suppressBodyCapture = true;
  next();
}

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

  const json = express.json({ limit: '64kb' });

  /** multer's own errors, translated into codes a client may see. */
  const receive = (req, res, next) => upload(req, res, (err) => {
    if (err) {
      const code = uploadErrorCode(err);
      return fail(res, code === 'file_too_large' ? 413 : 400, code);
    }
    // Lift the two fields we need, then scrub. Everything downstream sees a
    // body with no password in it.
    req.casPassword = typeof req.body?.password === 'string' ? req.body.password : '';
    req.casPortfolioId = typeof req.body?.portfolio_id === 'string'
      ? req.body.portfolio_id : null;
    return scrubRequest(req, res, next);
  });

  /** Parse a statement and store the plan. Writes no holdings. */
  router.post('/portfolio/import/cas', requireUser, uploadLimiter, receive,
    async (req, res) => {
      const userId = req.user?.id;
      const accessToken = req.user?.accessToken;
      if (!userId || !accessToken) return fail(res, 401, 'authentication_required');

      const decoded = checkUpload(req.file);
      if (!decoded.ok) {
        return fail(res, decoded.error === 'file_too_large' ? 413 : 415, decoded.error);
      }

      // Lifted in `receive` before the body was scrubbed. Never stored,
      // never logged, never echoed.
      const password = req.casPassword || '';
      const portfolioId = req.casPortfolioId;

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
      } finally {
        // Overwrite the document before dropping it. A Buffer can be zeroed,
        // which is worth doing while the page is still ours; the password is a
        // string and cannot be, so it is only dereferenced. Neither is erasure
        // from memory in any strong sense - it shortens the window, and that is
        // all it claims to do.
        if (req.file?.buffer) {
          try { req.file.buffer.fill(0); } catch { /* already detached */ }
          req.file.buffer = null;
        }
        req.casPassword = '';
      }

      if (!parsed?.ok) {
        const code = CLIENT_SAFE_ERRORS.has(parsed?.error) ? parsed.error : 'parse_failed';
        return fail(res, code === 'password_required' ? 401 : 422, code);
      }

      const expiresAt = new Date(Date.now() + PLAN_TTL_MINUTES * 60_000).toISOString();
      let saved;
      try {
        saved = await db.insertImportPlan({
          accessToken,
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
      const accessToken = req.user?.accessToken;
      if (!userId || !accessToken) return fail(res, 401, 'authentication_required');

      const selected = cleanSelection(req.body?.selected_row_ids);
      if (!selected.length) return fail(res, 400, 'nothing_selected');

      try {
        // The write happens in one transaction inside db.confirmImport, so a
        // partial failure leaves the portfolio exactly as it was. Ownership is
        // re-checked there against the stored plan rather than trusted here.
        const result = await db.confirmImport({
          accessToken,
          importId: req.params.importId,
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
      if (!req.user?.accessToken) return fail(res, 401, 'authentication_required');
      await db.discardImport({
        accessToken: req.user.accessToken, importId: req.params.importId,
      });
      return res.json({ ok: true });
    } catch {
      return fail(res, 500, 'discard_failed');
    }
  });

  return router;
}

export default createPortfolioImportRouter;
