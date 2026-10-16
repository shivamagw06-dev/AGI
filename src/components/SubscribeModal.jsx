// src/components/SubscribeModal.jsx
import React, { useEffect, useRef, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { subscribeNewsletter } from '@/lib/subscribeNewsletter';

async function subscribeWithSupabase(emailFromInput) {
  const email = (emailFromInput || '').trim().toLowerCase();
  if (!email) throw new Error('Please enter a valid email address.');
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new Error('Please enter a valid email address.');
  }

  const { data: sessionData } = await supabase.auth.getSession();
  const userId = sessionData?.session?.user?.id || null;

  try {
    await subscribeNewsletter(email, { userId });
    return { ok: true, mode: 'upserted' };
  } catch (err) {
    if (/already subscribed/i.test(err?.message || '')) {
      return { ok: true, mode: 'exists' };
    }
    throw err;
  }
}

/** Subscribe modal component */
export default function SubscribeModal({ open, onOpenChange }) {
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [errMsg, setErrMsg] = useState('');
  const dialogRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === 'Escape' && onOpenChange?.(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onOpenChange]);

  useEffect(() => {
    if (open) dialogRef.current?.querySelector('input')?.focus();
  }, [open]);

  const handleSubscribe = async (e) => {
    e?.preventDefault?.();
    setBusy(true);
    setMessage('');
    setErrMsg('');
    try {
      const res = await subscribeWithSupabase(email);
      setMessage(res.mode === 'exists' ? 'You are already subscribed.' : 'You’re all set! Your subscription is active.');
      if (res.mode !== 'exists') setEmail('');
    } catch (err) {
      // map common Supabase/DB issues to friendly messages
      const text = (err?.message || '').toString();
      if (text.toLowerCase().includes('email')) {
        setErrMsg(text);
      } else {
        setErrMsg('Something went wrong. Please try again.');
      }
      console.error('Subscribe error:', err);
    } finally {
      setBusy(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      aria-modal="true"
      role="dialog"
      aria-labelledby="subscribe-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onOpenChange?.(false);
      }}
    >
      <div className="absolute inset-0 bg-black/50" />
      <div ref={dialogRef} className="relative z-10 w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-neutral-900">
        <div className="mb-4">
          <h2 id="subscribe-title" className="text-xl font-semibold">
            Subscribe for updates
          </h2>
          <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">
            Get our latest research and product updates in your inbox.
          </p>
        </div>

        <form onSubmit={handleSubscribe} className="space-y-3">
          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={busy}
            className="w-full rounded-xl border border-neutral-300 bg-white px-3 py-2 text-sm outline-none ring-0 focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-800"
          />

          {errMsg ? <div className="text-sm text-red-600">{errMsg}</div> : null}
          {message ? <div className="text-sm text-green-600">{message}</div> : null}

          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => onOpenChange?.(false)}
              disabled={busy}
              className="rounded-xl border border-neutral-300 px-4 py-2 text-sm hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={busy}
              className="rounded-xl bg-black px-4 py-2 text-sm text-white hover:opacity-90 disabled:opacity-60 dark:bg-white dark:text-black"
            >
              {busy ? 'Submitting…' : 'Subscribe'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
