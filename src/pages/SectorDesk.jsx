import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate, useParams } from 'react-router-dom';
import DiscoveryRail from '@/components/Product/DiscoveryRail';
import { getUiSector } from '@/lib/uiApi';
import { trackProductEvent } from '@/lib/productAnalytics';

function Block({ title, children }) {
  return (
    <section className="border border-[#dddddd] p-5 bg-white">
      <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">{title}</h2>
      <div className="mt-3 text-sm text-[#333] leading-relaxed">{children}</div>
    </section>
  );
}

export default function SectorDesk() {
  const { sectorId } = useParams();
  const navigate = useNavigate();
  const [state, setState] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let active = true;
    setState({ loading: true, data: null, error: null });
    getUiSector(sectorId)
      .then((data) => {
        if (!active) return;
        setState({ loading: false, data, error: null });
        trackProductEvent('sector_viewed', { sectorId });
      })
      .catch((error) => active && setState({ loading: false, data: null, error }));
    return () => {
      active = false;
    };
  }, [sectorId]);

  const data = state.data;
  const onAsk = (q) => navigate(`/ask?q=${encodeURIComponent(q)}`);
  const valuation = data?.valuation_summary || {};

  return (
    <div className="bg-white min-h-screen">
      <Helmet>
        <title>{`${sectorId} Sector Intelligence | Agarwal Global Investments`}</title>
        <meta name="description" content={`AGI sector intelligence for ${sectorId}: outlook, leaders, risks, valuation and research.`} />
        <link rel="canonical" href={`https://agarwalglobalinvestments.com/sectors/${encodeURIComponent(sectorId || '')}`} />
        <meta property="og:title" content={`${sectorId} Sector | AGI`} />
        <script type="application/ld+json">
          {JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'CollectionPage',
            name: `${sectorId} Sector Intelligence`,
          })}
        </script>
      </Helmet>

      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-8">
        <Link to="/research" className="text-xs font-bold text-[#111] hover:text-[#ff6600]">← Research</Link>
        <p className="mt-4 text-[11px] font-bold uppercase tracking-wider text-[#ff6600]">Sector Intelligence</p>
        <h1 className="mt-2 text-3xl font-bold text-[#111111]">{sectorId}</h1>
        <p className="mt-2 text-sm text-[#767676]">
          Outlook: {data?.current_outlook || data?.sector_health || '—'}
        </p>

        {state.loading ? (
          <div className="mt-8 space-y-3" aria-busy="true">
            <div className="h-28 bg-[#eee] animate-pulse" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="h-32 bg-[#eee] animate-pulse" />
              <div className="h-32 bg-[#eee] animate-pulse" />
            </div>
          </div>
        ) : state.error ? (
          <div className="mt-8 border border-[#dddddd] p-6">
            <p className="text-sm font-bold">Sector intelligence temporarily unavailable</p>
            <Link to={`/ask?q=${encodeURIComponent(`What is AGI's outlook for ${sectorId}?`)}`} className="inline-block mt-3 text-xs font-bold hover:text-[#ff6600]">
              Ask AGI →
            </Link>
          </div>
        ) : (
          <div className="mt-8 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Block title="Current outlook / sector health">
                <p className="text-lg font-bold text-[#111]">{data?.current_outlook || data?.sector_health || '—'}</p>
                <p className="text-xs text-[#767676] mt-2">Theme focus: {data?.current_theme || sectorId}</p>
              </Block>
              <Block title="Sector valuation">
                <p className="font-bold text-[#111]">{valuation.label || 'Snapshot'}</p>
                <p className="text-xs text-[#767676] mt-2">
                  {Object.keys(valuation.detail || data?.valuation_snapshot || {}).length
                    ? `${Object.keys(valuation.detail || data?.valuation_snapshot || {}).length} allocation signals`
                    : 'Valuation context loads with portfolio coverage.'}
                </p>
              </Block>
              <Block title="Leading companies">
                <div className="flex flex-wrap gap-2">
                  {(data?.leaders || []).map((t) => (
                    <Link key={t} to={`/research/stocks/${encodeURIComponent(t)}`} className="text-xs font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]">
                      {t}
                    </Link>
                  ))}
                  {(data?.leaders || []).length === 0 && <p className="text-xs text-[#767676]">Leaders appear with coverage.</p>}
                </div>
              </Block>
              <Block title="Lagging companies">
                <div className="flex flex-wrap gap-2">
                  {(data?.laggards || []).map((t) => (
                    <Link key={t} to={`/research/stocks/${encodeURIComponent(t)}`} className="text-xs font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]">
                      {t}
                    </Link>
                  ))}
                  {(data?.laggards || []).length === 0 && <p className="text-xs text-[#767676]">Laggards appear with coverage.</p>}
                </div>
              </Block>
              <Block title="Current risks">
                <ul className="space-y-2">
                  {(data?.current_risks || []).map((r) => <li key={r}>• {r}</li>)}
                  {(data?.current_risks || []).length === 0 && <li className="text-[#767676]">No material sector risks tagged yet.</li>}
                </ul>
              </Block>
              <Block title="Current opportunities">
                <ul className="space-y-2">
                  {(data?.current_opportunities || []).map((r) => <li key={r}>• {r}</li>)}
                </ul>
              </Block>
            </div>

            <Block title="Macro drivers">
              <div className="flex flex-wrap gap-2">
                {(data?.macro_drivers || []).map((m) => (
                  <Link key={m} to="/macro-intelligence" className="text-xs font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]">
                    {m}
                  </Link>
                ))}
                {(data?.macro_drivers || []).length === 0 && (
                  <Link to="/macro-intelligence" className="text-xs font-bold hover:text-[#ff6600]">
                    Open Macro Intelligence →
                  </Link>
                )}
              </div>
            </Block>

            <Block title="Sector timeline">
              <ol className="space-y-3">
                {(data?.sector_timeline || []).slice(0, 12).map((ev, idx) => (
                  <li key={idx} className="border-l-2 border-[#ff6600] pl-3">
                    <p className="text-[10px] font-bold uppercase text-[#767676]">
                      {ev.as_of ? String(ev.as_of).slice(0, 10) : 'Undated'} · {ev.type || 'research'}
                    </p>
                    <p className="text-sm font-bold mt-0.5">{ev.title || ev.label}</p>
                  </li>
                ))}
                {(data?.sector_timeline || []).length === 0 && (
                  <p className="text-xs text-[#929292]">Timeline fills as sector research is published.</p>
                )}
              </ol>
            </Block>

            <Block title="Current research">
              <ul className="space-y-2">
                {(data?.current_research || []).slice(0, 10).map((r, idx) => (
                  <li key={r.research_id || r.id || idx} className="text-sm border-b border-[#eee] pb-2">
                    {(r.research_id || r.id) ? (
                      <Link to={`/article/${encodeURIComponent(r.research_id || r.id)}`} className="font-bold hover:text-[#ff6600]">
                        {r.title || r.id}
                      </Link>
                    ) : (
                      r.title || r.id
                    )}
                  </li>
                ))}
              </ul>
            </Block>

            <Block title="Suggested follow-up questions">
              <div className="flex flex-wrap gap-2">
                {(data?.follow_up_questions || []).map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => onAsk(q)}
                    className="text-[11px] border border-[#ddd] px-3 py-1.5 text-left hover:border-[#111] hover:text-[#ff6600]"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </Block>

            <DiscoveryRail discovery={data?.discovery} onAsk={onAsk} />
          </div>
        )}
      </div>
    </div>
  );
}
