import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Activity,
  Bell,
  BookMarked,
  BookOpen,
  Brain,
  BrainCircuit,
  Briefcase,
  Building2,
  Bus,
  CalendarRange,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  Compass,
  Database,
  ExternalLink,
  FileSpreadsheet,
  FileStack,
  FileText,
  Fingerprint,
  FlaskConical,
  FolderOpen,
  Gauge,
  Gavel,
  GitBranch,
  Globe2,
  GraduationCap,
  Landmark,
  Layers,
  Layers3,
  LayoutDashboard,
  Library,
  Lightbulb,
  LineChart,
  ListChecks,
  LogOut,
  Map,
  MessageSquare,
  Network,
  Package,
  Plus,
  Radar,
  Radio,
  Scale,
  Shield,
  ShieldCheck,
  ShieldQuestion,
  Sparkles,
  Target,
  Zap,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { isAdmin } from '@/lib/adminAuth';

const authorNavItems = [
  { to: '/admin/articles', label: 'My Articles', icon: FileText },
  { to: '/admin/articles/new', label: 'New Article', icon: Plus },
];

const navItems = [
  { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/admin/data-warehouse', label: 'Data Warehouse', icon: Database },
  { to: '/admin/financial-warehouse', label: 'Financial Warehouse', icon: Database },
  { to: '/admin/financial-coverage', label: 'Financial Coverage', icon: CalendarRange },
  { to: '/admin/company-financials', label: 'Company Financials', icon: FileSpreadsheet },
  { to: '/admin/historical-coverage', label: 'Historical Coverage', icon: CalendarRange },
  { to: '/admin/upstox-bootstrap', label: 'Upstox Bootstrap', icon: Database },
  { to: '/admin/upstox-fundamentals', label: 'Upstox Fundamentals', icon: Building2 },
  { to: '/admin/valuation-policy', label: 'Valuation Policy', icon: Scale },
  { to: '/admin/historical-valuation', label: 'Historical Valuation', icon: CalendarRange },
  { to: '/admin/hvie-runtime', label: 'HVIE Build', icon: Activity },
  { to: '/admin/research-intelligence', label: 'Research Intelligence', icon: BookOpen },
  { to: '/admin/market-research-note', label: 'Market Research Note', icon: FileText },
  { to: '/admin/forecast-runtime', label: 'Forecast Output', icon: LineChart },
  { to: '/admin/macro-runtime', label: 'Macro Runtime', icon: Globe2 },
  { to: '/admin/ifac', label: 'Answer Composer', icon: Layers3 },
  { to: '/admin/aqe', label: 'Ask Product Quality', icon: ClipboardCheck },
  { to: '/admin/kul', label: 'KUL Routing', icon: Network },
  { to: '/admin/intelligence', label: 'Intelligence CMS', icon: Sparkles },
  { to: '/admin/knowledge-operations', label: 'Knowledge Operations', icon: Library },
  { to: '/admin/valuation-intelligence', label: 'Valuation Intelligence', icon: Scale },
  { to: '/admin/valuation-terminal', label: 'Valuation Terminal', icon: LineChart },
  { to: '/admin/investment-office', label: 'Investment Office', icon: Landmark },
  { to: '/admin/mission-control', label: 'Mission Control', icon: Gauge },
  { to: '/admin/release-health', label: 'Release Health', icon: ShieldCheck },
  { to: '/admin/articles', label: 'All Articles', icon: FileText },
  { to: '/admin/intelligence-map', label: 'Intelligence Map', icon: Map },
  { to: '/admin/intent-intelligence', label: 'Intent Intelligence', icon: BrainCircuit },
  { to: '/admin/entity-resolution', label: 'Entity Resolution', icon: Fingerprint },
  { to: '/admin/research-planner', label: 'Research Planner', icon: ClipboardList },
  { to: '/admin/context-intelligence', label: 'Context Intelligence', icon: Layers3 },
  { to: '/admin/analyst-router', label: 'Analyst Router', icon: Network },
  { to: '/admin/layer-router', label: 'Layer Router', icon: GitBranch },
  { to: '/admin/acquisition-planner', label: 'Acquisition Planner', icon: Database },
  { to: '/admin/blueprint-engine', label: 'Blueprint Engine', icon: FileStack },
  { to: '/admin/validation-engine', label: 'Validation Engine', icon: ShieldQuestion },
  { to: '/admin/research-execution', label: 'Research Execution', icon: Package },
  { to: '/admin/hypothesis-engine', label: 'Hypothesis Engine', icon: Lightbulb },
  { to: '/admin/research-questions', label: 'Research Questions', icon: ListChecks },
  { to: '/admin/hypothesis-testing', label: 'Hypothesis Testing', icon: FlaskConical },
  { to: '/admin/belief-engine', label: 'Belief Engine', icon: Gauge },
  { to: '/admin/thesis-construction', label: 'Thesis Construction', icon: Landmark },
  { to: '/admin/institutional-debate', label: 'Institutional Debate', icon: MessageSquare },
  { to: '/admin/decision-readiness', label: 'Decision Readiness', icon: ShieldCheck },
  { to: '/admin/reasoning-audit', label: 'Reasoning Audit', icon: ClipboardCheck },
  { to: '/admin/articles/new', label: 'New Article', icon: Plus },
  { to: '/admin/categories', label: 'Categories', icon: FolderOpen },

  { to: '/admin/knowledge', label: 'Knowledge Corpus', icon: Brain },
  { to: '/admin/open-intelligence', label: 'Open Intelligence', icon: Radar },
  { to: '/admin/evidence', label: 'Evidence', icon: Shield },
  { to: '/admin/live-evidence', label: 'Live Evidence (LEO)', icon: Activity },
  { to: '/admin/company-dossiers', label: 'Company Dossiers', icon: Briefcase },
  { to: '/admin/yahoo-provider', label: 'Yahoo Provider', icon: Radio },
  { to: '/admin/data-quality', label: 'Data Quality (DVC)', icon: ShieldCheck },
  { to: '/admin/evidence-completion', label: 'Evidence Completion', icon: ClipboardCheck },
  { to: '/admin/company-analysis', label: 'Company Analysis', icon: Building2 },
  { to: '/admin/institutional-stack', label: 'Institutional Stack', icon: Layers },
  { to: '/admin/financial-statements', label: 'Financial Statements', icon: FileSpreadsheet },
  { to: '/admin/financial-knowledge', label: 'Financial Knowledge', icon: BookOpen },
  { to: '/admin/accounting-intelligence', label: 'Accounting Intel', icon: Scale },
  { to: '/admin/portfolio-intelligence', label: 'Portfolio Intel', icon: Briefcase },
  { to: '/admin/causal-intelligence', label: 'Causal Intel', icon: GitBranch },
  { to: '/admin/forecast-intelligence', label: 'Forecast Intel', icon: Compass },
  { to: '/admin/knowledge-graph', label: 'Knowledge Graph', icon: Network },
  { to: '/admin/institutional-memory', label: 'Learning & Memory', icon: BookMarked },
  { to: '/admin/simulation-lab', label: 'Simulation Lab', icon: FlaskConical },
  { to: '/admin/strategy-lab', label: 'Strategy Lab', icon: LineChart },
  { to: '/admin/decision-engine-v2', label: 'Decision Engine V2', icon: Gavel },
  { to: '/admin/institutional-intelligence', label: 'Institutional Intelligence', icon: Activity },
  { to: '/admin/company-monitor', label: 'Company Monitor', icon: Bell },
  { to: '/admin/investment-intelligence', label: 'Investment Intel', icon: LineChart },
  { to: '/admin/forecasting', label: 'Forecasting', icon: Target },
  { to: '/admin/events', label: 'Events', icon: Zap },
  { to: '/admin/context', label: 'Context', icon: Layers },
  { to: '/admin/intelligence-bus', label: 'Intelligence Bus', icon: Bus },
  { to: '/admin/valuation', label: 'Valuation', icon: Scale },
  { to: '/admin/models', label: 'Models', icon: BookOpen },
  { to: '/admin/academy', label: 'Finance Academy', icon: GraduationCap },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const admin = isAdmin(user);
  const items = admin ? navItems : authorNavItems;

  return (
    <div className="min-h-screen flex bg-slate-100">
      <aside className="w-64 shrink-0 bg-[#0c1220] text-white flex flex-col border-r border-slate-800">
        <div className="px-5 py-6 border-b border-slate-800">
          <p className="text-[10px] uppercase tracking-[0.2em] text-orange-400 font-semibold">AGIB CMS</p>
          <h1 className="text-lg font-bold mt-1">{admin ? 'Content Studio' : 'My Articles'}</h1>
          <p className="text-xs text-slate-400 mt-1 truncate">{user?.email}</p>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {items.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-slate-800 space-y-1">
          <button
            type="button"
            onClick={() => window.open('/', '_blank')}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <ExternalLink size={16} />
            View Website
          </button>
          <button
            type="button"
            onClick={async () => {
              await logout();
              navigate('/login');
            }}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 shrink-0 bg-white border-b border-slate-200 flex items-center justify-between px-6">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <span>CMS</span>
            <ChevronRight size={14} />
            <span className="text-slate-900 font-medium">Editor</span>
          </div>
          <span className="text-xs text-slate-400">Publish market updates in real time</span>
        </header>

        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
