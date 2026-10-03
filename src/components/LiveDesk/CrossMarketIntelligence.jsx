import { Card, State, pct } from './Primitives';

/**
 * Global developments with a stated India exposure.
 *
 * The relationships are structural facts about the Indian economy - a crude
 * importer, a market sensitive to global risk appetite - not patterns mined
 * from co-movement. The data decides only whether a linkage is live.
 *
 * DETECTED means the global leg moved. CONFIRMED means the domestic leg moved
 * with it. Neither says one caused the other, and an unconfirmed linkage says
 * so on its face rather than being quietly dropped.
 */
export default function CrossMarketIntelligence({ links, loading, error }) {
  return (
    <Card title="Cross-Market Intelligence" tight>
      <State
        loading={loading}
        error={error}
        empty={!links?.length}
        labels={{
          loading: 'Assessing global to India linkages…',
          empty: 'No global development is currently large enough to read through to Indian assets.',
        }}
      >
        <div className="ld-feed">
          {(links || []).map((link) => (
            <article className="ld-feed-item" key={link.id}>
              <div className="ld-feed-meta">
                <span className={link.status === 'CONFIRMED' ? 'ld-chip ld-chip-notable' : 'ld-chip'}>
                  {link.status}
                </span>
                <span className="ld-label">Global → India</span>
              </div>

              <div className="ld-xm-row">
                <span className="ld-label">Global signal</span>
                <span className="ld-num">{link.signalLabel} {pct(link.signalChange)}</span>
              </div>
              <div className="ld-xm-row">
                <span className="ld-label">India exposure</span>
                <span>{link.exposure}</span>
              </div>
              <div className="ld-xm-row">
                <span className="ld-label">{link.confirmLabel}</span>
                <span className="ld-num">
                  {link.confirmChange === null ? 'not priced' : pct(link.confirmChange)}
                  {link.confirmReads ? ` · ${link.confirmReads}` : ''}
                </span>
              </div>

              <div className="ld-feed-body" style={{ marginTop: '0.45rem' }}>{link.rationale}</div>
              {link.note ? (
                <div className="ld-feed-body" style={{ color: 'var(--ld-warn)' }}>{link.note}</div>
              ) : null}
              {link.watch?.length ? (
                <div className="ld-feed-body" style={{ color: 'var(--ld-faint)' }}>
                  Watch: {link.watch.join(' · ')}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </State>
    </Card>
  );
}
