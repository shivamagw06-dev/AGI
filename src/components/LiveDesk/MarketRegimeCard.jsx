import { Card, State } from './Primitives';

/**
 * AGI's regime read, or an explicit absence.
 *
 * The intelligence engine returns the literal string "Unavailable" when it is
 * degraded. That is not a regime and is filtered out upstream, so this panel
 * shows the unavailable state rather than presenting the engine's error as a
 * market condition.
 */
export default function MarketRegimeCard({ regime, flows, loading, error }) {
  const breadth = regime?.breadth;
  const rows = [];
  if (regime?.regime) rows.push(['Regime', regime.regime]);
  if (regime?.health?.overall) rows.push(['Market health', regime.health.overall]);
  if (breadth && Number.isFinite(Number(breadth.advancing)) && Number.isFinite(Number(breadth.declining))) {
    const advancing = Number(breadth.advancing);
    const declining = Number(breadth.declining);
    rows.push(['Breadth', `${advancing} advancing / ${declining} declining`]);
  }
  if (breadth?.sentiment) rows.push(['Sentiment', breadth.sentiment]);
  // FII/DII is India-only. The latest day can be present with no figures on it,
  // which the engine reports separately - so the trend is shown when the day is
  // not yet populated, rather than a blank row implying no flows.
  if (flows) {
    if (flows.hasLatest && flows.fiiNet !== null) {
      rows.push(['FII net', `${flows.fiiNet > 0 ? '+' : ''}${flows.fiiNet.toLocaleString('en-IN')} Cr`]);
    }
    if (flows.hasLatest && flows.diiNet !== null) {
      rows.push(['DII net', `${flows.diiNet > 0 ? '+' : ''}${flows.diiNet.toLocaleString('en-IN')} Cr`]);
    }
    if (!flows.hasLatest && flows.trend5d !== null) {
      rows.push(['Flows, 5d', `${flows.trend5d > 0 ? '+' : ''}${flows.trend5d.toLocaleString('en-IN')} Cr`]);
    }
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
