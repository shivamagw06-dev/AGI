import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate, useParams } from 'react-router-dom';
import DiscoveryRail from '@/components/Product/DiscoveryRail';
import { getUiTheme } from '@/lib/uiApi';
import { toggleFavouriteTheme, getFavouriteThemes } from '@/lib/searchHistory';
import { trackProductEvent } from '@/lib/productAnalytics';

function Block({ title, children, className = '' }) {
  return (
    <section className={`border border-[#dddddd] p-5 bg-white ${className}`}>
      <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">{title}</h2>
      <div className="mt-3 text-sm text-[#333] leading-relaxed">{children}</div>
    </section>
  );
}

function fmtConf(v) {
  if (v == null) return '—';
  const n = Number(v);
  if (Number.isNaN(n)) return '—';
  return n <= 1 ? `${Math.round(n * 100)}%` : `${Math.round(n)}%`;
}

export default function ThemeDesk() {
  const { themeId } = useParams();
  const navigate = useNavigate();
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [favs, setFavs] = useState(() => getFavouriteThemes());

  useEffect(() => {
    let active = true;
    setState({ loading: true, data: null, error: null });
    getUiTheme(themeId)
      .then((data) => {
        if (!active) return;
        setState({ loading: false, data, error: null });
        trackProductEvent('theme_viewed', { themeId });
      })
      .catch((error) => active && setState({ loading: false, data: null, error }));
    return () => {
      active = false;
    };
  }, [themeId]);

  const data = state.data;
  const houseLabel =
    data?.stance ||
    data?.house_view?.current_view ||
    data?.house_view?.stance ||
    data?.house_view?.label ||
    'Under review';
  const kg = data?.knowledge_graph?.buckets || {};
  const onAsk = (q) => navigate(`/ask?q=${encodeURIComponent(q)}`);

  return (
    <div className="bg-white min-h-screen">
      <Helmet>
        <title>{`${themeId} Theme Intelligence | Agarwal Global Investments`}</title>
        <meta name="description" content={`AGI theme intelligence for ${themeId}: thesis, confidence, companies, risks and catalysts.`} />
        <link rel="canonical" href={`https://agarwalglobalinvestments.com/themes/${encodeURIComponent(themeId || '')}`} />
        <meta property="og:title" content={`${themeId} Theme | AGI`} />
        <meta property="og:description" content="Institutional investment theme hub — thesis, evidence and discovery." />
        <script type="application/ld+json">
          {JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'CollectionPage',
            name: `${themeId} Theme Intelligence`,
            description: data?.current_thesis || `AGI theme desk for ${themeId}`,
          })}
        </script>
      </Helmet>

      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link to="/" className="text-xs font-bold text-[#111] hover:text-[#ff6600]">← Home</Link>
          <button
            type="button"
            onClick={() => setFavs(toggleFavouriteTheme(themeId))}
            className="text-xs font-bold border border-[#ddd] px-3 py-1.5 hover:border-[#111]"
          >
            {favs.includes(themeId) ? 'Saved theme' : 'Save theme'}
          </button>
        </div>

        <p className="mt-4 text-[11px] font-bold uppercase tracking-wider text-[#ff6600]">Theme Intelligence</p>
        <h1 className="mt-2 text-3xl font-bold text-[#111111]">{themeId}</h1>
        <p className="mt-2 text-sm text-[#555] max-w-3xl">
          {data?.current_thesis || 'Institutional theme hub — thesis, exposure, risks and research.'}
        </p>

        {state.loading ? (
          <div className="mt-8 space-y-3" aria-busy="true">
            <div className="h-28 bg-[#eee] animate-pulse" />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="h-32 bg-[#eee] animate-pulse" />
              <div className="h-32 bg-[#eee] animate-pulse" />
              <div className="h-32 bg-[#eee] animate-pulse" />
            </div>
          </div>
        ) : state.error ? (
          <div className="mt-8 border border-[#dddddd] p-6">
            <p className="text-sm font-bold text-[#111]">Theme intelligence temporarily unavailable</p>
            <p className="text-xs text-[#767676] mt-2">Try Ask AGI or explore related sectors.</p>
            <Link to={`/ask?q=${encodeURIComponent(`What is AGI's view on ${themeId}?`)}`} className="inline-block mt-3 text-xs font-bold hover:text-[#ff6600]">
              Ask AGI about {themeId} →
            </Link>
          </div>
        ) : (
          <div className="mt-8 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Block title="Current thesis">
                <p className="font-bold text-[#111]">{data?.current_thesis || 'Forming'}</p>
              </Block>
              <Block title="House view">
                <p className="text-lg font-bold text-[#111]">{houseLabel}</p>
              </Block>
              <Block title="Confidence">
                <p className="text-lg font-bold text-[#111]">{fmtConf(data?.confidence)}</p>
              </Block>
              <Block title="Freshness">
                <p className="font-bold capitalize text-[#111]">{data?.product_meta?.freshness_indicator || 'unknown'}</p>
                <p className="text-[11px] text-[#767676] mt-1">
                  Evidence {data?.product_meta?.evidence_count ?? 0} · Research {data?.product_meta?.research_count ?? 0}
                </p>
              </Block>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Block title="Companies exposed">
                <div className="flex flex-wrap gap-2">
                  {(data?.related_companies || []).map((t) => (
                    <Link key={t} to={`/research/stocks/${encodeURIComponent(t)}`} className="text-xs font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]">
                      {t}
                    </Link>
                  ))}
                  {(data?.related_companies || []).length === 0 && (
                    <p className="text-xs text-[#767676]">No linked companies yet.</p>
                  )}
                </div>
              </Block>
              <Block title="Related macro">
                <div className="flex flex-wrap gap-2">
                  {(data?.related_macro || []).map((t) => (
                    <Link key={t} to={`/macro-intelligence`} className="text-xs font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]">
                      {t}
                    </Link>
                  ))}
                  {(data?.related_macro || []).length === 0 && <p className="text-xs text-[#767676]">Macro links appear as knowledge grows.</p>}
                </div>
              </Block>
              <Block title="Current risks">
                <ul className="space-y-2">
                  {(data?.current_risks || []).map((r) => <li key={r}>• {r}</li>)}
                  {(data?.current_risks || []).length === 0 && <li className="text-[#767676]">No risks tagged yet.</li>}
                </ul>
              </Block>
              <Block title="Current catalysts">
                <ul className="space-y-2">
                  {(data?.current_catalysts || []).map((r) => <li key={r}>• {r}</li>)}
                  {(data?.current_catalysts || []).length === 0 && <li className="text-[#767676]">No catalysts tagged yet.</li>}
                </ul>
              </Block>
            </div>

            <Block title="Research timeline">
              <ol className="space-y-3">
                {(data?.research_timeline || data?.timeline || []).slice(0, 12).map((ev, idx) => (
                  <li key={idx} className="border-l-2 border-[#ff6600] pl-3">
                    <p className="text-[10px] font-bold uppercase text-[#767676]">
                      {ev.as_of ? String(ev.as_of).slice(0, 10) : 'Undated'} · {ev.type || 'event'}
                    </p>
                    <p className="text-sm font-bold text-[#111] mt-0.5">{ev.title || ev.label}</p>
                  </li>
                ))}
                {(data?.research_timeline || data?.timeline || []).length === 0 && (
                  <p className="text-xs text-[#929292]">Timeline populates as research is ingested.</p>
                )}
              </ol>
            </Block>

            <Block title="Knowledge graph">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {Object.entries(kg).slice(0, 9).map(([key, vals]) => (
                  <div key={key} className="border border-[#eee] p-3">
                    <p className="text-[10px] font-bold uppercase text-[#767676] mb-2">{key.replace(/_/g, ' ')}</p>
                    <div className="flex flex-wrap gap-1">
                      {(vals || []).slice(0, 4).map((v) => (
                        <span key={v} className="text-[11px] border border-[#ddd] px-1.5 py-0.5">{v}</span>
                      ))}
                      {(vals || []).length === 0 && <span className="text-[11px] text-[#929292]">—</span>}
                    </div>
                  </div>
                ))}
              </div>
            </Block>

            <Block title="Related research">
              <ul className="space-y-2">
                {(data?.related_research || []).slice(0, 8).map((r, idx) => (
                  <li key={r.id || r.title || idx} className="text-sm border-b border-[#eee] pb-2">
                    {r.id ? (
                      <Link to={`/article/${encodeURIComponent(r.id)}`} className="font-bold hover:text-[#ff6600]">
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
