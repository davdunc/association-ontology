"""Append-only Parquet store: ingest, validate, current state, review (spec §6–10).

Layout: <root>/<table>/run_id=<run_id>/part-0.parquet. Files are never rewritten;
state changes (including human review) are new rows in a new partition.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import secrets
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from . import vocab
from .schema import TABLES

UTC = dt.UTC


class ValidationError(ValueError):
    pass


def now() -> dt.datetime:
    return dt.datetime.now(UTC)


def new_run_id(ts: dt.datetime | None = None) -> str:
    ts = ts or now()
    return ts.strftime("%Y%m%dT%H%M%S%fZ") + "-" + secrets.token_hex(2)


def _h(*parts: str | None) -> str:
    return hashlib.sha256("|".join(p or "" for p in parts).encode()).hexdigest()[:16]


def entity_id_for(ticker: str | None = None, cik: str | None = None, name: str | None = None) -> str:
    if ticker:
        return f"tkr:{ticker.upper()}"
    if cik:
        return f"cik:{int(cik):010d}"
    if name:
        return "name:" + "-".join(name.lower().split())
    raise ValidationError("entity needs ticker, cik, or name")


def edge_id_for(subject_id: str, rel_type: str, object_id: str, agreement_key: str | None = None) -> str:
    return "e_" + _h(subject_id, rel_type, object_id, agreement_key)


def evidence_id_for(url: str, accession_no: str | None = None, item: str | None = None) -> str:
    return "ev_" + _h(url, accession_no, item)


def _date(v: Any) -> dt.date | None:
    if v in (None, ""):
        return None
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v)[:10])


def _ts(v: Any) -> dt.datetime | None:
    if v in (None, ""):
        return None
    if isinstance(v, dt.datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    return dt.datetime.fromisoformat(str(v))


@dataclass
class Batch:
    run: dict[str, Any]
    rows: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {t: [] for t in TABLES})


class Store:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    # ---------- reading ----------
    def files(self, table: str) -> list[Path]:
        return sorted((self.root / table).glob("run_id=*/*.parquet"))

    def read(self, table: str) -> pa.Table:
        files = self.files(table)
        if not files:
            return TABLES[table].empty_table()
        return pa.concat_tables([pq.read_table(f, schema=TABLES[table]) for f in files])

    def rows(self, table: str) -> list[dict[str, Any]]:
        return self.read(table).to_pylist()

    def entities(self) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for r in sorted(self.rows("entities"), key=lambda r: r["recorded_at"]):
            prev = latest.get(r["entity_id"], {})
            latest[r["entity_id"]] = {**prev, **{k: v for k, v in r.items() if v is not None}}
        return latest

    def evidence(self) -> dict[str, dict[str, Any]]:
        return {r["evidence_id"]: r for r in self.rows("evidence")}

    def current_edges(self) -> dict[str, dict[str, Any]]:
        """Latest state per edge plus first_seen / last_confirmed."""
        out: dict[str, dict[str, Any]] = {}
        for ev in sorted(self.rows("edge_events"), key=lambda r: (r["observed_at"], r["run_id"], r["event_id"])):
            cur = out.get(ev["edge_id"])
            state = dict(ev)
            if cur is None:
                state["first_seen"] = ev["observed_at"]
                state["last_confirmed"] = ev["observed_at"]
            else:
                state["first_seen"] = cur["first_seen"]
                state["last_confirmed"] = (
                    ev["observed_at"] if ev["event_type"] in vocab.DETECTION_EVENTS else cur["last_confirmed"]
                )
            out[ev["edge_id"]] = state
        return out

    # ---------- writing ----------
    def _write(self, batch: Batch) -> dict[str, int]:
        run_id = batch.run["run_id"]
        counts: dict[str, int] = {}
        batch.rows["runs"] = [batch.run]
        for table, rows in batch.rows.items():
            if not rows:
                continue
            d = self.root / table / f"run_id={run_id}"
            if d.exists():
                raise ValidationError(f"partition already exists: {d}")
            d.mkdir(parents=True)
            pq.write_table(pa.Table.from_pylist(rows, schema=TABLES[table]), d / "part-0.parquet", compression="zstd")
            counts[table] = len(rows)
        return counts

    def ingest(
        self,
        records: Iterable[dict[str, Any]],
        trigger: str,
        anchors: list[str] | None = None,
        note: str | None = None,
        sources_checked: list[str] | None = None,
        failures: list[str] | None = None,
        ts: dt.datetime | None = None,
    ) -> tuple[str, dict[str, int]]:
        """Validate and append one run's detections. Never promotes an edge to active."""
        if trigger not in vocab.TRIGGERS - {"review"}:
            raise ValidationError(f"bad trigger {trigger!r}")
        ts = ts or now()
        run_id = new_run_id(ts)
        batch = Batch(
            run={
                "run_id": run_id,
                "trigger": trigger,
                "anchors": anchors or [],
                "note": note,
                "started_at": ts,
                "finished_at": now(),
                "sources_checked": sources_checked or [],
                "failures": failures or [],
            }
        )
        known_entities = set(self.entities())
        evidence = self.evidence()
        edges = self.current_edges()
        records = list(records)

        for r in records:
            if r.get("kind") == "entity":
                row = self._entity_row(r, run_id, ts)
                known_entities.add(row["entity_id"])
                batch.rows["entities"].append(row)
        for r in records:
            if r.get("kind") == "evidence":
                row = self._evidence_row(r, run_id, ts)
                evidence[row["evidence_id"]] = row
                batch.rows["evidence"].append(row)
        for r in records:
            kind = r.get("kind")
            if kind == "edge":
                row = self._edge_row(r, run_id, ts, known_entities, evidence, edges)
                edges[row["edge_id"]] = {**edges.get(row["edge_id"], {}), **row}
                batch.rows["edge_events"].append(row)
            elif kind == "basket":
                batch.rows["baskets"].append(self._basket_row(r, run_id, ts, known_entities))
            elif kind not in ("entity", "evidence"):
                raise ValidationError(f"unknown record kind {kind!r}")
        return run_id, self._write(batch)

    def review(self, edge_id: str, decision: str, note: str | None = None) -> str:
        """Human acceptance/rejection. Only path to status=active."""
        if decision not in vocab.REVIEW_EVENTS:
            raise ValidationError("decision must be accepted or rejected")
        cur = self.current_edges().get(edge_id)
        if cur is None:
            raise ValidationError(f"unknown edge {edge_id}")
        if decision == "accepted":
            if cur["best_tier"] not in vocab.ACCOUNTABLE_TIERS:
                raise ValidationError("only tier A/B evidence can make an edge active")
            if cur["status"] in ("terminated", "rejected"):
                raise ValidationError(f"cannot accept a {cur['status']} edge")
        ts = now()
        run_id = new_run_id(ts)
        row = {k: cur.get(k) for k in TABLES["edge_events"].names}
        row.update(
            event_id="x_" + _h(edge_id, run_id, decision),
            run_id=run_id,
            observed_at=ts,
            event_type=decision,
            status="active" if decision == "accepted" else "rejected",
            note=note,
        )
        batch = Batch(
            run={
                "run_id": run_id,
                "trigger": "review",
                "anchors": [],
                "note": note,
                "started_at": ts,
                "finished_at": ts,
                "sources_checked": [],
                "failures": [],
            }
        )
        batch.rows["edge_events"].append(row)
        self._write(batch)
        return run_id

    # ---------- row builders ----------
    @staticmethod
    def _entity_row(r: dict[str, Any], run_id: str, ts: dt.datetime) -> dict[str, Any]:
        eid = r.get("entity_id") or entity_id_for(r.get("ticker"), r.get("cik"), r.get("legal_name"))
        et = r.get("entity_type", "public_company")
        if et not in vocab.ENTITY_TYPES:
            raise ValidationError(f"{eid}: bad entity_type {et!r}")
        roles = r.get("roles") or []
        if bad := set(roles) - vocab.ROLES:
            raise ValidationError(f"{eid}: bad roles {bad}")
        us = r.get("universe_source", "discovered")
        if us not in vocab.UNIVERSE_SOURCES:
            raise ValidationError(f"{eid}: bad universe_source {us!r}")
        return {
            "entity_id": eid,
            "ticker": (r.get("ticker") or None) and r["ticker"].upper(),
            "cik": r.get("cik"),
            "lei": r.get("lei"),
            "legal_name": r.get("legal_name"),
            "entity_type": et,
            "roles": roles,
            "universe_source": us,
            "in_daily_review": bool(r.get("in_daily_review", False)),
            "sector": r.get("sector"),
            "recorded_at": ts,
            "run_id": run_id,
        }

    @staticmethod
    def _evidence_row(r: dict[str, Any], run_id: str, ts: dt.datetime) -> dict[str, Any]:
        if not r.get("url"):
            raise ValidationError("evidence needs url")
        tier = r.get("tier")
        if tier not in vocab.TIERS:
            raise ValidationError(f"{r['url']}: bad tier {tier!r}")
        return {
            "evidence_id": r.get("evidence_id") or evidence_id_for(r["url"], r.get("accession_no"), r.get("item")),
            "url": r["url"],
            "tier": tier,
            "source_form": r.get("source_form"),
            "item": r.get("item"),
            "accession_no": r.get("accession_no"),
            "publisher": r.get("publisher"),
            "filed_date": _date(r.get("filed_date")),
            "excerpt": r.get("excerpt"),
            "retrieved_at": _ts(r.get("retrieved_at")) or ts,
            "run_id": run_id,
        }

    @staticmethod
    def _edge_row(
        r: dict[str, Any],
        run_id: str,
        ts: dt.datetime,
        known: set[str],
        evidence: dict[str, dict[str, Any]],
        edges: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        et = r.get("event_type", "new")
        if et not in vocab.DETECTION_EVENTS:
            raise ValidationError(f"runs may only write detection events, got {et!r}")
        s, o, rt = r.get("subject_id"), r.get("object_id"), r.get("rel_type")
        if rt not in vocab.REL_TYPES:
            raise ValidationError(f"bad rel_type {rt!r}")
        for e in (s, o):
            if e not in known:
                raise ValidationError(f"unknown entity {e!r}; include an entity record")
        if s == o:
            raise ValidationError("self-edge")
        eid = edge_id_for(s, rt, o, r.get("agreement_key"))
        prior = edges.get(eid)
        ev_ids = list(r.get("evidence_ids") or [])
        if not ev_ids and et != "reconfirmed":
            raise ValidationError(f"{eid}: evidence required")
        for x in ev_ids:
            if x not in evidence:
                raise ValidationError(f"{eid}: unknown evidence {x}")
        tiers = sorted(
            {evidence[x]["tier"] for x in ev_ids}
            | ({prior["best_tier"]} if prior and prior.get("best_tier") else set())
        )
        mat = r.get("materiality", prior["materiality"] if prior else "unknown")
        if mat not in vocab.MATERIALITY:
            raise ValidationError(f"{eid}: bad materiality {mat!r}")
        dp = r.get("dependent_party", prior["dependent_party"] if prior else "unknown")
        if dp not in vocab.DEPENDENT_PARTY:
            raise ValidationError(f"{eid}: bad dependent_party {dp!r}")
        exp = r.get("exposure_pct", prior["exposure_pct"] if prior else None)
        if exp is not None and not 0 <= float(exp) <= 1:
            raise ValidationError(f"{eid}: exposure_pct must be a 0-1 fraction or null")
        tr = r.get("trade_relevance", "background")
        if tr not in vocab.TRADE_RELEVANCE:
            raise ValidationError(f"{eid}: bad trade_relevance {tr!r}")
        if prior is None and et not in ("new",):
            raise ValidationError(f"{eid}: first event for an edge must be 'new'")
        prior_status = prior["status"] if prior else None
        if et == "terminated":
            status = "terminated"
        elif et == "reconfirmed":
            status = prior_status
        elif prior_status in (None, "proposed", "rejected"):
            status = "proposed"
        else:
            status = "amended"  # changed active edge goes back to review
        return {
            "event_id": "x_" + _h(eid, run_id, et, ",".join(ev_ids)),
            "edge_id": eid,
            "run_id": run_id,
            "observed_at": ts,
            "event_type": et,
            "subject_id": s,
            "object_id": o,
            "rel_type": rt,
            "category": vocab.REL_TYPES[rt],
            "agreement_key": r.get("agreement_key"),
            "status": status,
            "materiality": mat,
            "weight": float(r.get("weight", vocab.MATERIALITY[mat])),
            "dependent_party": dp,
            "exposure_pct": None if exp is None else float(exp),
            "best_tier": tiers[0] if tiers else None,
            "evidence_ids": sorted(set(ev_ids) | set(prior.get("evidence_ids") or [] if prior else [])),
            "effective_date": _date(r.get("effective_date")) or (prior or {}).get("effective_date"),
            "end_date": _date(r.get("end_date")),
            "trade_relevance": tr,
            "note": r.get("note"),
        }

    @staticmethod
    def _basket_row(r: dict[str, Any], run_id: str, ts: dt.datetime, known: set[str]) -> dict[str, Any]:
        if r.get("anchor_id") not in known:
            raise ValidationError(f"basket anchor {r.get('anchor_id')!r} unknown")
        bt = r.get("basket_type")
        if bt not in vocab.BASKET_TYPES:
            raise ValidationError(f"bad basket_type {bt!r}")
        members = r.get("members") or []
        if not 3 <= len(members) <= 8:
            raise ValidationError("baskets need 3-8 members")
        for m in members:
            if m["entity_id"] not in known:
                raise ValidationError(f"basket member {m['entity_id']!r} unknown")
        for f in ("thesis", "catalyst", "hedge_leg", "invalidation"):
            if not r.get(f):
                raise ValidationError(f"basket needs {f}")
        w = r.get("weighting", "equal")
        st = r.get("status", "idea")
        if w not in vocab.WEIGHTING or st not in vocab.BASKET_STATUS:
            raise ValidationError("bad weighting or status")
        return {
            "basket_id": r.get("basket_id") or "b_" + _h(r["anchor_id"], bt, r["thesis"]),
            "run_id": run_id,
            "recorded_at": ts,
            "anchor_id": r["anchor_id"],
            "basket_type": bt,
            "members": [
                {
                    "entity_id": m["entity_id"],
                    "hop": int(m.get("hop", 1)),
                    "path_score": m.get("path_score"),
                    "weight": m.get("weight"),
                }
                for m in members
            ],
            "thesis": r["thesis"],
            "catalyst": r["catalyst"],
            "hedge_leg": r["hedge_leg"],
            "invalidation": r["invalidation"],
            "weighting": w,
            "status": st,
        }


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]
