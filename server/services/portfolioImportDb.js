/**
 * The database side of CAS import: three RPC calls, nothing else.
 *
 * Every write goes through a Postgres function so that a confirmation is one
 * transaction. Doing it as a sequence of Supabase client calls would let a
 * network failure land between them, leaving a portfolio holding half a
 * statement with no record of which half.
 *
 * The client here is built from the caller's own access token, not the service
 * role. That is deliberate: the functions are SECURITY INVOKER and RLS confines
 * them to the caller's rows, so running as the user means the database enforces
 * ownership rather than this file remembering to. The service-role key stays on
 * the BFF for the things that genuinely need it and is never used to write a
 * client's holdings.
 */

import { createClient } from '@supabase/supabase-js';

/** Postgres error text is a code we raised, or something we do not surface. */
const CODE_FROM_MESSAGE = /(authentication_required|nothing_selected|import_plan_missing|not_your_import|import_already_resolved|import_expired|portfolio_changed|portfolio_not_found)/;

function toError(error, fallback) {
  const raw = String(error?.message || '');
  const found = raw.match(CODE_FROM_MESSAGE);
  const wrapped = new Error(found ? found[1] : fallback);
  wrapped.code = found ? found[1] : fallback;
  return wrapped;
}

export function createPortfolioImportDb({ supabaseUrl, anonKey }) {
  if (!supabaseUrl || !anonKey) {
    throw new Error('portfolio import db requires supabaseUrl and anonKey');
  }

  /** A client acting as the signed-in user, so RLS applies to every statement. */
  const asUser = (accessToken) => createClient(supabaseUrl, anonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { Authorization: `Bearer ${accessToken}` } },
  });

  return {
    async insertImportPlan({ accessToken, portfolioId, sourceType, statementDate,
                             statementFingerprint, planSummary, expiresAt }) {
      const { data, error } = await asUser(accessToken).rpc('create_cas_import_plan', {
        p_portfolio_id: portfolioId,
        p_source_type: sourceType,
        p_statement_date: statementDate,
        p_fingerprint: statementFingerprint,
        p_plan: planSummary,
        p_expires_at: expiresAt,
      });
      if (error) {
        // The unique index on (user, portfolio, fingerprint) is how a repeat
        // upload of the same document becomes a refusal rather than a
        // duplicate portfolio.
        if (error.code === '23505') {
          const dup = new Error('already_imported');
          dup.code = 'duplicate_statement';
          throw dup;
        }
        throw toError(error, 'plan_not_saved');
      }
      const row = Array.isArray(data) ? data[0] : data;
      if (!row?.import_id) throw toError(null, 'plan_not_saved');
      return { id: row.import_id, baseVersion: row.base_version };
    },

    /**
     * Apply a confirmed selection.
     *
     * `selectedRowIds` are ids and only ids. The function reads the stored plan
     * and applies what those ids point at; nothing from the browser describes a
     * holding.
     */
    async confirmImport({ accessToken, importId, selectedRowIds }) {
      const { data, error } = await asUser(accessToken).rpc('confirm_cas_import', {
        p_import_id: importId,
        p_selected_row_ids: selectedRowIds,
      });
      if (error) throw toError(error, 'confirm_failed');
      if (!data?.ok) throw toError(null, 'confirm_failed');
      return {
        inserted: data.inserted ?? 0,
        updated: data.updated ?? 0,
        closed: data.closed ?? 0,
        reviewQueued: data.review_queued ?? 0,
        unknownRowIds: data.unknown_row_ids ?? [],
        portfolioVersion: data.portfolio_version ?? null,
      };
    },

    async discardImport({ accessToken, importId }) {
      const { data, error } = await asUser(accessToken).rpc('discard_cas_import', {
        p_import_id: importId,
      });
      if (error) throw toError(error, 'discard_failed');
      return { discarded: data?.discarded ?? 0 };
    },
  };
}

export const _internals = { toError, CODE_FROM_MESSAGE };
export default createPortfolioImportDb;
