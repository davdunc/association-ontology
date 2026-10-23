# Company Association Ontology — Spec v0.2

> Status: Draft v0.1 · Owner: David Duncan · Created 2026-10-23 · v0.2 2026-10-23. Goal: model the accountable associations around the companies in my daily reviews so I can trade 2nd- and 3rd-order baskets instead of single names. This spec defines intent; thresholds below are experimental until validated against recorded sessions and Falcon trade outcomes.
## 1. Purpose
- Represent every company I review as a node, and every disclosed, enforceable relationship around it as a typed, evidenced edge.
- Detect changes in those relationships on a schedule (new contracts, terminated agreements, new financing, ownership changes) and record them in a change log.
- Turn an anchor event (e.g. a capex raise at META, a bond deal at AMZN) into ranked 1st/2nd/3rd-hop baskets with an explicit thesis, hedge leg, and catalyst.
- Feed baskets into TradeKit / Falcon as hypotheses to be evaluated, not as signals to be executed.
## 2. Scope and universe
- Anchors: every single-name `Thesis Ticker` in the Daily Game Plan database, plus manually added anchors (META, AMZN to start).
- ETFs and index products (SPY, SOXL, XLE, IBIT, UVXY, IGV) are modeled as instruments, used as hedge legs and as `CONSTITUENT_OF` targets — not as companies.
- Counterparties discovered through edges (suppliers, lenders, partners) are added as nodes automatically with `Universe Source = Discovered`.
- Non-goals: no automated order placement; no promotion of an edge to Active without evidence; no use of unverifiable rumor.
## 3. Design principles
1. Accountable over associative. An edge must be backed by a document in which a party is accountable for the claim (a filing, a contract exhibit, a company release). Statistical co-movement and news co-mentions are discovery hints only.
2. Direction and dependency matter. "X supplies META" says little until we know who depends on whom. Each edge records the dependent party and, when disclosed, the exposure percentage.
3. Time is first-class. Every edge has effective, first-seen, and last-confirmed dates. Changes create log entries; edges are never silently overwritten.
4. Unknowns stay unknown. Missing exposure or materiality is recorded as Unknown, never estimated without labeling it as an estimate.
5. Spec separate from implementation. This page is the canonical definition; the scheduled review and any TradeKit module implement it.
## 4. Ontology classes
| Class | Description | Key attributes |
|---|---|---|
| Entity | A company, fund, government body, or other legal party | Ticker, legal name, CIK, LEI, entity type, role tags, sector |
| Instrument | A tradable product that is not an operating company (ETF, index) | Ticker, underlying exposure |
| Association (edge) | A typed, directed relationship Subject → Object | Type, category, evidence tier, status, materiality, weight, dependent party, exposure %, dates, evidence URL |
| Evidence | The document supporting an edge | URL, form type / item, filed date, tier |
| Change Event | A detected change to an edge | Change type, detected date, evidence, trade relevance, review status |
| Basket | A tradable group derived from an anchor's graph | Anchor, members, hop levels, type, thesis, hedge leg, weighting, catalysts |
## 5. Relationship types
Edges read Subject → Object. Inverses (e.g. `CUSTOMER_OF`) are derived, not stored separately.
| Category | Type | Meaning | Typical evidence |
|---|---|---|---|
| Supply chain | `SUPPLIES_COMPONENT_TO` | Subject sells chips, hardware, or parts used by Object | Supplier 10-K customer disclosure, 8-K Item 1.01 |
| Supply chain | `SUPPLIES_CAPACITY_TO` | Compute, cloud, data-center, or manufacturing capacity | Material contract exhibit, company release |
| Supply chain | `SUPPLIES_RESOURCE_TO` | Power, fuel, water, minerals, land | Offtake / PPA agreements, 8-K |
| Supply chain | `MANUFACTURES_FOR` | Contract manufacturing or foundry | 10-K, Exhibit 10 |
| Supply chain | `LICENSES_IP_TO` | Patent, software, or technology license the Object depends on | Exhibit 10 |
| Demand | `MAJOR_CUSTOMER_OF` | Object discloses Subject as ≥10% of revenue | 10-K / 10-Q concentration note |
| Capital | `LENDER_TO` | Subject lends to Object (term loan, revolver, private credit) | 8-K Item 2.03, credit agreement exhibit |
| Capital | `ADMIN_AGENT_FOR` | Administrative / collateral agent on a credit facility | Credit agreement |
| Capital | `UNDERWRITER_FOR` | Bookrunner or underwriter on a debt or equity offering | Prospectus / prospectus supplement |
| Capital | `TRUSTEE_FOR` | Indenture trustee on notes | Indenture exhibit |
| Capital | `LESSOR_TO` | Lessor of material property, data centers, or equipment | 10-K lease note, Exhibit 10 |
| Capital | `COUNTERPARTY_TO` | Derivative, hedge, or structured-financing counterparty | 10-K, 8-K |
| Capital | `GUARANTOR_OF` | Guarantees another party's obligation | Indenture, 8-K Item 2.03 |
| Ownership | `SUBSIDIARY_OF` | Controlled entity | Exhibit 21 |
| Ownership | `HOLDS_STAKE_IN` | ≥5% beneficial owner or strategic equity investor | Schedule 13D / 13G, company release |
| Ownership | `ACQUIRING` | Pending or completed acquisition | 8-K Items 1.01 / 2.01 |
| Partnership | `JOINT_VENTURE_WITH` | Shared-ownership venture | 8-K, 10-K |
| Partnership | `STRATEGIC_PARTNER_OF` | Co-development, distribution, or commercial alliance | Company release, 8-K Item 1.01 |
| Partnership | `OFFTAKE_WITH` | Long-term purchase commitment | 8-K, Exhibit 10 |
| Governance | `SHARES_DIRECTOR_WITH` | Board interlock | Proxy (DEF 14A) |
| Governance | `RELATED_PARTY_OF` | Related-person transaction | Proxy, 10-K |
| Governance | `AUDITOR_OF` | Certifying accountant | 10-K, 8-K Item 4.01 |
| Context (non-accountable) | `COMPETES_WITH` | Named competitor | 10-K competition section |
| Context (non-accountable) | `CONSTITUENT_OF` | Member of an ETF or index | Fund holdings |
| Context (non-accountable) | `CO_MOVES_WITH` | Statistical or news co-mention | Massive Related Companies API |
## 6. Evidence tiers
| Tier | Source | Can create Active edge? |
|---|---|---|
| A — Filing | SEC filing by either party (10-K, 10-Q, 8-K, exhibits, prospectus, 13D/G, proxy) | Yes |
| B — Company release | Press release or IR page from a party to the relationship | Yes, flagged for filing confirmation |
| C — Reputable press | Named, reputable outlet reporting the relationship | No — Proposed only |
| D — Inferred / statistical | Co-movement, co-mention, analyst speculation | No — discovery hint only |
Grounding references:
- [Form 8-K](https://www.sec.gov/info/edgar/forms/form8-k.pdf) Item 1.01 requires disclosure of the parties to a material definitive agreement not made in the ordinary course of business; Item 1.02 covers terminations; Item 2.03 covers new direct financial obligations; Item 2.04 covers triggering events that accelerate or increase them.
- [Regulation S-K Item 601(b)(10)](https://www.ecfr.gov/current/title-17/chapter-II/part-229/subpart-229.600/section-229.601) requires filing material contracts, including contracts on which the registrant's business is substantially dependent (e.g. supplying the major part of its requirements of goods, services, or raw materials).
- [ASC 280-10-50-42](https://dart.deloitte.com/USDART/home/codification/presentation/asc280-10/roadmap-segment-reporting/chapter-5-entity-wide-disclosures/5-7-information-about-major-customers) requires disclosure when a single customer is 10% or more of revenue (identity not always required — record as Unknown customer when unnamed).
- [EDGAR APIs on data.sec.gov](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) provide per-company submission history and XBRL data without an API key.
- [Massive Related Tickers](https://massive.com/docs/rest/stocks/tickers/related-tickers) (`/v1/related-companies/{ticker}`) returns related tickers based on news coverage and returns data — Tier D only.
## 7. Edge attributes
| Attribute | Rule |
|---|---|
| Weight (0–1) | Materiality score. Default: High = 0.9, Medium = 0.6, Low = 0.3, Unknown = 0.2. Experimental. |
| Dependent Party | Subject, Object, Both, or Unknown — whose economics move most if the relationship changes. |
| Exposure % | Disclosed share of the dependent party's revenue or cost tied to the relationship. Blank if not disclosed. |
| Status | Proposed → Active → Amended / Terminated; or Rejected. |
| Dates | Effective (per document), First Seen (by the review), Last Confirmed (latest document still supporting it). |
| Staleness | Active edge not reconfirmed in 400 days → flag for review (covers one annual-report cycle plus slack). |
## 8. 2nd- and 3rd-order propagation
- Hop 1: direct counterparties of the anchor. Hop 2: counterparties of those counterparties. Hop 3: one further step. Stop at hop 3.
- Path score = product of edge weights × hop decay, with decay λ = 0.5 per additional hop (experimental):
```
S(path) = λ^(k-1) × Π w_i      (k = hop count, λ = 0.5)
```
- Only Tier A/B Active edges contribute to accountable baskets. Paths containing a Tier C/D edge are shown separately as Speculative.
- Sensitivity runs toward the dependent party. A supplier with high exposure to the anchor is a high-sensitivity member; an anchor's sensitivity to a small supplier is low.
- Category-aware chains: Capital chains (anchor → lender → lender's funding / credit-spread exposure) are evaluated separately from Supply chains (anchor capex → component supplier → that supplier's suppliers).
## 9. Basket construction
| Basket type | Built from | Typical anchor event |
|---|---|---|
| Upstream suppliers | Supply-chain edges where the supplier is dependent | Anchor capex guidance change, product launch, order cut |
| Capital providers | Lender / underwriter / agent / lessor edges | Large debt raise, refinancing, credit event |
| Downstream customers | `MAJOR_CUSTOMER_OF` and capacity edges | Anchor pricing or capacity change |
| Ecosystem / ownership | Stakes, JVs, partners | M&A, stake changes, partnership terms |
| Pair / hedged | Any basket vs. anchor or sector ETF | Isolate the relationship from market beta |
Rules (experimental):
- 3–8 members; each must pass liquidity filters already used by TradeKit screening (price, average volume).
- Weighting: Equal by default; Exposure-weighted when exposure % is disclosed for most members; Inverse-volatility as alternative.
- Each basket records a thesis, the anchor catalyst, the hedge leg, and an invalidation condition.
- Baskets are hypotheses logged for out-of-sample evaluation in TradeKit / Falcon before any sizing rule is trusted.
## 10. Review triggers and procedure
Cadence: monthly sweep (first Sunday of the month, 17:00 America/Chicago) plus on-demand runs. An on-demand run is started when I report a new association or a news catalyst for a company (ticker, optional URL/note); it is scoped to that company and its hop-1 counterparties. No polling more often than monthly.

Each run:
1. Universe — entities with `in_daily_review = true`, plus new single-name `Thesis Ticker` values from the Notion Daily Game Plan since the previous run (monthly) or the named ticker (on-demand). Add missing entities; fill missing CIKs.
2. Collect filings since the previous run for each anchor and each active counterparty (first monthly run: last 12 months of 10-K/10-Q, last 90 days otherwise): 8-K Items 1.01, 1.02, 2.01, 2.03, 2.04, 5.01, 8.01; 10-K/10-Q customer concentration, Exhibit 10, Exhibit 21; prospectus filings (underwriters); 13D/13G; proxy statements (related parties, interlocks).
3. Search counterparties' filings and company releases naming the anchor (main source of hop-2 supplier dependence). Massive Related Companies only as tier D candidates.
4. Write a JSONL batch (see README) and `assoc-ontology ingest` it. The store enforces: new edges are `proposed`; runs cannot write `accepted`; only `review` can make an edge `active`, and only with tier A/B evidence; a changed active edge returns to `amended`.
5. Recompute hop-2/hop-3 paths for affected anchors (`assoc-ontology paths`), flag stale edges (`assoc-ontology stale`), propose baskets (status `idea`) only with ≥3 liquid members.
6. Commit the new Parquet partitions; report changes ranked by trade relevance, impacted baskets, stale edges, and every failed lookup (a failed lookup is a gap, not proof of no change).

## 11. Storage
- Canonical store: append-only Parquet (zstd), one partition per run: `data/<table>/run_id=<run_id>/part-0.parquet`. Files are never rewritten; review decisions are new rows. Git history is the audit trail.
- Tables: `runs`, `entities`, `evidence`, `edge_events` (event-sourced edges; current state = latest event per `edge_id`), `baskets` (members as list of structs).
- Secondary store: Postgres mirror via `assoc-ontology export-postgres --dsn ...` (full refresh in one transaction, plus a materialized `edges_current` table). Parquet always wins on conflict.
- Any Parquet reader (DuckDB, Polars, pandas, Spark) can query the files directly; none is required.
- IDs: entities `tkr:<TICKER>`, `cik:<10-digit>`, or `name:<slug>`; edges `e_` + hash(subject, rel_type, object, agreement_key); evidence `ev_` + hash(url, accession_no, item).
- Notion holds only the human-readable spec; it is not a datastore.

## 12. Acceptance criteria
- [x] Every active edge has tier A or B evidence (enforced by `review`).
- [x] No automated run can make an edge active (enforced by `ingest`).
- [x] Every detected change is one `edge_events` row linked to its run and evidence.
- [x] Partitions are append-only; review never rewrites history.
- [x] Baskets require 3–8 known members, thesis, catalyst, hedge leg, invalidation.
- [x] Paths report hop, score, and whether every edge is accountable.
- [ ] Every Daily Game Plan single-name anchor exists as an entity within one run of first appearing.
- [ ] Run reports list lookup failures explicitly (stored in `runs.failures`).
- [ ] Postgres mirror verified in CI against Postgres 16.

## 13. Open questions
- Whether a paid supply-chain dataset is worth adding for coverage beyond SEC disclosures.
- Weight and decay calibration against basket outcomes in TradeKit / Falcon.
- Whether TradeKit consumes this as a dependency or reads the Parquet directly.
- Foreign filers (20-F / 6-K) and private counterparties (e.g. private-credit lenders).
