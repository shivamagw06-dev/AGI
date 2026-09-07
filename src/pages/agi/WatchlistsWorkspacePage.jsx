import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  addWatchlistOfficeCompany,
  createWatchlistOfficeWatchlist,
  getWatchlistOfficeDashboard,
  getWatchlistOfficeWatchlist,
  patchWatchlistOfficeCompany,
  removeWatchlistOfficeCompany,
} from '@/lib/intelligenceApi';

const STATUSES = ['New', 'Reviewing', 'Monitoring', 'Archived'];
const DEFAULT_ID = 'agi-research-queue';

export default function WatchlistsWorkspacePage() {
  const [watchlistId, setWatchlistId] = useState(DEFAULT_ID);
  const [entries, setEntries] = useState([]);
  const [draft, setDraft] = useState('');
  const [filter, setFilter] = useState('New');
  const [flash, setFlash] = useState('');
  const [error, setError] = useState(null);

  const refresh = useCallback(async (id) => {
    const wl = await getWatchlistOfficeWatchlist(id);
    const list = wl?.watchlist?.entries || wl?.entries || wl?.queue || [];
    setEntries(Array.isArray(list) ? list : []);
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const dash = await getWatchlistOfficeDashboard().catch(() => null);
        let id = (dash?.watchlists || []).find((w) => w.watchlist_id === DEFAULT_ID)?.watchlist_id;
        if (!id) {
          const created = await createWatchlistOfficeWatchlist({
            watchlist_id: DEFAULT_ID,
            name: 'AGI Research Queue',
            entries: [
              { ticker: 'KOTAKBANK', company: 'Kotak Mahindra Bank', status: 'Reviewing' },
              { ticker: 'ICICIBANK', company: 'ICICI Bank', status: 'Monitoring' },
            ],
          });
          id = created?.watchlist_id || created?.watchlist?.watchlist_id || DEFAULT_ID;
        }
        if (!active) return;
        setWatchlistId(id);
        await refresh(id);
      } catch (err) {
        if (active) {
          setError(err?.message || 'Watchlist office unavailable');
          setEntries([
            { ticker: 'KOTAKBANK', company: 'Kotak Mahindra Bank', status: 'Reviewing' },
            { ticker: 'ICICIBANK', company: 'ICICI Bank', status: 'Monitoring' },
          ]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [refresh]);

  const notify = (msg) => {
    setFlash(msg);
    window.setTimeout(() => setFlash(''), 1600);
  };

  const onAdd = async (e) => {
    e.preventDefault();
    const ticker = draft.trim().toUpperCase();
    if (!ticker) return;
    if (entries.some((x) => String(x.ticker).toUpperCase() === ticker)) {
      notify('Already on queue — no duplicate');
      setDraft('');
      return;
    }
    try {
      await addWatchlistOfficeCompany(watchlistId, { ticker, status: 'New' });
      await refresh(watchlistId);
      notify(`Added ${ticker}`);
    } catch {
      setEntries((prev) => [...prev, { ticker, status: 'New' }]);
      notify(`Added ${ticker} (local)`);
    }
    setDraft('');
  };

  const setStatus = async (ticker, status) => {
    try {
      await patchWatchlistOfficeCompany(watchlistId, ticker, { status });
      await refresh(watchlistId);
    } catch {
      setEntries((prev) =>
        prev.map((x) => (String(x.ticker).toUpperCase() === ticker ? { ...x, status } : x))
      );
    }
    notify(`${ticker} → ${status}`);
  };

  const onRemove = async (ticker) => {
    try {
      await removeWatchlistOfficeCompany(watchlistId, ticker);
      await refresh(watchlistId);
    } catch {
      setEntries((prev) => prev.filter((x) => String(x.ticker).toUpperCase() !== ticker));
    }
    notify(`Removed ${ticker}`);
  };

  const visible = entries.filter((x) => {
    if (filter === 'New') return true;
    return String(x.status || 'New') === filter;
  });

  return (
    <div>
      <h1 className="agi-greeting">Watchlists</h1>
      <p className="agi-lede">
        Research queues — not ticker lists. New, Reviewing, Monitoring, Archived. Status updates, timeline events, no
        duplicates.
      </p>

      {error && <div className="agi-error">{error}</div>}
      {flash && <p className="agi-list-meta" style={{ color: 'var(--agi-ok)' }}>{flash}</p>}

      <form className="agi-search-bar" onSubmit={onAdd}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add company ticker"
          aria-label="Add company"
        />
        <button type="submit" className="agi-btn agi-btn-primary">
          Add
        </button>
      </form>

      <div className="agi-tabs" role="tablist">
        {['New', ...STATUSES].filter((v, i, a) => a.indexOf(v) === i).map((s) => (
          <button
            key={s}
            type="button"
            className={filter === s ? 'active' : undefined}
            onClick={() => setFilter(s === 'New' && filter !== 'New' ? 'New' : s)}
          >
            {s === 'New' && filter === 'New' ? 'All' : s}
          </button>
        ))}
      </div>

      <ul className="agi-list">
        {visible.map((entry) => {
          const ticker = String(entry.ticker || '').toUpperCase();
          const status = entry.status || 'New';
          return (
            <li key={ticker}>
              <Link to={`/agi/companies/${ticker}`}>
                <div className="agi-list-title">
                  {ticker} {entry.company ? `· ${entry.company}` : ''}
                </div>
                <div className="agi-list-meta">
                  Research status: {status} · latest evidence & alerts in workspace
                </div>
              </Link>
              <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
                {status !== 'Archived' ? (
                  <button type="button" className="agi-btn" onClick={() => setStatus(ticker, 'Archived')}>
                    Archive
                  </button>
                ) : (
                  <button type="button" className="agi-btn" onClick={() => setStatus(ticker, 'Monitoring')}>
                    Restore
                  </button>
                )}
                <button type="button" className="agi-btn" onClick={() => onRemove(ticker)}>
                  Remove
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      {!visible.length && <div className="agi-empty">No companies in this view.</div>}
    </div>
  );
}
