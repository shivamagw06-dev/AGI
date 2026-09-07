import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { clearTrustedDevice } from '@/lib/pinAuth';

export default function AccountSecurityPage() {
  const { user, hasPin, unlocked, devices, logout, lock, loading } = useAuth();

  if (loading) return <div className="p-10 text-sm text-[#6b7280]">Loading…</div>;
  if (!user || !hasPin || !unlocked) return <Navigate to="/login?next=/account/security" replace />;

  return (
    <div className="min-h-screen bg-[#f4f5f7] px-4 py-10">
      <div className="mx-auto max-w-2xl rounded-2xl border border-[#e5e7eb] bg-white p-8">
        <Link to="/portal" className="text-xs font-medium text-[#6b7280]">
          ← Research Portal
        </Link>
        <h1 className="mt-4 font-[Georgia,serif] text-3xl text-[#111827]">Security</h1>
        <p className="mt-2 text-sm text-[#6b7280]">{user.email}</p>

        <section className="mt-8">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-[#9ca3af]">PIN</h2>
          <p className="mt-3 text-sm text-[#374151]">
            {hasPin ? 'A 6-digit PIN is set on this account.' : 'No PIN set yet.'}
          </p>
          <Link to="/login?next=/portal" className="mt-3 inline-block text-sm font-semibold text-[#0a1e38]">
            Forgot PIN / reset via OTP →
          </Link>
        </section>

        <section className="mt-10">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-[#9ca3af]">Devices</h2>
          <ul className="mt-4 space-y-3">
            {devices.map((d) => (
              <li key={d.id} className="flex items-center justify-between border-t border-[#e5e7eb] pt-3 text-sm">
                <div>
                  <p className="font-medium text-[#111827]">{d.label}</p>
                  <p className="text-xs text-[#9ca3af]">Trusted · expires {new Date(d.expires_at).toLocaleDateString()}</p>
                </div>
                <button
                  type="button"
                  className="text-xs font-semibold text-[#b42318]"
                  onClick={() => {
                    clearTrustedDevice();
                    lock();
                    window.location.href = '/login?next=/portal';
                  }}
                >
                  Remove
                </button>
              </li>
            ))}
            {!devices.length && <li className="text-sm text-[#6b7280]">No trusted browsers.</li>}
          </ul>
        </section>

        <button
          type="button"
          className="mt-10 w-full rounded-xl border border-[#e5e7eb] px-4 py-3 text-sm font-semibold text-[#111827]"
          onClick={async () => {
            await logout({ forgetDevice: true });
            window.location.href = '/';
          }}
        >
          Log out & forget this device
        </button>
      </div>
    </div>
  );
}
