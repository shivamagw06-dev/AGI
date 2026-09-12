import { useCallback, useEffect, useState } from 'react';
import { FileSpreadsheet, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  getFdoAlerts,
  getFdoDashboard,
  getFdoSchedule,
  getFseCoverageCompany,
  getFseHealth,
  getFseSourceCoverage,
  getFseSourceHealth,
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

export default function FinancialStatementsEngine() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [sourceHealth, setSourceHealth] = useState(null);
  const [sourceCoverage, setSourceCoverage] = useState(null);
  const [company, setCompany] = useState(null);
  const [ticker, setTicker] = useState('TCS');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, s, a, sh] = await Promise.all([
        getFseHealth(),
        getFdoDashboard('gold'),
        getFdoSchedule('gold'),
        getFdoAlerts('gold'),
        getFseSourceHealth(),
      ]);
      setHealth(h);
      setDashboard(d);
      setSchedule(s);
      setAlerts(a);
      setSourceHealth(sh);
      try {
        setSourceCoverage(await getFseSourceCoverage());
      } catch {
        setSourceCoverage(null);
      }
    } catch (err) {
      setError(err?.message || 'Failed to load Financial Statements Engine');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onCoverage = async () => {
    setBusy('coverage');
    setError('');
    try {
      setCompany(await getFseCoverageCompany(ticker || 'TCS'));
    } catch (err) {
      setError(err?.message || 'Coverage lookup failed');
    } finally {
      setBusy('');
    }
  };

  const growth = dashboard?.raw_evidence_growth || {};
  const alertRows = alerts?.alerts || dashboard?.alerts || [];
  const queue = schedule?.queue || dashboard?.gap_schedule || [];
  const sources = sourceHealth?.sources || dashboard?.source_health || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-teal-800 font-semibold">
            Financial Statements Engine · FDO Phase 1 · soft-wire
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <FileSpreadsheet className="h-6 w-6 text-teal-800" />
            Coverage, freshness, throughput, reliability
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Operate the existing FSE pipeline at scale — Raw Evidence growth, gap schedule, source
            health. No BUY/SELL. No engine redesign.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-36"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
          />
          <Button variant="outline" onClick={onCoverage} disabled={!!busy}>
            {busy === 'coverage' ? 'Loading…' : 'Company coverage'}
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
        <Stat label="FSE status" value={health?.status ?? '—'} hint={health?.version || 'fse'} />
        <Stat
          label="Coverage %"
          value={dashboard?.coverage_pct ?? '—'}
          hint="Universe average"
        />
        <Stat
          label="Completeness %"
          value={dashboard?.completeness_pct ?? '—'}
          hint="Checklist average"
        />
        <Stat
          label="Queue / DLQ"
          value={`${dashboard?.queue_depth ?? '—'} / ${dashboard?.dlq_size ?? '—'}`}
          hint="Workflow depth"
        />
        <Stat
          label="Raw evidence"
          value={growth.files ?? '—'}
          hint={growth.storage_mb != null ? `${growth.storage_mb} MB` : 'files'}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-slate-900">Gap schedule (largest gaps first)</h2>
          <ul className="space-y-2 text-slate-600 max-h-72 overflow-auto">
            {(queue || []).slice(0, 12).map((row) => (
              <li
                key={row.ticker}
                className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2"
              >
                <span className="font-medium text-slate-800">{row.ticker}</span>
                <span className="text-xs text-slate-500">
                  score {row.score ?? '—'} · cov {row.coverage_pct ?? '—'}%
                </span>
              </li>
            ))}
            {!queue?.length ? <li className="text-slate-400">No schedule rows</li> : null}
          </ul>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-slate-900">Operational alerts</h2>
          <ul className="space-y-2 text-slate-600 max-h-72 overflow-auto">
            {alertRows.map((a, idx) => (
              <li
                key={`${a.code}-${idx}`}
                className="flex items-start justify-between gap-3 border border-slate-100 rounded-lg px-3 py-2"
              >
                <span>
                  <span className="font-medium text-slate-800">{a.code}</span>
                  <span className="block text-xs text-slate-500">{a.message}</span>
                </span>
                <span className="text-[10px] uppercase text-slate-400">{a.severity}</span>
              </li>
            ))}
            {!alertRows.length ? <li className="text-slate-400">No alerts</li> : null}
          </ul>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <h2 className="font-semibold text-slate-900">Source health</h2>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {(sources || []).map((s) => (
            <div
              key={s.source_id}
              className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2"
            >
              <span className="text-slate-700">{s.source_name || s.source_id}</span>
              <span className="text-xs text-slate-500">
                {s.availability || s.status || '—'}
                {s.success_pct != null ? ` · ${s.success_pct}% ok` : ''}
              </span>
            </div>
          ))}
          {!sources?.length ? (
            <p className="text-slate-400 text-sm">No source metrics yet</p>
          ) : null}
        </div>
        {sourceCoverage ? (
          <p className="text-xs text-slate-400">
            Official registry sources:{' '}
            {sourceCoverage.n ?? sourceCoverage.sources_n ?? (sourceCoverage.sources || []).length}{' '}
            · FSE-02.3 soft board
          </p>
        ) : null}
      </div>

      {company ? (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
          <h2 className="font-semibold text-slate-900">{company.ticker} completeness</h2>
          <p className="text-slate-600">
            Overall {company.overall_completeness_pct ?? '—'}% · coverage{' '}
            {company.coverage?.coverage_pct ?? '—'}%
          </p>
          <ul className="grid gap-1 sm:grid-cols-2">
            {(company.checklist || []).map((c) => (
              <li key={c.label} className="flex justify-between border border-slate-100 rounded px-3 py-1.5">
                <span>{c.label}</span>
                <span className="text-slate-500">{c.status}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
