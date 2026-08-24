import { Card, State, dirClass, pct, price } from './Primitives';

/**
 * Compact cards for the assets AGI actually prices.
 *
 * The list is whatever the snapshot returns, not a fixed roster. A desk that
 * shows a tile for an instrument it cannot price teaches the reader to
 * distrust the ones it can.
 */
export default function MarketPulse({ items, loading, error, stale }) {
  return (
    <Card
      title="Market Pulse"
      right={stale ? <span className="ld-label ld-stale">Data delayed</span> : null}
    >
      <State
        loading={loading}
        error={error}
        empty={!items?.length}
        labels={{ loading: 'Loading market data…', empty: 'Market data temporarily unavailable.' }}
      >
        <div className="ld-pulse">
          {(items || []).map((row) => (
            <div className="ld-pulse-card" key={row.name}>
              <div className="ld-pulse-name">{row.name}</div>
              <div className="ld-pulse-value">{price(row.price)}</div>
              <div className={`ld-pulse-chg ${dirClass(row.percentChange)}`}>
                {pct(row.percentChange)}
              </div>
            </div>
          ))}
        </div>
      </State>
    </Card>
  );
}
