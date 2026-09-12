import React from "react";
import { motion } from "framer-motion";
import { ArrowRight, Clock3 } from "lucide-react";
import { Button } from "@/components/ui/button";

const reports = [
  {
    title: "India Banking Sector Outlook FY2027",
    category: "Sector Research",
    readTime: "12 min",
    premium: true,
  },
  {
    title: "Global Macro Weekly",
    category: "Macroeconomics",
    readTime: "8 min",
  },
  {
    title: "Private Equity Deal Review",
    category: "Private Markets",
    readTime: "10 min",
  },
  {
    title: "Market Closing Note",
    category: "Daily Brief",
    readTime: "5 min",
  },
];

export default function FeaturedResearch() {
  return (
    <section className="bg-slate-950 py-24">

      <div className="max-w-7xl mx-auto px-6">

        <div className="flex justify-between items-end mb-14">

          <div>

            <span className="text-blue-400 text-sm font-semibold uppercase tracking-widest">
              Featured Research
            </span>

            <h2 className="text-5xl font-bold text-white mt-3">
              Institutional Reports
            </h2>

          </div>

          <Button variant="outline">
            View All Reports
          </Button>

        </div>

        <div className="grid lg:grid-cols-3 gap-8">

          {/* Large Card */}

          <motion.div
            whileHover={{ y: -8 }}
            className="lg:col-span-2 rounded-3xl overflow-hidden border border-white/10 bg-gradient-to-br from-blue-700 via-slate-900 to-slate-950 p-10"
          >

            <span className="inline-block rounded-full bg-blue-500/20 px-4 py-2 text-blue-300 text-sm">
              Premium Research
            </span>

            <h3 className="mt-8 text-4xl font-bold text-white leading-tight">
              India Banking Sector Outlook FY2027
            </h3>

            <p className="mt-6 text-slate-300 leading-8 max-w-2xl">
              A comprehensive review of the Indian banking sector,
              covering credit growth, NIM trends,
              asset quality, valuation,
              and future earnings outlook.
            </p>

            <div className="mt-10 flex items-center gap-6 text-slate-300">

              <div className="flex items-center gap-2">

                <Clock3 size={18}/>

                12 min read

              </div>

              <div>

                July 2026

              </div>

            </div>

            <Button className="mt-10 bg-white text-slate-900 hover:bg-slate-200">
              Read Report
              <ArrowRight className="ml-2 h-4 w-4"/>
            </Button>

          </motion.div>

          {/* Side Cards */}

          <div className="space-y-6">

            {reports.slice(1).map((item)=>(
              <motion.div
                key={item.title}
                whileHover={{x:6}}
                className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6"
              >

                <p className="text-blue-400 text-sm">
                  {item.category}
                </p>

                <h4 className="mt-3 text-white text-xl font-semibold">
                  {item.title}
                </h4>

                <p className="mt-5 flex items-center gap-2 text-slate-400 text-sm">
                  <Clock3 size={15}/>
                  {item.readTime}
                </p>

              </motion.div>
            ))}

          </div>

        </div>

      </div>

    </section>
  );
}