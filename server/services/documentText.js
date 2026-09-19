/**
 * A filing as pages, because scope lives in the running header.
 *
 * Pasted text is one string, and one string cannot say which page a line was
 * on. That matters more than it sounds: Reliance states operating cash flow
 * twice under the same words, 79,059 crore standalone and 1,92,113
 * consolidated, and the only thing separating them is the header at the top of
 * the page each sits on. Flatten the document and that distinction is gone -
 * along with the page number, which is what lets a reader check a figure in
 * seconds rather than by searching.
 *
 * So the document is read as pages and kept that way.
 */

/** What one page of text looks like once the layout is gone. */
const collapse = (text) => String(text ?? '').replace(/\s+/g, ' ').trim();

/** A plain Uint8Array over whatever the caller had. */
export function bytesOf(data) {
  if (ArrayBuffer.isView(data)) {
    return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
  }
  return new Uint8Array(data);
}

/**
 * Every page of a PDF, in order.
 *
 * pdfjs is imported where it is used rather than at module load, so a server
 * that never reads a document does not pay for the parser.
 */
export async function pagesFromPdf(data) {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const doc = await pdfjs.getDocument({
    // A Node Buffer is a Uint8Array subclass, so an instanceof check passes it
    // through and pdfjs then rejects it by name. multer hands over a Buffer,
    // so this is the shape that actually arrives. The view is zero-copy.
    data: bytesOf(data),
    useSystemFonts: true,
    // A filing is text. Anything that wants to run is not being run.
    isEvalSupported: false,
  }).promise;
  const pages = [];
  for (let at = 1; at <= doc.numPages; at += 1) {
    const content = await (await doc.getPage(at)).getTextContent();
    pages.push(content.items.map((item) => item.str).join(' '));
  }
  return pages;
}

/**
 * Pasted text as pages, as far as that is possible.
 *
 * It is not possible well. A paste has no page boundaries, and the markers
 * that would stand in for them appear in cross-references too - "Consolidated
 * Financial Statements" occurs 215 times in a filing with 53 consolidated
 * pages. Splitting on them would mark fragments with a scope they do not have,
 * which is the one failure worth avoiding here because a wrong scope reads
 * exactly like a right one.
 *
 * So pasted text is returned as a single page with no scope. Everything that
 * depends on scope will report that it has no way to look, which is true, and
 * the document can be supplied as a PDF instead.
 */
export function pagesFromText(text) {
  const body = collapse(text);
  return body ? [body] : [];
}

/** The whole document, for the checks that need to see all of it. */
export function joinPages(pages) {
  return (pages || []).join('\n');
}
