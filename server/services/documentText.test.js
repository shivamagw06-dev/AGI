import test from 'node:test';
import assert from 'node:assert/strict';
import { bytesOf, joinPages, pagesFromText } from './documentText.js';

test('a Node Buffer becomes a plain Uint8Array', () => {
  // A Buffer is a Uint8Array subclass, so an instanceof check passes it
  // through and pdfjs then rejects it by name. multer hands over a Buffer, so
  // this is the shape that actually arrives from an upload.
  const buffer = Buffer.from([1, 2, 3, 4]);
  const bytes = bytesOf(buffer);
  assert.equal(bytes.constructor, Uint8Array);
  assert.notEqual(bytes.constructor, Buffer);
  assert.deepEqual([...bytes], [1, 2, 3, 4]);
});

test('a view keeps its own window, not the whole pool', () => {
  // Node allocates small Buffers out of a shared pool, so passing the
  // underlying ArrayBuffer without the offset hands over other buffers' bytes.
  const pool = Buffer.from([9, 9, 1, 2, 3, 9]);
  const slice = pool.subarray(2, 5);
  assert.deepEqual([...bytesOf(slice)], [1, 2, 3]);
});

test('an ArrayBuffer is accepted too', () => {
  assert.deepEqual([...bytesOf(new Uint8Array([7, 8]).buffer)], [7, 8]);
});

test('pasted text is one page with no scope', () => {
  // A paste has no page boundaries, and the markers that would stand in for
  // them appear in cross-references: "Consolidated Financial Statements"
  // occurs 215 times in a filing with 53 consolidated pages. Splitting on them
  // would mark fragments with a scope they do not have, and a wrong scope
  // reads exactly like a right one.
  const pages = pagesFromText('  Some   pasted   filing text  ');
  assert.deepEqual(pages, ['Some pasted filing text']);
});

test('an empty paste is no pages at all', () => {
  assert.deepEqual(pagesFromText('   '), []);
  assert.deepEqual(pagesFromText(null), []);
});

test('pages join back into a document the citation check can search', () => {
  assert.equal(joinPages(['a', 'b']), 'a\nb');
  assert.equal(joinPages(), '');
});
