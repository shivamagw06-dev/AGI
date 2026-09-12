import React from "react";
import { motion } from "framer-motion";
import { heroStats } from "@/lib/theme";

const HeroStats = () => {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mt-20">

      {heroStats.map((item, index) => (

        <motion.div
          key={item.label}
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.6,
            delay: index * 0.15,
          }}
          whileHover={{
            y: -6,
            scale: 1.03,
          }}
          className="
            rounded-2xl
            border
            border-white/10
            bg-white/5
            backdrop-blur-xl
            p-6
            text-center
            shadow-xl
            transition-all
          "
        >
          <h2 className="text-4xl font-bold text-white">
            {item.number}
          </h2>

          <p className="mt-2 text-slate-300">
            {item.label}
          </p>

        </motion.div>

      ))}

    </div>
  );
};

export default HeroStats;