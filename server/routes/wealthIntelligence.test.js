import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { once } from 'node:events';
import createRouter from './wealthIntelligence.js';

test('server enforces sign-in, validates search, and does not expose errors or cache private responses', async t => {
  let calls = 0;
  const app = express();
  app.use('/api/wealth', createRouter({
    authenticate: async token => token === 'valid' ? { id: 'user' } : token === 'anon' ? { id: 'user', is_anonymous: true } : null,
    getUniverse: async params => { calls++; return { items: [], total: 0, params }; },
  }));
  const server = app.listen(0, '127.0.0.1'); await once(server, 'listening');
  t.after(() => { server.closeAllConnections(); server.close(); });
  const url = `http://127.0.0.1:${server.address().port}/api/wealth/universe`;
  assert.equal((await fetch(url)).status, 401);
  for (const token of ['invalid', 'anon']) assert.equal((await fetch(url, { headers: { Authorization: `Bearer ${token}` } })).status, 401);
  const headers = { Authorization: 'Bearer valid' };
  for (const query of ['?assetClass=property', '?limit=1000', '?offset=-1', '?q[a]=b']) assert.equal((await fetch(url + query, { headers })).status, 400);
  assert.equal(calls, 0);
  const response = await fetch(url + '?q=test&limit=25', { headers });
  assert.equal(response.status, 200); assert.equal(response.headers.get('cache-control'), 'private, no-store');
  assert.equal((await response.json()).params.q, 'test'); assert.equal(calls, 1);
});
