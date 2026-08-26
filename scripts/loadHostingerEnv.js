import fs from 'node:fs';
import path from 'node:path';

function applyEnvFile(file) {
  if (!fs.existsSync(file)) return;
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq < 1) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1).replace(/\\"/g, '"');
    }
    if (!process.env[key]) process.env[key] = val;
  }
}

export function loadHostingerEnv(root = process.cwd()) {
  applyEnvFile(path.join(root, '.env.production.local'));
  applyEnvFile(path.join(root, '.env.local'));
  applyEnvFile(path.join(root, '.env'));
}
