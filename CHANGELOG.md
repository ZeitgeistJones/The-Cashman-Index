# Changelog

All notable changes to the Front Office Index are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/). Dates are UTC commit days on `claude/cashman-index-mvp-m7bsps`.

## [Unreleased]

### Fixed

- Trade ledger closed-market: symmetric horizons + `reconcile_trades` player-movement
  attribution (multi-team residual ~+32 / 0.7%; harness 9/9)
- Non-trade moves no longer duplicate on Stats API row id
- Composite scoring treats missing components as null (drop + renormalize), not fake 0.0
- Payroll thrift is league-relative (wins/$100M ÷ that year’s league mean)
- Yearly/exit tenure-shrink like GM board; as-of WAR clips when BRef loads
- Scored outputs pin `as_of` from `weights.json`; windows `[2006, 2025]` everywhere
- Exit ledger “Exit-pool index”; GmTable shrink toward 0

### Changed

- GM views: Career / After this year / Season grades (one question per tab; no nested resume-vs-moves toggle)
- About: league-relative thrift, winning-block ~0.41, player-movement trades, Every season tab
- “Thrift vs era” → “Thrift vs league” (ERA collision)
- Lens UI states winning components overlap — ranks barely move between lenses
- Every season: clearer “too young to grade” filter, `#rank/N` + mid-season hint, mobile spark
- `check_invariants.py` in CI; audit doc post-fix status table

### Known / deferred

- Full contemporaneous vintage WAR for every historical resume beyond clip path
- Call-ups vs acquisitions (disclosed, not reclassified)
- Collapse winning block / payroll-weight thesis (owner calls; disclosed only)

### Added

- Favicon, Apple icon, Open Graph card, manifest, and header mark (navy diamond)
- Every season tab — all executive-seasons in one pool (`b4c0752`)
- Success-lens toggles (Balanced / October / Value / Builder) (`f936865`)
- Start-here strip, construction grades, post-verify commit rule

---

## Earlier (pre-changelog)

Notable landings before this file existed (2026-08-02–03): Front Office Index MVP UI, mobile polish, 2020 payroll pacing + About methodology, scheduled ranking refreshes.
