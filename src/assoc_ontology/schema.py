"""Arrow schemas for the append-only Parquet tables (spec §11)."""

from __future__ import annotations

import pyarrow as pa

TS = pa.timestamp("us", tz="UTC")

RUNS = pa.schema(
    [
        ("run_id", pa.string()),
        ("trigger", pa.string()),
        ("anchors", pa.list_(pa.string())),
        ("note", pa.string()),
        ("started_at", TS),
        ("finished_at", TS),
        ("sources_checked", pa.list_(pa.string())),
        ("failures", pa.list_(pa.string())),
    ]
)

ENTITIES = pa.schema(
    [
        ("entity_id", pa.string()),
        ("ticker", pa.string()),
        ("cik", pa.string()),
        ("lei", pa.string()),
        ("legal_name", pa.string()),
        ("entity_type", pa.string()),
        ("roles", pa.list_(pa.string())),
        ("universe_source", pa.string()),
        ("in_daily_review", pa.bool_()),
        ("sector", pa.string()),
        ("recorded_at", TS),
        ("run_id", pa.string()),
    ]
)

EVIDENCE = pa.schema(
    [
        ("evidence_id", pa.string()),
        ("url", pa.string()),
        ("tier", pa.string()),
        ("source_form", pa.string()),
        ("item", pa.string()),
        ("accession_no", pa.string()),
        ("publisher", pa.string()),
        ("filed_date", pa.date32()),
        ("excerpt", pa.string()),
        ("retrieved_at", TS),
        ("run_id", pa.string()),
    ]
)

EDGE_EVENTS = pa.schema(
    [
        ("event_id", pa.string()),
        ("edge_id", pa.string()),
        ("run_id", pa.string()),
        ("observed_at", TS),
        ("event_type", pa.string()),
        ("subject_id", pa.string()),
        ("object_id", pa.string()),
        ("rel_type", pa.string()),
        ("category", pa.string()),
        ("agreement_key", pa.string()),
        ("status", pa.string()),
        ("materiality", pa.string()),
        ("weight", pa.float64()),
        ("dependent_party", pa.string()),
        ("exposure_pct", pa.float64()),
        ("best_tier", pa.string()),
        ("evidence_ids", pa.list_(pa.string())),
        ("effective_date", pa.date32()),
        ("end_date", pa.date32()),
        ("trade_relevance", pa.string()),
        ("note", pa.string()),
    ]
)

MEMBER = pa.struct(
    [
        ("entity_id", pa.string()),
        ("hop", pa.int8()),
        ("path_score", pa.float64()),
        ("weight", pa.float64()),
    ]
)

BASKETS = pa.schema(
    [
        ("basket_id", pa.string()),
        ("run_id", pa.string()),
        ("recorded_at", TS),
        ("anchor_id", pa.string()),
        ("basket_type", pa.string()),
        ("members", pa.list_(MEMBER)),
        ("thesis", pa.string()),
        ("catalyst", pa.string()),
        ("hedge_leg", pa.string()),
        ("invalidation", pa.string()),
        ("weighting", pa.string()),
        ("status", pa.string()),
    ]
)

TABLES: dict[str, pa.Schema] = {
    "runs": RUNS,
    "entities": ENTITIES,
    "evidence": EVIDENCE,
    "edge_events": EDGE_EVENTS,
    "baskets": BASKETS,
}
