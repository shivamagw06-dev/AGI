import { Search, Menu, X, User, LogOut, Edit2, Shield, Briefcase, LayoutDashboard, Gauge, Activity, Bell, Bookmark, CreditCard, Settings, Newspaper, ListChecks, Library, Landmark, ChevronDown } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import { useToast } from '@/components/ui/use-toast';
import { supabase } from '@/lib/supabaseClient';
import { isAdmin } from '@/lib/adminAuth';
import { firstNameFromUser } from '@/lib/authValidation';
import Logo from '@/components/Layout/Logo';
import MarketOutlookStrip from '@/components/Home/MarketOutlookStrip';
import ResearchSearch from '@/components/Search/ResearchSearch';
import { buildLoginUrl } from '@/lib/accessPolicy';

const PRIMARY_NAV = [
  { name: 'Market Intelligence', path: '/market-intelligence' },
  { name: 'Portfolio', path: '/portfolio' },
  { name: 'Live Desk', path: '/live-desk' },
  { name: 'Hedge Fund', path: '/hedge-fund' },
  { name: 'Live Alpha', path: '/live-alpha' },
];

const MORE_NAV = [
  { name: 'Insider Activity', path: '/insider-activity' },
  { name: 'Private Markets', path: '/private-markets' },
  { name: 'Global Markets', path: '/global-markets' },
  { name: 'FX Intelligence', path: '/economics' },
  { name: 'US Market', path: '/us-stock-intelligence' },
];

const MOBILE_NAV = [{ name: 'Home', path: '/' }, ...PRIMARY_NAV, ...MORE_NAV];

function navItemClass(active) {
  return `h-full shrink-0 px-2.5 xl:px-3 text-[13px] font-medium border-b-2 border-transparent transition-colors whitespace-nowrap focus:outline-none focus:shadow-none focus-visible:bg-[#f5f5f5] ${
    active
      ? 'text-[#111111] border-b-[#111111]'
      : 'text-[#444444] hover:text-[#111111] hover:border-b-[#cccccc]'
  }`;
}

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const { user, logout, logoutAllDevices } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [handle, setHandle] = useState('');
  const userIsAdmin = isAdmin(user);
  const firstName = firstNameFromUser(user);
  const returnTo = `${location.pathname}${location.search || ''}` || '/';
  const loginHref = buildLoginUrl({ returnTo, mode: 'signin' });
  const signupHref = buildLoginUrl({ returnTo, mode: 'signup' });

  useEffect(() => {
    if (!user) {
      setHandle('');
      return;
    }
    let mounted = true;
    supabase
      .from('profiles')
      .select('handle')
      .eq('id', user.id)
      .maybeSingle()
      .then(({ data }) => {
        if (mounted) setHandle(data?.handle || user.email?.split('@')[0] || 'me');
      });
    return () => {
      mounted = false;
    };
  }, [user]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const tag = (e.target?.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || e.target?.isContentEditable) return;
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/';
    if (path.startsWith('/#')) return location.pathname === '/' && location.hash === path.slice(1);
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  const go = (path) => {
    setMobileOpen(false);
    setSearchOpen(false);
    if (path.startsWith('/#')) {
      const hash = path.slice(1);
      if (location.pathname === '/') {
        const el = document.querySelector(hash);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          return;
        }
      }
      navigate({ pathname: '/', hash: hash.slice(1) });
      return;
    }
    navigate(path);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
      toast?.({ title: 'Signed out' });
    } catch (err) {
      toast?.({ title: 'Error', description: err?.message, variant: 'destructive' });
    }
  };

  const handleLogoutAll = async () => {
    try {
      await logoutAllDevices();
      navigate('/');
      toast?.({ title: 'Signed out of all devices' });
    } catch (err) {
      toast?.({ title: 'Error', description: err?.message, variant: 'destructive' });
    }
  };

  return (
    <header className="sticky top-0 z-50 bg-white shadow-sm">
      <div className="border-b border-[#dddddd]">
        <div className="max-w-[1800px] mx-auto px-4 sm:px-6">
          <div className="flex items-center h-[58px] gap-3 min-w-0 overflow-hidden">
            <Logo className="relative z-20 shrink-0" />

            <nav className="hidden xl:flex min-w-0 flex-1 items-center justify-end h-full overflow-hidden">
              {PRIMARY_NAV.map((item) => (
                <button
                  key={item.path}
                  type="button"
                  onClick={() => go(item.path)}
                  className={navItemClass(isActive(item.path))}
                >
                  {item.name}
                </button>
              ))}
              <div className="hidden min-[1680px]:flex h-full items-center">
                {MORE_NAV.map((item) => (
                  <button
                    key={item.path}
                    type="button"
                    onClick={() => go(item.path)}
                    className={navItemClass(isActive(item.path))}
                  >
                    {item.name}
                  </button>
                ))}
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    className={`${navItemClass(MORE_NAV.some((item) => isActive(item.path)))} min-[1680px]:hidden inline-flex items-center gap-0.5`}
                    aria-label="More desks"
                  >
                    More
                    <ChevronDown className="w-3.5 h-3.5" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-52">
                  {MORE_NAV.map((item) => (
                    <DropdownMenuItem
                      key={item.path}
                      onClick={() => go(item.path)}
                      className={isActive(item.path) ? 'font-semibold text-[#111]' : ''}
                    >
                      {item.name}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </nav>

            <div className="ml-auto flex items-center gap-1.5 shrink-0 relative z-20">
              <button
                type="button"
                onClick={() => setSearchOpen(true)}
                className="p-2 text-[#111111] hover:bg-[#f5f5f5] rounded-sm"
                aria-label="Universal search"
              >
                <Search className="w-5 h-5" />
              </button>

              {user ? (
                <>
                  <button
                    type="button"
                    onClick={() => go('/workspace')}
                    className="hidden sm:inline-flex p-2 text-[#111111] hover:bg-[#f5f5f5]"
                    aria-label="Notifications"
                    title="Notifications"
                  >
                    <Bell className="w-5 h-5" />
                  </button>

                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" className="hidden sm:flex h-8 text-xs text-[#111111]">
                        <User className="w-4 h-4 mr-1" />
                        Account
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                      <DropdownMenuLabel className="font-normal">
                        <div className="text-sm font-semibold text-[#111]">{firstName}</div>
                        <div className="truncate text-[11px] text-[#767676]">{user.email}</div>
                      </DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => go('/workspace')}>
                        <LayoutDashboard className="w-4 h-4 mr-2" /> Dashboard
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => go('/workspace')}>
                        <Bookmark className="w-4 h-4 mr-2" /> Saved Articles
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => go('/workspace')}>
                        <ListChecks className="w-4 h-4 mr-2" /> Watchlist
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => go('/#newsletter')}>
                        <Newspaper className="w-4 h-4 mr-2" /> Newsletter
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => go('/profile/edit')}>
                        <Settings className="w-4 h-4 mr-2" /> Settings
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => go('/#newsletter')}>
                        <Briefcase className="w-4 h-4 mr-2" /> Subscription
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => go('/account/security')}>
                        <CreditCard className="w-4 h-4 mr-2" /> Billing
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => go('/account/security')}>
                        <Shield className="w-4 h-4 mr-2" /> Security &amp; PIN
                      </DropdownMenuItem>
                      {handle && (
                        <DropdownMenuItem onClick={() => go(`/u/${handle}`)}>
                          <User className="w-4 h-4 mr-2" /> Public profile
                        </DropdownMenuItem>
                      )}
                      {userIsAdmin && (
                        <>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => go('/admin')}>
                            <Edit2 className="w-4 h-4 mr-2" /> CMS
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => go('/admin/institutional-intelligence')}>
                            <Activity className="w-4 h-4 mr-2" /> Institutional Intelligence
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => go('/admin/mission-control')}>
                            <Gauge className="w-4 h-4 mr-2" /> Mission Control
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => go('/admin/knowledge-operations')}>
                            <Library className="w-4 h-4 mr-2" /> Knowledge Operations
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => go('/admin/investment-office')}>
                            <Landmark className="w-4 h-4 mr-2" /> Investment Office
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => go('/admin/founder-portfolio')}>
                            <Briefcase className="w-4 h-4 mr-2" /> Founder Portfolio
                          </DropdownMenuItem>
                        </>
                      )}
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={handleLogout}>
                        <LogOut className="w-4 h-4 mr-2" /> Logout
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={handleLogoutAll}>
                        Sign out all devices
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => go(loginHref)}
                    className="hidden sm:block text-sm font-medium text-[#111111] hover:underline px-2"
                  >
                    Login
                  </button>
                  <button
                    type="button"
                    onClick={() => go(signupHref)}
                    className="hidden sm:block rounded-md bg-[#0b1f33] text-white text-sm font-bold px-4 py-1.5 hover:bg-[#163353]"
                  >
                    Sign up free
                  </button>
                </>
              )}

              <button
                type="button"
                className="xl:hidden p-2"
                onClick={() => setMobileOpen(!mobileOpen)}
                aria-label="Menu"
              >
                {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {mobileOpen && (
        <nav className="xl:hidden border-b border-[#ddd] bg-white px-4 py-2">
          {MOBILE_NAV.map((item) => (
            <button
              key={item.path}
              type="button"
              onClick={() => go(item.path)}
              className={`block w-full text-left py-3 text-sm font-medium border-b border-[#eee] ${
                isActive(item.path) ? 'text-[#111111] font-semibold' : 'text-[#111]'
              }`}
            >
              {item.name}
            </button>
          ))}
          {!user ? (
            <div className="grid grid-cols-2 gap-2 py-3">
              <button
                type="button"
                onClick={() => go(loginHref)}
                className="min-h-[44px] border border-[#111111] px-3 text-sm font-bold text-[#111111]"
              >
                Login
              </button>
              <button
                type="button"
                onClick={() => go(signupHref)}
                className="min-h-[44px] rounded-md bg-[#0b1f33] px-3 text-sm font-bold text-white"
              >
                Sign up free
              </button>
            </div>
          ) : (
            <div className="space-y-1 border-t border-[#eee] py-3">
              <p className="px-1 pb-2 text-xs text-[#767676]">Signed in as {firstName}</p>
              <button type="button" onClick={() => go('/workspace')} className="block w-full py-2.5 text-left text-sm font-medium">
                Dashboard
              </button>
              <button type="button" onClick={() => go('/workspace')} className="block w-full py-2.5 text-left text-sm font-medium">
                Watchlist
              </button>
              <button type="button" onClick={() => go('/profile/edit')} className="block w-full py-2.5 text-left text-sm font-medium">
                Settings
              </button>
              {userIsAdmin ? (
                <>
                  <button
                    type="button"
                    onClick={() => go('/admin/knowledge-operations')}
                    className="block w-full py-2.5 text-left text-sm font-bold text-[#0b1f33]"
                  >
                    Knowledge Operations
                  </button>
                  <button
                    type="button"
                    onClick={() => go('/admin/investment-office')}
                    className="block w-full py-2.5 text-left text-sm font-bold text-[#0b1f33]"
                  >
                    Investment Office
                  </button>
                </>
              ) : null}
              <button type="button" onClick={handleLogout} className="block w-full py-2.5 text-left text-sm font-medium text-[#b42318]">
                Logout
              </button>
            </div>
          )}
        </nav>
      )}

      <MarketOutlookStrip />

      {searchOpen && <ResearchSearch onClose={() => setSearchOpen(false)} />}
    </header>
  );
}
