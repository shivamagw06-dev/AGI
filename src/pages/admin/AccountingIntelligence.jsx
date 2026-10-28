import { useCallback, useEffect, useState } from 'react';
import { Scale, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  analyseAci,
  getAciCompany,
  getAciDashboard,
  getAciHealth,
  getAciQualityGates,
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

export default function AccountingIntelligence() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [company, setCompany] = useState(null);
  const [ticker, setTicker] = useState('HDFCBANK');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getAciHealth(),
        getAciDashboard(),
        getAciQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Accounting Intelligence');
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
      await analyseAci(ticker || 'HDFCBANK');
      const pack = await getAciCompany(ticker || 'HDFCBANK');
      setCompany(pack);
      await load();
    } catch (err) {
      setError(err?.message || 'Analyse failed');
    } finally {
      setBusy('');
    }
  };

  const report = company?.report || {};
  const aq = report.accounting_quality || {};
  const behaviour = company?.behaviour || {};
  const forensic = company?.forensic || {};
  const manipulation = company?.manipulation || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-rose-700 font-semibold">
            Accounting Intelligence Engine v1.0 · soft layer
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Scale className="h-6 w-6 text-rose-700" />
            Can the statements be trusted?
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Earnings quality, cash conversion, accruals, revenue recognition, forensic models and
            accounting behaviour — not ratio printing.
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
            {busy === 'analyse' ? 'Analysing…' : 'Run ACI'}
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
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version || 'aci'} />
        <Stat label="Profiles" value={(dashboard?.profiles || []).length || '—'} />
        <Stat
          label="Quality score"
          value={aq.score ?? '—'}
          hint={behaviour.primary ? `Behaviour: ${behaviour.primary}` : 'Run ticker'}
        />
        <Stat
          label="Manipulation"
          value={manipulation.manipulation_risk ?? '—'}
          hint={`${manipulation.alert_count ?? 0} alerts`}
        />
        <Stat
          label="Quality gates"
          value={gates?.passed ? 'Pass' : 'Review'}
          hint={gates?.passed ? 'IRS-ready checks' : 'Inspect checks'}
        />
      </div>

      {company ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">{company.ticker} accounting desk</h2>
            <p className="text-slate-600">{report.executive_summary}</p>
            <ul className="space-y-1 text-slate-600">
              <li>Cash quality: {aq.cash_quality ?? '—'}</li>
              <li>Earnings quality: {aq.earnings_quality ?? '—'} ({company.earnings?.label})</li>
              <li>Accruals: {company.accruals?.label}</li>
              <li>
                Beneish M: {(forensic.beneish || {}).beneish_m ?? '—'} · Piotroski F:{' '}
                {(forensic.piotroski || {}).piotroski_f ?? '—'}
              </li>
            </ul>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Open concerns</h2>
            <ul className="space-y-1 text-slate-600">
              {(company.open_concerns || []).length
                ? company.open_concerns.map((c) => <li key={c}>• {c}</li>)
                : <li>None flagged</li>}
            </ul>
            <p className="text-xs text-slate-400 mt-3">{behaviour.narrative}</p>
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
