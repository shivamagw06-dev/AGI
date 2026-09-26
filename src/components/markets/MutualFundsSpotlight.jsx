import React from "react";
import { motion } from "framer-motion";
import { Star, TrendingUp } from "lucide-react";
import { useMarketOverviewContext } from "@/contexts/MarketOverviewContext";
import { SectionHeader } from "@/components/markets/MarketWidgets";
import { formatNumber, formatPct, pctClass } from "@/lib/marketFormat";

export default function MutualFundsSpotlight() {
  const { mutualFunds, loading } = useMarketOverviewContext();

  return (
    <section className="bg-slate-950 py-24 border-t border-white/5">
      <div className="max-w-7xl mx-auto px-6">
        <SectionHeader
          label="Mutual Funds"
          title="Top Performers"
          subtitle="Highest 1-year returns across debt, equity, and hybrid categories."
        />

        <div className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl overflow-hidden">
          <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 border-b border-white/10">
            <div className="col-span-5">Fund</div>
            <div className="col-span-2 text-right">NAV</div>
            <div className="col-span-2 text-right">1Y Return</div>
            <div className="col-span-2 text-center">Rating</div>
            <div className="col-span-1 text-right">Day</div>
          </div>

          {loading ? (
            <p className="px-6 py-12 text-slate-500 animate-pulse">Loading fund data…</p>
          ) : mutualFunds.length === 0 ? (
            <p className="px-6 py-12 text-slate-500">Fund data temporarily unavailable.</p>
          ) : (
            <div className="divide-y divide-white/5">
              {mutualFunds.map((fund, i) => (
                <motion.div
                  key={fund.name}
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.04 }}
                  className="grid grid-cols-1 md:grid-cols-12 gap-2 md:gap-4 px-6 py-5 hover:bg-white/[0.03] items-center"
                >
                  <div className="md:col-span-5">
                    <p className="font-medium text-white">{fund.name}</p>
                    {fund.category && (
                      <p className="text-xs text-slate-500 mt-0.5">{fund.category}</p>
                    )}
                  </div>
                  <div className="md:col-span-2 md:text-right">
                    <span className="md:hidden text-slate-500 text-xs mr-2">NAV</span>
                    <span className="text-white tabular-nums">{formatNumber(fund.nav)}</span>
                  </div>
                  <div className="md:col-span-2 md:text-right">
                    <span className="md:hidden text-slate-500 text-xs mr-2">1Y</span>
                    <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold tabular-nums">
                      <TrendingUp size={14} />
                      {formatPct(fund.return1y)}
                    </span>
                  </div>
                  <div className="md:col-span-2 md:text-center">
                    <span className="inline-flex items-center gap-0.5">
                      {Array.from({ length: 5 }).map((_, s) => (
                        <Star
                          key={s}
                          size={14}
                          className={s < (fund.rating || 0) ? "text-amber-400 fill-amber-400" : "text-slate-700"}
                        />
                      ))}
                    </span>
                  </div>
                  <div className={`md:col-span-1 md:text-right text-sm font-medium tabular-nums ${pctClass(fund.change)}`}>
                    {formatPct(fund.change)}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
