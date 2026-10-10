import React from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowRight, FileText, Globe2, Building2, BarChart3 } from "lucide-react";
import { useNavigate } from "react-router-dom";

const Hero = () => {
  const navigate = useNavigate();

  return (
    <section className="relative overflow-hidden bg-slate-950 text-white">

      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800" />

      <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_center,#3b82f6_0,transparent_70%)]" />

      <div className="relative max-w-7xl mx-auto px-6 lg:px-8 py-28">

        <motion.div
          initial={{ opacity:0,y:20 }}
          animate={{ opacity:1,y:0 }}
          transition={{ duration:0.6 }}
          className="text-center"
        >

          <span className="inline-flex rounded-full bg-blue-600/20 border border-blue-500/30 px-5 py-2 text-sm text-blue-300 mb-8">
            AGARWAL GLOBAL INVESTMENTS
          </span>

          <h1 className="text-5xl md:text-7xl font-extrabold leading-tight">

            Institutional Research

            <br/>

            <span className="text-blue-400">
              Made Accessible
            </span>

          </h1>

          <p className="mt-8 max-w-3xl mx-auto text-xl text-slate-300 leading-8">

            Independent research covering equities,
            macroeconomics, private equity, mergers &
            acquisitions, capital markets and global investing.

            Built for investors who demand institutional-quality
            intelligence.

          </p>

          <div className="mt-12 flex flex-wrap justify-center gap-4">

            <Button
              size="lg"
              onClick={() => navigate("/research-notes")}
              className="px-8 h-14 text-lg"
            >
              Read Today's Report
              <ArrowRight className="ml-2 h-5 w-5"/>
            </Button>

            <Button
              size="lg"
              variant="outline"
              onClick={() => navigate("/login")}
              className="px-8 h-14 border-slate-500 text-white hover:bg-white hover:text-black"
            >
              Explore Research
            </Button>

          </div>

        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-24">

          <div className="rounded-2xl bg-white/5 border border-white/10 p-6">
            <FileText className="text-blue-400 mb-4"/>
            <h3 className="font-semibold">
              Daily Research
            </h3>
            <p className="text-slate-400 text-sm mt-2">
              Morning Brief, Midday Update and Closing Note.
            </p>
          </div>

          <div className="rounded-2xl bg-white/5 border border-white/10 p-6">
            <BarChart3 className="text-green-400 mb-4"/>
            <h3 className="font-semibold">
              Market Intelligence
            </h3>
            <p className="text-slate-400 text-sm mt-2">
              Sector analysis, macro trends and earnings.
            </p>
          </div>

          <div className="rounded-2xl bg-white/5 border border-white/10 p-6">
            <Building2 className="text-orange-400 mb-4"/>
            <h3 className="font-semibold">
              Company Research
            </h3>
            <p className="text-slate-400 text-sm mt-2">
              Institutional-quality equity reports.
            </p>
          </div>

          <div className="rounded-2xl bg-white/5 border border-white/10 p-6">
            <Globe2 className="text-purple-400 mb-4"/>
            <h3 className="font-semibold">
              Global Macro
            </h3>
            <p className="text-slate-400 text-sm mt-2">
              Inflation, GDP, Central Banks and global markets.
            </p>
          </div>

        </div>

      </div>

    </section>
  );
};

export default Hero;