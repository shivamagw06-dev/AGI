import { useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { getPinConfig, isValidPin, verifyDevicePin } from '@/lib/devicePin';
import { firstNameFromUser } from '@/lib/authValidation';
import { Lock } from 'lucide-react';

export default function PinUnlockPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const next = searchParams.get('next') || '/';
  const safeNext = next.startsWith('/') ? next : '/';
  const cfg = useMemo(() => (user?.id ? getPinConfig(user.id) : null), [user]);
  const length = cfg?.length === 6 ? 6 : 4;
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const firstName = firstNameFromUser(user);

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5f7fa] px-4">
        <div className="w-full max-w-md border border-[#dce1e7] bg-white p-8 text-center">
          <p className="text-sm text-[#667085]">Sign in first to unlock this device.</p>
          <Link to="/login" className="mt-4 inline-block text-sm font-semibold text-[#274c77]">
            Go to sign in
          </Link>
        </div>
      </div>
    );
  }

  const submit = async (value) => {
    setError('');
    if (!isValidPin(value, { length })) {
      setError(`Enter your ${length}-digit PIN.`);
      return;
    }
    setBusy(true);
    try {
      const ok = await verifyDevicePin(user.id, value);
      if (!ok) {
        setError('Incorrect PIN. Try again.');
        setPin('');
        return;
      }
      navigate(safeNext, { replace: true });
    } finally {
      setBusy(false);
    }
  };

  const onChange = (raw) => {
    const digits = String(raw || '')
      .replace(/\D/g, '')
      .slice(0, length);
    setPin(digits);
    if (digits.length === length) {
      void submit(digits);
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f7fa] px-4 py-16">
      <div className="mx-auto max-w-md border border-[#dce1e7] bg-white p-8 shadow-[0_16px_50px_rgba(15,35,60,0.08)]">
        <Lock className="h-8 w-8 text-[#0d1d33]" />
        <h1 className="mt-4 text-2xl font-bold text-[#18202b]">Welcome back, {firstName}</h1>
        <p className="mt-2 text-sm text-[#667085]">
          Enter the local PIN for this browser. This is not your AGI account password.
        </p>
        <label htmlFor="pin" className="mt-6 mb-1 block text-sm font-medium">
          {length}-digit PIN
        </label>
        <input
          id="pin"
          inputMode="numeric"
          autoComplete="one-time-code"
          autoFocus
          value={pin}
          onChange={(e) => onChange(e.target.value)}
          className="w-full border border-[#cbd2da] px-3 py-3 text-center text-2xl tracking-[0.4em] focus:border-[#274c77] focus:outline-none"
          placeholder={'•'.repeat(length)}
          disabled={busy}
        />
        {error && (
          <p className="mt-3 border border-[#f7c5c0] bg-[#fff1f0] p-3 text-xs text-[#b42318]">{error}</p>
        )}
        <button
          type="button"
          disabled={busy || pin.length !== length}
          onClick={() => submit(pin)}
          className="mt-5 w-full bg-[#0d1d33] px-4 py-3 text-sm font-bold text-white hover:bg-[#182f4e] disabled:opacity-50"
        >
          {busy ? 'Unlocking…' : 'Unlock'}
        </button>
        <div className="mt-6 flex flex-wrap justify-between gap-3 text-xs">
          <Link to="/account/security" className="font-semibold text-[#274c77] hover:underline">
            Forgot PIN? Use password settings
          </Link>
          <button
            type="button"
            className="font-semibold text-[#667085] hover:underline"
            onClick={async () => {
              await logout();
              navigate('/login?mode=signin', { replace: true });
            }}
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
