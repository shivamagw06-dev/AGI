/**
 * Remove comment lines from source before a guard inspects it.
 *
 * Several guards assert that a pattern is ABSENT from a file - no
 * `price_date >= date`, no `report_date < RULE_DATE`, no `no_look_ahead`. They
 * strip comments first, because those files carry notes explaining why the
 * pattern was removed, and a guard that cannot tell a warning from the thing it
 * warns about gets deleted by whoever trips it next.
 *
 * The obvious way to strip is a regex for block comments. It is wrong here, and
 * dangerously so. institutionalHoldingsService.js sends an HTTP Accept header:
 *
 *     'application/xml,text/xml,text/plain,<star><slash><star>'
 *
 * (written with placeholders above, because quoting it literally closes this
 * very comment - which is the hazard, one level up.)
 *
 * That string contains a block-comment opener. A global
 * block-comment regex match starts there and runs to the next closer,
 * which deleted 56% of the file - including all three call sites one guard was
 * counting. It reported "found 0" for code plainly present.
 *
 * The absence assertions are the real hazard. Deleting half a file makes a
 * pattern genuinely absent, so those guards pass while checking nothing, and
 * they pass more convincingly the more code is destroyed.
 *
 * So this works line by line and only ever drops a line that is entirely a
 * comment. A string literal containing comment syntax is never at the start of
 * a line, so it cannot be mistaken for one. A trailing comment after code
 * survives, which is the safe direction: a guard may see slightly more than the
 * executable source, never less.
 */

export function stripCommentLines(source) {
  const lines = String(source || '').split('\n');
  const kept = [];
  let inBlock = false;

  for (const line of lines) {
    const trimmed = line.trim();

    if (inBlock) {
      if (trimmed.endsWith('*/') || trimmed === '*/') inBlock = false;
      continue;
    }
    // A block comment that opens a line. If it also closes on that line, the
    // line is a comment and nothing more.
    if (trimmed.startsWith('/*')) {
      if (!trimmed.includes('*/')) inBlock = true;
      continue;
    }
    // A whole-line // comment, or the continuation body of a JSDoc block.
    if (trimmed.startsWith('//') || trimmed.startsWith('*')) continue;

    kept.push(line);
  }
  return kept.join('\n');
}
