import { Card, State, pct } from './Primitives';

/**
 * Why the session is moving, or an admission that it is not clear.
 *
 * The hook returns null unless several assets agree, and this renders that
 * null honestly. Naming a driver from one index being down is how a research
 * page starts writing narrative to fill a card, which is the opposite of what
 * this product is for.
 */
export default function MarketDriverPanel({ drivers, loading, error }) {
  return (
    <Card title="Why Markets Are Moving">
      <State
        loading={loading}
        error={error}
        empty={!drivers}
        labels={{
          loading: 'Assessing market drivers…',
          empty: 'No single dominant market driver has been identified.',
        }}
      >
        {drivers ? (
          <>
            <div className="ld-driver-row">
              <span className="ld-label">Primary driver</span>
              <span>{drivers.primary}</span>
            </div>
            {drivers.secondary ? (
              <div className="ld-driver-row">
                <span className="ld-label">Secondary</span>
                <span>{drivers.secondary}</span>
              </div>
            ) : null}
            {(drivers.confirmations || []).map((c) => (
              <div className="ld-driver-row" key={c.label}>
                <span className="ld-label">{c.label}</span>
                <span className="ld-num">{pct(c.value)} · {c.reads}</span>
              </div>
            ))}
            <div className="ld-view">
              <div className="ld-label" style={{ marginBottom: '0.35rem' }}>AGI view</div>
              {drivers.view}
              <div style={{ marginTop: '0.5rem', fontSize: '0.74rem', color: 'var(--ld-faint)' }}>
                {drivers.basis}
              </div>
            </div>
          </>
        ) : null}
      </State>
    </Card>
  );
}
