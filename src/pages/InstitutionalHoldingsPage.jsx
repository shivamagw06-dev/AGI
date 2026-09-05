import { useEffect, useMemo, useState } from 'react';
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
import './institutionalHoldingsTheme.css';

const FUND_BRANDS = {
  'berkshire-hathaway': { mark: 'BH', accent: '#d7a15f', gradient: 'linear-gradient(145deg,#173d51,#0b2230)', strap: 'Quality compounders' },
  'pershing-square': { mark: 'PS', accent: '#79c8d4', gradient: 'linear-gradient(145deg,#174f60,#0a2937)', strap: 'Concentrated activist' },
  'appaloosa-management': { mark: 'AM', accent: '#e18c62', gradient: 'linear-gradient(145deg,#653c35,#251d27)', strap: 'Opportunistic value' },
  'baupost-group': { mark: 'BG', accent: '#d8bf75', gradient: 'linear-gradient(145deg,#4e4935,#1f282a)', strap: 'Deep value' },
  'third-point': { mark: 'III', accent: '#7cc7bb', gradient: 'linear-gradient(145deg,#1d5b59,#102c36)', strap: 'Event driven' },
  'greenlight-capital': { mark: 'GL', accent: '#7fd19c', gradient: 'linear-gradient(145deg,#195444,#122c32)', strap: 'Long-short value' },
  'coatue-management': { mark: 'C', accent: '#88b7ff', gradient: 'linear-gradient(145deg,#254f85,#15263d)', strap: 'Technology growth' },
  'viking-global': { mark: 'V', accent: '#e2b36e', gradient: 'linear-gradient(145deg,#664a31,#292633)', strap: 'Fundamental growth' },
  'lone-pine-capital': { mark: 'LP', accent: '#8fc89f', gradient: 'linear-gradient(145deg,#315944,#1c3031)', strap: 'Growth at a price' },
  'tiger-global': { mark: 'T', accent: '#f09b6f', gradient: 'linear-gradient(145deg,#6c4037,#2d2731)', strap: 'Global technology' },
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
    accent: '#d7a15f',
    gradient: 'linear-gradient(145deg,#173d51,#0b2230)',
    strap: fund?.strategy || 'Institutional manager',
  };
  const dimensions = size === 'lg' ? 'h-20 w-20 rounded-[24px] text-2xl' : size === 'sm' ? 'h-10 w-10 rounded-xl text-xs' : 'h-14 w-14 rounded-2xl text-base';
  return (
    <div
      className={`${dimensions} relative grid shrink-0 place-items-center overflow-hidden border border-white/15 font-serif font-bold text-white shadow-[0_12px_30px_rgba(4,25,35,.22)]`}
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
    increased: 'bg-cyan-100 text-cyan-800',
    reduced: 'bg-amber-100 text-amber-800',
    exited: 'bg-rose-100 text-rose-800',
    held: 'bg-slate-100 text-slate-600',
    unchanged: 'bg-slate-100 text-slate-600',
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
    <div className="ihi-theme min-h-screen bg-[#eaf0ef] px-5 py-16">
      <div className="mx-auto max-w-[1460px]">
        <div className="h-64 animate-pulse rounded-[32px] bg-[#dbe5e4]" />
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {[0, 1, 2].map((item) => <div key={item} className="h-48 animate-pulse rounded-3xl bg-white" />)}
        </div>
      </div>
    </div>
  );
}

function Empty({ error }) {
  return (
    <div className="ihi-theme min-h-[70vh] bg-[#eaf0ef] px-5 py-20">
      <div className="mx-auto max-w-2xl rounded-[32px] border border-white bg-white/80 p-10 text-center shadow-[0_30px_80px_rgba(11,45,56,.09)] backdrop-blur">
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-[#0d3443] text-[#e2ad68]">
          <Database className="h-7 w-7" />
        </div>
        <h2 className="mt-6 font-serif text-3xl font-bold text-[#092937]">Coverage is being prepared</h2>
        <p className="mt-4 text-sm leading-7 text-[#66777d]">
          {error || 'The first SEC filing refresh will activate fund portfolios, stock consensus and filing signals.'}
        </p>
        <Link to="/institutional-holdings" className="mt-7 inline-flex items-center gap-2 rounded-full bg-[#0d3443] px-5 py-3 text-xs font-bold text-white">
          Return to overview <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}

function ModuleShell({ children, title, eyebrow, subtitle, back }) {
  return (
    <div className="ihi-theme min-h-screen bg-[#eaf0ef] text-[#092937]">
      <Helmet>
        <title>{title} | AGI Institutional Holdings</title>
        <meta name="description" content={subtitle} />
      </Helmet>
      <header className="relative overflow-hidden bg-[#061f2b] text-white">
        <div className="absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(100,204,210,.08)_1px,transparent_1px),linear-gradient(90deg,rgba(100,204,210,.08)_1px,transparent_1px)] [background-size:42px_42px]" />
        <div className="absolute left-[66%] top-[-180px] h-[560px] w-[560px] rounded-full border border-cyan-300/20 bg-cyan-300/5 shadow-[0_0_160px_rgba(51,189,199,.16)]" />
        <div className="absolute left-[73%] top-[-90px] h-[340px] w-[340px] rounded-full border border-amber-300/20" />
        <div className="relative mx-auto max-w-[1500px] px-5 pb-12 pt-7 sm:px-8 sm:pb-16">
          <div className="mb-10 flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
            <Link to="/institutional-holdings" className="flex items-center gap-3">
              <div className="grid h-9 w-9 place-items-center rounded-xl border border-cyan-200/20 bg-white/5">
                <Radar className="h-5 w-5 text-[#e2ad68]" />
              </div>
              <div>
                <span className="block text-[10px] font-extrabold uppercase tracking-[.2em] text-[#e2ad68]">AGI Intelligence</span>
                <span className="text-xs text-[#a9c0c8]">Institutional Holdings</span>
              </div>
            </Link>
            <div className="flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.12em] text-emerald-200">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300" />
              Filing aware
            </div>
          </div>
          {back ? (
            <Link to={back} className="mb-8 inline-flex items-center gap-2 text-xs font-bold text-[#adc5cc] transition hover:text-white">
              <ArrowLeft className="h-4 w-4" /> Back to overview
            </Link>
          ) : null}
          <p className="text-[10px] font-extrabold uppercase tracking-[.26em] text-[#e2ad68]">{eyebrow}</p>
          <h1 className="mt-4 max-w-5xl font-serif text-4xl font-bold leading-[.98] tracking-[-.04em] sm:text-6xl lg:text-7xl">{title}</h1>
          <p className="mt-6 max-w-3xl text-sm leading-7 text-[#b3c8ce] sm:text-base">{subtitle}</p>
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
  const tone = type === 'exit_pressure' ? '#d47964' : '#3ab1ae';
  return (
    <motion.article
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="group relative overflow-hidden rounded-3xl border border-white bg-white/85 p-5 shadow-[0_16px_40px_rgba(16,54,64,.07)] backdrop-blur"
    >
      <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-10 transition group-hover:scale-125" style={{ background: tone }} />
      <div className="flex items-start justify-between gap-4">
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#edf5f4] text-[#155565]"><Icon className="h-5 w-5" /></div>
        <div className="text-right">
          <span className="font-serif text-3xl font-bold text-[#0b3543]">{signal ? Math.round(score) : '--'}</span>
          <span className="ml-1 text-[10px] text-[#8c999d]">/100</span>
        </div>
      </div>
      <h3 className="mt-5 font-serif text-xl font-bold capitalize">{meta.title}</h3>
      <p className="mt-2 min-h-[42px] text-xs leading-5 text-[#738188]">{signal?.explanation || meta.copy}</p>
      <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-[#e8edeb]">
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: tone }} />
      </div>
      <div className="mt-3 flex items-center justify-between text-[10px] font-bold uppercase tracking-[.1em]">
        <span className="text-[#89969a]">Transparent score</span>
        <span style={{ color: tone }}>{signal?.label || 'Awaiting history'}</span>
      </div>
    </motion.article>
  );
}

function MetricCard({ icon: Icon, label, value, note }) {
  return (
    <div className="rounded-3xl border border-white bg-white/80 p-5 shadow-[0_16px_40px_rgba(12,49,59,.06)] backdrop-blur">
      <div className="flex items-center justify-between">
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#0e3947] text-[#e5b16d]"><Icon className="h-5 w-5" /></div>
        <div className="h-2 w-2 rounded-full bg-[#55c2b6] shadow-[0_0_15px_rgba(85,194,182,.8)]" />
      </div>
      <p className="mt-5 text-[10px] font-extrabold uppercase tracking-[.17em] text-[#849196]">{label}</p>
      <p className="mt-2 font-serif text-2xl font-bold text-[#092937]">{value}</p>
      {note ? <p className="mt-1 text-[11px] text-[#839095]">{note}</p> : null}
    </div>
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
      subtitle="Explore ten distinctive institutional portfolios, understand what changed quarter by quarter, and see where manager conviction overlaps."
    >
      <main className="mx-auto max-w-[1500px] px-5 pb-16 sm:px-8">
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="-mt-7 grid overflow-hidden rounded-[30px] border border-white/70 bg-white/90 shadow-[0_30px_90px_rgba(6,37,48,.14)] backdrop-blur-xl lg:grid-cols-[1.15fr_.85fr]"
        >
          <div className="p-6 sm:p-8 lg:p-10">
            <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.18em] text-[#9e6b3b]">
              <CircleDot className="h-4 w-4" /> Search the smart-money network
            </div>
            <h2 className="mt-4 max-w-2xl font-serif text-3xl font-bold leading-tight sm:text-4xl">Which tracked funds own a stock?</h2>
            <p className="mt-3 max-w-xl text-sm leading-6 text-[#6d7b81]">Enter a US ticker or verified CUSIP to open its manager overlap, quarterly activity and AGI Consensus Score.</p>
            <form onSubmit={openStock} className="mt-6 flex overflow-hidden rounded-2xl border border-[#cedad9] bg-[#f5f9f8] p-2 focus-within:border-[#3ba6aa]">
              <Search className="ml-3 mt-3 h-5 w-5 shrink-0 text-[#6b7d83]" />
              <input
                value={stockQuery}
                onChange={(event) => setStockQuery(event.target.value)}
                placeholder="Try AAPL, AMZN or a CUSIP"
                className="min-w-0 flex-1 bg-transparent px-3 py-3 text-sm font-semibold uppercase outline-none placeholder:normal-case placeholder:font-normal"
              />
              <button className="inline-flex items-center gap-2 rounded-xl bg-[#0c3544] px-5 text-xs font-bold text-white transition hover:bg-[#145162]">
                Open stock <ArrowRight className="h-4 w-4" />
              </button>
            </form>
          </div>
          <div className="relative overflow-hidden bg-[#0d3443] p-7 text-white sm:p-9">
            <div className="absolute -right-20 -top-20 h-56 w-56 rounded-full border border-cyan-300/20" />
            <p className="text-[10px] font-extrabold uppercase tracking-[.2em] text-[#e3ad69]">Coverage pulse</p>
            <div className="mt-6 grid grid-cols-2 gap-4">
              <div><span className="font-serif text-4xl font-bold">{data?.covered_managers || 10}</span><p className="mt-1 text-xs text-[#adc4cb]">Selected managers</p></div>
              <div><span className="font-serif text-4xl font-bold">{data?.consensus_managers || 0}</span><p className="mt-1 text-xs text-[#adc4cb]">Current for consensus</p></div>
              <div><span className="font-serif text-2xl font-bold">{data?.latest_report_date || 'Pending'}</span><p className="mt-1 text-xs text-[#adc4cb]">Latest quarter</p></div>
              <div><span className="font-serif text-4xl font-bold">{data?.consensus?.length || 0}</span><p className="mt-1 text-xs text-[#adc4cb]">Consensus names</p></div>
            </div>
            <div className="mt-7 flex items-center gap-2 border-t border-white/10 pt-5 text-[11px] text-[#a9c1c8]">
              <ShieldCheck className="h-4 w-4 text-[#62c8bc]" /> Point-in-time and amendment aware
            </div>
          </div>
        </motion.section>

        {error ? <div className="mt-8"><Empty error={error} /></div> : (
          <>
            <section id="funds" className="pt-14">
              <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-[10px] font-extrabold uppercase tracking-[.22em] text-[#a56e3d]">Manager constellation</p>
                  <h2 className="mt-3 font-serif text-3xl font-bold sm:text-4xl">Choose a portfolio to explore</h2>
                  <p className="mt-2 text-sm text-[#718087]">Each profile separates the reporting quarter from the date clients could actually know it.</p>
                </div>
                <label className="flex w-full max-w-sm items-center gap-3 rounded-2xl border border-white bg-white/75 px-4 shadow-sm">
                  <Search className="h-4 w-4 text-[#7c8d91]" />
                  <input value={fundQuery} onChange={(event) => setFundQuery(event.target.value)} placeholder="Find a manager" className="w-full bg-transparent py-3.5 text-sm outline-none" />
                </label>
              </div>

              <div className="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-5">
                {funds.map((fund, index) => {
                  const brand = FUND_BRANDS[fund.slug] || {};
                  return (
                    <motion.div key={fund.id || fund.slug} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.04 }}>
                      <Link
                        to={`/institutional-holdings/funds/${fund.slug}`}
                        className="group flex h-full min-h-[310px] flex-col overflow-hidden rounded-[28px] border border-white bg-white/85 p-5 shadow-[0_18px_45px_rgba(12,48,59,.07)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_28px_65px_rgba(12,48,59,.14)]"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <FundLogo fund={fund} />
                          <span className="text-[10px] font-bold text-[#99a3a6]">0{index + 1}</span>
                        </div>
                        <p className="mt-7 text-[9px] font-extrabold uppercase tracking-[.17em]" style={{ color: brand.accent || '#a66e3b' }}>{brand.strap || fund.strategy}</p>
                        <h3 className="mt-2 font-serif text-xl font-bold leading-tight">{fund.display_name}</h3>
                        <p className="mt-2 line-clamp-2 text-xs leading-5 text-[#748187]">{fund.strategy}</p>
                        <div className="mt-auto grid grid-cols-3 gap-2 border-t border-[#e8edeb] pt-5 text-center">
                          <div><strong className="block font-serif text-xl">{fund.position_count || 0}</strong><span className="text-[9px] uppercase text-[#8d999d]">Positions</span></div>
                          <div><strong className="block font-serif text-xl text-[#19806b]">{fund.new_positions || 0}</strong><span className="text-[9px] uppercase text-[#8d999d]">New</span></div>
                          <div><strong className="block font-serif text-xl text-[#b25749]">{fund.exits || 0}</strong><span className="text-[9px] uppercase text-[#8d999d]">Exits</span></div>
                        </div>
                        <div className="mt-5 flex items-center justify-between text-[10px] font-bold uppercase tracking-[.08em] text-[#52666d]">
                          <span>{fund.latest_filing?.report_date || 'Awaiting filing'}</span>
                          <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
                        </div>
                      </Link>
                    </motion.div>
                  );
                })}
              </div>
            </section>

            <section id="consensus" className="mt-16 grid gap-6 xl:grid-cols-[1.55fr_.75fr]">
              <div className="overflow-hidden rounded-[30px] border border-white bg-white/85 shadow-[0_20px_55px_rgba(12,48,59,.08)] backdrop-blur">
                <div className="flex flex-col gap-4 border-b border-[#e3eae7] p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
                  <div>
                    <p className="text-[10px] font-extrabold uppercase tracking-[.2em] text-[#a56e3d]">Collective positioning</p>
                    <h2 className="mt-2 font-serif text-3xl font-bold">Consensus radar</h2>
                    <p className="mt-2 text-xs text-[#78878c]">{data.consensus_ready ? 'Breadth across active tracked portfolios, not a recommendation.' : `Scores activate after ${data.consensus_min_managers || 4} manager portfolios are verified. Holdings remain visible meanwhile.`}</p>
                  </div>
                  <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[#0c3544] text-[#6dd2c5]"><Radar className="h-6 w-6" /></div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[780px] text-left">
                    <thead className="bg-[#f4f8f6] text-[9px] font-extrabold uppercase tracking-[.16em] text-[#7b898e]">
                      <tr><th className="px-8 py-4">Security</th><th className="px-4 py-4">Fund network</th><th className="px-4 py-4">Aggregate weight</th><th className="px-4 py-4">Quarter activity</th><th className="px-8 py-4 text-right">AGI score</th></tr>
                    </thead>
                    <tbody>
                      {(data?.consensus || []).slice(0, 16).map((row, index) => (
                        <tr key={row.key} className="border-t border-[#e8eeeb] transition hover:bg-[#f8fbfa]">
                          <td className="px-8 py-4">
                            <div className="flex items-center gap-3">
                              <div className="grid h-9 w-9 place-items-center rounded-xl bg-[#eaf2f1] text-[10px] font-extrabold text-[#145366]">{row.ticker?.slice(0, 3) || String(index + 1).padStart(2, '0')}</div>
                              <div><Link to={`/institutional-holdings/stocks/${row.ticker || row.cusip}`} className="text-sm font-extrabold hover:text-[#167482]">{row.ticker || row.issuer_name}</Link><span className="block max-w-[220px] truncate text-[11px] text-[#829095]">{row.issuer_name}</span></div>
                            </div>
                          </td>
                          <td className="px-4 py-4">
                            <strong className="text-sm">{row.owners}/{data.consensus_managers}</strong>
                            <div className="mt-2 h-1.5 w-24 overflow-hidden rounded-full bg-[#e1e9e7]"><div className="h-full rounded-full bg-[#38a99f]" style={{ width: `${(row.owners / Math.max(data.consensus_managers, 1)) * 100}%` }} /></div>
                          </td>
                          <td className="px-4 py-4 text-sm font-semibold">{pct(row.aggregate_weight)}</td>
                          <td className="px-4 py-4"><span className="text-xs font-bold text-emerald-700">+{row.new_buyers + row.increasers}</span><span className="mx-2 text-[#b6c0bd]">/</span><span className="text-xs font-bold text-rose-700">-{row.reducers + row.exits}</span></td>
                          <td className="px-8 py-4 text-right"><span className="font-serif text-2xl font-bold">{data.consensus_ready ? Math.round(row.consensus_score) : '--'}</span><span className="ml-1 text-[9px] text-[#89969a]">{data.consensus_ready ? '/100' : 'gated'}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!data?.consensus?.length ? <p className="p-10 text-center text-sm text-[#77868b]">The consensus radar activates after the first SEC refresh.</p> : null}
              </div>

              <aside id="alerts" className="relative overflow-hidden rounded-[30px] bg-[#0c3544] p-7 text-white shadow-[0_24px_65px_rgba(7,37,48,.2)]">
                <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full border border-cyan-200/10" />
                <div className="flex items-center justify-between">
                  <div><p className="text-[10px] font-extrabold uppercase tracking-[.2em] text-[#e2ad68]">Disclosure monitor</p><h2 className="mt-2 font-serif text-2xl font-bold">Filing signals</h2></div>
                  <Zap className="h-6 w-6 text-[#6dd2c5]" />
                </div>
                <div className="mt-7 space-y-5">
                  {(data?.alerts || []).slice(0, 7).map((alert) => (
                    <article key={alert.id} className="relative border-l border-[#456d78] pl-5">
                      <span className="absolute -left-1 top-1 h-2 w-2 rounded-full bg-[#6dd2c5] shadow-[0_0_12px_rgba(109,210,197,.7)]" />
                      <div className="flex items-center gap-2 text-[9px] font-bold uppercase tracking-[.12em] text-[#e2ad68]"><span>{alert.severity}</span><span className="text-[#63818a]">/</span><span>{shortDate(alert.created_at)}</span></div>
                      <h3 className="mt-2 text-sm font-bold leading-5">{alert.title}</h3>
                      <p className="mt-1 text-xs leading-5 text-[#aec5cc]">{alert.body}</p>
                    </article>
                  ))}
                  {!data?.alerts?.length ? <p className="text-sm leading-6 text-[#aec5cc]">New filings, amendments, material initiations and reported exits will appear here.</p> : null}
                </div>
              </aside>
            </section>

            <section id="methodology" className="mt-16">
              <div className="text-center">
                <p className="text-[10px] font-extrabold uppercase tracking-[.22em] text-[#a56e3d]">Explainable by design</p>
                <h2 className="mt-3 font-serif text-3xl font-bold sm:text-4xl">Five signals. Every input visible.</h2>
                <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[#718087]">Scores summarize disclosed positioning. They never claim to know a manager's current portfolio or expected return.</p>
              </div>
              <div className="mt-8 grid gap-4 md:grid-cols-5">
                {Object.keys(SCORE_META).map((key, index) => <ScoreCard key={key} type={key} index={index} />)}
              </div>
            </section>

            <section className="mt-14 flex flex-col gap-5 rounded-[28px] border border-[#d2deda] bg-[#f5f9f7] p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
              <div className="flex gap-4">
                <Info className="mt-1 h-5 w-5 shrink-0 text-[#a56e3d]" />
                <div><h3 className="font-serif text-lg font-bold">A disclosure lens, not a live portfolio</h3><p className="mt-1 max-w-3xl text-xs leading-6 text-[#6f7f84]">Form 13F is delayed and excludes cash, shorts and many non-reportable assets. AGI uses the SEC acceptance timestamp so a quarter is never presented as knowable before publication.</p></div>
              </div>
              <a href="https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/frequently-asked-questions-about-form-13f" target="_blank" rel="noreferrer" className="inline-flex shrink-0 items-center gap-2 text-xs font-bold text-[#15596a]">Read SEC methodology <ArrowRight className="h-4 w-4" /></a>
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
          <div className="flex items-center gap-5"><FundLogo fund={fund} size="lg" /><div><p className="text-[10px] font-extrabold uppercase tracking-[.16em] text-[#a56e3d]">Tracked legal filer</p><h2 className="mt-1 font-serif text-2xl font-bold">{fund.legal_name}</h2><p className="mt-1 text-xs text-[#7d898e]">Quarter {data.latest_filing?.report_date || 'pending'}</p></div></div>
          <div className="flex items-center gap-3 rounded-2xl bg-[#edf7f4] px-4 py-3 text-xs font-bold text-[#1a735f]"><CheckCircle2 className="h-5 w-5" /> Point-in-time verified</div>
        </section>

        <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard icon={Building2} label="Disclosed value" value={money(data.latest_filing?.total_value_usd)} note="Reported market value" />
          <MetricCard icon={Layers3} label="Positions" value={data.latest_filing?.holdings_count || 0} note="Includes separately reported lines" />
          <MetricCard icon={FileClock} label="Filing version" value={data.latest_filing?.amendment_type || 'Pending'} note={data.latest_filing?.form_type || '13F coverage'} />
          <MetricCard icon={Eye} label="Public since" value={shortDate(data.latest_filing?.filed_at)} note="SEC acceptance timestamp" />
        </section>

        <section className="mt-8">
          <div className="mb-5 flex items-center justify-between"><div><p className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#a56e3d]">Manager signal profile</p><h2 className="mt-2 font-serif text-3xl font-bold">What changed and how much it matters</h2></div></div>
          <div className="grid gap-4 md:grid-cols-5">
            {Object.keys(SCORE_META).map((key, index) => <ScoreCard key={key} type={key} signal={signals.get(key)} index={index} />)}
          </div>
        </section>

        <section className="mt-10 grid gap-6 xl:grid-cols-[1.6fr_.65fr]">
          <div className="overflow-hidden rounded-[30px] border border-white bg-white/90 shadow-[0_20px_55px_rgba(12,48,59,.07)]">
            <div className="flex flex-col gap-5 border-b border-[#e3ebe8] p-6 sm:flex-row sm:items-end sm:justify-between sm:p-8">
              <div><p className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#a56e3d]">Position intelligence</p><h2 className="mt-2 font-serif text-3xl font-bold">Disclosed portfolio</h2></div>
              <div className="flex flex-wrap gap-2">
                {['all', 'new', 'increased', 'reduced', 'exited'].map((key) => (
                  <button key={key} onClick={() => setFilter(key)} className={`rounded-full px-3.5 py-2 text-[10px] font-extrabold uppercase tracking-[.08em] transition ${filter === key ? 'bg-[#0c3544] text-white shadow-lg' : 'bg-[#edf2f0] text-[#607178] hover:bg-[#dfe9e6]'}`}>{key}</button>
                ))}
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-left">
                <thead className="bg-[#f5f8f7] text-[9px] font-extrabold uppercase tracking-[.15em] text-[#7c898e]"><tr><th className="px-8 py-4">Security</th><th className="px-4 py-4">Portfolio weight</th><th className="px-4 py-4">Reported value</th><th className="px-4 py-4">Shares</th><th className="px-8 py-4">Quarter signal</th></tr></thead>
                <tbody>
                  {activeRows.map((row) => {
                    const change = changesByCusip.get(row.cusip) || row;
                    const weight = Number(row.portfolio_weight || row.previous_weight || 0);
                    return (
                      <tr key={`${row.cusip}-${row.put_call || ''}`} className="border-t border-[#e8eeeb] hover:bg-[#f8fbfa]">
                        <td className="px-8 py-4">
                          <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-[#eaf2f1] text-[10px] font-extrabold text-[#145366]">{row.ticker?.slice(0, 3) || 'ID'}</div><div><Link to={`/institutional-holdings/stocks/${row.ticker || row.cusip}`} className="text-sm font-extrabold hover:text-[#167482]">{row.ticker || row.issuer_name}</Link><span className="block max-w-[250px] truncate text-[11px] text-[#829095]">{row.issuer_name}{row.put_call ? ` / ${row.put_call}` : ''}</span></div></div>
                        </td>
                        <td className="px-4 py-4"><strong className="text-sm">{pct(weight)}</strong><div className="mt-2 h-1.5 w-28 overflow-hidden rounded-full bg-[#e1e9e7]"><div className="h-full rounded-full bg-gradient-to-r from-[#2b9b99] to-[#d09a5f]" style={{ width: `${Math.min(weight * 5, 100)}%` }} /></div></td>
                        <td className="px-4 py-4 text-sm font-semibold">{money(row.value_usd)}</td>
                        <td className="px-4 py-4 text-sm">{Number(row.shares || row.previous_shares || 0).toLocaleString('en-US')}</td>
                        <td className="px-8 py-4"><SignalPill type={change.change_type || 'held'} /></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {!activeRows.length ? <p className="p-10 text-center text-sm text-[#77868b]">No positions match this activity view.</p> : null}
          </div>

          <aside className="rounded-[30px] bg-[#0c3544] p-6 text-white shadow-[0_24px_65px_rgba(7,37,48,.18)]">
            <div className="flex items-center justify-between"><div><p className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#e2ad68]">Time machine</p><h2 className="mt-2 font-serif text-2xl font-bold">Quarter archive</h2></div><CalendarClock className="h-6 w-6 text-[#6dd2c5]" /></div>
            <div className="mt-6 space-y-3">
              {(data.filings || []).map((filing, index) => (
                <a key={filing.id} href={filing.source_url} target="_blank" rel="noreferrer" className="group block rounded-2xl border border-white/10 bg-white/5 p-4 transition hover:border-[#6dd2c5]/50 hover:bg-white/10">
                  <div className="flex items-center justify-between gap-3"><strong className="font-serif text-lg">{filing.report_date}</strong><span className="rounded-full bg-white/10 px-2 py-1 text-[9px] font-bold uppercase text-[#d6e2e5]">{filing.form_type}</span></div>
                  <p className="mt-2 text-xs text-[#b5cbd1]">{filing.holdings_count} lines / {money(filing.total_value_usd)}</p>
                  <div className="mt-3 flex items-center justify-between border-t border-white/10 pt-3 text-[9px] uppercase tracking-[.08em] text-[#7899a2]"><span>Accepted {shortDate(filing.filed_at)}</span><ChevronRight className="h-3 w-3 transition group-hover:translate-x-1" /></div>
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
  return (
    <ModuleShell
      back="/institutional-holdings"
      eyebrow={`Consensus security / CUSIP ${data.cusip}`}
      title={data.ticker || data.issuer_name}
      subtitle={`${data.owner_count} of ${data.manager_count} current manager portfolios disclose this security. Stale fund histories are excluded from consensus scoring.`}
    >
      <main className="mx-auto max-w-[1380px] px-5 pb-16 sm:px-8">
        <section className="-mt-8 grid overflow-hidden rounded-[32px] border border-white bg-white/90 shadow-[0_30px_80px_rgba(6,37,48,.13)] backdrop-blur lg:grid-cols-[360px_1fr]">
          <div className="relative grid place-items-center overflow-hidden bg-[#0c3544] p-10 text-white">
            <div className="absolute inset-0 opacity-30 [background-image:radial-gradient(circle_at_center,rgba(101,210,199,.25),transparent_60%)]" />
            <div className="relative grid h-52 w-52 place-items-center rounded-full" style={{ background: `conic-gradient(#63cec1 ${score}%, rgba(255,255,255,.1) 0)` }}>
              <div className="grid h-[174px] w-[174px] place-items-center rounded-full bg-[#0c3544] text-center">
                <div><span className="font-serif text-6xl font-bold">{scoreAvailable ? score : '--'}</span><span className="block text-[10px] font-extrabold uppercase tracking-[.18em] text-[#9db8bf]">{scoreAvailable ? 'Consensus score' : 'Coverage building'}</span></div>
              </div>
            </div>
            <p className="relative mt-5 text-center text-xs leading-5 text-[#b6ccd2]">{scoreAvailable ? 'Breadth plus average disclosed portfolio importance' : `Available after ${data.consensus_min_managers || 4} manager portfolios are verified`}</p>
          </div>
          <div className="grid gap-px bg-[#e1e9e6] sm:grid-cols-2">
            <div className="bg-white p-7"><Users className="h-5 w-5 text-[#a56e3d]" /><p className="mt-5 text-[10px] font-extrabold uppercase tracking-[.14em] text-[#879499]">Manager ownership</p><p className="mt-2 font-serif text-4xl font-bold">{data.owner_count}<span className="text-xl text-[#8c999d]">/{data.manager_count}</span></p></div>
            <div className="bg-white p-7"><BarChart3 className="h-5 w-5 text-[#a56e3d]" /><p className="mt-5 text-[10px] font-extrabold uppercase tracking-[.14em] text-[#879499]">Aggregate weight</p><p className="mt-2 font-serif text-4xl font-bold">{pct(data.aggregate_weight)}</p></div>
            <div className="bg-white p-7"><Building2 className="h-5 w-5 text-[#a56e3d]" /><p className="mt-5 text-[10px] font-extrabold uppercase tracking-[.14em] text-[#879499]">Reported value</p><p className="mt-2 font-serif text-4xl font-bold">{money(data.aggregate_value_usd)}</p></div>
            <div className="bg-white p-7"><Activity className="h-5 w-5 text-[#a56e3d]" /><p className="mt-5 text-[10px] font-extrabold uppercase tracking-[.14em] text-[#879499]">Latest activity</p><p className="mt-2 font-serif text-2xl font-bold">{(data.changes || []).filter((row) => ['new', 'increased'].includes(row.change_type)).length} adding</p></div>
          </div>
        </section>

        <section className="mt-10">
          <div><p className="text-[10px] font-extrabold uppercase tracking-[.2em] text-[#a56e3d]">Ownership network</p><h2 className="mt-2 font-serif text-3xl font-bold sm:text-4xl">Who owns it and what changed</h2><p className="mt-2 text-sm text-[#718087]">Position weights are comparable within each manager's disclosed 13F portfolio.</p></div>
          <div className="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {(data.owners || []).map((row, index) => {
              const manager = row.manager || {};
              const change = (data.changes || []).find((item) => item.manager_id === row.manager_id);
              return (
                <motion.div key={row.manager_id} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}>
                  <Link to={`/institutional-holdings/funds/${manager.slug}`} className="group block rounded-[28px] border border-white bg-white/85 p-6 shadow-[0_18px_45px_rgba(12,48,59,.07)] transition hover:-translate-y-1 hover:shadow-[0_26px_60px_rgba(12,48,59,.13)]">
                    <div className="flex items-start justify-between gap-4"><div className="flex items-center gap-3"><FundLogo fund={manager} size="sm" /><div><h3 className="font-serif text-lg font-bold">{manager.display_name}</h3><p className="text-[10px] text-[#819095]">Quarter {row.report_date}</p></div></div><SignalPill type={change?.change_type || 'held'} /></div>
                    <div className="mt-7 flex items-end justify-between"><div><p className="text-[9px] font-bold uppercase tracking-[.13em] text-[#89969a]">Portfolio weight</p><p className="mt-1 font-serif text-3xl font-bold">{pct(row.portfolio_weight)}</p></div><p className="text-sm font-semibold">{money(row.value_usd)}</p></div>
                    <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-[#e3ebe8]"><div className="h-full rounded-full bg-gradient-to-r from-[#2aa19d] to-[#d09a5f]" style={{ width: `${Math.min(Number(row.portfolio_weight || 0) * 7, 100)}%` }} /></div>
                    <div className="mt-5 flex items-center justify-between border-t border-[#e7eeeb] pt-4 text-[10px] font-bold uppercase tracking-[.08em] text-[#5a6e74]"><span>Open manager portfolio</span><ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></div>
                  </Link>
                </motion.div>
              );
            })}
          </div>
        </section>

        <section className="mt-12 grid gap-5 lg:grid-cols-2">
          <div className="rounded-[28px] bg-[#0c3544] p-7 text-white">
            <ShieldCheck className="h-6 w-6 text-[#6dd2c5]" />
            <h2 className="mt-5 font-serif text-2xl font-bold">What the score tells you</h2>
            <p className="mt-3 text-sm leading-7 text-[#b5cbd1]">A higher score means ownership is broader across the selected network and the position matters more inside those disclosed portfolios.</p>
          </div>
          <div className="rounded-[28px] border border-[#d5dfdc] bg-[#f4f8f6] p-7">
            <Info className="h-6 w-6 text-[#a56e3d]" />
            <h2 className="mt-5 font-serif text-2xl font-bold">What it cannot tell you</h2>
            <p className="mt-3 text-sm leading-7 text-[#6d7d82]">It cannot confirm a current holding, purchase price, short position, hedge, expected return or agreement among managers.</p>
          </div>
        </section>
      </main>
    </ModuleShell>
  );
}

export default function InstitutionalHoldingsPage() {
  const { fundSlug, stockKey } = useParams();
  if (fundSlug) return <FundPage slug={fundSlug} />;
  if (stockKey) return <StockPage stockKey={stockKey} />;
  return <OverviewPage />;
}
