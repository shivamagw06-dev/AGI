import { Card, State } from './Primitives';

/**
 * AGI's regime read, or an explicit absence.
 *
 * The intelligence engine returns the literal string "Unavailable" when it is
 * degraded. That is not a regime and is filtered out upstream, so this panel
 * shows the unavailable state rather than presenting the engine's error as a
 * market condition.
 */
export default function MarketRegimeCard({ regime, loading, error }) {
  const breadth = regime?.breadth;
  const rows = [];
  if (regime?.regime) rows.push(['Regime', regime.regime]);
  if (regime?.health?.overall) rows.push(['Market health', regime.health.overall]);
  if (breadth && Number.isFinite(Number(breadth.advancing)) && Number.isFinite(Number(breadth.declining))) {
    const advancing = Number(breadth.advancing);
    const declining = Number(breadth.declining);
    rows.push(['Breadth', `${advancing} advancing / ${declining} declining`]);
  }

  return (
    <Card title="Market Regime">
      <State
        loading={loading}
        error={error}
        empty={!rows.length}
        labels={{
          loading: 'Loading regime model…',
          empty: 'Market regime model unavailable.',
        }}
      >
        {rows.map(([label, value]) => (
          <div className="ld-regime-row" key={label}>
            <span className="ld-label">{label}</span>
            <span className="ld-regime-val">{value}</span>
          </div>
        ))}
        {(regime?.drivers || []).length ? (
          <div className="ld-view">
            <div className="ld-label" style={{ marginBottom: '0.35rem' }}>Engine drivers</div>
            {regime.drivers.slice(0, 4).map((driver, index) => (
              <div key={index} className="ld-feed-body">
                {typeof driver === 'string' ? driver : driver?.label || driver?.name || ''}
              </div>
            ))}
          </div>
        ) : null}
      </State>
    </Card>
  );
}
