import { useMemo, useRef, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { isSupabaseConfigured, supabase } from '../lib/supabaseClient';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { isAdmin } from '@/lib/adminAuth';
import { validateSignup, passwordChecks, isValidEmail } from '@/lib/authValidation';
import { ArrowLeft, Check, Eye, EyeOff, Lock, Mail } from 'lucide-react';

const AUTH_UNCONFIGURED =
  'Sign-in is not configured on this site build. Supabase auth keys are missing — redeploy the frontend with VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.';

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="mr-2 h-5 w-5" aria-hidden="true">
      <path fill="#4285F4" d="M21.35 12.27c0-.74-.07-1.45-.19-2.14H12v4.05h5.24a4.48 4.48 0 0 1-1.94 2.94v2.63h3.14c1.84-1.7 2.91-4.2 2.91-7.48Z" />
      <path fill="#34A853" d="M12 21.75c2.62 0 4.82-.87 6.42-2.36l-3.14-2.63c-.87.58-1.98.93-3.28.93-2.52 0-4.65-1.7-5.41-3.99H3.34v2.72A9.7 9.7 0 0 0 12 21.75Z" />
      <path fill="#FBBC05" d="M6.59 13.7A5.83 5.83 0 0 1 6.3 12c0-.59.1-1.15.29-1.7V7.58H3.34a9.73 9.73 0 0 0 0 8.84l3.25-2.72Z" />
      <path fill="#EA4335" d="M12 6.31c1.42 0 2.69.49 3.69 1.45l2.77-2.77C16.81 3.45 14.62 2.5 12 2.5a9.7 9.7 0 0 0-8.66 5.08l3.25 2.72C7.35 8.01 9.48 6.31 12 6.31Z" />
    </svg>
  );
}

function LinkedInMark() {
  return (
    <svg viewBox="0 0 24 24" className="mr-2 h-5 w-5 text-[#0a66c2]" aria-hidden="true" fill="currentColor">
      <path d="M20.45 3H3.55A.55.55 0 0 0 3 3.55v16.9c0 .3.25.55.55.55h16.9c.3 0 .55-.25.55-.55V3.55A.55.55 0 0 0 20.45 3ZM8.34 18.34H5.67V9.76h2.67v8.58ZM7 8.58a1.55 1.55 0 1 1 0-3.1 1.55 1.55 0 0 1 0 3.1Zm11.35 9.76h-2.66v-4.17c0-.99-.02-2.26-1.38-2.26-1.38 0-1.59 1.08-1.59 2.19v4.24h-2.66V9.76h2.55v1.17h.04c.36-.67 1.22-1.38 2.51-1.38 2.69 0 3.19 1.77 3.19 4.07v4.72Z" />
    </svg>
  );
}

function Field({ id, label, error, children }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-[#18202b]">
        {label}
      </label>
      {children}
      {error ? <p id={`${id}-error`} className="mt-1 text-xs text-[#b42318]">{error}</p> : null}
    </div>
  );
}

function PasswordStrength({ password }) {
  const checks = passwordChecks(password);
  const items = [
    { ok: checks.minLength, label: '12+ characters' },
    { ok: checks.hasUpper, label: 'Uppercase' },
    { ok: checks.hasLower, label: 'Lowercase' },
    { ok: checks.hasNumber, label: 'Number' },
    { ok: checks.hasSymbol, label: 'Symbol' },
  ];
  if (!password) return null;
  return (
    <ul className="mt-2 grid grid-cols-2 gap-1 text-[11px]">
      {items.map((item) => (
        <li key={item.label} className={item.ok ? 'text-[#087443]' : 'text-[#7b8491]'}>
          {item.ok ? '✓' : '○'} {item.label}
        </li>
      ))}
    </ul>
  );
}

export default function LoginPage() {
  const { user, register, loginWithPassword, resendVerification } = useAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const next = searchParams.get('next') || searchParams.get('redirect') || '/';
  const safeNext = next.startsWith('/') ? next : '/';
  const [mode, setMode] = useState(searchParams.get('mode') === 'signup' ? 'signup' : 'signin');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [acceptPrivacy, setAcceptPrivacy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [message, setMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [pendingVerifyEmail, setPendingVerifyEmail] = useState('');
  const formRef = useRef(null);
  const busy = loading || oauthLoading !== null;

  const redirectTo =
    typeof window !== 'undefined'
      ? `${window.location.origin}${safeNext}`
      : 'https://agarwalglobalinvestments.com';

  const subtitle = useMemo(
    () =>
      mode === 'signup'
        ? 'Create your AGI account with email and password.'
        : 'Sign in with your verified email and password.',
    [mode]
  );

  const resetAlerts = () => {
    setMessage('');
    setErrorMessage('');
    setFieldErrors({});
  };

  const focusFirstInvalid = (errors) => {
    const first = Object.keys(errors)[0];
    requestAnimationFrame(() => formRef.current?.querySelector(`#${first}`)?.focus());
  };

  const switchMode = (nextMode) => {
    if (busy || nextMode === mode) return;
    setMode(nextMode);
    setPassword('');
    setConfirmPassword('');
    setShowPassword(false);
    setShowConfirmPassword(false);
    setAcceptTerms(false);
    setAcceptPrivacy(false);
    resetAlerts();
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    resetAlerts();
    if (!isSupabaseConfigured) {
      setErrorMessage(AUTH_UNCONFIGURED);
      return;
    }
    const errors = validateSignup({
      fullName,
      email,
      password,
      confirmPassword,
      acceptTerms,
      acceptPrivacy,
    });
    setFieldErrors(errors);
    if (Object.keys(errors).length) {
      focusFirstInvalid(errors);
      return;
    }

    setLoading(true);
    try {
      const data = await register({
        fullName,
        email,
        password,
        emailRedirectTo: `${window.location.origin}/verify-email?next=${encodeURIComponent(safeNext)}`,
      });
      if (data?.session?.user) {
        navigate(isAdmin(data.session.user) ? '/admin' : safeNext, { replace: true });
        return;
      }
      setPendingVerifyEmail(email.trim());
      setMessage('Account created. Check your inbox to verify your email, then sign in.');
      setMode('signin');
      setPassword('');
      setConfirmPassword('');
    } catch (err) {
      setErrorMessage(err?.message || 'Unable to create your account.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignin = async (e) => {
    e.preventDefault();
    resetAlerts();
    if (!isSupabaseConfigured) {
      setErrorMessage(AUTH_UNCONFIGURED);
      return;
    }
    if (!isValidEmail(email)) {
      const errors = { email: 'Enter a valid email address.' };
      setFieldErrors(errors);
      focusFirstInvalid(errors);
      return;
    }
    if (!password) {
      const errors = { password: 'Enter your password.' };
      setFieldErrors(errors);
      focusFirstInvalid(errors);
      return;
    }

    setLoading(true);
    try {
      const data = await loginWithPassword(email, password);
      const loggedIn = data?.user;
      if (!loggedIn?.email_confirmed_at && !loggedIn?.confirmed_at) {
        setPendingVerifyEmail(email.trim());
        setErrorMessage('Please verify your email before signing in. Check your inbox for the AGI verification link.');
        return;
      }
      navigate(isAdmin(loggedIn) ? '/admin' : safeNext, { replace: true });
    } catch (err) {
      const msg = err?.message || 'Unable to sign in.';
      if (/email not confirmed|confirm/i.test(msg)) {
        setPendingVerifyEmail(email.trim());
      }
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    const target = pendingVerifyEmail || email;
    if (!isValidEmail(target)) {
      setErrorMessage('Enter the email used at signup to resend verification.');
      return;
    }
    setLoading(true);
    resetAlerts();
    try {
      await resendVerification(target, {
        redirectTo: `${window.location.origin}/verify-email?next=${encodeURIComponent(safeNext)}`,
      });
      setMessage('If this account needs verification, an email will arrive shortly.');
    } catch (err) {
      setErrorMessage(err?.message || 'Unable to resend verification email.');
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthLogin = async (provider) => {
    try {
      if (mode === 'signup' && (!acceptTerms || !acceptPrivacy)) {
        const errors = {
          ...(!acceptTerms ? { acceptTerms: 'Accept the Terms & Conditions to continue.' } : {}),
          ...(!acceptPrivacy ? { acceptPrivacy: 'Accept the Privacy Policy to continue.' } : {}),
        };
        setFieldErrors(errors);
        focusFirstInvalid(errors);
        return;
      }
      setOauthLoading(provider);
      resetAlerts();
      if (!isSupabaseConfigured) throw new Error(AUTH_UNCONFIGURED);
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: { redirectTo },
      });
      if (error) throw error;
    } catch (err) {
      setErrorMessage(err.message || `Unable to continue with ${provider}.`);
      setOauthLoading(null);
    }
  };

  if (user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5f7fa] px-4">
        <div className="w-full max-w-md border border-[#dce1e7] bg-white p-6 shadow-[0_16px_50px_rgba(15,35,60,0.08)]">
          <h1 className="text-xl font-semibold text-[#18202b]">You are already signed in</h1>
          <p className="mt-2 text-sm text-[#667085]">Continue to your AGI workspace.</p>
          <button
            type="button"
            className="mt-6 w-full bg-[#0d1d33] px-4 py-3 text-sm font-bold text-white hover:bg-[#182f4e]"
            onClick={() => navigate(isAdmin(user) ? '/admin' : safeNext)}
          >
            {isAdmin(user) ? 'Go to CMS' : 'Continue'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f5f7fa] px-4 py-10">
      <div className="mx-auto grid max-w-5xl overflow-hidden border border-[#dce1e7] bg-white shadow-[0_16px_50px_rgba(15,35,60,0.08)] lg:grid-cols-2">
        <aside className="hidden bg-[#0d1d33] p-10 text-white lg:block">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#a7c5ec]">
            Agarwal Global Investments
          </p>
          <h1 className="mt-5 text-4xl font-bold leading-tight">
            Understand markets.
            <br />
            Stay in control.
          </h1>
          <p className="mt-5 max-w-sm text-sm leading-relaxed text-[#c6d4e7]">
            Create a secure AGI account to save research preferences, unlock personal workspace tools,
            and keep your session protected with an optional device PIN.
          </p>
          <ul className="mt-10 space-y-4 text-sm text-[#dbe7f6]">
            {[
              'Email + password with verification',
              'Persistent signed-in sessions',
              'Optional device PIN unlock',
              'No trading calls or investment recommendations',
            ].map((item) => (
              <li key={item} className="flex items-start gap-3">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#76d2a4]" />
                {item}
              </li>
            ))}
          </ul>
        </aside>

        <div className="p-6 sm:p-10">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-xs font-bold text-[#59616d] hover:text-[#111]"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to public research
          </Link>
          <h2 className="mt-8 text-2xl font-bold text-[#18202b]">
            {mode === 'signup' ? 'Create your account' : 'Welcome back'}
          </h2>
          <p className="mt-2 text-sm text-[#667085]">{subtitle}</p>

          {!isSupabaseConfigured && (
            <p className="mt-4 border border-[#f7c5c0] bg-[#fff1f0] p-3 text-xs text-[#b42318]">
              {AUTH_UNCONFIGURED}
            </p>
          )}

          <div className="mt-6 grid grid-cols-2 rounded-sm border border-[#dce1e7] p-1 text-sm font-semibold">
            <button
              type="button"
              onClick={() => {
                switchMode('signup');
              }}
              disabled={busy}
              className={`rounded-sm py-2 ${mode === 'signup' ? 'bg-[#0d1d33] text-white' : 'text-[#667085]'}`}
            >
              Sign up
            </button>
            <button
              type="button"
              onClick={() => {
                switchMode('signin');
              }}
              disabled={busy}
              className={`rounded-sm py-2 ${mode === 'signin' ? 'bg-[#0d1d33] text-white' : 'text-[#667085]'}`}
            >
              Sign in
            </button>
          </div>

          <form
            onSubmit={mode === 'signup' ? handleSignup : handleSignin}
            ref={formRef}
            className="mt-6 space-y-4"
            noValidate
          >
            {mode === 'signup' && (
              <Field id="fullName" label="Full name" error={fieldErrors.fullName}>
                <input
                  id="fullName"
                  type="text"
                  autoComplete="name"
                  className="w-full border border-[#cbd2da] bg-white px-3 py-3 text-sm focus:border-[#274c77] focus:outline-none"
                  placeholder="Your full name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  aria-invalid={Boolean(fieldErrors.fullName)}
                  aria-describedby={fieldErrors.fullName ? 'fullName-error' : undefined}
                />
              </Field>
            )}

            <Field id="email" label="Email" error={fieldErrors.email}>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                className="w-full border border-[#cbd2da] bg-white px-3 py-3 text-sm focus:border-[#274c77] focus:outline-none"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? 'email-error' : undefined}
              />
            </Field>

            <Field id="password" label="Password" error={fieldErrors.password}>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                  required
                  className="w-full border border-[#cbd2da] bg-white px-3 py-3 pr-11 text-sm focus:border-[#274c77] focus:outline-none"
                  placeholder={mode === 'signup' ? 'Create a strong password' : 'Your password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={Boolean(fieldErrors.password)}
                  aria-describedby={fieldErrors.password ? 'password-error' : mode === 'signup' ? 'password-help' : undefined}
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#667085]"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {mode === 'signup' ? <div id="password-help"><PasswordStrength password={password} /></div> : null}
            </Field>

            {mode === 'signup' && (
              <Field id="confirmPassword" label="Confirm password" error={fieldErrors.confirmPassword}>
                <input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  className="w-full border border-[#cbd2da] bg-white px-3 py-3 text-sm focus:border-[#274c77] focus:outline-none"
                  placeholder="Re-enter password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  aria-invalid={Boolean(fieldErrors.confirmPassword)}
                  aria-describedby={fieldErrors.confirmPassword ? 'confirmPassword-error' : undefined}
                />
                <button type="button" onClick={() => setShowConfirmPassword((v) => !v)} aria-label={showConfirmPassword ? 'Hide confirmation password' : 'Show confirmation password'} className="text-xs font-semibold text-[#667085]">
                  {showConfirmPassword ? 'Hide' : 'Show'}
                </button>
              </Field>
            )}

            {mode === 'signup' && (
              <div className="space-y-2 text-sm text-[#445066]">
                <label className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={acceptTerms}
                    id="acceptTerms"
                    aria-invalid={Boolean(fieldErrors.acceptTerms)}
                    aria-describedby={fieldErrors.acceptTerms ? 'acceptTerms-error' : undefined}
                    onChange={(e) => setAcceptTerms(e.target.checked)}
                  />
                  <span>
                    I accept the{' '}
                    <Link to="/terms" className="underline">
                      Terms &amp; Conditions
                    </Link>
                    .
                  </span>
                </label>
                {fieldErrors.acceptTerms ? (
                  <p id="acceptTerms-error" className="text-xs text-[#b42318]">{fieldErrors.acceptTerms}</p>
                ) : null}
                <label className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={acceptPrivacy}
                    id="acceptPrivacy"
                    aria-invalid={Boolean(fieldErrors.acceptPrivacy)}
                    aria-describedby={fieldErrors.acceptPrivacy ? 'acceptPrivacy-error' : undefined}
                    onChange={(e) => setAcceptPrivacy(e.target.checked)}
                  />
                  <span>
                    I accept the{' '}
                    <Link to="/privacy" className="underline">
                      Privacy Policy
                    </Link>
                    .
                  </span>
                </label>
                {fieldErrors.acceptPrivacy ? (
                  <p id="acceptPrivacy-error" className="text-xs text-[#b42318]">{fieldErrors.acceptPrivacy}</p>
                ) : null}
              </div>
            )}

            {mode === 'signin' && (
              <div className="flex justify-end">
                <Link to="/forgot-password" className="text-xs font-semibold text-[#274c77] hover:underline">
                  Forgot password?
                </Link>
              </div>
            )}

            <button
              type="submit"
              disabled={busy}
              className="w-full bg-[#0d1d33] px-4 py-3 text-sm font-bold text-white hover:bg-[#182f4e] disabled:opacity-50"
            >
              {mode === 'signup' ? (
                <>
                  <Mail className="mr-2 inline h-4 w-4" />
                  {loading ? 'Creating account…' : 'Create account'}
                </>
              ) : (
                <>
                  <Lock className="mr-2 inline h-4 w-4" />
                  {loading ? 'Signing in…' : 'Sign in'}
                </>
              )}
            </button>
          </form>

          {(pendingVerifyEmail || message.includes('verification')) && (
            <button
              type="button"
              onClick={handleResend}
              disabled={busy}
              className="mt-3 w-full border border-[#cbd2da] px-4 py-2.5 text-xs font-semibold text-[#18202b] hover:bg-[#f8fafb] disabled:opacity-50"
            >
              Resend verification email
            </button>
          )}

          {message && (
            <p className="mt-4 border border-[#b7ebcc] bg-[#ecfdf3] p-3 text-xs text-[#087443]">{message}</p>
          )}
          {errorMessage && (
            <p className="mt-4 border border-[#f7c5c0] bg-[#fff1f0] p-3 text-xs text-[#b42318]">
              {errorMessage}
            </p>
          )}

          <div className="my-6 flex items-center">
            <div className="h-px flex-grow bg-zinc-300" />
            <span className="px-2 text-sm text-zinc-500">or continue with</span>
            <div className="h-px flex-grow bg-zinc-300" />
          </div>

          <div className="space-y-3">
            <button
              type="button"
              onClick={() => handleOAuthLogin('google')}
              disabled={busy}
              className="flex w-full items-center justify-center border border-[#cbd2da] px-4 py-3 text-sm font-semibold text-[#18202b] hover:bg-[#f8fafb] disabled:opacity-50"
            >
              <GoogleMark />
              {oauthLoading === 'google' ? 'Continuing…' : 'Continue with Google'}
            </button>
            <button
              type="button"
              onClick={() => handleOAuthLogin('linkedin_oidc')}
              disabled={busy}
              className="flex w-full items-center justify-center border border-[#cbd2da] px-4 py-3 text-sm font-semibold text-[#18202b] hover:bg-[#f8fafb] disabled:opacity-50"
            >
              <LinkedInMark />
              {oauthLoading === 'linkedin_oidc' ? 'Continuing…' : 'Continue with LinkedIn'}
            </button>
          </div>

          <p className="mt-6 text-center text-[11px] leading-relaxed text-[#7b8491]">
            By continuing, you agree to the <Link to="/terms" className="underline">Terms</Link> and{' '}
            <Link to="/privacy" className="underline">Privacy Policy</Link>.
          </p>
        </div>
      </div>
    </div>
  );
}
