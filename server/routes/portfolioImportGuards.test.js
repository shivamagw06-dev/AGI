import { describe, it, expect } from 'vitest';
import {
  MAX_PDF_BYTES, cleanSelection, decodeUpload, looksLikePdf,
} from './portfolioImportGuards.js';

const b64 = (text) => Buffer.from(text).toString('base64');

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

describe('decoding an upload', () => {
  it('accepts a base64 PDF', () => {
    const out = decodeUpload({ pdf_base64: b64('%PDF-1.7 hello') });
    expect(out.ok).toBe(true);
    expect(out.buffer.length).toBeGreaterThan(0);
  });

  it('refuses a missing document', () => {
    expect(decodeUpload({}).error).toBe('no_file');
    expect(decodeUpload({ pdf_base64: '' }).error).toBe('no_file');
  });

  it('refuses a non-PDF even when it decodes cleanly', () => {
    expect(decodeUpload({ pdf_base64: b64('PK zipped') }).error).toBe('not_a_pdf');
  });

  it('refuses an oversized document before allocating it', () => {
    // Base64 length alone is enough to know it is too big.
    const oversized = 'A'.repeat(Math.ceil((MAX_PDF_BYTES + 1024) / 0.75));
    expect(decodeUpload({ pdf_base64: oversized }).error).toBe('file_too_large');
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
