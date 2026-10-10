import { useCallback, useEffect, useState } from 'react';
import { Activity, AlertTriangle, RefreshCw, Trophy } from 'lucide-react';
import {
  getInstitutionalIntelligenceSnapshot,
  runDecisionQuality,
  runHistoricalDepth,
  runInstitutionalKnowledgeStack,
  runMacroIntelligence,
  runSectorIntelligence,
  runUniverseIntelligence,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function Stat({ label, value, hint }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1 text-slate-900 tabular-nums">{value ?? '—'}</p>
      {hint ? <p className="text-xs text-slate-400 mt-1">{hint}</p> : null}
    </div>
  );
}

function pct(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  return n <= 1 && n >= 0 ? `${Math.round(n * 1000) / 10}%` : `${Math.round(n * 10) / 10}`;
}

function LayerChip({ name, status }) {
  const ok = status === 'ok';
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
        ok ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-100 text-slate-600'
      }`}
    >
      {name}
      <span className="ml-1 opacity-70">{ok ? 'ready' : status || '—'}</span>
    </span>
  );
}

export default function InstitutionalIntelligence() {
  const [health, setHealth] = useState(null);
  const [hd, setHd] = useState(null);
  const [isi, setIsi] = useState(null);
  const [imi, setImi] = useState(null);
  const [idq, setIdq] = useState(null);
  const [hall, setHall] = useState(null);
  const [iui, setIui] = useState(null);
  const [iks, setIks] = useState(null);
  const [ieri, setIeri] = useState(null);
  const [iadi, setIadi] = useState(null);
  const [imei, setImei] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async ({ quiet } = {}) => {
    if (!quiet) setLoading(true);
    setError('');
    try {
      // Snapshot reader only — no parallel dashboard fan-out on page open.
      const snap = await getInstitutionalIntelligenceSnapshot();
      const boards = snap?.boards || {};
      setHealth(boards.health || null);
      setHd(boards.historical_depth || null);
      setIsi(boards.sector || null);
      setImi(boards.macro || null);
      setIdq(boards.decision_quality || null);
      setHall(boards.hall || null);
      setIui(boards.universe || null);
      setIks(boards.institutional_knowledge || null);
      setIeri(boards.relationship || null);
      setIadi(boards.alternative_data || null);
      setImei(boards.expectations || null);
      if (snap?._warming || snap?.status === 'warming') {
        setError(snap?.message || 'Institutional Intelligence is warming up — worker building first snapshot.');
      }
    } catch (err) {
      setError(err?.message || 'Failed to load Institutional Intelligence snapshot');
    } finally {
      if (!quiet) setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // Poll cached snapshot only while mounted.
    const t = window.setInterval(() => load({ quiet: true }), 90_000);
    return () => window.clearInterval(t);
  }, [load]);

  const runAll = async () => {
    setBusy('run');
    setError('');
    try {
      await Promise.allSettled([
        runUniverseIntelligence({ universe_id: 'NIFTY_500', force_full: false }),
        runHistoricalDepth(),
        runSectorIntelligence(),
        runMacroIntelligence(),
        runDecisionQuality(),
        runInstitutionalKnowledgeStack({ ensure_only_missing: true }),
      ]);
      await load();
    } catch (err) {
      setError(err?.message || 'Pipeline run failed');
    } finally {
      setBusy('');
    }
  };

  const dc = health?.decision_coverage || {};
  const idqKpi = idq?.kpi || {};
  const imiKpi = imi?.kpi || imi || {};
  const fame = hall?.hall_of_fame || [];
  const shame = hall?.hall_of_shame || [];
  const iuiCov = iui?.coverage || health?.universe_intelligence || {};
  const leaders = iui?.ici_leaders || [];
  const summary = iks?.summary || {};
  const reality = iks?.reality || {};
  const expectations = iks?.expectations || {};
  const relCov = ieri?.economic_relationship_coverage || {};
  const altCov = iadi?.alternative_data_coverage || {};
  const expCov = imei?.expectation_dashboard || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-700 font-semibold">
            AGIB v2.0 · Institutional Knowledge Stack
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Activity className="h-6 w-6 text-slate-800" />
            Institutional Intelligence
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Reality (companies → industries → relationships → alt data) + Expectations (guidance,
            revisions, surprises). Soft Knowledge Factory only — Phases 1–7 frozen. Snapshot-backed
            (poll 90s) — page open never fans out live dashboards.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => load()} disabled={loading || !!busy}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Check snapshot
          </Button>
          <Button onClick={runAll} disabled={!!busy || loading}>
            {busy ? 'Running…' : 'Prime / Run stack'}
          </Button>
        </div>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Knowledge Stack"
          value={
            summary.stack_complete
              ? 'Complete'
              : `${summary.reality_layers_ok ?? '—'}/${7}R · ${summary.expectation_layers_ok ?? '—'}/1E`
          }
          hint="Reality + Expectations"
        />
        <Stat
          label="Relationships"
          value={relCov.relationships ?? '—'}
          hint={`${relCov.commodities ?? '—'} commodities`}
        />
        <Stat
          label="Alt-Data Datasets"
          value={altCov.datasets ?? '—'}
          hint={`${altCov.observations ?? '—'} observations`}
        />
        <Stat
          label="Expectation Surprises"
          value={expCov.surprises ?? '—'}
          hint={`${expCov.narratives ?? '—'} narratives`}
        />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="text-sm font-semibold text-slate-800 mb-3">Stack layers</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(reality).map(([k, v]) => (
            <LayerChip key={k} name={k} status={v?.status} />
          ))}
          {Object.entries(expectations).map(([k, v]) => (
            <LayerChip key={`e-${k}`} name={`expectations:${k}`} status={v?.status} />
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Avg ICI (Nifty 500)"
          value={iuiCov.avg_ici != null ? Number(iuiCov.avg_ici).toFixed(1) : '—'}
          hint="Institutional Coverage Index"
        />
        <Stat
          label="Institutional Coverage"
          value={pct(iuiCov.institutional_coverage_pct)}
          hint={`${iuiCov.institutional_coverage ?? iuiCov.institutional_coverage_n ?? '—'} / 500 Level-7`}
        />
        <Stat
          label="Decision Ready"
          value={pct(iuiCov.decision_ready_pct ?? dc.nifty_500)}
          hint={dc.nifty_500_note || 'Universe Health'}
        />
        <Stat
          label="Gate Failures"
          value={iui?.failure_count ?? health?.universe_intelligence?.failure_count ?? '—'}
          hint={`Stale ${iui?.stale_count ?? health?.universe_intelligence?.stale_count ?? '—'}`}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Nifty 100 Decision Coverage" value={pct(dc.nifty_100)} hint="Tier 1" />
        <Stat label="Nifty 500 Decision Coverage" value={pct(dc.nifty_500)} hint="Tier 2" />
        <Stat
          label="Historical Depth ≥20y"
          value={pct(hd?.companies_gt_20y_pct)}
          hint={`Avg years ${hd?.average_history_years ?? '—'}`}
        />
        <Stat
          label="Sector / Macro"
          value={pct(isi?.sector_coverage_pct)}
          hint={`Macro ${imiKpi?.coverage != null ? Number(imiKpi.coverage).toFixed(2) : '—'}`}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
            <Trophy className="h-4 w-4 text-amber-600" />
            ICI Leaders
          </h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {leaders.length === 0 ? (
              <li className="text-slate-400">No ICI board yet — run Universe Intelligence.</li>
            ) : null}
            {leaders.slice(0, 8).map((e) => (
              <li key={e.ticker} className="border-b border-slate-100 pb-2 flex justify-between gap-3">
                <span className="font-medium">{e.ticker}</span>
                <span className="tabular-nums text-slate-600">
                  {Number(e.ici).toFixed(1)} · {e.band}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-800">Hall of Fame / Shame</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {fame.length === 0 && shame.length === 0 ? (
              <li className="text-slate-400">No IDQ classifications yet — run Decision Quality.</li>
            ) : null}
            {fame.slice(0, 3).map((e) => (
              <li key={`f-${e.decision_id}`} className="border-b border-slate-100 pb-2">
                <span className="font-medium">{e.entity}</span>
                <span className="text-slate-400"> · fame · {e.category}</span>
              </li>
            ))}
            {shame.slice(0, 3).map((e) => (
              <li key={`s-${e.decision_id}`} className="border-b border-slate-100 pb-2">
                <span className="font-medium">{e.entity}</span>
                <span className="text-slate-400"> · shame · {e.category}</span>
              </li>
            ))}
            <li className="text-xs text-slate-400 pt-2">
              Decision Quality coverage:{' '}
              {idqKpi?.coverage != null ? Number(idqKpi.coverage).toFixed(1) : '—'}
            </li>
          </ul>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 text-sm text-slate-600">
        <p>
          Roadmap next:{' '}
          <span className="font-semibold text-slate-900">
            {iks?.roadmap_next || health?.roadmap_next || '—'}
          </span>
        </p>
        <p className="mt-1 text-xs text-slate-400">
          Soft Knowledge Factory stack. Reasoning, governance, and planners remain frozen.
        </p>
      </div>
    </div>
  );
}
