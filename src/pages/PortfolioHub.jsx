import { Link, useLocation } from 'react-router-dom';
import PortfolioDesk from '@/pages/PortfolioDesk';
import FounderPortfolio from '@/pages/FounderPortfolio';

export default function PortfolioHub() {
  const location = useLocation();
  const founderActive = location.pathname.startsWith('/portfolio/founder');

  return (
    <div className="bg-[#f4f1ea]">
      <div className="border-b border-[#d8d2c7] bg-[#fffdf8]">
        <div className="mx-auto flex max-w-[1800px] items-center gap-2 px-4 py-3 sm:px-6">
          <Link
            to="/portfolio"
            className={`px-4 py-2 text-sm font-semibold transition ${
              !founderActive ? 'bg-[#102a43] text-white' : 'text-[#475569] hover:bg-[#ece7dc]'
            }`}
          >
            AGI Model Portfolio
          </Link>
          <Link
            to="/portfolio/founder"
            className={`px-4 py-2 text-sm font-semibold transition ${
              founderActive ? 'bg-[#102a43] text-white' : 'text-[#475569] hover:bg-[#ece7dc]'
            }`}
          >
            Founder&apos;s Portfolio
          </Link>
        </div>
      </div>
      {founderActive ? <FounderPortfolio /> : <PortfolioDesk />}
    </div>
  );
}

