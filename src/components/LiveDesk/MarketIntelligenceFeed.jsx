import { Card, State, dirClass, istTime, pct } from './Primitives';

/**
 * The panel that differentiates this page from an embedded television.
 *
 * Items are built from the market snapshot and AGI's own theme engine. They
 * are ranked by magnitude, then by cross-asset confirmation, then recency -
 * so a large isolated move ranks below a smaller one several assets agree on.
 *
 * There is no fallback copy. When nothing clears the bar the panel says so,
 * because a desk that always has something to say is one that is sometimes
 * making it up.
 */
export default function MarketIntelligenceFeed({ items, loading, error, updatedAt, onEvidence }) {
  return (
    <Card
      title="AGI Market Intelligence"
      right={updatedAt ? <span className="ld-refresh">{istTime(updatedAt)}</span> : null}
      tight
    >
      <State
        loading={loading}
        error={error}
        empty={!items?.length}
        labels={{
          loading: 'Loading market intelligence…',
          empty: 'No high-confidence intelligence signals right now.',
        }}
      >
        <div className="ld-feed">
          {(items || []).map((item) => (
            <article className="ld-feed-item" key={item.id}>
              <div className="ld-feed-meta">
                {item.time ? <span className="ld-label">{item.time}</span> : null}
                <span className="ld-chip">{item.category}</span>
                {item.severity && item.severity !== 'WATCH' ? (
                  <span className={item.severity === 'MAJOR' ? 'ld-chip ld-chip-major' : 'ld-chip ld-chip-notable'}>
                    {item.severity}
                  </span>
                ) : null}
              </div>
              <div className="ld-feed-head">
                {item.headline}
                {typeof item.changePct === 'number' ? (
                  <span className={`ld-num ${dirClass(item.changePct)}`} style={{ marginLeft: '0.5rem', fontSize: '0.86rem' }}>
                    {pct(item.changePct)}
                  </span>
                ) : null}
              </div>
              {item.body ? <div className="ld-feed-body">{item.body}</div> : null}
              {item.evidence?.length ? (
                <button type="button" className="ld-evidence" onClick={() => onEvidence(item)}>
                  View evidence
                </button>
              ) : null}
            </article>
          ))}
        </div>
      </State>
    </Card>
  );
}
