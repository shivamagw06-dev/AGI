import { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import { listPublishedMarketActivities } from '@/lib/marketActivitiesApi';

function formatWhen(value) {
  if (!value) return '';
  try {
    return new Date(value).toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

/**
 * Right-rail updates for Market Intelligence — short admin one/two-liners.
 */
export default function MarketActivitiesRail({ limit = 8, className = '' }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    listPublishedMarketActivities({ limit })
      .then((rows) => {
        if (active) setItems(rows);
      })
      .catch(() => {
        if (active) setItems([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [limit]);

  return (
    <aside
      className={`rounded-xl border border-[#dde1e6] bg-white p-5 sm:p-6 ${className}`}
      aria-label="Activities"
    >
      <div className="flex items-center gap-2">
        <Activity className="h-4 w-4 text-[#274c77]" />
        <h2 className="text-lg font-bold text-[#18202b]">Activities</h2>
      </div>
      <p className="mt-1 text-xs text-[#737982]">Desk updates — short notes from the research team.</p>

      {loading ? (
        <div className="mt-5 space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-[#f3f5f7]" />
          ))}
        </div>
      ) : !items.length ? (
        <p className="mt-5 rounded-lg border border-dashed border-[#dde1e6] px-3 py-6 text-center text-sm text-[#737982]">
          No activities yet. Admins can post short updates from Admin → Activities.
        </p>
      ) : (
        <ul className="mt-5 space-y-3">
          {items.map((item) => (
            <li key={item.id} className="rounded-lg border border-[#e8eaee] bg-[#f8fafb] px-3.5 py-3">
              <p className="text-sm leading-snug text-[#18202b]">{item.body}</p>
              {item.created_at ? (
                <p className="mt-1.5 text-[10px] font-semibold uppercase tracking-wide text-[#8a919c]">
                  {formatWhen(item.created_at)}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
