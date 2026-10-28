import React from 'react';
import {
  listRebalanceEvents, getRebalanceEvent, previewRebalancePaste, publishRebalance,
} from '@/lib/indexRebalanceApi';
import { supabase } from '@/lib/supabaseClient';
import { isAdmin } from '@/lib/adminAuth';
import './indexRebalanceTheme.css';

/**
 * Index rebalance research.
 *
 * The table has two kinds of column and the page keeps them visibly apart,
 * because conflating them is what makes a published rebalance table stale
 * within days. The flow estimate is somebody's model output as of a date, and
 * it is labelled with whose and when. Price, traded value, return since
 * announcement and days-of-ADVT are refreshed nightly, and a row that could
 * not be refreshed says so rather than showing a blank cell that reads as
 * zero.
 */

const fmtFlow = (value) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  // Parentheses for outflows, the convention every source table uses. A minus
  // sign at small sizes is easy to miss, and the sign is the whole point.
  const body = `$${Math.abs(number).toFixed(0)}mn`;
  return number < 0 ? `(${body})` : body;
};

const fmtDays = (value) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return `${number < 0 ? '(' : ''}${Math.abs(number).toFixed(1)}d${number < 0 ? ')' : ''}`;
};

const fmtPct = (value) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return `${number >= 0 ? '+' : ''}${number.toFixed(1)}%`;
};

function daysUntil(date) {
  if (!date) return null;
  const target = new Date(`${String(date).slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(target.getTime())) return null;
  return Math.round((target.getTime() - Date.now()) / 86_400_000);
}

function EntryTable({ title, rows, tone }) {
  if (!rows?.length) return null;
  return (
    <section className="rebalance-block">
      <h3 className={`rebalance-block__title rebalance-block__title--${tone}`}>{title}</h3>
      <div className="rebalance-scroll">
        <table className="rebalance-table">
          <thead>
            <tr>
              <th scope="col">Ticker</th>
              <th scope="col">Company</th>
              <th scope="col">Sector</th>
              <th scope="col">Change</th>
              <th scope="col" className="num">Est. net flow</th>
              <th scope="col" className="num">Days of ADVT</th>
              <th scope="col" className="num">Since ann.</th>
              <th scope="col" className="num">Last (₹)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id || row.source_ticker}>
                <th scope="row">{row.source_ticker}</th>
                <td>{row.company_name || '—'}</td>
                <td>{row.sector || '—'}</td>
                <td>{row.change_type}</td>
                <td className="num num--flow">{fmtFlow(row.net_passive_flow_usd_mn)}</td>
                <td className="num">{fmtDays(row.quote?.days_of_advt)}</td>
                <td className="num">{fmtPct(row.quote?.return_since_announced_pct)}</td>
                <td className="num">
                  {row.quote?.last_price_inr
                    ? Number(row.quote.last_price_inr).toFixed(2)
                    : <span className="rebalance-unpriced" title={row.quote?.refresh_note || 'Not refreshed yet'}>—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}


/**
 * Paste a review table in, confirm what was understood, then publish.
 *
 * Deliberately two steps. The parser matches columns by header text and the
 * headers differ between houses and between quarters, so the operator has to
 * see which rows were read and which were rejected before anything is stored.
 * A parser that silently drops eight of twenty-five names produces a table
 * that looks complete and is not.
 */
function PastePanel({ onPublished }) {
  const [text, setText] = React.useState('');
  const [meta, setMeta] = React.useState({
    provider: 'FTSE', index_name: '', announced_on: '', effective_on: '',
    estimate_source: '', estimate_as_of: '', source_url: '',
  });
  const [preview, setPreview] = React.useState(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [open, setOpen] = React.useState(false);

  const set = (key) => (event) => setMeta((prev) => ({ ...prev, [key]: event.target.value }));

  const run = (fn) => async () => {
    setBusy(true); setError(null);
    try { await fn(); } catch (err) { setError(err.message); } finally { setBusy(false); }
  };

  const doPreview = run(async () => setPreview(await previewRebalancePaste(text)));
  const doPublish = run(async () => {
    const result = await publishRebalance(meta, text);
    setPreview(null); setText('');
    onPublished(result);
  });

  if (!open) {
    return (
      <button type="button" className="rebalance-admin__toggle" onClick={() => setOpen(true)}>
        Add a rebalance
      </button>
    );
  }

  return (
    <section className="rebalance-admin">
      <h2>Add a rebalance</h2>
      <div className="rebalance-admin__grid">
        <label>Provider
          <select value={meta.provider} onChange={set('provider')}>
            {['FTSE', 'MSCI', 'SP', 'NSE', 'Other'].map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>
        <label>Index<input value={meta.index_name} onChange={set('index_name')} placeholder="Global All Cap" /></label>
        <label>Announced<input type="date" value={meta.announced_on} onChange={set('announced_on')} /></label>
        <label>Effective<input type="date" value={meta.effective_on} onChange={set('effective_on')} /></label>
        <label>Estimate source<input value={meta.estimate_source} onChange={set('estimate_source')} placeholder="Goldman Sachs" /></label>
        <label>Estimate as of<input type="date" value={meta.estimate_as_of} onChange={set('estimate_as_of')} /></label>
      </div>

      <label className="rebalance-admin__paste">Paste the table, including its header row
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8} spellCheck={false} />
      </label>

      <div className="rebalance-admin__actions">
        <button type="button" onClick={doPreview} disabled={busy || !text.trim()}>Preview</button>
        <button type="button" onClick={doPublish} disabled={busy || !preview?.rows?.length || !meta.index_name || !meta.announced_on}>
          Publish {preview?.rows?.length ? `${preview.rows.length} row(s)` : ''}
        </button>
        <button type="button" onClick={() => setOpen(false)} disabled={busy}>Close</button>
      </div>

      {error && <p className="rebalance-error">{error}</p>}

      {preview && (
        <div className="rebalance-admin__preview">
          <p>
            {preview.rows.length} row(s) understood
            {preview.header?.unmatched?.length > 0 && `, ${preview.header.unmatched.length} column(s) not recognised: ${preview.header.unmatched.join(', ')}`}
          </p>
          {/* Rejected lines are shown, not counted. A section banner landing
              here is correct; a real name landing here is a parser problem, and
              only the text tells them apart. */}
          {preview.rejected?.length > 0 && (
            <details>
              <summary>{preview.rejected.length} line(s) not used</summary>
              <ul>{preview.rejected.map((row, i) => <li key={i}><code>{row.line.slice(0, 90)}</code> — {row.reason}</li>)}</ul>
            </details>
          )}
          <div className="rebalance-scroll">
            <table className="rebalance-table">
              <thead><tr><th>Ticker</th><th>Symbol</th><th>Company</th><th className="num">Flow</th><th>Change</th></tr></thead>
              <tbody>
                {preview.rows.map((row, i) => (
                  <tr key={i}>
                    <th scope="row">{row.source_ticker}</th>
                    <td>{row.exchange_symbol || '—'}</td>
                    <td>{row.company_name || '—'}</td>
                    <td className="num num--flow">{fmtFlow(row.net_passive_flow_usd_mn)}</td>
                    <td>{row.change_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

export default function IndexRebalancePage() {
  const [events, setEvents] = React.useState([]);
  const [selected, setSelected] = React.useState(null);
  const [detail, setDetail] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [admin, setAdmin] = React.useState(false);

  React.useEffect(() => {
    let live = true;
    supabase.auth.getUser()
      .then(({ data }) => live && setAdmin(isAdmin(data?.user)))
      .catch(() => live && setAdmin(false));
    return () => { live = false; };
  }, []);

  const reload = React.useCallback(() => {
    listRebalanceEvents().then(({ events: rows }) => {
      setEvents(rows || []);
      setSelected((current) => current || rows?.[0]?.id || null);
    }).catch((err) => setError(err.message));
  }, []);

  React.useEffect(() => {
    let live = true;
    listRebalanceEvents()
      .then(({ events: rows }) => {
        if (!live) return;
        setEvents(rows || []);
        setSelected(rows?.[0]?.id || null);
      })
      .catch((err) => live && setError(err.message))
      .finally(() => live && setLoading(false));
    return () => { live = false; };
  }, []);

  React.useEffect(() => {
    if (!selected) return undefined;
    let live = true;
    setDetail(null);
    getRebalanceEvent(selected)
      .then((payload) => live && setDetail(payload))
      .catch((err) => live && setError(err.message));
    return () => { live = false; };
  }, [selected]);

  if (loading) return <main className="rebalance-page"><p>Loading index rebalance research…</p></main>;
  if (error) return <main className="rebalance-page"><p className="rebalance-error">{error}</p></main>;

  if (!events.length) {
    return (
      <main className="rebalance-page">
        <h1>Index rebalance</h1>
        <p className="rebalance-empty">
          No rebalance has been published yet.
          {admin ? ' Paste an index review table to start one.' : ' Nothing to show here yet.'}
        </p>
        {admin && <PastePanel onPublished={reload} />}
      </main>
    );
  }

  const event = detail?.event;
  const untilEffective = daysUntil(event?.effective_on);
  const estimateSource = detail?.inflows?.[0]?.estimate_source
    || detail?.outflows?.[0]?.estimate_source
    || null;

  return (
    <main className="rebalance-page">
      <header className="rebalance-header">
        <h1>Index rebalance</h1>
        {admin && <PastePanel onPublished={reload} />}
        <label className="rebalance-picker">
          <span>Review</span>
          <select value={selected || ''} onChange={(e) => setSelected(e.target.value)}>
            {events.map((row) => (
              <option key={row.id} value={row.id}>
                {row.provider} {row.index_name} — announced {String(row.announced_on).slice(0, 10)}
              </option>
            ))}
          </select>
        </label>
      </header>

      {event && (
        <section className="rebalance-summary">
          <div>
            <span className="rebalance-label">Announced</span>
            <strong>{String(event.announced_on).slice(0, 10)}</strong>
          </div>
          <div>
            <span className="rebalance-label">Effective</span>
            <strong>
              {event.effective_on ? String(event.effective_on).slice(0, 10) : 'not set'}
              {/* The gap between announcement and effective date is the trade.
                  Flows print on the effective date; positioning happens before. */}
              {untilEffective !== null && (
                <em className="rebalance-countdown">
                  {untilEffective > 0 ? ` in ${untilEffective}d` : untilEffective === 0 ? ' today' : ` ${Math.abs(untilEffective)}d ago`}
                </em>
              )}
            </strong>
          </div>
          <div>
            <span className="rebalance-label">Names</span>
            <strong>{detail.total_entries}</strong>
          </div>
        </section>
      )}

      {estimateSource && (
        // Attribution sits above the numbers, not in a footnote. These are
        // somebody else's estimates and the page should never imply otherwise.
        <p className="rebalance-attribution">
          Flow estimates are {estimateSource}&rsquo;s
          {detail?.inflows?.[0]?.estimate_as_of ? `, as of ${String(detail.inflows[0].estimate_as_of).slice(0, 10)}` : ''}.
          Price, traded value and return are refreshed nightly from exchange data.
        </p>
      )}

      {detail ? (
        <>
          {detail.sectors?.length > 0 && (
            <section className="rebalance-block">
              <h3 className="rebalance-block__title">Net flow by sector</h3>
              <ul className="rebalance-sectors">
                {detail.sectors.map((row) => (
                  <li key={row.sector}>
                    <span>{row.sector}</span>
                    <strong className={row.net_flow_usd_mn < 0 ? 'is-out' : 'is-in'}>
                      {fmtFlow(row.net_flow_usd_mn)}
                    </strong>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <EntryTable title="Potential inflows" rows={detail.inflows} tone="in" />
          <EntryTable title="Potential outflows" rows={detail.outflows} tone="out" />
          {/* Kept visible on purpose: a constituent change nobody has sized is
              still a constituent change, and dropping it would leave the page
              disagreeing with the index provider's own announcement. */}
          <EntryTable title="Index changes without a flow estimate" rows={detail.unsized} tone="neutral" />
        </>
      ) : (
        <p>Loading review…</p>
      )}
    </main>
  );
}
