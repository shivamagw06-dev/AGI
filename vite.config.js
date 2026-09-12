// vite.config.js
import fs from 'node:fs';
import path from 'node:path';
import react from '@vitejs/plugin-react';
import { createLogger, defineConfig, loadEnv } from 'vite';
import inlineEditPlugin from './plugins/visual-editor/vite-plugin-react-inline-editor.js';
import editModeDevPlugin from './plugins/visual-editor/vite-plugin-edit-mode.js';
import iframeRouteRestorationPlugin from './plugins/vite-plugin-iframe-route-restoration.js';

function readBuildId() {
  try {
    const fromFile = fs.readFileSync(path.resolve(__dirname, '.build-id'), 'utf8').trim();
    if (fromFile) return fromFile;
  } catch {
    /* first build before write-build-version */
  }
  return (
    process.env.VITE_BUILD_ID ||
    process.env.GITHUB_SHA?.slice(0, 12) ||
    `dev-${Date.now().toString(36)}`
  );
}

/* ---- NOTE: don't compute isDev at top-level using process.env.NODE_ENV.
   Vite passes `mode` into defineConfig — use that. ---- */

// Removed broken Horizons placeholder script injectors that polluted production HTML.
const addTransformIndexHtml = {
  name: 'add-transform-index-html',
  transformIndexHtml(html) {
    return {
      html: html.replace(/<script type="module">\/\* … your string … \*\/<\/script>\s*/g, ''),
      tags: [],
    };
  },
};

/* logger tweak (ignore postcss CssSyntaxError spam) */
const logger = createLogger();
const loggerError = logger.error;
logger.error = (msg, options) => {
  try {
    const maybeErr = options && options.error;
    const errStr = (typeof maybeErr === 'string') ? maybeErr : (maybeErr && typeof maybeErr.toString === 'function' ? maybeErr.toString() : '');
    if (errStr && errStr.includes('CssSyntaxError: [postcss]')) return;
  } catch (e) {
    // if our check throws for any reason, fall back to original
  }
  loggerError(msg, options);
};

export default defineConfig(({ mode }) => {
  const isDev = mode !== 'production';

  // load .env* into process.env-like object for vite (prefix handling done below)
  const env = loadEnv(mode, process.cwd(), '');
  const buildId = env.VITE_BUILD_ID || readBuildId();

  // configurable backends / keys (read VITE_ vars for client usage)
  const apiBackend = env.VITE_API_BACKEND || 'http://localhost:3001';
  const indianApiBackend = env.VITE_INDIANAPI || 'https://stock.indianapi.in';
  const tradewatchKey = env.VITE_TRADEWATCH_API_KEY || '';

  // ---- set your production base here ----
  const BASE_PATH_PROD = '/'; // root deploy
  const BASE_PATH = env.VITE_BASE ?? (isDev ? '/' : BASE_PATH_PROD);

  return {
    base: BASE_PATH,
    customLogger: logger,
    define: {
      'import.meta.env.VITE_BUILD_ID': JSON.stringify(buildId),
    },
    plugins: [
      // dev-only plugins
      ...(isDev ? [inlineEditPlugin(), editModeDevPlugin(), iframeRouteRestorationPlugin()] : []),
      react(),
      addTransformIndexHtml,
    ],
    server: {
      // allow network access in dev (replaces allowedHosts)
      host: true,
      cors: true,
      // NOTE: COEP / credentialless can cause stricter headers in browsers.
      // Keep it only if you need SharedArrayBuffer / cross-origin isolation features.
      headers: { 'Cross-Origin-Embedder-Policy': 'credentialless' },
      // hmr overlay default is useful; keep it enabled (you can disable by setting server.hmr.overlay = false)
      proxy: {
        // map /stooq -> https://stooq.com
        '/stooq': {
          target: 'https://stooq.com',
          changeOrigin: true,
          secure: true,
          rewrite: (p) => p.replace(/^\/stooq/, ''),
        },

        // St Louis Fed
        '/fred': {
          target: 'https://api.stlouisfed.org',
          changeOrigin: true,
          secure: true,
          rewrite: (p) => p.replace(/^\/fred/, ''),
        },

        // World Bank Documents: keep prefix so client can call /wds/api/...
        '/wds': {
          target: 'https://search.worldbank.org',
          changeOrigin: true,
          secure: true,
          // no rewrite — keep /wds prefix
        },

        // TradeWatch example (inject API key from env)
        '/tw': {
          target: 'https://api.tradewatch.io',
          changeOrigin: true,
          ws: true,
          secure: true,
          headers: tradewatchKey ? { 'X-API-Key': tradewatchKey } : {},
        },

        // Your backend API (local)
        '/api': {
          target: apiBackend,
          changeOrigin: true,
          secure: typeof apiBackend === 'string' && apiBackend.startsWith('https'),
          // keep prefix: /api/whatever -> forwarded to <apiBackend>/api/whatever
        },

        // Direct IndianAPI proxy for client-side fallback/direct calls
        // Client: fetch('/indianapi/trending') -> proxied to https://stock.indianapi.in/trending
        '/indianapi': {
          target: indianApiBackend,
          changeOrigin: true,
          secure: true,
          rewrite: (p) => p.replace(/^\/indianapi/, ''),
        },
      },
    },
    resolve: {
      extensions: ['.jsx', '.js', '.tsx', '.ts', '.json'],
      // common aliases — add both '@' and '@components' because code may use either style
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@components': path.resolve(__dirname, './src/components'),
        '@contexts': path.resolve(__dirname, './src/contexts'),
        '@hooks': path.resolve(__dirname, './src/hooks'),
      },
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      // Route-level React.lazy splits keep the homepage entry smaller.
      // Avoid aggressive manualChunks here — forcing charts/editor into shared
      // vendor files can accidentally suck react/jsx-runtime into those chunks
      // and modulepreload them on every page.
      chunkSizeWarningLimit: 700,
      rollupOptions: {
        external: [
          // keep these external if you bundle them separately or want to exclude them
          '@babel/parser',
          '@babel/traverse',
          '@babel/generator',
          '@babel/types',
        ],
      },
    },
  };
});
