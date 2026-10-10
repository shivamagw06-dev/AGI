-- Remove the trigger that propagated a ticker to every holding for a CUSIP.
--
-- It fired for each row inserted into or updated on security_identifier_history
-- and ran two unscoped updates:
--
--   update institutional_holdings set ticker = ... where cusip = new.cusip;
--   update holding_changes      set ticker = ... where cusip = new.cusip;
--
-- Two problems, and they are separate.
--
-- The one that shows: upserting a batch of 209 mappings fired 418 full-table
-- updates over 587,000 holdings rows inside a single statement, which then had
-- to finish inside statement_timeout. It did not. The identifier backfill died
-- at 123 seconds with "canceling statement due to statement timeout", twice,
-- and the phase timing put it here.
--
-- The one that does not show: `where cusip = new.cusip` has no date bound. A
-- mapping valid from 2023 was written onto holdings disclosed in 2019. That is
-- the same error the resolution path was just fixed for - applying today's
-- identifier to filings it says nothing about - reintroduced by the database
-- behind the application's back. Every care taken over valid_from and valid_to
-- was being undone on write.
--
-- Propagation now happens in the application, per security, scoped to the
-- mapping's validity window, with a failure on one security reported by CUSIP
-- rather than taking the batch with it. Both writers already do this:
-- enrichSecurityIdentifiers and saveSecurityMapping.

drop trigger if exists security_identifier_ticker_propagation on public.security_identifier_history;

-- The function goes too. Left behind it is an invitation to re-attach it.
drop function if exists public.propagate_security_ticker_mapping();
