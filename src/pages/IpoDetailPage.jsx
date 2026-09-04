import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  AlertTriangle, ArrowLeft, ArrowRight, BarChart3, BookOpen, Building2,
  CalendarDays, CheckCircle2, Clock3, ExternalLink, FileSearch, FileText,
  Gauge, Info, Landmark, Scale, ShieldAlert, Sparkles, Target, TrendingUp,
} from 'lucide-react';
import { getIpoDetail } from '@/lib/ipoApi';
import useIpoPlatform from '@/hooks/useIpoPlatform';
import {
  aggregateInsights,
  intelligencePanel,
  matchArticlesToIpo,
} from '@/lib/ipoIntelligence';

const TABS = [
  { id: 'overview', label: 'Investment overview' },
  { id: 'scorecard', label: 'AGI scorecard' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'documents', label: 'Evidence room' },
];

function parseDate(value) {
  if (!value) return null;
  const date = String(value).length > 10 ? new Date(value) : new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(value) {
  const date = parseDate(value);
  return date ? date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'To be announced';
}

function number(value, fallback = 'Pending') {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(parsed) : fallback;
}

function priceBand(ipo) {
  if (ipo?.minPrice == null && ipo?.maxPrice == null) return 'Pending';
  return Number(ipo.minPrice) === Number(ipo.maxPrice) ? `₹${number(ipo.maxPrice)}` : `₹${number(ipo.minPrice)} – ₹${number(ipo.maxPrice)}`;
}

function minimumInvestment(ipo) {
  const quantity = Number(ipo?.minimumBidQuantity || ipo?.lotSize);
  const price = Number(ipo?.maxPrice);
  return Number.isFinite(quantity) && Number.isFinite(price) ? quantity * price : null;
}

function demandScore(subscription) {
  const value = Number(subscription);
  if (!Number.isFinite(value)) return null;
  if (value >= 20) return 95;
  if (value >= 10) return 88;
  if (value >= 5) return 78;
  if (value >= 2) return 67;
  if (value >= 1) return 55;
  return 35;
}

function listingReturn(ipo) {
  const listed = Number(ipo?.listingPrice);
  const issue = Number(ipo?.cutOffPrice || ipo?.maxPrice);
  return Number.isFinite(listed) && Number.isFinite(issue) && issue !== 0 ? ((listed - issue) / issue) * 100 : null;
}

function stanceTone(stance = '') {
  const value = String(stance).toLowerCase();
  if (value.includes('bull')) return 'border-[#8fd4ad] bg-[#dff5e8] text-[#176b45]';
  if (value.includes('bear')) return 'border-[#efb8aa] bg-[#fff0eb] text-[#9f351f]';
  return 'border-[#e3c997] bg-[#fff7e7] text-[#8a631b]';
}

function ScoreBar({ score }) {
  return <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#e8ecee]"><div className="h-full rounded-full bg-gradient-to-r from-[#2d667d] to-[#c58a59]" style={{ width: `${score || 0}%` }} /></div>;
}

function Fact({ label, value, note }) {
  return <div className="rounded-2xl border border-[#e1e6e8] bg-white p-4"><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#87939a]">{label}</p><p className="mt-2 text-base font-bold text-[#152f3d]">{value || 'Pending'}</p>{note && <p className="mt-1 text-[11px] text-[#7a878f]">{note}</p>}</div>;
}

function EvidencePending({ children = 'Awaiting verified RHP or AGI research evidence.' }) {
  return <div className="mt-3 flex items-start gap-2 rounded-xl bg-[#f3f5f4] p-3 text-xs leading-5 text-[#718087]"><Clock3 className="mt-0.5 h-3.5 w-3.5 shrink-0" />{children}</div>;
}

function LoadingDossier() {
  return <div className="min-h-screen bg-[#f5f3ee] px-4 py-16"><div className="mx-auto max-w-6xl animate-pulse"><div className="h-5 w-36 rounded bg-[#dde3e3]" /><div className="mt-10 h-14 w-2/3 rounded bg-[#dde3e3]" /><div className="mt-10 grid gap-4 md:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-28 rounded-2xl bg-white" />)}</div></div></div>;
}

export default function IpoDetailPage() {
  const { symbol } = useParams();
  const { research } = useIpoPlatform();
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [tab, setTab] = useState('overview');

  useEffect(() => {
    let active = true;
    setState({ loading: true, data: null, error: null });
    getIpoDetail(symbol)
      .then((data) => active && setState({ loading: false, data, error: null }))
      .catch((error) => active && setState({ loading: false, data: null, error }));
    return () => { active = false; };
  }, [symbol]);

  const ipo = state.data?.ipo;
  const articles = useMemo(() => matchArticlesToIpo(research?.articles || [], ipo || {}), [research?.articles, ipo]);
  const panel = useMemo(() => intelligencePanel(articles), [articles]);
  const insights = useMemo(() => aggregateInsights(articles), [articles]);
  const explicitResearch = articles.find((article) => article.researchMeta?.stance);
  const meta = explicitResearch?.researchMeta || null;
  const stance = meta?.stance || 'Coverage pending';
  const confidence = meta ? panel.confidence : 0;
  const demand = demandScore(ipo?.subscriptionRate);
  const listedReturn = listingReturn(ipo);

  const suppliedScores = meta?.ipo_scores || meta?.scores || {};
  const scorecards = [
    { key: 'business_quality', label: 'Business quality', weight: 25, score: suppliedScores.business_quality, icon: Building2, detail: 'Moat, industry position and customer resilience' },
    { key: 'financial_quality', label: 'Financial quality', weight: 20, score: suppliedScores.financial_quality, icon: BarChart3, detail: 'Growth, margins, returns and cash conversion' },
    { key: 'valuation', label: 'Valuation', weight: 20, score: suppliedScores.valuation, icon: Scale, detail: 'Price-band valuation against relevant peers' },
    { key: 'governance', label: 'Governance', weight: 15, score: suppliedScores.governance, icon: ShieldAlert, detail: 'Promoters, litigation and related parties' },
    { key: 'issue_structure', label: 'Issue structure', weight: 10, score: suppliedScores.issue_structure, icon: Landmark, detail: 'Fresh issue, OFS, dilution and use of proceeds' },
    { key: 'demand_quality', label: 'Demand quality', weight: 10, score: suppliedScores.demand_quality ?? demand, icon: TrendingUp, detail: 'Subscription strength and investor participation' },
  ];
  const scored = scorecards.filter((item) => Number.isFinite(Number(item.score)));
  const overallScore = scored.length >= 4
    ? Math.round(scored.reduce((sum, item) => sum + Number(item.score) * item.weight, 0) / scored.reduce((sum, item) => sum + item.weight, 0))
    : null;

  const timeline = [
    ['Pre-apply opens', ipo?.preApplyStartDate],
    ['IPO opens', ipo?.biddingStartDate],
    ['IPO closes', ipo?.biddingEndDate],
    ['Allotment finalisation', ipo?.allotmentDate],
    ['Refund initiation', ipo?.refundInitiationDate],
    ['Listing', ipo?.listingDate],
    ['UPI mandate deadline', ipo?.mandateEndDate],
  ].filter(([, date]) => date).sort((a, b) => String(a[1]).localeCompare(String(b[1])));

  if (state.loading) return <LoadingDossier />;
  if (state.error || !ipo) {
    return <div className="min-h-[70vh] bg-[#f5f3ee] px-4 py-20 text-center"><h1 className="font-serif text-3xl font-semibold text-[#152f3d]">IPO dossier unavailable</h1><p className="mt-3 text-sm text-[#6f7c84]">{state.error?.message || 'This IPO could not be found in the current pipeline.'}</p><Link to="/ipo-intelligence" className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#173a4d] px-5 py-3 text-xs font-bold text-white"><ArrowLeft className="h-4 w-4" /> Return to IPO Intelligence</Link></div>;
  }

  return (
    <div className="min-h-screen bg-[#f5f3ee] text-[#152f3d]">
      <Helmet><title>{ipo.name} IPO Research | AGI</title><meta name="description" content={`Independent IPO intelligence, issue details and evidence for ${ipo.name}.`} /></Helmet>

      <section className="relative overflow-hidden bg-[#102b3b] text-white">
        <div className="absolute inset-0 opacity-50" style={{ backgroundImage: 'radial-gradient(circle at 80% 15%, rgba(197,138,89,.28), transparent 30%), linear-gradient(120deg, transparent 55%, rgba(255,255,255,.04) 55%)' }} />
        <div className="relative mx-auto max-w-[1450px] px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
          <Link to="/ipo-intelligence" className="inline-flex items-center gap-2 text-xs font-bold text-white/60 transition hover:text-white"><ArrowLeft className="h-4 w-4" /> IPO Intelligence</Link>
          <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_330px] lg:items-end">
            <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.16em]">{ipo.isSme ? 'SME issue' : 'Mainboard issue'}</span>
                <span className="rounded-full bg-[#c58a59]/20 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.16em] text-[#e5ba95]">{ipo.status || 'IPO'}</span>
                {ipo.industry && <span className="rounded-full border border-white/15 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.16em] text-white/65">{ipo.industry}</span>}
              </div>
              <h1 className="mt-5 max-w-4xl font-serif text-4xl font-semibold? font-semibold leading-[1.06] tracking-[-0.03em] sm:text-5xl lg:text-6xl">{ipo.name}</h1>
              <p className="mt-3 text-xs font-bold uppercase tracking-[0.2em] text-white/50">{ipo.symbol}{ipo.isin ? ` · ${ipo.isin}` : ''}</p>
            </motion.div>
            <div className="rounded-[24px] border border-white/10 bg-white/[0.07] p-5 backdrop-blur">
              <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/50">AGI research view</p>
              <div className="mt-3 flex items-center justify-between gap-3"><span className={`rounded-full border px-3 py-1.5 text-xs font-bold uppercase tracking-[0.12em] ${stanceTone(stance)}`}>{stance}</span>{confidence > 0 && <span className="text-xs text-white/60">{confidence}% confidence</span>}</div>
              <p className="mt-4 text-sm leading-6 text-white/70">{meta?.thesis || explicitResearch?.excerpt || 'An analyst-authored view will appear after AGI publishes verified research for this issue.'}</p>
            </div>
          </div>
        </div>
      </section>

      <div className="sticky top-[58px] z-30 border-b border-[#dce2e3] bg-[#f5f3ee]/95 backdrop-blur">
        <nav className="mx-auto flex max-w-[1450px] gap-2 overflow-x-auto px-4 py-3 sm:px-6 lg:px-8">
          {TABS.map((item) => <button key={item.id} type="button" onClick={() => setTab(item.id)} className={`shrink-0 rounded-full px-4 py-2 text-xs font-bold transition ${tab === item.id ? 'bg-[#173a4d] text-white' : 'text-[#65747c] hover:bg-white'}`}>{item.label}</button>)}
        </nav>
      </div>

      <main className="mx-auto max-w-[1450px] px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
        <section className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <Fact label="Price band" value={priceBand(ipo)} />
          <Fact label="Minimum investment" value={minimumInvestment(ipo) ? `₹${number(minimumInvestment(ipo))}` : 'Pending'} />
          <Fact label="Lot size" value={ipo.lotSize ? `${number(ipo.lotSize)} shares` : 'Pending'} />
          <Fact label="Issue size" value={ipo.issueSize != null ? `₹${number(ipo.issueSize)} crore` : 'Pending'} />
          <Fact label="Total subscription" value={ipo.subscriptionRate != null ? `${number(ipo.subscriptionRate)}x` : 'Awaiting data'} />
        </section>

        {tab === 'overview' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-8 grid gap-6 xl:grid-cols-[1fr_360px]">
            <div className="space-y-6">
              <section className="rounded-[24px] border border-[#dfe5e7] bg-white p-5 sm:p-7">
                <div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#edf3f5] text-[#173a4d]"><Target className="h-5 w-5" /></div><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#9a6944]">Decision brief</p><h2 className="font-serif text-2xl font-semibold">What matters for this issue</h2></div></div>
                <div className="mt-6 grid gap-5 md:grid-cols-2">
                  <div className="rounded-2xl bg-[#eef5f0] p-5"><p className="text-xs font-bold uppercase tracking-[0.12em] text-[#26714b]">Potential strengths</p><div className="mt-4 space-y-3">{insights.topOpportunities.slice(0, 3).map((item) => <p key={item} className="flex items-start gap-2 text-sm leading-6 text-[#405e4d]"><CheckCircle2 className="mt-1 h-4 w-4 shrink-0" />{item}</p>)}</div></div>
                  <div className="rounded-2xl bg-[#fff1eb] p-5"><p className="text-xs font-bold uppercase tracking-[0.12em] text-[#a1482e]">Principal risks</p><div className="mt-4 space-y-3">{insights.topRisks.slice(0, 3).map((item) => <p key={item} className="flex items-start gap-2 text-sm leading-6 text-[#765044]"><AlertTriangle className="mt-1 h-4 w-4 shrink-0" />{item}</p>)}</div></div>
                </div>
                {!articles.length && <EvidencePending>Publish a matching IPO research article in the CMS to replace these evidence prompts with analyst-authored strengths and risks.</EvidencePending>}
              </section>

              <section className="grid gap-6 md:grid-cols-2">
                <div className="rounded-[24px] border border-[#dfe5e7] bg-white p-5 sm:p-6"><Scale className="h-5 w-5 text-[#9a6944]" /><h2 className="mt-4 font-serif text-xl font-semibold">Valuation intelligence</h2><div className="mt-5 space-y-4"><Fact label="Offer price" value={priceBand(ipo)} /><Fact label="Cut-off price" value={ipo.cutOffPrice != null ? `₹${number(ipo.cutOffPrice)}` : 'Pending'} /></div><EvidencePending>Peer multiples and growth-adjusted valuation require verified financial statements from the offer document.</EvidencePending></div>
                <div className="rounded-[24px] border border-[#dfe5e7] bg-white p-5 sm:p-6"><Landmark className="h-5 w-5 text-[#9a6944]" /><h2 className="mt-4 font-serif text-xl font-semibold">Issue structure</h2><div className="mt-5 grid grid-cols-2 gap-3"><Fact label="Issue type" value={ipo.isSme ? 'SME' : 'Mainboard'} /><Fact label="Face value" value={ipo.faceValue != null ? `₹${number(ipo.faceValue)}` : 'Pending'} /><Fact label="Exchange" value={ipo.listingExchange} /><Fact label="Issue size" value={ipo.issueSize != null ? `₹${number(ipo.issueSize)} cr` : 'Pending'} /></div><EvidencePending>Fresh issue, OFS, dilution and use of proceeds will be sourced from the RHP.</EvidencePending></div>
              </section>

              <section className="rounded-[24px] border border-[#dfe5e7] bg-white p-5 sm:p-7">
                <div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#9a6944]">Scenario framework</p><h2 className="mt-2 font-serif text-2xl font-semibold">What could change the outcome</h2></div><Sparkles className="h-5 w-5 text-[#9a6944]" /></div>
                <div className="mt-6 grid gap-4 md:grid-cols-3">
                  {[['Bull case', insights.topOpportunities[0], 'border-[#9dceb1] bg-[#f1f8f4]'], ['Base case', meta?.thesis || explicitResearch?.excerpt || 'Issue prices within a reasonable peer range and executes its stated use of proceeds.', 'border-[#d8c495] bg-[#fffaf0]'], ['Bear case', insights.topRisks[0], 'border-[#e5b5a8] bg-[#fff5f1]']].map(([label, text, tone]) => <div key={label} className={`rounded-2xl border p-5 ${tone}`}><p className="text-xs font-bold uppercase tracking-[0.12em]">{label}</p><p className="mt-3 text-sm leading-6 text-[#56636a]">{text}</p></div>)}
                </div>
                <p className="mt-4 text-xs leading-5 text-[#7b878e]">These are research conditions, not price targets or probability forecasts. AGI will publish quantified scenarios only when sufficient financial evidence is available.</p>
              </section>
            </div>

            <aside className="space-y-5">
              <section className="rounded-[24px] bg-[#173a4d] p-6 text-white"><Gauge className="h-5 w-5 text-[#d5b694]" /><p className="mt-4 text-[10px] font-bold uppercase tracking-[0.16em] text-white/50">AGI intelligence score</p><p className="mt-2 font-serif text-5xl font-semibold">{overallScore ?? '—'}</p><p className="mt-3 text-sm leading-6 text-white/65">{overallScore != null ? 'Weighted score based on available evidence.' : 'Withheld until at least four scoring pillars have verified evidence.'}</p><Link to="#" onClick={(event) => { event.preventDefault(); setTab('scorecard'); }} className="mt-5 inline-flex items-center gap-2 text-xs font-bold text-[#e1b990]">Open scorecard <ArrowRight className="h-4 w-4" /></Link></section>
              <section className="rounded-[24px] border border-[#dfe5e7] bg-white p-6"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a969c]">Market demand signal</p><div className="mt-3 flex items-end justify-between"><p className="font-serif text-4xl font-semibold">{demand ?? '—'}</p><p className="text-sm font-bold text-[#9a6944]">{ipo.subscriptionRate != null ? `${number(ipo.subscriptionRate)}x subscribed` : 'Pending'}</p></div>{demand != null ? <ScoreBar score={demand} /> : <EvidencePending />}</section>
              {listedReturn != null && <section className="rounded-[24px] border border-[#dfe5e7] bg-white p-6"><TrendingUp className="h-5 w-5 text-[#27734d]" /><p className="mt-4 text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a969c]">Listing performance</p><p className={`mt-2 font-serif text-4xl font-semibold ${listedReturn >= 0 ? 'text-[#27734d]' : 'text-[#a33e28]'}`}>{listedReturn >= 0 ? '+' : ''}{listedReturn.toFixed(1)}%</p><p className="mt-2 text-xs text-[#738087]">Listing price ₹{number(ipo.listingPrice)} versus issue price ₹{number(ipo.cutOffPrice || ipo.maxPrice)}</p></section>}
            </aside>
          </motion.div>
        )}

        {tab === 'scorecard' && (
          <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-8">
            <div className="grid gap-6 lg:grid-cols-[330px_1fr]">
              <div className="rounded-[26px] bg-[#173a4d] p-7 text-white"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#d5b694]">Weighted framework</p><p className="mt-4 font-serif text-6xl font-semibold">{overallScore ?? '—'}</p><p className="mt-3 text-sm leading-6 text-white/65">{overallScore != null ? 'Overall AGI IPO score out of 100.' : 'No overall score is published until at least four pillars are evidence-backed.'}</p><div className="mt-6 border-t border-white/10 pt-5 text-xs leading-5 text-white/55">{scored.length} of 6 components currently scored</div></div>
              <div className="grid gap-4 md:grid-cols-2">
                {scorecards.map((item) => { const Icon = item.icon; const score = Number(item.score); const available = Number.isFinite(score); return <div key={item.key} className="rounded-[22px] border border-[#dfe5e7] bg-white p-5"><div className="flex items-start justify-between gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#edf3f5] text-[#173a4d]"><Icon className="h-4 w-4" /></div><span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#8b969c]">Weight {item.weight}%</span></div><div className="mt-4 flex items-end justify-between"><div><h3 className="font-serif text-lg font-semibold">{item.label}</h3><p className="mt-1 text-xs text-[#76838a]">{item.detail}</p></div><p className="text-2xl font-semibold">{available ? score : '—'}</p></div>{available ? <ScoreBar score={score} /> : <EvidencePending />}</div>; })}
              </div>
            </div>
          </motion.section>
        )}

        {tab === 'timeline' && (
          <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-8 grid gap-6 lg:grid-cols-[1fr_360px]">
            <div className="rounded-[26px] border border-[#dfe5e7] bg-white p-6 sm:p-8"><div className="flex items-center gap-3"><CalendarDays className="h-5 w-5 text-[#9a6944]" /><h2 className="font-serif text-2xl font-semibold">Issue calendar</h2></div><div className="mt-8">{timeline.map(([label, date], index) => <div key={label} className="relative flex gap-5 pb-8 last:pb-0"><div className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[#c8a17e] bg-[#f8eee5] text-xs font-bold text-[#8a5e3c]">{index + 1}</div>{index < timeline.length - 1 && <div className="absolute bottom-0 left-5 top-10 w-px bg-[#dce2e3]" />}<div><p className="text-xs font-bold uppercase tracking-[0.12em] text-[#8b969c]">{formatDate(date)}</p><p className="mt-1 font-serif text-lg font-semibold">{label}</p></div></div>)}{!timeline.length && <EvidencePending>No exchange dates have been published for this issue.</EvidencePending>}</div></div>
            <div className="rounded-[26px] bg-[#e8ece8] p-6"><Clock3 className="h-5 w-5 text-[#8a5e3c]" /><h2 className="mt-4 font-serif text-2xl font-semibold">Bidding window</h2><div className="mt-5 space-y-4"><Fact label="Opens" value={formatDate(ipo.biddingStartDate)} /><Fact label="Closes" value={formatDate(ipo.biddingEndDate)} /><Fact label="Daily timing" value={ipo.dailyStartTime && ipo.dailyEndTime ? `${ipo.dailyStartTime} – ${ipo.dailyEndTime} IST` : 'Exchange timing pending'} /></div></div>
          </motion.section>
        )}

        {tab === 'documents' && (
          <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-8">
            <div className="grid gap-6 lg:grid-cols-3">
              {[['Red Herring Prospectus', ipo.rhpUrl, 'Final issue terms and disclosures', FileText], ['Draft Red Herring Prospectus', ipo.drhpUrl, 'Initial filing and business disclosures', FileSearch], ['AGI research coverage', explicitResearch?.slug ? `/article/${explicitResearch.slug}` : null, 'Independent thesis, valuation and risks', BookOpen]].map(([label, url, detail, Icon]) => <div key={label} className="rounded-[24px] border border-[#dfe5e7] bg-white p-6"><div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#edf3f5] text-[#173a4d]"><Icon className="h-5 w-5" /></div><h2 className="mt-5 font-serif text-xl font-semibold">{label}</h2><p className="mt-2 text-sm leading-6 text-[#6d7a82]">{detail}</p>{url ? (url.startsWith('/') ? <Link to={url} className="mt-6 inline-flex items-center gap-2 text-xs font-bold text-[#8a5e3c]">Open research <ArrowRight className="h-4 w-4" /></Link> : <a href={url} target="_blank" rel="noreferrer" className="mt-6 inline-flex items-center gap-2 text-xs font-bold text-[#8a5e3c]">Open document <ExternalLink className="h-4 w-4" /></a>) : <EvidencePending>Document not yet available from the provider.</EvidencePending>}</div>)}
            </div>
            <div className="mt-6 rounded-[24px] border border-[#dfe5e7] bg-white p-6"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a969c]">Evidence provenance</p><div className="mt-4 grid gap-4 sm:grid-cols-3"><Fact label="Market data source" value={state.data?.source} /><Fact label="Research assets" value={`${articles.length} matching article${articles.length === 1 ? '' : 's'}`} /><Fact label="Last refreshed" value={state.data?.updatedAt ? new Date(state.data.updatedAt).toLocaleString('en-IN') : 'Pending'} /></div></div>
          </motion.section>
        )}

        <section className="mt-10 flex items-start gap-3 rounded-[20px] border border-[#ded5c8] bg-[#eee8df] p-5 text-xs leading-6 text-[#645c51]"><Info className="mt-1 h-4 w-4 shrink-0" /><p>AGI uses Bullish, Neutral and Bearish research views rather than Buy or Sell instructions. Scores are withheld when evidence is incomplete. This material is informational and not an offer, solicitation or personalised investment recommendation.</p></section>
      </main>
    </div>
  );
}
