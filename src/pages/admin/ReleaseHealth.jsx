import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { RefreshCw, ShieldCheck } from 'lucide-react';
import { getReleaseHealthDashboard, runReleaseHealth } from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function Row({ label, value, ok }) {
  const tone =
    ok === true ? 'text-emerald-700' : ok === false ? 'text-red-700' : 'text-slate-500';
  return (
    <div className="flex items-baseline justify-between gap-6 border-b border-slate-200 py-3.5">
      <div className="text-[0.95rem] font-medium text-slate-800">{label}</div>
      <div className={`font-serif text-xl font-semibold tracking-tight ${tone}`}>{String(value)}</div>
    </div>
  );
}

export default function ReleaseHealth() {
  const [snapshot, setSnapshot] = useState(null);
  const [access, setAccess] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const dash = await getReleaseHealthDashboard(false);
      // Prefer unwrapped dashboard; tolerate legacy `{ ok, status, data }` BFF wrappers.
      const payload = dash?.snapshot ? dash : dash?.data || dash;
      setSnapshot(payload?.snapshot || null);
      setAccess(payload?.access || dash?.access || null);
    } catch (err) {
      setError(err?.message || 'Failed to load Release Health');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRun = async () => {
    setRunning(true);
    setError('');
    try {
      // Skip pytest by default — unit tests alone can exceed HTTP timeouts on Render.
      // Use CLI `python3 -m release_health --run` for the full gate including unit tests.
      const snap = await runReleaseHealth({ run_unit_tests: false });
      setSnapshot(snap?.snapshot || snap);
    } catch (err) {
      setError(err?.message || 'Release gate run failed');
    } finally {
      setRunning(false);
    }
  };

  const ready = snapshot?.ready_for_release;
  const rows = snapshot?.rows || [];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-slate-500 text-xs font-semibold tracking-[0.08em] uppercase">
            <ShieldCheck className="w-4 h-4" />
            Release gate
          </div>
          <h1 className="mt-1 font-serif text-3xl font-semibold tracking-tight text-slate-900">
            AGI Release Health
          </h1>
          <p className="mt-2 text-slate-600 text-sm max-w-xl">
            The one screen before every release — Build, tests, IST, IBS, E2E, hallucinations, provenance,
            regression, and Ready for Release.
          </p>
        </div>
        <Button onClick={onRun} disabled={running} className="gap-2">
          <RefreshCw className={`w-4 h-4 ${running ? 'animate-spin' : ''}`} />
          {running ? 'Running gate…' : 'Refresh Release Gate'}
        </Button>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      ) : null}

      <div
        className={`rounded-2xl border px-6 py-5 ${
          ready ? 'border-emerald-200 bg-emerald-50/60' : 'border-slate-200 bg-white'
        }`}
      >
        <div className="text-xs font-semibold tracking-[0.08em] uppercase text-slate-500">Ready for Release</div>
        <div
          className={`mt-1 font-serif text-4xl font-semibold tracking-tight ${
            ready ? 'text-emerald-800' : ready === false ? 'text-red-700' : 'text-slate-400'
          }`}
        >
          {snapshot?.ready_for_release_label || (loading ? '…' : 'NOT RUN')}
        </div>
        <div className="mt-2 text-sm text-slate-600">
          Average Benchmark{' '}
          <span className="font-semibold text-slate-900">{snapshot?.average_benchmark ?? '—'}</span>
          {snapshot?.as_of ? (
            <span className="text-slate-400"> · as of {String(snapshot.as_of).slice(0, 19)}</span>
          ) : null}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white px-6 py-2">
        {loading && !snapshot ? (
          <p className="py-8 text-center text-slate-500">Loading…</p>
        ) : rows.length ? (
          rows.map((r) => <Row key={r.label} label={r.label} value={r.value} ok={r.ok} />)
        ) : (
          <p className="py-8 text-center text-slate-500">
            No snapshot yet. Click <strong>Refresh Release Gate</strong> to run IST · IBS · E2E.
          </p>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 px-5 py-4 text-sm text-slate-600 space-y-2">
        <div className="font-semibold text-slate-800">How to access</div>
        <ul className="list-disc pl-5 space-y-1">
          <li>
            Admin UI: <Link className="text-slate-900 underline" to="/admin/release-health">/admin/release-health</Link>
          </li>
          <li>
            Product Settings: <Link className="text-slate-900 underline" to="/agi/settings">/agi/settings</Link>
          </li>
          <li>
            API: <code className="text-xs bg-white border px-1 rounded">GET /api/intelligence/release-health/dashboard</code>
          </li>
          <li>
            CLI:{' '}
            <code className="text-xs bg-white border px-1 rounded">
              cd intelligence-engine && PYTHONPATH=. python3 -m release_health --run
            </code>
          </li>
        </ul>
        {access?.cli ? <p className="text-xs text-slate-400">Engine CLI: {access.cli}</p> : null}
      </div>
    </div>
  );
}
