import { useCallback, useEffect, useState } from 'react';
import { Layers, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  analyseInstitutionalStack,
  bootstrapInstitutionalStack,
  getInstitutionalStackCompany,
  getInstitutionalStackDashboard,
  getInstitutionalStackHealth,
  getInstitutionalStackQualityGates,
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

export default function InstitutionalStack() {
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
        getInstitutionalStackHealth(),
        getInstitutionalStackDashboard(),
        getInstitutionalStackQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Institutional Stack');
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
      await analyseInstitutionalStack(ticker || 'HDFCBANK');
      const pack = await getInstitutionalStackCompany(ticker || 'HDFCBANK');
      setCompany(pack);
      await load();
    } catch (err) {
      setError(err?.message || 'Analyse failed');
    } finally {
      setBusy('');
    }
  };

  const onBootstrap = async () => {
    setBusy('bootstrap');
    setError('');
    try {
      await bootstrapInstitutionalStack();
      await load();
      const pack = await getInstitutionalStackCompany(ticker || 'HDFCBANK');
      setCompany(pack);
    } catch (err) {
      setError(err?.message || 'Bootstrap failed');
    } finally {
      setBusy('');
    }
  };

  const layerHealth = dashboard?.layer_health || {};
  const summary = company?.summary || dashboard?.sample_summary || {};
  const layers = company?.layers || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-teal-700 font-semibold">
            Institutional Intelligence Stack · soft integration
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Layers className="h-6 w-6 text-teal-700" />
            FIL → FDI → MII → EIL → PIL
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Ingests filings, runs what-changed and management trust, and feeds analysts, Ask AGI,
            Mission Control and IRS. Not a new engine — soft wiring only.
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
            {busy === 'analyse' ? 'Analysing…' : 'Refresh ticker'}
          </Button>
          <Button variant="outline" onClick={onBootstrap} disabled={!!busy}>
            {busy === 'bootstrap' ? 'Seeding…' : 'Bootstrap seed'}
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
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version || 'iis'} />
        <Stat
          label="Seed docs"
          value={dashboard?.seed?.document_count ?? '—'}
          hint="FIL corpus"
        />
        <Stat
          label="MII confidence"
          value={summary.management_confidence ?? '—'}
          hint={summary.management_dna ? `DNA: ${summary.management_dna}` : 'Management trust'}
        />
        <Stat
          label="Quality gates"
          value={gates?.passed ? 'Pass' : 'Review'}
          hint={gates?.passed ? 'All checks green' : 'Inspect checks'}
        />
        <Stat
          label="Layers"
          value={Object.keys(layerHealth).length || '—'}
          hint="EIL PIL FIL FDI MII"
        />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <h2 className="font-semibold text-slate-900">Layer health</h2>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-sm">
          {Object.entries(layerHealth).map(([key, row]) => (
            <div
              key={key}
              className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2"
            >
              <span className="text-slate-700">{key.replaceAll('_', ' ')}</span>
              <span className={row?.enabled === false ? 'text-amber-600' : 'text-emerald-600'}>
                {row?.enabled === false ? 'Off' : 'On'}
              </span>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-500">
          Pipeline: {(dashboard?.pipeline || health?.pipeline || []).join(' → ')}
        </p>
      </div>

      {company ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
            <h2 className="font-semibold text-slate-900">{company.ticker} summary</h2>
            <ul className="text-sm text-slate-600 space-y-1">
              <li>Management DNA: {summary.management_dna || '—'}</li>
              <li>Trust score: {summary.management_confidence ?? '—'}</li>
              <li>Filing found: {String(summary.filing_found ?? '—')}</li>
              <li>Material change signal: {String(summary.material_change_signal ?? '—')}</li>
            </ul>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
            <h2 className="font-semibold text-slate-900">Soft slices present</h2>
            <ul className="text-sm text-slate-600 space-y-1">
              {Object.keys(layers).map((k) => (
                <li key={k}>
                  {k.replaceAll('_', ' ')} —{' '}
                  <span className="text-emerald-700">
                    {layers[k]?.enabled === false ? 'missing' : 'loaded'}
                  </span>
                </li>
              ))}
            </ul>
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
