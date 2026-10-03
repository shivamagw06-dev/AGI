import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { API_ORIGIN } from '@/config';

const labels = {
  company_master: 'Companies', daily_market_history: 'Daily market prices', financials_annual: 'Annual financial statements',
  financials_quarterly: 'Quarterly financial statements', valuation_ratios: 'Valuation ratios', historical_valuation: 'Historical valuation observations',
  institutional_flow: 'Institutional flows', ownership: 'Ownership records', corporate_actions: 'Corporate actions',
};

function number(value) { return new Intl.NumberFormat('en-IN').format(Number(value || 0)); }
function when(value) { return value ? new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : 'Not recorded yet'; }

async function get(path) {
  const response = await fetch(`${API_ORIGIN}/api/${path}`, { signal: AbortSignal.timeout(35_000) });
  if (!response.ok) throw new Error(`Could not load ${path}`);
  return response.json();
}

export default function DataHealthSheet() {
  const [state, setState] = useState({ loading: true, error: '', coverage: null, gather: null, statements: null });
  const load = async () => {
    setState((previous) => ({ ...previous, loading: true, error: '' }));
    try {
      const [coverage, gather, statements] = await Promise.all([
        get('intelligence/warehouse/coverage'),
        get('intelligence/continuous-gather-learn/health'),
        get('market/upstox/statements/status'),
      ]);
      setState({ loading: false, error: '', coverage, gather, statements });
    } catch (error) {
      setState((previous) => ({ ...previous, loading: false, error: error.message || 'Data health is temporarily unavailable.' }));
    }
  };
  useEffect(() => { load(); }, []);
  const counts = state.coverage?.row_counts || {};
  const rows = Object.entries(counts).filter(([, value]) => Number(value) > 0).sort((a, b) => Number(b[1]) - Number(a[1]));
  const cgl = state.gather || {};
  const statement = state.statements?.scheduler || {};
  return (
    <main className="min-h-screen bg-[#f7f9fb] text-[#172033]">
      <Helmet><title>Data Health Sheet | Agarwal Global Investments</title></Helmet>
      <section className="border-b border-[#dbe3ee] bg-[#10233e] text-white"><div className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#a9c8ef]">AGI Intelligence Operations</p>
        <h1 className="mt-2 text-3xl font-semibold">Data Health Sheet</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[#d8e4f2]">A plain-English review of what AGI has stored, when it refreshes, and where data is still incomplete. Numbers are warehouse records—not investment signals.</p>
      </div></section>
      <section className="mx-auto max-w-6xl px-5 py-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-600">{state.loading ? 'Loading the latest warehouse status…' : `Last refresh: ${when(state.coverage?.last_refresh)}`}</p><button onClick={load} className="border border-[#294f7d] bg-white px-4 py-2 text-sm font-semibold text-[#17395f]">Refresh view</button></div>
        {state.error && <div className="mb-6 border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">{state.error}. Your data is not deleted; the review service may be restarting. Try again shortly.</div>}
        <div className="grid gap-4 md:grid-cols-3">
          <article className="border border-[#dbe3ee] bg-white p-5"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Companies covered</p><p className="mt-2 text-3xl font-semibold">{number(state.coverage?.companies)}</p><p className="mt-2 text-sm text-slate-600">Companies with a warehouse identity record.</p></article>
          <article className="border border-[#dbe3ee] bg-white p-5"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Stored records</p><p className="mt-2 text-3xl font-semibold">{number(state.coverage?.total_rows)}</p><p className="mt-2 text-sm text-slate-600">All current data rows across the intelligence warehouse.</p></article>
          <article className="border border-[#dbe3ee] bg-white p-5"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Continuous learning</p><p className="mt-2 text-xl font-semibold">{cgl.enabled ? 'Running' : 'Not running'}</p><p className="mt-2 text-sm text-slate-600">{cgl.intervalMs ? `Checks every ${Math.round(cgl.intervalMs / 60_000)} minutes.` : 'Status is loading.'}</p></article>
        </div>
        <section className="mt-6 border border-[#dbe3ee] bg-white"><div className="border-b border-[#e7edf4] p-5"><h2 className="text-lg font-semibold">What AGI has stored</h2><p className="mt-1 text-sm text-slate-600">Each row below is a data collection, not a claim that every company has complete history.</p></div><div className="divide-y divide-[#edf1f5]">{rows.map(([key, value]) => <div key={key} className="flex items-center justify-between gap-4 p-4"><div><p className="font-medium">{labels[key] || key.replaceAll('_', ' ')}</p><p className="mt-1 text-xs text-slate-500">Warehouse collection: {key}</p></div><strong>{number(value)} records</strong></div>)}</div></section>
        <section className="mt-6 border border-[#dbe3ee] bg-white p-5"><h2 className="text-lg font-semibold">Automatic collection</h2><div className="mt-4 grid gap-4 md:grid-cols-2"><div className="border border-[#e3eaf2] p-4"><p className="font-medium">Gather → Learn</p><p className="mt-1 text-sm text-slate-600">{cgl.enabled ? `Active. Last cycle: ${when(cgl.lastRun?.at)}.` : 'Not active. Check Render environment settings.'}</p></div><div className="border border-[#e3eaf2] p-4"><p className="font-medium">AGI financial statements</p><p className="mt-1 text-sm text-slate-600">{statement.running ? `Active: ${statement.target}. Batch size: ${statement.batchSize}.` : 'Starting after deployment.'}</p><p className="mt-1 text-xs text-slate-500">It rotates through companies, so the same first names are not refreshed every day.</p></div></div></section>
        <section className="mt-6 border-l-4 border-[#b7791f] bg-[#fffaf0] p-5 text-sm text-[#6c4c15]"><strong>What still needs review:</strong> Current AGI feeds provide short recent statement history. AGI retains normalized figures today; preserving every raw source line item and long-horizon filing history is the next data-quality expansion.</section>
      </section>
    </main>
  );
}
