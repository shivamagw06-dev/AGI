import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Pause, Play, RefreshCw, Zap } from 'lucide-react';
import {
  getFinancialCoverage,
  getFwcpImportBoard,
  getMissingShareCount,
  getMissingStatements,
  postFwcpImportResume,
  postFwcpImportRetry,
  postFwcpImportRun,
  postFwcpImportStart,
  postFwcpImportStop,
} from '@/lib/warehouseApi';
import './valuationPolicy.css';

function fmt(n, d = 0) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: d });
}

function pctClass(value, target) {
  if (value == null) return '';
  if (value >= target) return 'ok';
  if (value >= target * 0.75) return 'warn';
  return 'bad';
}

function Stat({ label, value, hint, tone }) {
  return (
    <div className={`vp-stat ${tone || ''}`}>
      <span className="label">{label}</span>
      <span className="value">{value ?? '—'}</span>
      {hint ? <span className="vp-muted" style={{ fontSize: '0.75rem' }}>{hint}</span> : null}
    </div>
  );
}

export default function FinancialWarehouse() {
  const [board, setBoard] = useState(null);
  const [coverage, setCoverage] = useState(null);
  const [missing, setMissing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [b, c, ms, msc] = await Promise.all([
        getFwcpImportBoard(),
        getFinancialCoverage(),
        getMissingStatements(25),
        getMissingShareCount(25),
      ]);
      setBoard(b);
      setCoverage(c);
      setMissing({ statements: ms, shares: msc });
      setError(null);
    } catch (err) {
      setError(String(err?.message || err));
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 20000);
    return () => clearInterval(id);
  }, [refresh]);

  const act = async (label, fn) => {
    setBusy(true);
    setNote(null);
    try {
      const out = await fn();
      if (out?.already_running) {
        setNote('Import worker already running — coverage will keep updating.');
      } else if (out?.ok === false) {
        setNote(`${label} failed: ${out.error || 'unknown'}`);
      } else {
        setNote(
          label === 'start' || label === 'resume'
            ? 'Import started. It fills statements and share counts — leave this page open or come back later.'
            : label === 'stop'
              ? 'Import paused. Finished companies stay finished.'
              : `${label}: ok`,
        );
      }
      await refresh();
    } catch (err) {
      setError(String(err?.message || err));
    } finally {
      setBusy(false);
    }
  };

  const runtimeStatus = board?.runtime?.status || 'idle';
  const isRunning = runtimeStatus === 'running';
  const metrics = coverage?.metrics || board?.progress || {};
  const targets = coverage?.targets || board?.targets || {};
  const counts = coverage?.counts || {};
  const financialPct = Number(metrics.company_financial_pct || 0);

  return (
    <div className="vp-root">
      <div className="vp-shell">
        <Link to="/admin" className="vp-back"><ArrowLeft size={16} /> Admin</Link>

        <p className="vp-kicker">Phase 7.4F · Warehouse foundation</p>
        <h1 className="vp-title">Financial Warehouse</h1>
        <p className="vp-sub">
          {board?.what_this_does
            || 'Completes statements, share counts, ownership and consensus so HVIE and research engines stop stalling on missing inputs. Never imports vendor historical PE/PB/EV.'}
        </p>
        <p className="vp-sub">
          Measure depth and run the Yahoo-first fill on{' '}
          <Link to="/admin/financial-coverage">Financial Coverage Audit</Link>
          {' '}(thin records → AGI enrichment for long-history coverage).
        </p>

        <div className="hr-actions">
          <button
            type="button"
            className="hr-btn primary"
            disabled={busy || isRunning}
            onClick={() => act('start', () => postFwcpImportStart({ batch: 15 }))}
          >
            <Play size={14} /> {isRunning ? 'Running…' : 'Start import'}
          </button>
          <button
            type="button"
            className="hr-btn"
            disabled={busy}
            onClick={() => act('resume', () => postFwcpImportResume({ batch: 15 }))}
          >
            <RefreshCw size={14} /> Resume
          </button>
          <button
            type="button"
            className="hr-btn"
            disabled={busy}
            onClick={() => act('run', () => postFwcpImportRun({ batch: 5 }))}
          >
            <Zap size={14} /> Run 5 now
          </button>
          <button
            type="button"
            className="hr-btn"
            disabled={busy}
            onClick={() => act('retry', () => postFwcpImportRetry({ limit: 40 }))}
          >
            Retry queue
          </button>
          <button
            type="button"
            className="hr-btn ghost"
            disabled={busy || !isRunning}
            onClick={() => act('stop', postFwcpImportStop)}
          >
            <Pause size={14} /> Stop
          </button>
          <button type="button" className="hr-btn ghost" disabled={busy} onClick={refresh}>
            Refresh
          </button>
        </div>

        {error ? <div className="vp-error">{error}</div> : null}
        {note ? <p className="hr-note">{note}</p> : null}

        <section className="hr-hero">
          <div className="hr-hero-top">
            <div>
              <span className={`hr-status ${isRunning ? 'on' : runtimeStatus === 'stopped' ? 'off' : 'idle'}`}>
                {isRunning ? 'Importing' : runtimeStatus === 'stopped' ? 'Paused' : 'Idle'}
              </span>
              <p className="hr-plain">
                {coverage?.plain_english || board?.plain_english || 'Loading coverage…'}
              </p>
            </div>
            <div className="hr-pct">
              <strong>{fmt(financialPct, 1)}%</strong>
              <span>financial coverage</span>
            </div>
          </div>
          <div className="hr-bar" aria-hidden="true">
            <div className="hr-bar-fill" style={{ width: `${Math.min(100, Math.max(0, financialPct))}%` }} />
          </div>
          <p className="vp-muted hr-bar-caption">
            Target ≥{fmt(targets.company_financial_pct || 95)}% company financial coverage ·
            HVIE complete target ≥{fmt(targets.hvie_complete_pct || 90)}%
          </p>
        </section>

        <section className="vp-stats">
          <Stat label="Universe" value={fmt(coverage?.universe)} hint="company_master" />
          <Stat
            label="Annual"
            value={`${fmt(metrics.annual_pct, 1)}%`}
            hint={`target ≥${fmt(targets.annual_pct)}%`}
            tone={pctClass(metrics.annual_pct, targets.annual_pct || 95)}
          />
          <Stat
            label="Quarterly"
            value={`${fmt(metrics.quarterly_pct, 1)}%`}
            hint={`target ≥${fmt(targets.quarterly_pct)}%`}
            tone={pctClass(metrics.quarterly_pct, targets.quarterly_pct || 95)}
          />
          <Stat
            label="Share counts"
            value={`${fmt(metrics.share_count_pct, 1)}%`}
            hint={`target ≥${fmt(targets.share_count_pct)}%`}
            tone={pctClass(metrics.share_count_pct, targets.share_count_pct || 99)}
          />
          <Stat
            label="Consensus"
            value={`${fmt(metrics.consensus_pct, 1)}%`}
            hint={`target ≥${fmt(targets.consensus_pct)}%`}
          />
          <Stat
            label="Ownership"
            value={`${fmt(metrics.ownership_pct, 1)}%`}
            hint={`target ≥${fmt(targets.ownership_pct)}%`}
          />
          <Stat
            label="HVIE ready"
            value={`${fmt(metrics.hvie_eligible_pct, 1)}%`}
            hint={`${fmt(counts.hvie_ready)} companies`}
          />
          <Stat
            label="HVIE complete"
            value={`${fmt(metrics.hvie_complete_pct, 1)}%`}
            hint={`${fmt(counts.hvie_complete)} finished`}
            tone={pctClass(metrics.hvie_complete_pct, targets.hvie_complete_pct || 90)}
          />
        </section>

        <div className="hr-grid">
          <section className="hr-panel">
            <h2>Missing statements (sample)</h2>
            <p className="vp-muted">
              Annual gaps: {fmt(missing?.statements?.counts?.missing_annual)} ·
              Quarterly gaps: {fmt(missing?.statements?.counts?.missing_quarterly)}
            </p>
            <ul className="hr-stages">
              {(missing?.statements?.missing_annual || []).slice(0, 12).map((row) => (
                <li key={`a-${row.symbol}`}>
                  <div>
                    <strong>{row.symbol}</strong>
                    <span className="vp-muted">{row.company_name || row.sector || '—'}</span>
                  </div>
                  <em>{fmt(row.annual_rows)} yr</em>
                </li>
              ))}
            </ul>
          </section>
          <section className="hr-panel">
            <h2>Missing share counts (sample)</h2>
            <p className="vp-muted">
              {fmt(missing?.shares?.count)} companies without usable share counts
            </p>
            <ul className="hr-stages">
              {(missing?.shares?.rows || []).slice(0, 12).map((row) => (
                <li key={`s-${row.symbol}`}>
                  <div>
                    <strong>{row.symbol}</strong>
                    <span className="vp-muted">{row.company_name || row.isin || '—'}</span>
                  </div>
                  <em>need shares</em>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <section className="hr-panel" style={{ marginTop: '1.25rem' }}>
          <h2>Coverage by sector</h2>
          <ul className="hr-stages">
            {(coverage?.by_sector || []).slice(0, 15).map((row) => (
              <li key={row.sector}>
                <div>
                  <strong>{row.sector}</strong>
                  <span className="vp-muted">
                    {fmt(row.companies)} cos · annual {fmt(row.annual_pct, 1)}% ·
                    shares {fmt(row.share_count_pct, 1)}%
                  </span>
                </div>
                <em>{fmt(row.hvie_ready_pct, 1)}% ready</em>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
