-- Situational awareness: a world model, a causal graph, and what it implies
-- for companies. Pointed at the Indian AI-infrastructure chain, because that
-- is the chain this warehouse actually holds -- company_master is 2,714 rows
-- and every one of them is NSE, India, INR. A graph built on Nvidia and SK
-- Hynix would have no prices, no financials and no consensus behind it.
--
-- The design constraint is the same one the options warehouse settled on: a
-- belief recorded today must never be quietly replaced by a belief held
-- tomorrow. Every table here is append-only on (key, as_of), so what the
-- engine thought last month survives being wrong.

-- Nodes are economic quantities, not companies. "Data-centre power demand" is
-- a node; NTPC is not.
CREATE TABLE IF NOT EXISTS public.sa_node (
  node_id        text        PRIMARY KEY,
  label          text        NOT NULL,
  layer          text        NOT NULL,
  unit           text,
  description    text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT sa_node_layer_chk CHECK (layer IN (
    'capability', 'demand', 'compute', 'infrastructure', 'power', 'labour'))
);

-- A directed edge carries an elasticity, a lag and a confidence. Without all
-- three it is an opinion drawn as an arrow: elasticity says how much, lag says
-- when, confidence says how much to discount both.
CREATE TABLE IF NOT EXISTS public.sa_edge (
  from_node      text        NOT NULL REFERENCES public.sa_node (node_id),
  to_node        text        NOT NULL REFERENCES public.sa_node (node_id),
  as_of          date        NOT NULL,
  elasticity     numeric(8,4) NOT NULL,
  -- A range, so the engine can propagate a bear and bull case rather than
  -- carrying 0.54 four hops as though it were measured. Nullable: an edge that
  -- has no honest range says so, and the engine then uses the base for all
  -- three rather than inventing width.
  elasticity_low  numeric(8,4),
  elasticity_high numeric(8,4),
  CONSTRAINT causal_edge_elasticity_range CHECK (
    (elasticity_low IS NULL OR elasticity_low <= elasticity) AND
    (elasticity_high IS NULL OR elasticity_high >= elasticity)
  ),
  lag_months_min smallint    NOT NULL DEFAULT 0,
  lag_months_max smallint    NOT NULL DEFAULT 0,
  confidence     numeric(4,3) NOT NULL,
  basis          text        NOT NULL,
  source         text,
  PRIMARY KEY (from_node, to_node, as_of),
  CONSTRAINT sa_edge_conf_chk CHECK (confidence > 0 AND confidence <= 1),
  CONSTRAINT sa_edge_lag_chk CHECK (lag_months_max >= lag_months_min),
  CONSTRAINT sa_edge_no_self CHECK (from_node <> to_node)
);

-- How much of a company's fortunes ride on a node. Kept separate from the edge
-- table because a company is not an economic quantity and should not be able
-- to sit in the middle of a causal chain.
CREATE TABLE IF NOT EXISTS public.sa_company_exposure (
  symbol         text        NOT NULL,
  node_id        text        NOT NULL REFERENCES public.sa_node (node_id),
  as_of          date        NOT NULL,
  exposure       numeric(5,3) NOT NULL,
  revenue_share  numeric(5,3),
  margin_sensitivity numeric(6,3),
  confidence     numeric(4,3) NOT NULL,
  basis          text        NOT NULL,
  PRIMARY KEY (symbol, node_id, as_of),
  CONSTRAINT sa_exposure_range CHECK (exposure >= -1 AND exposure <= 1),
  CONSTRAINT sa_exposure_conf CHECK (confidence > 0 AND confidence <= 1)
);

-- What the engine currently believes each node is doing, and what the market
-- appears to believe. The gap between them is the whole point: a node moving
-- as expected is news to nobody.
CREATE TABLE IF NOT EXISTS public.sa_world_state (
  node_id        text        NOT NULL REFERENCES public.sa_node (node_id),
  as_of          date        NOT NULL,
  level          numeric(10,3),
  our_growth_pct numeric(10,3),
  consensus_growth_pct numeric(10,3),
  confidence     numeric(4,3) NOT NULL,
  basis          text        NOT NULL,
  PRIMARY KEY (node_id, as_of)
);

CREATE INDEX IF NOT EXISTS sa_edge_from_idx ON public.sa_edge (from_node, as_of DESC);
CREATE INDEX IF NOT EXISTS sa_exposure_node_idx ON public.sa_company_exposure (node_id, as_of DESC);
CREATE INDEX IF NOT EXISTS sa_world_state_node_idx ON public.sa_world_state (node_id, as_of DESC);

ALTER TABLE public.sa_node ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sa_edge ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sa_company_exposure ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sa_world_state ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.sa_node FROM anon, authenticated;
REVOKE ALL ON public.sa_edge FROM anon, authenticated;
REVOKE ALL ON public.sa_company_exposure FROM anon, authenticated;
REVOKE ALL ON public.sa_world_state FROM anon, authenticated;

COMMENT ON TABLE public.sa_edge IS
  'Directed causal edges with elasticity, lag and confidence. An edge without '
  'all three is an opinion drawn as an arrow.';
COMMENT ON COLUMN public.sa_company_exposure.exposure IS
  'Signed -1..1. Negative is real: IT services carry a negative edge to '
  'automation capability.';
