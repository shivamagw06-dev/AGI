import test from 'node:test';
import assert from 'node:assert/strict';
import { isStrongPassword, passwordChecks, validateSignup } from './authValidation.js';
import { mapAuthError } from './authErrors.js';

test('password policy requires 12 characters and every advertised character class', () => {
  assert.equal(isStrongPassword('Short1!'), false);
  assert.equal(isStrongPassword('LongPassword1'), false);
  assert.equal(isStrongPassword('LongPassword1!'), true);
  assert.deepEqual(passwordChecks('LongPassword1!'), {
    minLength: true,
    hasUpper: true,
    hasLower: true,
    hasNumber: true,
    hasSymbol: true,
  });
});

test('signup validation no longer collects or validates optional mobile data', () => {
  const errors = validateSignup({
    fullName: 'AGI User',
    email: 'user@example.com',
    password: 'LongPassword1!',
    confirmPassword: 'LongPassword1!',
    acceptTerms: true,
    acceptPrivacy: true,
  });
  assert.deepEqual(errors, {});
});

test('auth errors are mapped to stable user-facing messages', () => {
  assert.equal(mapAuthError({ message: 'Invalid login credentials' }), 'The email or password is incorrect.');
  assert.match(mapAuthError({ status: 429 }, 'resend'), /Too many attempts/);
  assert.doesNotMatch(mapAuthError({ message: 'postgres trigger xyz failed' }, 'signup'), /postgres|trigger/i);
});
