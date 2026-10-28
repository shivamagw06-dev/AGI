import React from 'react';
import { motion } from 'framer-motion';
import { Construction } from 'lucide-react';

const PlaceholderPage = ({ title, subtitle }) => {
  return (
    <section className="py-20 sm:py-32 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <div className="bg-blue-100 p-4 rounded-full w-20 h-20 mx-auto mb-8 flex items-center justify-center">
            <Construction className="h-10 w-10 text-blue-600" />
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-6">
            {title}
          </h1>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto">
            {subtitle}
          </p>
          <p className="text-lg text-slate-500 mt-4 max-w-2xl mx-auto">
            This page is currently under construction. Check back soon for exciting updates! 🚀
          </p>
        </motion.div>
      </div>
    </section>
  );
};

export default PlaceholderPage;