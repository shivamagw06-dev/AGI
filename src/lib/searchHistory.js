const KEY = 'agi_ask_history_v1';
const FAV_COMPANIES = 'agi_fav_companies_v1';
const FAV_THEMES = 'agi_fav_themes_v1';
const SAVED = 'agi_saved_searches_v1';
const SAVED_ANSWERS = 'agi_saved_answers_v1';
const READING = 'agi_reading_history_v1';
const WATCHLIST = 'agi_watchlist_v1';
const BOOKMARKS = 'agi_bookmarks_v1';

function read(key, fallback = []) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore quota */
  }
}

export function getRecentSearches(limit = 8) {
  return read(KEY).slice(0, limit);
}

export function pushSearch(question) {
  const q = String(question || '').trim();
  if (!q) return;
  const prev = read(KEY).filter((x) => x.toLowerCase() !== q.toLowerCase());
  write(KEY, [q, ...prev].slice(0, 20));
}

export function getSavedSearches() {
  return read(SAVED);
}

export function saveSearch(question) {
  const q = String(question || '').trim();
  if (!q) return;
  const prev = read(SAVED).filter((x) => x.toLowerCase() !== q.toLowerCase());
  write(SAVED, [q, ...prev].slice(0, 30));
}

export function getFavouriteCompanies() {
  return read(FAV_COMPANIES);
}

export function toggleFavouriteCompany(ticker) {
  const t = String(ticker || '').toUpperCase();
  if (!t) return [];
  const prev = read(FAV_COMPANIES);
  const next = prev.includes(t) ? prev.filter((x) => x !== t) : [t, ...prev].slice(0, 40);
  write(FAV_COMPANIES, next);
  return next;
}

export function getFavouriteThemes() {
  return read(FAV_THEMES);
}

export function toggleFavouriteTheme(theme) {
  const t = String(theme || '');
  if (!t) return [];
  const prev = read(FAV_THEMES);
  const next = prev.includes(t) ? prev.filter((x) => x !== t) : [t, ...prev].slice(0, 40);
  write(FAV_THEMES, next);
  return next;
}

export function getSavedAnswers(limit = 12) {
  return read(SAVED_ANSWERS).slice(0, limit);
}

export function saveAnswer(answer) {
  const question = String(answer?.question || '').trim();
  if (!question) return getSavedAnswers();
  const row = {
    id: `${Date.now()}-${question.slice(0, 24)}`,
    question,
    stance: answer?.stance || '',
    summary: answer?.summary || '',
    href: answer?.href || `/ask?q=${encodeURIComponent(question)}`,
    saved_at: new Date().toISOString(),
  };
  const prev = read(SAVED_ANSWERS).filter(
    (x) => String(x.question || '').toLowerCase() !== question.toLowerCase()
  );
  write(SAVED_ANSWERS, [row, ...prev].slice(0, 40));
  return getSavedAnswers();
}

export function getReadingHistory(limit = 20) {
  return read(READING).slice(0, limit);
}

export function pushReading(item) {
  const title = String(item?.title || item?.id || '').trim();
  if (!title) return getReadingHistory();
  const row = {
    id: item?.id || title,
    title,
    href: item?.href || (item?.id ? `/article/${encodeURIComponent(item.id)}` : '/research'),
    at: new Date().toISOString(),
  };
  const prev = read(READING).filter((x) => x.id !== row.id);
  write(READING, [row, ...prev].slice(0, 50));
  return getReadingHistory();
}

export function getWatchlist() {
  const explicit = read(WATCHLIST);
  if (explicit.length) return explicit;
  return getFavouriteCompanies();
}

export function toggleWatchlist(ticker) {
  const t = String(ticker || '').toUpperCase();
  if (!t) return getWatchlist();
  const prev = read(WATCHLIST);
  const base = prev.length ? prev : getFavouriteCompanies();
  const next = base.includes(t) ? base.filter((x) => x !== t) : [t, ...base].slice(0, 40);
  write(WATCHLIST, next);
  return next;
}

export function getBookmarks(limit = 20) {
  return read(BOOKMARKS).slice(0, limit);
}

export function pushBookmark(item) {
  const href = String(item?.href || '').trim();
  if (!href) return getBookmarks();
  const row = {
    id: item?.id || href,
    title: item?.title || href,
    href,
    at: new Date().toISOString(),
  };
  const prev = read(BOOKMARKS).filter((x) => x.href !== href);
  write(BOOKMARKS, [row, ...prev].slice(0, 50));
  return getBookmarks();
}
