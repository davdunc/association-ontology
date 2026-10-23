"""Controlled vocabulary for the company association ontology (spec §5–7)."""

from __future__ import annotations

# relationship type -> category
REL_TYPES: dict[str, str] = {
    "SUPPLIES_COMPONENT_TO": "supply_chain",
    "SUPPLIES_CAPACITY_TO": "supply_chain",
    "SUPPLIES_RESOURCE_TO": "supply_chain",
    "MANUFACTURES_FOR": "supply_chain",
    "LICENSES_IP_TO": "supply_chain",
    "MAJOR_CUSTOMER_OF": "demand",
    "LENDER_TO": "capital",
    "ADMIN_AGENT_FOR": "capital",
    "UNDERWRITER_FOR": "capital",
    "TRUSTEE_FOR": "capital",
    "LESSOR_TO": "capital",
    "COUNTERPARTY_TO": "capital",
    "GUARANTOR_OF": "capital",
    "SUBSIDIARY_OF": "ownership",
    "HOLDS_STAKE_IN": "ownership",
    "ACQUIRING": "ownership",
    "JOINT_VENTURE_WITH": "partnership",
    "STRATEGIC_PARTNER_OF": "partnership",
    "OFFTAKE_WITH": "partnership",
    "SHARES_DIRECTOR_WITH": "governance",
    "RELATED_PARTY_OF": "governance",
    "AUDITOR_OF": "governance",
    "COMPETES_WITH": "context",
    "CONSTITUENT_OF": "context",
    "CO_MOVES_WITH": "context",
}

ACCOUNTABLE_CATEGORIES = frozenset(c for c in REL_TYPES.values() if c != "context")

ENTITY_TYPES = frozenset({"public_company", "private_company", "etf_fund", "government_agency", "other"})
ROLES = frozenset(
    {
        "anchor",
        "supplier",
        "customer",
        "capital_provider",
        "financial_institution",
        "partner",
        "competitor",
        "hedge_instrument",
    }
)
UNIVERSE_SOURCES = frozenset({"daily_game_plan", "manual", "discovered"})

TIERS = frozenset({"A", "B", "C", "D"})  # A filing, B company release, C reputable press, D inferred
ACCOUNTABLE_TIERS = frozenset({"A", "B"})

STATUSES = frozenset({"proposed", "active", "amended", "terminated", "rejected"})
MATERIALITY = {"high": 0.9, "medium": 0.6, "low": 0.3, "unknown": 0.2}
DEPENDENT_PARTY = frozenset({"subject", "object", "both", "unknown"})

# Events written by automated runs. 'accepted'/'rejected' are only written by `review`.
DETECTION_EVENTS = frozenset(
    {"new", "amended", "strengthened", "weakened", "terminated", "reclassified", "reconfirmed"}
)
REVIEW_EVENTS = frozenset({"accepted", "rejected"})
EVENT_TYPES = DETECTION_EVENTS | REVIEW_EVENTS

TRADE_RELEVANCE = frozenset({"actionable", "watch", "background"})
TRIGGERS = frozenset({"scheduled", "on_demand", "seed", "review"})

BASKET_TYPES = frozenset(
    {"upstream_suppliers", "capital_providers", "downstream_customers", "ecosystem_ownership", "pair_hedged"}
)
BASKET_STATUS = frozenset({"idea", "research", "validated", "retired"})
WEIGHTING = frozenset({"equal", "exposure_weighted", "inverse_volatility"})

HOP_DECAY = 0.5  # experimental (spec §8)
STALE_DAYS = 400  # experimental (spec §7)
