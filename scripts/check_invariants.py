#!/usr/bin/env python3
"""Independent invariant checks for the Front Office Index.

These are the pass/fail gates for the seven defects agreed in the joint math
audit at commit 70e1468 (two independent reviewers, all findings confirmed
arithmetically by both). Each check is a property the published numbers must
satisfy for the site's claims to be true — not a unit test of any particular
implementation, so it stays valid however the fixes are written.

Deliberately standalone: stdlib only, read-only, no imports from scripts/, and
not wired into CI. It reads data/*.json the way a skeptical reader would, so it
cannot pass by agreeing with a bug in the code that produced them.

    python scripts/check_invariants.py            # all checks
    python scripts/check_invariants.py --baseline # record current values

Exit code is the number of failures. Wire this into ci.yml once the fixes land.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics as st
from collections import Counter
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
SCRIPTS = REPO / "scripts"

# Tolerances. Deliberately loose: these catch structural defects, not noise.
CLOSED_MARKET_TOL = 0.05   # |league net| as a share of WAR credited
SYMMETRY_TOL = 1.10        # charged / credited
MISSING_Z_TOL = 0.25       # |z| a missing component may occupy
ERA_CORR_TOL = 0.20        # |corr(tenure era, payroll efficiency)|

results: list[tuple[str, bool | None, str]] = []


def load(name: str) -> Any:
    path = DATA / name
    if not path.exists():
        return None
    return json.loads(path.read_text())


def rows_of(blob: Any, *keys: str) -> list[dict]:
    if isinstance(blob, list):
        return blob
    if isinstance(blob, dict):
        for key in keys:
            if isinstance(blob.get(key), list):
                return blob[key]
    return []


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 3:
        return float("nan")
    mx, my = st.fmean(xs), st.fmean(ys)
    vx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    vy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if vx * vy == 0:
        return float("nan")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (vx * vy)


def check(name: str, fn: Callable[[], tuple[bool | None, str]]) -> None:
    try:
        ok, detail = fn()
    except Exception as exc:  # a crashing check is a failing check
        ok, detail = False, f"check raised {type(exc).__name__}: {exc}"
    results.append((name, ok, detail))


# ---------------------------------------------------------------------------
# 1-2. Trade accounting must balance across a closed market
# ---------------------------------------------------------------------------


def closed_market() -> tuple[bool | None, str]:
    """Every trade has two sides, so league-wide net WAR must be ~zero.

    It currently is not, because acquired WAR is counted only while the player
    stays with the acquiring club while departing WAR is counted everywhere,
    forever. That asymmetry makes all 30 clubs look like losing traders.
    """
    league = rows_of(load("league_moves.json"), "moves")
    if not league:
        return None, "data/league_moves.json not present"
    nets = [m["net_war_exchange"] for m in league if m.get("net_war_exchange") is not None]
    if not nets:
        return None, "no net_war_exchange values"
    credited = sum(m.get("war_acquired") or 0.0 for m in league)
    total = sum(nets)
    share = abs(total) / credited if credited else float("inf")
    return (
        share <= CLOSED_MARKET_TOL,
        f"sum={total:,.1f} over n={len(nets)} ({share:.0%} of {credited:,.0f} credited; "
        f"tolerance {CLOSED_MARKET_TOL:.0%})",
    )


def trade_symmetry() -> tuple[bool | None, str]:
    """WAR charged to sellers must roughly equal WAR credited to buyers."""
    league = rows_of(load("league_moves.json"), "moves")
    if not league:
        return None, "data/league_moves.json not present"
    credited = sum(m.get("war_acquired") or 0.0 for m in league)
    charged = sum(m.get("war_sent_away") or 0.0 for m in league)
    if credited <= 0:
        return False, "no WAR credited at all"
    ratio = charged / credited
    return (
        ratio <= SYMMETRY_TOL,
        f"charged {charged:,.0f} / credited {credited:,.0f} = {ratio:.2f}x "
        f"(tolerance {SYMMETRY_TOL:.2f}x)",
    )


# ---------------------------------------------------------------------------
# 3. A missing component must not score as an average-or-better one
# ---------------------------------------------------------------------------


def missing_is_not_zero() -> tuple[bool | None, str]:
    """An absent trade or draft book must not land above the peer mean.

    Nulls coerced to 0.0 enter the z-population as real zeros. Because most GMs
    grade negative on trades, 0.0 then reads as comfortably above average, so
    knowing nothing about a GM beats having a mediocre record.
    """
    gms = rows_of(load("gm_index.json"), "rows", "gms", "index")
    if not gms:
        return None, "data/gm_index.json not present"
    worst = None
    for field in ("trade_net_rate", "draft_vos"):
        vals = [r[field] for r in gms if isinstance(r.get(field), (int, float))]
        if len(vals) < 3:
            continue
        mean, sd = st.fmean(vals), st.pstdev(vals)  # pstdev matches scoring.zscore
        if sd == 0:
            continue
        z_zero = (0.0 - mean) / sd
        zeros = sum(1 for v in vals if v == 0.0)
        entry = (abs(z_zero), f"{field}: z(0.0)={z_zero:+.2f}, {zeros} exact zeros "
                              f"(mean={mean:+.2f} pstdev={sd:.2f} n={len(vals)})")
        if worst is None or entry[0] > worst[0]:
            worst = entry
    if worst is None:
        return None, "no scorable components found"
    return worst[0] <= MISSING_Z_TOL, f"{worst[1]}; tolerance |z|<={MISSING_Z_TOL}"


# ---------------------------------------------------------------------------
# 4. Payroll efficiency must measure skill, not the calendar
# ---------------------------------------------------------------------------


def era_neutrality() -> tuple[bool | None, str]:
    """Wins per dollar must not correlate with when a GM happened to work.

    A win cost roughly half as much in 2006 as in 2025, so raw wins/$100M ranks
    executives largely by era. This is the heaviest-weighted component.
    """
    gms = rows_of(load("gm_index.json"), "rows", "gms", "index")
    tenures = rows_of(load("gm_tenures.json"), "stints", "rows", "tenures")
    if not gms or not tenures:
        return None, "gm_index.json or gm_tenures.json not present"

    midpoints: dict[str, list[float]] = {}
    for stint in tenures:
        pid = stint.get("person_id")
        if not pid:
            continue
        try:
            start = int(str(stint.get("start") or "")[:4])
            end = int(str(stint.get("end") or "")[:4] or start)
        except ValueError:
            continue
        midpoints.setdefault(pid, []).append((start + end) / 2)

    pairs = [
        (st.fmean(midpoints[r["person_id"]]), float(r["payroll_efficiency"]))
        for r in gms
        if r.get("person_id") in midpoints
        and isinstance(r.get("payroll_efficiency"), (int, float))
        and r["payroll_efficiency"]
    ]
    if len(pairs) < 10:
        return None, f"only {len(pairs)} GMs with era and efficiency"
    r = pearson([p[0] for p in pairs], [p[1] for p in pairs])
    return (
        abs(r) <= ERA_CORR_TOL,
        f"corr(tenure midpoint, payroll_efficiency) = {r:+.2f} over n={len(pairs)} "
        f"(tolerance |r|<={ERA_CORR_TOL})",
    )


# ---------------------------------------------------------------------------
# 5-6. Reproducibility: one clock, one window
# ---------------------------------------------------------------------------


def pinned_as_of() -> tuple[bool | None, str]:
    """No builder that writes scored output may read the wall clock.

    A builder calling date.today() produces different numbers on every rerun,
    so two rebuilds of the same commit disagree.

    Only date.today() counts. A datetime.now() stamped into `generated_at` is a
    build timestamp, not a scoring input, and flagging it would bury the real
    offenders in noise.
    """
    offenders = []
    for path in sorted(SCRIPTS.glob("build_*.py")):
        for num, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#") or "date.today()" not in stripped:
                continue
            offenders.append(f"{path.name}:{num}  {stripped[:56]}")
    return not offenders, ("none" if not offenders
                           else f"{len(offenders)} scoring-relevant: " + " | ".join(offenders))


def consistent_window() -> tuple[bool | None, str]:
    """Every index must score over the same seasons.

    Trade rates divided by a different season count than the rankings they feed
    silently rescale one component against the others.
    """
    windows: dict[str, tuple] = {}
    for name in ("franchise_index", "gm_index", "trade_index", "draft_index",
                 "season_index", "yearly_index"):
        blob = load(f"{name}.json")
        if isinstance(blob, dict) and isinstance(blob.get("window"), list):
            windows[name] = tuple(blob["window"])
    if not windows:
        return None, "no index files carry a window"
    distinct = set(windows.values())
    detail = ", ".join(f"{k}={list(v)}" for k, v in sorted(windows.items()))
    return len(distinct) == 1, detail


def shrink_parity() -> tuple[bool | None, str]:
    """Career, yearly and exit boards must damp small samples identically.

    Shrinking only the career board means a two-season GM is penalised on one
    screen and not on another, from the same underlying record.
    """
    path = SCRIPTS / "build_rankings.py"
    if not path.exists():
        return None, "scripts/build_rankings.py not present"
    lines = path.read_text().splitlines()
    composites = [i + 1 for i, l in enumerate(lines) if "composite_scores(" in l and "def " not in l]
    shrinks = [i + 1 for i, l in enumerate(lines) if "tenure_shrink(" in l and "def " not in l]
    return (
        len(shrinks) >= len(composites),
        f"{len(composites)} composite_scores call sites {composites} vs "
        f"{len(shrinks)} tenure_shrink {shrinks}",
    )


# ---------------------------------------------------------------------------
# 7. Record hygiene
# ---------------------------------------------------------------------------


def no_duplicate_moves() -> tuple[bool | None, str]:
    """The same transaction must appear once.

    Non-trade rows key on the raw API row id, so one signing reported under
    several ids becomes several moves — and its WAR is credited several times.
    """
    moves = rows_of(load("moves.json"), "moves")
    if not moves:
        return None, "data/moves.json not present"
    key = lambda m: (
        m.get("move_date"),
        m.get("move_type"),
        tuple(sorted(p["name"] for p in m.get("players_acquired") or [])),
        tuple(sorted(p["name"] for p in m.get("players_sent_away") or [])),
    )
    counts = Counter(key(m) for m in moves)
    dups = {k: n for k, n in counts.items() if n > 1}
    redundant = sum(n - 1 for n in dups.values())
    worst = ""
    if dups:
        k, n = max(dups.items(), key=lambda kv: kv[1])
        who = (k[2] or k[3] or ("?",))[0]
        worst = f"; worst x{n} {k[0]} {who}"
    return not dups, f"{len(dups)} duplicate groups, {redundant} redundant of {len(moves)}{worst}"


def json_is_finite() -> tuple[bool | None, str]:
    """Published JSON must not contain NaN or Infinity.

    Both are invalid JSON. Python emits them happily; every strict parser,
    including the web build, rejects them.
    """
    bad = []
    for path in sorted(DATA.glob("*.json")):
        text = path.read_text()
        if re.search(r"\bNaN\b|\b-?Infinity\b", text):
            bad.append(path.name)
    return not bad, ("none" if not bad else "non-finite literals in: " + ", ".join(bad))


CHECKS = [
    ("closed market (league net WAR ~ 0)", closed_market),
    ("trade symmetry (charged ~ credited)", trade_symmetry),
    ("missing component is not scored as zero", missing_is_not_zero),
    ("payroll efficiency is era-neutral", era_neutrality),
    ("no wall-clock reads in builders", pinned_as_of),
    ("all indexes share one season window", consistent_window),
    ("small-sample shrink applied everywhere", shrink_parity),
    ("no duplicate move records", no_duplicate_moves),
    ("published JSON is finite", json_is_finite),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", action="store_true",
                        help="print current values as a reference snapshot")
    parser.parse_args()

    for name, fn in CHECKS:
        check(name, fn)

    width = max(len(n) for n, _, _ in results)
    failures = skipped = 0
    print("Front Office Index — invariant checks\n")
    for name, ok, detail in results:
        if ok is None:
            mark, skipped = "SKIP", skipped + 1
        elif ok:
            mark = "PASS"
        else:
            mark, failures = "FAIL", failures + 1
        print(f"  {mark}  {name.ljust(width)}  {detail}")

    passed = len(results) - failures - skipped
    print(f"\n{passed} passed, {failures} failed, {skipped} skipped")
    if failures:
        print("\nEach failure is a defect confirmed by the joint audit, not a flaky "
              "threshold.\nSee docs/audit-2026-08.md for what each one does to the "
              "published numbers.")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
