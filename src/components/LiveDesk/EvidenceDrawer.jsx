import { useEffect } from 'react';
import { pct } from './Primitives';

/** what → why → so what → evidence. The drawer is the evidence step: every
 *  number in it is one the card was actually derived from. */
export default function EvidenceDrawer({ item, onClose }) {
  useEffect(() => {
    if (!item) return undefined;
    const onKey = (event) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [item, onClose]);

  if (!item) return null;

  return (
    <>
      <div className="ld-drawer-scrim" onClick={onClose} role="presentation" />
      <aside className="ld-drawer" role="dialog" aria-label="Evidence">
        <div className="ld-drawer-head">
          <span className="ld-label">AGI Intelligence</span>
          <button type="button" className="ld-drawer-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="ld-drawer-body">
          <h3 style={{ fontSize: '1rem' }}>{item.headline}</h3>
          {item.body ? <p className="ld-feed-body" style={{ marginTop: '0.4rem' }}>{item.body}</p> : null}

          <div className="ld-label" style={{ margin: '1.1rem 0 0.4rem' }}>Evidence</div>
          {(item.evidence || []).length ? (
            (item.evidence || []).map((row) => (
              <div className="ld-regime-row" key={row.label}>
                <span>{row.label}</span>
                <span className="ld-num">
                  {typeof row.value === 'number' ? pct(row.value) : row.value}
                </span>
              </div>
            ))
          ) : (
            <p className="ld-feed-body">No supporting series recorded for this item.</p>
          )}

          {item.sources?.length ? (
            <>
              <div className="ld-label" style={{ margin: '1.1rem 0 0.4rem' }}>Sources</div>
              <p className="ld-feed-body">{item.sources.join(' · ')}</p>
            </>
          ) : null}
        </div>
      </aside>
    </>
  );
}
