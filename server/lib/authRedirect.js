export function safeVerificationRedirect(value, siteUrl) {
  const fallback = `${siteUrl.replace(/\/$/, '')}/verify-email`;
  try {
    const candidate = new URL(String(value || ''), fallback);
    const allowed = new URL(siteUrl);
    return candidate.origin === allowed.origin && candidate.pathname === '/verify-email'
      ? candidate.toString()
      : fallback;
  } catch {
    return fallback;
  }
}
