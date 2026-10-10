import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  GitCompare,
  LineChart,
  RefreshCw,
  Search,
  Sparkles,
} from 'lucide-react';
import {
  analyseIieCompany,
  compareIie,
  consultIie,
  getIieCatalysts,
  getIieDashboard,
  getIieDna,
  getIieHealth,
  getIieMacro,
  getIieRisks,
  getIieSectors,
  getIieThemes,
  runIieBatch,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function pct(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  return n > 1 ? `${Math.round(n)}` : `${Math.round(n * 100)}%`;
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
  'Company Intelligence',
  'Sector Intelligence',
  'Theme Explorer',
  'Catalyst Dashboard',
  'Risk Centre',
  'Opportunity Centre',
  'Scenario Manager',
  'Company DNA',
  'Investment Thesis Library',
  'Knowledge Evolution',
  'Comparison Engine',
  'Monitoring Status',
  'Confidence Heatmap',
  'Version History',
];

export default function InvestmentIntelligence() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [sectors, setSectors] = useState([]);
  const [themes, setThemes] = useState([]);
  const [catalysts, setCatalysts] = useState([]);
  const [risks, setRisks] = useState([]);
  const [query, setQuery] = useState('INFY');
  const [consult, setConsult] = useState(null);
  const [dna, setDna] = useState(null);
  const [macro, setMacro] = useState(null);
  const [compare, setCompare] = useState(null);
  const [module, setModule] = useState(MODULES[0]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, s, t, c, r] = await Promise.all([
        getIieHealth(),
        getIieDashboard(),
        getIieSectors().catch(() => ({ sectors: [] })),
        getIieThemes().catch(() => ({ themes: [] })),
        getIieCatalysts({ limit: 20 }).catch(() => ({ catalysts: [] })),
        getIieRisks({ limit: 20 }).catch(() => ({ risks: [] })),
      ]);
      setHealth(h);
      setDashboard(d);
      setSectors(s?.sectors || []);
      setThemes(t?.themes || []);
      setCatalysts(c?.catalysts || d?.catalysts || []);
      setRisks(r?.risks || d?.risks || []);
    } catch (err) {
      setError(err?.message || 'Failed to load Investment Intelligence console');
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
      await analyseIieCompany(query.trim() || 'INFY');
      const [c, dn] = await Promise.all([
        consultIie(query.trim() || 'INFY'),
        getIieDna(query.trim() || 'INFY').catch(() => null),
      ]);
      setConsult(c);
      setDna(dn?.dna || null);
      await load();
    } catch (err) {
      setError(err?.message || 'Analyse failed');
    } finally {
      setBusy('');
    }
  };

  const onBatch = async () => {
    setBusy('batch');
    setError('');
    try {
      await runIieBatch(12);
      await load();
    } catch (err) {
      setError(err?.message || 'Batch failed');
    } finally {
      setBusy('');
    }
  };

  const onMacro = async () => {
    setBusy('macro');
    try {
      const m = await getIieMacro('repo_rate_cut');
      setMacro(m);
    } catch (err) {
      setError(err?.message || 'Macro map failed');
    } finally {
      setBusy('');
    }
  };

  const onCompare = async () => {
    setBusy('compare');
    try {
      const ids = (dashboard?.recent_profiles || []).slice(0, 2).map((p) => p.company_id);
      if (ids.length < 2) {
        setError('Analyse at least two companies before comparing');
        return;
      }
      const result = await compareIie(ids);
      setCompare(result);
    } catch (err) {
      setError(err?.message || 'Compare failed');
    } finally {
      setBusy('');
    }
  };

  const metrics = dashboard?.metrics || health?.metrics || {};
  const heatmap = dashboard?.confidence_heatmap || [];
  const distribution = dashboard?.confidence_distribution || {};
  const evolution = dashboard?.audit || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-orange-500 font-semibold">IIE v1.0</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Investment Intelligence</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Analytical layer after EVE — converts verified facts into institutional investment intelligence without redesigning Architecture v1.0.1.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={onBatch} disabled={busy === 'batch'}>
            <Activity className="w-4 h-4 mr-2" />
            Run batch
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
        <Stat label="Companies analysed" value={metrics.companies_analysed ?? '—'} />
        <Stat label="Analytical updates" value={metrics.analytical_updates ?? '—'} />
        <Stat label="Catalysts" value={metrics.catalyst_detections ?? catalysts.length ?? '—'} />
        <Stat label="Risk changes" value={metrics.risk_changes ?? '—'} hint={`Latency ${metrics.last_latency_ms ?? '—'} ms`} />
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
              <h2 className="font-semibold text-slate-900">Company Intelligence / Thesis</h2>
            </div>
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                onAnalyse();
              }}
            >
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="Symbol or company id (e.g. INFY)"
              />
              <Button type="submit" disabled={busy === 'analyse'}>
                <Sparkles className="w-4 h-4 mr-2" />
                Analyse
              </Button>
            </form>
            {consult?.company ? (
              <div className="mt-4 space-y-3 text-sm">
                <p className="text-slate-700">
                  <span className="font-medium">{consult.company.name || consult.company.company_id}</span>
                  {' · '}
                  confidence {pct(consult.company.profile?.confidence)}
                  {' · '}v{consult.company.profile?.version}
                </p>
                <p className="text-slate-600 whitespace-pre-wrap">
                  {consult.company.thesis?.investment_thesis || consult.company.profile?.sections?.investment_thesis || '—'}
                </p>
                <div className="grid md:grid-cols-3 gap-3">
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs uppercase text-slate-400 mb-1">Bull</p>
                    <p className="text-slate-700">{consult.company.scenarios?.bull?.key_drivers?.[0] || '—'}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs uppercase text-slate-400 mb-1">Base</p>
                    <p className="text-slate-700">{consult.company.scenarios?.base?.assumptions?.[0] || '—'}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs uppercase text-slate-400 mb-1">Bear</p>
                    <p className="text-slate-700">{consult.company.scenarios?.bear?.key_drivers?.[0] || '—'}</p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500 mt-4">Analyse a company to populate living intelligence objects.</p>
            )}
          </section>

          {(module === 'Confidence Heatmap' || module === 'Company Intelligence') && (
            <section className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3">Confidence Heatmap</h2>
              <div className="space-y-2">
                {heatmap.length ? (
                  heatmap.slice(0, 12).map((row) => (
                    <div key={row.company_id} className="flex items-center gap-3 text-sm">
                      <span className="w-28 truncate text-slate-700">{row.name || row.company_id}</span>
                      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className="h-full bg-emerald-500"
                          style={{ width: `${Math.min(100, Math.round((row.confidence || 0) * 100))}%` }}
                        />
                      </div>
                      <span className="w-12 text-right text-slate-500">{pct(row.confidence)}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">No profiles yet.</p>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-3">
                Distribution — low {distribution.low ?? 0} · medium {distribution.medium ?? 0} · high {distribution.high ?? 0}
              </p>
            </section>
          )}

          {(module === 'Risk Centre' || module === 'Catalyst Dashboard') && (
            <section className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3">
                {module === 'Risk Centre' ? 'Risk Centre' : 'Catalyst Dashboard'}
              </h2>
              <ul className="space-y-2 text-sm">
                {(module === 'Risk Centre' ? risks : catalysts).slice(0, 10).map((item) => (
                  <li key={item.risk_id || item.catalyst_id} className="border-b border-slate-100 pb-2">
                    <p className="font-medium text-slate-800">{item.title}</p>
                    <p className="text-xs text-slate-500">
                      {(item.risk_type || item.catalyst_type) || '—'} · conf {pct(item.confidence)}
                    </p>
                  </li>
                ))}
                {!(module === 'Risk Centre' ? risks : catalysts).length ? (
                  <li className="text-slate-500">No items yet — run analyse/batch after EVE evidence lands.</li>
                ) : null}
              </ul>
            </section>
          )}

          {module === 'Company DNA' && dna ? (
            <section className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3">Company DNA</h2>
              <div className="grid md:grid-cols-2 gap-2 text-sm">
                {Object.entries(dna.dimensions || {}).slice(0, 12).map(([key, dim]) => (
                  <div key={key} className="flex justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2">
                    <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
                    <span className="font-medium text-slate-900">{dim.assessment} ({pct(dim.confidence)})</span>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </div>

        <div className="space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
              <LineChart className="w-4 h-4" /> Sector / Theme
            </h2>
            <p className="text-xs text-slate-500 mb-2">Sectors ({sectors.length})</p>
            <div className="flex flex-wrap gap-1.5 mb-4">
              {sectors.slice(0, 16).map((s) => (
                <span key={s.sector_id} className="text-xs px-2 py-1 rounded bg-slate-100 text-slate-700">
                  {s.name}
                </span>
              ))}
            </div>
            <p className="text-xs text-slate-500 mb-2">Themes ({themes.length})</p>
            <div className="flex flex-wrap gap-1.5">
              {themes.slice(0, 16).map((t) => (
                <span key={t.theme_id} className="text-xs px-2 py-1 rounded bg-orange-50 text-orange-800">
                  {t.name}
                  {t.company_ids?.length ? ` · ${t.company_ids.length}` : ''}
                </span>
              ))}
            </div>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
            <h2 className="font-semibold text-slate-900 flex items-center gap-2">
              <GitCompare className="w-4 h-4" /> Macro / Compare
            </h2>
            <Button variant="outline" className="w-full" onClick={onMacro} disabled={busy === 'macro'}>
              Map repo rate cut
            </Button>
            {macro ? (
              <p className="text-xs text-slate-600">
                Chain: {(macro.chain || []).join(' → ') || '—'}
              </p>
            ) : null}
            <Button variant="outline" className="w-full" onClick={onCompare} disabled={busy === 'compare'}>
              Compare recent companies
            </Button>
            {compare ? (
              <p className="text-xs text-slate-600">{compare.summary}</p>
            ) : null}
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Version / Audit</h2>
            <ul className="space-y-2 text-xs text-slate-600 max-h-64 overflow-auto">
              {(evolution || []).slice(-12).reverse().map((a, idx) => (
                <li key={`${a.created_at}-${idx}`}>
                  <span className="font-medium text-slate-800">{a.action}</span>
                  {a.object_id ? ` · ${a.object_id}` : ''}
                </li>
              ))}
              {!evolution?.length ? <li>No audit events yet.</li> : null}
            </ul>
            <p className="text-[11px] text-slate-400 mt-3">
              Health: {health?.status || '—'} · {health?.position || ''} · locked {health?.architecture_status || ''}
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
