import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import SubscribeModal from '@/components/SubscribeModal';

const taglines = [
  'Insights That Power Investment Decisions',
  'Global Perspectives. Local Expertise.',
  'Actionable Research for Finance, Economics & Deals',
  'Your Daily Edge on Finance, Private Equity & M&A',
];

const Hero = () => {
  const [taglineIndex, setTaglineIndex] = useState(0);
  const [openSubscribe, setOpenSubscribe] = useState(false);

  useEffect(() => {
    const interval = setInterval(
      () => setTaglineIndex((i) => (i + 1) % taglines.length),
      4000
    );
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <section className="relative overflow-hidden bg-background pt-20 pb-24 sm:pt-32 sm:pb-32">
        <div className="absolute inset-0 bg-grid-slate-200 [mask-image:linear-gradient(0deg,white,rgba(255,255,255,0.6))]" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-foreground mb-4">
                Agarwal Global Investments
              </h1>
              <p className="text-lg sm:text-xl text-foreground/70 mb-6 max-w-3xl mx-auto">
                Independent research and live insights on finance, economics, private equity & M&A.
              </p>
            </motion.div>

            <div className="h-8 mb-8 flex items-center justify-center">
              <AnimatePresence mode="wait">
                <motion.p
                  key={taglineIndex}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ duration: 0.5 }}
                  className="text-secondary font-semibold text-base sm:text-lg"
                >
                  {taglines[taglineIndex]}
                </motion.p>
              </AnimatePresence>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="flex flex-col sm:flex-row gap-4 justify-center"
            >
              <Button
                size="lg"
                className="bg-primary text-primary-foreground hover:bg-primary/90 px-8 shadow-lg hover:shadow-primary/40 transition-shadow"
                onClick={() => setOpenSubscribe(true)}
              >
                Subscribe for Free Updates
              </Button>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Modal */}
      <SubscribeModal open={openSubscribe} onClose={() => setOpenSubscribe(false)} />
    </>
  );
};

export default Hero;
