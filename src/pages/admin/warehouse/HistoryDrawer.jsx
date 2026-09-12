import { useCallback, useEffect, useState } from 'react';
import { GitCompare, RotateCcw, X } from 'lucide-react';
import { compareVersions, getRowHistory, restoreVersion } from '@/lib/warehouseApi';

export default function HistoryDrawer({ tab, row, onClose, onRestored }) {
  const [history, setHistory] = useState(null);
  const [diff, setDiff] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!row?.row_id) return;
    setBusy(true);
    setError(null);
    try {
      setHistory(await getRowHistory(tab.id, row.row_id));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }, [row, tab]);

  useEffect(() => {
    load();
  }, [load]);

  const showDiff = async (version) => {
    try {
      setDiff(await compareVersions(tab.id, row.row_id, version));
    } catch (err) {
      setError(err.message);
    }
  };

  const restore = async (version) => {
    setBusy(true);
    try {
      const result = await restoreVersion(tab.id, row.row_id, version);
      if (!result?.ok) throw new Error(result?.error || 'restore_failed');
      await load();
      onRestored?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const keyLabel = (tab.key || []).map((k) => row?.[k]).filter(Boolean).join(' · ');

  return (
    <aside className="wh-drawer">
      <header>
        <div>
          <h2>Version history</h2>
          <p>{keyLabel || row?.row_id}</p>
        </div>
        <button type="button" onClick={onClose} aria-label="Close">
          <X size={15} />
        </button>
      </header>

      {error ? <div className="wh-error">{error}</div> : null}
      {busy ? <div className="wh-muted">Working…</div> : null}

      <section>
        <h3>Cell changes</h3>
        {history?.cells?.length ? (
          <ul className="wh-history-list">
            {history.cells.map((entry) => (
              <li key={entry.id}>
                <div className="wh-history-head">
                  <strong>{entry.column}</strong>
                  <span>v{entry.version}</span>
                </div>
                <div className="wh-history-values">
                  <span className="old">{entry.old_value ?? '—'}</span>
                  <span className="arrow">to</span>
                  <span className="new">{entry.new_value ?? '—'}</span>
                </div>
                <div className="wh-history-meta">
                  {entry.actor} · {entry.source || 'manual'} ·{' '}
                  {new Date(entry.at).toLocaleString()}
                  {entry.reason ? ` · ${entry.reason}` : ''}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="wh-muted">No cell changes recorded yet.</p>
        )}
      </section>

      <section>
        <h3>Snapshots</h3>
        {history?.versions?.length ? (
          <ul className="wh-version-list">
            {history.versions.map((snapshot) => (
              <li key={snapshot.id}>
                <div>
                  <strong>v{snapshot.version}</strong>
                  <span className="wh-muted">
                    {snapshot.kind} · {snapshot.actor} · {new Date(snapshot.at).toLocaleString()}
                  </span>
                </div>
                <div className="wh-version-actions">
                  <button type="button" onClick={() => showDiff(snapshot.version)} title="Compare with current">
                    <GitCompare size={12} /> Diff
                  </button>
                  <button type="button" onClick={() => restore(snapshot.version)} title="Restore this version">
                    <RotateCcw size={12} /> Restore
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="wh-muted">No snapshots yet.</p>
        )}
      </section>

      {diff ? (
        <section>
          <h3>
            v{diff.from} vs {diff.to}
          </h3>
          {diff.changes?.length ? (
            <table className="wh-diff">
              <tbody>
                {diff.changes.map((change) => (
                  <tr key={change.column}>
                    <td>{change.column}</td>
                    <td className="old">{String(change.old_value ?? '—')}</td>
                    <td className="new">{String(change.new_value ?? '—')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="wh-muted">Identical.</p>
          )}
        </section>
      ) : null}
    </aside>
  );
}
