import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  Gauge,
  RefreshCw,
  Search,
  Target,
} from 'lucide-react';
import {
  consultFle,
  generateFleForecasts,
  getFleCalibration,
  getFleDashboard,
  getFleHealth,
  getFleLearning,
  resolveFleForecast,
  runFleJobs,
  searchFle,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function pct(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  return n > 1 ? `${Math.round(n)}%` : `${Math.round(n * 100)}%`;
}

function Stat({ label, value, hint }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1 text-slate-900">{value}</p>
      {hint ? <p className="text-xs text-slate-400 mt-1">{hint}</p> : null}
    </div>
  );
}

const MODULES = [
  'Forecast Registry',
  'Pending Reviews',
  'Resolved Forecasts',
  'Accuracy Dashboard',
  'Calibration Dashboard',
  'Scenario Explorer',
  'Learning Library',
  'Forecast Timeline',
  'Forecast Search',
  'Forecast Heatmap',
  'Sector Accuracy',
  'Macro Accuracy',
  'Portfolio Forecasts',
  'Expired Forecasts',
];

export default function Forecasting() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [calibration, setCalibration] = useState(null);
  const [learnings, setLearnings] = useState([]);
  const [query, setQuery] = useState('INFY');
  const [consult, setConsult] = useState(null);
  const [hits, setHits] = useState([]);
  const [module, setModule] = useState(MODULES[0]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [resolveValue, setResolveValue] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, c, l] = await Promise.all([
        getFleHealth(),
        getFleDashboard(),
        getFleCalibration().catch(() => null),
        getFleLearning({ limit: 20 }).catch(() => ({ learnings: [] })),
      ]);
      setHealth(h);
      setDashboard(d);
      setCalibration(c?.current || d?.calibration || null);
      setLearnings(l?.learnings || d?.learnings || []);
    } catch (err) {
      setError(err?.message || 'Failed to load Forecasting console');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onGenerate = async () => {
    setBusy('generate');
    setError('');
    try {
      await generateFleForecasts(query.trim() || 'INFY');
      const c = await consultFle(query.trim() || 'INFY');
      setConsult(c);
      await load();
    } catch (err) {
      setError(err?.message || 'Generate failed');
    } finally {
      setBusy('');
    }
  };

  const onSearch = async (e) => {
    e?.preventDefault?.();
    setBusy('search');
    try {
      const [s, c] = await Promise.all([
        searchFle(query.trim() || 'INFY'),
        consultFle(query.trim() || 'INFY'),
      ]);
      setHits(s?.hits || []);
      setConsult(c);
    } catch (err) {
      setError(err?.message || 'Search failed');
    } finally {
      setBusy('');
    }
  };

  const onJobs = async () => {
    setBusy('jobs');
    try {
      await runFleJobs();
      await load();
    } catch (err) {
      setError(err?.message || 'Jobs failed');
    } finally {
      setBusy('');
    }
  };

  const onResolveFirst = async () => {
    const pending = dashboard?.pending_reviews?.[0] || dashboard?.recent_forecasts?.[0];
    if (!pending?.forecast_id) {
      setError('No forecast available to resolve');
      return;
    }
    setBusy('resolve');
    try {
      await resolveFleForecast(pending.forecast_id, {
        actual_value: resolveValue || pending.predicted_value || '100',
        notes: 'Resolved from admin console',
      });
      await load();
    } catch (err) {
      setError(err?.message || 'Resolve failed');
    } finally {
      setBusy('');
    }
  };

  const metrics = dashboard?.metrics || health?.metrics || {};
  const accuracy = dashboard?.accuracy || {};
  const heatmap = dashboard?.heatmap || [];
  const pending = dashboard?.pending_reviews || [];
  const resolved = dashboard?.resolved_forecasts || [];
  const recent = dashboard?.recent_forecasts || [];
  const buckets = calibration?.buckets || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-orange-500 font-semibold">FLE v1.0</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Forecasting & Learning</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Institutional forecast memory after IIE — record predictions, measure outcomes, calibrate confidence, and learn without overwriting history.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" onClick={onJobs} disabled={busy === 'jobs'}>
            Run resolution jobs
          </Button>
          <Button onClick={onGenerate} disabled={busy === 'generate'}>
            <Target className="w-4 h-4 mr-2" />
            Generate from IIE
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm flex gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Forecasts created" value={metrics.forecasts_created ?? '—'} />
        <Stat label="Resolved" value={metrics.forecasts_resolved ?? '—'} />
        <Stat label="Avg accuracy" value={pct(metrics.average_accuracy ?? accuracy.mean_accuracy_score)} />
        <Stat
          label="Calibration drift"
          value={metrics.calibration_drift ?? calibration?.calibration_drift ?? '—'}
          hint={`Pending reviews ${metrics.pending_reviews ?? pending.length}`}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {MODULES.map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setModule(m)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              module === m
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Search className="w-4 h-4 text-slate-500" />
              <h2 className="font-semibold text-slate-900">Forecast Search / Company Timeline</h2>
            </div>
            <form className="flex gap-2" onSubmit={onSearch}>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="Symbol or forecast query"
              />
              <Button type="submit" disabled={busy === 'search'}>
                Search
              </Button>
            </form>
            {consult?.company ? (
              <div className="mt-4 space-y-2 text-sm">
                <p className="text-slate-700 font-medium">{consult.company.company_id}</p>
                <p className="text-xs text-slate-500">
                  Pending {consult.company.pending_forecasts?.length || 0} · Resolved{' '}
                  {consult.company.resolved_forecasts?.length || 0} · Learnings{' '}
                  {consult.company.learning_history?.length || 0}
                </p>
                {(consult.uncertainty_flags || []).length ? (
                  <p className="text-amber-700 text-xs">
                    Uncertainty: {(consult.uncertainty_flags || []).join(', ')}
                  </p>
                ) : null}
                <ul className="space-y-2">
                  {(consult.company.pending_forecasts || []).slice(0, 5).map((f) => (
                    <li key={f.forecast_id} className="border-b border-slate-100 pb-2">
                      <p className="font-medium text-slate-800">
                        {f.metric} · {f.predicted_value}
                      </p>
                      <p className="text-xs text-slate-500">
                        conf {pct(f.confidence)} · {f.status} · v{f.version}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-sm text-slate-500 mt-4">Generate or search to load forecast history.</p>
            )}
            {hits.length ? (
              <div className="mt-4">
                <p className="text-xs uppercase text-slate-400 mb-2">Hits</p>
                <ul className="space-y-1 text-sm">
                  {hits.slice(0, 8).map((h) => (
                    <li key={`${h.kind}-${h.id}`} className="text-slate-700">
                      {h.kind}: {h.label}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

          {(module === 'Forecast Registry' || module === 'Pending Reviews') && (
            <section className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3">
                {module === 'Pending Reviews' ? 'Pending Reviews' : 'Forecast Registry'}
              </h2>
              <ul className="space-y-2 text-sm">
                {(module === 'Pending Reviews' ? pending : recent).slice(0, 12).map((f) => (
                  <li key={f.forecast_id} className="border-b border-slate-100 pb-2">
                    <p className="font-medium text-slate-800">
                      {(f.company_symbol || f.company_id) || '—'} · {f.metric}
                    </p>
                    <p className="text-slate-600">{f.predicted_value}</p>
                    <p className="text-xs text-slate-500">
                      {f.status} · conf {pct(f.confidence)} · review {f.review_date || '—'}
                    </p>
                  </li>
                ))}
                {!(module === 'Pending Reviews' ? pending : recent).length ? (
                  <li className="text-slate-500">No forecasts yet.</li>
                ) : null}
              </ul>
              <div className="mt-4 flex gap-2">
                <input
                  value={resolveValue}
                  onChange={(e) => setResolveValue(e.target.value)}
                  className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  placeholder="Actual value to resolve first forecast"
                />
                <Button variant="outline" onClick={onResolveFirst} disabled={busy === 'resolve'}>
                  Resolve
                </Button>
              </div>
            </section>
          )}

          {(module === 'Calibration Dashboard' || module === 'Accuracy Dashboard') && (
            <section className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <Gauge className="w-4 h-4" />
                {module}
              </h2>
              {module === 'Accuracy Dashboard' ? (
                <div className="grid md:grid-cols-3 gap-3 text-sm">
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs text-slate-400">Directional</p>
                    <p className="text-xl font-semibold">{pct(accuracy.directional_accuracy)}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs text-slate-400">Mean accuracy</p>
                    <p className="text-xl font-semibold">{pct(accuracy.mean_accuracy_score)}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs text-slate-400">Mean % error</p>
                    <p className="text-xl font-semibold">{accuracy.mean_percentage_error ?? '—'}</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  {buckets.length ? (
                    buckets.map((b) => (
                      <div key={b.band} className="flex items-center justify-between text-sm rounded-lg bg-slate-50 px-3 py-2">
                        <span className="text-slate-700">{b.band}</span>
                        <span className="text-slate-600">
                          success {pct(b.historical_success_rate)} · {b.calibration_label} · n={b.forecast_count}
                        </span>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500">Resolve forecasts to populate calibration.</p>
                  )}
                </div>
              )}
            </section>
          )}

          {module === 'Forecast Heatmap' && (
            <section className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3">Forecast Heatmap</h2>
              <div className="space-y-2">
                {heatmap.length ? (
                  heatmap.slice(0, 12).map((row) => (
                    <div key={row.company_id} className="flex items-center gap-3 text-sm">
                      <span className="w-28 truncate text-slate-700">{row.company_id}</span>
                      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className="h-full bg-teal-600"
                          style={{ width: `${Math.min(100, Math.round((row.accuracy || 0) * 100))}%` }}
                        />
                      </div>
                      <span className="w-12 text-right text-slate-500">{pct(row.accuracy)}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">No company health yet.</p>
                )}
              </div>
            </section>
          )}
        </div>

        <div className="space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
              <BookOpen className="w-4 h-4" /> Learning Library
            </h2>
            <ul className="space-y-2 text-sm max-h-80 overflow-auto">
              {learnings.slice(0, 12).map((l) => (
                <li key={l.learning_id} className="border-b border-slate-100 pb-2">
                  <p className="font-medium text-slate-800">
                    {l.metric} · {l.company_id || '—'}
                  </p>
                  <p className="text-xs text-slate-600">{(l.lessons_learned || []).join(' ')}</p>
                </li>
              ))}
              {!learnings.length ? <li className="text-slate-500">No learnings yet — resolve forecasts first.</li> : null}
            </ul>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Resolved</h2>
            <ul className="space-y-2 text-sm">
              {resolved.slice(0, 8).map((o) => (
                <li key={o.outcome_id} className="text-slate-700">
                  {o.forecast_id.slice(0, 16)}… · acc {pct(o.accuracy_score)}
                </li>
              ))}
              {!resolved.length ? <li className="text-slate-500">None yet.</li> : null}
            </ul>
            <p className="text-[11px] text-slate-400 mt-3">
              Health: {health?.status || '—'} · {health?.position || ''} · {health?.architecture_status || ''}
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
