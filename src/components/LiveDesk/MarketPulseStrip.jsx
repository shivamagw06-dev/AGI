import { MISSING } from '@/lib/liveDeskIntelligence';
import { Card, State, dirClass, pct, price } from './Primitives';

/** India first, then global, then the instruments AGI does not price.
 *  Grouped rather than mixed so a reader can find their market at a glance. */
const ORDER = {
  NIFTY: 1, 'BANK NIFTY': 2, SENSEX: 3, MIDCAP: 4, SMALLCAP: 5, 'INDIA VIX': 6, USDINR: 7,
  'S&P': 10, NASDAQ: 11, Dow: 12, Brent: 13, Gold: 14, Silver: 15, Bitcoin: 16,
};

export default function MarketPulseStrip({ items, loading, error, stale, updatedLabel }) {
  const sorted = [...(items || [])].sort(
    (a, b) => (ORDER[a?.name] ?? 99) - (ORDER[b?.name] ?? 99)
  );

  return (
    <Card
      title="AGI Market Pulse"
      right={
        <span className={stale ? 'ld-label ld-stale' : 'ld-refresh'}>
          {stale ? 'Data delayed' : updatedLabel || ''}
        </span>
      }
    >
      <State
        loading={loading}
        error={error}
        empty={!sorted.length}
        labels={{ loading: 'Loading market data…', empty: 'Market data temporarily unavailable.' }}
      >
        <div className="ld-pulse">
          {sorted.map((row) => (
            <div className="ld-pulse-card" key={row.name}>
              <div className="ld-pulse-name">{row.name}</div>
              <div className="ld-pulse-value">{price(row.price)}</div>
              <div className={`ld-pulse-chg ${dirClass(row.percentChange)}`}>{pct(row.percentChange)}</div>
            </div>
          ))}
          {/* Shown as unpriced rather than omitted. A strip with no US 10Y reads
              as "rates are quiet", and a reader who believes that once will not
              trust the tiles that are real. */}
          {MISSING.map((row) => (
            <div className="ld-pulse-card ld-pulse-missing" key={row.label}>
              <div className="ld-pulse-name">{row.label}</div>
              <div className="ld-pulse-value">—</div>
              <div className="ld-pulse-chg ld-flat">Not priced by AGI</div>
            </div>
          ))}
        </div>
      </State>
    </Card>
  );
}
