function apiBase() {
  if (typeof window !== 'undefined' && window.API_URL) return String(window.API_URL).replace(/\/$/, '');
  return (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
}

async function request(path) {
  const response = await fetch(`${apiBase()}/api/research/nifty500${path}`);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.error || 'Unable to load Nifty 500 research.');
    error.status = response.status;
    error.code = body.code;
    throw error;
  }
  return response.json();
}

export function getNifty500Summary() {
  return request('/summary');
}

export function searchNifty500Research(query) {
  return request(`/search?q=${encodeURIComponent(query)}`);
}

export function getNifty500StockResearch(symbol) {
  return request(`/stocks/${encodeURIComponent(symbol)}`);
}
