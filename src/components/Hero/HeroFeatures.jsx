import React from "react";
import { motion } from "framer-motion";
import {
  BarChart3,
  Globe2,
  Building2,
  Sparkles,
} from "lucide-react";

const features = [
  {
    icon: BarChart3,
    title: "Equity Research",
    description:
      "Institutional-quality company research, valuation, earnings analysis and investment insights.",
  },
  {
    icon: Globe2,
    title: "Macroeconomics",
    description:
      "GDP, inflation, RBI policy, global markets and economic intelligence.",
  },
  {
    icon: Building2,
    title: "Private Markets",
    description:
      "Private equity, venture capital, M&A and transaction intelligence.",
  },
  {
    icon: Sparkles,
    title: "AI Intelligence",
    description:
      "AI-powered research, summaries, screening and financial insights.",
  },
];

export default function HeroFeatures() {
  return (
    <section className="mt-24">

      <div className="text-center mb-12">

        <h2 className="text-3xl md:text-4xl font-bold text-white">
          What We Cover
        </h2>

        <p className="mt-4 text-slate-400 max-w-3xl mx-auto">
          Professional research designed for investors,
          analysts and business leaders.
        </p>

      </div>

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-6">

        {features.map((feature, index) => {

          const Icon = feature.icon;

          return (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 25 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{
                delay: index * 0.15,
                duration: 0.5,
              }}
              whileHover={{
                y: -8,
              }}
              className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-8 hover:border-blue-500/50 transition-all"
            >

              <div className="w-14 h-14 rounded-2xl bg-blue-600/20 flex items-center justify-center">

                <Icon className="text-blue-400" size={28} />

              </div>

              <h3 className="mt-6 text-xl font-semibold text-white">
                {feature.title}
              </h3>

              <p className="mt-4 text-slate-400 leading-7">
                {feature.description}
              </p>

            </motion.div>
          );
        })}
      </div>

    </section>
  );
}