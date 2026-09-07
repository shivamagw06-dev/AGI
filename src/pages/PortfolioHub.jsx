import { Link } from 'react-router-dom';
import ClientPortfolioIntelligence from '@/pages/ClientPortfolioIntelligence';
import { useAuth } from '@/contexts/AuthContext';
import { isAdmin } from '@/lib/adminAuth';

export default function PortfolioHub() {
  const { user } = useAuth();
  const admin = isAdmin(user);

  return (
    <div className="bg-[#f4f1ea]">
      <div className="border-b border-[#d8d2c7] bg-[#fffdf8]">
        <div className="mx-auto flex max-w-[1800px] items-center gap-2 px-4 py-3 sm:px-6">
          <span className="bg-[#102a43] px-4 py-2 text-sm font-semibold text-white">
            Portfolio Intelligence
          </span>
          {admin ? (
            <Link
              to="/admin/founder-portfolio"
              className="px-4 py-2 text-sm font-semibold text-[#475569] transition hover:bg-[#ece7dc]"
            >
              Founder&apos;s Portfolio
            </Link>
          ) : null}
        </div>
      </div>
      <ClientPortfolioIntelligence />
    </div>
  );
}
