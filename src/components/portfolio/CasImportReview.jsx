import { useMemo, useState } from 'react';

/**
 * Review a parsed statement before any of it is imported.
 *
 * The client sees every proposed change and chooses. Confirmation sends the
 * import id and the selected row ids and nothing else -- not quantities, not
 * ISINs -- because the server holds the authoritative plan and would not
 * believe rows posted from here.
 *
 * The button says "Import selected holdings" rather than "Sync": this is a
 * statement read once, not a live connection that will keep itself current,
 * and a word that implies otherwise would set the wrong expectation about a
 * portfolio that silently ages.
 */

const SECTIONS = [
  { key: 'adds', title: 'New holdings', selectable: true,
    blurb: 'Present in the statement and not yet in this portfolio.' },
  { key: 'updates', title: 'Updated holdings', selectable: true,
    blurb: 'Quantity or average cost differs from what is recorded.' },
  { key: 'closures', title: 'Proposed as inactive', selectable: true,
    blurb: 'Absent from this statement. Marked inactive, never deleted, and reversible.' },
  { key: 'unchanged', title: 'Unchanged', selectable: false,
    blurb: 'Already matching. Nothing will be written for these.' },
];

function money(value) {
  if (value === null || value === undefined || value === '') return '—';
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString('en-IN', { maximumFractionDigits: 3 }) : '—';
}

function rowLabel(row) {
  const h = row.holding || {};
  return h.name || h.isin || h.folio || row.id || 'Unnamed holding';
}

function rowIdentity(row) {
  const h = row.holding || {};
  const parts = [h.isin, h.folio, h.account_ref].filter(Boolean);
  return parts.join(' · ') || '—';
}

export default function CasImportReview({ plan, meta, onConfirm, onDiscard, busy }) {
  const initial = useMemo(() => {
    const set = new Set();
    // Adds and updates are pre-selected; closures are not. Marking a holding
    // inactive is the one destructive-looking action here, so it is opted into
    // rather than out of.
    for (const key of ['adds', 'updates']) {
      for (const row of plan?.[key] || []) if (row.row_id) set.add(row.row_id);
    }
    return set;
  }, [plan]);

  const [selected, setSelected] = useState(initial);
  const [expanded, setExpanded] = useState(() => new Set(['adds', 'updates', 'closures']));

  const toggle = (rowId) => setSelected((prev) => {
    const next = new Set(prev);
    if (next.has(rowId)) next.delete(rowId); else next.add(rowId);
    return next;
  });

  const toggleSection = (key) => setExpanded((prev) => {
    const next = new Set(prev);
    if (next.has(key)) next.delete(key); else next.add(key);
    return next;
  });

  const selectAllIn = (key, on) => setSelected((prev) => {
    const next = new Set(prev);
    for (const row of plan?.[key] || []) {
      if (!row.row_id) continue;
      if (on) next.add(row.row_id); else next.delete(row.row_id);
    }
    return next;
  });

  const review = plan?.review_queue || [];
  const warnings = plan?.warnings || [];
  const accounts = meta?.accounts || [];
  const count = selected.size;

  return (
    <section className="cas-review">
      <header className="cas-review__head">
        <h2>Review statement</h2>
        <dl className="cas-review__meta">
          <div><dt>Provider</dt><dd>{meta?.provider || 'Not identified'}</dd></div>
          <div><dt>Statement date</dt><dd>{meta?.statement_date || 'Not stated'}</dd></div>
          <div>
            <dt>Accounts covered</dt>
            <dd>{accounts.length ? accounts.join(', ') : 'None identified'}</dd>
          </div>
        </dl>
        {accounts.length ? (
          <p className="cas-review__scope">
            Only holdings in {accounts.length === 1 ? 'this account' : 'these accounts'} can be
            marked inactive by this import. Holdings held elsewhere are untouched.
          </p>
        ) : null}
      </header>

      {warnings.length ? (
        <ul className="cas-review__warnings">
          {warnings.map((text) => <li key={text}>{text}</li>)}
        </ul>
      ) : null}

      {SECTIONS.map(({ key, title, blurb, selectable }) => {
        const rows = plan?.[key] || [];
        const open = expanded.has(key);
        return (
          <div className="cas-review__section" key={key}>
            <button type="button" className="cas-review__toggle"
                    onClick={() => toggleSection(key)} aria-expanded={open}>
              {title} <span className="cas-review__count">{rows.length}</span>
            </button>
            {open ? (
              <>
                <p className="cas-review__blurb">{blurb}</p>
                {selectable && rows.length ? (
                  <p className="cas-review__bulk">
                    <button type="button" onClick={() => selectAllIn(key, true)}>Select all</button>
                    <button type="button" onClick={() => selectAllIn(key, false)}>Select none</button>
                  </p>
                ) : null}
                {rows.length === 0 ? <p className="cas-review__empty">None.</p> : (
                  <table className="cas-review__table">
                    <thead>
                      <tr>
                        {selectable ? <th scope="col"><span className="sr-only">Import</span></th> : null}
                        <th scope="col">Holding</th>
                        <th scope="col">Identifier</th>
                        <th scope="col">{key === 'updates' ? 'Change' : 'Quantity'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => {
                        const id = row.row_id || row.id;
                        return (
                          <tr key={id}>
                            {selectable ? (
                              <td>
                                <input type="checkbox" checked={selected.has(row.row_id)}
                                       onChange={() => toggle(row.row_id)}
                                       aria-label={`Import ${rowLabel(row)}`} />
                              </td>
                            ) : null}
                            <td>{rowLabel(row)}</td>
                            <td className="cas-review__ident">{rowIdentity(row)}</td>
                            <td>
                              {key === 'updates' && row.changes
                                ? Object.entries(row.changes).map(([field, change]) => (
                                    <span key={field} className="cas-review__delta">
                                      {field}: {money(change.from)} → {money(change.to)}
                                    </span>
                                  ))
                                : money(row.holding?.quantity ?? row.quantity)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </>
            ) : null}
          </div>
        );
      })}

      <div className="cas-review__section">
        <h3>Unmatched rows <span className="cas-review__count">{review.length}</span></h3>
        <p className="cas-review__blurb">
          Lines the statement contained that could not be resolved to a holding.
          These are never imported. They are kept so nothing is lost silently —
          a portfolio that is quietly short a position still adds up.
        </p>
        {review.length === 0 ? <p className="cas-review__empty">None.</p> : (
          <ul className="cas-review__unmatched">
            {review.map((row, index) => (
              <li key={`${row.reason}-${index}`}>
                <code>{row.reason}</code>
                {row.excerpt ? <span className="cas-review__excerpt">{row.excerpt}</span> : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <footer className="cas-review__actions">
        <button type="button" className="cas-review__confirm" disabled={busy || count === 0}
                onClick={() => onConfirm?.(Array.from(selected))}>
          {busy ? 'Importing…' : `Import selected holdings (${count})`}
        </button>
        <button type="button" className="cas-review__discard" disabled={busy}
                onClick={() => onDiscard?.()}>
          Discard
        </button>
        <p className="cas-review__note">
          Nothing has been written yet. This statement is imported once — it is
          not a live connection and will not update on its own.
        </p>
      </footer>
    </section>
  );
}
