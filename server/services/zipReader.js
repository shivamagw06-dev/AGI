/**
 * Read entries out of a ZIP, with no dependency.
 *
 * The SEC publishes its bulk Form 345 datasets as quarterly ZIPs. There is no
 * zip library in this project and no guarantee the `unzip` binary exists in
 * the deploy container, so this reads the format directly - it is a handful of
 * fixed-width headers and a deflate stream, both of which node:zlib already
 * handles.
 *
 * The central directory is used rather than scanning for local file headers.
 * A local header may carry zeroes for the sizes and defer them to a data
 * descriptor after the payload (general-purpose bit 3), so a scanner that
 * trusts local headers reads zero bytes and reports an empty file - which
 * looks exactly like a quarter in which nobody filed anything.
 */
import { inflateRawSync } from 'node:zlib';

const EOCD_SIGNATURE = 0x06054b50;
const CENTRAL_SIGNATURE = 0x02014b50;
const STORED = 0;
const DEFLATED = 8;

/** Find the end-of-central-directory record, which sits at the very end. */
function findEocd(buffer) {
  // It ends with a comment of up to 65,535 bytes, so the signature is within
  // the last 64KB plus the record's own 22 bytes. Scanned backwards because
  // the comment may itself contain the signature bytes.
  const start = Math.max(0, buffer.length - (0xffff + 22));
  for (let i = buffer.length - 22; i >= start; i -= 1) {
    if (buffer.readUInt32LE(i) === EOCD_SIGNATURE) return i;
  }
  return -1;
}

/**
 * The entries in a ZIP: name, where the data is, and how big it is.
 *
 * Names only - the payloads are not decompressed here, because a Form 345
 * archive holds a 25 MB footnotes file that nothing in this project reads.
 */
export function listEntries(buffer) {
  const eocd = findEocd(buffer);
  if (eocd < 0) throw new Error('not a ZIP archive: no end-of-central-directory record');

  const count = buffer.readUInt16LE(eocd + 10);
  let offset = buffer.readUInt32LE(eocd + 16);

  const entries = [];
  for (let i = 0; i < count; i += 1) {
    if (buffer.readUInt32LE(offset) !== CENTRAL_SIGNATURE) {
      throw new Error(`corrupt central directory at entry ${i}`);
    }
    const method = buffer.readUInt16LE(offset + 10);
    const compressedSize = buffer.readUInt32LE(offset + 20);
    const uncompressedSize = buffer.readUInt32LE(offset + 24);
    const nameLength = buffer.readUInt16LE(offset + 28);
    const extraLength = buffer.readUInt16LE(offset + 30);
    const commentLength = buffer.readUInt16LE(offset + 32);
    const localOffset = buffer.readUInt32LE(offset + 42);
    const name = buffer.toString('utf8', offset + 46, offset + 46 + nameLength);

    entries.push({ name, method, compressedSize, uncompressedSize, localOffset });
    offset += 46 + nameLength + extraLength + commentLength;
  }
  return entries;
}

/**
 * Decompress one entry.
 *
 * The local header's name and extra-field lengths are read again here rather
 * than reused from the central directory: the two are allowed to differ, and
 * the extra field routinely does, so using the central figure lands a few
 * bytes into the payload and inflate fails on data that is perfectly fine.
 */
export function readEntry(buffer, entry) {
  const nameLength = buffer.readUInt16LE(entry.localOffset + 26);
  const extraLength = buffer.readUInt16LE(entry.localOffset + 28);
  const start = entry.localOffset + 30 + nameLength + extraLength;
  const body = buffer.subarray(start, start + entry.compressedSize);

  if (entry.method === STORED) return body;
  if (entry.method === DEFLATED) return inflateRawSync(body);
  throw new Error(`${entry.name}: unsupported compression method ${entry.method}`);
}

/** Read one named entry, or throw naming what was actually in the archive. */
export function extract(buffer, name) {
  const entries = listEntries(buffer);
  const entry = entries.find((row) => row.name === name);
  if (!entry) {
    throw new Error(`${name} is not in the archive; it holds ${entries.map((e) => e.name).join(', ')}`);
  }
  return readEntry(buffer, entry);
}
