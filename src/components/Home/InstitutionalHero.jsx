import { ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function InstitutionalHero() {
  const navigate = useNavigate();

  return (
    <section className="bg-white border-b border-[#dddddd]">
      <div className="max-w-4xl mx-auto px-6 py-16 md:py-24 text-center">
        <h1 className="reuters-heading text-3xl sm:text-4xl md:text-[2.75rem] leading-tight">
          Institutional-Quality Market Research for Indian Investors
        </h1>
        <p className="reuters-body mt-5 text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
          Daily market updates, company research, earnings analysis, and actionable investment insights.
        </p>
        <div className="mt-9">
          <button
            type="button"
            onClick={() => navigate('/research')}
            className="reuters-btn inline-flex items-center h-11 px-7 text-sm uppercase tracking-wide"
          >
            Explore Today&apos;s Research
            <ArrowRight className="ml-2 h-4 w-4" />
          </button>
        </div>
      </div>
    </section>
  );
}
