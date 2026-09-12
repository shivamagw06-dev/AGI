import { NavLink } from 'react-router-dom';
import {
  Home,
  Bot,
  Globe2,
  Building2,
  FileText,
  LineChart,
  Search,
  Scale,
  Eye,
  BarChart3,
  CloudSun,
  Settings,
  Briefcase,
  Landmark,
} from 'lucide-react';

const ITEMS = [
  { to: '/beta', end: true, label: 'Home', icon: Home },
  { to: '/beta/investment-office', label: 'Investment Office', icon: Landmark },
  { to: '/beta/copilot', label: 'Copilot', icon: Bot },
  { to: '/beta/markets', label: 'Markets', icon: Globe2 },
  { to: '/beta/macro', label: 'Macro', icon: CloudSun },
  { to: '/beta/companies', label: 'Companies', icon: Building2 },
  { to: '/beta/research', label: 'Research', icon: FileText },
  { to: '/beta/forecasts', label: 'Forecasts', icon: LineChart },
  { to: '/beta/screener', label: 'Screener', icon: Search },
  { to: '/beta/compare', label: 'Compare', icon: Scale },
  { to: '/beta/watchlists', label: 'Watchlists', icon: Eye },
  { to: '/beta/portfolio', label: 'Portfolio Office', icon: Briefcase },
  { to: '/beta/validation', label: 'Validation', icon: BarChart3 },
  { to: '/beta/settings', label: 'Settings', icon: Settings },
];

export default function StoryNav({ onNavigate }) {
  return (
    <nav className="flex flex-col gap-0.5" aria-label="AGI Beta">
      {ITEMS.map(({ to, end, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) => `beta-nav-link ${isActive ? 'active' : ''}`}
        >
          <Icon className="h-4 w-4 shrink-0 opacity-80" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
