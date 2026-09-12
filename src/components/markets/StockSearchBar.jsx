import React, { useState } from "react";
import { Search, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { searchStock } from "@/api/indianApi";

export default function StockSearchBar({ compact = false }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  const handleSearch = async (value) => {
    setQuery(value);
    if (value.trim().length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }

    setLoading(true);
    try {
      const data = await searchStock(value.trim());
      const rows = Array.isArray(data) ? data : data?.results || data?.stocks || [];
      setResults(
        rows.slice(0, 6).map((item) => ({
          name: item.commonName || item.name || item.company_name,
          symbol: item.exchangeCodeNsi || item["nse-code"] || item.nse_code || item.symbol,
        }))
      );
      setOpen(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const pickResult = (item) => {
    const name = item.name || item.company_name || item.symbol;
    setOpen(false);
    setQuery("");
    navigate(`/sections/markets?q=${encodeURIComponent(name)}`);
  };

  return (
    <div className={`relative ${compact ? "w-full max-w-md" : "w-full max-w-2xl mx-auto"}`}>
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
        {loading && (
          <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 text-blue-400 animate-spin" size={18} />
        )}
        <input
          type="search"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 200)}
          placeholder="Search stocks — Reliance, TCS, HDFC Bank…"
          className={`w-full rounded-2xl border border-white/10 bg-white/5 pl-12 pr-12 text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 ${
            compact ? "py-2.5 text-sm" : "py-4 text-base"
          }`}
        />
      </div>

      {open && results.length > 0 && (
        <div className="absolute z-50 mt-2 w-full rounded-2xl border border-white/10 bg-slate-900 shadow-2xl overflow-hidden">
          {results.map((item, i) => (
              <button
                key={`${item.symbol}-${i}`}
                type="button"
                onMouseDown={() => pickResult(item)}
                className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-white/5 transition-colors"
              >
                <span className="text-white font-medium">{item.name}</span>
                <span className="text-xs text-slate-500">{item.symbol}</span>
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
