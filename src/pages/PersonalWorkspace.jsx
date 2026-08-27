import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import DiscoveryRail from '@/components/Product/DiscoveryRail';
import {
  getFavouriteCompanies,
  getFavouriteThemes,
  getReadingHistory,
  getRecentSearches,
  getSavedAnswers,
  getSavedSearches,
  getWatchlist,
} from '@/lib/searchHistory';
import { getProductAnalytics, trackProductEvent } from '@/lib/productAnalytics';
import { useAuth } from '@/contexts/AuthContext';

function Block({ title, children, action }) {
  return (
    <section className="border border-[#dddddd] p-5 bg-white">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">{title}</h2>
        {action}
      </div>
      <div className="mt-3 text-sm text-[#333]">{children}</div>
    </section>
  );
}

export default function PersonalWorkspace() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [tick, setTick] = useState(0);

  useEffect(() => {
    trackProductEvent('session_start', { surface: 'workspace' });
  }, []);

  const data = useMemo(() => {
    void tick;
    return {
      companies: getFavouriteCompanies(),
      themes: getFavouriteThemes(),
      recent: getRecentSearches(12),
      savedSearches: getSavedSearches(),
      savedAnswers: getSavedAnswers(12),
      reading: getReadingHistory(12),
      watchlist: getWatchlist(),
      analytics: getProductAnalytics(),
    };
  }, [tick]);

  const onAsk = (q) => navigate(`/ask?q=${encodeURIComponent(q)}`);
  const refresh = () => setTick((n) => n + 1);

  const recommended = [
    ...data.companies.slice(0, 3).map((t) => `What changed in AGI's view on ${t}?`),
    ...data.themes.slice(0, 2).map((t) => `What is AGI's current thesis on ${t}?`),
    'What is AGI’s current market view?',
  ].slice(0, 6);

  return (
    <div className="bg-white min-h-screen">
      <Helmet>
        <title>Personal Workspace | Agarwal Global Investments</title>
        <meta
          name="description"
          content="Your AGI research workspace — saved companies, themes, questions, reading history and watchlists."
        />
        <link rel="canonical" href="https://agarwalglobalinvestments.com/workspace" />
      </Helmet>

      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-8">
        <Link to="/" className="text-xs font-bold text-[#111] hover:text-[#ff6600]">← Home</Link>
        <p className="mt-4 text-[11px] font-bold uppercase tracking-wider text-[#ff6600]">Personal Workspace</p>
        <h1 className="mt-2 text-3xl font-bold text-[#111]">
          {user ? `Welcome back` : 'Your research desk'}
        </h1>
        <p className="mt-2 text-sm text-[#767676] max-w-2xl">
          Saved companies, themes, questions and reading history — personalised on this device.
          {user ? ' Signed-in preferences sync locally with your session.' : ' Sign in to keep your desk across sessions.'}
        </p>

        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
          <Block
            title="Saved companies"
            action={<button type="button" onClick={refresh} className="text-[10px] font-bold text-[#767676]">Refresh</button>}
          >
            <div className="flex flex-wrap gap-2">
              {data.companies.map((t) => (
                <Link key={t} to={`/research/stocks/${encodeURIComponent(t)}`} className="text-xs font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]">
                  {t}
                </Link>
              ))}
              {!data.companies.length && <p className="text-xs text-[#929292]">Bookmark companies from Ask AGI or company pages.</p>}
            </div>
          </Block>

          <Block title="Saved themes">
            <div className="flex flex-wrap gap-2">
              {data.themes.map((t) => (
                <Link key={t} to={`/themes/${encodeURIComponent(t)}`} className="text-xs font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]">
                  {t}
                </Link>
              ))}
              {!data.themes.length && <p className="text-xs text-[#929292]">Save themes from theme intelligence hubs.</p>}
            </div>
          </Block>

          <Block title="Recent searches">
            <ul className="space-y-2">
              {data.recent.map((q) => (
                <li key={q}>
                  <button type="button" onClick={() => onAsk(q)} className="text-left hover:text-[#ff6600]">
                    {q}
                  </button>
                </li>
              ))}
              {!data.recent.length && <li className="text-xs text-[#929292]">Ask AGI to start your history.</li>}
            </ul>
          </Block>

          <Block title="Saved questions & answers">
            <ul className="space-y-2">
              {data.savedAnswers.map((item) => (
                <li key={item.id} className="border-b border-[#eee] pb-2">
                  <button type="button" onClick={() => onAsk(item.question)} className="text-left font-bold hover:text-[#ff6600]">
                    {item.question}
                  </button>
                  {item.stance && <p className="text-[11px] text-[#767676] mt-1">{item.stance}</p>}
                </li>
              ))}
              {data.savedSearches.slice(0, 5).map((q) => (
                <li key={`s-${q}`}>
                  <button type="button" onClick={() => onAsk(q)} className="text-left hover:text-[#ff6600]">{q}</button>
                </li>
              ))}
              {!data.savedAnswers.length && !data.savedSearches.length && (
                <li className="text-xs text-[#929292]">Save answers from the Ask AGI workspace.</li>
              )}
            </ul>
          </Block>

          <Block title="Watchlist">
            <div className="flex flex-wrap gap-2">
              {data.watchlist.map((t) => (
                <Link key={t} to={`/research/stocks/${encodeURIComponent(t)}`} className="text-xs font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]">
                  {t}
                </Link>
              ))}
              {!data.watchlist.length && (
                <p className="text-xs text-[#929292]">
                  Watchlist mirrors saved companies for now.{' '}
                  <Link to="/ask" className="font-bold hover:text-[#ff6600]">Ask AGI</Link>
                </p>
              )}
            </div>
          </Block>

          <Block title="Reading history">
            <ul className="space-y-2">
              {data.reading.map((item) => (
                <li key={item.id || item.href}>
                  <Link to={item.href || '/research'} className="font-bold hover:text-[#ff6600]">
                    {item.title || item.id}
                  </Link>
                </li>
              ))}
              {!data.reading.length && <li className="text-xs text-[#929292]">Open research articles to build history.</li>}
            </ul>
          </Block>
        </div>

        <div className="mt-4 border border-[#dddddd] p-5">
          <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">Research alerts · recently updated</h2>
          <p className="mt-2 text-xs text-[#767676]">
            Alerts surface when saved companies or themes receive new institutional updates.
            Use Prediction Centre and company pages for the latest changes.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link to="/predictions" className="text-[11px] font-bold border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">
              Prediction Centre
            </Link>
            <Link to="/macro-intelligence" className="text-[11px] font-bold border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">
              Macro Intelligence
            </Link>
          </div>
        </div>

        <div className="mt-4 border border-[#dddddd] p-5">
          <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">Recommended questions</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {recommended.map((q) => (
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
        </div>

        <div className="mt-4">
          <DiscoveryRail
            discovery={{
              related_companies: data.companies,
              related_themes: data.themes,
              related_questions: recommended,
              popular_questions: data.recent.slice(0, 4),
            }}
            onAsk={onAsk}
            title="Continue exploring"
          />
        </div>

        {!user && (
          <p className="mt-6 text-xs text-[#767676]">
            <Link to="/login" className="font-bold hover:text-[#ff6600]">Sign in</Link> to keep this workspace tied to your account profile.
          </p>
        )}
      </div>
    </div>
  );
}
