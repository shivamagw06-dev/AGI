-- Supabase default grants include UPDATE/DELETE for service_role. Remove those
-- from immutable publication history while retaining RPC insert/read access.
revoke all on public.screener_library_snapshots from service_role;
grant select,insert on public.screener_library_snapshots to service_role;
revoke all on sequence public.screener_library_snapshots_id_seq from service_role;
grant usage,select on sequence public.screener_library_snapshots_id_seq to service_role;
