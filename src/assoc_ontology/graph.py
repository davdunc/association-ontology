"""2nd/3rd-order propagation over current edges (spec §8)."""

from __future__ import annotations

import datetime as dt
from typing import Any

from . import vocab


def _usable(e: dict[str, Any], include_proposed: bool) -> bool:
    if e["status"] in ("terminated", "rejected"):
        return False
    if e["status"] == "active":
        return True
    return include_proposed


def _accountable(e: dict[str, Any]) -> bool:
    return (
        e["status"] == "active"
        and e.get("best_tier") in vocab.ACCOUNTABLE_TIERS
        and e["category"] in vocab.ACCOUNTABLE_CATEGORIES
    )


def paths(
    edges: dict[str, dict[str, Any]],
    anchor_id: str,
    max_hops: int = 3,
    include_proposed: bool = False,
    decay: float = vocab.HOP_DECAY,
) -> list[dict[str, Any]]:
    """Best simple path from anchor to every reachable entity, traversing edges in both directions.

    score = decay**(k-1) * prod(weights). `accountable` is True only if every edge is tier A/B and active.
    """
    adj: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for e in edges.values():
        if not _usable(e, include_proposed):
            continue
        adj.setdefault(e["subject_id"], []).append((e["object_id"], e))
        adj.setdefault(e["object_id"], []).append((e["subject_id"], e))

    best: dict[str, dict[str, Any]] = {}
    frontier: list[tuple[str, list[str], list[dict[str, Any]], float]] = [(anchor_id, [anchor_id], [], 1.0)]
    for hop in range(1, max_hops + 1):
        nxt = []
        for node, visited, via, prod in frontier:
            for other, e in adj.get(node, []):
                if other in visited:
                    continue
                p = prod * e["weight"]
                score = decay ** (hop - 1) * p
                chain = [*via, e]
                rec = {
                    "entity_id": other,
                    "hop": hop,
                    "path_score": round(score, 6),
                    "path": [*visited, other],
                    "edge_ids": [x["edge_id"] for x in chain],
                    "rel_types": [x["rel_type"] for x in chain],
                    "accountable": all(_accountable(x) for x in chain),
                    # sensitivity runs toward the dependent party of the first edge out of the anchor side
                    "dependent_party_last": e["dependent_party"],
                }
                cur = best.get(other)
                if cur is None or (rec["accountable"], score) > (cur["accountable"], cur["path_score"]):
                    best[other] = rec
                nxt.append((other, [*visited, other], chain, p))
        frontier = nxt
    return sorted(best.values(), key=lambda r: (not r["accountable"], r["hop"], -r["path_score"]))


def stale(
    edges: dict[str, dict[str, Any]], as_of: dt.datetime | None = None, days: int = vocab.STALE_DAYS
) -> list[dict[str, Any]]:
    as_of = as_of or dt.datetime.now(dt.UTC)
    cutoff = as_of - dt.timedelta(days=days)
    return [e for e in edges.values() if e["status"] == "active" and e["last_confirmed"] < cutoff]
