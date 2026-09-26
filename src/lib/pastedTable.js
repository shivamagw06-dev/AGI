// Turning a clipboard block into rows.
//
// The naive version -- split on newlines, then on the delimiter -- is wrong for
// the insider export, which writes a post-transaction holding as a quoted field
// with newlines inside it:
//
//     Panacea Biotec ... 3000  "0
//
//                             (0%)"   0.00  409.6 ...
//
// Split on newlines first and that single trade becomes two rows: a truncated
// one ending at the open quote, and a phantom whose first column is (0%)". The
// desk sees a grid that does not match what it copied.

/** Excel and Sheets copy as tab-separated; a saved CSV is not.
 *
 * Decided from the header alone, matching the engine: a company name
 * legitimately contains a comma ("Tata Motors, Ltd"), so counting commas across
 * the whole block would pick the wrong split on genuinely tab-separated data.
 */
export function delimiterOf(header) {
  if (header.includes('\t')) return '\t';
  return header.split(';').length > header.split(',').length ? ';' : ',';
}

/** Walk the text once, treating a newline as a row break only outside quotes. */
export function parseDelimited(text, delimiter) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch !== '"') { field += ch; continue; }
      if (text[i + 1] === '"') { field += '"'; i += 1; continue; }  // "" is one quote
      quoted = false;
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === delimiter) {
      row.push(field);
      field = '';
    } else if (ch === '\n') {
      row.push(field);
      field = '';
      rows.push(row);
      row = [];
    } else if (ch !== '\r') {
      field += ch;
    }
  }
  row.push(field);
  rows.push(row);

  // Drops the empty row a trailing newline leaves. Blank lines inside a quoted
  // field are part of that field and were never split, so they survive.
  return rows.filter((r) => r.some((c) => c.trim()));
}

/** Rows from a pasted block, header included. */
export function parsePaste(text) {
  if (!text.trim()) return [];
  return parseDelimited(text, delimiterOf(text.split('\n', 1)[0]));
}
