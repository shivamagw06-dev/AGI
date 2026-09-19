/**
 * Give each tracked manager its Form ADV registration.
 *
 *   node server/scripts/importAdviserProfiles.mjs
 *   node server/scripts/importAdviserProfiles.mjs --apply
 *
 * A manager on the site is a name and a list of positions. Form ADV is where an
 * investment adviser states what it is - when it registered, under what legal
 * name, from where, whether anything is disclosed against it - and it is
 * public, filed by the adviser itself, and carries no licence.
 *
 * Registration facts only. The narrative brochures an adviser files are its own
 * writing and its own copyright; nothing here is anyone else's prose, so the
 * page can state all of it in its own words.
 *
 * Two small requests per manager rather than the SEC's bulk archive, which is
 * 669MB of every filing since 2011 to answer a question about fifty-one firms.
 *
 * Assets under management are deliberately not here. They are in Part 1 of that
 * archive and not in this API, and a profile is worth having without them.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { paged } from '../services/institutionalResearchLayerService.js';
import { matchAdviser, officeAddress, advDate } from '../services/adviserMatch.js';

const APPLY = process.argv.includes('--apply');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const ONLY = argOf('--manager');
const SEARCH = 'https://api.adviserinfo.sec.gov/search/firm';
const UA = process.env.SEC_USER_AGENT || 'AGI Institutional Research research@agarwalglobalinvestments.com';

if (!getSupabaseAdminCredentials()) {
  console.error('[adv] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchJson(url) {
  const res = await fetch(url, { headers: { 'User-Agent': UA, Accept: 'application/json' }, signal: AbortSignal.timeout(30_000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** The registration detail behind a CRD, or null if it cannot be read. */
async function firmDetail(crd) {
  try {
    const body = await fetchJson(`${SEARCH}/${encodeURIComponent(crd)}`);
    const raw = body?.hits?.hits?.[0]?._source?.iacontent;
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    // The profile is worth having without it: the search result already
    // carries the name, CRD, SEC number and scope.
    console.warn(`[adv]   detail for CRD ${crd} unavailable: ${error.message}`);
    return null;
  }
}

async function main() {
  console.log(`[adv] mode: ${APPLY ? 'APPLY - this writes' : 'dry run - nothing is written'}`);

  const managers = await paged(
    () => client.from('institutional_managers').select('id,slug,display_name').order('display_name'),
    { label: 'managers' },
  );
  const wanted = ONLY ? managers.filter((m) => m.slug === ONLY || m.id === ONLY) : managers;
  console.log(`[adv] ${wanted.length} manager(s)`);

  const rows = [];
  const unmatched = [];
  for (const manager of wanted) {
    try {
      const search = await fetchJson(`${SEARCH}?query=${encodeURIComponent(manager.display_name)}&start=0&hits=20`);
      const hits = (search?.hits?.hits || []).map((h) => h._source);
      const found = matchAdviser(manager.display_name, hits);
      if (!found) {
        unmatched.push({ manager, loose: search?.hits?.total || 0 });
        await sleep(350);
        continue;
      }

      const crd = String(found.firm.firm_source_id);
      const detail = await firmDetail(crd);
      const address = officeAddress(found.firm);
      const registration = detail?.registrationStatus?.[0] || {};
      rows.push({
        manager_id: manager.id,
        crd,
        sec_number: found.firm.firm_ia_full_sec_number || null,
        legal_name: found.firm.firm_name,
        registration_scope: found.firm.firm_ia_scope || null,
        registered_since: advDate(registration.effectiveDate),
        latest_adv_filed: advDate(detail?.basicInformation?.advFilingDate),
        // As filed. The adviser answers this question on the form, and it is
        // shown as its answer rather than as a judgement.
        has_disclosure: found.firm.firm_ia_disclosure_fl === 'Y',
        branch_count: Number.isFinite(Number(found.firm.firm_branches_count)) ? Number(found.firm.firm_branches_count) : null,
        city: address.city,
        country: address.country,
        other_names: found.firm.firm_other_names || [],
        matched_by: found.matchedBy,
        source_url: `https://adviserinfo.sec.gov/firm/summary/${crd}`,
        source_as_of: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      console.log(`[adv] ${manager.display_name.padEnd(34)} -> ${found.firm.firm_name.slice(0, 38).padEnd(40)} CRD ${crd}`);
      await sleep(350);
    } catch (error) {
      unmatched.push({ manager, loose: 0, error: error.message });
      console.warn(`[adv] ${manager.display_name}: ${error.message}`);
      await sleep(350);
    }
  }

  console.log('');
  console.log(`[adv] ${rows.length} matched, ${unmatched.length} not`);
  if (unmatched.length) {
    // Named, because most of these are correct. Berkshire Hathaway is an
    // operating company that files 13F; a family office has been exempt from
    // registering since 2011. A manager with no adviser registration is a fact
    // about the manager, not a gap in the import.
    console.log('[adv] no registration matched:');
    for (const row of unmatched) {
      console.log(`  ${row.manager.display_name.padEnd(36)} ${row.error ? row.error : `${row.loose} loose hit(s), none an exact legal-name match`}`);
    }
  }

  if (!APPLY) {
    console.log('');
    console.log('[adv] dry run only. Re-run with --apply to write.');
    return;
  }

  for (let index = 0; index < rows.length; index += 200) {
    const { error } = await client.from('institutional_adviser_profiles')
      .upsert(rows.slice(index, index + 200), { onConflict: 'manager_id' });
    if (error) throw new Error(`writing at ${index}: ${error.message}`);
  }
  console.log(`[adv] ${rows.length} profile(s) written`);
}

main().catch((error) => {
  console.error(`[adv] ${error.message}`);
  process.exit(1);
});
