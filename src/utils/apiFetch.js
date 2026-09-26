// src/utils/apiFetch.js
import { API_ORIGIN } from '../config';

export default async function apiFetch(input, opts = {}) {
  // if input is a path starting with /api -> convert to full URL using API_ORIGIN if available
  let url = input;
  if (typeof input === 'string' && input.startsWith('/api')) {
    if (API_ORIGIN) url = `${API_ORIGIN.replace(/\/$/, '')}${input}`;
  }
  return fetch(url, opts);
}
