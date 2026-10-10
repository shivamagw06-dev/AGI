import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  Network,
  RefreshCw,
} from 'lucide-react';
import {
  analyseFiml,
  bundleFiml,
  getFimlDashboard,
  getFimlGraph,
  getFimlHealth,
  getFimlMetrics,
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
  'Accounting',
  'Business',
  'Industry',
  'Competition',
  'Capital Allocation',
  'Economics',
  'Risk',
  'Governance',
  'Decision',
  'Model Registry',
  'Version History',
  'Coverage Dashboard',
  'Quality Scores',
  'Dependency Graph',
];

const DOMAIN_MAP = {
  Accounting: 'accounting',
  Business: 'business',
  Industry: 'industry',
  Competition: 'competition',
  'Capital Allocation': 'capital_allocation',
  Economics: 'economics',
  Risk: 'risk',
  Governance: 'governance',
  Decision: 'decision',
};

export default function Models() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [graph, setGraph] = useState(null);
  const [symbol, setSymbol] = useState('INFY');
  const [module, setModule] = useState(MODULES[0]);
  const [analysis, setAnalysis] = useState(null);
  const [bundle, setBundle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, m, g] = await Promise.all([
        getFimlHealth(),
        getFimlDashboard(),
        getFimlMetrics(),
        getFimlGraph(),
      ]);
      setHealth(h);
      setDashboard(d);
      setMetrics(m?.metrics || d?.metrics || {});
      setGraph(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Models console');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onAnalyse = async (e) => {
    e?.preventDefault?.();
    setBusy('analyse');
    setError('');
    try {
      const domain = DOMAIN_MAP[module] || 'decision';
      const payload = {
        company_symbol: symbol.trim().toUpperCase() || 'INFY',
        revenue_growth: 0.18,
        gross_margin: 0.32,
        gross_margin_delta: 0.01,
        revenue_driver: 'pricing',
        cash_conversion: 0.95,
        ebit_margin: 0.22,
        fcf_margin: 0.14,
        recurring_revenue_share: 0.7,
        pricing_power: 0.7,
        switching_costs: 0.65,
        roic: 0.22,
        wacc: 0.11,
        margin_of_safety: 0.18,
        data_quality: 'B',
        peers: ['TCS', 'WIPRO'],
      };
      const [a, b] = await Promise.all([analyseFiml(domain, payload), bundleFiml(payload)]);
      setAnalysis(a);
      setBundle(b);
      await load();
    } catch (err) {
      setError(err?.message || 'Analysis failed');
    } finally {
      setBusy('');
    }
  };

  const m = metrics || dashboard?.metrics || health?.metrics || {};
  const models = dashboard?.models || health?.domains || [];
  const industries = dashboard?.industries || health?.industry_configs || [];
  const consumers = graph?.consumers || {};
  const decision = bundle?.decision || analysis;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-orange-500 font-semibold">FIML v1.0</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Financial Models</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Shared institutional domain models — not an engine. Accounting, industry, competition, capital allocation, risk, governance and decision frameworks for every AGI consumer.
          </p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm flex gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Analyses" value={m.analyses ?? '—'} />
        <Stat label="Domains" value={Array.isArray(models) ? models.length : '—'} />
        <Stat label="Industries" value={industries.length || '—'} />
        <Stat label="Decisions" value={m.decisions ?? '—'} hint={`Refuses ${m.refuses ?? 0}`} />
      </div>

      <div className="flex flex-wrap gap-2">
        {MODULES.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => setModule(name)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              module === name
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <BookOpen className="w-4 h-4 text-slate-500" />
              <h2 className="font-semibold text-slate-900">Run Model</h2>
            </div>
            <form className="flex gap-2" onSubmit={onAnalyse}>
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="Symbol"
              />
              <Button type="submit" disabled={busy === 'analyse'}>
                Analyse {DOMAIN_MAP[module] || 'decision'}
              </Button>
            </form>
            <p className="text-xs text-slate-500 mt-3">Active module: {module}</p>
            {analysis ? (
              <div className="mt-4 space-y-2 text-sm">
                <p className="font-medium text-slate-900">{analysis.summary}</p>
                <p className="text-slate-600">
                  Score {pct(analysis.score)} · {analysis.label} · conf {pct(analysis.confidence)}
                </p>
                {(analysis.red_flags || []).length ? (
                  <p className="text-xs text-red-600">Flags: {(analysis.red_flags || []).join('; ')}</p>
                ) : null}
              </div>
            ) : null}
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Decision Bundle</h2>
            {decision?.outputs?.decision || decision?.summary ? (
              <div className="text-sm space-y-2">
                <p>{decision.summary || decision.outputs?.decision?.suggested_action}</p>
                <div className="grid md:grid-cols-3 gap-3">
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs text-slate-400">Action</p>
                    <p className="font-semibold">
                      {decision.outputs?.decision?.suggested_action || decision.label || '—'}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs text-slate-400">Quality</p>
                    <p className="font-semibold">
                      {pct(decision.outputs?.decision?.investment_quality || decision.score)}
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs text-slate-400">Conviction</p>
                    <p className="font-semibold">
                      {pct(decision.outputs?.decision?.conviction)}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Run analysis to populate the decision bundle.</p>
            )}
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Network className="w-4 h-4 text-slate-500" />
              <h2 className="font-semibold text-slate-900">Dependency Graph</h2>
            </div>
            <div className="space-y-2 text-sm max-h-64 overflow-auto">
              {Object.entries(consumers).map(([engine, domains]) => (
                <div key={engine} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="font-medium">{engine}</p>
                  <p className="text-xs text-slate-500">{(domains || []).join(', ')}</p>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Model Registry</h2>
            <div className="space-y-2 text-sm max-h-72 overflow-auto">
              {(Array.isArray(models) ? models : []).map((model) => (
                <div key={model.model_id || model.domain || model} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="font-medium">{model.name || model.domain || model}</p>
                  <p className="text-xs text-slate-500">
                    {model.domain} · v{model.version || '1.0.0'}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Industry Coverage</h2>
            <div className="flex flex-wrap gap-2">
              {industries.map((ind) => (
                <span key={ind} className="text-xs rounded-md border border-slate-200 px-2 py-1 bg-white">
                  {ind}
                </span>
              ))}
            </div>
            <p className="text-xs text-slate-500 mt-3">
              Status: {health?.status || '—'} · {health?.not_an_engine ? 'Library (not an engine)' : ''}
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
