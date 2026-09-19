import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  MAX_PDF_BYTES, checkUpload, cleanSelection, looksLikePdf, redactBody,
  uploadErrorCode,
} from './portfolioImportGuards.js';

describe('content inspection, not the filename', () => {
  test('accepts a real PDF header', () => {
    assert.equal(looksLikePdf(Buffer.from('%PDF-1.7 header')), true);
  });

  test('rejects a renamed file whatever it claims to be', () => {
    // statement.pdf containing a zip is still a zip.
    assert.equal(looksLikePdf(Buffer.from('PK zipped')), false);
    assert.equal(looksLikePdf(Buffer.from('<html>')), false);
  });

  test('rejects an empty or truncated buffer', () => {
    assert.equal(looksLikePdf(Buffer.alloc(0)), false);
    assert.equal(looksLikePdf(Buffer.from('%PD')), false);
  });

  test('rejects a non-buffer', () => {
    assert.equal(looksLikePdf('%PDF-1.7'), false);
    assert.equal(looksLikePdf(null), false);
  });
});

describe('checking an uploaded file', () => {
  test('accepts a PDF within the limit', () => {
    const out = checkUpload({ buffer: Buffer.from('%PDF-1.7 hello') });
    assert.equal(out.ok, true);
  });

  test('refuses a missing file', () => {
    assert.equal(checkUpload(undefined).error, 'no_file');
    assert.equal(checkUpload({ buffer: Buffer.alloc(0) }).error, 'no_file');
  });

  test('refuses a non-PDF that arrived under a pdf field name', () => {
    assert.equal(checkUpload({ buffer: Buffer.from('PK zipped') }).error, 'not_a_pdf');
  });

  test('refuses an oversized file even if multer let it through', () => {
    const big = Buffer.concat([Buffer.from('%PDF'), Buffer.alloc(MAX_PDF_BYTES)]);
    assert.equal(checkUpload({ buffer: big }).error, 'file_too_large');
  });
});

describe('a confirmation carries ids and nothing else', () => {
  test('keeps well-formed string ids', () => {
    assert.deepEqual(cleanSelection(['abc', 'def']), ['abc', 'def']);
  });

  test('drops anything that is not a string id', () => {
    // The one place a client could try to smuggle a holding through.
    const out = cleanSelection(['abc', { isin: 'INE002A01018', quantity: 9999 }, 42, null]);
    assert.deepEqual(out, ['abc']);
  });

  test('de-duplicates', () => {
    assert.deepEqual(cleanSelection(['abc', 'abc', ' abc ']), ['abc']);
  });

  test('rejects absurdly long ids', () => {
    assert.deepEqual(cleanSelection(['x'.repeat(65)]), []);
  });

  test('caps the selection size', () => {
    const many = Array.from({ length: 20 }, (_, i) => `id-${i}`);
    assert.equal(cleanSelection(many, { max: 5 }).length, 5);
  });

  test('returns nothing for a non-array', () => {
    assert.deepEqual(cleanSelection('abc'), []);
    assert.deepEqual(cleanSelection(null), []);
  });
});

describe('bodies are redacted before anything logs them', () => {
  test('masks the password', () => {
    // Multipart keeps the document out of the JSON body, but the password is
    // still a form field and APM captures bodies by default.
    const out = redactBody({ password: 'PAN-of-the-client', portfolio_id: 'p1' });
    assert.equal(out.password, '[redacted]');
    assert.equal(out.portfolio_id, 'p1');
  });

  test('masks a document and a fingerprint wherever they appear', () => {
    const out = redactBody({
      pdf_base64: 'JVBERi0xLjc=',
      nested: { statement_fingerprint: 'abc', access_token: 'tok' },
    });
    assert.equal(out.pdf_base64, '[redacted]');
    assert.equal(out.nested.statement_fingerprint, '[redacted]');
    assert.equal(out.nested.access_token, '[redacted]');
  });

  test('leaves harmless values alone and tolerates non-objects', () => {
    assert.deepEqual(redactBody({ selected_row_ids: ['a', 'b'] }).selected_row_ids, ['a', 'b']);
    assert.equal(redactBody(null), null);
    assert.equal(redactBody('text'), 'text');
  });
});

describe('multer errors never carry field values outward', () => {
  test('maps each limit to a fixed client code', () => {
    assert.equal(uploadErrorCode({ code: 'LIMIT_FILE_SIZE' }), 'file_too_large');
    assert.equal(uploadErrorCode({ code: 'LIMIT_UNEXPECTED_FILE' }), 'no_file');
    assert.equal(uploadErrorCode({ code: 'LIMIT_FIELD_VALUE' }), 'field_too_large');
    assert.equal(uploadErrorCode({ code: 'LIMIT_PART_COUNT' }), 'too_many_fields');
    assert.equal(uploadErrorCode({ code: 'LIMIT_FIELD_COUNT' }), 'too_many_fields');
  });

  test('falls back to a generic code for anything unrecognised', () => {
    assert.equal(uploadErrorCode({ code: 'SOMETHING_NEW' }), 'upload_failed');
    assert.equal(uploadErrorCode(undefined), 'upload_failed');
  });

  test('never returns the field or the value that tripped the limit', () => {
    // multer attaches both; returning the error would hand back the input.
    const err = { code: 'LIMIT_FIELD_VALUE', field: 'password', value: 'the-secret' };
    const out = uploadErrorCode(err);
    assert.equal(out, 'field_too_large');
    // Neither the value nor the field name. multer attaches both to the error,
    // and returning either would hand the uploaded secret back to the caller.
    assert.ok(!JSON.stringify(out).includes('the-secret'), 'the field value leaked into the response');
    assert.ok(!JSON.stringify(out).includes('password'), 'the field name leaked into the response');
  });
});
