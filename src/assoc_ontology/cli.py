"""assoc-ontology CLI."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import graph
from .store import Store, ValidationError, read_jsonl


def _out(obj: Any) -> None:
    json.dump(obj, sys.stdout, default=str, indent=None)
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="assoc-ontology")
    p.add_argument("--root", default="data", help="Parquet store root (default: data)")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("ingest", help="append one run's JSONL detections")
    i.add_argument("file")
    i.add_argument("--trigger", required=True, choices=["scheduled", "on_demand", "seed"])
    i.add_argument("--anchors", default="", help="comma-separated entity_ids")
    i.add_argument("--note")
    i.add_argument("--sources", default="", help="comma-separated sources checked")
    i.add_argument("--failures", default="", help="'|'-separated lookup failures")
    i.add_argument("--dry-run", action="store_true")

    r = sub.add_parser("review", help="accept or reject an edge (only path to active)")
    r.add_argument("edge_id")
    r.add_argument("decision", choices=["accepted", "rejected"])
    r.add_argument("--note")

    sub.add_parser("entities")
    e = sub.add_parser("edges")
    e.add_argument("--entity")
    e.add_argument("--status")

    pa_ = sub.add_parser("paths")
    pa_.add_argument("anchor_id")
    pa_.add_argument("--max-hops", type=int, default=3)
    pa_.add_argument("--include-proposed", action="store_true")

    sub.add_parser("stale")
    sub.add_parser("runs")

    pg = sub.add_parser("export-postgres", help="mirror Parquet into Postgres")
    pg.add_argument("--dsn", required=True)
    pg.add_argument("--schema", default="assoc_ontology")

    a = p.parse_args(argv)
    store = Store(a.root)
    try:
        if a.cmd == "ingest":
            recs = read_jsonl(a.file)
            split = lambda s, sep=",": [x for x in s.split(sep) if x]
            if a.dry_run:
                import shutil
                import tempfile

                with tempfile.TemporaryDirectory() as td:
                    if store.root.exists():
                        shutil.copytree(store.root, td, dirs_exist_ok=True)
                    run_id, counts = Store(td).ingest(
                        recs, a.trigger, split(a.anchors), a.note, split(a.sources), split(a.failures, "|")
                    )
                _out({"dry_run": True, "counts": counts})
            else:
                run_id, counts = store.ingest(
                    recs, a.trigger, split(a.anchors), a.note, split(a.sources), split(a.failures, "|")
                )
                _out({"run_id": run_id, "counts": counts})
        elif a.cmd == "review":
            _out({"run_id": store.review(a.edge_id, a.decision, a.note)})
        elif a.cmd == "entities":
            for v in store.entities().values():
                _out(v)
        elif a.cmd == "edges":
            for v in store.current_edges().values():
                if a.entity and a.entity not in (v["subject_id"], v["object_id"]):
                    continue
                if a.status and v["status"] != a.status:
                    continue
                _out(v)
        elif a.cmd == "paths":
            for v in graph.paths(store.current_edges(), a.anchor_id, a.max_hops, a.include_proposed):
                _out(v)
        elif a.cmd == "stale":
            for v in graph.stale(store.current_edges()):
                _out(v)
        elif a.cmd == "runs":
            for v in store.rows("runs"):
                _out(v)
        elif a.cmd == "export-postgres":
            from .pg import export

            _out(export(store, a.dsn, a.schema))
    except ValidationError as exc:
        print(f"validation error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
