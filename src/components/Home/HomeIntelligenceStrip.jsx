/**
 * Live Investment Office intelligence for the homepage.
 * Preserves editorial layout language — no redesign.
 */
import { Link } from 'react-router-dom';
import useUiHome from '@/hooks/useUiHome';

function Panel({ title, subtitle, children, href, linkLabel = 'Open →' }) {
  return (
    <div className="border border-[#dddddd] p-4 h-full">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wide text-[#767676]">{title}</h3>
          {subtitle && <p className="text-[11px] text-[#929292] mt-1">{subtitle}</p>}
        </div>
        {href && (
          <Link to={href} className="text-[11px] font-bold text-[#111111] hover:text-[#ff6600] shrink-0">
            {linkLabel}
          </Link>
        )}
      </div>
      {children}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="border border-[#eeeeee] p-3">
      <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676]">{label}</p>
      <p className="mt-1 text-sm font-bold text-[#111111]">{value || '—'}</p>
    </div>
  );
}

export default function HomeIntelligenceStrip() {
  const { data, loading, error } = useUiHome();

  if (error && !data) {
    return null; // keep homepage calm if engine offline — existing CMS sections remain
  }

  const brief = data?.market_brief;
  const themes = data?.market_themes || [];
  const research = data?.latest_published?.length ? data.latest_published : data?.todays_research || [];
  const news = data?.latest_news || [];
  const health = data?.system_health;
  const calendar = data?.economic_calendar || [];
  const composite = data?.composite_view;

  return (
    <section className="py-8 border-b border-[#dddddd]">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-[#111111]">Institutional Desk Pulse</h2>
          <p className="text-sm text-[#767676] mt-1">
            Live regime, risk, research and knowledge from the AGI Investment Office
          </p>
        </div>
        <Link to="/market-intelligence" className="text-xs font-bold text-[#111111] hover:text-[#ff6600] hidden sm:block">
          Market desk →
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 bg-[#eee] animate-pulse" />
          ))}
        </div>
      ) : (
        <>
          {brief?.summary && (
            <div className="mb-6 p-4 bg-[#fafafa] border border-[#eeeeee] border-l-4 border-l-[#ff6600]">
              <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676] mb-2">
                {brief.title || "Today's AGI Market Brief"}
              </p>
              <p className="text-sm text-[#333333] leading-relaxed">{brief.summary}</p>
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <Metric label="Composite View" value={composite?.n_names != null ? `${composite.n_names} names` : '—'} />
            <Metric label="Market Regime" value={data?.market_regime?.label} />
            <Metric label="Market Risk" value={data?.market_risk?.label} />
            <Metric
              label="System Health"
              value={
                typeof health?.overall === 'string'
                  ? health.overall
                  : health?.overall?.status || health?.detail?.overall || '—'
              }
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-4">
              <Panel title="Today's Research" subtitle="Research desk" href="/research">
                {(research || []).slice(0, 4).length === 0 ? (
                  <p className="text-xs text-[#767676]">No published research in the live desk yet.</p>
                ) : (
                  <ul className="space-y-3">
                    {research.slice(0, 4).map((r) => (
                      <li key={r.research_id || r.id || r.title} className="border-b border-[#eeeeee] pb-2 last:border-0">
                        <p className="text-sm font-bold text-[#111111] line-clamp-2">{r.title}</p>
                        <p className="text-[11px] text-[#767676] mt-1">
                          {(r.tickers || []).join(', ') || r.status || 'Research'}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </div>

            <div className="lg:col-span-4">
              <Panel title="Latest Knowledge" subtitle="Institutional memory" href="/research">
                {(news || []).slice(0, 4).length === 0 ? (
                  <p className="text-xs text-[#767676]">Knowledge feed will populate as documents are ingested.</p>
                ) : (
                  <ul className="space-y-3">
                    {news.slice(0, 4).map((n) => (
                      <li key={n.id || n.title} className="border-b border-[#eeeeee] pb-2 last:border-0">
                        <p className="text-sm font-bold text-[#111111] line-clamp-2">{n.title}</p>
                        {n.snippet && <p className="text-[11px] text-[#767676] mt-1 line-clamp-2">{n.snippet}</p>}
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </div>

            <div className="lg:col-span-4 space-y-4">
              <Panel title="Market Themes" href="/themes">
                {themes.length === 0 ? (
                  <p className="text-xs text-[#767676]">Themes appear as research is tagged in knowledge.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {themes.slice(0, 8).map((t) => (
                      <Link
                        key={t.id || t.name}
                        to={`/themes/${encodeURIComponent(t.id || t.name)}`}
                        className="text-[11px] font-bold border border-[#dddddd] px-2 py-1 text-[#111111] hover:border-[#111111] hover:text-[#ff6600]"
                      >
                        {t.name || t.id}
                      </Link>
                    ))}
                  </div>
                )}
              </Panel>
              <Panel title="Economic Calendar" subtitle="Event watch" href="/macro-intelligence">
                {calendar.length === 0 ? (
                  <p className="text-xs text-[#767676]">Calendar items load with event intelligence.</p>
                ) : (
                  <ul className="space-y-2">
                    {calendar.slice(0, 3).map((e, idx) => (
                      <li key={e.id || e.title || idx} className="text-xs text-[#333333]">
                        {e.title || e.name}
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </div>
          </div>

          {(composite?.sample || []).length > 0 && (
            <div className="mt-6 border border-[#dddddd] p-4">
              <div className="flex items-end justify-between mb-3">
                <h3 className="text-xs font-bold uppercase tracking-wide text-[#767676]">Composite Book Snapshot</h3>
                <Link to="/portfolio" className="text-[11px] font-bold text-[#111111] hover:text-[#ff6600]">
                  Portfolio →
                </Link>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
                {composite.sample.slice(0, 8).map((row) => (
                  <Link
                    key={row.ticker}
                    to={`/research/stocks/${encodeURIComponent(row.ticker)}`}
                    className="border border-[#eeeeee] p-2 hover:border-[#111111]"
                  >
                    <p className="text-xs font-bold text-[#111111]">{row.ticker}</p>
                    <p className="text-[10px] text-[#767676] mt-1">{row.label}</p>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
