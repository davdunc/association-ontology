"""Mirror the Parquet store into Postgres (secondary store; Parquet stays canonical).

Full refresh inside one transaction: truncate, COPY every row, rebuild edges_current.
Requires the optional `postgres` extra (psycopg 3).
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from .schema import TABLES
from .store import Store


def _ddl() -> str:
    return resources.files("assoc_ontology").joinpath("postgres.sql").read_text()


def _cell(v: Any) -> Any:
    if isinstance(v, list) and v and isinstance(v[0], dict):
        return json.dumps(v, default=str)
    return v


def export(store: Store, dsn: str, schema: str = "assoc_ontology") -> dict[str, int]:
    import psycopg  # optional dependency

    counts: dict[str, int] = {}
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        cur.execute(f'SET search_path TO "{schema}"')
        cur.execute(_ddl())
        for table, sch in TABLES.items():
            cols = sch.names
            cur.execute(f"TRUNCATE {table}")
            rows = store.rows(table)
            with cur.copy(f"COPY {table} ({', '.join(cols)}) FROM STDIN") as cp:
                for r in rows:
                    cp.write_row([_cell(r[c]) for c in cols])
            counts[table] = len(rows)
        cur.execute("TRUNCATE edges_current")
        edges = store.current_edges()
        cols = [
            "edge_id",
            "subject_id",
            "object_id",
            "rel_type",
            "category",
            "status",
            "best_tier",
            "materiality",
            "weight",
            "dependent_party",
            "exposure_pct",
            "evidence_ids",
            "effective_date",
            "first_seen",
            "last_confirmed",
        ]
        with cur.copy(f"COPY edges_current ({', '.join(cols)}) FROM STDIN") as cp:
            for e in edges.values():
                cp.write_row([e[c] for c in cols])
        counts["edges_current"] = len(edges)
    return counts
