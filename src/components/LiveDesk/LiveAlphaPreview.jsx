import { Link } from 'react-router-dom';
import { ENGINE_PLAIN } from '@/lib/liveAlphaDashboardModel';
import { Card, State } from './Primitives';

/** A count per engine, read from Live Alpha's own workspace endpoint.
 *  The signal engine is not reimplemented here - this is a window onto it. */
export default function LiveAlphaPreview({ liveAlpha, loading, error }) {
  const engines = liveAlpha?.engines || [];
  return (
    <Card
      title="Live Alpha"
      right={liveAlpha?.stale ? <span className="ld-label ld-stale">Stale</span> : null}
      tight
    >
      <State
        loading={loading}
        error={error}
        empty={!engines.length}
        labels={{ loading: 'Loading Live Alpha…', empty: 'No Live Alpha signals available.' }}
      >
        <div className="ld-card-body">
          {engines.map(({ engine, count }) => (
            <div className="ld-regime-row" key={engine}>
              <span>{ENGINE_PLAIN?.[engine]?.label || engine}</span>
              <span className="ld-num">{count} {count === 1 ? 'signal' : 'signals'}</span>
            </div>
          ))}
          <div style={{ marginTop: '0.8rem' }}>
            <Link to="/live-alpha" style={{ color: 'var(--ld-accent)', fontSize: '0.8rem', textDecoration: 'none' }}>
              Open Live Alpha →
            </Link>
          </div>
        </div>
      </State>
    </Card>
  );
}
