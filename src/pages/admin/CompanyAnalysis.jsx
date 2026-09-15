import { useCallback, useEffect, useState } from 'react';
import { Building2, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  getCompanyAnalysisDashboard,
  getCompanyAnalysisHealth,
  getCompanyAnalysisQualityGates,
  analyseCompany,
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

export default function CompanyAnalysis() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [probe, setProbe] = useState(null);
  const [ticker, setTicker] = useState('HDFCBANK');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getCompanyAnalysisHealth(),
        getCompanyAnalysisDashboard(),
        getCompanyAnalysisQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Company Analysis dashboard');
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
      const result = await analyseCompany(ticker || 'HDFCBANK', `Analyse ${ticker}`);
      setProbe(result);
      await load();
    } catch (err) {
      setError(err?.message || 'Analysis failed');
    } finally {
      setBusy('');
    }
  };

  const m = dashboard?.metrics || {};
  const reports = dashboard?.latest_reports || [];
  const readiness = probe?.recommendation_readiness || {};
  const scores = readiness.scores || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-indigo-700 font-semibold">
            Company Analysis Engine v1.0 · Institutional layer
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Building2 className="h-6 w-6 text-indigo-700" />
            Company Analysis
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Applies Academy concepts to each company with CID / LEO / DVC / SIF evidence. Not a
            recommendation engine. Not Context Assembly. Recommendation gate unchanged.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-36"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
          />
          <Button variant="outline" onClick={onAnalyse} disabled={!!busy}>
            {busy === 'analyse' ? 'Analysing…' : 'Run Analysis'}
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
        <Stat label="Status" value={health?.status || '—'} hint={health?.version} />
        <Stat label="Reports" value={m.reports ?? 0} />
        <Stat label="Avg readiness" value={m.avg_readiness != null ? `${m.avg_readiness}%` : '—'} />
        <Stat label="Eligible" value={m.eligible_count ?? 0} hint="Coverage only — not buys" />
        <Stat
          label="Quality gates"
          value={gates?.passed ? 'PASS' : gates ? 'FAIL' : '—'}
          hint={gates?.message}
        />
      </div>

      {probe ? (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-semibold text-slate-900">
              Probe · {probe.ticker || ticker}
            </h2>
            <p className="text-sm text-slate-500">
              Business quality {(probe.business_quality || {}).business_quality_score ?? '—'} · Gate{' '}
              {readiness.gate || '—'} · {readiness.overall ?? '—'}%
            </p>
          </div>
          <p className="text-sm text-slate-700">{probe.executive_summary}</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Financial" value={scores.financial_intelligence != null ? `${scores.financial_intelligence}%` : '—'} />
            <Stat label="Valuation" value={scores.valuation != null ? `${scores.valuation}%` : '—'} />
            <Stat label="Sector" value={scores.sector_intelligence != null ? `${scores.sector_intelligence}%` : '—'} />
            <Stat label="Knowledge" value={scores.knowledge != null ? `${scores.knowledge}%` : '—'} />
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500 mb-2">Applied Academy concepts</p>
            <ul className="space-y-2">
              {((probe.academy_application || {}).applied_concepts || []).slice(0, 6).map((c) => (
                <li key={c.concept_id || c.title} className="text-sm text-slate-700 border-l-2 border-indigo-200 pl-3">
                  <span className="font-semibold">{c.title}</span> — {c.application}
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="text-lg font-semibold text-slate-900 mb-3">Latest analyses</h2>
        {reports.length === 0 ? (
          <p className="text-sm text-slate-500">No reports yet — run an analysis.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b">
                  <th className="py-2 pr-4">Ticker</th>
                  <th className="py-2 pr-4">Business quality</th>
                  <th className="py-2 pr-4">Readiness</th>
                  <th className="py-2 pr-4">Gate</th>
                  <th className="py-2 pr-4">Concepts</th>
                  <th className="py-2">Generated</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={`${r.ticker}-${r.generated_at}`} className="border-b border-slate-100">
                    <td className="py-2 pr-4 font-medium">{r.ticker}</td>
                    <td className="py-2 pr-4">{r.business_quality_score ?? '—'}</td>
                    <td className="py-2 pr-4">{r.overall_readiness != null ? `${r.overall_readiness}%` : '—'}</td>
                    <td className="py-2 pr-4">{r.gate || '—'}</td>
                    <td className="py-2 pr-4">{r.applied_concepts ?? '—'}</td>
                    <td className="py-2 text-slate-500">{r.generated_at || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
