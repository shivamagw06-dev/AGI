import { Card, State } from './Primitives';

/**
 * Scheduled events for one market, from AGI's economic calendar.
 *
 * Split by the calendar's own country field rather than by guessing from the
 * title. GLOBAL-tagged events appear on the global side because that is where
 * a reader looks for an OPEC meeting.
 */
export default function UpcomingEvents({ events, market, loading, error }) {
  const scoped = (events || []).filter((event) => {
    const country = String(event?.country || '').toUpperCase();
    return market === 'INDIA' ? country === 'IN' : country !== 'IN';
  });

  return (
    <Card title={market === 'INDIA' ? 'India Events' : 'Global Events'} tight>
      <State
        loading={loading}
        error={error}
        empty={!scoped.length}
        labels={{
          loading: 'Loading events…',
          empty: `No scheduled ${market === 'INDIA' ? 'India' : 'global'} events on the AGI calendar.`,
        }}
      >
        <div className="ld-feed">
          {scoped.map((event) => {
            const assets = (Array.isArray(event.affected_sectors) ? event.affected_sectors : []).slice(0, 3);
            const high = String(event.importance || '').toLowerCase() === 'high';
            return (
              <div className="ld-feed-item" key={event.id || event.title}>
                <div className="ld-feed-meta">
                  <span className="ld-label">{event.when || event.date || 'Scheduled'}</span>
                  {event.country ? <span className="ld-chip">{event.country}</span> : null}
                  {high ? <span className="ld-chip ld-chip-notable">High impact</span> : null}
                </div>
                <div className="ld-feed-head">{event.title}</div>
                {event.expected_impact ? <div className="ld-feed-body">{event.expected_impact}</div> : null}
                {assets.length ? (
                  <div className="ld-feed-body" style={{ color: 'var(--ld-faint)' }}>{assets.join(' · ')}</div>
                ) : null}
              </div>
            );
          })}
        </div>
      </State>
    </Card>
  );
}
