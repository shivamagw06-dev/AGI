import React from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  Globe2,
  CalendarDays,
  Newspaper,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useMarketOverviewContext } from "@/contexts/MarketOverviewContext";
import { formatPct } from "@/lib/marketFormat";

const fallbackEvents = [
  { title: "India CPI", date: "This Week" },
  { title: "RBI MPC Meeting", date: "This Week" },
  { title: "US FOMC", date: "Next Week" },
];

export default function MarketBrief() {
  const { gainers, losers, news, commodities, loading } = useMarketOverviewContext();

  const themes = [
    ...news.slice(0, 3).map((n) => n.topics?.[0] || n.title?.slice(0, 40)),
    ...gainers.slice(0, 2).map((g) => `${g.name} rally`),
    ...losers.slice(0, 1).map((l) => `${l.name} decline`),
  ].filter(Boolean).slice(0, 6);

  const globalItems = commodities.slice(0, 4).map((c) => ({
    label: c.product?.replace(/MIC$/i, "") || "Commodity",
    value: formatPct(c.per_change),
    positive: Number(c.per_change) >= 0,
  }));

  const headlines = news.slice(0, 3);

  return (
    <section className="relative py-24 bg-slate-950">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 25 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mb-16 text-center"
        >
          <span className="inline-flex rounded-full bg-blue-600/10 border border-blue-500/20 px-4 py-2 text-blue-300 text-sm font-medium">
            Daily Intelligence
          </span>
          <h2 className="mt-6 text-5xl font-bold text-white">Today&apos;s Market Intelligence</h2>
          <p className="mt-5 text-slate-400 text-lg max-w-3xl mx-auto">
            Live themes, commodity moves, and headlines every investor should know.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-8">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-8"
          >
            <div className="flex items-center gap-3">
              <TrendingUp className="text-green-400" />
              <h3 className="text-2xl font-bold text-white">Market Themes</h3>
            </div>
            <div className="mt-8 space-y-4">
              {(loading ? ["Loading themes…"] : themes).map((theme) => (
                <div
                  key={theme}
                  className="rounded-xl border border-white/10 bg-slate-900/70 p-4 text-slate-300 hover:border-blue-500 transition line-clamp-2"
                >
                  {theme}
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-8"
          >
            <div className="flex items-center gap-3">
              <Globe2 className="text-cyan-400" />
              <h3 className="text-2xl font-bold text-white">Commodities</h3>
            </div>
            <div className="mt-8 space-y-5">
              {(globalItems.length ? globalItems : [{ label: "MCX Futures", value: "—", positive: true }]).map((item) => (
                <div key={item.label} className="flex justify-between border-b border-white/10 pb-4">
                  <span className="text-slate-300">{item.label}</span>
                  <span className={item.positive ? "text-emerald-400" : "text-rose-400"}>{item.value}</span>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-8"
          >
            <div className="flex items-center gap-3">
              <CalendarDays className="text-orange-400" />
              <h3 className="text-2xl font-bold text-white">Headlines</h3>
            </div>
            <div className="mt-8 space-y-5">
              {(headlines.length ? headlines : fallbackEvents).map((item, i) => (
                <div key={item.title || i} className="border-b border-white/10 pb-4">
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-white hover:text-blue-400 transition line-clamp-2"
                    >
                      {item.title}
                    </a>
                  ) : (
                    <>
                      <p className="text-white">{item.title}</p>
                      <p className="text-slate-500 text-sm">High Impact</p>
                    </>
                  )}
                  {item.source && (
                    <p className="text-slate-500 text-xs mt-1">{item.source}</p>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-10">
              <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700" asChild>
                <a href="/sections/markets">
                  <Newspaper className="mr-2 h-4 w-4" />
                  Full Markets Dashboard
                  <ArrowRight className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
