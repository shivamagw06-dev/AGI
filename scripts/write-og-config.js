#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadHostingerEnv } from './loadHostingerEnv.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
loadHostingerEnv(root);
const supabaseUrl = String(process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '')
  .trim()
  .replace(/\/$/, '');
const anonKey = String(process.env.VITE_SUPABASE_ANON_KEY || '').trim();

if (!supabaseUrl || !anonKey) {
  console.warn('write-og-config: missing Supabase URL or anon key; PHP will use the Render fallback.');
  process.exit(0);
}

const php = `<?php
return [
  'supabaseUrl' => ${JSON.stringify(supabaseUrl)},
  'anonKey' => ${JSON.stringify(anonKey)},
];
`;

for (const dest of ['dist/og-config.php', 'og-config.php']) {
  const file = path.join(root, dest);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, php);
}
console.log('write-og-config: wrote og-config.php');
