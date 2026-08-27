import { useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import {
  Activity,
  BookOpen,
  BrainCircuit,
  CalendarDays,
  ChevronRight,
  FileText,
  GraduationCap,
  Layers3,
  MessageSquare,
  Network,
  Search,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import useIpoPlatform from '@/hooks/useIpoPlatform';
import {
  ARTICLE_TAGS,
  LEARNING_MODULES,
  LIBRARY_DOC_TYPES,
  SOURCE_CREDIBILITY,
  answerIpoQuestion,
  classifyLibraryDocs,
} from '@/lib/ipoIntelligence';

const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: Activity },
  { id: 'current', label: 'Current IPOs', icon: Layers3 },
  { id: 'upcoming', label: 'Upcoming IPOs', icon: CalendarDays },
  { id: 'listed', label: 'Listed IPOs', icon: FileText },
  { id: 'calendar', label: 'IPO Calendar', icon: CalendarDays },
  { id: 'research', label: 'Research Hub', icon: BookOpen },
  { id: 'learning', label: 'Learning Centre', icon: GraduationCap },
  { id: 'copilot', label: 'AI Copilot', icon: BrainCircuit },
];

function formatDate(value) {
  if (!value) return 'TBA';
  const date = String(value).length > 10 ? new Date(value) : new Date(`${value}T00:00:00`);
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function priceBand(ipo) {
  if (ipo?.minPrice == null && ipo?.maxPrice == null) return 'Price band pending';
  if (ipo.minPrice === ipo.maxPrice) return `₹${ipo.minPrice}`;
  return `₹${ipo.minPrice}–${ipo.maxPrice}`;
}

function toneClass(value = '') {
  const text = String(value).toLowerCase();
  if (text.includes('bear') || text.includes('negative')) return 'bg-[#fff1f0] text-[#b42318] border-[#f7c5c0]';
  if (text.includes('bull') || text.includes('positive')) return 'bg-[#ecfdf3] text-[#087443] border-[#b7ebcc]';
  return 'bg-[#fff8e8] text-[#966a00] border-[#f4d99d]';
}

function MetricCard({ label, value, detail }) {
  return (
    <div className="border border-[#dde1e6] bg-white p-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#737982]">{label}</p>
      <p className="mt-2 text-xl font-bold text-[#18202b]">{value ?? '—'}</p>
      {detail && <p className="mt-1 text-[11px] text-[#737982]">{detail}</p>}
    </div>
  );
}

function IpoCard({ ipo }) {
  return (
    <Link
      to={`/ipos/${encodeURIComponent(ipo.symbol)}`}
      className="group border border-[#dde1e6] bg-white p-4 transition-colors hover:border-[#274c77]"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-bold text-[#18202b] group-hover:underline">{ipo.name}</p>
          <p className="mt-1 text-[11px] text-[#737982]">
            {ipo.isSme ? 'SME' : 'Mainboard'} · {ipo.symbol}
          </p>
        </div>
        <ChevronRight className="h-4 w-4 text-[#737982] group-hover:text-[#274c77]" />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 border-y border-[#edf0f2] py-3 text-xs">
        <div>
          <p className="text-[#737982]">Opens</p>
          <p className="mt-1 font-bold text-[#18202b]">{formatDate(ipo.biddingStartDate)}</p>
        </div>
        <div>
          <p className="text-[#737982]">Price band</p>
          <p className="mt-1 font-bold text-[#18202b]">{priceBand(ipo)}</p>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        <span className="text-[10px] font-bold uppercase tracking-wide text-[#59616d]">{ipo.status || 'IPO'}</span>
        {ipo.subscriptionRate != null && (
          <span className="text-[11px] font-bold text-[#274c77]">{ipo.subscriptionRate}× subscribed</span>
        )}
      </div>
    </Link>
  );
}

function ArticleRow({ article, selectedTopic, onTopic }) {
  if (selectedTopic && !(article.topics || []).includes(selectedTopic)) return null;
  return (
    <article className="border border-[#dde1e6] bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wide text-[#274c77]">{article.publisher}</p>
          <Link to={`/article/${article.slug}`} className="mt-1 block text-base font-bold text-[#18202b] hover:underline">
            {article.title}
          </Link>
          <p className="mt-1 text-xs text-[#737982]">
            {article.author} · {formatDate(article.publishedAt)} · {article.readingTime} min read
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className={`border px-2 py-1 text-[10px] font-bold uppercase ${toneClass(article.sentiment)}`}>
            {article.sentiment}
          </span>
          <span className="text-[11px] font-bold text-[#18202b]">Credibility {article.credibility}</span>
        </div>
      </div>
      {article.excerpt && <p className="mt-3 line-clamp-2 text-sm text-[#4b5563]">{article.excerpt}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        {(article.topics || []).map((topic) => (
          <button
            key={topic}
            type="button"
            onClick={() => onTopic?.(topic)}
            className="border border-[#edf0f2] bg-[#f8fafb] px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-[#59616d] hover:border-[#274c77]"
          >
            {topic}
          </button>
        ))}
      </div>
      {article.ai?.executiveSummary?.length > 0 && (
        <div className="mt-4 border-l-4 border-[#274c77] bg-[#f8fafb] p-3">
          <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">AI Summary</p>
          <ul className="mt-2 space-y-1 text-sm text-[#374151]">
            {article.ai.executiveSummary.slice(0, 3).map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] text-[#737982]">
            Impact {article.ai.impact} · Confidence {article.ai.confidence}%
          </p>
        </div>
      )}
    </article>
  );
}

export default function IpoIntelligencePage() {
  const { loading, platform, error, research } = useIpoPlatform();
  const [tab, setTab] = useState('dashboard');
  const [topicFilter, setTopicFilter] = useState('');
  const [publisherFilter, setPublisherFilter] = useState('');
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState(null);
  const [libraryQuery, setLibraryQuery] = useState('');

  const active = platform?.active || [];
  const upcoming = platform?.upcoming || [];
  const listed = platform?.listed || [];
  const closed = platform?.closed || [];
  const calendar = platform?.calendar || [];
  const panel = research.panel;

  const filteredArticles = useMemo(() => {
    return research.articles.filter((article) => {
      if (topicFilter && !(article.topics || []).includes(topicFilter)) return false;
      if (publisherFilter && article.publisher !== publisherFilter) return false;
      if (libraryQuery) {
        const hay = `${article.title} ${article.excerpt} ${article.publisher}`.toLowerCase();
        if (!hay.includes(libraryQuery.toLowerCase())) return false;
      }
      return true;
    });
  }, [research.articles, topicFilter, publisherFilter, libraryQuery]);

  const library = useMemo(
    () => classifyLibraryDocs(filteredArticles),
    [filteredArticles]
  );

  const handleAsk = (event) => {
    event?.preventDefault?.();
    setAnswer(answerIpoQuestion(query, research.articles));
  };

  return (
    <div className="min-h-screen bg-[#f8fafb]">
      <Helmet>
        <title>IPO Intelligence | Agarwal Global Investments</title>
        <meta
          name="description"
          content="AGIB IPO Intelligence Platform — current and upcoming issues, research hub, source credibility, and evidence-backed IPO analysis."
        />
      </Helmet>

      <section className="border-b border-[#dde1e6] bg-[#0d1d33] text-white">
        <div className="mx-auto max-w-[1800px] px-4 py-8 sm:px-6 sm:py-10 lg:py-14">
          <div className="flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase tracking-[0.12em] text-[#a7c5ec]">
            <Sparkles className="h-4 w-4" /> AGIB IPO Intelligence Platform
          </div>
          <div className="mt-4 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight md:text-5xl">IPO Intelligence</h1>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#d2dceb] md:text-base">
                Institutional research hub for public issues — live pipeline, classified coverage, credibility-weighted evidence, and AI-assisted reasoning.
              </p>
            </div>
            <div className="text-xs leading-relaxed text-[#c6d4e7]">
              {platform?.updatedAt
                ? `Pipeline updated ${new Date(platform.updatedAt).toLocaleString('en-IN')}`
                : 'Awaiting IPO pipeline refresh'}
              <div className="mt-1 opacity-80">Next refresh {platform?.nextRefreshAt ? formatDate(platform.nextRefreshAt) : '12:00 PM IST'}</div>
            </div>
          </div>
        </div>
      </section>

      <div className="sticky top-[58px] z-30 border-b border-[#dde1e6] bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1800px] gap-1 overflow-x-auto px-4 py-2 sm:px-6">
          {TABS.map((item) => {
            const Icon = item.icon;
            const activeTab = tab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setTab(item.id)}
                className={`inline-flex shrink-0 items-center gap-2 border px-3 py-2 text-xs font-bold transition-colors ${
                  activeTab
                    ? 'border-[#274c77] bg-[#274c77] text-white'
                    : 'border-transparent text-[#59616d] hover:border-[#dde1e6] hover:bg-[#f8fafb]'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
              </button>
            );
          })}
        </div>
      </div>

      <main className="mx-auto max-w-[1800px] px-4 py-6 sm:px-6 sm:py-8">
        {loading ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-24 animate-pulse border border-[#dde1e6] bg-white" />
            ))}
          </div>
        ) : error && !platform ? (
          <section className="border border-dashed border-[#cbd2da] bg-white p-8 text-center">
            <h2 className="text-lg font-bold text-[#18202b]">IPO pipeline temporarily unavailable</h2>
            <p className="mx-auto mt-2 max-w-lg text-sm text-[#667085]">
              The Research Hub still loads CMS IPO articles when the live IndianAPI feed is down.
            </p>
          </section>
        ) : null}

        {!loading && tab === 'dashboard' && (
          <div className="space-y-6">
            <section className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
              <MetricCard label="Articles analysed" value={panel.articlesAnalysed} />
              <MetricCard label="Current IPOs" value={platform?.counts?.active ?? active.length} />
              <MetricCard label="Upcoming" value={platform?.counts?.upcoming ?? upcoming.length} />
              <MetricCard label="Consensus" value={panel.consensus} />
              <MetricCard label="Sentiment" value={`${panel.sentiment}%`} />
              <MetricCard label="Risk score" value={panel.riskScore} />
              <MetricCard label="Confidence" value={`${panel.confidence}%`} detail={`${panel.contradictions} contradictions`} />
            </section>

            <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
              <div className="border border-[#dde1e6] bg-white p-5">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-sm font-bold text-[#18202b]">Current & upcoming pipeline</h2>
                  <button type="button" onClick={() => setTab('current')} className="text-xs font-bold text-[#274c77] hover:underline">
                    View all
                  </button>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {[...active, ...upcoming].slice(0, 4).map((ipo) => (
                    <IpoCard key={ipo.symbol} ipo={ipo} />
                  ))}
                  {!active.length && !upcoming.length && (
                    <p className="text-sm text-[#667085] sm:col-span-2">No active or upcoming issues in the latest snapshot.</p>
                  )}
                </div>
              </div>

              <div className="border border-[#dde1e6] bg-white p-5">
                <h2 className="text-sm font-bold text-[#18202b]">AGIB Intelligence Panel</h2>
                <p className="mt-1 text-xs text-[#737982]">Live enrichment from classified IPO research assets.</p>
                <div className="mt-4 space-y-3">
                  <div className="border border-[#edf0f2] bg-[#f8fafb] p-3">
                    <p className="text-[10px] font-bold uppercase text-[#737982]">Top opportunities</p>
                    <ul className="mt-2 space-y-1 text-sm text-[#374151]">
                      {research.insights.topOpportunities.slice(0, 3).map((item) => (
                        <li key={item}>• {item}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="border border-[#edf0f2] bg-[#f8fafb] p-3">
                    <p className="text-[10px] font-bold uppercase text-[#737982]">Top risks</p>
                    <ul className="mt-2 space-y-1 text-sm text-[#374151]">
                      {research.insights.topRisks.slice(0, 3).map((item) => (
                        <li key={item}>• {item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </section>

            <section className="border border-[#dde1e6] bg-white p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-bold text-[#18202b]">Latest research coverage</h2>
                <button type="button" onClick={() => setTab('research')} className="text-xs font-bold text-[#274c77] hover:underline">
                  Open Research Hub
                </button>
              </div>
              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                {research.articles.slice(0, 4).map((article) => (
                  <ArticleRow key={article.id} article={article} />
                ))}
                {!research.articles.length && (
                  <p className="text-sm text-[#667085] lg:col-span-2">
                    Publish CMS articles with section <strong>IPOs</strong> to populate the Research Hub.
                  </p>
                )}
              </div>
            </section>
          </div>
        )}

        {!loading && tab === 'current' && (
          <section>
            <h2 className="text-lg font-bold text-[#18202b]">Current IPOs</h2>
            <p className="mt-1 text-sm text-[#667085]">Issues currently open for bidding.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {active.map((ipo) => (
                <IpoCard key={ipo.symbol} ipo={ipo} />
              ))}
              {!active.length && <p className="text-sm text-[#667085]">No current IPOs in the latest feed.</p>}
            </div>
          </section>
        )}

        {!loading && tab === 'upcoming' && (
          <section>
            <h2 className="text-lg font-bold text-[#18202b]">Upcoming IPOs</h2>
            <p className="mt-1 text-sm text-[#667085]">Issues expected to open, with price band and calendar fields when available.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {upcoming.map((ipo) => (
                <IpoCard key={ipo.symbol} ipo={ipo} />
              ))}
              {!upcoming.length && <p className="text-sm text-[#667085]">No upcoming IPOs in the latest feed.</p>}
            </div>
          </section>
        )}

        {!loading && tab === 'listed' && (
          <section className="space-y-8">
            <div>
              <h2 className="text-lg font-bold text-[#18202b]">Listed IPOs</h2>
              <p className="mt-1 text-sm text-[#667085]">Recently listed issues from the provider snapshot.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {listed.map((ipo) => (
                  <IpoCard key={ipo.symbol} ipo={ipo} />
                ))}
                {!listed.length && <p className="text-sm text-[#667085]">No listed IPOs in the latest feed.</p>}
              </div>
            </div>
            {closed.length > 0 && (
              <div>
                <h3 className="text-sm font-bold text-[#18202b]">Closed / allotment window</h3>
                <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {closed.slice(0, 12).map((ipo) => (
                    <IpoCard key={ipo.symbol} ipo={ipo} />
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {!loading && tab === 'calendar' && (
          <section>
            <h2 className="text-lg font-bold text-[#18202b]">IPO Calendar</h2>
            <p className="mt-1 text-sm text-[#667085]">Chronological open, close, allotment, and listing events.</p>
            <div className="mt-4 border border-[#dde1e6] bg-white">
              {calendar.length ? (
                <ul className="divide-y divide-[#edf0f2]">
                  {calendar.slice(0, 60).map((event, index) => (
                    <li key={`${event.symbol}-${event.date}-${event.label}-${index}`} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex items-start gap-4">
                        <div className="w-28 shrink-0 text-xs font-bold text-[#274c77]">{formatDate(event.date)}</div>
                        <div>
                          <p className="text-sm font-bold text-[#18202b]">{event.label}</p>
                          <p className="text-xs text-[#737982]">{event.name}</p>
                        </div>
                      </div>
                      <Link to={`/ipos/${encodeURIComponent(event.symbol)}`} className="text-xs font-bold text-[#274c77] hover:underline">
                        Open dossier →
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="p-6 text-sm text-[#667085]">Calendar events will appear when IPO dates are present in the feed.</p>
              )}
            </div>
          </section>
        )}

        {!loading && tab === 'research' && (
          <div className="space-y-6">
            <section className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
              <MetricCard label="Articles" value={panel.articlesAnalysed} />
              <MetricCard label="Publishers" value={research.publishers.length} />
              <MetricCard label="Consensus" value={panel.consensus} />
              <MetricCard label="Sentiment" value={`${panel.sentiment}%`} />
              <MetricCard label="Contradictions" value={panel.contradictions} />
              <MetricCard label="Confidence" value={`${panel.confidence}%`} />
            </section>

            <section className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h2 className="text-lg font-bold text-[#18202b]">Research Hub</h2>
                <p className="mt-1 text-sm text-[#667085]">
                  Every IPO article is classified into a searchable research database with publisher, sentiment, topics, and credibility.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <select
                  value={publisherFilter}
                  onChange={(e) => setPublisherFilter(e.target.value)}
                  className="border border-[#dde1e6] bg-white px-3 py-2 text-xs font-bold text-[#18202b]"
                >
                  <option value="">All publishers</option>
                  {research.publishers.map((publisher) => (
                    <option key={publisher} value={publisher}>
                      {publisher}
                    </option>
                  ))}
                </select>
                <select
                  value={topicFilter}
                  onChange={(e) => setTopicFilter(e.target.value)}
                  className="border border-[#dde1e6] bg-white px-3 py-2 text-xs font-bold text-[#18202b]"
                >
                  <option value="">All topics</option>
                  {ARTICLE_TAGS.map((tag) => (
                    <option key={tag} value={tag}>
                      {tag}
                    </option>
                  ))}
                </select>
                <label className="relative">
                  <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[#737982]" />
                  <input
                    value={libraryQuery}
                    onChange={(e) => setLibraryQuery(e.target.value)}
                    placeholder="Search research…"
                    className="border border-[#dde1e6] bg-white py-2 pl-8 pr-3 text-xs text-[#18202b] outline-none focus:border-[#274c77]"
                  />
                </label>
              </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
              <div className="space-y-3">
                {filteredArticles.map((article) => (
                  <ArticleRow
                    key={article.id}
                    article={article}
                    selectedTopic={topicFilter}
                    onTopic={setTopicFilter}
                  />
                ))}
                {!filteredArticles.length && (
                  <div className="border border-dashed border-[#cbd2da] bg-white p-8 text-center text-sm text-[#667085]">
                    No classified IPO articles match these filters. Publish CMS content with section IPOs to seed the hub.
                  </div>
                )}
              </div>

              <aside className="space-y-4">
                <div className="border border-[#dde1e6] bg-white p-4">
                  <div className="flex items-center gap-2 text-[#274c77]">
                    <Network className="h-4 w-4" />
                    <h3 className="text-sm font-bold text-[#18202b]">Source credibility</h3>
                  </div>
                  <ul className="mt-3 space-y-2">
                    {Object.entries(SOURCE_CREDIBILITY)
                      .slice(0, 8)
                      .map(([name, score]) => (
                        <li key={name} className="flex items-center justify-between text-xs">
                          <span className="text-[#4b5563]">{name}</span>
                          <span className="font-bold text-[#18202b]">{score}</span>
                        </li>
                      ))}
                  </ul>
                </div>

                <div className="border border-[#dde1e6] bg-white p-4">
                  <h3 className="text-sm font-bold text-[#18202b]">Article comparison</h3>
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-[#edf0f2] text-[#737982]">
                          <th className="py-2 font-bold">Source</th>
                          <th className="py-2 font-bold">Bullish</th>
                          <th className="py-2 font-bold">Neutral</th>
                          <th className="py-2 font-bold">Bearish</th>
                        </tr>
                      </thead>
                      <tbody>
                        {research.comparison.map((row) => (
                          <tr key={row.source} className="border-b border-[#f3f5f7]">
                            <td className="py-2 font-bold text-[#18202b]">{row.source}</td>
                            <td className="py-2">{row.Bullish ? '✓' : ''}</td>
                            <td className="py-2">{row.Neutral ? '✓' : ''}</td>
                            <td className="py-2">{row.Bearish ? '✓' : ''}</td>
                          </tr>
                        ))}
                        {!research.comparison.length && (
                          <tr>
                            <td colSpan={4} className="py-3 text-[#667085]">
                              Comparison appears once multiple publishers are classified.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {research.contradictions[0] && (
                  <div className="border border-[#f2d7a0] bg-[#fffaf0] p-4">
                    <div className="flex items-center gap-2 text-[#966a00]">
                      <ShieldAlert className="h-4 w-4" />
                      <h3 className="text-sm font-bold">Contradiction detected</h3>
                    </div>
                    <p className="mt-3 text-xs text-[#6f5a2e]">
                      <strong>{research.contradictions[0].left.source}</strong> — {research.contradictions[0].left.claim}
                    </p>
                    <p className="mt-2 text-xs text-[#6f5a2e]">
                      <strong>{research.contradictions[0].right.source}</strong> — {research.contradictions[0].right.claim}
                    </p>
                    <p className="mt-3 text-[11px] text-[#6f5a2e]">
                      Confidence {research.contradictions[0].confidence}% · {research.contradictions[0].reason}
                    </p>
                  </div>
                )}

                <div className="border border-[#dde1e6] bg-white p-4">
                  <h3 className="text-sm font-bold text-[#18202b]">Research library</h3>
                  <p className="mt-1 text-xs text-[#737982]">Document classes for full-text and semantic search.</p>
                  <ul className="mt-3 space-y-2">
                    {LIBRARY_DOC_TYPES.map((type) => (
                      <li key={type} className="flex items-center justify-between text-xs">
                        <span className="text-[#4b5563]">{type}</span>
                        <span className="font-bold text-[#18202b]">{(library[type] || []).length}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </aside>
            </section>
          </div>
        )}

        {!loading && tab === 'learning' && (
          <section>
            <h2 className="text-lg font-bold text-[#18202b]">Learning Centre</h2>
            <p className="mt-1 max-w-2xl text-sm text-[#667085]">
              Core IPO literacy modules for analysts — how to read offer documents, interpret demand, and weight sources.
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {LEARNING_MODULES.map((module) => (
                <article key={module.id} className="border border-[#dde1e6] bg-white p-5">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-[#274c77]">Module</p>
                  <h3 className="mt-2 text-base font-bold text-[#18202b]">{module.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-[#4b5563]">{module.summary}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {module.topics.map((topic) => (
                      <button
                        key={topic}
                        type="button"
                        onClick={() => {
                          setTopicFilter(topic);
                          setTab('research');
                        }}
                        className="border border-[#edf0f2] bg-[#f8fafb] px-2 py-1 text-[10px] font-bold uppercase text-[#59616d]"
                      >
                        {topic}
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </div>
            <div className="mt-6 border border-[#dde1e6] bg-white p-5">
              <h3 className="text-sm font-bold text-[#18202b]">Recommended research workflow</h3>
              <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-[#4b5563]">
                <li>Start with primary documents (DRHP / RHP / SEBI).</li>
                <li>Classify secondary coverage by publisher credibility.</li>
                <li>Track narrative changes on the coverage timeline.</li>
                <li>Surface contradictions before forming a house view.</li>
                <li>Ask the AI Copilot with evidence constraints — never from headlines alone.</li>
              </ol>
            </div>
          </section>
        )}

        {!loading && tab === 'copilot' && (
          <section className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
            <div className="border border-[#dde1e6] bg-white p-5">
              <div className="flex items-center gap-2 text-[#274c77]">
                <MessageSquare className="h-4 w-4" />
                <h2 className="text-lg font-bold text-[#18202b]">AI Question Answering</h2>
              </div>
              <p className="mt-1 text-sm text-[#667085]">
                Ask across classified IPO research instead of scanning articles one by one.
              </p>
              <form onSubmit={handleAsk} className="mt-4 flex flex-col gap-3 sm:flex-row">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Why are institutions bullish?"
                  className="flex-1 border border-[#dde1e6] px-3 py-3 text-sm text-[#18202b] outline-none focus:border-[#274c77]"
                />
                <button type="submit" className="bg-[#274c77] px-4 py-3 text-xs font-bold uppercase tracking-wide text-white hover:bg-[#1f3d61]">
                  Ask
                </button>
              </form>
              <div className="mt-3 flex flex-wrap gap-2">
                {['Why are institutions bullish?', 'What are the key risks?', 'How is subscription trending?'].map((sample) => (
                  <button
                    key={sample}
                    type="button"
                    onClick={() => {
                      setQuery(sample);
                      setAnswer(answerIpoQuestion(sample, research.articles));
                    }}
                    className="border border-[#edf0f2] bg-[#f8fafb] px-3 py-1.5 text-[11px] font-bold text-[#59616d] hover:border-[#274c77]"
                  >
                    {sample}
                  </button>
                ))}
              </div>

              {answer && (
                <div className="mt-5 border border-[#edf0f2] bg-[#f8fafb] p-4">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">
                    Based on {answer.basedOn} research articles · Confidence {answer.confidence}%
                  </p>
                  <p className="mt-3 text-sm font-bold text-[#18202b]">Primary reasons</p>
                  <ul className="mt-2 space-y-1 text-sm text-[#374151]">
                    {answer.primaryReasons.map((item) => (
                      <li key={item}>• {item}</li>
                    ))}
                  </ul>
                  {answer.evidence?.length > 0 && (
                    <>
                      <p className="mt-4 text-sm font-bold text-[#18202b]">Evidence</p>
                      <p className="mt-1 text-xs text-[#667085]">{[...new Set(answer.evidence)].join(' · ')}</p>
                    </>
                  )}
                  <Link to={answer.askAgiHref} className="mt-4 inline-flex text-xs font-bold text-[#274c77] hover:underline">
                    Continue in Ask AGI →
                  </Link>
                </div>
              )}
            </div>

            <aside className="space-y-4">
              <div className="border border-[#dde1e6] bg-white p-4">
                <h3 className="text-sm font-bold text-[#18202b]">Enrichment pipeline</h3>
                <ol className="mt-3 space-y-2 text-xs text-[#4b5563]">
                  {[
                    'Upload / publish article',
                    'Text extraction',
                    'Metadata & publisher detection',
                    'Entity & topic recognition',
                    'Sentiment analysis',
                    'Knowledge graph update',
                    'AI summary & risk extraction',
                    'IPO Intelligence dashboard',
                  ].map((step) => (
                    <li key={step} className="border-l-2 border-[#274c77] pl-3">
                      {step}
                    </li>
                  ))}
                </ol>
              </div>
              <div className="border border-[#f2d7a0] bg-[#fffaf0] p-4 text-xs leading-relaxed text-[#6f5a2e]">
                <p className="font-bold uppercase tracking-wide">Disclosure</p>
                <p className="mt-2">
                  IPO Intelligence is informational only and not investment advice. Verify offer documents with the issuer, NSE, BSE, or SEBI before acting.
                </p>
              </div>
            </aside>
          </section>
        )}
      </main>
    </div>
  );
}
