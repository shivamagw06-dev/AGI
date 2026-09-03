/**
 * Pure checks for the CAS upload endpoint.
 *
 * Separated from the route so they can be tested without standing up Express,
 * and so the rules are readable in one place rather than buried in middleware.
 */

/** 10 MB of PDF, enforced by multer before the body is fully buffered. */
export const MAX_PDF_BYTES = 10 * 1024 * 1024;
export const PARSE_TIMEOUT_MS = 30_000;
export const PLAN_TTL_MINUTES = 120;

/**
 * Content inspection, never the filename. A filename is client-supplied and a
 * .pdf extension says nothing about what is inside.
 */
export function looksLikePdf(buffer) {
  return Buffer.isBuffer(buffer)
    && buffer.length > 4
    && buffer.subarray(0, 4).toString('latin1') === '%PDF';
}

/**
 * Check an uploaded file. Returns a code rather than throwing, because every
 * failure here is shown to a client and none of them should quote the input.
 */
export function checkUpload(file) {
  const buffer = file?.buffer;
  if (!Buffer.isBuffer(buffer) || buffer.length === 0) {
    return { ok: false, error: 'no_file' };
  }
  if (buffer.length > MAX_PDF_BYTES) return { ok: false, error: 'file_too_large' };
  if (!looksLikePdf(buffer)) return { ok: false, error: 'not_a_pdf' };
  return { ok: true, buffer };
}

/**
 * The row ids a confirmation may carry.
 *
 * Anything that is not a string id is dropped rather than coerced: a confirm
 * body is the one place a client could try to smuggle a holding, and the
 * server takes ids and nothing else.
 */
export function cleanSelection(value, { max = 5000 } = {}) {
  if (!Array.isArray(value)) return [];
  const out = [];
  const seen = new Set();
  for (const entry of value) {
    if (typeof entry !== 'string') continue;
    const id = entry.trim();
    if (!id || id.length > 64 || seen.has(id)) continue;
    seen.add(id);
    out.push(id);
    if (out.length >= max) break;
  }
  return out;
}

/**
 * Keys whose values must never reach a log, an APM span or an error body.
 *
 * The password is the obvious one. `pdf_base64` remains here because an older
 * client may still send it and a body logger would happily record a client's
 * entire financial position.
 */
export const REDACT_KEYS = new Set([
  'password', 'pdf_base64', 'statement', 'file', 'buffer',
  'statement_fingerprint', 'access_token', 'refresh_token',
]);

/**
 * Redact a request body before anything logs it.
 *
 * Multipart keeps the document out of the JSON body, but the password still
 * arrives as a form field, so a body-logging middleware would capture it
 * unless the body is scrubbed first.
 */
export function redactBody(body) {
  if (!body || typeof body !== 'object') return body;
  const out = Array.isArray(body) ? [] : {};
  for (const [key, value] of Object.entries(body)) {
    if (REDACT_KEYS.has(key)) {
      out[key] = '[redacted]';
    } else if (value && typeof value === 'object') {
      out[key] = redactBody(value);
    } else {
      out[key] = value;
    }
  }
  return out;
}

/** Error codes a client may see verbatim. Anything else becomes a generic 500. */
export const CLIENT_SAFE_ERRORS = new Set([
  'not_your_import', 'import_expired', 'portfolio_changed',
  'import_already_resolved', 'no_valid_rows_selected', 'nothing_selected',
  'import_plan_missing', 'already_imported', 'password_required',
  'wrong_password', 'not_a_pdf', 'file_too_large', 'too_many_pages',
  'no_text_extracted', 'unreadable_pdf', 'no_file', 'portfolio_not_found',
]);
