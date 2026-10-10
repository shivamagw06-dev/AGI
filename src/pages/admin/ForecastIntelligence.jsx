import { useCallback, useEffect, useState } from 'react';
import { Compass, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  analyseLegacyFie,
  getLegacyFieCompany,
  getLegacyFieDashboard,
  getLegacyFieHealth,
  getLegacyFieQualityGates,
  getLegacyFieScenarios,
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

export default function ForecastIntelligence() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [pack, setPack] = useState(null);
  const [ticker, setTicker] = useState('HDFCBANK');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getLegacyFieHealth(),
        getLegacyFieDashboard(),
        getLegacyFieQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Forecast Intelligence');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onCompany = async () => {
    setBusy('company');
    setError('');
    try {
      const out = await getLegacyFieCompany(ticker || 'HDFCBANK');
      setPack(out);
    } catch (err) {
      setError(err?.message || 'Company forecast failed');
    } finally {
      setBusy('');
    }
  };

  const onScenarios = async () => {
    setBusy('scenarios');
    setError('');
    try {
      const out = await getLegacyFieScenarios(ticker || 'HDFCBANK');
      setPack(out);
    } catch (err) {
      setError(err?.message || 'Scenarios failed');
    } finally {
      setBusy('');
    }
  };

  const onAnalyse = async () => {
    setBusy('analyse');
    setError('');
    try {
      const out = await analyseLegacyFie({
        ticker: ticker || undefined,
        question: `What has to happen for ${ticker || 'this company'} to outperform?`,
      });
      setPack(out);
      await load();
    } catch (err) {
      setError(err?.message || 'Analyse failed');
    } finally {
      setBusy('');
    }
  };

  const dist = pack?.probabilities?.distribution || dashboard?.sample_distribution || {};
  const scenarios = pack?.scenarios || [];
  const catalysts = pack?.catalysts?.timeline || pack?.catalysts?.items || [];
  const sens = pack?.sensitivity?.top_sensitivities || [];
  const report = pack?.report || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-sky-700 font-semibold">
            Forecast Intelligence Engine v1.0 · soft layer
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Compass className="h-6 w-6 text-sky-700" />
            What future paths are plausible?
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Probabilistic institutional scenarios — bull/base/bear/stress/recovery with catalysts,
            triggers, sensitivity and explicit uncertainty. Not a price prediction engine.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-36"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
          />
          <Button variant="outline" onClick={onCompany} disabled={!!busy}>
            {busy === 'company' ? 'Loading…' : 'Company'}
          </Button>
          <Button variant="outline" onClick={onScenarios} disabled={!!busy}>
            {busy === 'scenarios' ? 'Loading…' : 'Scenarios'}
          </Button>
          <Button variant="outline" onClick={onAnalyse} disabled={!!busy}>
            {busy === 'analyse' ? 'Analysing…' : 'Analyse'}
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
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version || 'fie'} />
        <Stat
          label="Most likely"
          value={pack?.probabilities?.most_likely || dashboard?.sample_most_likely || '—'}
          hint="Scenario, not price"
        />
        <Stat
          label="Confidence"
          value={pack?.confidence?.confidence ?? dashboard?.sample_confidence ?? '—'}
          hint={pack?.confidence?.label || 'evidence-backed'}
        />
        <Stat
          label="Uncertainty"
          value={pack?.uncertainty?.uncertainty_score ?? '—'}
          hint="explicitly disclosed"
        />
        <Stat
          label="Quality gates"
          value={gates?.passed ? 'Pass' : 'Review'}
          hint="No price targets"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
          <h2 className="font-semibold text-slate-900">Probability distribution</h2>
          <ul className="space-y-2 text-slate-600">
            {Object.entries(dist).map(([k, v]) => (
              <li key={k} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2">
                <span className="capitalize">{k}</span>
                <span className="text-sky-700 font-medium">{v}</span>
              </li>
            ))}
            {!Object.keys(dist).length ? <li>Run company analyse to populate.</li> : null}
          </ul>
          <p className="text-xs text-slate-400 mt-3">{report.cio_brief || dashboard?.sample_summary}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
          <h2 className="font-semibold text-slate-900">Catalyst timeline</h2>
          <ul className="space-y-2 text-slate-600">
            {catalysts.slice(0, 8).map((c) => (
              <li key={c.id || c.label}>
                <span className="text-xs uppercase tracking-wide text-sky-700 mr-2">{c.kind}</span>
                {c.label}
                <span className="text-slate-400"> · {c.polarity} · {c.horizon}</span>
              </li>
            ))}
            {!catalysts.length ? <li>Run company pack to populate catalysts.</li> : null}
          </ul>
        </div>
      </div>

      {scenarios.length ? (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-slate-900">Scenario / trigger monitor</h2>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {scenarios.map((s) => (
              <div key={s.name} className="border border-slate-100 rounded-lg p-3">
                <p className="font-semibold capitalize text-slate-900">
                  {s.name} · {s.probability}
                </p>
                <ul className="mt-2 space-y-1 text-slate-600">
                  {(s.triggers || []).slice(0, 4).map((t) => (
                    <li key={`${s.name}-${t.metric}`}>{t.monitor || `${t.metric} ${t.condition}`}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {sens.length ? (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <h2 className="font-semibold text-slate-900">Sensitivity heatmap</h2>
          <div className="grid gap-2 sm:grid-cols-2 text-sm">
            {sens.map((s) => (
              <div
                key={s.factor}
                className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2"
              >
                <span className="text-slate-600">{s.factor.replaceAll('_', ' ')}</span>
                <span className="text-sky-700 font-medium">
                  {s.sensitivity} · {s.band}
                </span>
              </div>
            ))}
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
