import datetime as dt
import os

import pytest

from assoc_ontology import graph
from assoc_ontology.store import Store, ValidationError, edge_id_for, evidence_id_for

UTC = dt.UTC


def ent(t, roles=("anchor",), **kw):
    return {"kind": "entity", "ticker": t, "legal_name": t, "roles": list(roles), "universe_source": "manual", **kw}


def evid(url, tier="A"):
    return {"kind": "evidence", "url": url, "tier": tier, "source_form": "10-K"}


def edge(s, rt, o, url, **kw):
    return {
        "kind": "edge",
        "subject_id": f"tkr:{s}",
        "object_id": f"tkr:{o}",
        "rel_type": rt,
        "evidence_ids": [evidence_id_for(url)],
        **kw,
    }


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "data")
    s.ingest(
        [
            ent("META"),
            ent("SUP"),
            ent("SUB2"),
            ent("BANK", roles=["capital_provider"]),
            evid("https://sec/a"),
            evid("https://sec/b"),
            evid("https://news/c", "C"),
            edge(
                "SUP",
                "SUPPLIES_COMPONENT_TO",
                "META",
                "https://sec/a",
                materiality="high",
                dependent_party="subject",
                exposure_pct=0.3,
            ),
            edge("SUB2", "SUPPLIES_COMPONENT_TO", "SUP", "https://sec/b", materiality="medium"),
            edge("BANK", "LENDER_TO", "META", "https://news/c"),
        ],
        trigger="seed",
        ts=dt.datetime(2026, 1, 1, tzinfo=UTC),
    )
    return s


def test_new_edges_are_proposed_never_active(store):
    assert {e["status"] for e in store.current_edges().values()} == {"proposed"}


def test_partitions_are_append_only(store, tmp_path):
    n = len(list((tmp_path / "data").rglob("*.parquet")))
    eid = edge_id_for("tkr:SUP", "SUPPLIES_COMPONENT_TO", "tkr:META")
    store.review(eid, "accepted")
    assert len(list((tmp_path / "data").rglob("*.parquet"))) == n + 2  # runs + edge_events
    assert store.current_edges()[eid]["status"] == "active"


def test_tier_c_cannot_be_accepted(store):
    with pytest.raises(ValidationError):
        store.review(edge_id_for("tkr:BANK", "LENDER_TO", "tkr:META"), "accepted")


def test_runs_cannot_write_review_events(store):
    with pytest.raises(ValidationError):
        store.ingest(
            [edge("SUP", "SUPPLIES_COMPONENT_TO", "META", "https://sec/a", event_type="accepted")], trigger="on_demand"
        )


def test_unknown_entity_and_missing_evidence_rejected(store):
    with pytest.raises(ValidationError):
        store.ingest([evid("https://sec/z"), edge("NOPE", "LENDER_TO", "META", "https://sec/z")], trigger="on_demand")
    with pytest.raises(ValidationError):
        store.ingest(
            [{"kind": "edge", "subject_id": "tkr:SUP", "object_id": "tkr:META", "rel_type": "LENDER_TO"}],
            trigger="on_demand",
        )


def test_amending_active_edge_returns_it_to_review(store):
    eid = edge_id_for("tkr:SUP", "SUPPLIES_COMPONENT_TO", "tkr:META")
    store.review(eid, "accepted")
    store.ingest(
        [
            evid("https://sec/a2"),
            edge("SUP", "SUPPLIES_COMPONENT_TO", "META", "https://sec/a2", event_type="weakened", exposure_pct=0.1),
        ],
        trigger="on_demand",
    )
    cur = store.current_edges()[eid]
    assert cur["status"] == "amended" and cur["exposure_pct"] == 0.1 and len(cur["evidence_ids"]) == 2


def test_paths_and_scores(store):
    a = edge_id_for("tkr:SUP", "SUPPLIES_COMPONENT_TO", "tkr:META")
    b = edge_id_for("tkr:SUB2", "SUPPLIES_COMPONENT_TO", "tkr:SUP")
    assert graph.paths(store.current_edges(), "tkr:META") == []  # nothing active yet
    store.review(a, "accepted")
    store.review(b, "accepted")
    res = {r["entity_id"]: r for r in graph.paths(store.current_edges(), "tkr:META")}
    assert res["tkr:SUP"]["hop"] == 1 and res["tkr:SUP"]["path_score"] == pytest.approx(0.9)
    assert res["tkr:SUB2"]["hop"] == 2 and res["tkr:SUB2"]["path_score"] == pytest.approx(0.5 * 0.9 * 0.6)
    assert all(r["accountable"] for r in res.values())
    spec = {r["entity_id"]: r for r in graph.paths(store.current_edges(), "tkr:META", include_proposed=True)}
    assert spec["tkr:BANK"]["accountable"] is False


def test_stale(store):
    eid = edge_id_for("tkr:SUP", "SUPPLIES_COMPONENT_TO", "tkr:META")
    store.review(eid, "accepted")
    assert [e["edge_id"] for e in graph.stale(store.current_edges(), dt.datetime(2027, 3, 1, tzinfo=UTC))] == [eid]


def test_basket_rules(store):
    with pytest.raises(ValidationError):
        store.ingest(
            [
                {
                    "kind": "basket",
                    "anchor_id": "tkr:META",
                    "basket_type": "upstream_suppliers",
                    "members": [{"entity_id": "tkr:SUP"}],
                    "thesis": "t",
                    "catalyst": "c",
                    "hedge_leg": "h",
                    "invalidation": "i",
                }
            ],
            trigger="on_demand",
        )
    store.ingest(
        [
            {
                "kind": "basket",
                "anchor_id": "tkr:META",
                "basket_type": "upstream_suppliers",
                "members": [{"entity_id": f"tkr:{t}", "hop": 1} for t in ("SUP", "SUB2", "BANK")],
                "thesis": "t",
                "catalyst": "c",
                "hedge_leg": "SOXX",
                "invalidation": "i",
            }
        ],
        trigger="on_demand",
    )
    assert len(store.rows("baskets")) == 1


@pytest.mark.skipif(not os.environ.get("ASSOC_PG_DSN"), reason="no Postgres")
def test_postgres_export(store):
    from assoc_ontology.pg import export

    counts = export(store, os.environ["ASSOC_PG_DSN"], schema="assoc_test")
    assert counts["edges_current"] == 3 and counts["entities"] == 4
