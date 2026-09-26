import { useEffect, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import {
  BookOpen,
  Building2,
  Bell,
  ChevronRight,
  Eye,
  FileText,
  Lock,
  LogOut,
  Shield,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { listResearchRuns } from '@/lib/intelligenceApi';

export default function ResearchPortal() {
  const { user, profile, hasPin, unlocked, logout, lock, devices, loading } = useAuth();
  const navigate = useNavigate();
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    listResearchRuns({ limit: '4' })
      .then((data) => setRecent(Array.isArray(data) ? data : data?.runs || []))
      .catch(() => setRecent([]));
  }, []);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-[#6b7280]">Loading portal…</div>;
  }
  if (!user || !hasPin || !unlocked) return <Navigate to="/login?next=/portal" replace />;

  const firstName =
    profile?.display_name?.split(' ')[0] ||
    user.user_metadata?.full_name?.split(' ')[0] ||
    user.email?.split('@')[0] ||
    'there';

  return (
    <div className="min-h-screen bg-[#f4f5f7]">
      <header className="border-b border-[#e5e7eb] bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <div>
            <Link to="/portal" className="font-[Georgia,serif] text-2xl font-semibold text-[#0a1e38]">
              AGI
            </Link>
            <p className="text-[11px] uppercase tracking-[0.16em] text-[#9ca3af]">Research Portal</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                lock();
                navigate('/login?next=/portal');
              }}
              className="rounded-lg border border-[#e5e7eb] px-3 py-2 text-xs font-medium text-[#374151] hover:bg-[#fafbfc]"
            >
              Lock
            </button>
            <Link
              to="/account/security"
              className="rounded-lg border border-[#e5e7eb] px-3 py-2 text-xs font-medium text-[#374151] hover:bg-[#fafbfc]"
            >
              Security
            </Link>
            <button
              type="button"
              onClick={async () => {
                await logout({ forgetDevice: false });
                navigate('/');
              }}
              className="inline-flex items-center gap-1 rounded-lg bg-[#0a1e38] px-3 py-2 text-xs font-semibold text-white"
            >
              <LogOut className="h-3.5 w-3.5" /> Logout
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#9ca3af]">Good to see you</p>
        <h1 className="mt-2 font-[Georgia,serif] text-4xl text-[#111827]">Welcome {firstName}</h1>
        <p className="mt-3 max-w-2xl text-[#6b7280]">
          Your institutional workspace — research notes, watchlists, and AI priorities in one place.
        </p>

        <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { to: '/research', label: 'Research Notes', icon: FileText, detail: 'Continue reading' },
            { to: '/beta/watchlists', label: 'Watchlist', icon: Eye, detail: 'Saved names' },
            { to: '/beta/companies', label: 'Saved Companies', icon: Building2, detail: 'Coverage desk' },
            { to: '/macro-intelligence', label: 'Macro Notes', icon: BookOpen, detail: 'Latest briefing' },
          ].map(({ to, label, icon: Icon, detail }) => (
            <Link
              key={to}
              to={to}
              className="rounded-2xl border border-[#e5e7eb] bg-white p-5 transition hover:border-[#0a1e38]/30"
            >
              <Icon className="h-5 w-5 text-[#0a1e38]" />
              <p className="mt-4 font-semibold text-[#111827]">{label}</p>
              <p className="mt-1 flex items-center gap-1 text-sm text-[#6b7280]">
                {detail} <ChevronRight className="h-3.5 w-3.5" />
              </p>
            </Link>
          ))}
        </section>

        <section className="mt-10 grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
          <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-[#0a1e38]" />
              <h2 className="font-[Georgia,serif] text-xl text-[#111827]">AI priorities for you</h2>
            </div>
            <ul className="mt-5 space-y-4 text-sm text-[#374151]">
              <li className="border-t border-[#e5e7eb] pt-4">
                Personalisation activates as you save companies and research — morning notes will emphasise your desk.
              </li>
              <li className="border-t border-[#e5e7eb] pt-4">
                Open Watchlists and Company pages to train your AGI feed.
              </li>
              <li className="border-t border-[#e5e7eb] pt-4">
                Latest reports stay available under Research without re-authentication on this trusted device.
              </li>
            </ul>
          </div>

          <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6">
            <h2 className="font-[Georgia,serif] text-xl text-[#111827]">Latest reports</h2>
            <div className="mt-4 space-y-3">
              {recent.length ? (
                recent.map((r) => (
                  <div key={r.run_id || r.id} className="border-t border-[#e5e7eb] pt-3 text-sm">
                    <p className="font-medium text-[#111827]">{r.query || r.desk || 'Research run'}</p>
                    <p className="text-xs text-[#9ca3af]">{r.status}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-[#6b7280]">No intelligence runs yet — explore Market Intelligence.</p>
              )}
            </div>
            <Link to="/beta/investment-office" className="mt-6 inline-block text-sm font-semibold text-[#0a1e38]">
              Open Investment Office →
            </Link>
          </div>
        </section>

        <section className="mt-10 grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              <h2 className="font-[Georgia,serif] text-xl">Notifications</h2>
            </div>
            <ul className="mt-4 space-y-3 text-sm">
              {[
                ['Morning Note', 'ON'],
                ['Pre-Market', 'ON'],
                ['Market Close', 'ON'],
                ['Research', 'ON'],
                ['Macro Reports', 'OFF'],
              ].map(([label, state]) => (
                <li key={label} className="flex justify-between border-t border-[#e5e7eb] pt-3">
                  <span>{label}</span>
                  <span className={state === 'ON' ? 'text-[#0f7a4a] font-semibold' : 'text-[#9ca3af]'}>{state}</span>
                </li>
              ))}
            </ul>
            <Link to="/account" className="mt-5 inline-block text-sm font-semibold text-[#0a1e38]">
              Manage account →
            </Link>
          </div>

          <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              <h2 className="font-[Georgia,serif] text-xl">Trusted devices</h2>
            </div>
            <ul className="mt-4 space-y-3 text-sm">
              {devices.length ? (
                devices.map((d) => (
                  <li key={d.id} className="flex justify-between border-t border-[#e5e7eb] pt-3">
                    <span>
                      <Lock className="mr-1 inline h-3.5 w-3.5" />
                      {d.label}
                    </span>
                    <span className="text-[#9ca3af]">This browser</span>
                  </li>
                ))
              ) : (
                <li className="border-t border-[#e5e7eb] pt-3 text-[#6b7280]">No trusted device stored yet.</li>
              )}
            </ul>
            <Link to="/account/security" className="mt-5 inline-block text-sm font-semibold text-[#0a1e38]">
              Security settings →
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
