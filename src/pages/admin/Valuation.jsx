import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Calculator,
  RefreshCw,
  Scale,
} from 'lucide-react';
import {
  consultVe,
  getVeCompare,
  getVeDashboard,
  getVeHealth,
  getVeScenarios,
  getVeSensitivity,
  valueVeCompany,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function pct(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  return `${Math.round(n * (Math.abs(n) <= 1 ? 100 : 1))}${Math.abs(n) <= 1 ? '%' : ''}`;
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
  'Valuation Dashboard',
  'DCF Explorer',
  'Relative Valuation',
  'Historical Multiples',
  'Sensitivity Analysis',
  'Assumption Registry',
  'Scenario Comparison',
  'Margin of Safety',
  'Peer Comparison',
];

export default function Valuation() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [symbol, setSymbol] = useState('INFY');
  const [consult, setConsult] = useState(null);
  const [scenarios, setScenarios] = useState(null);
  const [sensitivity, setSensitivity] = useState(null);
  const [compare, setCompare] = useState(null);
  const [module, setModule] = useState(MODULES[0]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d] = await Promise.all([getVeHealth(), getVeDashboard()]);
      setHealth(h);
      setDashboard(d);
    } catch (err) {
      setError(err?.message || 'Failed to load Valuation console');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onValue = async (e) => {
    e?.preventDefault?.();
    setBusy('value');
    setError('');
    try {
      await valueVeCompany({ key: symbol.trim() || 'INFY', trigger: 'admin' });
      const [c, s, sens, cmp] = await Promise.all([
        consultVe(symbol.trim() || 'INFY'),
        getVeScenarios(symbol.trim() || 'INFY'),
        getVeSensitivity(symbol.trim() || 'INFY'),
        getVeCompare(symbol.trim() || 'INFY'),
      ]);
      setConsult(c);
      setScenarios(s);
      setSensitivity(sens);
      setCompare(cmp);
      await load();
    } catch (err) {
      setError(err?.message || 'Valuation failed');
    } finally {
      setBusy('');
    }
  };

  const m = dashboard?.metrics || health?.metrics || {};
  const latest = dashboard?.latest_valuations || [];
  const valuation = consult?.latest_valuation || {};
  const mos = consult?.margin_of_safety || valuation.margin_of_safety || {};
  const assumptions = consult?.assumptions || valuation.assumptions || [];
  const models = valuation.models || [];
  const dcf = models.find((x) => x.model === 'dcf_fcff');
  const peers = compare?.peers || valuation.peers || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-orange-500 font-semibold">VE v1.0</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Valuation</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Institutional intrinsic value — DCF, relative, SOTP, scenarios and margin of safety from verified intelligence only.
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
        <Stat label="Valuations" value={m.valuations_created ?? '—'} />
        <Stat label="Companies" value={m.companies_covered ?? '—'} />
        <Stat label="Undervalued" value={m.undervalued_count ?? '—'} hint={`Over ${m.overvalued_count ?? 0}`} />
        <Stat label="Avg MoS" value={m.avg_mos_pct != null ? `${m.avg_mos_pct}%` : '—'} />
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
              <Calculator className="w-4 h-4 text-slate-500" />
              <h2 className="font-semibold text-slate-900">Value Company</h2>
            </div>
            <form className="flex gap-2" onSubmit={onValue}>
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="Symbol e.g. INFY"
              />
              <Button type="submit" disabled={busy === 'value'}>
                <Scale className="w-4 h-4 mr-2" />
                Value
              </Button>
            </form>
            <p className="text-xs text-slate-500 mt-3">Active module: {module}</p>
            {valuation.valuation_id ? (
              <div className="mt-4 grid md:grid-cols-4 gap-3 text-sm">
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-400">Intrinsic</p>
                  <p className="text-xl font-semibold">₹{valuation.intrinsic_value ?? '—'}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-400">Market</p>
                  <p className="text-xl font-semibold">₹{valuation.market_price ?? '—'}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-400">MoS</p>
                  <p className="text-xl font-semibold">{mos.discount_premium_pct ?? '—'}%</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-400">Label</p>
                  <p className="text-xl font-semibold capitalize">{mos.label || '—'}</p>
                </div>
              </div>
            ) : null}
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">DCF Explorer</h2>
            {dcf ? (
              <div className="text-sm space-y-2">
                <p>
                  FCFF intrinsic <span className="font-semibold">₹{dcf.intrinsic_value}</span> · EV{' '}
                  {dcf.enterprise_value ?? '—'}
                </p>
                <p className="text-xs text-slate-500">
                  Terminal {dcf.details?.terminal_value_cr ?? '—'} · WACC {pct(dcf.details?.wacc)}
                </p>
                <p className="text-xs text-slate-500">
                  FCF path: {(dcf.details?.fcf_path_cr || []).join(' → ') || '—'}
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Run a valuation to explore DCF.</p>
            )}
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Scenarios</h2>
            <div className="grid md:grid-cols-3 gap-3">
              {(scenarios?.scenarios || valuation.scenarios || []).map((s) => (
                <div key={s.name} className="rounded-lg bg-slate-50 p-3 text-sm">
                  <p className="font-medium capitalize">{s.name}</p>
                  <p className="text-xl font-semibold mt-1">₹{s.intrinsic_value}</p>
                  <p className="text-xs text-slate-500">p={s.probability} · conf {pct(s.confidence)}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Sensitivity</h2>
            <div className="space-y-2 max-h-56 overflow-auto text-sm">
              {(sensitivity?.most_sensitive_assumptions || []).map((row) => (
                <div key={row.parameter} className="flex justify-between rounded-lg bg-slate-50 px-3 py-2">
                  <span>{row.parameter}</span>
                  <span className="font-medium">{row.max_abs_change_pct}%</span>
                </div>
              ))}
              {!sensitivity?.most_sensitive_assumptions?.length ? (
                <p className="text-slate-500">No sensitivity yet</p>
              ) : null}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Assumption Registry</h2>
            <div className="space-y-2 max-h-64 overflow-auto text-sm">
              {assumptions.slice(0, 12).map((a) => (
                <div key={`${a.name}-${a.source}-${a.version}`} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="font-medium">
                    {a.name}: {a.value}
                  </p>
                  <p className="text-xs text-slate-500">
                    {a.source} · conf {pct(a.confidence)}
                  </p>
                </div>
              ))}
              {!assumptions.length ? <p className="text-slate-500">None yet</p> : null}
            </div>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Peer Comparison</h2>
            <div className="space-y-2 text-sm max-h-56 overflow-auto">
              {peers.map((p) => (
                <div key={p.symbol} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="font-medium">{p.symbol}</p>
                  <p className="text-xs text-slate-500">
                    P/E {p.pe} · EV/EBITDA {p.ev_ebitda} · ROE {pct(p.roe)}
                  </p>
                </div>
              ))}
              {!peers.length ? <p className="text-slate-500">None yet</p> : null}
            </div>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Latest Valuations</h2>
            <div className="space-y-2 text-sm max-h-48 overflow-auto">
              {latest.slice(0, 8).map((v) => (
                <div key={v.valuation_id} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="font-medium">
                    {v.company_symbol} · ₹{v.intrinsic_value}
                  </p>
                  <p className="text-xs text-slate-500">
                    {v.fiscal_year} v{v.version} · {v.margin_of_safety?.label || '—'}
                  </p>
                </div>
              ))}
              {!latest.length ? <p className="text-slate-500">No valuations yet</p> : null}
            </div>
            <p className="text-xs text-slate-500 mt-3">
              Status: {health?.status || '—'} · {health?.architecture_status || ''}
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
