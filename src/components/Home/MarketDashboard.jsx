import React from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Newspaper,
  ArrowUpRight,
} from "lucide-react";
import { useMarketOverviewContext } from "@/contexts/MarketOverviewContext";
import { formatPct } from "@/lib/marketFormat";

export default function MarketDashboard() {
  const { gainers, losers, mostActive, news, commodities, loading } = useMarketOverviewContext();

  const topGainer = gainers[0];
  const topLoser = losers[0];
  const topActive = mostActive[0];
  const gold = commodities.find((c) => /gold/i.test(c.product || ""));

  const cards = [
    {
      title: "Top Gainer",
      value: topGainer?.name?.split(" ")[0] || "—",
      subtitle: topGainer ? `${formatPct(topGainer.change)} · ${topGainer.name}` : "Loading movers…",
      icon: TrendingUp,
      color: "text-green-400",
    },
    {
      title: "Top Loser",
      value: topLoser?.name?.split(" ")[0] || "—",
      subtitle: topLoser ? `${formatPct(topLoser.change)} · ${topLoser.name}` : "Loading movers…",
      icon: TrendingDown,
      color: "text-rose-400",
    },
    {
      title: "Most Active",
      value: topActive?.symbol || topActive?.name?.slice(0, 8) || "—",
      subtitle: topActive
        ? `${topActive.name} · Vol ${Number(topActive.volume || 0).toLocaleString("en-IN")}`
        : "By NSE volume",
      icon: Activity,
      color: "text-cyan-400",
    },
    {
      title: "Market News",
      value: loading ? "…" : String(news.length || 0),
      subtitle: news[0]?.title?.slice(0, 60) || "Latest headlines",
      icon: Newspaper,
      color: "text-blue-400",
    },
  ];

  if (gold) {
    cards[3].subtitle = `Gold ${gold.last_traded_price} (${formatPct(gold.per_change)}) · ${news.length} headlines`;
  }

  return (
    <section className="bg-slate-950 py-24">
      <div className="max-w-7xl mx-auto px-6">
        <div className="mb-14">
          <span className="text-blue-400 uppercase tracking-widest text-sm font-semibold">
            Dashboard
          </span>
          <h2 className="text-5xl font-bold text-white mt-3">Market Dashboard</h2>
          <p className="mt-5 text-slate-400 text-lg max-w-3xl">
            Live snapshot of today&apos;s top movers, volume leaders, and market headlines.
          </p>
        </div>

        <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-8">
          {cards.map((card, index) => {
            const Icon = card.icon;
            return (
              <motion.div
                key={card.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -6 }}
                className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-8"
              >
                <div className="flex justify-between items-center">
                  <div className="w-14 h-14 rounded-2xl bg-slate-900 flex items-center justify-center">
                    <Icon className={card.color} size={28} />
                  </div>
                  <ArrowUpRight className="text-slate-500" />
                </div>
                <h3 className="mt-8 text-slate-400">{card.title}</h3>
                <div className="mt-3 text-3xl font-bold text-white truncate">{card.value}</div>
                <p className="mt-4 text-slate-400 leading-7 text-sm line-clamp-2">{card.subtitle}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
