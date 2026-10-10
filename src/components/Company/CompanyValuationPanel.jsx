import { useEffect, useMemo, useState } from 'react';
import { BarChart3, Building2, CalendarClock, Scale, ShieldCheck } from 'lucide-react';
import { getValuationConsensusCompany, getVtCompany } from '@/lib/intelligenceApi';

const LABELS = {
  pe: 'P/E',
  pb: 'P/B',
  ev_ebitda: 'EV/EBITDA',
  ev_sales: 'EV/Sales',
  ps: 'Price/Sales',
  roe: 'ROE',
  dividend_yield: 'Dividend yield',
  forward_pe: 'Forward P/E',
};

function number(value) {
  if (value === '' || value == null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function decimal(value, suffix = '') {
  const parsed = number(value);
  return parsed == null ? '-' : `${parsed.toLocaleString('en-IN', { maximumFractionDigits: 2 })}${suffix}`;
}

function money(value) {
  const parsed = number(value);
  return parsed == null
    ? '-'
    : new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(parsed);
}

function positionClass(value = '') {
  const text = String(value).toLowerCase();
  if (text.includes('discount') || text.includes('below')) return 'border-[#9fc9ad] bg-[#eaf5ee] text-[#17633a]';
  if (text.includes('premium') || text.includes('above')) return 'border-[#e2aea4] bg-[#fff0ec] text-[#a13a2b]';
  return 'border-[#d7c39c] bg-[#fff7e7] text-[#805d1f]';
}

function Position({ children }) {
  return <span className={`inline-flex rounded-full border px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${positionClass(children)}`}>{children || 'In line'}</span>;
}

function SnapshotCard({ icon: Icon, label, value, note }) {
  return (
    <article className="rounded-xl border border-[#e0ddd5] bg-white p-4">
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.13em] text-[#778089]">
        <Icon className="h-3.5 w-3.5 text-[#a66e37]" aria-hidden /> {label}
      </div>
      <p className="mt-3 font-serif text-2xl font-bold text-[#102433]">{value}</p>
      {note ? <p className="mt-1 text-[11px] leading-4 text-[#778089]">{note}</p> : null}
    </article>
  );
}

export default function CompanyValuationPanel({ symbol }) {
  const [state, setState] = useState({ loading: true, terminal: null, consensus: null });

  useEffect(() => {
    let active = true;
    setState({ loading: true, terminal: null, consensus: null });
    Promise.allSettled([
      getVtCompany(symbol, { window: '5Y', peer_limit: 8 }),
      getValuationConsensusCompany(symbol),
    ]).then(([terminalResult, consensusResult]) => {
      if (!active) return;
      setState({
        loading: false,
        terminal: terminalResult.status === 'fulfilled' && terminalResult.value?.ok ? terminalResult.value : null,
        consensus: consensusResult.status === 'fulfilled' && consensusResult.value?.ok ? consensusResult.value : null,
      });
    });
    return () => {
      active = false;
    };
  }, [symbol]);

  const consensus = state.consensus?.valuation || {};
  const terminal = state.terminal;
  const rows = useMemo(
    () => (terminal?.table || []).filter((row) => row.meaningful !== false && row.available !== false && number(row.company) != null),
    [terminal]
  );
  const peers = terminal?.peers?.rows || [];
  const health = number(terminal?.health_score?.score ?? terminal?.health_score);
  const primaryMetric = terminal?.sector_context?.primary_metric;
  const primaryRow = rows.find((row) => row.metric === primaryMetric) || rows[0];
  const updated = state.consensus?.market_consensus?.row?.updated_at || terminal?.overview?.updated;

  if (state.loading) {
    return <section className="mt-6 h-64 animate-pulse rounded-2xl border border-[#dedbd3] bg-white" aria-label="Loading valuation intelligence" />;
  }

  if (!terminal && !state.consensus) {
    return (
      <section className="mt-6 rounded-2xl border border-dashed border-[#c9c5bb] bg-white/65 p-6">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a6338]">Valuation intelligence</p>
        <h2 className="mt-2 font-serif text-2xl font-bold text-[#102433]">Coverage is still being built</h2>
        <p className="mt-2 text-sm leading-6 text-[#687178]">No verified valuation pack is currently available for this symbol. AGI withholds valuation figures instead of estimating missing data.</p>
      </section>
    );
  }

  return (
    <section className="mt-6 overflow-hidden rounded-2xl border border-[#d8d5cc] bg-[#f1ede4]">
      <div className="flex flex-col gap-4 border-b border-[#d8d5cc] bg-[#102f3c] px-5 py-5 text-white sm:flex-row sm:items-center sm:justify-between sm:px-7">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.17em] text-[#d8b277]"><Scale className="h-4 w-4" /> Valuation intelligence</div>
          <h2 className="mt-2 font-serif text-2xl font-bold">What is {String(symbol || '').toUpperCase()} priced for?</h2>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-[#bdd0d6]"><CalendarClock className="h-4 w-4" />{updated ? `Updated ${new Date(updated).toLocaleDateString('en-IN')}` : 'Latest verified warehouse record'}</div>
      </div>

      <div className="p-5 sm:p-7">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SnapshotCard icon={BarChart3} label="Current market price" value={money(consensus.current_price)} note={state.consensus ? 'Capital IQ market-consensus snapshot' : 'Consensus coverage unavailable'} />
          <SnapshotCard icon={Scale} label="Consensus target" value={money(consensus.consensus_target)} note="External analyst consensus, not AGI fair value" />
          <SnapshotCard icon={Building2} label="Implied move" value={decimal(consensus.upside, '%')} note={consensus.coverage_count ? `${consensus.coverage_count} contributing analysts` : 'Coverage count unavailable'} />
          <SnapshotCard icon={ShieldCheck} label="Valuation confidence" value={health == null ? '-' : `${Math.round(health)}%`} note={terminal?.coverage ? `${terminal.coverage.available ?? '-'} of ${terminal.coverage.applicable ?? '-'} applicable metrics` : 'Warehouse evidence score'} />
        </div>

        {primaryRow ? (
          <div className="mt-5 flex flex-col gap-4 rounded-xl border border-[#d8d5cc] bg-white p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#7b858c]">Primary valuation lens</p>
              <p className="mt-2 font-serif text-2xl font-bold">{LABELS[primaryRow.metric] || primaryRow.metric}: {decimal(primaryRow.company)}</p>
              <p className="mt-1 text-xs text-[#6d767d]">Sector median {decimal(primaryRow.industry)} - 5Y historical median {decimal(primaryRow.historical)}</p>
            </div>
            <Position>{primaryRow.position}</Position>
          </div>
        ) : null}

        {rows.length ? (
          <div className="mt-5 overflow-x-auto rounded-xl border border-[#d8d5cc] bg-white">
            <table className="w-full min-w-[680px] text-left text-xs">
              <thead className="bg-[#e9e5dc] text-[10px] uppercase tracking-[0.12em] text-[#69737a]">
                <tr><th className="px-4 py-3">Metric</th><th className="px-4 py-3">Company</th><th className="px-4 py-3">Sector median</th><th className="px-4 py-3">Historical median</th><th className="px-4 py-3">Position</th><th className="px-4 py-3">History</th></tr>
              </thead>
              <tbody className="divide-y divide-[#ece9e2]">
                {rows.map((row) => (
                  <tr key={row.metric}>
                    <td className="px-4 py-3 font-bold text-[#102433]">{LABELS[row.metric] || row.metric}</td>
                    <td className="px-4 py-3 font-semibold">{decimal(row.company, row.metric === 'roe' || row.metric === 'dividend_yield' ? '%' : '')}</td>
                    <td className="px-4 py-3 text-[#657078]">{decimal(row.industry)}</td>
                    <td className="px-4 py-3 text-[#657078]">{decimal(row.historical)}</td>
                    <td className="px-4 py-3"><Position>{row.position}</Position></td>
                    <td className="px-4 py-3 text-[#657078]">{row.coverage?.historical_percentile != null ? `${decimal(row.coverage.historical_percentile)} percentile` : row.coverage?.historical_observation_label || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {peers.length ? (
          <div className="mt-5 rounded-xl border border-[#d8d5cc] bg-white p-5">
            <div className="flex items-center justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#8a6338]">Comparable companies</p><h3 className="mt-1 font-serif text-xl font-bold">Peer valuation context</h3></div><span className="text-xs text-[#747d84]">{terminal?.sector_context?.sector || 'Sector peers'}</span></div>
            <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {peers.filter((peer) => !peer.is_self).slice(0, 4).map((peer) => (
                <article key={peer.symbol} className="rounded-lg border border-[#ece9e2] p-3">
                  <p className="text-xs font-bold text-[#102433]">{peer.company_name || peer.symbol}</p>
                  <p className="mt-2 text-[11px] text-[#6d767d]">P/E {decimal(peer.pe)} - P/B {decimal(peer.pb)}</p>
                  <p className="mt-1 text-[10px] text-[#8a9298]">{peer.selection_reason || 'Sector comparable'}</p>
                </article>
              ))}
            </div>
          </div>
        ) : null}

        <p className="mt-5 border-t border-[#d8d5cc] pt-4 text-[11px] leading-5 text-[#687178]">
          Consensus targets represent external market expectations and are not AGI fair values or recommendations. Multiples are shown only where the valuation policy marks them meaningful and verified warehouse data is available.
        </p>
      </div>
    </section>
  );
}
