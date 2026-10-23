# assoc-ontology

Append-only Parquet datastore for **accountable associations** between publicly traded companies
(suppliers, lenders, underwriters, partners, owners) and the 2nd/3rd-order baskets derived from them.
The canonical spec is [`docs/spec.md`](docs/spec.md); the human-readable copy lives in Notion.

- **Canonical store:** Parquet under `data/`, one immutable partition per run.
- **Secondary store:** Postgres mirror (`export-postgres`).
- **Guardrails in code:** runs can only *propose*; only `review` can make an edge `active`, and only with tier A/B evidence.

## Install

```bash
pip install -e ".[dev]"            # core + tests
pip install -e ".[postgres]"       # Postgres mirror
```

## Commands

```bash
assoc-ontology ingest inbox/batch.jsonl --trigger on_demand --anchors tkr:META \
    --sources "edgar:8-K,edgar:10-Q,ir" --failures "edgar full-text timeout"   # append a run
assoc-ontology ingest inbox/batch.jsonl --trigger scheduled --dry-run         # validate only
assoc-ontology edges --entity tkr:META --status proposed                      # current state (JSONL)
assoc-ontology review e_1a2b3c4d5e6f7a8b accepted --note "checked 10-K p.42"  # promote to active
assoc-ontology paths tkr:META --max-hops 3 [--include-proposed]               # 2nd/3rd-order paths
assoc-ontology stale                                                          # active, unconfirmed >400d
assoc-ontology export-postgres --dsn postgresql://user@host/db                # mirror to Postgres
```

Query directly with any Parquet engine, e.g. DuckDB:

```sql
SELECT * FROM read_parquet('data/edge_events/*/*.parquet') WHERE object_id = 'tkr:META';
```

## Batch format (JSONL)

One object per line; `kind` is `entity`, `evidence`, `edge`, or `basket`. Entities and evidence referenced by
an edge must already exist or appear in the same batch.

```json
{"kind":"entity","ticker":"MU","legal_name":"Micron Technology, Inc.","entity_type":"public_company","roles":["supplier"],"universe_source":"discovered"}
{"kind":"evidence","url":"https://www.sec.gov/Archives/...","tier":"A","source_form":"8-K","item":"1.01","accession_no":"0000000000-26-000000","filed_date":"2026-10-20","excerpt":"..."}
{"kind":"edge","event_type":"new","subject_id":"tkr:MU","object_id":"tkr:META","rel_type":"SUPPLIES_COMPONENT_TO","materiality":"unknown","dependent_party":"unknown","exposure_pct":null,"evidence_ids":["ev_<hash>"],"effective_date":"2026-10-20","trade_relevance":"watch","note":"..."}
```

(Illustrative shape only — not a claimed relationship.) Evidence IDs are `ev_` + sha256(url|accession_no|item)[:16];
compute with `assoc_ontology.store.evidence_id_for`. Enum values are lowercase snake_case versions of the spec labels;
see `src/assoc_ontology/vocab.py`.

| Field | Values |
|---|---|
| `event_type` (runs) | new, amended, strengthened, weakened, terminated, reclassified, reconfirmed |
| `tier` | A filing · B company release · C reputable press · D inferred/statistical |
| `materiality` → default weight | high 0.9 · medium 0.6 · low 0.3 · unknown 0.2 |
| `dependent_party` | subject, object, both, unknown |
| `exposure_pct` | 0–1 fraction of the dependent party's revenue/cost, or null if undisclosed |

## Layout

```
data/<table>/run_id=<YYYYMMDDTHHMMSSffffffZ-xxxx>/part-0.parquet
  tables: runs, entities, evidence, edge_events, baskets
```
