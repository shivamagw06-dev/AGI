import { useEffect, useRef, useState } from 'react';

/**
 * 6-digit PIN entry — banking-app dots, institutional styling.
 */
export default function PinPad({
  value,
  onChange,
  onComplete,
  disabled = false,
  error = '',
  autoFocus = true,
  length = 6,
}) {
  const refs = useRef([]);
  const digits = String(value || '')
    .replace(/\D/g, '')
    .slice(0, length)
    .split('');

  useEffect(() => {
    if (autoFocus) refs.current[Math.min(digits.length, length - 1)]?.focus();
  }, [autoFocus, digits.length, length]);

  useEffect(() => {
    if (digits.length === length && onComplete) {
      const code = digits.join('');
      if (refs.current._lastComplete === code) return;
      refs.current._lastComplete = code;
      onComplete(code);
    }
    if (digits.length < length) refs.current._lastComplete = '';
  }, [digits.join(''), length]); // eslint-disable-line react-hooks/exhaustive-deps

  const setAt = (index, char) => {
    const next = [...Array(length)].map((_, i) => digits[i] || '');
    next[index] = char;
    const joined = next.join('').replace(/\D/g, '').slice(0, length);
    onChange?.(joined);
  };

  return (
    <div>
      <div className="flex justify-center gap-3" role="group" aria-label="6-digit PIN">
        {Array.from({ length }).map((_, i) => {
          const filled = Boolean(digits[i]);
          return (
            <div key={i} className="relative">
              <input
                ref={(el) => {
                  refs.current[i] = el;
                }}
                type="password"
                inputMode="numeric"
                autoComplete={i === 0 ? 'one-time-code' : 'off'}
                maxLength={1}
                disabled={disabled}
                value={digits[i] || ''}
                aria-label={`PIN digit ${i + 1}`}
                className="h-12 w-10 rounded-xl border border-[#e5e7eb] bg-white text-center text-lg text-transparent caret-transparent outline-none focus:border-[#0a1e38] focus:ring-2 focus:ring-[#0a1e38]/15 disabled:opacity-50"
                onChange={(e) => {
                  const d = e.target.value.replace(/\D/g, '').slice(-1);
                  if (!d) {
                    setAt(i, '');
                    return;
                  }
                  setAt(i, d);
                  refs.current[i + 1]?.focus();
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Backspace') {
                    if (digits[i]) setAt(i, '');
                    else refs.current[i - 1]?.focus();
                  }
                  if (e.key === 'ArrowLeft') refs.current[i - 1]?.focus();
                  if (e.key === 'ArrowRight') refs.current[i + 1]?.focus();
                }}
                onPaste={(e) => {
                  e.preventDefault();
                  const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
                  if (pasted) onChange?.(pasted);
                }}
              />
              <span
                className={`pointer-events-none absolute left-1/2 top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ${
                  filled ? 'bg-[#0a1e38]' : 'bg-[#d1d5db]'
                }`}
              />
            </div>
          );
        })}
      </div>
      {error ? <p className="mt-4 text-center text-sm text-[#b42318]">{error}</p> : null}
    </div>
  );
}
