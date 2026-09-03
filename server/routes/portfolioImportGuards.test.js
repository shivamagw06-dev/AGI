import { describe, it, expect } from 'vitest';
import {
  MAX_PDF_BYTES, checkUpload, cleanSelection, looksLikePdf, redactBody,
} from './portfolioImportGuards.js';

describe('content inspection, not the filename', () => {
  it('accepts a real PDF header', () => {
    expect(looksLikePdf(Buffer.from('%PDF-1.7 header'))).toBe(true);
  });

  it('rejects a renamed file whatever it claims to be', () => {
    // statement.pdf containing a zip is still a zip.
    expect(looksLikePdf(Buffer.from('PK zipped'))).toBe(false);
    expect(looksLikePdf(Buffer.from('<html>'))).toBe(false);
  });

  it('rejects an empty or truncated buffer', () => {
    expect(looksLikePdf(Buffer.alloc(0))).toBe(false);
    expect(looksLikePdf(Buffer.from('%PD'))).toBe(false);
  });

  it('rejects a non-buffer', () => {
    expect(looksLikePdf('%PDF-1.7')).toBe(false);
    expect(looksLikePdf(null)).toBe(false);
  });
});

describe('checking an uploaded file', () => {
  it('accepts a PDF within the limit', () => {
    const out = checkUpload({ buffer: Buffer.from('%PDF-1.7 hello') });
    expect(out.ok).toBe(true);
  });

  it('refuses a missing file', () => {
    expect(checkUpload(undefined).error).toBe('no_file');
    expect(checkUpload({ buffer: Buffer.alloc(0) }).error).toBe('no_file');
  });

  it('refuses a non-PDF that arrived under a pdf field name', () => {
    expect(checkUpload({ buffer: Buffer.from('PK zipped') }).error).toBe('not_a_pdf');
  });

  it('refuses an oversized file even if multer let it through', () => {
    const big = Buffer.concat([Buffer.from('%PDF'), Buffer.alloc(MAX_PDF_BYTES)]);
    expect(checkUpload({ buffer: big }).error).toBe('file_too_large');
  });
});

describe('a confirmation carries ids and nothing else', () => {
  it('keeps well-formed string ids', () => {
    expect(cleanSelection(['abc', 'def'])).toEqual(['abc', 'def']);
  });

  it('drops anything that is not a string id', () => {
    // The one place a client could try to smuggle a holding through.
    const out = cleanSelection(['abc', { isin: 'INE002A01018', quantity: 9999 }, 42, null]);
    expect(out).toEqual(['abc']);
  });

  it('de-duplicates', () => {
    expect(cleanSelection(['abc', 'abc', ' abc '])).toEqual(['abc']);
  });

  it('rejects absurdly long ids', () => {
    expect(cleanSelection(['x'.repeat(65)])).toEqual([]);
  });

  it('caps the selection size', () => {
    const many = Array.from({ length: 20 }, (_, i) => `id-${i}`);
    expect(cleanSelection(many, { max: 5 })).toHaveLength(5);
  });

  it('returns nothing for a non-array', () => {
    expect(cleanSelection('abc')).toEqual([]);
    expect(cleanSelection(null)).toEqual([]);
  });
});

describe('bodies are redacted before anything logs them', () => {
  it('masks the password', () => {
    // Multipart keeps the document out of the JSON body, but the password is
    // still a form field and APM captures bodies by default.
    const out = redactBody({ password: 'PAN-of-the-client', portfolio_id: 'p1' });
    expect(out.password).toBe('[redacted]');
    expect(out.portfolio_id).toBe('p1');
  });

  it('masks a document and a fingerprint wherever they appear', () => {
    const out = redactBody({
      pdf_base64: 'JVBERi0xLjc=',
      nested: { statement_fingerprint: 'abc', access_token: 'tok' },
    });
    expect(out.pdf_base64).toBe('[redacted]');
    expect(out.nested.statement_fingerprint).toBe('[redacted]');
    expect(out.nested.access_token).toBe('[redacted]');
  });

  it('leaves harmless values alone and tolerates non-objects', () => {
    expect(redactBody({ selected_row_ids: ['a', 'b'] }).selected_row_ids).toEqual(['a', 'b']);
    expect(redactBody(null)).toBeNull();
    expect(redactBody('text')).toBe('text');
  });
});
