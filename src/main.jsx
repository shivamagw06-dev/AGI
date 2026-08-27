// src/main.jsx

// Polyfill: safe net.http_post helper so any library expecting it won't crash.
// Keeps existing behaviour but is slightly more defensive and logs helpful debug info.
if (!globalThis.net) globalThis.net = {};
if (!globalThis.net.http_post) {
  globalThis.net.http_post = async (url, headers = {}, body = {}) => {
    try {
      // Allow passing already-stringified bodies or objects
      const payload = typeof body === 'string' ? body : JSON.stringify(body);

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers },
        body: payload,
        credentials: 'include',
      });

      const contentType = res.headers.get('content-type') || '';

      // prefer JSON when available, otherwise text
      if (contentType.includes('application/json')) {
        const json = await res.json();
        if (!res.ok) return { status: res.status, ok: false, body: json };
        return json;
      }

      const text = await res.text();
      if (!res.ok) return { status: res.status, ok: false, body: text };
      return text;
    } catch (err) {
      // Keep the error shape consistent for callers and log helpful debug info
      console.error('net.http_post polyfill failed:', err);
      return { error: err?.message || String(err) };
    }
  };
}

import React from 'react';
import ReactDOM from 'react-dom/client';
import { HelmetProvider } from 'react-helmet-async';
import App from './App';
import './index.css';

import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { startBuildVersionWatcher } from '@/lib/buildVersion';

// export helmetContext so it can be used on the server if you later add SSR
export const helmetContext = {};

// Detect Hostinger deploy race (fresh HTML + stale hashed chunks) and reload once.
if (typeof window !== 'undefined') {
  startBuildVersionWatcher({ intervalMs: 60_000 });
}

/**
 * Initialize theme (dark class) on documentElement early.
 * - Checks saved preference in localStorage ('theme' = 'dark'|'light')
 * - Falls back to system preference (prefers-color-scheme)
 * - Applies .dark to <html> if dark should be active
 *
 * Running this synchronously here minimizes a flash of incorrect theme on initial paint.
 */
(function initTheme() {
  try {
    // Read saved preference; we intentionally don't parse JSON — it's a simple string
    const saved = typeof window !== 'undefined' ? localStorage.getItem('theme') : null;
    const prefersDark =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches;

    const shouldDark = saved === 'dark';

    if (typeof document !== 'undefined') {
      document.documentElement.classList.remove('dark');
      if (shouldDark) document.documentElement.classList.add('dark');
    }
  } catch (err) {
    // Non-fatal: just log in dev
    // We don't want this to crash render in test/SSR environments where window/document may be undefined
    // eslint-disable-next-line no-console
    console.warn('initTheme failed:', err);
  }
})();

const rootElement = typeof document !== 'undefined' ? document.getElementById('root') : null;

if (!rootElement) {
  // Fail fast with a helpful message in development
  console.error('Root element not found: make sure an element with id="root" exists in index.html');
} else {
  const root = ReactDOM.createRoot(rootElement);

  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <HelmetProvider context={helmetContext}>
          <ThemeProvider>
            <AuthProvider>
              <App />
            </AuthProvider>
          </ThemeProvider>
        </HelmetProvider>
      </ErrorBoundary>
    </React.StrictMode>
  );
}
