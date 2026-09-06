import { useEffect, useMemo, useRef, useState } from 'react';
import { Helmet } from 'react-helmet';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Building2,
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Database,
  Eye,
  FileClock,
  Fingerprint,
  Info,
  Landmark,
  Layers3,
  Radar,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react';
import {
  getInstitutionalFund,
  getInstitutionalOverview,
  getInstitutionalStock,
} from '@/lib/institutionalHoldingsApi';
import InstitutionalManagerExplorer from '@/components/Research/InstitutionalManagerExplorer';
import InstitutionalIntelligenceWorkbench from '@/components/Research/InstitutionalIntelligenceWorkbench';
import InstitutionalResearchLayer from '@/components/Research/InstitutionalResearchLayer';
import './institutionalHoldingsTheme.css';

const FUND_BRANDS = {
  'berkshire-hathaway': { mark: 'BH', accent: '#aaaaaa', gradient: 'linear-gradient(145deg,#444444,#222222)', strap: 'Quality compounders' },
  'pershing-square': { mark: 'PS', accent: '#bbbbbb', gradient: 'linear-gradient(145deg,#444444,#222222)', strap: 'Concentrated activist' },
  'appaloosa-management': { mark: 'AM', accent: '#999999', gradient: 'linear-gradient(145deg,#444444,#222222)', strap: 'Opportunistic value' },
  'baupost-group': { mark: 'BG', accent: '#bbbbbb', gradient: 'linear-gradient(145deg,#444444,#333333)', strap: 'Deep value' },
  'third-point': { mark: 'III', accent: '#bbbbbb', gradient: 'linear-gradient(145deg,#555555,#333333)', strap: 'Event driven' },
  'greenlight-capital': { mark: 'GL', accent: '#bbbbbb', gradient: 'linear-gradient(145deg,#444444,#333333)', strap: 'Long-short value' },
  'coatue-management': { mark: 'C', accent: '#bbbbbb', gradient: 'linear-gradient(145deg,#555555,#222222)', strap: 'Technology growth' },
  'viking-global': { mark: 'V', accent: '#bbbbbb', gradient: 'linear-gradient(145deg,#555555,#333333)', strap: 'Fundamental growth' },
  'lone-pine-capital': { mark: 'LP', accent: '#bbbbbb', gradient: 'linear-gradient(145deg,#555555,#333333)', strap: 'Growth at a price' },
  'tiger-global': { mark: 'T', accent: '#aaaaaa', gradient: 'linear-gradient(145deg,#555555,#333333)', strap: 'Global technology' },
};

const SCORE_META = {
  conviction: { title: 'Conviction', icon: Fingerprint, copy: 'How concentrated the manager is in its ten largest disclosed positions.' },
  accumulation: { title: 'Accumulation', icon: TrendingUp, copy: 'How much disclosed portfolio weight moved into new or increased positions.' },
  new_idea: { title: 'New Idea', icon: Sparkles, copy: 'How important newly disclosed positions are within the portfolio.' },
  exit_pressure: { title: 'Exit Pressure', icon: TrendingDown, copy: 'How much disclosed weight was removed through reductions and exits.' },
  consensus: { title: 'Consensus', icon: Users, copy: 'How broadly the selected managers overlap in the same securities.' },
};

const money = (value) => {
  const amount = Number(value || 0);
  if (amount >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`;
  if (amount >= 1e6) return `$${(amount / 1e6).toFixed(1)}M`;
  return `$${Math.round(amount).toLocaleString('en-US')}`;
};

const pct = (value, digits = 1) => `${Number(value || 0).toFixed(digits)}%`;
const shortDate = (value) => value
  ? new Date(value).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })
  : 'Coverage pending';

function FundLogo({ fund, size = 'md' }) {
  const brand = FUND_BRANDS[fund?.slug] || {
    mark: String(fund?.display_name || 'AGI').split(/\s+/).map((word) => word[0]).join('').slice(0, 2),
    accent: '#aaaaaa',
    gradient: 'linear-gradient(145deg,#444444,#222222)',
    strap: fund?.strategy || 'Institutional manager',
  };
  const dimensions = size === 'lg' ? 'h-20 w-20 rounded-[24px] text-2xl' : size === 'sm' ? 'h-10 w-10 rounded-xl text-xs' : 'h-14 w-14 rounded-2xl text-base';
  return (
    <div
      className={`${dimensions} relative grid shrink-0 place-items-center overflow-hidden border border-white/15 font-bold text-white shadow-[0_12px_30px_rgba(4,25,35,.22)]`}
      style={{ background: brand.gradient }}
      aria-label={`${fund?.display_name || 'Fund'} AGI manager mark`}
    >
      <span className="absolute inset-x-2 top-2 h-px opacity-70" style={{ background: brand.accent }} />
      <span className="relative">{brand.mark}</span>
      <span className="absolute bottom-1.5 h-1 w-1 rounded-full" style={{ background: brand.accent }} />
    </div>
  );
}

function SignalPill({ type }) {
  const tones = {
    new: 'bg-emerald-100 text-emerald-800',
    increased: 'bg-neutral-100 text-neutral-800',
    reduced: 'bg-neutral-100 text-neutral-800',
    exited: 'bg-rose-100 text-rose-800',
    held: 'bg-neutral-100 text-neutral-700',
    unchanged: 'bg-neutral-100 text-neutral-700',
  };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-[.1em] ${tones[type] || tones.held}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {type || 'held'}
    </span>
  );
}

function Loading() {
  return (
    <div className="ihi-theme min-h-screen bg-[#eeeeee] px-5 py-16">
      <div className="mx-auto max-w-[1460px]">
        <div className="h-64 animate-pulse rounded-[32px] bg-[#dddddd]" />
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {[0, 1, 2].map((item) => <div key={item} className="h-48 animate-pulse rounded-3xl bg-white" />)}
        </div>
      </div>
    </div>
  );
}

function Empty({ error }) {
  return (
    <div className="ihi-theme min-h-[70vh] bg-[#eeeeee] px-5 py-20">
      <div className="mx-auto max-w-2xl rounded-[32px] border border-white bg-white/80 p-10 text-center shadow-[0_30px_80px_rgba(11,45,56,.09)] backdrop-blur">
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-[#333333] text-[#bbbbbb]">
          <Database className="h-7 w-7" />
        </div>
        <h2 className="mt-6 text-3xl font-bold text-[#222222]">Coverage is being prepared</h2>
        <p className="mt-4 text-sm leading-7 text-[#777777]">
          {error || 'The first SEC filing refresh will activate fund portfolios, stock consensus and filing signals.'}
        </p>
        <Link to="/institutional-holdings" className="mt-7 inline-flex items-center gap-2 rounded-full bg-[#333333] px-5 py-3 text-xs font-bold text-white">
          Return to overview <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}

function ModuleShell({ children, title, eyebrow, subtitle, back }) {
  return (
    <div className="ihi-theme min-h-screen bg-[#eeeeee] text-[#222222]">
      <Helmet>
        <title>{title} | AGI Institutional Holdings</title>
        <meta name="description" content={subtitle} />
      </Helmet>
      <header className="relative overflow-hidden bg-[#222222] text-white">
        <div className="absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(100,204,210,.08)_1px,transparent_1px),linear-gradient(90deg,rgba(100,204,210,.08)_1px,transparent_1px)] [background-size:42px_42px]" />
        <div className="absolute left-[66%] top-[-180px] h-[560px] w-[560px] rounded-full border border-neutral-300/20 bg-neutral-900/5 shadow-[0_0_160px_rgba(51,189,199,.16)]" />
        <div className="absolute left-[73%] top-[-90px] h-[340px] w-[340px] rounded-full border border-neutral-300/20" />
        <div className="relative mx-auto max-w-[1500px] px-5 pb-12 pt-7 sm:px-8 sm:pb-16">
          <div className="mb-10 flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
            <Link to="/institutional-holdings" className="flex items-center gap-3">
              <div className="grid h-9 w-9 place-items-center rounded-xl border border-neutral-200/20 bg-white/5">
                <Radar className="h-5 w-5 text-[#bbbbbb]" />
              </div>
              <div>
                <span className="block text-[10px] font-extrabold uppercase tracking-[.2em] text-[#bbbbbb]">AGI Intelligence</span>
                <span className="text-xs text-[#bbbbbb]">Institutional Holdings</span>
              </div>
            </Link>
            <div className="flex items-center gap-2 rounded-full border border-neutral-300 bg-neutral-100 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.12em] text-neutral-700">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-500" />
              Filing aware
            </div>
          </div>
          {back ? (
            <Link to={back} className="mb-8 inline-flex items-center gap-2 text-xs font-bold text-[#bbbbbb] transition hover:text-white">
              <ArrowLeft className="h-4 w-4" /> Back to overview
            </Link>
          ) : null}
          <p className="text-[10px] font-extrabold uppercase tracking-[.26em] text-[#bbbbbb]">{eyebrow}</p>
          <h1 className="mt-4 max-w-5xl text-4xl font-bold leading-[.98] tracking-[-.04em] sm:text-6xl lg:text-7xl">{title}</h1>
          <p className="mt-6 max-w-3xl text-sm leading-7 text-[#bbbbbb] sm:text-base">{subtitle}</p>
        </div>
      </header>
      {children}
    </div>
  );
}

function ScoreCard({ type, signal, index }) {
  const meta = SCORE_META[type];
  const Icon = meta.icon;
  const score = Number(signal?.score || 0);
  const tone = type === 'exit_pressure' ? '#888888' : '#999999';
  return (
    <motion.article
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="group relative overflow-hidden rounded-3xl border border-white bg-white/85 p-5 shadow-[0_16px_40px_rgba(16,54,64,.07)] backdrop-blur"
    >
      <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-10 transition group-hover:scale-125" style={{ background: tone }} />
      <div className="flex items-start justify-between gap-4">
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#eeeeee] text-[#555555]"><Icon className="h-5 w-5" /></div>
        <div className="text-right">
          <span className="text-3xl font-bold text-[#333333]">{signal ? Math.round(score) : '--'}</span>
          <span className="ml-1 text-[10px] text-[#999999]">/100</span>
        </div>
      </div>
      <h3 className="mt-5 text-xl font-bold capitalize">{meta.title}</h3>
      <p className="mt-2 min-h-[42px] text-xs leading-5 text-[#777777]">{signal?.explanation || meta.copy}</p>
      <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-[#eeeeee]">
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: tone }} />
      </div>
      <div className="mt-3 flex items-center justify-between text-[10px] font-bold uppercase tracking-[.1em]">
        <span className="text-[#999999]">Transparent score</span>
        <span style={{ color: tone }}>{signal?.label || 'Awaiting history'}</span>
      </div>
    </motion.article>
  );
}

function MetricCard({ icon: Icon, label, value, note }) {
  return (
    <div className="rounded-3xl border border-white bg-white/80 p-5 shadow-[0_16px_40px_rgba(12,49,59,.06)] backdrop-blur">
      <div className="flex items-center justify-between">
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#333333] text-[#bbbbbb]"><Icon className="h-5 w-5" /></div>
        <div className="h-2 w-2 rounded-full bg-[#aaaaaa] shadow-[0_0_15px_rgba(85,194,182,.8)]" />
      </div>
      <p className="mt-5 text-[10px] font-extrabold uppercase tracking-[.17em] text-[#888888]">{label}</p>
      <p className="mt-2 text-2xl font-bold text-[#222222]">{value}</p>
      {note ? <p className="mt-1 text-[11px] text-[#888888]">{note}</p> : null}
    </div>
  );
}

function MarketIntelligencePanel({ data }) {
  const intelligence = useMemo(() => {
    const rows = [...(data?.consensus || [])];
    const activity = (row) => Number(row.new_buyers || 0) + Number(row.increasers || 0) + Number(row.reducers || 0) + Number(row.exits || 0);
    const netBreadth = (row) => Number(row.new_buyers || 0) + Number(row.increasers || 0) - Number(row.reducers || 0) - Number(row.exits || 0);
    const byConsensus = [...rows].sort((a, b) => Number(b.consensus_score || 0) - Number(a.consensus_score || 0));
    const byAccumulation = [...rows].filter((row) => netBreadth(row) > 0).sort((a, b) => netBreadth(b) - netBreadth(a) || Number(b.aggregate_weight || 0) - Number(a.aggregate_weight || 0));
    const byDistribution = [...rows].filter((row) => netBreadth(row) < 0).sort((a, b) => netBreadth(a) - netBreadth(b) || Number(b.aggregate_weight || 0) - Number(a.aggregate_weight || 0));
    const activeNames = rows.filter((row) => activity(row) > 0);
    const grossAdds = rows.reduce((sum, row) => sum + Number(row.new_buyers || 0) + Number(row.increasers || 0), 0);
    const grossCuts = rows.reduce((sum, row) => sum + Number(row.reducers || 0) + Number(row.exits || 0), 0);
    const anchor = byConsensus[0];
    const leader = byAccumulation[0];
    const pressure = byDistribution[0];
    const tone = grossAdds > grossCuts ? 'Accumulation-led' : grossCuts > grossAdds ? 'Reduction-led' : 'Balanced rotation';
    const name = (row) => row?.ticker || row?.issuer_name || 'No verified name';
    return {
      anchor,
      leader,
      pressure,
      activeNames: activeNames.length,
      grossAdds,
      grossCuts,
      tone,
      headline: rows.length
        ? `${tone}: ${name(leader || anchor)} leads positive breadth${pressure ? ` while ${name(pressure)} carries the clearest reduction pressure` : ''}.`
        : 'The intelligence brief activates after verified manager portfolios are available.',
    };
  }, [data]);

  const cards = [
    { label: 'Consensus anchor', row: intelligence.anchor, icon: Radar, value: intelligence.anchor ? `${intelligence.anchor.owners}/${data?.consensus_managers || 0} managers` : '--', note: intelligence.anchor ? `${Math.round(Number(intelligence.anchor.consensus_score || 0))}/100 transparent score` : 'Awaiting verified overlap' },
    { label: 'Accumulation leader', row: intelligence.leader, icon: TrendingUp, value: intelligence.leader ? `+${Number(intelligence.leader.new_buyers || 0) + Number(intelligence.leader.increasers || 0)} managers` : '--', note: 'Initiations plus disclosed increases' },
    { label: 'Reduction pressure', row: intelligence.pressure, icon: TrendingDown, value: intelligence.pressure ? `-${Number(intelligence.pressure.reducers || 0) + Number(intelligence.pressure.exits || 0)} managers` : '--', note: 'Reductions plus disclosed exits' },
  ];

  return (
    <section id="market-intelligence" className="pt-14">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[10px] font-extrabold uppercase tracking-[.22em] text-[#777777]">AGI institutional intelligence</p>
          <h2 className="mt-3 text-3xl font-bold sm:text-4xl">What the filings say together</h2>
        </div>
        <div className="inline-flex items-center gap-2 self-start rounded-full border border-[#dddddd] bg-white/70 px-3 py-2 text-[10px] font-extrabold uppercase tracking-[.12em] text-[#555555]">
          <ShieldCheck className="h-3.5 w-3.5 text-[#888888]" /> Evidence only
        </div>
      </div>
      <div className="grid overflow-hidden rounded-[30px] border border-white bg-white/85 shadow-[0_24px_70px_rgba(12,48,59,.09)] backdrop-blur xl:grid-cols-[1.1fr_.9fr]">
        <div className="relative overflow-hidden bg-[#333333] p-7 text-white sm:p-9">
          <div className="absolute -right-20 -top-24 h-64 w-64 rounded-full border border-neutral-200/15 bg-neutral-200/5" />
          <div className="relative">
            <div className="flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-2xl border border-white/10 bg-white/5 text-[#bbbbbb]"><Sparkles className="h-5 w-5" /></div><div><p className="text-[9px] font-extrabold uppercase tracking-[.18em] text-[#aaaaaa]">Network read</p><p className="mt-1 text-xs text-[#aaaaaa]">Latest verified manager quarters</p></div></div>
            <h3 className="mt-7 max-w-3xl text-2xl font-bold leading-tight sm:text-3xl">{intelligence.headline}</h3>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-[#bbbbbb]">Across the tracked network, AGI counts {intelligence.grossAdds} positive manager actions and {intelligence.grossCuts} reductions or exits across {intelligence.activeNames} active consensus names. This measures disclosed breadth, not purchase timing or expected return.</p>
            <div className="mt-7 flex flex-wrap gap-2">
              <span className="rounded-full border border-[#bbbbbb]/25 bg-[#bbbbbb]/10 px-3 py-2 text-[10px] font-bold uppercase tracking-[.1em] text-[#cccccc]">{intelligence.tone}</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-[10px] font-bold uppercase tracking-[.1em] text-[#cccccc]">13F delayed disclosure</span>
            </div>
          </div>
        </div>
        <div className="grid gap-px bg-[#dddddd] sm:grid-cols-3 xl:grid-cols-1">
          {cards.map(({ label, row, icon: Icon, value, note }) => (
            <Link key={label} to={row ? `/institutional-holdings/stocks/${row.ticker || row.cusip}` : '#'} className="group flex items-center gap-4 bg-white p-6 transition hover:bg-[#ffffff]">
              <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[#eeeeee] text-[#555555]"><Icon className="h-5 w-5" /></div>
              <div className="min-w-0 flex-1"><p className="text-[9px] font-extrabold uppercase tracking-[.14em] text-[#999999]">{label}</p><div className="mt-1 flex items-baseline gap-2"><strong className="truncate text-xl">{row?.ticker || row?.issuer_name || 'Building'}</strong><span className="shrink-0 text-xs font-bold text-[#777777]">{value}</span></div><p className="mt-1 text-[10px] text-[#888888]">{note}</p></div>
              <ChevronRight className="h-4 w-4 shrink-0 text-[#aaaaaa] transition group-hover:translate-x-1" />
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

function OverviewPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [fundQuery, setFundQuery] = useState('');
  const [stockQuery, setStockQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    getInstitutionalOverview().then(setData).catch((err) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  const funds = useMemo(
    () => (data?.managers || []).filter((fund) => `${fund.display_name} ${fund.strategy}`.toLowerCase().includes(fundQuery.toLowerCase())),
    [data, fundQuery],
  );

  const openStock = (event) => {
    event.preventDefault();
    if (stockQuery.trim()) navigate(`/institutional-holdings/stocks/${stockQuery.trim().toUpperCase()}`);
  };

  if (loading) return <Loading />;

  return (
    <ModuleShell
      eyebrow="Public filings transformed into decision context"
      title="See where conviction is moving."
      subtitle="Search fifty institutional portfolios, expand every latest holding, and understand what changed quarter by quarter."
    >
      <main className="mx-auto max-w-[1500px] px-5 pb-16 sm:px-8">
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="-mt-7 grid overflow-hidden rounded-[30px] border border-white/70 bg-white/90 shadow-[0_30px_90px_rgba(6,37,48,.14)] backdrop-blur-xl lg:grid-cols-[1.15fr_.85fr]"
        >
          <div className="p-6 sm:p-8 lg:p-10">
            <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.18em] text-[#777777]">
              <CircleDot className="h-4 w-4" /> Search the smart-money network
            </div>
            <h2 className="mt-4 max-w-2xl text-3xl font-bold leading-tight sm:text-4xl">Which tracked funds own a stock?</h2>
            <p className="mt-3 max-w-xl text-sm leading-6 text-[#777777]">Enter a US ticker or verified CUSIP to open its manager overlap, quarterly activity and AGI Consensus Score.</p>
            <form onSubmit={openStock} className="mt-6 flex overflow-hidden rounded-2xl border border-[#dddddd] bg-[#ffffff] p-2 focus-within:border-[#999999]">
              <Search className="ml-3 mt-3 h-5 w-5 shrink-0 text-[#777777]" />
              <input
                value={stockQuery}
                onChange={(event) => setStockQuery(event.target.value)}
                placeholder="Try AAPL, AMZN or a CUSIP"
                className="min-w-0 flex-1 bg-transparent px-3 py-3 text-sm font-semibold uppercase outline-none placeholder:normal-case placeholder:font-normal"
              />
              <button className="inline-flex items-center gap-2 rounded-xl bg-[#333333] px-5 text-xs font-bold text-white transition hover:bg-[#444444]">
                Open stock <ArrowRight className="h-4 w-4" />
              </button>
            </form>
          </div>
          <div className="relative overflow-hidden bg-[#333333] p-7 text-white sm:p-9">
            <div className="absolute -right-20 -top-20 h-56 w-56 rounded-full border border-neutral-300/20" />
            <p className="text-[10px] font-extrabold uppercase tracking-[.2em] text-[#bbbbbb]">Coverage pulse</p>
            <div className="mt-6 grid grid-cols-2 gap-4">
              <div><span className="text-4xl font-bold">{data?.covered_managers || 10}</span><p className="mt-1 text-xs text-[#bbbbbb]">Selected managers</p></div>
              <div><span className="text-4xl font-bold">{data?.consensus_managers || 0}</span><p className="mt-1 text-xs text-[#bbbbbb]">Current for consensus</p></div>
              <div><span className="text-2xl font-bold">{data?.latest_report_date || 'Pending'}</span><p className="mt-1 text-xs text-[#bbbbbb]">Latest quarter</p></div>
              <div><span className="text-4xl font-bold">{data?.consensus?.length || 0}</span><p className="mt-1 text-xs text-[#bbbbbb]">Consensus names</p></div>
            </div>
            <div className="mt-7 flex items-center gap-2 border-t border-white/10 pt-5 text-[11px] text-[#bbbbbb]">
              <ShieldCheck className="h-4 w-4 text-[#bbbbbb]" /> Point-in-time and amendment aware
            </div>
          </div>
        </motion.section>

        {error ? <div className="mt-8"><Empty error={error} /></div> : (
          <>
            <MarketIntelligencePanel data={data} />
            <InstitutionalIntelligenceWorkbench />
            <InstitutionalResearchLayer />

            <section id="funds" className="pt-14">
              <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-[10px] font-extrabold uppercase tracking-[.22em] text-[#777777]">Manager constellation</p>
                  <h2 className="mt-3 text-3xl font-bold sm:text-4xl">Choose a portfolio to explore</h2>
                  <p className="mt-2 text-sm text-[#777777]">Each profile separates the reporting quarter from the date clients could actually know it.</p>
                </div>
                <ManagerSearch managers={data?.managers || []} query={fundQuery} onQuery={setFundQuery} />
              </div>

              <InstitutionalManagerExplorer funds={funds} />
            </section>

            <section id="consensus" className="mt-16 grid gap-6 xl:grid-cols-[1.55fr_.75fr]">
              <div className="overflow-hidden rounded-[30px] border border-white bg-white/85 shadow-[0_20px_55px_rgba(12,48,59,.08)] backdrop-blur">
                <div className="flex flex-col gap-4 border-b border-[#eeeeee] p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
                  <div>
                    <p className="text-[10px] font-extrabold uppercase tracking-[.2em] text-[#777777]">Collective positioning</p>
                    <h2 className="mt-2 text-3xl font-bold">Consensus radar</h2>
                    <p className="mt-2 text-xs text-[#888888]">{data.consensus_ready ? 'Breadth across active tracked portfolios, not a recommendation.' : `Scores activate after ${data.consensus_min_managers || 4} manager portfolios are verified. Holdings remain visible meanwhile.`}</p>
                  </div>
                  <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[#333333] text-[#bbbbbb]"><Radar className="h-6 w-6" /></div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[780px] text-left">
                    <thead className="bg-[#ffffff] text-[9px] font-extrabold uppercase tracking-[.16em] text-[#6f6f6f]">
                      <tr><th className="px-8 py-4">Security</th><th className="px-4 py-4">Fund network</th><th className="px-4 py-4">Aggregate weight</th><th className="px-4 py-4">Quarter activity</th><th className="px-8 py-4 text-right">AGI score</th></tr>
                    </thead>
                    <tbody>
                      {(data?.consensus || []).slice(0, 16).map((row, index) => (
                        <tr key={row.key} className="border-t border-[#eeeeee] transition hover:bg-[#ffffff]">
                          <td className="px-8 py-4">
                            <div className="flex items-center gap-3">
                              <div className="grid h-9 w-9 place-items-center rounded-xl bg-[#eeeeee] text-[10px] font-extrabold text-[#555555]">{row.ticker?.slice(0, 3) || String(index + 1).padStart(2, '0')}</div>
                              <div><Link to={`/institutional-holdings/stocks/${row.ticker || row.cusip}`} className="text-sm font-extrabold hover:text-[#666666]">{row.ticker || row.issuer_name}</Link><span className="block max-w-[220px] truncate text-[11px] text-[#888888]">{row.issuer_name}</span></div>
                            </div>
                          </td>
                          <td className="px-4 py-4">
                            <strong className="text-sm">{row.owners}/{data.consensus_managers}</strong>
                            <div className="mt-2 h-1.5 w-24 overflow-hidden rounded-full bg-[#eeeeee]"><div className="h-full rounded-full bg-[#999999]" style={{ width: `${(row.owners / Math.max(data.consensus_managers, 1)) * 100}%` }} /></div>
                          </td>
                          <td className="px-4 py-4 text-sm font-semibold">{pct(row.aggregate_weight)}</td>
                          <td className="px-4 py-4"><span className="text-xs font-bold text-emerald-700">+{row.new_buyers + row.increasers}</span><span className="mx-2 text-[#bbbbbb]">/</span><span className="text-xs font-bold text-rose-700">-{row.reducers + row.exits}</span></td>
                          <td className="px-8 py-4 text-right"><span className="text-2xl font-bold">{data.consensus_ready ? Math.round(row.consensus_score) : '--'}</span><span className="ml-1 text-[9px] text-[#999999]">{data.consensus_ready ? '/100' : 'gated'}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!data?.consensus?.length ? <p className="p-10 text-center text-sm text-[#888888]">The consensus radar activates after the first SEC refresh.</p> : null}
              </div>

              <aside id="alerts" className="relative overflow-hidden rounded-[30px] bg-[#333333] p-7 text-white shadow-[0_24px_65px_rgba(7,37,48,.2)]">
                <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full border border-neutral-200/10" />
                <div className="flex items-center justify-between">
                  <div><p className="text-[10px] font-extrabold uppercase tracking-[.2em] text-[#bbbbbb]">Disclosure monitor</p><h2 className="mt-2 text-2xl font-bold">Filing signals</h2></div>
                  <Zap className="h-6 w-6 text-[#bbbbbb]" />
                </div>
                <div className="mt-7 space-y-5">
                  {(data?.alerts || []).slice(0, 7).map((alert) => (
                    <article key={alert.id} className="relative border-l border-[#666666] pl-5">
                      <span className="absolute -left-1 top-1 h-2 w-2 rounded-full bg-[#bbbbbb] shadow-[0_0_12px_rgba(109,210,197,.7)]" />
                      <div className="flex items-center gap-2 text-[9px] font-bold uppercase tracking-[.12em] text-[#bbbbbb]"><span>{alert.severity}</span><span className="text-[#777777]">/</span><span>{shortDate(alert.created_at)}</span></div>
                      <h3 className="mt-2 text-sm font-bold leading-5">{alert.title}</h3>
                      <p className="mt-1 text-xs leading-5 text-[#bbbbbb]">{alert.body}</p>
                    </article>
                  ))}
                  {!data?.alerts?.length ? <p className="text-sm leading-6 text-[#bbbbbb]">New filings, amendments, material initiations and reported exits will appear here.</p> : null}
                </div>
              </aside>
            </section>

            <section id="methodology" className="mt-16">
              <div className="text-center">
                <p className="text-[10px] font-extrabold uppercase tracking-[.22em] text-[#777777]">Explainable by design</p>
                <h2 className="mt-3 text-3xl font-bold sm:text-4xl">Five signals. Every input visible.</h2>
                <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[#777777]">Scores summarize disclosed positioning. They never claim to know a manager's current portfolio or expected return.</p>
              </div>
              <div className="mt-8 grid gap-4 md:grid-cols-5">
                {Object.keys(SCORE_META).map((key, index) => <ScoreCard key={key} type={key} index={index} />)}
              </div>
            </section>

            <section className="mt-14 flex flex-col gap-5 rounded-[28px] border border-[#dddddd] bg-[#ffffff] p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
              <div className="flex gap-4">
                <Info className="mt-1 h-5 w-5 shrink-0 text-[#777777]" />
                <div><h3 className="text-lg font-bold">A disclosure lens, not a live portfolio</h3><p className="mt-1 max-w-3xl text-xs leading-6 text-[#777777]">Form 13F is delayed and excludes cash, shorts and many non-reportable assets. AGI uses the SEC acceptance timestamp so a quarter is never presented as knowable before publication.</p></div>
              </div>
              <a href="https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/frequently-asked-questions-about-form-13f" target="_blank" rel="noreferrer" className="inline-flex shrink-0 items-center gap-2 text-xs font-bold text-[#555555]">Read SEC methodology <ArrowRight className="h-4 w-4" /></a>
            </section>
          </>
        )}
      </main>
    </ModuleShell>
  );
}

function FundPage({ slug }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    getInstitutionalFund(slug).then(setData).catch((err) => setError(err.message));
  }, [slug]);

  if (!data && !error) return <Loading />;
  if (error || !data) return <Empty error={error} />;

  const fund = data.manager;
  const changesByCusip = new Map((data.changes || []).map((row) => [row.cusip, row]));
  const signals = new Map((data.signals || []).map((row) => [row.signal_type, row]));
  const activeRows = filter === 'exited'
    ? (data.changes || []).filter((row) => row.change_type === 'exited')
    : filter === 'all'
      ? data.holdings
      : data.holdings.filter((row) => changesByCusip.get(row.cusip)?.change_type === filter);

  return (
    <ModuleShell
      back="/institutional-holdings"
      eyebrow={`${fund.strategy} / CIK ${fund.cik}`}
      title={fund.display_name}
      subtitle={`Explore the portfolio reported for ${data.latest_filing?.report_date || 'the pending coverage period'} and disclosed publicly on ${shortDate(data.latest_filing?.filed_at)}.`}
    >
      <main className="mx-auto max-w-[1500px] px-5 pb-16 sm:px-8">
        <section className="-mt-8 flex flex-col gap-5 rounded-[30px] border border-white bg-white/90 p-6 shadow-[0_28px_80px_rgba(6,37,48,.13)] backdrop-blur sm:flex-row sm:items-center sm:justify-between sm:p-8">
          <div className="flex items-center gap-5"><FundLogo fund={fund} size="lg" /><div><p className="text-[10px] font-extrabold uppercase tracking-[.16em] text-[#777777]">Tracked legal filer</p><h2 className="mt-1 text-2xl font-bold">{fund.legal_name}</h2><p className="mt-1 text-xs text-[#888888]">Quarter {data.latest_filing?.report_date || 'pending'}</p></div></div>
          <div className="flex items-center gap-3 rounded-2xl bg-[#eeeeee] px-4 py-3 text-xs font-bold text-[#666666]"><CheckCircle2 className="h-5 w-5" /> Point-in-time verified</div>
        </section>

        <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard icon={Building2} label="Disclosed value" value={money(data.latest_filing?.total_value_usd)} note="Reported market value" />
          <MetricCard icon={Layers3} label="Positions" value={data.latest_filing?.holdings_count || 0} note="Includes separately reported lines" />
          <MetricCard icon={FileClock} label="Filing version" value={data.latest_filing?.amendment_type || 'Pending'} note={data.latest_filing?.form_type || '13F coverage'} />
          <MetricCard icon={Eye} label="Public since" value={shortDate(data.latest_filing?.filed_at)} note="SEC acceptance timestamp" />
        </section>

        <section className="mt-8">
          <div className="mb-5 flex items-center justify-between"><div><p className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#777777]">Manager signal profile</p><h2 className="mt-2 text-3xl font-bold">What changed and how much it matters</h2></div></div>
          <div className="grid gap-4 md:grid-cols-5">
            {Object.keys(SCORE_META).map((key, index) => <ScoreCard key={key} type={key} signal={signals.get(key)} index={index} />)}
          </div>
        </section>

        <section className="mt-10 grid gap-6 xl:grid-cols-[1.6fr_.65fr]">
          <div className="overflow-hidden rounded-[30px] border border-white bg-white/90 shadow-[0_20px_55px_rgba(12,48,59,.07)]">
            <div className="flex flex-col gap-5 border-b border-[#eeeeee] p-6 sm:flex-row sm:items-end sm:justify-between sm:p-8">
              <div><p className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#777777]">Position intelligence</p><h2 className="mt-2 text-3xl font-bold">Disclosed portfolio</h2></div>
              <div className="flex flex-wrap gap-2">
                {['all', 'new', 'increased', 'reduced', 'exited'].map((key) => (
                  <button key={key} onClick={() => setFilter(key)} className={`rounded-full px-3.5 py-2 text-[10px] font-extrabold uppercase tracking-[.08em] transition ${filter === key ? 'bg-[#333333] text-white shadow-lg' : 'bg-[#eeeeee] text-[#666666] hover:bg-[#eeeeee]'}`}>{key}</button>
                ))}
              </div>
            </div>
            {/* Historical repair.
                Amendments are repaired quarter by quarter, so there is a window
                where some history is corrected and some is not. A consensus
                number computed across both is not a number of anything, so it
                is labelled rather than quietly published. */}
            {data?.data_integrity && data.data_integrity.clean === false ? (
              <div className="mx-8 mb-4 flex items-start gap-2.5 rounded-lg border border-[#aaaaaa] bg-[#ffffff] px-4 py-3">
                <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-[#888888]" />
                <p className="text-[11px] leading-5 text-[#555555]">
                  <span className="font-bold text-[#444444]">Historical repair in progress.</span>{' '}
                  {data.data_integrity.message}
                  {Number(data.data_integrity.pending_review) > 0
                    ? ` ${data.data_integrity.pending_review} filing(s) are awaiting review and are excluded from these figures.`
                    : ''}
                </p>
              </div>
            ) : null}
            {/* What a reader is entitled to know before reading the table: this is a
                partial view assembled from filings that were already weeks old when
                they became public. Stated once, plainly, above the data itself. */}
            <div className="mx-8 mb-4 flex items-start gap-2.5 rounded-lg border border-[#cccccc] bg-[#eeeeee] px-4 py-3">
              <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-[#777777]" />
              <p className="text-[11px] leading-5 text-[#666666]">
                <span className="font-bold text-[#444444]">Coverage in build.</span>{' '}
                Derived from delayed public filings. Not a complete institutional ownership universe.
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-left">
                <thead className="bg-[#ffffff] text-[9px] font-extrabold uppercase tracking-[.15em] text-[#6f6f6f]"><tr><th className="px-8 py-4">Security</th><th className="px-4 py-4">Portfolio weight</th><th className="px-4 py-4">Reported value</th><th className="px-4 py-4">Shares</th><th className="px-8 py-4">Quarter signal</th></tr></thead>
                <tbody>
                  {activeRows.map((row) => {
                    const change = changesByCusip.get(row.cusip) || row;
                    const weight = Number(row.portfolio_weight || row.previous_weight || 0);
                    return (
                      <tr key={`${row.cusip}-${row.put_call || ''}`} className="border-t border-[#eeeeee] hover:bg-[#ffffff]">
                        <td className="px-8 py-4">
                          <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-[#eeeeee] text-[10px] font-extrabold text-[#555555]">{row.ticker?.slice(0, 3) || 'ID'}</div><div><Link to={`/institutional-holdings/stocks/${row.ticker || row.cusip}`} className="text-sm font-extrabold hover:text-[#666666]">{row.ticker || row.issuer_name}</Link><span className="block max-w-[250px] truncate text-[11px] text-[#888888]">{row.issuer_name}{row.put_call ? ` / ${row.put_call}` : ''}</span></div></div>
                        </td>
                        <td className="px-4 py-4"><strong className="text-sm">{pct(weight)}</strong><div className="mt-2 h-1.5 w-28 overflow-hidden rounded-full bg-[#eeeeee]"><div className="h-full rounded-full bg-gradient-to-r from-[#888888] to-[#aaaaaa]" style={{ width: `${Math.min(weight * 5, 100)}%` }} /></div></td>
                        <td className="px-4 py-4 text-sm font-semibold">{money(row.value_usd)}</td>
                        <td className="px-4 py-4 text-sm">{Number(row.shares || row.previous_shares || 0).toLocaleString('en-US')}</td>
                        <td className="px-8 py-4"><SignalPill type={change.change_type || 'held'} /></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {!activeRows.length ? <p className="p-10 text-center text-sm text-[#888888]">No positions match this activity view.</p> : null}
          </div>

          <aside className="rounded-[30px] bg-[#333333] p-6 text-white shadow-[0_24px_65px_rgba(7,37,48,.18)]">
            <div className="flex items-center justify-between"><div><p className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#bbbbbb]">Time machine</p><h2 className="mt-2 text-2xl font-bold">Quarter archive</h2></div><CalendarClock className="h-6 w-6 text-[#bbbbbb]" /></div>
            <div className="mt-6 space-y-3">
              {(data.filings || []).map((filing, index) => (
                <a key={filing.id} href={filing.source_url} target="_blank" rel="noreferrer" className="group block rounded-2xl border border-white/10 bg-white/5 p-4 transition hover:border-[#bbbbbb]/50 hover:bg-white/10">
                  <div className="flex items-center justify-between gap-3"><strong className="text-lg">{filing.report_date}</strong><span className="rounded-full bg-white/10 px-2 py-1 text-[9px] font-bold uppercase text-[#dddddd]">{filing.form_type}</span></div>
                  <p className="mt-2 text-xs text-[#cccccc]">{filing.holdings_count} lines / {money(filing.total_value_usd)}</p>
                  <div className="mt-3 flex items-center justify-between border-t border-white/10 pt-3 text-[9px] uppercase tracking-[.08em] text-[#999999]"><span>Accepted {shortDate(filing.filed_at)}</span><ChevronRight className="h-3 w-3 transition group-hover:translate-x-1" /></div>
                </a>
              ))}
            </div>
          </aside>
        </section>
      </main>
    </ModuleShell>
  );
}

function StockPage({ stockKey }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getInstitutionalStock(stockKey).then(setData).catch((err) => setError(err.message));
  }, [stockKey]);

  if (!data && !error) return <Loading />;
  if (error || !data) return <Empty error={error} />;

  const scoreAvailable = Boolean(data.consensus_ready) && Number.isFinite(Number(data.consensus_score));
  const score = scoreAvailable ? Math.round(Number(data.consensus_score)) : 0;
  const flow = (data.changes || []).reduce((summary, row) => {
    const type = row.change_type || 'held';
    summary[type] = (summary[type] || 0) + 1;
    return summary;
  }, { new: 0, increased: 0, reduced: 0, exited: 0, held: 0 });
  const positiveBreadth = flow.new + flow.increased;
  const negativeBreadth = flow.reduced + flow.exited;
  const flowTone = positiveBreadth > negativeBreadth ? 'Positive breadth' : negativeBreadth > positiveBreadth ? 'Negative breadth' : 'Balanced breadth';
  const flowCopy = positiveBreadth > negativeBreadth
    ? `${positiveBreadth} tracked managers initiated or increased the security, compared with ${negativeBreadth} reducing or exiting.`
    : negativeBreadth > positiveBreadth
      ? `${negativeBreadth} tracked managers reduced or exited the security, compared with ${positiveBreadth} initiating or increasing.`
      : `${positiveBreadth} managers added exposure and ${negativeBreadth} reduced it, leaving disclosed activity balanced.`;
  return (
    <ModuleShell
      back="/institutional-holdings"
      eyebrow={`Consensus security / CUSIP ${data.cusip}`}
      title={data.ticker || data.issuer_name}
      subtitle={`${data.owner_count} of ${data.manager_count} current manager portfolios disclose this security. Stale fund histories are excluded from consensus scoring.`}
    >
      <main className="mx-auto max-w-[1380px] px-5 pb-16 sm:px-8">
        <section className="-mt-8 grid overflow-hidden rounded-[32px] border border-white bg-white/90 shadow-[0_30px_80px_rgba(6,37,48,.13)] backdrop-blur lg:grid-cols-[360px_1fr]">
          <div className="relative grid place-items-center overflow-hidden bg-[#333333] p-10 text-white">
            <div className="absolute inset-0 opacity-30 [background-image:radial-gradient(circle_at_center,rgba(101,210,199,.25),transparent_60%)]" />
            <div className="relative grid h-52 w-52 place-items-center rounded-full" style={{ background: `conic-gradient(#bbbbbb ${score}%, rgba(255,255,255,.1) 0)` }}>
              <div className="grid h-[174px] w-[174px] place-items-center rounded-full bg-[#333333] text-center">
                <div><span className="text-6xl font-bold">{scoreAvailable ? score : '--'}</span><span className="block text-[10px] font-extrabold uppercase tracking-[.18em] text-[#aaaaaa]">{scoreAvailable ? 'Consensus score' : 'Coverage building'}</span></div>
              </div>
            </div>
            <p className="relative mt-5 text-center text-xs leading-5 text-[#cccccc]">{scoreAvailable ? 'Breadth plus average disclosed portfolio importance' : `Available after ${data.consensus_min_managers || 4} manager portfolios are verified`}</p>
          </div>
          <div className="grid gap-px bg-[#eeeeee] sm:grid-cols-2">
            <div className="bg-white p-7"><Users className="h-5 w-5 text-[#777777]" /><p className="mt-5 text-[10px] font-extrabold uppercase tracking-[.14em] text-[#888888]">Manager ownership</p><p className="mt-2 text-4xl font-bold">{data.owner_count}<span className="text-xl text-[#999999]">/{data.manager_count}</span></p></div>
            <div className="bg-white p-7"><BarChart3 className="h-5 w-5 text-[#777777]" /><p className="mt-5 text-[10px] font-extrabold uppercase tracking-[.14em] text-[#888888]">Aggregate weight</p><p className="mt-2 text-4xl font-bold">{pct(data.aggregate_weight)}</p></div>
            <div className="bg-white p-7"><Building2 className="h-5 w-5 text-[#777777]" /><p className="mt-5 text-[10px] font-extrabold uppercase tracking-[.14em] text-[#888888]">Reported value</p><p className="mt-2 text-4xl font-bold">{money(data.aggregate_value_usd)}</p></div>
            <div className="bg-white p-7"><Activity className="h-5 w-5 text-[#777777]" /><p className="mt-5 text-[10px] font-extrabold uppercase tracking-[.14em] text-[#888888]">Latest activity</p><p className="mt-2 text-2xl font-bold">{(data.changes || []).filter((row) => ['new', 'increased'].includes(row.change_type)).length} adding</p></div>
          </div>
        </section>

        <section className="mt-8 grid overflow-hidden rounded-[28px] border border-white bg-white/85 shadow-[0_18px_50px_rgba(12,48,59,.07)] lg:grid-cols-[1fr_1.2fr]">
          <div className="bg-[#333333] p-7 text-white sm:p-8">
            <div className="flex items-center justify-between"><div><p className="text-[9px] font-extrabold uppercase tracking-[.18em] text-[#aaaaaa]">Quarterly flow verdict</p><h2 className="mt-2 text-2xl font-bold">{flowTone}</h2></div><Activity className="h-6 w-6 text-[#bbbbbb]" /></div>
            <p className="mt-4 text-sm leading-7 text-[#bbbbbb]">{flowCopy}</p>
            <p className="mt-5 border-t border-white/10 pt-4 text-[10px] leading-5 text-[#999999]">The verdict counts reporting managers equally. Use portfolio-weight changes below to judge how material each action was.</p>
          </div>
          <div className="grid grid-cols-2 gap-px bg-[#dddddd] sm:grid-cols-4 lg:grid-cols-2 xl:grid-cols-4">
            {[['New', flow.new, TrendingUp, '#777777'], ['Increased', flow.increased, ArrowRight, '#666666'], ['Reduced', flow.reduced, TrendingDown, '#777777'], ['Exited', flow.exited, ArrowLeft, '#666666']].map(([label, value, Icon, color]) => (
              <div key={label} className="bg-white p-5 sm:p-6"><Icon className="h-4 w-4" style={{ color }} /><p className="mt-5 text-[9px] font-extrabold uppercase tracking-[.14em] text-[#999999]">{label}</p><p className="mt-1 text-3xl font-bold">{value}</p><p className="mt-1 text-[10px] text-[#999999]">reporting managers</p></div>
            ))}
          </div>
        </section>

        <section className="mt-10">
          <div><p className="text-[10px] font-extrabold uppercase tracking-[.2em] text-[#777777]">Ownership network</p><h2 className="mt-2 text-3xl font-bold sm:text-4xl">Who owns it and what changed</h2><p className="mt-2 text-sm text-[#777777]">Position weights are comparable within each manager's disclosed 13F portfolio.</p></div>
          <div className="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {(data.owners || []).map((row, index) => {
              const manager = row.manager || {};
              const change = (data.changes || []).find((item) => item.manager_id === row.manager_id);
              return (
                <motion.div key={row.manager_id} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}>
                  <Link to={`/institutional-holdings/funds/${manager.slug}`} className="group block rounded-[28px] border border-white bg-white/85 p-6 shadow-[0_18px_45px_rgba(12,48,59,.07)] transition hover:-translate-y-1 hover:shadow-[0_26px_60px_rgba(12,48,59,.13)]">
                    <div className="flex items-start justify-between gap-4"><div className="flex items-center gap-3"><FundLogo fund={manager} size="sm" /><div><h3 className="text-lg font-bold">{manager.display_name}</h3><p className="text-[10px] text-[#888888]">Quarter {row.report_date}</p></div></div><SignalPill type={change?.change_type || 'held'} /></div>
                    <div className="mt-7 flex items-end justify-between"><div><p className="text-[9px] font-bold uppercase tracking-[.13em] text-[#999999]">Portfolio weight</p><p className="mt-1 text-3xl font-bold">{pct(row.portfolio_weight)}</p></div><p className="text-sm font-semibold">{money(row.value_usd)}</p></div>
                    <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-[#eeeeee]"><div className="h-full rounded-full bg-gradient-to-r from-[#888888] to-[#aaaaaa]" style={{ width: `${Math.min(Number(row.portfolio_weight || 0) * 7, 100)}%` }} /></div>
                    <div className="mt-4 grid grid-cols-2 gap-3 rounded-2xl bg-[#eeeeee] p-3 text-[10px]"><div><span className="block uppercase tracking-[.1em] text-[#999999]">Previous weight</span><strong className="mt-1 block text-xs text-[#444444]">{change ? pct(change.previous_weight) : '--'}</strong></div><div><span className="block uppercase tracking-[.1em] text-[#999999]">Weight change</span><strong className={`mt-1 block text-xs ${Number(change?.weight_change || 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>{change ? `${Number(change.weight_change || 0) >= 0 ? '+' : ''}${pct(change.weight_change)}` : '--'}</strong></div></div>
                    <div className="mt-5 flex items-center justify-between border-t border-[#eeeeee] pt-4 text-[10px] font-bold uppercase tracking-[.08em] text-[#666666]"><span>Open manager portfolio</span><ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></div>
                  </Link>
                </motion.div>
              );
            })}
          </div>
        </section>

        <section className="mt-12 grid gap-5 lg:grid-cols-2">
          <div className="rounded-[28px] bg-[#333333] p-7 text-white">
            <ShieldCheck className="h-6 w-6 text-[#bbbbbb]" />
            <h2 className="mt-5 text-2xl font-bold">What the score tells you</h2>
            <p className="mt-3 text-sm leading-7 text-[#cccccc]">A higher score means ownership is broader across the selected network and the position matters more inside those disclosed portfolios.</p>
          </div>
          <div className="rounded-[28px] border border-[#dddddd] bg-[#ffffff] p-7">
            <Info className="h-6 w-6 text-[#777777]" />
            <h2 className="mt-5 text-2xl font-bold">What it cannot tell you</h2>
            <p className="mt-3 text-sm leading-7 text-[#777777]">It cannot confirm a current holding, purchase price, short position, hedge, expected return or agreement among managers.</p>
          </div>
        </section>
      </main>
    </ModuleShell>
  );
}

/**
 * Manager search with suggestions.
 *
 * Typing filters the explorer below as it always did; the list that appears is
 * the same match set, shown rather than left for the reader to infer. Fifty
 * managers is past the point where scanning a grid beats naming the one you
 * want - and half of them are known by a person's name rather than the firm's,
 * so matching runs over the strategy text too.
 *
 * Built as a combobox rather than a styled input: arrow keys move, Enter picks,
 * Escape closes and clears the highlight, and the active option is announced.
 * A search box that only works with a mouse is a search box half the desk
 * cannot use quickly.
 */
function ManagerSearch({ managers, query, onQuery }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const boxRef = useRef(null);

  const suggestions = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return [];
    const hay = (fund) => `${fund.display_name} ${fund.legal_name || ''} ${fund.strategy || ''}`.toLowerCase();
    const scored = (managers || [])
      .filter((fund) => hay(fund).includes(term))
      // A name that starts with what was typed is almost always the one meant.
      .sort((a, b) => {
        const aStarts = a.display_name.toLowerCase().startsWith(term) ? 0 : 1;
        const bStarts = b.display_name.toLowerCase().startsWith(term) ? 0 : 1;
        return aStarts - bStarts || a.display_name.localeCompare(b.display_name);
      });
    return scored.slice(0, 8);
  }, [managers, query]);

  // An exact match means the reader has already chosen; keep the list shut.
  const exact = suggestions.length === 1
    && suggestions[0].display_name.toLowerCase() === query.trim().toLowerCase();
  const show = open && suggestions.length > 0 && !exact;

  useEffect(() => { setActive(-1); }, [query]);

  useEffect(() => {
    const away = (event) => { if (boxRef.current && !boxRef.current.contains(event.target)) setOpen(false); };
    document.addEventListener('mousedown', away);
    return () => document.removeEventListener('mousedown', away);
  }, []);

  const choose = (fund) => { onQuery(fund.display_name); setOpen(false); setActive(-1); };

  const onKeyDown = (event) => {
    if (!show) { if (event.key === 'ArrowDown' && suggestions.length) setOpen(true); return; }
    if (event.key === 'ArrowDown') { event.preventDefault(); setActive((i) => (i + 1) % suggestions.length); }
    else if (event.key === 'ArrowUp') { event.preventDefault(); setActive((i) => (i <= 0 ? suggestions.length : i) - 1); }
    else if (event.key === 'Enter' && active >= 0) { event.preventDefault(); choose(suggestions[active]); }
    else if (event.key === 'Escape') { setOpen(false); setActive(-1); }
  };

  return (
    <div ref={boxRef} className="relative w-full max-w-sm">
      <label className="flex items-center gap-3 rounded-2xl border border-white bg-white/75 px-4 shadow-sm">
        <Search className="h-4 w-4 text-[#888888]" />
        <input
          value={query}
          onChange={(event) => { onQuery(event.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="Find a manager"
          className="w-full bg-transparent py-3.5 text-sm outline-none placeholder:text-[#999999]"
          role="combobox"
          aria-expanded={show}
          aria-controls="manager-search-list"
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? `manager-option-${active}` : undefined}
          autoComplete="off"
        />
        {query ? (
          <button
            type="button"
            onClick={() => { onQuery(''); setOpen(false); }}
            className="text-[11px] font-bold uppercase tracking-[.14em] text-[#999999] hover:text-[#444444]"
            aria-label="Clear search"
          >
            Clear
          </button>
        ) : null}
      </label>

      {show ? (
        <ul
          id="manager-search-list"
          role="listbox"
          className="absolute z-30 mt-2 w-full overflow-hidden rounded-2xl border border-[#dddddd] bg-white shadow-[0_18px_44px_rgba(0,0,0,.14)]"
        >
          {suggestions.map((fund, index) => (
            <li key={fund.id || fund.slug} role="option" aria-selected={index === active} id={`manager-option-${index}`}>
              <button
                type="button"
                onMouseEnter={() => setActive(index)}
                onClick={() => choose(fund)}
                className={`flex w-full items-baseline justify-between gap-3 px-4 py-3 text-left ${index === active ? 'bg-[#f2f2f2]' : 'bg-white'}`}
              >
                <span className="text-sm font-semibold text-[#222222]">{fund.display_name}</span>
                <span className="shrink-0 text-[10px] font-bold uppercase tracking-[.14em] text-[#888888]">
                  {fund.strategy || '13F filer'}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export default function InstitutionalHoldingsPage() {
  const { fundSlug, stockKey } = useParams();
  if (fundSlug) return <FundPage slug={fundSlug} />;
  if (stockKey) return <StockPage stockKey={stockKey} />;
  return <OverviewPage />;
}
