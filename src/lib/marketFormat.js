export function formatInr(value, decimals = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: decimals,
  }).format(n);
}

export function formatNumber(value, decimals = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: decimals }).format(n);
}

export function formatPct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
}

export function pctClass(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "text-slate-400";
  return n >= 0 ? "text-emerald-500" : "text-rose-500";
}

export function normalizeStock(row = {}) {
  return {
    name: row.company_name || row.displayName || row.company || row.name || row.symbol || "—",
    symbol: row.ticker || row.nseCode || row.ric || row.symbol || "",
    price: row.price ?? row.last_traded_price ?? row.last ?? null,
    change: row.percent_change ?? row.percentChange ?? row.per_change ?? null,
    volume: row.volume ?? null,
  };
}
