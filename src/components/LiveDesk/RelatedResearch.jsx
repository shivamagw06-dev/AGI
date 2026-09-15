import { Link } from 'react-router-dom';
import { Card, State } from './Primitives';

/** AGI research, linked by the href the feed supplies. Items without one are
 *  dropped rather than pointed at a guessed route, so there are no dead links. */
export default function RelatedResearch({ research, loading, error }) {
  const items = (research || []).filter((item) => item?.href && item?.title);
  return (
    <Card title="Related AGI Research" tight>
      <State
        loading={loading}
        error={error}
        empty={!items.length}
        labels={{ loading: 'Loading research…', empty: 'No related research available.' }}
      >
        <div className="ld-feed">
          {items.map((item) => {
            const external = /^https?:\/\//i.test(item.href);
            const inner = (
              <>
                <div className="ld-research-title">{item.title}</div>
                {item.summary ? <div className="ld-research-sum">{item.summary}</div> : null}
                {item.category ? (
                  <div className="ld-research-sum" style={{ color: 'var(--ld-faint)' }}>{item.category}</div>
                ) : null}
              </>
            );
            return external ? (
              <a className="ld-research-item" key={item.id || item.href} href={item.href}
                 target="_blank" rel="noopener noreferrer">{inner}</a>
            ) : (
              <Link className="ld-research-item" key={item.id || item.href} to={item.href}>{inner}</Link>
            );
          })}
        </div>
      </State>
    </Card>
  );
}
