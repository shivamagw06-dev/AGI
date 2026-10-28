const DEFAULT_MESSAGES = {
  signin: 'Unable to sign in. Check your details and try again.',
  signup: 'Unable to create your account right now. Please try again.',
  resend: 'Unable to send a verification email right now. Please try again.',
  reset: 'Unable to complete that request right now. Please try again.',
};

export function mapAuthError(error, context = 'signin') {
  const raw = String(error?.message || error || '').toLowerCase();
  const status = Number(error?.status || 0);
  if (status === 429 || /rate limit|too many requests|over_email_send_rate_limit/.test(raw)) {
    return 'Too many attempts. Wait a few minutes before trying again.';
  }
  if (/email not confirmed|email.*confirm/.test(raw)) {
    return 'Verify your email before signing in. You can resend the verification email below.';
  }
  if (/invalid login credentials|invalid.*password/.test(raw)) return 'The email or password is incorrect.';
  if (/user.*banned|locked|temporarily unavailable/.test(raw)) {
    return 'This account is temporarily locked. Wait a few minutes or reset your password.';
  }
  if (/user already registered|already.*exists/.test(raw)) {
    return 'An account may already exist for this email. Try signing in or resetting your password.';
  }
  if (/weak password|password/.test(raw) && context !== 'signin') {
    return 'Use 12+ characters with uppercase, lowercase, a number, and a symbol.';
  }
  return DEFAULT_MESSAGES[context] || DEFAULT_MESSAGES.signin;
}
