import { NavLink, Outlet, Link, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  LineChart,
  ArrowLeftRight,
  Building2,
  Briefcase,
  Landmark,
  Factory,
  Users,
  PenLine,
  FileText,
  Sparkles,
  ExternalLink,
  LogOut,
  Network,
  UserRoundSearch,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const MODULE_NAV = [
  { to: '/admin/intelligence', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/admin/intelligence/entities', label: 'Entity Registry', icon: Network, enabled: true },
  { to: '/admin/intelligence/insider-trading-data', label: 'Insider Data', icon: UserRoundSearch, enabled: true },
  { to: '/admin/intelligence/valuation-monitor', label: 'Valuation Monitor', icon: LineChart, enabled: true },
  { to: '/admin/intelligence/transactions', label: 'Recent Transactions', icon: ArrowLeftRight, enabled: true },
  { to: '/admin/intelligence/pe-firms', label: 'PE Firms', icon: Building2, enabled: false },
  { to: '/admin/intelligence/portfolio-companies', label: 'Portfolio Companies', icon: Briefcase, enabled: false },
  { to: '/admin/intelligence/funds', label: 'Funds', icon: Landmark, enabled: false },
  { to: '/admin/intelligence/industries', label: 'Industries', icon: Factory, enabled: false },
  { to: '/admin/intelligence/people', label: 'People', icon: Users, enabled: false },
  { to: '/admin/intelligence/editors-desk', label: "Editor's Desk", icon: PenLine, enabled: false },
  { to: '/admin/articles', label: 'Articles', icon: FileText, enabled: true, external: true },
  { to: '/admin/intelligence/ai-drafts', label: 'AI Drafts', icon: Sparkles, enabled: false },
];

export default function IntelligenceCmsLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex bg-[#f4f5f7]">
      <aside className="w-64 shrink-0 bg-[#0b3b60] text-white flex flex-col">
        <div className="px-5 py-6 border-b border-white/10">
          <p className="text-[10px] uppercase tracking-[0.2em] text-white/60 font-semibold">AGI</p>
          <h1 className="text-lg font-bold mt-1">Intelligence CMS</h1>
          <p className="text-xs text-white/60 mt-1 truncate">{user?.email}</p>
        </div>
        <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
          {MODULE_NAV.map(({ to, label, icon: Icon, end, enabled, external }) => {
            if (external) {
              return (
                <Link
                  key={to}
                  to={to}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-white/70 hover:bg-white/10 hover:text-white"
                >
                  <Icon size={17} />
                  {label}
                </Link>
              );
            }
            return (
              <NavLink
                key={to}
                to={to}
                end={end}
                onClick={(e) => {
                  if (enabled === false) e.preventDefault();
                }}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors ${
                    enabled === false
                      ? 'text-white/30 cursor-not-allowed'
                      : isActive
                        ? 'bg-white/15 text-white font-medium'
                        : 'text-white/75 hover:bg-white/10 hover:text-white'
                  }`
                }
              >
                <Icon size={17} />
                {label}
                {enabled === false && <span className="ml-auto text-[9px] uppercase tracking-wider opacity-60">Soon</span>}
              </NavLink>
            );
          })}
        </nav>
        <div className="px-2 py-4 border-t border-white/10 space-y-1">
          <button
            type="button"
            onClick={() => window.open('/private-markets', '_blank')}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-white/70 hover:text-white"
          >
            <ExternalLink size={15} /> View Private Markets
          </button>
          <button
            type="button"
            onClick={() => navigate('/admin')}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-white/70 hover:text-white"
          >
            <ArrowLeftRight size={15} /> Main CMS
          </button>
          <button
            type="button"
            onClick={async () => { await logout(); navigate('/login'); }}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-white/70 hover:text-white"
          >
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
