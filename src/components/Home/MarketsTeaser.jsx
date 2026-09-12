import { ArrowRight, BarChart3 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';

export default function MarketsTeaser() {
  const navigate = useNavigate();

  return (
    <section className="border-y border-white/10 bg-slate-900/50">
      <div className="max-w-7xl mx-auto px-6 py-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="rounded-xl bg-blue-600/20 p-3 text-blue-400 shrink-0">
            <BarChart3 size={22} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Live market intelligence</h2>
            <p className="text-sm text-slate-400 mt-1">
              SWOT, technicals, heatmaps &amp; fundamentals on our Markets page.
            </p>
          </div>
        </div>
        <Button
          onClick={() => navigate('/markets')}
          className="bg-blue-600 hover:bg-blue-700 shrink-0"
        >
          Open Markets
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </section>
  );
}
