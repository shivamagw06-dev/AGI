-- HIP / HAP append-only historical store (separate from live KAIP)

CREATE TABLE IF NOT EXISTS historical_raw_archive (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    collector_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    company_symbol TEXT,
    category TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    effective_start TEXT,
    effective_end TEXT,
    checksum TEXT NOT NULL,
    validation_status TEXT,
    validation_errors_json TEXT,
    ingestion_run_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_symbol_cat
    ON historical_raw_archive(company_symbol, category, retrieved_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_checksum
    ON historical_raw_archive(checksum);

CREATE TABLE IF NOT EXISTS historical_ingestion_runs (
    run_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    collector_id TEXT NOT NULL,
    symbols_json TEXT NOT NULL,
    categories_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL,
    raw_accepted INTEGER NOT NULL DEFAULT 0,
    raw_rejected INTEGER NOT NULL DEFAULT 0,
    objects_written INTEGER NOT NULL DEFAULT 0,
    detail_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_knowledge_objects (
    object_id TEXT PRIMARY KEY,
    object_type TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    company_symbol TEXT,
    effective_date TEXT NOT NULL,
    period_kind TEXT NOT NULL,
    version INTEGER NOT NULL,
    previous_object_id TEXT,
    knowledge_json TEXT NOT NULL,
    entity_refs_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hko_type_subject_eff
    ON historical_knowledge_objects(object_type, subject_key, effective_date, version DESC);

CREATE TABLE IF NOT EXISTS historical_prices (
    object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    period_kind TEXT NOT NULL,
    version INTEGER NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    knowledge_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_prices_symbol_date_ver
    ON historical_prices(company_symbol, effective_date, period_kind, version);

CREATE TABLE IF NOT EXISTS historical_financials (
    object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    period_kind TEXT NOT NULL,
    statement_type TEXT NOT NULL,
    version INTEGER NOT NULL,
    revenue REAL,
    net_income REAL,
    knowledge_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fins_symbol_period_ver
    ON historical_financials(company_symbol, effective_date, period_kind, statement_type, version);

CREATE TABLE IF NOT EXISTS historical_balance_sheets (
    object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    period_kind TEXT NOT NULL,
    version INTEGER NOT NULL,
    knowledge_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_cashflows (
    object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    period_kind TEXT NOT NULL,
    version INTEGER NOT NULL,
    knowledge_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_dividends (
    object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    version INTEGER NOT NULL,
    amount REAL,
    knowledge_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_actions (
    object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    action_type TEXT NOT NULL,
    version INTEGER NOT NULL,
    knowledge_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_events (
    object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    event_type TEXT NOT NULL,
    version INTEGER NOT NULL,
    knowledge_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_reports (
    object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    report_type TEXT NOT NULL,
    version INTEGER NOT NULL,
    title TEXT,
    knowledge_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_company_profiles (
    object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    version INTEGER NOT NULL,
    knowledge_json TEXT NOT NULL,
    entity_refs_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_news (
    object_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    version INTEGER NOT NULL,
    title TEXT,
    knowledge_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_metadata (
    meta_key TEXT PRIMARY KEY,
    meta_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_entities (
    company_symbol TEXT PRIMARY KEY,
    company_name TEXT,
    sector TEXT,
    sector_key TEXT,
    industry TEXT,
    index_membership_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Sprint 8.2 Timeline Intelligence (append-only narrative nodes)
CREATE TABLE IF NOT EXISTS historical_timelines (
    event_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    year INTEGER NOT NULL,
    date TEXT,
    title TEXT NOT NULL,
    description TEXT,
    importance TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    links_json TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL,
    version INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_timelines_scope_subject_year
    ON historical_timelines(scope, subject_key, year ASC, version DESC);

CREATE TABLE IF NOT EXISTS historical_timeline_links (
    link_id TEXT PRIMARY KEY,
    from_key TEXT NOT NULL,
    to_key TEXT NOT NULL,
    relation TEXT NOT NULL,
    note TEXT,
    subject_key TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_timeline_links_subject
    ON historical_timeline_links(subject_key, from_key, to_key);

-- Sprint 8.3 Historical Relationship Intelligence (evidence-backed graph)
CREATE TABLE IF NOT EXISTS historical_relationships (
    relationship_id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    source_key TEXT NOT NULL,
    source_label TEXT NOT NULL,
    target_key TEXT NOT NULL,
    target_label TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    direction TEXT NOT NULL,
    confidence TEXT NOT NULL,
    occurrences INTEGER NOT NULL,
    average_delay TEXT,
    first_observed TEXT,
    last_confirmed TEXT,
    chain_json TEXT NOT NULL,
    version INTEGER NOT NULL,
    published INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hri_domain_source
    ON historical_relationships(domain, source_key);
CREATE INDEX IF NOT EXISTS idx_hri_domain_target
    ON historical_relationships(domain, target_key);
CREATE INDEX IF NOT EXISTS idx_hri_type
    ON historical_relationships(relationship_type, confidence);

CREATE TABLE IF NOT EXISTS company_relationships (
    relationship_id TEXT PRIMARY KEY,
    company_symbol TEXT NOT NULL,
    FOREIGN KEY(relationship_id) REFERENCES historical_relationships(relationship_id)
);
CREATE INDEX IF NOT EXISTS idx_company_rel_symbol
    ON company_relationships(company_symbol, relationship_id);

CREATE TABLE IF NOT EXISTS sector_relationships (
    relationship_id TEXT PRIMARY KEY,
    sector_key TEXT NOT NULL,
    FOREIGN KEY(relationship_id) REFERENCES historical_relationships(relationship_id)
);
CREATE INDEX IF NOT EXISTS idx_sector_rel_key
    ON sector_relationships(sector_key, relationship_id);

CREATE TABLE IF NOT EXISTS macro_relationships (
    relationship_id TEXT PRIMARY KEY,
    macro_event_key TEXT NOT NULL,
    FOREIGN KEY(relationship_id) REFERENCES historical_relationships(relationship_id)
);
CREATE INDEX IF NOT EXISTS idx_macro_rel_key
    ON macro_relationships(macro_event_key, relationship_id);

CREATE TABLE IF NOT EXISTS market_relationships (
    relationship_id TEXT PRIMARY KEY,
    market_key TEXT NOT NULL,
    FOREIGN KEY(relationship_id) REFERENCES historical_relationships(relationship_id)
);
CREATE INDEX IF NOT EXISTS idx_market_rel_key
    ON market_relationships(market_key, relationship_id);

CREATE TABLE IF NOT EXISTS relationship_evidence (
    evidence_id TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    summary TEXT NOT NULL,
    period TEXT,
    source_refs_json TEXT NOT NULL,
    weight REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(relationship_id) REFERENCES historical_relationships(relationship_id)
);
CREATE INDEX IF NOT EXISTS idx_rel_evidence_rel
    ON relationship_evidence(relationship_id);

CREATE TABLE IF NOT EXISTS relationship_versions (
    version_id TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(relationship_id) REFERENCES historical_relationships(relationship_id)
);
CREATE INDEX IF NOT EXISTS idx_rel_versions
    ON relationship_versions(relationship_id, version DESC);

-- Sprint 8.4 Historical Analogue Intelligence
CREATE TABLE IF NOT EXISTS analogue_searches (
    search_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    question TEXT,
    situation TEXT,
    as_of_period TEXT,
    features_json TEXT NOT NULL,
    top_k INTEGER NOT NULL,
    result_count INTEGER NOT NULL,
    avg_similarity REAL,
    latency_ms REAL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_analogue_searches_entity
    ON analogue_searches(scope, entity_key, created_at DESC);

CREATE TABLE IF NOT EXISTS analogue_results (
    result_id TEXT PRIMARY KEY,
    search_id TEXT NOT NULL,
    analogue_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    matched_period TEXT NOT NULL,
    similarity_score REAL NOT NULL,
    confidence TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(search_id) REFERENCES analogue_searches(search_id)
);
CREATE INDEX IF NOT EXISTS idx_analogue_results_search
    ON analogue_results(search_id, rank ASC);
