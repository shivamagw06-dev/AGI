import { useMemo, useState } from 'react';
import { FILTERS, applyFilter } from '@/lib/liveDeskIntelligence';
import { Card, State, dirClass, pct } from './Primitives';

/** The same intelligence items, read chronologically and filterable.
 *  Filtering is client-side over data already fetched, so changing a filter
 *  costs no request and cannot show a different session to the panel above. */
export default function LiveIntelligenceTimeline({ items, loading, error }) {
  const [filter, setFilter] = useState('ALL');
  const filtered = useMemo(() => applyFilter(items || [], filter), [items, filter]);

  return (
    <Card title="Live Intelligence" tight>
      <div className="ld-filters">
        {FILTERS.map((name) => (
          <button
            key={name}
            type="button"
            className={name === filter ? 'ld-filter ld-filter-on' : 'ld-filter'}
            onClick={() => setFilter(name)}
          >
            {name}
          </button>
        ))}
      </div>
      <State
        loading={loading}
        error={error}
        empty={!filtered.length}
        labels={{
          loading: 'Loading intelligence…',
          empty: filter === 'ALL'
            ? 'No high-confidence intelligence signals right now.'
            : `No signals in ${filter} right now.`,
        }}
      >
        <div className="ld-feed">
          {filtered.map((item) => (
            <div className="ld-feed-item" key={`tl-${item.id}`}>
              <div className="ld-feed-meta">
                {item.time ? <span className="ld-label">{item.time}</span> : null}
                <span className="ld-chip">{item.category}</span>
                {item.geography ? <span className="ld-chip">{item.geography}</span> : null}
              </div>
              <div className="ld-feed-head">
                {item.headline}
                {typeof item.changePct === 'number' ? (
                  <span className={`ld-num ${dirClass(item.changePct)}`} style={{ marginLeft: '0.5rem', fontSize: '0.86rem' }}>
                    {pct(item.changePct)}
                  </span>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </State>
    </Card>
  );
}
