import React, { useMemo, useState } from "react";
import { Helmet } from "react-helmet-async";
import { useSearchParams } from "react-router-dom";
import { Search, BarChart3 } from "lucide-react";
import MarketsDeskNav from "@/components/markets/MarketsDeskNav";
import TrendlyneWidget, { buildTrendlyneUrls } from "@/components/markets/TrendlyneWidget";
import {
  TradingViewFinancials,
  TradingViewHeatmap,
  TradingViewMarketOverview,
} from "@/components/markets/TradingViewWidgets";

const STOCK_CATALOG = [
  { symbol: "RELIANCE", name: "Reliance Industries" },
  { symbol: "TCS", name: "Tata Consultancy Services" },
  { symbol: "HDFCBANK", name: "HDFC Bank" },
  { symbol: "INFY", name: "Infosys" },
  { symbol: "ICICIBANK", name: "ICICI Bank" },
  { symbol: "ITC", name: "ITC Limited" },
  { symbol: "SBIN", name: "State Bank of India" },
  { symbol: "BHARTIARTL", name: "Bharti Airtel" },
  { symbol: "KOTAKBANK", name: "Kotak Mahindra Bank" },
  { symbol: "LT", name: "Larsen & Toubro" },
  { symbol: "AXISBANK", name: "Axis Bank" },
  { symbol: "MARUTI", name: "Maruti Suzuki" },
  { symbol: "TITAN", name: "Titan Company" },
  { symbol: "BAJFINANCE", name: "Bajaj Finance" },
  { symbol: "WIPRO", name: "Wipro" },
  { symbol: "HINDUNILVR", name: "Hindustan Unilever" },
  { symbol: "ASIANPAINT", name: "Asian Paints" },
  { symbol: "SUNPHARMA", name: "Sun Pharmaceutical" },
];

const DEFAULT_SYMBOL = "RELIANCE";

export default function Markets() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = (searchParams.get("symbol") || DEFAULT_SYMBOL).toUpperCase();
  const [symbol, setSymbol] = useState(initial);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const trendlyne = useMemo(() => buildTrendlyneUrls(symbol), [symbol]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return STOCK_CATALOG.filter(
      (s) =>
        s.symbol.toLowerCase().includes(q) ||
        s.name.toLowerCase().includes(q)
    ).slice(0, 8);
  }, [query]);

  const selectSymbol = (next) => {
    const sym = next.toUpperCase();
    setSymbol(sym);
    setQuery("");
    setOpen(false);
    setSearchParams({ symbol: sym }, { replace: true });
  };

  const selectedStock = STOCK_CATALOG.find((s) => s.symbol === symbol);

  return (
    <>
      <Helmet>
        <title>Markets | Agarwal Global Investments</title>
        <meta
          name="description"
          content="Trendlyne and TradingView market widgets with SWOT, technicals, heatmap, and fundamentals."
        />
      </Helmet>

      <div className="bg-white min-h-screen reuters-page">
        <section className="bg-white border-b border-[#dddddd]">
          <div className="max-w-6xl mx-auto px-6 py-10 lg:py-12">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#767676]">
              <BarChart3 size={16} />
              Market Overview
            </div>
            <h1 className="reuters-heading mt-2 text-3xl md:text-4xl">
              Market Intelligence
            </h1>
            <p className="reuters-body mt-3 text-base max-w-2xl">
              Search a stock to update SWOT, technical analysis, and fundamentals widgets below.
            </p>
            <MarketsDeskNav />

            <div className="mt-6">
              <span className="inline-block border border-[#dddddd] bg-[#f7f7f7] px-3 py-1 text-xs font-semibold text-[#555555]">
                Viewing: {symbol}
                {selectedStock ? ` · ${selectedStock.name}` : ''}
              </span>
            </div>

            <div className="relative mt-5 max-w-xl">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#767676]" size={18} />
              <input
                type="search"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setOpen(true);
                }}
                onFocus={() => setOpen(true)}
                onBlur={() => setTimeout(() => setOpen(false), 180)}
                placeholder="Search stock — Reliance, TCS, HDFC Bank…"
                className="w-full border border-[#dddddd] bg-white pl-10 pr-4 py-2.5 text-[#111111] placeholder:text-[#767676] focus:border-[#ff8000] focus:outline-none focus:ring-1 focus:ring-[#ff8000]"
              />
              {open && filtered.length > 0 && (
                <div className="absolute z-30 mt-1 w-full border border-[#dddddd] bg-white shadow-sm overflow-hidden">
                  {filtered.map((s) => (
                    <button
                      key={s.symbol}
                      type="button"
                      onMouseDown={() => selectSymbol(s.symbol)}
                      className="flex w-full px-4 py-3 hover:bg-[#f7f7f7] text-left border-b border-[#eeeeee] last:border-0"
                    >
                      <div>
                        <p className="font-semibold text-sm text-[#111111]">{s.symbol}</p>
                        <p className="text-xs text-[#767676]">{s.name}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {STOCK_CATALOG.slice(0, 10).map((s) => (
                <button
                  key={s.symbol}
                  type="button"
                  onClick={() => selectSymbol(s.symbol)}
                  className={`px-3 py-1 text-xs font-medium border transition-colors ${
                    symbol === s.symbol
                      ? 'bg-[#ff8000] text-white border-[#ff8000]'
                      : 'bg-white text-[#555555] border-[#dddddd] hover:border-[#bbbbbb]'
                  }`}
                >
                  {s.symbol}
                </button>
              ))}
            </div>
          </div>
        </section>

        <div className="max-w-6xl mx-auto px-6 py-10 space-y-10">
          {/* TradingView — market-wide */}
          <section className="space-y-10">
            <TradingViewMarketOverview />
            <TradingViewHeatmap />
          </section>

          {/* Stock-specific — 2 column layout */}
          <section>
            <div className="mb-6 border-b border-[#dddddd] pb-4">
              <h2 className="reuters-heading text-xl">Stock Analysis · {symbol}</h2>
              <p className="reuters-muted mt-1 text-sm">Trendlyne & TradingView</p>
            </div>

            <div className="grid xl:grid-cols-2 gap-8">
              <TrendlyneWidget
                title="SWOT Analysis"
                subtitle={`Strengths, weaknesses, opportunities & threats · ${symbol}`}
                dataUrl={trendlyne.swot}
                minHeight={480}
              />
              <TradingViewFinancials symbol={symbol} />
            </div>

            <div className="grid xl:grid-cols-2 gap-8 mt-8">
              <TrendlyneWidget
                title="Technical Analysis"
                subtitle={`RSI, MACD, moving averages · ${symbol}`}
                dataUrl={trendlyne.technical}
                minHeight={480}
              />
              <TrendlyneWidget
                title="IPO Tracker"
                subtitle="Live IPOs, allotment status & listing returns"
                dataUrl={trendlyne.ipo}
                minHeight={480}
              />
            </div>
          </section>

          <p className="text-[11px] text-[#767676] text-center pb-6">
            Widgets by Trendlyne & TradingView. For informational purposes only — not investment advice.
          </p>
        </div>
      </div>
    </>
  );
}
