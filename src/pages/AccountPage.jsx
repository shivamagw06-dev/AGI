import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

const LINKS = [
  { to: '/portal', label: 'Research Portal' },
  { to: '/profile/edit', label: 'Profile' },
  { to: '/research', label: 'Research Library' },
  { to: '/beta/watchlists', label: 'Watchlist' },
  { to: '/beta/screener', label: 'Saved Screens' },
  { to: '/account/security', label: 'Notifications' },
  { to: '/account/security', label: 'Security' },
];

export default function AccountPage() {
  const { user, profile, hasPin, unlocked, loading, logout } = useAuth();
  if (loading) return <div className="p-10 text-sm text-[#6b7280]">Loading…</div>;
  if (!user || !hasPin || !unlocked) return <Navigate to="/login?next=/account" replace />;

  const prefs = profile?.notification_prefs || {
    morning_note: true,
    pre_market: true,
    market_close: true,
    research: true,
    macro_reports: false,
  };

  return (
    <div className="min-h-screen bg-[#f4f5f7] px-4 py-10">
      <div className="mx-auto max-w-xl space-y-6">
        <div className="rounded-2xl border border-[#e5e7eb] bg-white p-8">
          <p className="font-[Georgia,serif] text-2xl text-[#0a1e38]">AGI</p>
          <h1 className="mt-4 font-[Georgia,serif] text-3xl text-[#111827]">Account</h1>
          <p className="mt-2 text-sm text-[#6b7280]">{user.email}</p>
          <nav className="mt-8 divide-y divide-[#e5e7eb] border-y border-[#e5e7eb]">
            {LINKS.map((item) => (
              <Link
                key={item.label}
                to={item.to}
                className="block py-4 text-sm font-medium text-[#111827] hover:text-[#0a1e38]"
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <button
            type="button"
            className="mt-8 w-full rounded-xl bg-[#0a1e38] px-4 py-3 text-sm font-semibold text-white"
            onClick={async () => {
              await logout();
              window.location.href = '/';
            }}
          >
            Logout
          </button>
        </div>

        <div className="rounded-2xl border border-[#e5e7eb] bg-white p-8">
          <h2 className="font-[Georgia,serif] text-xl text-[#111827]">Notifications</h2>
          <p className="mt-2 text-sm text-[#6b7280]">Preference defaults for your research desk.</p>
          <ul className="mt-6 space-y-3 text-sm">
            {[
              ['Morning Note', prefs.morning_note],
              ['Pre-Market', prefs.pre_market],
              ['Market Close', prefs.market_close],
              ['Research', prefs.research],
              ['Macro Reports', prefs.macro_reports],
            ].map(([label, on]) => (
              <li key={label} className="flex justify-between border-t border-[#e5e7eb] pt-3">
                <span>{label}</span>
                <span className={on ? 'font-semibold text-[#0f7a4a]' : 'text-[#9ca3af]'}>{on ? 'ON' : 'OFF'}</span>
              </li>
            ))}
          </ul>
          <Link to="/account/security" className="mt-5 inline-block text-sm font-semibold text-[#0a1e38]">
            Security & devices →
          </Link>
        </div>
      </div>
    </div>
  );
}
