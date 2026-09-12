import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import PageShell from '@/components/Layout/PageShell';
import { MARKET_UPDATE_CATEGORIES } from '@/config/contentCategories';

export default function MarketUpdates() {
  const navigate = useNavigate();

  return (
    <PageShell
      theme="light"
      eyebrow="Market Updates"
      title="Daily Market Updates"
      description="Pre-market briefings, mid-day check-ins, and end-of-day summaries for Indian equities."
      metaTitle="Market Updates | Agarwal Global Investments"
    >
      <div className="grid sm:grid-cols-3 gap-5 max-w-4xl">
        {MARKET_UPDATE_CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          return (
            <button
              key={cat.id}
              type="button"
              onClick={() => navigate(cat.path)}
              className="group text-left rounded-xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md hover:border-slate-300 transition-all"
            >
              <Icon size={24} className="text-slate-700 group-hover:text-blue-700 transition-colors" />
              <h2 className="mt-4 font-semibold text-slate-900">{cat.title}</h2>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">{cat.description}</p>
              <span className="mt-4 inline-flex items-center text-sm text-blue-700 font-medium">
                Read updates
                <ArrowRight className="ml-1 h-4 w-4" />
              </span>
            </button>
          );
        })}
      </div>
    </PageShell>
  );
}
