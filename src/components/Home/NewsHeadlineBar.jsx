import { useEffect, useState } from 'react';
import { Newspaper } from 'lucide-react';
import { API_ORIGIN } from '@/config';

const REFRESH_MS = 30 * 60 * 1000;

export default function NewsHeadlineBar() {
  const [headlines, setHeadlines] = useState([]);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetch(`${API_ORIGIN || ''}/api/news/headlines`);
        const data = await response.json();
        if (active && Array.isArray(data.items)) setHeadlines(data.items);
      } catch {
        /* Headlines are supplementary; do not interrupt public market intelligence. */
      }
    }

    load();
    const interval = window.setInterval(load, REFRESH_MS);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  if (!headlines.length) return null;
  const loop = [...headlines, ...headlines];

  return (
    <section className="mt-5 border border-[#dde1e6] bg-white" aria-label="Latest business headlines">
      <div className="flex items-stretch">
        <div className="hidden shrink-0 items-center gap-2 border-r border-[#dde1e6] bg-[#f8fafb] px-4 sm:flex">
          <Newspaper className="h-4 w-4 text-[#274c77]" />
          <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#18202b]">Headlines</span>
        </div>
        <div className="agi-headline-ticker min-w-0 flex-1 py-3">
          <div className="agi-headline-ticker-track">
            {loop.map((headline, index) => (
              <a
                key={`${headline.url}-${index}`}
                href={headline.url}
                target="_blank"
                rel="noreferrer"
                className="flex shrink-0 items-center gap-2 pr-8 text-xs text-[#374151] hover:text-[#274c77]"
                title={`${headline.source} — ${headline.title}`}
              >
                <span className="font-bold text-[#59616d]">{headline.source}</span>
                <span className="max-w-[360px] truncate">{headline.title}</span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
