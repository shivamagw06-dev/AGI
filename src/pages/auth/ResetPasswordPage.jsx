import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { isStrongPassword, passwordChecks } from '@/lib/authValidation';
import { supabase } from '@/lib/supabaseClient';

export default function ResetPasswordPage() {
  const { updatePassword, user } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    let mounted = true;
    (async () => {
      const { data } = await supabase.auth.getSession();
      if (!mounted) return;
      setReady(Boolean(data.session?.user || user));
    })();
    const { data: sub } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY' || event === 'SIGNED_IN') setReady(true);
    });
    return () => {
      mounted = false;
      sub?.subscription?.unsubscribe?.();
    };
  }, [user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    if (!isStrongPassword(password)) {
      setError('Use 12+ characters with uppercase, lowercase, a number, and a symbol.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await updatePassword(password);
      setMessage('Password updated. You can continue to AGI.');
      setTimeout(() => navigate('/', { replace: true }), 1000);
    } catch (err) {
      setError(err?.message || 'Unable to update password.');
    } finally {
      setLoading(false);
    }
  };

  const checks = passwordChecks(password);

  return (
    <div className="min-h-screen bg-[#f5f7fa] px-4 py-16">
      <div className="mx-auto max-w-md border border-[#dce1e7] bg-white p-8 shadow-[0_16px_50px_rgba(15,35,60,0.08)]">
        <h1 className="text-2xl font-bold text-[#18202b]">Choose a new password</h1>
        <p className="mt-2 text-sm text-[#667085]">
          {ready
            ? 'Enter a strong password for your AGI account.'
            : 'Open this page from the password reset email link to continue.'}
        </p>

        {!ready ? (
          <div className="mt-6 space-y-3 text-sm">
            <p className="text-[#667085]">Waiting for a valid recovery session…</p>
            <Link to="/forgot-password" className="font-semibold text-[#274c77] hover:underline">
              Request a new reset link
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="password" className="mb-1 block text-sm font-medium">
                New password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-[#cbd2da] px-3 py-3 text-sm focus:border-[#274c77] focus:outline-none"
              />
              <ul className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-[#7b8491]">
                <li className={checks.minLength ? 'text-[#087443]' : ''}>12+ characters</li>
                <li className={checks.hasUpper ? 'text-[#087443]' : ''}>Uppercase</li>
                <li className={checks.hasLower ? 'text-[#087443]' : ''}>Lowercase</li>
                <li className={checks.hasNumber ? 'text-[#087443]' : ''}>Number</li>
                <li className={checks.hasSymbol ? 'text-[#087443]' : ''}>Symbol</li>
              </ul>
            </div>
            <div>
              <label htmlFor="confirm" className="mb-1 block text-sm font-medium">
                Confirm password
              </label>
              <input
                id="confirm"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full border border-[#cbd2da] px-3 py-3 text-sm focus:border-[#274c77] focus:outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#0d1d33] px-4 py-3 text-sm font-bold text-white hover:bg-[#182f4e] disabled:opacity-50"
            >
              {loading ? 'Updating…' : 'Update password'}
            </button>
          </form>
        )}

        {message && (
          <p className="mt-4 border border-[#b7ebcc] bg-[#ecfdf3] p-3 text-xs text-[#087443]">{message}</p>
        )}
        {error && (
          <p className="mt-4 border border-[#f7c5c0] bg-[#fff1f0] p-3 text-xs text-[#b42318]">{error}</p>
        )}
      </div>
    </div>
  );
}
