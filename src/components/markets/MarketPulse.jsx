import React, { useState } from "react";
import { motion } from "framer-motion";
import { Activity, TrendingDown, TrendingUp, Zap, BarChart3 } from "lucide-react";
import { useMarketOverviewContext } from "@/contexts/MarketOverviewContext";
import { SectionHeader, StockTable } from "@/components/markets/MarketWidgets";
import { normalizeStock } from "@/lib/marketFormat";

const TABS = [
  { id: "gainers", label: "Top Gainers", icon: TrendingUp },
  { id: "losers", label: "Top Losers", icon: TrendingDown },
  { id: "active", label: "Most Active", icon: Activity },
  { id: "shockers", label: "Price Shockers", icon: Zap },
  { id: "highs", label: "52-Week Highs", icon: BarChart3 },
];

export default function MarketPulse() {
  const { gainers, losers, mostActive, priceShockers, weekHighs, loading } = useMarketOverviewContext();
  const [tab, setTab] = useState("gainers");

  const weekHighRows = weekHighs.map((r) =>
    normalizeStock({ company: r.company, ticker: r.ticker, price: r.price, percentChange: null })
  );

  const panels = {
    gainers,
    losers,
    active: mostActive,
    shockers: priceShockers,
    highs: weekHighRows,
  };

  return (
    <section className="bg-slate-950 py-24 border-t border-white/5">
      <div className="max-w-7xl mx-auto px-6">
        <SectionHeader
          label="Live Markets"
          title="Market Pulse"
          subtitle="Real-time movers across NSE — gainers, losers, volume leaders, and breakout stocks."
        />

        <div className="flex flex-wrap gap-2 mb-8">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-all ${
                tab === id
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                  : "bg-white/5 text-slate-400 hover:text-white hover:bg-white/10"
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>

        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl overflow-hidden"
        >
          <div className="border-b border-white/10 px-6 py-4 flex items-center justify-between">
            <h3 className="font-semibold text-white">
              {TABS.find((t) => t.id === tab)?.label}
            </h3>
            <span className="text-xs text-slate-500">Delayed · NSE/BSE</span>
          </div>

          {loading ? (
            <div className="px-6 py-12 text-center text-slate-500 animate-pulse">
              Loading market data…
            </div>
          ) : (
            <StockTable rows={panels[tab]} />
          )}
        </motion.div>
      </div>
    </section>
  );
}
