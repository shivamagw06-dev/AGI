// src/components/Header.jsx
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Menu, X, User, LogOut, Sun, Moon, Edit2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { useToast } from '@/components/ui/use-toast';
import { supabase } from '@/lib/supabaseClient';

const Header = ({ currentPage, setCurrentPage }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [handle, setHandle] = useState('');

  // Prefer an env var, fallback to hardcoded ID (replace in .env.local: VITE_ADMIN_ID)
  const ADMIN_ID = import.meta?.env?.VITE_ADMIN_ID || 'c56e4d07-273c-49c9-86a5-a4445e687ece';

  // load profile handle once user logs in
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
      .then(({ data, error }) => {
        if (!mounted) return;
        if (error) {
          console.error('Profile fetch error:', error);
          setHandle(user.email?.split('@')[0] || 'me');
        } else if (!data) {
          setHandle(user.email?.split('@')[0] || 'me');
        } else {
          setHandle(data.handle || user.email?.split('@')[0] || 'me');
        }
      })
      .catch((err) => {
        console.error('Profile fetch catch:', err);
        if (mounted) setHandle(user.email?.split('@')[0] || 'me');
      });

    return () => {
      mounted = false;
    };
  }, [user]);
  const navItems = [
    { name: 'Home', page: 'home', path: '/' },
    { name: 'Live Articles', page: 'live-articles', path: '/sections/live-articles' },
    { name: 'Research Notes', page: 'research-notes', path: '/sections/research-notes' },
    { name: 'Deal Tracker', page: 'deal-tracker', path: '/sections/deal-tracker' },
    { name: 'Markets Dashboard', page: 'markets', path: '/sections/markets' },
    { name: 'Wealth Management', page: 'wealth-management', path: '/wealth-management' },
    // ✅ Added Business Page
    { name: 'Business', page: 'business', path: '/business' },
    { name: 'Events & Webinars', page: 'events-webinars', path: '/events' },
    { name: 'About Us', page: 'about', path: '/about' },
    { name: 'Contact', page: 'contact', path: '/contact' },
  ];  
  const handleNavClick = (page, path) => {
    if (typeof setCurrentPage === 'function') {
      try {
        setCurrentPage(page);
      } catch (err) {
        // ignore setCurrentPage errors
      }
    }

    if (path) navigate(path);
    setMobileMenuOpen(false);
    // small delay so navigation begins then scroll — avoids jumping when route changes instantly
    setTimeout(() => window.scrollTo({ top: 0, behavior: 'smooth' }), 50);
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
      toast?.({ title: 'Logged out', description: 'You have been signed out.' });
    } catch (err) {
      console.error('Logout failed', err);
      toast?.({ title: 'Logout failed', description: err?.message || 'Try again' });
    } finally {
      setMobileMenuOpen(false);
    }
  };

  return (
    <header className="sticky top-0 z-50 bg-background/95 backdrop-blur-sm border-b border-border">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center cursor-pointer"
            onClick={() => handleNavClick('home', '/')}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && handleNavClick('home', '/')}
          >
            <span className="text-xl md:text-2xl font-bold bg-gradient-to-r from-primary to-purple-800 bg-clip-text text-transparent">
              AGI
            </span>
          </motion.div>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center space-x-4">
            {navItems.map((item) => (
              <motion.button
                key={item.page}
                onClick={() => handleNavClick(item.page, item.path)}
                className={`text-sm font-medium transition-colors whitespace-nowrap px-2 py-1 rounded-md ${
                  currentPage === item.page
                    ? 'text-primary bg-primary/10'
                    : 'text-foreground/70 hover:text-primary hover:bg-primary/5'
                }`}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.98 }}
                aria-current={currentPage === item.page ? 'page' : undefined}
              >
                {item.name}
              </motion.button>
            ))}

            {/* Admin-only Write button */}
            {user?.id === ADMIN_ID && (
              <Button
                variant="secondary"
                onClick={() => handleNavClick('write', '/articles/new')}
                className="inline-flex items-center gap-2 ml-3"
                aria-label="Write new article"
              >
                <Edit2 className="h-4 w-4" />
                Write
              </Button>
            )}
          </div>

          {/* Right Side Buttons */}
          <div className="flex items-center gap-2">
            {/* Theme Toggle */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              title="Toggle theme"
              aria-pressed={theme === 'dark'}
            >
              {theme === 'dark' ? (
                <Sun className="h-[1.2rem] w-[1.2rem]" aria-hidden />
              ) : (
                <Moon className="h-[1.2rem] w-[1.2rem]" aria-hidden />
              )}
              <span className="sr-only">Toggle theme</span>
            </Button>

            {/* Profile / Auth */}
            <div className="hidden lg:block">
              {user ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      <span>{(user.email ?? 'User').split('@')[0]}</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => {
                        setMobileMenuOpen(false);
                        navigate('/profile/edit');
                      }}
                    >
                      Edit Profile
                    </DropdownMenuItem>
                    {handle && (
                      <DropdownMenuItem
                        onClick={() => {
                          setMobileMenuOpen(false);
                          navigate(`/u/${handle}`);
                        }}
                      >
                        View My Profile
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleLogout}>
                      <LogOut className="mr-2 h-4 w-4" />
                      <span>Log out</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : (
                <Button onClick={() => navigate('/login')}>Login / Sign Up</Button>
              )}
            </div>

            {/* Mobile Menu Icon */}
            <div className="lg:hidden">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                aria-expanded={mobileMenuOpen}
                aria-controls="mobile-menu"
              >
                {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
              </Button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <motion.div
            id="mobile-menu"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="lg:hidden overflow-hidden"
          >
            <div className="py-4 border-t border-border flex flex-col items-start">
              {navItems.map((item) => (
                <button
                  key={item.page}
                  onClick={() => handleNavClick(item.page, item.path)}
                  className={`block w-full text-left px-4 py-3 text-base font-medium ${
                    currentPage === item.page ? 'text-primary bg-primary/10' : 'text-foreground/80 hover:bg-accent'
                  }`}
                >
                  {item.name}
                </button>
              ))}

              <div className="px-4 pt-3 w-full">
                {user ? (
                  <>
                    {user.id === ADMIN_ID && (
                      <Button
                        onClick={() => {
                          setMobileMenuOpen(false);
                          navigate('/articles/new');
                        }}
                        variant="secondary"
                        className="w-full mb-2"
                        aria-label="Write a new article"
                      >
                        ✍️ Write a new article
                      </Button>
                    )}

                    <Button
                      onClick={() => {
                        setMobileMenuOpen(false);
                        navigate('/profile/edit');
                      }}
                      variant="outline"
                      className="w-full mb-2"
                    >
                      Edit Profile
                    </Button>

                    {handle && (
                      <Button
                        onClick={() => {
                          setMobileMenuOpen(false);
                          navigate(`/u/${handle}`);
                        }}
                        variant="outline"
                        className="w-full mb-2"
                      >
                        View My Profile
                      </Button>
                    )}

                    <Button
                      onClick={() => {
                        setMobileMenuOpen(false);
                        handleLogout();
                      }}
                      variant="outline"
                      className="w-full"
                    >
                      Log Out
                    </Button>
                  </>
                ) : (
                  <Button
                    onClick={() => {
                      setMobileMenuOpen(false);
                      navigate('/login');
                    }}
                    className="w-full"
                  >
                    Login / Sign Up
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </nav>
    </header>
  );
};

export default Header;
