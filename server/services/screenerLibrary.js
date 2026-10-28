import crypto from 'node:crypto';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { SCREENER_CATEGORIES, LEGACY_SCREENERS } from '../../src/lib/screenerLibrary.js';
import { parseScreenerTables, compareScreenerSnapshots } from '../../src/lib/screenerTable.js';
import { validateAsOf } from './manualLowPeScreener.js';
export function inputError(message, status = 400) { return Object.assign(Error(message), { status }); }
export function safeSourceUrl(value) {
  if (!value) return null;
  try { const u = new URL(String(value)); if (u.protocol !== 'https:' || u.username || u.password || u.href.length > 2000) throw Error(); return u.href; }
  catch { throw inputError('Source URL must be an HTTPS link without credentials.'); }
}
export function libraryDefinition(body, slug) {
  const { display_name, category, description = '', rule_notes = '', default_source_url = '' } = body || {};
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug || '') || slug.length < 3 || slug.length > 80 || LEGACY_SCREENERS.some(s => s.slug === slug)) throw inputError('Choose a unique URL name of 3–80 lowercase letters, numbers and hyphens. Existing screen names are reserved.');
  if (typeof display_name !== 'string' || display_name.trim().length < 3 || display_name.length > 120 || !SCREENER_CATEGORIES.includes(category)) throw inputError('Enter a screener name and choose a category.');
  if (typeof description !== 'string' || description.length > 1000 || typeof rule_notes !== 'string' || rule_notes.length > 3000) throw inputError('Description or screening notes are too long.');
  return { slug, display_name: display_name.trim(), category, description: description.trim(), rule_notes: rule_notes.trim(), default_source_url: safeSourceUrl(default_source_url) };
}
export function libraryImport(body) {
  const asOf = validateAsOf(body?.asOf);
  const table = parseScreenerTables([body?.text, body?.secondText].filter(v => typeof v === 'string' && v.trim()), body?.identityHeader);
  const sourceUrl = safeSourceUrl(body?.sourceUrl);
  const hash = crypto.createHash('sha256').update(JSON.stringify({ columns: table.columns, rows: table.rows, identityColumn: table.identityColumn, sourceUrl })).digest('hex');
  return { ...table, asOf, sourceUrl, hash };
}
export function createScreenerLibraryStore(client = createSupabaseAdmin()) {
  const db = () => { if (!client) throw Error('Screener storage is unavailable.'); return client; };
  const result = async q => { const r = await q; if (r.error) throw r.error; return r.data; };
  const definition = slug => result(db().from('screener_library').select('slug,display_name,category,description,rule_notes,default_source_url,created_at,updated_at').eq('slug', slug).eq('archived', false).maybeSingle());
  return {
    async catalogue() {
      const [custom, legacy] = await Promise.all([
        result(db().from('screener_library_catalogue').select('*').eq('archived', false).order('display_name')),
        Promise.all(LEGACY_SCREENERS.map(async s => {
          const latest = await result(db().from(s.table).select('as_of,created_at,row_count').order('id', { ascending: false }).limit(1).maybeSingle());
          const { table, ...metadata } = s;
          return { ...metadata, kind: 'legacy', as_of: latest?.as_of || null, row_count: latest?.row_count ?? null, published_at: latest?.created_at || null };
        })),
      ]);
      return [...legacy, ...custom.map(s => ({ ...s, kind: 'imported' }))];
    },
    definition,
    async create(body, actorId) { return result(db().from('screener_library').insert({ ...body, created_by: actorId }).select('slug,display_name,category,description,rule_notes,default_source_url').single()); },
    async update(slug, body) { return result(db().from('screener_library').update({ ...body, updated_at: new Date().toISOString() }).eq('slug', slug).eq('archived', false).select('slug,display_name,category,description,rule_notes,default_source_url').single()); },
    async history(slug) { return result(db().from('screener_library_snapshots').select('id,as_of,created_at,row_count,source_url').eq('screener_slug', slug).order('id', { ascending: false }).limit(100)); },
    async detail(slug, id) {
      const screen = await definition(slug); if (!screen) return null;
      let query = db().from('screener_library_snapshots').select('id,as_of,created_at,row_count,columns,rows,identity_column,source_url,definition').eq('screener_slug', slug);
      query = id ? query.eq('id', id) : query.order('id', { ascending: false });
      const snapshot = await result(query.limit(1).maybeSingle());
      if (id && !snapshot) return null;
      const previous = snapshot ? await result(db().from('screener_library_snapshots').select('id,as_of,columns,rows,identity_column').eq('screener_slug', slug).lt('id', snapshot.id).order('id', { ascending: false }).limit(1).maybeSingle()) : null;
      return { screen, snapshot, changes: snapshot ? compareScreenerSnapshots(snapshot, previous) : null };
    },
    async publish(slug, data, actorId) {
      return result(db().rpc('publish_screener_library_snapshot', { p_slug: slug, p_as_of: data.asOf, p_columns: data.columns, p_rows: data.rows, p_identity_column: data.identityColumn, p_source_url: data.sourceUrl, p_hash: data.hash, p_actor: actorId }));
    },
  };
}
