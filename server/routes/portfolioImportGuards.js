/**
 * Pure checks for the CAS upload endpoint.
 *
 * Separated from the route so they can be tested without standing up Express,
 * and so the rules are readable in one place rather than buried in middleware.
 */

/** 10 MB of PDF. Base64 inflates by a third, so the body limit is larger. */
export const MAX_PDF_BYTES = 10 * 1024 * 1024;
export const MAX_BODY_BYTES = Math.ceil(MAX_PDF_BYTES * 1.4);
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
 * Decode the uploaded document.
 *
 * Returns a code rather than throwing, because every failure here is something
 * the client is shown and none of them should quote the input back.
 */
export function decodeUpload(body) {
  const encoded = typeof body?.pdf_base64 === 'string' ? body.pdf_base64 : '';
  if (!encoded) return { ok: false, error: 'no_file' };
  // Reject before allocating: base64 length tells us the decoded size.
  if (Math.floor(encoded.length * 0.75) > MAX_PDF_BYTES) {
    return { ok: false, error: 'file_too_large' };
  }
  let buffer;
  try {
    buffer = Buffer.from(encoded, 'base64');
  } catch {
    return { ok: false, error: 'not_a_pdf' };
  }
  if (!buffer.length) return { ok: false, error: 'no_file' };
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

/** Error codes a client may see verbatim. Anything else becomes a generic 500. */
export const CLIENT_SAFE_ERRORS = new Set([
  'not_your_import', 'import_expired', 'portfolio_changed',
  'import_already_resolved', 'no_valid_rows_selected', 'nothing_selected',
  'import_plan_missing', 'already_imported', 'password_required',
  'wrong_password', 'not_a_pdf', 'file_too_large', 'too_many_pages',
  'no_text_extracted', 'unreadable_pdf', 'no_file',
]);
