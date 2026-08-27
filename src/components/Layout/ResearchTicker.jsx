import { ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

const items = [
  { label: "Featured Research", path: "/" },
  { label: "Research Library", path: "/sections/live-articles" },
  { label: "Research Notes", path: "/sections/research-notes" },
  { label: "Deal Tracker", path: "/sections/deal-tracker" },
  { label: "Markets", path: "/markets/stocks" },
  { label: "Economy", path: "/sections/research-notes" },
  { label: "Private Equity", path: "/sections/deal-tracker" },
  { label: "Opinions", path: "/sections/opinions-editorials" },
  { label: "Business", path: "/business" },
];

export default function ResearchTicker() {
  const navigate = useNavigate();

  return (
    <section className="border-b border-slate-200 bg-white">
      <div className="max-w-7xl mx-auto flex items-center overflow-x-auto whitespace-nowrap px-6 py-3 scrollbar-hide">
        <span className="mr-5 font-semibold text-blue-700 shrink-0">Research</span>

        {items.map((item) => (
          <div key={item.path} className="flex items-center text-sm shrink-0">
            <button
              type="button"
              onClick={() => navigate(item.path)}
              className="px-3 text-slate-700 hover:text-blue-700 transition-colors"
            >
              {item.label}
            </button>
            <ChevronRight className="h-3 w-3 text-slate-300" />
          </div>
        ))}
      </div>
    </section>
  );
}
