import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  Database,
  FileSearch,
  Fingerprint,
  Layers3,
  Loader2,
  Network,
  Search,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Users,
} from 'lucide-react';
import { getInstitutionalDecisionIntelligence } from '@/lib/institutionalHoldingsApi';

const money = (value) => {
  const amount = Number(value || 0);
  if (amount >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`;
  if (amount >= 1e6) return `$${(amount / 1e6).toFixed(1)}M`;
  return `$${Math.round(amount).toLocaleString('en-US')}`;
};

const scoreTone = (score) => score >= 70 ? '#2f9f91' : score >= 45 ? '#d29b55' : '#bf6657';

function ScoreBar({ score }) {
  const value = Number(score || 0);
  return <div className="flex items-center gap-3"><div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#dce6e3]"><div className="h-full rounded-full" style={{ width: `${Math.min(100, value)}%`, background: scoreTone(value) }} /></div><strong className="w-8 text-right text-xs">{Math.round(value)}</strong></div>;
}

function RankingCard({ title, subtitle, icon: Icon, rows, scoreKey, onSelect }) {
  return <article className="overflow-hidden rounded-[26px] border border-white bg-white/85 shadow-[0_18px_55px_rgba(10,45,55,.07)]">
    <header className="flex items-center gap-3 border-b border-[#e4ece9] p-5"><div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#eaf3f1] text-[#155767]"><Icon className="h-5 w-5" /></div><div><h3 className="font-serif text-xl font-bold">{title}</h3><p className="mt-0.5 text-[10px] uppercase tracking-[.12em] text-[#849196]">{subtitle}</p></div></header>
    <div className="divide-y divide-[#e7edeb]">{(rows || []).slice(0, 5).map((row, index) => <button type="button" key={row.key} onClick={() => onSelect(row)} className="grid w-full grid-cols-[26px_1fr_92px] items-center gap-3 px-5 py-4 text-left transition hover:bg-[#f2f7f5]"><span className="font-serif text-sm font-bold text-[#ad7744]">{String(index + 1).padStart(2, '0')}</span><span className="min-w-0"><strong className="block truncate text-sm">{row.ticker || row.issuer_name}</strong><span className="mt-1 block text-[10px] text-[#7c8b90]">{row.owner_count} owners · {money(row.aggregate_value_usd)}</span></span><ScoreBar score={row.scores?.[scoreKey]?.score} /></button>)}</div>
  </article>;
}

function EvidencePanel({ row, onClose }) {
  if (!row) return null;
  const scoreRows = Object.entries(row.scores || {});
  return <div className="fixed inset-0 z-[80] flex justify-end bg-[#061f2b]/55 backdrop-blur-sm" onClick={onClose} role="presentation"><aside className="h-full w-full max-w-xl overflow-y-auto bg-[#f4f7f5] p-6 shadow-2xl sm:p-8" onClick={(event) => event.stopPropagation()}><button type="button" onClick={onClose} className="text-xs font-bold text-[#557078]">Close evidence</button><p className="mt-8 text-[10px] font-extrabold uppercase tracking-[.2em] text-[#a56e3d]">Transparent institutional signal</p><h3 className="mt-3 font-serif text-4xl font-bold">{row.ticker || row.issuer_name}</h3><p className="mt-2 text-sm text-[#6b7c82]">{row.issuer_name} · CUSIP {row.cusip}</p><div className="mt-7 grid grid-cols-2 gap-3"><div className="rounded-2xl bg-white p-4"><span className="text-[10px] uppercase text-[#849196]">Owners</span><strong className="mt-1 block font-serif text-2xl">{row.owner_count}</strong></div><div className="rounded-2xl bg-white p-4"><span className="text-[10px] uppercase text-[#849196]">Disclosed value</span><strong className="mt-1 block font-serif text-2xl">{money(row.aggregate_value_usd)}</strong></div></div><div className="mt-7 space-y-3">{scoreRows.map(([key, value]) => <div key={key} className="rounded-2xl border border-white bg-white/80 p-4"><div className="flex items-center justify-between"><strong className="capitalize">{key.replace('_', ' ')}</strong><span className="font-serif text-xl font-bold">{Math.round(value.score)}/100</span></div><div className="mt-3"><ScoreBar score={value.score} /></div><div className="mt-3 flex flex-wrap gap-2">{Object.entries(value.components || {}).map(([label, component]) => <span key={label} className="rounded-full bg-[#edf3f1] px-2.5 py-1 text-[9px] font-bold text-[#557078]">{label.replaceAll('_', ' ')}: {component}</span>)}</div></div>)}</div><h4 className="mt-8 font-serif text-2xl font-bold">SEC evidence</h4><div className="mt-4 space-y-3">{(row.evidence || []).map((item) => <a key={`${item.accession_number}-${item.manager}`} href={item.source_url} target="_blank" rel="noreferrer" className="flex items-center justify-between gap-4 rounded-2xl bg-white p-4 text-sm transition hover:bg-[#eaf3f1]"><span><strong className="block">{item.manager}</strong><span className="mt-1 block text-[10px] text-[#7f8f94]">Holdings {item.report_date} · filed {item.filed_at ? new Date(item.filed_at).toLocaleDateString() : 'unknown'}{item.is_amendment ? ' · amendment' : ''}</span></span><ArrowUpRight className="h-4 w-4 shrink-0" /></a>)}</div></aside></div>;
}

export default function InstitutionalIntelligenceWorkbench() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('signals');
  const [query, setQuery] = useState('');
  const [signal, setSignal] = useState('consensus');
  const [selected, setSelected] = useState(null);

  useEffect(() => { getInstitutionalDecisionIntelligence().then(setData).catch((err) => setError(err.message)); }, []);
  const screened = useMemo(() => (data?.screener || [])
    .filter((row) => `${row.ticker || ''} ${row.issuer_name || ''} ${row.cusip || ''}`.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => Number(b.scores?.[signal]?.score || 0) - Number(a.scores?.[signal]?.score || 0))
    .slice(0, 15), [data, query, signal]);

  if (error) return <section className="mt-14 rounded-3xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700"><AlertTriangle className="mr-2 inline h-5 w-5" />Decision Intelligence could not load: {error}</section>;
  if (!data) return <section className="mt-14 flex min-h-48 items-center justify-center rounded-3xl bg-white/70"><Loader2 className="h-7 w-7 animate-spin text-[#2b7f80]" /></section>;

  const health = data.data_health || {};
  const tabs = [{ id: 'signals', label: 'Signal map', icon: BarChart3 }, { id: 'managers', label: 'Manager quality', icon: Users }, { id: 'overlap', label: 'Overlap', icon: Network }, { id: 'limits', label: 'Evidence limits', icon: ShieldCheck }];
  return <section id="decision-intelligence" className="pt-14">
    <div className="relative overflow-hidden rounded-[34px] bg-[#071f2a] text-white shadow-[0_35px_95px_rgba(4,29,39,.18)]"><div className="absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(93,205,197,.08)_1px,transparent_1px),linear-gradient(90deg,rgba(93,205,197,.08)_1px,transparent_1px)] [background-size:38px_38px]" /><div className="relative p-6 sm:p-9"><div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between"><div><p className="text-[10px] font-extrabold uppercase tracking-[.22em] text-[#e0a963]">AGI Decision Intelligence</p><h2 className="mt-3 max-w-4xl font-serif text-3xl font-bold sm:text-5xl">From disclosed positions to explainable signals.</h2><p className="mt-4 max-w-3xl text-sm leading-7 text-[#a9c1c8]">{data.market_read?.headline}</p></div><div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{[['Health', `${Math.round(health.score || 0)}/100`], ['Comparable', health.comparable_managers], ['Mapped value', `${health.ticker_mapping_by_value || 0}%`], ['As of', data.as_of_quarter || '--']].map(([label, value]) => <div key={label} className="min-w-28 rounded-2xl border border-white/10 bg-white/5 p-3"><span className="text-[9px] uppercase tracking-wider text-[#819da6]">{label}</span><strong className="mt-1 block font-serif text-lg">{value}</strong></div>)}</div></div><div className="mt-8 flex gap-2 overflow-x-auto border-t border-white/10 pt-5">{tabs.map(({ id, label, icon: Icon }) => <button type="button" key={id} onClick={() => setTab(id)} className={`inline-flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-xs font-bold transition ${tab === id ? 'bg-[#66cfc1] text-[#06222d]' : 'bg-white/5 text-[#b3c7cd] hover:bg-white/10'}`}><Icon className="h-4 w-4" />{label}</button>)}</div></div></div>

    {tab === 'signals' ? <div className="mt-6 space-y-6"><div className="grid gap-5 lg:grid-cols-3"><RankingCard title="Accumulation" subtitle="Positive breadth" icon={TrendingUp} rows={data.rankings?.accumulation} scoreKey="accumulation" onSelect={setSelected} /><RankingCard title="Consensus" subtitle="Ownership and importance" icon={Fingerprint} rows={data.rankings?.consensus} scoreKey="consensus" onSelect={setSelected} /><RankingCard title="Exit pressure" subtitle="Reductions and exits" icon={TrendingDown} rows={data.rankings?.exit_pressure} scoreKey="exit_pressure" onSelect={setSelected} /></div><div className="overflow-hidden rounded-[28px] border border-white bg-white/85 shadow-[0_18px_55px_rgba(10,45,55,.07)]"><div className="flex flex-col gap-4 border-b border-[#e4ece9] p-5 md:flex-row md:items-end md:justify-between"><div><h3 className="font-serif text-2xl font-bold">Institutional signal screener</h3><p className="mt-1 text-xs text-[#7c8b90]">Search the comparable-quarter universe and rank it with a transparent signal.</p></div><div className="flex flex-col gap-2 sm:flex-row"><label className="flex items-center gap-2 rounded-xl border border-[#dce6e3] bg-white px-3"><Search className="h-4 w-4 text-[#819196]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ticker, issuer or CUSIP" className="w-52 py-2.5 text-sm outline-none" /></label><select value={signal} onChange={(event) => setSignal(event.target.value)} className="rounded-xl border border-[#dce6e3] bg-white px-3 py-2.5 text-sm"><option value="consensus">Consensus</option><option value="accumulation">Accumulation</option><option value="new_idea">New ideas</option><option value="crowding">Crowding</option><option value="exit_pressure">Exit pressure</option></select></div></div><div className="overflow-x-auto"><table className="w-full min-w-[820px] text-left"><thead className="bg-[#edf3f1] text-[9px] uppercase tracking-[.13em] text-[#718388]"><tr><th className="px-5 py-3">Security</th><th className="px-4 py-3">Owners</th><th className="px-4 py-3">New / Up</th><th className="px-4 py-3">Down / Exit</th><th className="px-4 py-3">Aggregate weight</th><th className="px-4 py-3">Score</th><th className="px-4 py-3">Evidence</th></tr></thead><tbody className="divide-y divide-[#e6ecea]">{screened.map((row) => <tr key={row.key} className="text-sm"><td className="px-5 py-4"><Link to={`/institutional-holdings/stocks/${row.ticker || row.cusip}`} className="font-bold text-[#125b67] hover:underline">{row.ticker || row.issuer_name}</Link><span className="ml-2 text-[10px] text-[#849196]">{row.issuer_name}</span></td><td className="px-4 py-4">{row.owner_count}</td><td className="px-4 py-4 text-emerald-700">{row.activity.new} / {row.activity.increased}</td><td className="px-4 py-4 text-rose-700">{row.activity.reduced} / {row.activity.exited}</td><td className="px-4 py-4">{row.aggregate_weight}%</td><td className="min-w-36 px-4 py-4"><ScoreBar score={row.scores?.[signal]?.score} /></td><td className="px-4 py-4"><button type="button" onClick={() => setSelected(row)} className="inline-flex items-center gap-1 text-xs font-bold text-[#a56e3d]"><FileSearch className="h-4 w-4" /> Open</button></td></tr>)}</tbody></table></div></div></div> : null}

    {tab === 'managers' ? <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{(data.managers || []).map((manager) => <Link key={manager.id} to={`/institutional-holdings/funds/${manager.slug}`} className="rounded-[24px] border border-white bg-white/85 p-5 shadow-[0_16px_45px_rgba(10,45,55,.06)] transition hover:-translate-y-1"><div className="flex items-start justify-between"><div><p className="text-[9px] font-bold uppercase tracking-[.14em] text-[#a56e3d]">{manager.strategy}</p><h3 className="mt-2 font-serif text-xl font-bold">{manager.display_name}</h3></div><span className="rounded-full bg-[#e9f3f0] px-2.5 py-1 text-xs font-bold text-[#25776f]">{Math.round(manager.data_quality_score)}/100</span></div><div className="mt-5 grid grid-cols-3 gap-2 text-center"><div className="rounded-xl bg-[#f0f4f2] p-2"><strong className="block">{manager.history_quarters}</strong><span className="text-[9px] text-[#809095]">Quarters</span></div><div className="rounded-xl bg-[#f0f4f2] p-2"><strong className="block">{manager.mapping_coverage}%</strong><span className="text-[9px] text-[#809095]">Mapped</span></div><div className="rounded-xl bg-[#f0f4f2] p-2"><strong className="block">{manager.top_ten_concentration}%</strong><span className="text-[9px] text-[#809095]">Top 10</span></div></div><p className="mt-4 text-[10px] leading-5 text-[#7a898e]">Filing lag {manager.filing_lag_days ?? '--'} days · turnover proxy {manager.turnover_proxy}%</p></Link>)}</div> : null}

    {tab === 'overlap' ? <div className="mt-6 grid gap-4 lg:grid-cols-2">{(data.overlap || []).map((pair) => <div key={`${pair.left.slug}-${pair.right.slug}`} className="rounded-[24px] border border-white bg-white/85 p-5 shadow-[0_16px_45px_rgba(10,45,55,.06)]"><div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#eaf3f1] text-[#155767]"><Layers3 className="h-5 w-5" /></div><div className="min-w-0"><h3 className="truncate font-serif text-lg font-bold">{pair.left.name} × {pair.right.name}</h3><p className="text-[10px] text-[#7c8b90]">{pair.shared_count} shared securities · {pair.overlap_score}% Jaccard overlap</p></div></div><div className="mt-4 flex flex-wrap gap-2">{pair.shared_securities.map((key) => <Link key={key} to={`/institutional-holdings/stocks/${key}`} className="rounded-full bg-[#edf3f1] px-3 py-1 text-[10px] font-bold text-[#35636b]">{key}</Link>)}</div></div>)}</div> : null}

    {tab === 'limits' ? <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_.8fr]"><div className="rounded-[26px] border border-white bg-white/85 p-6"><div className="flex items-center gap-3"><ShieldCheck className="h-6 w-6 text-[#2d8d82]" /><h3 className="font-serif text-2xl font-bold">What is verified</h3></div><div className="mt-5 space-y-3">{[data.methodology?.basis, data.methodology?.point_in_time_rule, data.methodology?.instrument_rule, data.methodology?.universe_rule].map((item) => <div key={item} className="flex gap-3 rounded-2xl bg-[#edf4f2] p-4 text-sm leading-6 text-[#48636b]"><CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-[#2e998d]" />{item}</div>)}</div><div className="mt-5 flex gap-3 rounded-2xl bg-amber-50 p-4 text-sm leading-6 text-amber-900"><AlertTriangle className="mt-1 h-4 w-4 shrink-0" />{data.methodology?.warning}</div></div><div className="rounded-[26px] border border-white bg-white/85 p-6"><div className="flex items-center gap-3"><Database className="h-6 w-6 text-[#a56e3d]" /><h3 className="font-serif text-2xl font-bold">Capability gates</h3></div><div className="mt-5 space-y-3">{Object.entries(data.capability_status || {}).map(([key, item]) => <div key={key} className="border-b border-[#e4ece9] pb-3"><div className="flex items-center justify-between"><strong className="text-sm capitalize">{key.replace('_', ' ')}</strong><span className="rounded-full bg-[#edf3f1] px-2 py-1 text-[9px] font-bold uppercase text-[#677b81]">{item.status.replace('_', ' ')}</span></div><p className="mt-2 text-xs leading-5 text-[#7c8b90]">{item.reason}</p></div>)}</div></div></div> : null}
    <EvidencePanel row={selected} onClose={() => setSelected(null)} />
  </section>;
}
