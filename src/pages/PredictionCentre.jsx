import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import DiscoveryRail from '@/components/Product/DiscoveryRail';
import { getUiPredictions } from '@/lib/uiApi';
import { trackProductEvent } from '@/lib/productAnalytics';

function pct(v) {
  if (v == null) return '—';
  const n = Number(v);
  if (Number.isNaN(n)) return '—';
  return n <= 1 ? `${Math.round(n * 100)}%` : `${Math.round(n)}%`;
}

export default function PredictionCentre() {
  const navigate = useNavigate();
  const [state, setState] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let active = true;
    trackProductEvent('prediction_view');
    getUiPredictions()
      .then((data) => active && setState({ loading: false, data, error: null }))
      .catch((error) => active && setState({ loading: false, data: null, error }));
    return () => {
      active = false;
    };
  }, []);

  const data = state.data;
  const acc = data?.accuracy || {};
  const onAsk = (q) => navigate(`/ask?q=${encodeURIComponent(q)}`);

  return (
    <div className="bg-white min-h-screen">
      <Helmet>
        <title>Prediction Centre | Agarwal Global Investments</title>
        <meta
          name="description"
          content="AGI public prediction tracker — horizons, status, returns, supporting research and historical accuracy."
        />
        <link rel="canonical" href="https://agarwalglobalinvestments.com/predictions" />
        <meta property="og:title" content="AGI Prediction Centre" />
        <script type="application/ld+json">
          {JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'WebPage',
            name: 'AGI Prediction Centre',
            description: 'Public institutional prediction tracker',
          })}
        </script>
      </Helmet>

      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-8">
        <Link to="/" className="text-xs font-bold text-[#111] hover:text-[#ff6600]">← Home</Link>
        <p className="mt-4 text-[11px] font-bold uppercase tracking-wider text-[#ff6600]">Prediction Centre</p>
        <h1 className="mt-2 text-3xl font-bold text-[#111]">Public prediction tracker</h1>
        <p className="mt-2 text-sm text-[#767676] max-w-2xl">
          Track AGI calls with publication date, horizon, status, supporting research and outcomes —
          without exposing internal models.
        </p>

        {state.loading && (
          <div className="mt-8 space-y-3" aria-busy="true">
            <div className="h-24 bg-[#eee] animate-pulse" />
            <div className="h-40 bg-[#eee] animate-pulse" />
          </div>
        )}

        {state.error && (
          <div className="mt-8 border border-[#dddddd] p-6">
            <p className="text-sm font-bold">Prediction desk temporarily unavailable</p>
            <Link to="/ask" className="inline-block mt-3 text-xs font-bold hover:text-[#ff6600]">Ask AGI →</Link>
          </div>
        )}

        {data && (
          <div className="mt-8 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                ['House view accuracy', pct(acc.house_view_accuracy)],
                ['Prediction success', pct(acc.prediction_success)],
                ['Tracked predictions', acc.n ?? (data.predictions || []).length],
                ['Resolved', acc.historical_performance?.resolved ?? '—'],
              ].map(([label, value]) => (
                <section key={label} className="border border-[#dddddd] p-4">
                  <p className="text-[10px] font-bold uppercase text-[#767676]">{label}</p>
                  <p className="mt-2 text-xl font-bold text-[#111]">{value}</p>
                </section>
              ))}
            </div>

            <section className="border border-[#dddddd] p-5">
              <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">Predictions</h2>
              {(data.predictions || []).length === 0 ? (
                <p className="mt-3 text-sm text-[#767676]">
                  Predictions appear as the knowledge desk records forward-looking views.{' '}
                  <Link to="/ask" className="font-bold hover:text-[#ff6600]">Ask AGI</Link> meanwhile.
                </p>
              ) : (
                <ul className="mt-4 space-y-3">
                  {(data.predictions || []).map((p) => (
                    <li key={p.id} className="border border-[#eee] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <Link
                          to={p.ticker ? `/research/stocks/${encodeURIComponent(p.ticker)}` : '/predictions'}
                          className="text-sm font-bold text-[#111] hover:text-[#ff6600]"
                        >
                          {p.ticker || 'Prediction'} · {p.thesis || 'Institutional call'}
                        </Link>
                        <span className="text-[11px] font-bold uppercase border border-[#ddd] px-2 py-0.5">
                          {p.current_status || 'open'}
                        </span>
                      </div>
                      <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-[#555]">
                        <p>Published {p.publication_date ? String(p.publication_date).slice(0, 10) : '—'}</p>
                        <p>Horizon {p.target_horizon || '—'}</p>
                        <p>Return {p.current_return != null ? String(p.current_return) : '—'}</p>
                        <p>Confidence {pct(p.confidence)}</p>
                      </div>
                      {p.outcome && <p className="mt-2 text-xs text-[#333]">Outcome: {p.outcome}</p>}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="border border-[#dddddd] p-5">
              <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">Prediction timeline</h2>
              <ol className="mt-3 space-y-3">
                {(data.prediction_timeline || []).slice(0, 16).map((ev, idx) => (
                  <li key={idx} className="border-l-2 border-[#ff6600] pl-3">
                    <p className="text-[10px] font-bold uppercase text-[#767676]">
                      {ev.as_of ? String(ev.as_of).slice(0, 10) : 'Undated'}
                    </p>
                    <p className="text-sm font-bold mt-0.5">{ev.title}</p>
                    {ev.summary && <p className="text-xs text-[#555] mt-1">{ev.summary}</p>}
                  </li>
                ))}
              </ol>
            </section>

            <section className="border border-[#dddddd] p-5">
              <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">Follow-up questions</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {(data.follow_up_questions || []).map((q) => (
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
            </section>

            <DiscoveryRail discovery={data.discovery} onAsk={onAsk} />
          </div>
        )}
      </div>
    </div>
  );
}
