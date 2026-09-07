import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/lib/supabaseClient';
import { CheckCircle2, Loader2, Mail } from 'lucide-react';
import {
  consumeSignupIntent,
  trackFunnelEvent,
  trackReturnedToIntended,
} from '@/lib/funnelAnalytics';

export default function VerifyEmailPage() {
  const { user, resendVerification } = useAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const next = searchParams.get('next') || '/';
  const safeNext = next.startsWith('/') ? next : '/';
  const [status, setStatus] = useState('checking');
  const [message, setMessage] = useState('');
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const { data } = await supabase.auth.getSession();
        const sessionUser = data.session?.user;
        if (!mounted) return;
        if (sessionUser?.email_confirmed_at || sessionUser?.confirmed_at || user?.email_confirmed_at) {
          setStatus('verified');
          const intent = consumeSignupIntent();
          trackFunnelEvent('signup_completed', {
            channel: intent?.channel || 'email',
            feature: intent?.feature || null,
            next: safeNext,
            via: 'verify_email',
          });
          trackReturnedToIntended(safeNext);
          setTimeout(() => navigate(safeNext, { replace: true }), 1200);
          return;
        }
        setStatus('pending');
      } catch {
        if (mounted) setStatus('pending');
      }
    })();
    return () => {
      mounted = false;
    };
  }, [navigate, safeNext, user]);

  const handleResend = async (e) => {
    e.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      await resendVerification(email || user?.email || '', {
        redirectTo: `${window.location.origin}/verify-email?next=${encodeURIComponent(safeNext)}`,
      });
      setMessage('Verification email sent. Check your inbox and spam folder.');
    } catch (err) {
      setMessage(err?.message || 'Unable to resend verification email.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f7fa] px-4 py-16">
      <div className="mx-auto max-w-lg border border-[#dce1e7] bg-white p-8 shadow-[0_16px_50px_rgba(15,35,60,0.08)]">
        {status === 'checking' && (
          <div className="flex items-center gap-3 text-sm text-[#667085]">
            <Loader2 className="h-5 w-5 animate-spin" /> Checking verification status…
          </div>
        )}

        {status === 'verified' && (
          <div>
            <CheckCircle2 className="h-10 w-10 text-[#087443]" />
            <h1 className="mt-4 text-2xl font-bold text-[#18202b]">Email verified</h1>
            <p className="mt-2 text-sm text-[#667085]">Taking you into AGI…</p>
          </div>
        )}

        {status === 'pending' && (
          <div>
            <Mail className="h-10 w-10 text-[#0d1d33]" />
            <h1 className="mt-4 text-2xl font-bold text-[#18202b]">Verify your email</h1>
            <p className="mt-2 text-sm leading-relaxed text-[#667085]">
              Open the verification email from{' '}
              <span className="font-semibold text-[#18202b]">support@agarwalglobalinvestments.com</span>{' '}
              and confirm your address. Then sign in with your password.
            </p>

            <form onSubmit={handleResend} className="mt-6 space-y-3">
              <input
                type="email"
                required
                placeholder="Email used at signup"
                value={email || user?.email || ''}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-[#cbd2da] px-3 py-3 text-sm focus:border-[#274c77] focus:outline-none"
              />
              <button
                type="submit"
                disabled={busy}
                className="w-full bg-[#0d1d33] px-4 py-3 text-sm font-bold text-white hover:bg-[#182f4e] disabled:opacity-50"
              >
                {busy ? 'Sending…' : 'Resend verification email'}
              </button>
            </form>

            {message && <p className="mt-4 text-xs text-[#445066]">{message}</p>}

            <div className="mt-6 flex flex-wrap gap-3 text-sm">
              <Link to={`/login?mode=signin&next=${encodeURIComponent(safeNext)}`} className="font-semibold text-[#274c77] hover:underline">
                Back to sign in
              </Link>
              <Link to="/" className="text-[#667085] hover:underline">
                Public research
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
