import { useCallback, useEffect, useState } from 'react';
import { Radio, AlertTriangle, RefreshCw } from 'lucide-react';
import { getYfpDashboard, getYfpHealth, getYfpQualityGates, enrichYfp, searchYfp } from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function Stat({ label, value, hint }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1 text-slate-900">{value}</p>
      {hint ? <p className="text-xs text-slate-400 mt-1">{hint}</p> : null}
    </div>
  );
}

export default function YahooProvider() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [probe, setProbe] = useState(null);
  const [searchQ, setSearchQ] = useState('HDFC Bank');
  const [hits, setHits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([getYfpHealth(), getYfpDashboard(), getYfpQualityGates()]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load YFP dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onEnrich = async () => {
    setBusy('enrich');
    setError('');
    try {
      const result = await enrichYfp('HDFCBANK');
      setProbe(result);
      await load();
    } catch (err) {
      setError(err?.message || 'Enrich failed');
    } finally {
      setBusy('');
    }
  };

  const onSearch = async () => {
    setBusy('search');
    setError('');
    try {
      const result = await searchYfp(searchQ, 8);
      setHits(result?.hits || []);
    } catch (err) {
      setError(err?.message || 'Search failed');
    } finally {
      setBusy('');
    }
  };

  const flags = dashboard?.coverage_flags || health?.flags || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-violet-600 font-semibold">
            YFP v1.0 · Yahoo Finance Institutional Provider
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Radio className="h-6 w-6 text-violet-600" />
            Provider Health — Yahoo
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Secondary MarketData adapter (priority 40). Canonical models only — never Yahoo-native payloads.
            Enriches CID / Ask AGI without overwriting higher-priority providers.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onEnrich} disabled={!!busy}>
            {busy === 'enrich' ? 'Enriching…' : 'Enrich HDFC'}
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
        <Stat label="Status" value={health?.yahoo_status || health?.status || '—'} hint={health?.version} />
        <Stat label="Priority" value={dashboard?.priority ?? 40} hint="Secondary after FMP" />
        <Stat label="Last sync" value={dashboard?.last_sync ? String(dashboard.last_sync).slice(11, 19) : '—'} />
        <Stat label="Companies updated" value={dashboard?.companies_updated ?? '—'} />
        <Stat label="Failed syncs" value={dashboard?.failed_syncs ?? '—'} hint={`Latency ${dashboard?.latency_ms ?? '—'}ms`} />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <h2 className="font-semibold text-slate-900">Feature flags</h2>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 text-sm">
          {Object.entries(flags).map(([key, ok]) => (
            <div key={key} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2">
              <span className="text-slate-600">{key}</span>
              <span className={ok ? 'text-emerald-600 font-medium' : 'text-slate-400'}>{ok ? 'On' : 'Off'}</span>
            </div>
          ))}
        </div>
      </div>

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
            <div key={key} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2">
              <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
              <span className={ok ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                {ok ? 'Yes' : 'No'}
              </span>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400">{gates?.note}</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <h2 className="font-semibold text-slate-900">Symbol search</h2>
        <div className="flex gap-2">
          <input
            className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            placeholder="Infosys / HDFC Bank"
          />
          <Button variant="outline" onClick={onSearch} disabled={!!busy}>
            Search
          </Button>
        </div>
        <ul className="text-sm space-y-1">
          {hits.map((h) => (
            <li key={h.yahoo_symbol || h.symbol} className="flex justify-between border-b border-slate-50 py-1">
              <span>
                <span className="font-medium">{h.symbol}</span>
                <span className="text-slate-400 ml-2">{h.yahoo_symbol}</span>
              </span>
              <span className="text-slate-500">{h.name}</span>
            </li>
          ))}
        </ul>
      </div>

      {probe ? (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
          <h2 className="font-semibold text-slate-900">HDFC enrich probe</h2>
          <p>Coverage: {probe.dossier?.coverage_grade} ({probe.dossier?.coverage_score})</p>
          <p>
            Quote: {probe.enrich?.has_quote ? 'Yes' : 'No'} · Fundamentals:{' '}
            {probe.enrich?.has_fundamentals ? 'Yes' : 'No'} · Events: {probe.enrich?.calendar_events ?? 0}
          </p>
          <p className="text-slate-500">KIP facts: {(probe.kip_facts || []).length}</p>
        </div>
      ) : null}
    </div>
  );
}
