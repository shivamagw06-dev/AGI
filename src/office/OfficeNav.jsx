import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Bell, Bookmark, Menu, Search, User, X } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const NAV = [
  { name: 'Home', path: '/' },
  { name: 'Ask AGI', path: '/ask' },
  { name: 'Markets', path: '/market-intelligence' },
  { name: 'Companies', path: '/company-updates' },
  { name: 'Sectors', path: '/sectors/Financials' },
  { name: 'Themes', path: '/themes/credit_growth' },
  { name: 'Research', path: '/research' },
  { name: 'Portfolio', path: '/portfolio' },
  { name: 'Macro', path: '/macro-intelligence' },
  { name: 'Predictions', path: '/predictions' },
  { name: 'Calendar', path: '/macro-intelligence#calendar' },
  { name: 'More', path: '/workspace' },
];

export default function OfficeNav({ onFocusSearch }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const tag = (e.target?.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || e.target?.isContentEditable) return;
        e.preventDefault();
        onFocusSearch?.();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onFocusSearch]);

  const primary = NAV.slice(0, 8);
  const more = NAV.slice(8);

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--io-border)] bg-[rgba(9,12,17,0.86)] backdrop-blur-xl">
      <div className="io-shell flex h-16 items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            className="lg:hidden rounded-lg border border-[var(--io-border)] p-2 text-[var(--io-ink-soft)]"
            onClick={() => setOpen((v) => !v)}
            aria-label="Menu"
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
          <Link to="/" className="flex items-center gap-2.5 shrink-0">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--io-gold-soft)] text-[var(--io-gold)] text-xs font-bold">
              AGI
            </span>
            <span className="hidden sm:block">
              <span className="block text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--io-gold)]">
                AGI
              </span>
              <span className="block text-xs font-semibold text-[var(--io-ink)] -mt-0.5">
                Investment Office
              </span>
            </span>
          </Link>
        </div>

        <nav className="hidden lg:flex items-center gap-1 min-w-0">
          {primary.map((item) => {
            const active =
              item.path === '/'
                ? location.pathname === '/'
                : location.pathname === item.path || location.pathname.startsWith(`${item.path}/`);
            return (
              <Link
                key={item.name}
                to={item.path}
                className={`rounded-lg px-2.5 py-1.5 text-[12px] font-semibold transition ${
                  active
                    ? 'bg-[var(--io-gold-soft)] text-[var(--io-gold)]'
                    : 'text-[var(--io-muted)] hover:text-[var(--io-ink)] hover:bg-[var(--io-surface)]'
                }`}
              >
                {item.name}
              </Link>
            );
          })}
          <div className="relative">
            <button
              type="button"
              onClick={() => setMoreOpen((v) => !v)}
              className="rounded-lg px-2.5 py-1.5 text-[12px] font-semibold text-[var(--io-muted)] hover:text-[var(--io-ink)] hover:bg-[var(--io-surface)]"
            >
              More
            </button>
            {moreOpen && (
              <div className="absolute right-0 mt-2 w-44 rounded-xl border border-[var(--io-border)] bg-[var(--io-bg-elevated)] p-1 shadow-xl">
                {more.map((item) => (
                  <Link
                    key={item.name}
                    to={item.path}
                    onClick={() => setMoreOpen(false)}
                    className="block rounded-lg px-3 py-2 text-xs font-semibold text-[var(--io-ink-soft)] hover:bg-[var(--io-surface)]"
                  >
                    {item.name}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </nav>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => onFocusSearch?.()}
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--io-border)] bg-[var(--io-surface)] px-3 py-2 text-xs text-[var(--io-muted)] hover:border-[var(--io-border-strong)]"
            aria-label="Universal search"
          >
            <Search className="h-3.5 w-3.5" />
            <span className="hidden md:inline">Search</span>
            <kbd className="hidden md:inline rounded border border-[var(--io-border)] px-1.5 py-0.5 text-[10px]">/</kbd>
          </button>
          <Link
            to="/workspace"
            className="rounded-xl border border-[var(--io-border)] p-2 text-[var(--io-muted)] hover:text-[var(--io-ink)]"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
          </Link>
          <Link
            to="/workspace"
            className="rounded-xl border border-[var(--io-border)] p-2 text-[var(--io-muted)] hover:text-[var(--io-ink)]"
            aria-label="Bookmarks"
          >
            <Bookmark className="h-4 w-4" />
          </Link>
          <button
            type="button"
            onClick={() => navigate(user ? '/workspace' : '/login')}
            className="rounded-xl border border-[var(--io-border)] p-2 text-[var(--io-muted)] hover:text-[var(--io-ink)]"
            aria-label="User profile"
          >
            <User className="h-4 w-4" />
          </button>
        </div>
      </div>

      {open && (
        <div className="border-t border-[var(--io-border)] bg-[var(--io-bg-elevated)] lg:hidden">
          <div className="io-shell grid grid-cols-2 gap-1 py-3">
            {NAV.map((item) => (
              <Link
                key={item.name}
                to={item.path}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-2 text-sm font-semibold text-[var(--io-ink-soft)] hover:bg-[var(--io-surface)]"
              >
                {item.name}
              </Link>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}
