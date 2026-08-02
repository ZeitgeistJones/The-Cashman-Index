# Talent acquisition index (draft → trades → other pipelines)

A front office’s job is not only standings — it is acquiring and reallocating
talent under money and roster constraints. This doc is the full target. We ship in
phases; later phases only start when earlier ones produce trustworthy numbers.

## Core idea

Every acquisition channel produces **assets**. Score assets in the same units
where possible:

- **On-field value** after acquisition (WAR for the acquiring club, or for the
  next club if traded away — net exchange).
- **Money context** — salary absorbed, salary dumped, cash in deal, remaining
  guarantee when known.
- **Opportunity cost** — draft slot expected value, intl bonus pool spent,
  Rule 5 / waiver claim scarcity.

Do **not** treat raw “number of prospects acquired” as skill.

---

## Implementation status

1. **Phase A — DONE** — draft VOS live (franchise-tenure WAR, all clubs).
2. **Phase B — DONE** — league trades scored club-perspective; `trade_net_rate`
   in composite; trade ledger + trade index UI.
3. **Phase C — DONE (channels)** — FA / waiver / Rule 5 / trade channel WAR for
   all 30 clubs via `build_league_acquisition.py`. Intl amateur pools still deferred.
4. Phase D development/call-ups — only if still needed after A–C.

Product name: **Front Office Index** (league-wide; no single-club thesis).
