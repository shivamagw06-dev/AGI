import React, { useState } from "react";
import { motion } from "framer-motion";
import { Rocket, ExternalLink, Calendar } from "lucide-react";
import { useMarketOverviewContext } from "@/contexts/MarketOverviewContext";
import { SectionHeader } from "@/components/markets/MarketWidgets";
import { formatNumber } from "@/lib/marketFormat";

const TABS = [
  { id: "upcoming", label: "Upcoming" },
  { id: "open", label: "Open Now" },
  { id: "listed", label: "Recently Listed" },
];

function IpoCard({ ipo }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 hover:border-blue-500/30 transition-colors"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-400">
            {ipo.symbol}
          </p>
          <h4 className="mt-1 text-lg font-bold text-white">{ipo.name}</h4>
        </div>
        {ipo.is_sme && (
          <span className="rounded-full bg-amber-500/10 px-2 py-1 text-xs text-amber-400">SME</span>
        )}
      </div>

      <p className="mt-3 text-sm text-slate-400 line-clamp-2">
        {ipo.additional_text || "Details to be announced"}
      </p>

      <div className="mt-4 flex flex-wrap gap-4 text-sm">
        {ipo.issue_price != null && (
          <span className="text-slate-300">
            Issue: <strong className="text-white">₹{formatNumber(ipo.issue_price)}</strong>
          </span>
        )}
        {ipo.listing_gains != null && (
          <span className="text-emerald-400">Listing gain: {ipo.listing_gains}%</span>
        )}
        {ipo.listing_date && (
          <span className="flex items-center gap-1 text-slate-500">
            <Calendar size={14} /> {ipo.listing_date}
          </span>
        )}
      </div>

      {ipo.document_url && (
        <a
          href={ipo.document_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300"
        >
          SEBI filing <ExternalLink size={14} />
        </a>
      )}
    </motion.div>
  );
}

export default function IpoWatch() {
  const { ipo, loading } = useMarketOverviewContext();
  const [tab, setTab] = useState("upcoming");
  const items = ipo[tab] || [];

  return (
    <section className="bg-slate-950 py-24">
      <div className="max-w-7xl mx-auto px-6">
        <SectionHeader
          label="IPO Watch"
          title="Primary Market Tracker"
          subtitle="Upcoming, open, and recently listed IPOs with SEBI filings and subscription data."
        />

        <div className="flex gap-2 mb-8">
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition-all ${
                tab === id
                  ? "bg-blue-600 text-white"
                  : "bg-white/5 text-slate-400 hover:text-white"
              }`}
            >
              <Rocket size={14} className="inline mr-1.5 -mt-0.5" />
              {label}
              <span className="ml-1.5 opacity-60">({(ipo[id] || []).length})</span>
            </button>
          ))}
        </div>

        {loading ? (
          <p className="text-slate-500 animate-pulse">Loading IPO data…</p>
        ) : items.length === 0 ? (
          <p className="text-slate-500 rounded-2xl border border-white/10 p-8 text-center">
            No {tab} IPOs at the moment.
          </p>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((item) => (
              <IpoCard key={item.symbol || item.name} ipo={item} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
