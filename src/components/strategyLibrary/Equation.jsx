import { useMemo } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';

/**
 * Typeset a display equation with KaTeX.
 *
 * Wide equations scroll horizontally inside .sl-eq-render rather than
 * overflowing the page — the brief requires this on mobile breakpoints.
 */
export default function Equation({ label, tex, note }) {
  const html = useMemo(
    () =>
      katex.renderToString(tex, {
        displayMode: true,
        throwOnError: false,
        strict: false,
      }),
    [tex],
  );

  return (
    <div className="sl-eq">
      {label ? <div className="sl-eq-label">{label}</div> : null}
      <div
        className="sl-eq-render"
        role="math"
        aria-label={label || 'equation'}
        dangerouslySetInnerHTML={{ __html: html }}
      />
      {note ? <p className="sl-eq-note">{note}</p> : null}
    </div>
  );
}

/** Inline variant for use inside prose. */
export function InlineMath({ tex }) {
  const html = useMemo(
    () => katex.renderToString(tex, { displayMode: false, throwOnError: false, strict: false }),
    [tex],
  );
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}
