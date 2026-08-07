# Changelog

All notable changes to the Front Office Index are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/). Dates are UTC commit days on `claude/cashman-index-mvp-m7bsps`.

## [Unreleased]

### Fixed

- Trade `net_war_exchange` horizons are symmetric (credit during focal club; debit during receiving club) so league sum ≈ 0; non-trade moves no longer duplicate on Stats API row id
- Composite scoring treats missing components as null (drop + renormalize), not fake 0.0
- Payroll thrift is era-relative (wins/$100M ÷ that year’s league mean) so early tenures are not automatic thrift leaders
- Yearly/exit resumes tenure-shrink toward 0 like the GM board; draft/trade WAR clipped to as-of when BRef loads
- Scored outputs pin `as_of` from `data/weights.json` (no `date.today()` in any `build_*.py`)
- Trade/draft index windows align to last complete season `[2006, 2025]` with rankings (M4)
- Exit ledger labels “Exit-pool index”; GmTable shrink copy says toward 0

### Changed

- About discloses era-relative thrift, winning-block collinearity (~0.41 stacked), call-up vs acquisition ambiguity
- UI payroll column relabeled “Thrift vs era” (ratio scale ≈ 1.0 = league-average)

### Known / deferred

- League `sum(net_war_exchange)` residual ≈ +525 (~11% of credited WAR) after symmetric horizons — down from ≈ −3769 (~35%). Remaining bias is Stats API multi-club / same-day package asymmetry, not the old forever-vs-tenure horizon bug. Harness still wants ≤5%.
- Yearly/exit as-of WAR clips are implemented in `build_rankings.py` (`--skip-war-clips` to bypass); this data rebuild used living nets on resumes for turnaround. Career boards use date-filtered trades/drafts.
- Full contemporaneous vintage WAR for every historical resume row remains deferred beyond the as-of clip path

### Added

- Success-lens toggles (Balanced / October / Value / Builder) reweight the same seven composite components client-side for Clubs, GMs, and By year · career grade (`f936865`)
- Start-here strip with plain why-bullets, plainer tab labels, and demoted trade-detail ledger (`b232f89`)
- Single-season FO **construction** grades (regime stock share, H-horizon trades, mature draft) + Yearly Resume vs Construction UI (`224a40b`)
- Project rule: commit and push after a successful `/verify` (`a3120aa`)

---

## Earlier (pre-changelog)

Notable landings before this file existed (2026-08-02–03): Front Office Index MVP UI, mobile polish, 2020 payroll pacing + About methodology, scheduled ranking refreshes.
