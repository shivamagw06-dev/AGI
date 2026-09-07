const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const PASSWORD_REQUIREMENTS = { minLength: 12 };

export function isValidEmail(email) {
  return EMAIL_RE.test(String(email || '').trim());
}

export function passwordChecks(password = '') {
  const value = String(password);
  return {
    minLength: value.length >= PASSWORD_REQUIREMENTS.minLength,
    hasUpper: /[A-Z]/.test(value),
    hasLower: /[a-z]/.test(value),
    hasNumber: /\d/.test(value),
    hasSymbol: /[^A-Za-z0-9]/.test(value),
  };
}

export function isStrongPassword(password) {
  const c = passwordChecks(password);
  return c.minLength && c.hasUpper && c.hasLower && c.hasNumber && c.hasSymbol;
}

export function validateSignup({
  fullName,
  email,
  password,
  confirmPassword,
  acceptTerms,
  acceptPrivacy,
}) {
  const errors = {};
  if (!String(fullName || '').trim() || String(fullName).trim().length < 2) {
    errors.fullName = 'Enter your full name.';
  }
  if (!isValidEmail(email)) errors.email = 'Enter a valid email address.';
  if (!isStrongPassword(password)) {
    errors.password = 'Use 12+ characters with uppercase, lowercase, a number, and a symbol.';
  }
  if (password !== confirmPassword) errors.confirmPassword = 'Passwords do not match.';
  if (!acceptTerms) errors.acceptTerms = 'Accept the Terms & Conditions to continue.';
  if (!acceptPrivacy) errors.acceptPrivacy = 'Accept the Privacy Policy to continue.';
  return errors;
}

export function firstNameFromUser(user) {
  const meta = user?.user_metadata || {};
  const full = meta.full_name || meta.name || user?.email?.split('@')[0] || 'Investor';
  return String(full).trim().split(/\s+/)[0] || 'Investor';
}

export function greetingForNow(date = new Date()) {
  const hour = date.getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}
