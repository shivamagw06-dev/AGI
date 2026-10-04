-- Append-only publication facts. Read APIs run on the server; no client writes.
CREATE TABLE public.alpha_publications (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 source_key text NOT NULL UNIQUE,
 symbol text NOT NULL,
 instrument_key text NOT NULL,
 sector text,
 direction text NOT NULL CHECK (direction IN ('positive','negative','conflicting')),
 score numeric NOT NULL,
 signal_at timestamptz NOT NULL,
 published_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 quote_at timestamptz,
 reference_price numeric CHECK (reference_price > 0),
 benchmark_price numeric CHECK (benchmark_price > 0),
 components jsonb NOT NULL DEFAULT '[]',
 quality jsonb NOT NULL DEFAULT '{}',
 model_version text NOT NULL DEFAULT 'alpha-publication-v1',
 CHECK (signal_at <= published_at)
);
CREATE INDEX alpha_publications_date_idx ON public.alpha_publications(published_at DESC,id DESC);
CREATE INDEX alpha_publications_symbol_date_idx ON public.alpha_publications(symbol,published_at DESC);
CREATE TABLE public.alpha_publication_heads (
 symbol text PRIMARY KEY,
 publication_id uuid REFERENCES public.alpha_publications(id),
 direction text,
 last_signal_at timestamptz NOT NULL,
 last_score numeric,
 last_components jsonb
);
CREATE INDEX alpha_publication_heads_id_idx ON public.alpha_publication_heads(publication_id);
CREATE TABLE public.alpha_publication_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 publication_id uuid NOT NULL REFERENCES public.alpha_publications(id),
 event_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 signal_at timestamptz NOT NULL,
 kind text NOT NULL CHECK (kind IN ('strengthened','weakened','components_changed','reversed','withdrawn')),
 details jsonb NOT NULL DEFAULT '{}',
 UNIQUE(publication_id,signal_at,kind)
);
CREATE INDEX alpha_publication_events_id_time_idx ON public.alpha_publication_events(publication_id,event_at);
CREATE TABLE public.alpha_publication_followups (
 publication_id uuid NOT NULL REFERENCES public.alpha_publications(id),
 horizon text NOT NULL CHECK(horizon IN ('15m','1h','close','1d','5d','20d','exit')),
 due_at timestamptz NOT NULL,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','completed','missing')),
 price numeric,
 observed_at timestamptz,
 benchmark_price numeric,
 benchmark_observed_at timestamptz,
 price_source text,
 stock_return_pct numeric,
 directional_return_pct numeric,
 benchmark_return_pct numeric,
 simulated_net_return_pct numeric,
 reason text,
 attempts integer NOT NULL DEFAULT 0,
 next_attempt_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(publication_id,horizon)
);
CREATE INDEX alpha_followups_due_idx ON public.alpha_publication_followups(next_attempt_at,due_at) WHERE status='pending';
CREATE TABLE public.alpha_publication_entries (
 publication_id uuid PRIMARY KEY REFERENCES public.alpha_publications(id),
 observed_at timestamptz NOT NULL,
 price numeric NOT NULL CHECK(price>0),
 source text NOT NULL,
 spread_bps numeric,
 cost_model text NOT NULL DEFAULT '10 bps round-trip fees + 5 bps slippage per side; bid/ask entry and exit; no borrow financing',
 recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.alpha_archive_daily_prices (
 instrument_key text NOT NULL,
 session_date date NOT NULL,
 price numeric NOT NULL CHECK(price>0),
 observed_at timestamptz NOT NULL,
 source text NOT NULL DEFAULT 'upstox_daily_close_unadjusted',
 recorded_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(instrument_key,session_date)
);
ALTER TABLE public.alpha_publications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alpha_publication_heads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alpha_publication_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alpha_publication_followups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alpha_publication_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alpha_archive_daily_prices ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.alpha_publications,public.alpha_publication_heads,public.alpha_publication_events,public.alpha_publication_followups,public.alpha_publication_entries,public.alpha_archive_daily_prices FROM anon,authenticated;
GRANT SELECT,INSERT,UPDATE ON public.alpha_publications,public.alpha_publication_heads,public.alpha_publication_events,public.alpha_publication_followups,public.alpha_publication_entries,public.alpha_archive_daily_prices TO service_role;
GRANT USAGE,SELECT ON SEQUENCE public.alpha_publication_events_id_seq TO service_role;
CREATE FUNCTION public.alpha_reject_fact_change() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
BEGIN RAISE EXCEPTION 'Publication facts are append-only'; END $$;
REVOKE ALL ON FUNCTION public.alpha_reject_fact_change() FROM PUBLIC,anon,authenticated;
CREATE TRIGGER alpha_publications_immutable BEFORE UPDATE OR DELETE ON public.alpha_publications FOR EACH ROW EXECUTE FUNCTION public.alpha_reject_fact_change();
CREATE TRIGGER alpha_events_immutable BEFORE UPDATE OR DELETE ON public.alpha_publication_events FOR EACH ROW EXECUTE FUNCTION public.alpha_reject_fact_change();
CREATE TRIGGER alpha_entries_immutable BEFORE UPDATE OR DELETE ON public.alpha_publication_entries FOR EACH ROW EXECUTE FUNCTION public.alpha_reject_fact_change();
-- Serialise competing publishers and preserve the actual first availability time.
CREATE FUNCTION public.alpha_publish_snapshot(p_rows jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE r jsonb; h public.alpha_publication_heads%ROWTYPE; new_id uuid; stamp timestamptz:=clock_timestamp(); sig timestamptz; dir text; event_kind text; created integer:=0;
BEGIN
 PERFORM pg_advisory_xact_lock(44190267);
 FOR r IN SELECT value FROM jsonb_array_elements(p_rows) LOOP
  sig := (r->>'signal_at')::timestamptz;
  -- Never backdate a published call or turn stale replay into a new live call.
  IF sig > stamp OR sig < stamp-interval '15 minutes' THEN CONTINUE; END IF;
  SELECT * INTO h FROM public.alpha_publication_heads WHERE symbol=r->>'symbol';
  IF h.last_signal_at IS NOT NULL AND h.last_signal_at >= sig THEN CONTINUE; END IF;
  dir := r->>'direction'; new_id:=h.publication_id; event_kind:=NULL;
  IF h.publication_id IS NOT NULL AND h.direction IS DISTINCT FROM dir THEN
   INSERT INTO public.alpha_publication_events(publication_id,event_at,signal_at,kind,details)
    VALUES(h.publication_id,stamp,sig,CASE WHEN dir IS NULL THEN 'withdrawn' ELSE 'reversed' END,jsonb_build_object('new_direction',dir,'score',r->'score'));
   INSERT INTO public.alpha_publication_followups(publication_id,horizon,due_at) VALUES(h.publication_id,'exit',stamp) ON CONFLICT DO NOTHING;
   new_id:=NULL;
  END IF;
  IF dir IS NOT NULL AND new_id IS NULL THEN
   INSERT INTO public.alpha_publications(source_key,symbol,instrument_key,sector,direction,score,signal_at,published_at,quote_at,reference_price,benchmark_price,components,quality)
    VALUES(r->>'source_key',r->>'symbol',r->>'instrument_key',r->>'sector',dir,(r->>'score')::numeric,sig,stamp,(r->>'quote_at')::timestamptz,(r->>'reference_price')::numeric,(r->>'benchmark_price')::numeric,r->'components',r->'quality') RETURNING id INTO new_id;
   created:=created+1;
   INSERT INTO public.alpha_publication_followups(publication_id,horizon,due_at)
    SELECT new_id,x->>'horizon',(x->>'due_at')::timestamptz+(stamp-(r->>'schedule_base')::timestamptz) FROM jsonb_array_elements(r->'schedule') x;
  ELSIF dir IS NOT NULL AND new_id IS NOT NULL THEN
   event_kind:=CASE WHEN abs((r->>'score')::numeric)-abs(h.last_score)>=15 THEN 'strengthened' WHEN abs(h.last_score)-abs((r->>'score')::numeric)>=15 THEN 'weakened' WHEN h.last_components IS DISTINCT FROM r->'component_keys' THEN 'components_changed' ELSE NULL END;
   IF event_kind IS NOT NULL THEN
    INSERT INTO public.alpha_publication_events(publication_id,event_at,signal_at,kind,details) VALUES(new_id,stamp,sig,event_kind,jsonb_build_object('score',r->'score','components',r->'components'));
   END IF;
  END IF;
  INSERT INTO public.alpha_publication_heads(symbol,publication_id,direction,last_signal_at,last_score,last_components)
   VALUES(r->>'symbol',new_id,dir,sig,CASE WHEN h.direction IS NOT DISTINCT FROM dir AND event_kind IS NULL AND h.publication_id IS NOT NULL THEN h.last_score ELSE (r->>'score')::numeric END,r->'component_keys')
   ON CONFLICT(symbol) DO UPDATE SET publication_id=excluded.publication_id,direction=excluded.direction,last_signal_at=excluded.last_signal_at,last_score=excluded.last_score,last_components=excluded.last_components;
 END LOOP;
 RETURN jsonb_build_object('created',created,'recorded_at',stamp);
END $$;
REVOKE ALL ON FUNCTION public.alpha_publish_snapshot(jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.alpha_publish_snapshot(jsonb) TO service_role;
-- Summary includes every matching publication, not just the visible page.
CREATE FUNCTION public.alpha_archive_summary(p_from timestamptz,p_to timestamptz,p_symbol text DEFAULT '',p_direction text DEFAULT '',p_horizon text DEFAULT '1d') RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT jsonb_build_object('published',count(*),'completed',count(f.price),'pending',count(*) FILTER(WHERE f.status='pending'),'missing',count(*) FILTER(WHERE f.status='missing'),'unmeasured',count(*) FILTER(WHERE f.publication_id IS NULL),
 'mean_directional_return_pct',avg(f.directional_return_pct),'median_directional_return_pct',percentile_cont(0.5) WITHIN GROUP(ORDER BY f.directional_return_pct),
 'positive_outcome_pct',100.0*count(*) FILTER(WHERE f.directional_return_pct>0)/nullif(count(f.directional_return_pct),0),
 'mean_stock_return_pct',avg(f.stock_return_pct),'mean_benchmark_return_pct',avg(f.benchmark_return_pct),'simulated_trades',count(f.simulated_net_return_pct),'mean_simulated_net_return_pct',avg(f.simulated_net_return_pct))
 FROM public.alpha_publications p LEFT JOIN public.alpha_publication_followups f ON f.publication_id=p.id AND f.horizon=p_horizon
 WHERE p.published_at>=p_from AND p.published_at<p_to AND (p_symbol='' OR p.symbol ILIKE '%'||p_symbol||'%') AND (p_direction='' OR p.direction=p_direction)
$$;
REVOKE ALL ON FUNCTION public.alpha_archive_summary(timestamptz,timestamptz,text,text,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.alpha_archive_summary(timestamptz,timestamptz,text,text,text) TO service_role;

CREATE FUNCTION public.alpha_guard_followup() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
BEGIN
 IF OLD.status <> 'pending' OR NEW.publication_id<>OLD.publication_id OR NEW.horizon<>OLD.horizon OR NEW.due_at<>OLD.due_at THEN RAISE EXCEPTION 'Settled follow-ups and original schedules cannot be rewritten'; END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.alpha_guard_followup() FROM PUBLIC,anon,authenticated;
CREATE TRIGGER alpha_followup_guard BEFORE UPDATE ON public.alpha_publication_followups FOR EACH ROW EXECUTE FUNCTION public.alpha_guard_followup();
