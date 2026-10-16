import React from 'react';

/**
 * Clean Database — the warehouse with the known-bad rows filtered out.
 *
 * The warehouse keeps good and corrupt rows in the same tables. A screen that
 * reads `financials_annual` without checking the fiscal-year label format can
 * pick up a quarterly figure in absolute rupees where it expected an annual one
 * in millions, and nothing about the number announces the mistake. This page
 * shows what survives each filter and, just as importantly, what does not:
 * a filter that silently drops a quarter of a table looks exactly like a filter
 * that is broken.
 *
 * Read-only. No view here writes, recomputes, or stores anything.
 */

const VIEWS = [
  {
    id: 'financials_annual',
    label: 'Annual Financials',
    blurb: 'Statement history with the quarterly rows that were labelled as annual removed.',
  },
  {
    id: 'sector_ratios',
    label: 'Sector Ratios',
    blurb: 'Ten years of Capital IQ company ratios, vendor exclusions honoured.',
  },
  {
    id: 'daily_prices',
    label: 'Daily Prices',
    blurb: 'Price bars with weekend rows removed — NSE was closed on those dates.',
  },
];

const num = (value, digits = 0) =>
  value === null || value === undefined || Number.isNaN(Number(value))
    ? '—'
    : Number(value).toLocaleString('en-IN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });

async function getJson(url) {
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function RejectionBar({ keptPct }) {
  return (
    <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
      <div
        className="h-full rounded-full bg-emerald-500/80"
        style={{ width: `${Math.max(0, Math.min(100, keptPct))}%` }}
      />
    </div>
  );
}

function SummaryCard({ item, active, onSelect }) {
  const meta = VIEWS.find((v) => v.id === item.view);
  const keptPct = item.scanned ? (item.kept / item.scanned) * 100 : 0;
  return (
    <button
      type="button"
      onClick={() => onSelect(item.view)}
      className={`rounded-lg border p-4 text-left transition ${
        active
          ? 'border-emerald-500/60 bg-emerald-500/5'
          : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
      }`}
    >
      <div className="text-sm font-semibold text-slate-100">{meta?.label || item.view}</div>
      <div className="mt-1 font-mono text-xs text-slate-500">{item.table}</div>
      {item.ok === false ? (
        <div className="mt-3 text-xs text-rose-400">{item.error || 'view failed'}</div>
      ) : (
        <>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-semibold tabular-nums text-slate-100">
              {num(item.kept)}
            </span>
            <span className="text-xs text-slate-500">of {num(item.scanned)} sampled</span>
          </div>
          <RejectionBar keptPct={keptPct} />
          <div className="mt-2 text-xs text-slate-400">
            {item.rejected ? (
              <span className="text-amber-400">{item.rejected_pct}% rejected</span>
            ) : (
              <span className="text-emerald-400">nothing rejected</span>
            )}
          </div>
        </>
      )}
    </button>
  );
}

function DataTable({ columns, rows }) {
  if (!rows?.length) {
    return <div className="p-8 text-center text-sm text-slate-500">No rows survived the filter.</div>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-800">
            {columns.map((c) => (
              <th
                key={c}
                className="whitespace-nowrap px-3 py-2 text-left font-medium text-slate-400"
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-slate-900 hover:bg-slate-900/40">
              {columns.map((c) => {
                const v = row[c];
                const numeric = typeof v === 'number';
                return (
                  <td
                    key={c}
                    className={`whitespace-nowrap px-3 py-1.5 ${
                      numeric ? 'text-right tabular-nums text-slate-200' : 'text-slate-300'
                    }`}
                  >
                    {v === null || v === undefined
                      ? <span className="text-slate-600">—</span>
                      : numeric ? num(v, Number.isInteger(v) ? 0 : 2) : String(v)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function CleanDatabase() {
  const [summary, setSummary] = React.useState(null);
  const [selected, setSelected] = React.useState(VIEWS[0].id);
  const [detail, setDetail] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let alive = true;
    getJson('/api/intelligence/warehouse/clean?limit=5000')
      .then((d) => alive && setSummary(d))
      .catch((e) => alive && setError(String(e.message || e)));
    return () => {
      alive = false;
    };
  }, []);

  React.useEffect(() => {
    let alive = true;
    setLoading(true);
    setDetail(null);
    getJson(`/api/intelligence/warehouse/clean/${selected}?limit=2000`)
      .then((d) => alive && setDetail(d))
      .catch((e) => alive && setError(String(e.message || e)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [selected]);

  const meta = VIEWS.find((v) => v.id === selected);

  return (
    <div className="min-h-screen bg-[#0b0e14] px-6 py-8 text-slate-200">
      <div className="mx-auto max-w-[1500px]">
        <header>
          <h1 className="text-2xl font-semibold text-slate-50">Clean Database</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-400">
            The warehouse with rows excluded that are known to be wrong. Every filter
            below corresponds to a defect verified against production, and each view
            reports what it rejected as well as what it kept — a filter that quietly
            drops a quarter of a table is indistinguishable from one that is broken.
          </p>
        </header>

        {error && (
          <div className="mt-6 rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300">
            {error}
          </div>
        )}

        <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(summary?.views || []).map((item) => (
            <SummaryCard
              key={item.view}
              item={item}
              active={item.view === selected}
              onSelect={setSelected}
            />
          ))}
        </section>

        <section className="mt-8 rounded-lg border border-slate-800 bg-slate-900/30">
          <div className="border-b border-slate-800 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-100">{meta?.label}</h2>
            <p className="mt-0.5 text-xs text-slate-500">{meta?.blurb}</p>
          </div>

          {detail?.rejected_reasons && Object.keys(detail.rejected_reasons).length > 0 && (
            <div className="border-b border-slate-800 px-4 py-3">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Excluded
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(detail.rejected_reasons).map(([reason, count]) => (
                  <span
                    key={reason}
                    className="rounded border border-amber-900/60 bg-amber-950/30 px-2 py-1 font-mono text-xs text-amber-300"
                  >
                    {reason} · {num(count)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {detail?.caveats?.length > 0 && (
            <div className="border-b border-slate-800 px-4 py-3">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Still true of the kept rows
              </div>
              <ul className="mt-2 space-y-1">
                {detail.caveats.map((c) => (
                  <li key={c} className="text-xs leading-relaxed text-slate-400">
                    — {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {loading ? (
            <div className="p-8 text-center text-sm text-slate-500">Loading…</div>
          ) : (
            <>
              <div className="flex items-baseline justify-between px-4 py-2 text-xs text-slate-500">
                <span>
                  showing {num(detail?.rows?.length)} of {num(detail?.kept)} kept
                  {detail?.units ? ` · ${detail.units}` : ''}
                </span>
                <span className="font-mono">{detail?.table}</span>
              </div>
              <DataTable columns={detail?.columns || []} rows={detail?.rows || []} />
            </>
          )}
        </section>

        <p className="mt-4 text-xs text-slate-600">
          Read-only. Counts describe the sampled rows, not the full table.
        </p>
      </div>
    </div>
  );
}
