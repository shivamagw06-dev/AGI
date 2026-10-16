import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { isValidEmail } from '@/lib/authValidation';
import { ArrowLeft } from 'lucide-react';

export default function ForgotPasswordPage() {
  const { requestPasswordReset, isConfigured } = useAuth();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');
    if (!isValidEmail(email)) {
      setError('Enter a valid email address.');
      return;
    }
    setLoading(true);
    try {
      const redirectTo =
        typeof window !== 'undefined'
          ? `${window.location.origin}/reset-password`
          : 'https://agarwalglobalinvestments.com/reset-password';
      await requestPasswordReset(email, redirectTo);
      setMessage(
        `If an account exists for ${email.trim()}, a password reset link from support@agarwalglobalinvestments.com is on its way.`
      );
    } catch (err) {
      if (!isConfigured) {
        setError(err?.message || 'Authentication is not configured on this deployment.');
      } else {
        setError(err?.message || 'Unable to send reset email.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f7fa] px-4 py-16">
      <div className="mx-auto max-w-md border border-[#dce1e7] bg-white p-8 shadow-[0_16px_50px_rgba(15,35,60,0.08)]">
        <Link to="/login?mode=signin" className="inline-flex items-center gap-2 text-xs font-bold text-[#59616d]">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to sign in
        </Link>
        <h1 className="mt-6 text-2xl font-bold text-[#18202b]">Reset your password</h1>
        <p className="mt-2 text-sm text-[#667085]">
          We will email a secure reset link from Agarwal Global Investments.
        </p>
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-[#cbd2da] px-3 py-3 text-sm focus:border-[#274c77] focus:outline-none"
              placeholder="you@example.com"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#0d1d33] px-4 py-3 text-sm font-bold text-white hover:bg-[#182f4e] disabled:opacity-50"
          >
            {loading ? 'Sending…' : 'Send reset link'}
          </button>
        </form>
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
