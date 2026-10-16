/**
 * Write public/version.json + .build-id before Vite build.
 * Hostinger serves /version.json so the client can detect deploy mismatches.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sha =
  process.env.GITHUB_SHA ||
  process.env.RENDER_GIT_COMMIT ||
  process.env.COMMIT_REF ||
  '';
const buildId =
  (sha && String(sha).slice(0, 12)) ||
  `local-${Date.now().toString(36)}`;

const version = {
  buildId,
  builtAt: new Date().toISOString(),
  commit: sha || null,
};

const publicDir = path.join(root, 'public');
fs.mkdirSync(publicDir, { recursive: true });
fs.writeFileSync(path.join(publicDir, 'version.json'), `${JSON.stringify(version, null, 2)}\n`);
fs.writeFileSync(path.join(root, '.build-id'), `${buildId}\n`);
console.info(`[build-version] ${buildId}`);
