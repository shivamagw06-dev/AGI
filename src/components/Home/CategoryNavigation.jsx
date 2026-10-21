import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import useCategories from '@/hooks/useCategories';

export default function CategoryNavigation() {
  const { categories, loading } = useCategories();

  if (loading || !categories.length) return null;

  return (
    <section className="bg-slate-900 border-y border-white/10 py-12">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-10">
          <span className="inline-flex rounded-full bg-blue-600/10 border border-blue-500/20 px-4 py-2 text-blue-300 text-sm font-medium">
            Browse by Topic
          </span>
          <h2 className="mt-5 text-3xl md:text-4xl font-bold text-white">
            Latest Updates & Research
          </h2>
          <p className="mt-3 text-slate-400 max-w-2xl mx-auto">
            Market updates, research reports and analysis — organized by category.
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-3">
          {categories.map((cat, index) => (
            <motion.div
              key={cat.id || cat.slug}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.04 }}
            >
              <Link
                to={`/category/${cat.slug}`}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-white/15 bg-white/5 text-slate-200 text-sm font-medium hover:border-blue-500/50 hover:bg-blue-600/10 hover:text-white transition-all"
              >
                {cat.name}
                <ArrowRight size={14} className="opacity-50" />
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
