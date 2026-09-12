import { useCallback, useEffect, useState } from 'react';
import { Activity, CheckCircle2, ClipboardList, Play, ShieldAlert, X } from 'lucide-react';
import { getAuditLog, listRefreshRuns, runRefresh, validateWarehouse } from '@/lib/warehouseApi';

const TABS = [
  { id: 'quality', label: 'Data quality', icon: ShieldAlert },
  { id: 'refresh', label: 'Refresh runs', icon: Activity },
  { id: 'audit', label: 'Audit trail', icon: ClipboardList },
];

export default function OpsPanel({ onClose, onRefreshed }) {
  const [view, setView] = useState('quality');
  const [quality, setQuality] = useState(null);
  const [runs, setRuns] = useState([]);
  const [audit, setAudit] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [q, r, a] = await Promise.all([
        validateWarehouse({ sample: 200 }),
        listRefreshRuns(8),
        getAuditLog({ limit: 60 }),
      ]);
      setQuality(q);
      setRuns(r?.runs || []);
      setAudit(a?.entries || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const triggerRefresh = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await runRefresh({ days: 10 });
      if (!result?.ok && result?.error) throw new Error(result.error);
      await load();
      onRefreshed?.(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="wh-drawer wh-drawer-wide">
      <header>
        <div>
          <h2>Operations</h2>
          <p>Quality, refresh pipeline and the audit trail</p>
        </div>
        <button type="button" onClick={onClose} aria-label="Close">
          <X size={15} />
        </button>
      </header>

      <div className="wh-ops-tabs">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              type="button"
              className={view === tab.id ? 'is-active' : ''}
              onClick={() => setView(tab.id)}
            >
              <Icon size={12} /> {tab.label}
            </button>
          );
        })}
        <button type="button" className="wh-btn wh-btn-primary wh-ops-run" disabled={busy} onClick={triggerRefresh}>
          <Play size={12} /> {busy ? 'Running…' : 'Run refresh'}
        </button>
      </div>

      {error ? <div className="wh-error">{error}</div> : null}

      {view === 'quality' ? (
        <section>
          <h3>
            {quality?.ok ? <CheckCircle2 size={13} /> : <ShieldAlert size={13} />}{' '}
            {quality?.failed?.length ? `${quality.failed.length} tables failing` : 'All tables passing'}
          </h3>
          <table className="wh-ops-table">
            <thead>
              <tr>
                <th>Table</th>
                <th>Rows</th>
                <th>Status</th>
                <th>Errors</th>
                <th>Warnings</th>
                <th>Freshness</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(quality?.tabs || {}).map(([id, entry]) => (
                <tr key={id} className={`is-${entry.status}`}>
                  <td>{id}</td>
                  <td className="is-num">{entry.rows?.toLocaleString?.() ?? entry.rows}</td>
                  <td>
                    <span className={`wh-pill is-${entry.status}`}>{entry.status}</span>
                  </td>
                  <td className="is-num">{entry.errors}</td>
                  <td className="is-num">{entry.warnings}</td>
                  <td>{entry.freshness}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {quality?.broken_references?.length ? (
            <p className="wh-muted">
              {quality.broken_references.length} rows reference a company that is not in Company Master.
            </p>
          ) : null}
        </section>
      ) : null}

      {view === 'refresh' ? (
        <section>
          <h3>Recent runs</h3>
          <ul className="wh-run-list">
            {runs.map((run) => (
              <li key={run.id} className={run.ok ? 'is-ok' : 'is-bad'}>
                <div className="wh-run-head">
                  <strong>{run.ok ? 'Completed' : 'Completed with errors'}</strong>
                  <span>{new Date(run.started_at).toLocaleString()}</span>
                </div>
                <div className="wh-muted">
                  {run.actor} · {run.stages?.join(' → ')}
                </div>
                {run.errors?.length ? (
                  <ul className="wh-run-errors">
                    {run.errors.map((entry) => (
                      <li key={entry.stage}>
                        {entry.stage}: {entry.error}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
            {!runs.length ? <li className="wh-muted">No refresh has run yet.</li> : null}
          </ul>
        </section>
      ) : null}

      {view === 'audit' ? (
        <section>
          <h3>Audit trail</h3>
          <ul className="wh-audit-list">
            {audit.map((entry) => (
              <li key={entry.id}>
                <span className={`wh-pill is-${entry.ok ? 'ok' : 'fail'}`}>{entry.action}</span>
                <span className="wh-audit-body">
                  <strong>{entry.actor}</strong> {entry.tab_id ? `on ${entry.tab_id}` : ''}
                  <em>{new Date(entry.created_at).toLocaleString()}</em>
                </span>
              </li>
            ))}
            {!audit.length ? <li className="wh-muted">Nothing recorded yet.</li> : null}
          </ul>
        </section>
      ) : null}
    </aside>
  );
}
