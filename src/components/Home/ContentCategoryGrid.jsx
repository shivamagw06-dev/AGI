import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { HOME_CATEGORIES } from '@/config/contentCategories';

export default function ContentCategoryGrid() {
  const navigate = useNavigate();

  return (
    <section className="bg-[#f7f7f7] border-b border-[#dddddd]">
      <div className="max-w-6xl mx-auto px-6 py-14 md:py-16">
        <div className="mb-10 md:mb-12 border-b border-[#dddddd] pb-8">
          <h2 className="reuters-heading text-2xl md:text-3xl">
            What would you like to read?
          </h2>
          <p className="reuters-muted mt-2 text-base max-w-2xl">
            Choose a section — market updates, research reports, company news, or live market data.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
          {HOME_CATEGORIES.map((category) => {
            const Icon = category.icon;
            return (
              <button
                key={category.id}
                type="button"
                onClick={() => navigate(category.path)}
                className="reuters-card group text-left p-6 transition-colors"
              >
                <Icon size={20} strokeWidth={1.5} className="text-[#555555]" />
                <h3 className="mt-4 text-base font-bold text-[#111111] group-hover:text-[#ff8000] transition-colors">
                  {category.title}
                </h3>
                <p className="mt-2 text-sm text-[#555555] leading-relaxed">
                  {category.description}
                </p>
                <span className="mt-4 inline-flex items-center text-xs font-semibold uppercase tracking-wide text-[#ff8000]">
                  Open
                  <ArrowRight className="ml-1 h-3.5 w-3.5" />
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
