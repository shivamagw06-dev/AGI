import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import {
  ArrowLeft,
  CalendarDays,
  ExternalLink,
  FileText,
  Network,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { getIpoDetail } from '@/lib/ipoApi';
import { supabase } from '@/lib/supabaseClient';
import {
  answerIpoQuestion,
  buildKnowledgeGraph,
  buildTimeline,
  classifyLibraryDocs,
  compareSources,
  detectContradictions,
  enrichArticle,
  intelligencePanel,
  aggregateInsights,
  matchArticlesToIpo,
} from '@/lib/ipoIntelligence';

function formatDate(value) {
  if (!value) return 'To be announced';
  const date = String(value).length > 10 ? new Date(value) : new Date(`${value}T00:00:00`);
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
}

function shortDate(value) {
  if (!value) return '—';
  const date = String(value).length > 10 ? new Date(value) : new Date(`${value}T00:00:00`);
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function valueOrPending(value, formatter = (item) => item) {
  return value == null || value === '' ? 'Pending / not provided' : formatter(value);
}

function DetailRow({ label, value }) {
  return (
    <div className="border border-[#edf0f2] p-4">
      <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">{label}</p>
      <p className="mt-1 text-sm font-bold text-[#18202b]">{value}</p>
    </div>
  );
}

function toneClass(value = '') {
  const text = String(value).toLowerCase();
  if (text.includes('bear') || text.includes('negative')) return 'bg-[#fff1f0] text-[#b42318] border-[#f7c5c0]';
  if (text.includes('bull') || text.includes('positive')) return 'bg-[#ecfdf3] text-[#087443] border-[#b7ebcc]';
  return 'bg-[#fff8e8] text-[#966a00] border-[#f4d99d]';
}

export default function IpoDetailPage() {
  const { symbol } = useParams();
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [articles, setArticles] = useState([]);
  const [graphFilter, setGraphFilter] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);

  useEffect(() => {
    let active = true;
    getIpoDetail(symbol)
      .then((data) => active && setState({ loading: false, data, error: null }))
      .catch((error) => active && setState({ loading: false, data: null, error }));
    return () => {
      active = false;
    };
  }, [symbol]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const select = 'id, title, slug, excerpt, cover_url, tags, published_at, section, status';
      let { data } = await supabase
        .from('articles')
        .select(select)
        .eq('status', 'published')
        .eq('section', 'IPOs')
        .order('published_at', { ascending: false })
        .limit(80);

      if (!data?.length) {
        const fallback = await supabase
          .from('articles')
          .select(select)
          .eq('status', 'published')
          .or('section.ilike.%IPO%,title.ilike.%IPO%')
          .order('published_at', { ascending: false })
          .limit(80);
        data = fallback.data || [];
      }

      if (cancelled) return;
      const chronological = [...(data || [])].sort((a, b) =>
        String(a.published_at || '').localeCompare(String(b.published_at || ''))
      );
      const enriched = [];
      for (const row of chronological) {
        enriched.push(enrichArticle(row, enriched.slice(-3)));
      }
      setArticles(enriched.reverse());
    })();
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  const ipo = state.data?.ipo;
  const matched = useMemo(() => (ipo ? matchArticlesToIpo(articles, ipo) : []), [articles, ipo]);
  const researchArticles = matched.length ? matched : articles.slice(0, 8);
  const filteredResearch = useMemo(() => {
    if (!graphFilter) return researchArticles;
    const needle = graphFilter.toLowerCase();
    return researchArticles.filter((article) => {
      const hay = `${article.title} ${article.excerpt} ${(article.topics || []).join(' ')} ${article.publisher}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [researchArticles, graphFilter]);

  const timeline = useMemo(() => (ipo ? buildTimeline(ipo, researchArticles) : []), [ipo, researchArticles]);
  const graph = useMemo(() => (ipo ? buildKnowledgeGraph(ipo, researchArticles) : { root: 'IPO', nodes: [] }), [ipo, researchArticles]);
  const panel = useMemo(() => intelligencePanel(researchArticles, ipo?.documentUrl ? [ipo.documentUrl] : []), [researchArticles, ipo]);
  const insights = useMemo(() => aggregateInsights(researchArticles), [researchArticles]);
  const comparison = useMemo(() => compareSources(researchArticles), [researchArticles]);
  const contradictions = useMemo(() => detectContradictions(researchArticles), [researchArticles]);
  const library = useMemo(() => classifyLibraryDocs(researchArticles, ipo), [researchArticles, ipo]);
  const publishers = useMemo(() => [...new Set(researchArticles.map((a) => a.publisher))], [researchArticles]);

  const priceBand =
    ipo?.minPrice == null && ipo?.maxPrice == null
      ? 'Pending / not provided'
      : ipo?.minPrice === ipo?.maxPrice
        ? `₹${ipo.minPrice}`
        : `₹${ipo?.minPrice}–${ipo?.maxPrice}`;

  const handleAsk = (event) => {
    event?.preventDefault?.();
    setAnswer(answerIpoQuestion(question, researchArticles, ipo));
  };

  return (
    <div className="min-h-screen bg-[#f8fafb]">
      <Helmet>
        <title>{ipo ? `${ipo.name} IPO Research Hub | AGI` : 'IPO Research Hub | AGI'}</title>
        <meta
          name="description"
          content="IPO Research Hub with classified coverage, AI summaries, timeline, knowledge graph, and credibility-weighted evidence."
        />
      </Helmet>

      <main className="mx-auto max-w-[1200px] px-4 py-7 sm:px-6 sm:py-10">
        <Link to="/ipo-intelligence" className="inline-flex items-center gap-2 text-xs font-bold text-[#274c77] hover:underline">
          <ArrowLeft className="h-4 w-4" /> Back to IPO Intelligence
        </Link>

        {state.loading ? (
          <div className="mt-6 h-80 animate-pulse border border-[#dde1e6] bg-white" />
        ) : state.error || !ipo ? (
          <section className="mt-6 border border-dashed border-[#cbd2da] bg-white p-8 text-center">
            <h1 className="text-xl font-bold text-[#18202b]">IPO information unavailable</h1>
            <p className="mx-auto mt-2 max-w-lg text-sm text-[#667085]">
              This issue is not present in the most recently refreshed IPO dataset.
            </p>
          </section>
        ) : (
          <>
            <section className="mt-6 border border-[#dde1e6] bg-white p-5 sm:p-8">
              <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex items-center gap-2 text-[#274c77]">
                    <Sparkles className="h-4 w-4" />
                    <span className="text-[10px] font-bold uppercase tracking-[0.12em]">IPO Research Hub</span>
                  </div>
                  <h1 className="mt-3 text-3xl font-bold tracking-tight text-[#18202b]">{ipo.name}</h1>
                  <p className="mt-2 text-sm text-[#667085]">
                    {ipo.isSme ? 'SME public issue' : 'Mainboard public issue'} · Symbol: {ipo.symbol}
                  </p>
                </div>
                <span className="w-fit border border-[#d9dee5] bg-[#f8fafb] px-3 py-2 text-xs font-bold uppercase tracking-wide text-[#59616d]">
                  {ipo.status}
                </span>
              </div>
              {ipo.detail && (
                <p className="mt-5 border-l-4 border-[#274c77] bg-[#f8fafb] p-4 text-sm leading-relaxed text-[#374151]">{ipo.detail}</p>
              )}
            </section>

            <section className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
              <DetailRow label="Articles analysed" value={panel.articlesAnalysed} />
              <DetailRow label="Consensus" value={panel.consensus} />
              <DetailRow label="Sentiment" value={`${panel.sentiment}%`} />
              <DetailRow label="Risk score" value={panel.riskScore} />
              <DetailRow label="Contradictions" value={panel.contradictions} />
              <DetailRow label="Confidence" value={`${panel.confidence}%`} />
            </section>

            <section className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <DetailRow label="Price band" value={priceBand} />
              <DetailRow label="Opens" value={formatDate(ipo.biddingStartDate)} />
              <DetailRow label="Closes" value={formatDate(ipo.biddingEndDate)} />
              <DetailRow label="Allotment" value={formatDate(ipo.allotmentDate)} />
              <DetailRow label="Listing date" value={formatDate(ipo.listingDate)} />
              <DetailRow label="Lot size" value={valueOrPending(ipo.lotSize)} />
              <DetailRow label="Minimum bid quantity" value={valueOrPending(ipo.minimumBidQuantity)} />
              <DetailRow label="Subscription rate" value={valueOrPending(ipo.subscriptionRate, (value) => `${value}x`)} />
            </section>

            <section className="mt-6 grid gap-6 lg:grid-cols-[1.35fr_1fr]">
              <div className="border border-[#dde1e6] bg-white p-5">
                <h2 className="text-sm font-bold text-[#18202b]">Research</h2>
                <div className="mt-3 flex flex-wrap gap-2">
                  {publishers.length ? (
                    publishers.map((publisher) => (
                      <span key={publisher} className="border border-[#edf0f2] bg-[#f8fafb] px-2 py-1 text-[10px] font-bold uppercase text-[#274c77]">
                        ✓ {publisher}
                      </span>
                    ))
                  ) : (
                    <p className="text-sm text-[#667085]">No classified research assets matched yet. Publish IPO-section articles mentioning this issuer.</p>
                  )}
                </div>

                <div className="mt-5 space-y-3">
                  {filteredResearch.map((article) => (
                    <article key={article.id} className="border border-[#edf0f2] p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-wide text-[#274c77]">{article.publisher}</p>
                          <Link to={`/article/${article.slug}`} className="mt-1 block font-bold text-[#18202b] hover:underline">
                            {article.title}
                          </Link>
                          <p className="mt-1 text-xs text-[#737982]">
                            {article.author} · {formatDate(article.publishedAt)} · {article.readingTime} min · Credibility {article.credibility}
                          </p>
                        </div>
                        <span className={`border px-2 py-1 text-[10px] font-bold uppercase ${toneClass(article.sentiment)}`}>
                          {article.sentiment}
                        </span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {(article.topics || []).map((topic) => (
                          <span key={topic} className="border border-[#edf0f2] bg-[#f8fafb] px-2 py-1 text-[10px] font-bold uppercase text-[#59616d]">
                            {topic}
                          </span>
                        ))}
                      </div>
                      {article.ai?.executiveSummary?.length > 0 && (
                        <div className="mt-3 border-l-4 border-[#274c77] bg-[#f8fafb] p-3">
                          <p className="text-[10px] font-bold uppercase text-[#737982]">Summary</p>
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
                  ))}
                </div>
              </div>

              <aside className="space-y-4">
                <div className="border border-[#dde1e6] bg-white p-4">
                  <div className="flex items-center gap-2">
                    <CalendarDays className="h-4 w-4 text-[#274c77]" />
                    <h2 className="text-sm font-bold text-[#18202b]">Timeline of coverage</h2>
                  </div>
                  <ul className="mt-4 space-y-3">
                    {timeline.map((event, index) => (
                      <li key={`${event.date}-${event.label}-${index}`} className="flex gap-3">
                        <div className="w-16 shrink-0 text-xs font-bold text-[#274c77]">{shortDate(event.date)}</div>
                        <div>
                          <p className="text-sm font-bold text-[#18202b]">{event.label}</p>
                          {event.detail && <p className="text-xs text-[#737982]">{event.detail}</p>}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="border border-[#dde1e6] bg-white p-4">
                  <div className="flex items-center gap-2">
                    <Network className="h-4 w-4 text-[#274c77]" />
                    <h2 className="text-sm font-bold text-[#18202b]">Knowledge graph</h2>
                  </div>
                  <p className="mt-2 text-xs font-bold text-[#18202b]">{graph.root}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {graph.nodes.map((node) => (
                      <button
                        key={node}
                        type="button"
                        onClick={() => setGraphFilter(graphFilter === node ? '' : node)}
                        className={`border px-2 py-1 text-[10px] font-bold uppercase ${
                          graphFilter === node
                            ? 'border-[#274c77] bg-[#274c77] text-white'
                            : 'border-[#edf0f2] bg-[#f8fafb] text-[#59616d]'
                        }`}
                      >
                        {node}
                      </button>
                    ))}
                  </div>
                  <p className="mt-2 text-[11px] text-[#737982]">Click a node to filter related research.</p>
                </div>

                <div className="border border-[#dde1e6] bg-white p-4">
                  <h2 className="text-sm font-bold text-[#18202b]">AI insights</h2>
                  <p className="mt-3 text-[10px] font-bold uppercase text-[#737982]">Top opportunities</p>
                  <ul className="mt-1 space-y-1 text-xs text-[#374151]">
                    {insights.topOpportunities.slice(0, 3).map((item) => (
                      <li key={item}>• {item}</li>
                    ))}
                  </ul>
                  <p className="mt-3 text-[10px] font-bold uppercase text-[#737982]">Top risks</p>
                  <ul className="mt-1 space-y-1 text-xs text-[#374151]">
                    {insights.topRisks.slice(0, 3).map((item) => (
                      <li key={item}>• {item}</li>
                    ))}
                  </ul>
                </div>
              </aside>
            </section>

            <section className="mt-6 grid gap-6 lg:grid-cols-2">
              <div className="border border-[#dde1e6] bg-white p-5">
                <h2 className="text-sm font-bold text-[#18202b]">Article comparison</h2>
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
                      {comparison.map((row) => (
                        <tr key={row.source} className="border-b border-[#f3f5f7]">
                          <td className="py-2 font-bold text-[#18202b]">{row.source}</td>
                          <td className="py-2">{row.Bullish ? '✓' : ''}</td>
                          <td className="py-2">{row.Neutral ? '✓' : ''}</td>
                          <td className="py-2">{row.Bearish ? '✓' : ''}</td>
                        </tr>
                      ))}
                      {!comparison.length && (
                        <tr>
                          <td colSpan={4} className="py-3 text-[#667085]">
                            Needs multiple classified publishers.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="border border-[#dde1e6] bg-white p-5">
                <h2 className="text-sm font-bold text-[#18202b]">AI question answering</h2>
                <form onSubmit={handleAsk} className="mt-3 flex flex-col gap-2 sm:flex-row">
                  <input
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Why are institutions bullish?"
                    className="flex-1 border border-[#dde1e6] px-3 py-2 text-sm outline-none focus:border-[#274c77]"
                  />
                  <button type="submit" className="bg-[#274c77] px-4 py-2 text-xs font-bold uppercase text-white">
                    Ask
                  </button>
                </form>
                {answer && (
                  <div className="mt-4 border border-[#edf0f2] bg-[#f8fafb] p-3">
                    <p className="text-[10px] font-bold uppercase text-[#737982]">
                      Based on {answer.basedOn} research articles · Confidence {answer.confidence}%
                    </p>
                    <ul className="mt-2 space-y-1 text-sm text-[#374151]">
                      {answer.primaryReasons.map((item) => (
                        <li key={item}>• {item}</li>
                      ))}
                    </ul>
                    <p className="mt-2 text-xs text-[#667085]">Evidence: {[...new Set(answer.evidence)].join(' · ') || '—'}</p>
                    <Link to={answer.askAgiHref} className="mt-3 inline-flex text-xs font-bold text-[#274c77] hover:underline">
                      Continue in Ask AGI →
                    </Link>
                  </div>
                )}
              </div>
            </section>

            {contradictions[0] && (
              <section className="mt-6 border border-[#f2d7a0] bg-[#fffaf0] p-5">
                <div className="flex items-center gap-2 text-[#966a00]">
                  <ShieldAlert className="h-4 w-4" />
                  <h2 className="text-sm font-bold">Contradiction detection</h2>
                </div>
                <p className="mt-3 text-sm text-[#6f5a2e]">
                  <strong>{contradictions[0].left.source}</strong> — {contradictions[0].left.claim}
                </p>
                <p className="mt-2 text-sm text-[#6f5a2e]">
                  <strong>{contradictions[0].right.source}</strong> — {contradictions[0].right.claim}
                </p>
                <p className="mt-3 text-xs text-[#6f5a2e]">
                  AGIB · Confidence {contradictions[0].confidence}% · {contradictions[0].reason}
                </p>
              </section>
            )}

            <section className="mt-6 border border-[#dde1e6] bg-white p-5">
              <h2 className="text-sm font-bold text-[#18202b]">Research library</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {Object.entries(library).map(([type, docs]) => (
                  <div key={type} className="border border-[#edf0f2] p-3">
                    <p className="text-[10px] font-bold uppercase text-[#737982]">{type}</p>
                    <p className="mt-1 text-lg font-bold text-[#18202b]">{docs.length}</p>
                    {docs[0] && (
                      docs[0].externalUrl ? (
                        <a href={docs[0].externalUrl} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-[#274c77] hover:underline">
                          <ExternalLink className="h-3.5 w-3.5" /> Open document
                        </a>
                      ) : docs[0].slug ? (
                        <Link to={`/article/${docs[0].slug}`} className="mt-2 inline-block text-xs font-bold text-[#274c77] hover:underline">
                          {docs[0].title}
                        </Link>
                      ) : null
                    )}
                  </div>
                ))}
              </div>
              {ipo.documentUrl && (
                <a
                  href={ipo.documentUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-[#274c77] hover:underline"
                >
                  <ExternalLink className="h-4 w-4" /> Open issuer / exchange / SEBI document
                </a>
              )}
            </section>

            <section className="mt-6 border border-[#f2d7a0] bg-[#fffaf0] p-5 text-xs leading-relaxed text-[#6f5a2e]">
              <p className="flex items-center gap-2 font-bold uppercase tracking-wide">
                <FileText className="h-4 w-4" /> Important disclosure
              </p>
              <p className="mt-2">
                IPO information is provided for informational purposes only and is not an offer, recommendation, or solicitation. Verify offer documents directly with the issuer, NSE, BSE, or SEBI before acting.
              </p>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
