import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, ArrowLeft, Play, RefreshCw, Square } from 'lucide-react';
import {
  bootstrapDataset,
  getUifiBootstrapStatus,
  getUifiCoverage,
  getUifiFailures,
  getUifiSchedulerStatus,
  runUpstoxEmptyFill,
  startUifiBootstrap,
  stopUifiBootstrap,
} from '@/lib/uifiApi';
import './upstoxBootstrap.css';

function fmt(n) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString();
}

function Stat({ label, value, hint }) {
  return (
    <div className="ub-stat">
      <span className="label">{label}</span>
      <span className="value">{value}</span>
      {hint ? <span className="ub-muted">{hint}</span> : null}
    </div>
  );
}

export default function UpstoxFundamentals() {
  const [coverage, setCoverage] = useState(null);
  const [status, setStatus] = useState(null);
  const [scheduler, setScheduler] = useState(null);
  const [failures, setFailures] = useState([]);
  const [error, setError] = useState(null);
  const [note, setNote] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [cov, st, sch, fail] = await Promise.all([
        getUifiCoverage(),
        getUifiBootstrapStatus(),
        getUifiSchedulerStatus(),
        getUifiFailures(),
      ]);
      setCoverage(cov);
      setStatus(st);
      setScheduler(sch);
      setFailures(fail?.rows || []);
      setError(null);
    } catch (err) {
      setError(err.message || 'load_failed');
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  const running = status?.status === 'running';

  const onStartAll = async () => {
    setBusy(true);
    try {
      const r = await startUifiBootstrap({ dataset: 'all', reset: false });
      setNote(r.ok ? 'UIFI bootstrap started (profile → statements → ownership → peers → CA).' : r.error);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onDataset = async (dataset) => {
    setBusy(true);
    try {
      const r = await bootstrapDataset(dataset, {});
      setNote(r.ok ? `Bootstrap started for ${dataset}` : r.error);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onStop = async () => {
    setBusy(true);
    try {
      await stopUifiBootstrap();
      setNote('Stop requested.');
      await load();
    } finally {
      setBusy(false);
    }
  };

  const onAnnualBackfill = async () => {
    setBusy(true);
    setNote(null);
    try {
      const result = await runUpstoxEmptyFill({ batch: 10 });
      const batch = result?.batch || {};
      setNote(
        result?.ok
          ? `Annual backfill finished: ${batch.filled || 0} companies filled, ${batch.failed || 0} need review.`
          : (result?.error || 'Annual backfill did not complete.'),
      );
      await load();
    } catch (err) {
      setError(err.message || 'annual_backfill_failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="ub-root">
      <header className="ub-header">
        <div>
          <Link to="/admin" className="ub-back">
            <ArrowLeft size={14} /> Admin
          </Link>
          <h1>AGI Institutional Fundamentals</h1>
          <p className="ub-muted">
            Warehouse-first AGI fundamentals integration. AGI manages structured fundamentals;
            AGI manages corporate actions and products through its internal data layer.
          </p>
        </div>
        <div className="ub-actions">
          <button type="button" disabled={busy || running} onClick={onStartAll}>
            <Play size={14} /> Bootstrap all
          </button>
          <button type="button" disabled={busy || running} onClick={onAnnualBackfill}>
            <Play size={14} /> Run 10-company annual backfill
          </button>
          <button type="button" disabled={busy || !running} onClick={onStop}>
            <Square size={14} /> Stop
          </button>
          <button type="button" disabled={busy} onClick={load}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </header>

      {error ? <div className="ub-banner err">{error}</div> : null}
      {note ? <div className="ub-banner">{note}</div> : null}

      <section className="ub-panel">
        <h2>Four-year company financial backfill</h2>
        <p className="ub-muted">
          Runs only eligible stocks that are missing annual statements. Each company runs through AGI financial collection:
          Income Statement, Balance Sheet, and Cash Flow. ETFs and funds are skipped.
        </p>
      </section>

      <section className="ub-grid">
        <Stat label="Companies" value={fmt(coverage?.companies)} />
        <Stat label="With ISIN" value={fmt(coverage?.with_isin)} hint={`${coverage?.isin_coverage_pct ?? '—'}%`} />
        <Stat label="Instrument keys" value={fmt(coverage?.with_instrument_key)} />
        <Stat label="Profiles" value={fmt(coverage?.profiles)} hint={`${fmt(coverage?.profile_symbols)} symbols`} />
        <Stat label="Annual statements" value={fmt(coverage?.statements_annual)} />
        <Stat label="Quarterly statements" value={fmt(coverage?.statements_quarterly)} />
        <Stat label="Ownership" value={fmt(coverage?.ownership)} />
        <Stat label="Competitors" value={fmt(coverage?.competitors)} />
        <Stat label="Corporate actions (AGI)" value={fmt(coverage?.corporate_actions)} hint="secondary" />
        <Stat label="Key ratios" value={fmt(coverage?.valuation_ratios)} />
      </section>

      <section className="ub-panel">
        <h2><Activity size={16} /> Runtime</h2>
        <div className="ub-grid">
          <Stat label="Bootstrap" value={status?.status || '—'} />
          <Stat label="Dataset" value={status?.datasets?.[status?.datasetCursor] || '—'} />
          <Stat label="Offset" value={fmt(status?.offset)} />
          <Stat label="Batches OK" value={fmt(status?.metrics?.successBatches)} />
          <Stat label="HTTP 429" value={fmt(status?.metrics?.http429)} />
          <Stat label="Scheduler" value={scheduler?.enabled ? 'on' : 'off'} hint={scheduler?.schedules?.weekly} />
        </div>
        <div className="ub-actions" style={{ marginTop: 12 }}>
          {['profile', 'statements', 'shareholding', 'competitors', 'corporate-actions'].map((ds) => (
            <button key={ds} type="button" disabled={busy || running} onClick={() => onDataset(ds)}>
              {ds}
            </button>
          ))}
        </div>
      </section>

      <section className="ub-panel">
        <h2>Recent log</h2>
        <ul className="ub-log">
          {(status?.recentLog || []).slice(0, 20).map((row, i) => (
            <li key={i}>
              <code>{row.at}</code> {row.event} {row.dataset || ''} fetched={row.fetched ?? '—'}
              {row.error ? ` — ${row.error}` : ''}
            </li>
          ))}
        </ul>
      </section>

      <section className="ub-panel">
        <h2>DQIV / failures</h2>
        <p className="ub-muted">{failures.length} recent AGI quality rows</p>
        <ul className="ub-log">
          {failures.slice(0, 15).map((row, i) => (
            <li key={i}><code>{row.symbol || row.feed || '—'}</code> {row.notes || row.message || JSON.stringify(row).slice(0, 120)}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
