import { useCallback, useEffect, useState } from 'react';
import { Briefcase, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  analysePio,
  getPioDashboard,
  getPioHealth,
  getPioPortfolio,
  getPioQualityGates,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function Stat({ label, value, hint }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1 text-slate-900">{value ?? '—'}</p>
      {hint ? <p className="text-xs text-slate-400 mt-1">{hint}</p> : null}
    </div>
  );
}

export default function PortfolioIntelligence() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [book, setBook] = useState(null);
  const [portfolioId, setPortfolioId] = useState('agib_core_india');
  const [candidate, setCandidate] = useState('KOTAKBANK');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getPioHealth(),
        getPioDashboard(),
        getPioQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Portfolio Intelligence');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onAnalyse = async () => {
    setBusy('analyse');
    setError('');
    try {
      const pack = await analysePio({
        portfolio_id: portfolioId || 'agib_core_india',
        candidate: candidate || undefined,
      });
      setBook(pack);
      await load();
    } catch (err) {
      setError(err?.message || 'Analyse failed');
    } finally {
      setBusy('');
    }
  };

  const onLoadBook = async () => {
    setBusy('book');
    setError('');
    try {
      const pack = await getPioPortfolio(portfolioId || 'agib_core_india');
      setBook(pack);
    } catch (err) {
      setError(err?.message || 'Load failed');
    } finally {
      setBusy('');
    }
  };

  const healthB = book?.health || {};
  const pqe = book?.portfolio_quality || {};
  const impact = book?.impact || {};
  const suit = book?.suitability || {};
  const risk = book?.risk || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-emerald-700 font-semibold">
            Portfolio Intelligence Office v1.0 · soft layer
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Briefcase className="h-6 w-6 text-emerald-700" />
            Does this improve the portfolio?
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Portfolio health, candidate impact, diversification, risk budget, scenarios and Portfolio
            Quality Engine — suitability only, never buy/sell orders.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-40"
            value={portfolioId}
            onChange={(e) => setPortfolioId(e.target.value)}
            placeholder="portfolio id"
          />
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-36"
            value={candidate}
            onChange={(e) => setCandidate(e.target.value.toUpperCase())}
            placeholder="CANDIDATE"
          />
          <Button variant="outline" onClick={onLoadBook} disabled={!!busy}>
            {busy === 'book' ? 'Loading…' : 'Load book'}
          </Button>
          <Button variant="outline" onClick={onAnalyse} disabled={!!busy}>
            {busy === 'analyse' ? 'Analysing…' : 'Candidate impact'}
          </Button>
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="h-4 w-4 mt-0.5" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version || 'pio'} />
        <Stat label="Books" value={(dashboard?.portfolios || []).length || '—'} />
        <Stat
          label="Sample grade"
          value={healthB.grade || dashboard?.sample_health || '—'}
          hint={`PQE ${pqe.portfolio_quality ?? dashboard?.sample_pqe ?? '—'}`}
        />
        <Stat
          label="Candidate effect"
          value={impact.net_portfolio_effect ?? '—'}
          hint={suit.portfolio_fit ? `Fit: ${suit.portfolio_fit}` : 'Run candidate'}
        />
        <Stat
          label="Quality gates"
          value={gates?.passed ? 'Pass' : 'Review'}
          hint="No buy/sell · evidence-backed"
        />
      </div>

      {book ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">
              {(book.profile || {}).name || book.portfolio_id}
            </h2>
            <p className="text-slate-600">{book.report?.executive_summary}</p>
            <ul className="space-y-1 text-slate-600">
              <li>Holdings: {(book.holdings || []).length} · Cash: {book.cash_weight}</li>
              <li>Expected vol: {risk.expected_volatility ?? '—'}</li>
              <li>
                Worst scenario: {(book.scenarios?.worst || {}).scenario} (
                {(book.scenarios?.worst || {}).portfolio_impact_pct}%)
              </li>
              <li>Optimisation: {book.optimisation?.optimisation_score ?? '—'} (quality, not return)</li>
            </ul>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Suitability matrix</h2>
            <p className="text-slate-600">{suit.summary || 'Run a candidate to populate.'}</p>
            <ul className="space-y-1 text-slate-600">
              {Object.entries(suit)
                .filter(([k]) =>
                  [
                    'strategic_fit',
                    'portfolio_fit',
                    'diversification_benefit',
                    'risk_contribution',
                    'monitoring_requirement',
                  ].includes(k)
                )
                .map(([k, v]) => (
                  <li key={k}>
                    {k.replaceAll('_', ' ')}: {String(v)}
                  </li>
                ))}
            </ul>
            <p className="text-xs text-slate-400 mt-3">{book.report?.cio_brief}</p>
          </div>
        </div>
      ) : null}

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Quality gates</h2>
          <span
            className={`text-xs font-semibold px-2 py-1 rounded-full ${
              gates?.passed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
            }`}
          >
            {gates?.passed ? 'Pass' : 'Review'}
          </span>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {Object.entries(gates?.checks || {}).map(([key, ok]) => (
            <div
              key={key}
              className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2"
            >
              <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
              <span className={ok ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                {ok ? 'Yes' : 'No'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
