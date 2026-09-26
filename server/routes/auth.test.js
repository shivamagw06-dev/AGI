import test from 'node:test';
import assert from 'node:assert/strict';
import { safeVerificationRedirect } from '../lib/authRedirect.js';

test('verification redirects stay on the configured site and verification route', () => {
  const site = 'https://agarwalglobalinvestments.com';
  assert.equal(
    safeVerificationRedirect('/verify-email?next=%2Fportal', site),
    'https://agarwalglobalinvestments.com/verify-email?next=%2Fportal'
  );
  assert.equal(
    safeVerificationRedirect('https://evil.example/verify-email', site),
    'https://agarwalglobalinvestments.com/verify-email'
  );
  assert.equal(
    safeVerificationRedirect('/reset-password', site),
    'https://agarwalglobalinvestments.com/verify-email'
  );
});
