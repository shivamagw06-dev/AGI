import { useMemo, useState } from 'react';
import { Download } from 'lucide-react';

const FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'investment', label: 'Investments' },
  { value: 'fund', label: 'Funds' },
  { value: 'transaction', label: 'Transactions' },
  { value: 'news', label: 'News' },
  { value: 'founded', label: 'Founded' },
  { value: 'exit', label: 'Exits' },
  { value: 'appointment', label: 'People' },
];

export default function EntityTimeline({ events, title = 'Timeline' }) {
  const [filter, setFilter] = useState('all');

  const filtered = useMemo(() => {
    if (!events?.length) return [];
    let rows = [...events].sort((a, b) => new Date(b.occurred_at) - new Date(a.occurred_at));
    if (filter !== 'all') {
      rows = rows.filter((e) => e.event_type === filter || e.event_type?.includes(filter));
    }
    return rows;
  }, [events, filter]);

  const exportTimeline = () => {
    const headers = ['Date', 'Type', 'Title', 'Description'];
    const lines = [headers.join(',')];
    filtered.forEach((e) => {
      lines.push([
        e.occurred_at,
        e.event_type,
        e.title,
        e.description || '',
      ].map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','));
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'entity-timeline.csv';
    a.click();
  };

  if (!events?.length) {
    return <p className="text-sm text-[var(--pe-muted)]">No timeline events yet.</p>;
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <h2 className="font-serif text-xl font-semibold">{title}</h2>
        <div className="flex flex-wrap gap-2 items-center">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => setFilter(f.value)}
              className={`px-3 py-1 text-[11px] font-medium uppercase tracking-wide border rounded-sm ${
                filter === f.value
                  ? 'bg-[var(--pe-accent)] text-white border-[var(--pe-accent)]'
                  : 'border-[var(--pe-border)] text-[var(--pe-muted)] hover:border-[var(--pe-accent)]'
              }`}
            >
              {f.label}
            </button>
          ))}
          <button type="button" className="pe-btn text-xs flex items-center gap-1" onClick={exportTimeline}>
            <Download size={12} /> Export
          </button>
        </div>
      </div>

      <ol className="relative border-l-2 border-[var(--pe-border)] ml-4 space-y-0">
        {filtered.map((event, i) => (
          <li key={event.id} className="relative pl-8 pb-8 last:pb-0">
            <span
              className="absolute -left-[7px] top-1 w-3 h-3 rounded-full border-2 border-white"
              style={{ background: i === 0 ? 'var(--pe-accent)' : '#cbd5e1' }}
            />
            <time className="text-[10px] uppercase tracking-wider text-[var(--pe-muted)]">
              {new Date(event.occurred_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short' })}
            </time>
            <p className="font-medium mt-1 text-[var(--pe-text)]">{event.title}</p>
            {event.description && (
              <p className="text-sm text-[var(--pe-muted)] mt-1 leading-relaxed max-w-2xl">{event.description}</p>
            )}
            <span className="inline-block mt-2 text-[9px] uppercase tracking-wider text-[var(--pe-muted)] border border-[var(--pe-border)] px-2 py-0.5">
              {event.event_type}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
