import React from "react";
import { motion } from "framer-motion";
import {
  BarChart3,
  Globe2,
  Building2,
  Landmark,
  Briefcase,
  Newspaper,
  ArrowRight,
} from "lucide-react";

const categories = [
  {
    title: "Equity Research",
    description:
      "Company analysis, valuation, earnings and institutional research.",
    icon: BarChart3,
    color: "text-blue-400",
  },
  {
    title: "Macroeconomics",
    description:
      "GDP, inflation, RBI policy, fiscal policy and global economy.",
    icon: Globe2,
    color: "text-cyan-400",
  },
  {
    title: "Markets",
    description:
      "Daily market intelligence, commodities, bonds and currencies.",
    icon: Landmark,
    color: "text-green-400",
  },
  {
    title: "Private Markets",
    description:
      "Private equity, venture capital, IPOs and M&A activity.",
    icon: Briefcase,
    color: "text-orange-400",
  },
  {
    title: "Business",
    description:
      "Corporate strategy, industries and business intelligence.",
    icon: Building2,
    color: "text-purple-400",
  },
  {
    title: "Daily Briefs",
    description:
      "Morning reports, evening wrap and market outlook.",
    icon: Newspaper,
    color: "text-pink-400",
  },
];

export default function ResearchCategories() {
  return (
    <section className="py-24 bg-slate-950">

      <div className="max-w-7xl mx-auto px-6">

        <div className="text-center mb-16">

          <span className="inline-flex rounded-full bg-blue-600/10 border border-blue-500/20 px-4 py-2 text-blue-300 text-sm font-medium">
            Research Platform
          </span>

          <h2 className="mt-6 text-5xl font-bold text-white">
            Explore Our Research
          </h2>

          <p className="mt-5 text-slate-400 max-w-3xl mx-auto text-lg">
            Institutional-quality research covering every major area of finance,
            economics and global markets.
          </p>

        </div>

        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-8">

          {categories.map((item, index) => {

            const Icon = item.icon;

            return (

              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{
                  duration: 0.5,
                  delay: index * 0.1,
                }}
                whileHover={{
                  y: -8,
                  scale: 1.02,
                }}
                className="group rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-8 hover:border-blue-500/40 transition-all cursor-pointer"
              >

                <div className="w-16 h-16 rounded-2xl bg-slate-900 flex items-center justify-center">

                  <Icon className={item.color} size={30} />

                </div>

                <h3 className="mt-8 text-2xl font-bold text-white group-hover:text-blue-400 transition">

                  {item.title}

                </h3>

                <p className="mt-4 text-slate-400 leading-7">

                  {item.description}

                </p>

                <div className="mt-8 flex items-center text-blue-400 font-medium">

                  Explore

                  <ArrowRight
                    size={18}
                    className="ml-2"
                  />

                </div>

              </motion.div>

            );
          })}

        </div>

      </div>

    </section>
  );
}