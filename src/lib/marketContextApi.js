function apiBase() {
  if (typeof window !== 'undefined' && window.API_URL) return String(window.API_URL).replace(/\/$/, '');
  return (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
}

export async function getMarketContext() {
  const response = await fetch(`${apiBase()}/api/market-context`);
  if (!response.ok) throw new Error('Unable to load market context.');
  return response.json();
}
