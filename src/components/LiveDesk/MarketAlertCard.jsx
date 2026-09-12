import { Card, State, pct } from './Primitives';

/**
 * Only rendered when a threshold is actually crossed.
 *
 * The note states the threshold rather than a percentile. The snapshot carries
 * no historical distribution, so "94th percentile of the last 12 months" would
 * be a statistic with nothing behind it - which is exactly the sort of number
 * a reader would rely on.
 */
export default function MarketAlertCard({ alerts, loading }) {
  if (loading) return null;
  if (!alerts?.length) return null;

  return (
    <Card title="What Needs Attention" tight>
      <State loading={false} error={null} empty={false}>
        <div className="ld-feed">
          {alerts.map((alert) => (
            <div className="ld-feed-item" key={alert.label}>
              <div className="ld-feed-meta">
                <span className={alert.severity === 'MAJOR' ? 'ld-chip ld-chip-major' : 'ld-chip ld-chip-notable'}>
                  {alert.severity}
                </span>
                <span className="ld-label">{alert.label}</span>
              </div>
              <div className="ld-feed-head ld-num">{pct(alert.changePct)}</div>
              <div className="ld-feed-body">
                {alert.note} Flagged because the session move exceeds {alert.threshold}%.
              </div>
            </div>
          ))}
        </div>
      </State>
    </Card>
  );
}
