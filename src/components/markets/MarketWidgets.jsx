import { formatNumber, formatPct, pctClass } from "@/lib/marketFormat";

export function StockTable({ rows, empty = "No data available." }) {
  if (!rows?.length) {
    return <p className="px-6 py-8 text-sm text-slate-500">{empty}</p>;
  }

  return (
    <div className="divide-y divide-white/5">
      {rows.map((row, i) => (
        <div
          key={`${row.symbol || row.name}-${i}`}
          className="flex items-center justify-between gap-4 px-6 py-4 hover:bg-white/[0.03] transition-colors"
        >
          <div className="min-w-0">
            <p className="font-medium text-white truncate">{row.name}</p>
            {row.symbol && (
              <p className="text-xs text-slate-500 truncate">{row.symbol}</p>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className="font-semibold text-white tabular-nums">
              {formatNumber(row.price)}
            </p>
            <p className={`text-sm font-medium tabular-nums ${pctClass(row.change)}`}>
              {formatPct(row.change)}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function SectionHeader({ label, title, subtitle, action }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 mb-10">
      <div>
        <span className="text-blue-400 uppercase tracking-widest text-sm font-semibold">
          {label}
        </span>
        <h2 className="text-4xl md:text-5xl font-bold text-white mt-2">{title}</h2>
        {subtitle && <p className="mt-3 text-slate-400 text-lg max-w-2xl">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
