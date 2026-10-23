-- Postgres mirror of the canonical Parquet tables. Rebuilt by `assoc-ontology export-postgres`.
CREATE TABLE IF NOT EXISTS runs (
  run_id text PRIMARY KEY, trigger text NOT NULL, anchors text[], note text,
  started_at timestamptz, finished_at timestamptz, sources_checked text[], failures text[]
);
CREATE TABLE IF NOT EXISTS entities (
  entity_id text NOT NULL, ticker text, cik text, lei text, legal_name text, entity_type text,
  roles text[], universe_source text, in_daily_review boolean, sector text,
  recorded_at timestamptz NOT NULL, run_id text NOT NULL,
  PRIMARY KEY (entity_id, run_id)
);
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id text NOT NULL, url text NOT NULL, tier char(1) NOT NULL CHECK (tier IN ('A','B','C','D')),
  source_form text, item text, accession_no text, publisher text, filed_date date, excerpt text,
  retrieved_at timestamptz, run_id text NOT NULL,
  PRIMARY KEY (evidence_id, run_id)
);
CREATE TABLE IF NOT EXISTS edge_events (
  event_id text PRIMARY KEY, edge_id text NOT NULL, run_id text NOT NULL, observed_at timestamptz NOT NULL,
  event_type text NOT NULL, subject_id text NOT NULL, object_id text NOT NULL, rel_type text NOT NULL,
  category text NOT NULL, agreement_key text, status text NOT NULL, materiality text, weight double precision,
  dependent_party text, exposure_pct double precision CHECK (exposure_pct BETWEEN 0 AND 1),
  best_tier char(1), evidence_ids text[], effective_date date, end_date date, trade_relevance text, note text
);
CREATE INDEX IF NOT EXISTS edge_events_edge_idx ON edge_events (edge_id, observed_at);
CREATE INDEX IF NOT EXISTS edge_events_subject_idx ON edge_events (subject_id);
CREATE INDEX IF NOT EXISTS edge_events_object_idx ON edge_events (object_id);
CREATE TABLE IF NOT EXISTS baskets (
  basket_id text NOT NULL, run_id text NOT NULL, recorded_at timestamptz NOT NULL, anchor_id text NOT NULL,
  basket_type text NOT NULL, members jsonb NOT NULL, thesis text, catalyst text, hedge_leg text,
  invalidation text, weighting text, status text,
  PRIMARY KEY (basket_id, run_id)
);
CREATE TABLE IF NOT EXISTS edges_current (
  edge_id text PRIMARY KEY, subject_id text, object_id text, rel_type text, category text, status text,
  best_tier char(1), materiality text, weight double precision, dependent_party text,
  exposure_pct double precision, evidence_ids text[], effective_date date,
  first_seen timestamptz, last_confirmed timestamptz
);
