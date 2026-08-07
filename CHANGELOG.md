# Changelog

All notable changes to the Front Office Index are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/). Dates are UTC commit days on `claude/cashman-index-mvp-m7bsps`.

## [Unreleased]

### Added

- Success-lens toggles (Balanced / October / Value / Builder) reweight the same seven composite components client-side for Clubs, GMs, and By year · career grade (`f936865`)
- Start-here strip with plain why-bullets, plainer tab labels, and demoted trade-detail ledger (`b232f89`)
- Single-season FO **construction** grades (regime stock share, H-horizon trades, mature draft) + Yearly Resume vs Construction UI (`224a40b`)
- Project rule: commit and push after a successful `/verify` (`a3120aa`)

### Fixed

- Season construction: empty trade windows show `—` (not fake zeros), drop missing components from the index, default UI to latest fully scored year, clamp own-stock % (`ad5483a`)
- Point-in-time resumes no longer use full-career draft/trade grades; incomplete championship year excluded from franchise/GM boards; payroll efficiency ignores seasons without payroll; Yearly exits table rendered (`98bcc49`)

### Changed

- About page documents success lenses, season construction, and intentional omissions
- Yearly resume leaderboard exports pennants / draft / trade fields so lenses can re-score

---

## Earlier (pre-changelog)

Notable landings before this file existed (2026-08-02–03): Front Office Index MVP UI, mobile polish, 2020 payroll pacing + About methodology, scheduled ranking refreshes.
