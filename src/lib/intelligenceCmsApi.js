import API_ORIGIN from '@/config';
const API_BASE = API_ORIGIN || '';

async function cmsFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}/api/intelligence/cms${path}`, {
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `CMS API ${res.status}`);
  return data;
}

export function fetchCmsModules() {
  return cmsFetch('/modules');
}

export function fetchCmsDashboard() {
  return cmsFetch('/dashboard');
}

export function fetchCmsRecords(moduleId, { status, q } = {}) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (q) params.set('q', q);
  const qs = params.toString();
  return cmsFetch(`/modules/${moduleId}/records${qs ? `?${qs}` : ''}`);
}

export function fetchCmsRecord(id) {
  return cmsFetch(`/records/${id}`);
}

export function createCmsRecord(moduleId, body) {
  return cmsFetch(`/modules/${moduleId}/records`, { method: 'POST', body: JSON.stringify(body) });
}

export function updateCmsRecord(id, body) {
  return cmsFetch(`/records/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
}

export function deleteCmsRecord(id) {
  return cmsFetch(`/records/${id}`, { method: 'DELETE' });
}

export function publishCmsRecord(id, actor) {
  return cmsFetch(`/records/${id}/publish`, { method: 'POST', body: JSON.stringify({ actor }) });
}

export function exportCmsModuleCsv(moduleId) {
  window.open(`${API_BASE}/api/intelligence/cms/modules/${moduleId}/export`, '_blank');
}

export async function importCmsModuleCsv(moduleId, csv, actor) {
  return cmsFetch(`/modules/${moduleId}/import`, {
    method: 'POST',
    body: JSON.stringify({ csv, actor }),
  });
}

export function fetchPublicCmsModule(moduleId) {
  return cmsFetch(`/public/${moduleId}`);
}
