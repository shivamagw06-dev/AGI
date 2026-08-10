import { useMemo, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import {
  disableDevicePin,
  getPinConfig,
  hasPin,
  isValidPin,
  setDevicePin,
} from '@/lib/devicePin';
import { isStrongPassword, passwordChecks } from '@/lib/authValidation';
import { Shield } from 'lucide-react';

export default function AccountSecurityPage() {
  const { user, updatePassword, logoutAllDevices, loading } = useAuth();
  const [pinLength, setPinLength] = useState(4);
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);

  const pinEnabled = useMemo(() => (user?.id ? hasPin(user.id) : false), [user, tick]);
  const pinCfg = useMemo(() => (user?.id ? getPinConfig(user.id) : null), [user, tick]);

  if (!loading && !user) return <Navigate to="/login?mode=signin&next=/account/security" replace />;

  const flash = (ok, text) => {
    setMessage(ok ? text : '');
    setError(ok ? '' : text);
  };

  const savePin = async (e) => {
    e.preventDefault();
    flash(true, '');
    if (!isValidPin(pin, { length: pinLength })) {
      flash(false, `PIN must be ${pinLength} digits.`);
      return;
    }
    if (pin !== confirmPin) {
      flash(false, 'PIN confirmation does not match.');
      return;
    }
    setBusy(true);
    try {
      await setDevicePin(user.id, pin, { length: pinLength });
      setPin('');
      setConfirmPin('');
      setTick((n) => n + 1);
      flash(true, 'Device PIN saved for this browser.');
    } catch (err) {
      flash(false, err?.message || 'Unable to save PIN.');
    } finally {
      setBusy(false);
    }
  };

  const removePin = () => {
    disableDevicePin(user.id);
    setTick((n) => n + 1);
    flash(true, 'Device PIN disabled on this browser.');
  };

  const changePassword = async (e) => {
    e.preventDefault();
    flash(true, '');
    if (!isStrongPassword(password)) {
      flash(false, 'Use 12+ characters with uppercase, lowercase, a number, and a symbol.');
      return;
    }
    if (password !== confirmPassword) {
      flash(false, 'Passwords do not match.');
      return;
    }
    setBusy(true);
    try {
      await updatePassword(password);
      setPassword('');
      setConfirmPassword('');
      flash(true, 'Password updated.');
    } catch (err) {
      flash(false, err?.message || 'Unable to update password.');
    } finally {
      setBusy(false);
    }
  };

  const checks = passwordChecks(password);

  return (
    <div className="min-h-screen bg-[#f5f7fa] px-4 py-10">
      <div className="mx-auto max-w-2xl space-y-6">
        <div className="border border-[#dce1e7] bg-white p-6 sm:p-8 shadow-[0_16px_50px_rgba(15,35,60,0.08)]">
          <div className="flex items-start gap-3">
            <Shield className="mt-1 h-6 w-6 text-[#0d1d33]" />
            <div>
              <h1 className="text-2xl font-bold text-[#18202b]">Account security</h1>
              <p className="mt-1 text-sm text-[#667085]">
                Manage your password, local browser PIN, and signed-in sessions.
              </p>
            </div>
          </div>
        </div>

        <section className="border border-[#dce1e7] bg-white p-6 sm:p-8">
          <h2 className="text-lg font-bold text-[#18202b]">Local browser PIN</h2>
          <p className="mt-1 text-sm text-[#667085]">
            This optional PIN only locks access in this browser after you sign in. It is not your
            account password and cannot recover or secure your account on other devices.
          </p>
          <p className="mt-3 text-xs font-semibold text-[#445066]">
            Status: {pinEnabled ? `Enabled (${pinCfg?.length || 4}-digit)` : 'Not set on this device'}
          </p>

          <form onSubmit={savePin} className="mt-5 space-y-3">
            <div className="flex gap-2 text-sm">
              {[4, 6].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setPinLength(n)}
                  className={`border px-3 py-1.5 font-semibold ${
                    pinLength === n ? 'border-[#0d1d33] bg-[#0d1d33] text-white' : 'border-[#cbd2da]'
                  }`}
                >
                  {n}-digit
                </button>
              ))}
            </div>
            <input
              inputMode="numeric"
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, pinLength))}
              placeholder={`New ${pinLength}-digit PIN`}
              className="w-full border border-[#cbd2da] px-3 py-3 text-sm focus:border-[#274c77] focus:outline-none"
            />
            <input
              inputMode="numeric"
              value={confirmPin}
              onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, '').slice(0, pinLength))}
              placeholder="Confirm PIN"
              className="w-full border border-[#cbd2da] px-3 py-3 text-sm focus:border-[#274c77] focus:outline-none"
            />
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={busy}
                className="bg-[#0d1d33] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#182f4e] disabled:opacity-50"
              >
                {pinEnabled ? 'Update PIN' : 'Enable PIN'}
              </button>
              {pinEnabled && (
                <button
                  type="button"
                  onClick={removePin}
                  className="border border-[#cbd2da] px-4 py-2.5 text-sm font-semibold"
                >
                  Disable PIN
                </button>
              )}
            </div>
          </form>
        </section>

        <section className="border border-[#dce1e7] bg-white p-6 sm:p-8">
          <h2 className="text-lg font-bold text-[#18202b]">Change password</h2>
          <form onSubmit={changePassword} className="mt-4 space-y-3">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="New password"
              className="w-full border border-[#cbd2da] px-3 py-3 text-sm focus:border-[#274c77] focus:outline-none"
            />
            <ul className="grid grid-cols-2 gap-1 text-[11px] text-[#7b8491]">
              <li className={checks.minLength ? 'text-[#087443]' : ''}>12+ characters</li>
              <li className={checks.hasUpper ? 'text-[#087443]' : ''}>Uppercase</li>
              <li className={checks.hasLower ? 'text-[#087443]' : ''}>Lowercase</li>
              <li className={checks.hasNumber ? 'text-[#087443]' : ''}>Number</li>
              <li className={checks.hasSymbol ? 'text-[#087443]' : ''}>Symbol</li>
            </ul>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm new password"
              className="w-full border border-[#cbd2da] px-3 py-3 text-sm focus:border-[#274c77] focus:outline-none"
            />
            <button
              type="submit"
              disabled={busy}
              className="bg-[#0d1d33] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#182f4e] disabled:opacity-50"
            >
              Update password
            </button>
          </form>
        </section>

        <section className="border border-[#dce1e7] bg-white p-6 sm:p-8">
          <h2 className="text-lg font-bold text-[#18202b]">Sessions</h2>
          <p className="mt-1 text-sm text-[#667085]">
            Sign out of every browser and device where this AGI account is active.
          </p>
          <button
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await logoutAllDevices();
                flash(true, 'Signed out of all devices.');
              } catch (err) {
                flash(false, err?.message || 'Unable to sign out everywhere.');
              } finally {
                setBusy(false);
              }
            }}
            className="mt-4 border border-[#b42318] px-4 py-2.5 text-sm font-semibold text-[#b42318] hover:bg-[#fff1f0] disabled:opacity-50"
          >
            Log out all devices
          </button>
        </section>

        {(message || error) && (
          <p
            className={`border p-3 text-xs ${
              message
                ? 'border-[#b7ebcc] bg-[#ecfdf3] text-[#087443]'
                : 'border-[#f7c5c0] bg-[#fff1f0] text-[#b42318]'
            }`}
          >
            {message || error}
          </p>
        )}

        <Link to="/" className="inline-block text-sm font-semibold text-[#274c77] hover:underline">
          ← Back to home
        </Link>
      </div>
    </div>
  );
}
