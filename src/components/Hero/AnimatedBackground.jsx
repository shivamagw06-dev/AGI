import React from "react";
import { motion } from "framer-motion";

const AnimatedBackground = () => {
  return (
    <div className="absolute inset-0 overflow-hidden">

      {/* Base Background */}
      <div className="absolute inset-0 bg-slate-950" />

      {/* Main Gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800" />

      {/* Grid Pattern */}
      <div
        className="absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.08) 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
        }}
      />

      {/* Blue Orb 1 */}
      <motion.div
        className="absolute w-[600px] h-[600px] rounded-full bg-blue-600/20 blur-3xl"
        initial={{ x: -150, y: -100 }}
        animate={{
          x: [-150, -80, -150],
          y: [-100, -40, -100],
        }}
        transition={{
          duration: 18,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      {/* Blue Orb 2 */}
      <motion.div
        className="absolute right-0 bottom-0 w-[500px] h-[500px] rounded-full bg-cyan-500/20 blur-3xl"
        initial={{ x: 100, y: 100 }}
        animate={{
          x: [100, 40, 100],
          y: [100, 40, 100],
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      {/* Small Floating Light */}
      <motion.div
        className="absolute top-1/3 left-2/3 w-44 h-44 rounded-full bg-blue-400/10 blur-2xl"
        animate={{
          y: [-20, 20, -20],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
        }}
      />

      {/* Radial Highlight */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(circle at center, rgba(37,99,235,0.12), transparent 65%)",
        }}
      />
    </div>
  );
};

export default AnimatedBackground;