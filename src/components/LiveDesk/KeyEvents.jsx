import { Card, State } from './Primitives';

/** Scheduled events from AGI's economic calendar. Nothing is synthesised:
 *  if the calendar is empty the panel says so. */
export default function KeyEvents({ events, loading, error }) {
  return (
    <Card title="Key Events" tight>
      <State
        loading={loading}
        error={error}
        empty={!events?.length}
        labels={{ loading: 'Loading events…', empty: 'No scheduled events on the AGI calendar.' }}
      >
        <div className="ld-feed">
          {(events || []).map((event) => {
            const assets = [
              ...(Array.isArray(event.affected_sectors) ? event.affected_sectors : []),
            ].slice(0, 3);
            const importance = String(event.importance || '').toLowerCase();
            return (
              <div className="ld-feed-item" key={event.id || event.title}>
                <div className="ld-feed-meta">
                  <span className="ld-label">{event.when || event.date || 'Scheduled'}</span>
                  {event.country ? <span className="ld-chip">{event.country}</span> : null}
                  {importance === 'high' ? <span className="ld-chip ld-chip-notable">High impact</span> : null}
                </div>
                <div className="ld-feed-head">{event.title}</div>
                {event.expected_impact ? (
                  <div className="ld-feed-body">{event.expected_impact}</div>
                ) : null}
                {assets.length ? (
                  <div className="ld-feed-body" style={{ color: 'var(--ld-faint)' }}>
                    {assets.join(' · ')}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </State>
    </Card>
  );
}
