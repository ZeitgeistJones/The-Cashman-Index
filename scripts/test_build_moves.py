#!/usr/bin/env python3
"""Offline checks for the grouping and scoring logic in build_moves.py.

Uses hand-built fixtures shaped like real MLB Stats API rows and Baseball
Reference WAR rows, so it runs with no network access.

    python scripts/test_build_moves.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_moves import (  # noqa: E402
    _effective_season,
    apply_overrides,
    enrich_moves,
    group_into_moves,
)

YANKEES = {"id": 147, "name": "New York Yankees"}
PADRES = {"id": 135, "name": "San Diego Padres"}
RANGERS = {"id": 140, "name": "Texas Rangers"}

failures: list[str] = []


def check(label: str, actual, expected) -> None:
    if actual == expected:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}: expected {expected!r}, got {actual!r}")
        failures.append(label)


# --- fixtures ---------------------------------------------------------------

TRANSACTION_ROWS = [
    # A five-for-two trade with San Diego: seven API rows, one real move.
    {"id": 1, "date": "2023-12-06", "typeCode": "TR", "typeDesc": "Trade",
     "person": {"id": 665742, "fullName": "Juan Soto"},
     "team": YANKEES, "fromTeam": PADRES,
     "description": "San Diego Padres traded Juan Soto to New York Yankees."},
    {"id": 2, "date": "2023-12-06", "typeCode": "TR", "typeDesc": "Trade",
     "person": {"id": 663757, "fullName": "Trent Grisham"},
     "team": YANKEES, "fromTeam": PADRES, "description": "..."},
    {"id": 3, "date": "2023-12-06", "typeCode": "TR", "typeDesc": "Trade",
     "person": {"id": 650633, "fullName": "Michael King"},
     "team": PADRES, "fromTeam": YANKEES, "description": "..."},
    {"id": 4, "date": "2023-12-06", "typeCode": "TR", "typeDesc": "Trade",
     "person": {"id": 543877, "fullName": "Kyle Higashioka"},
     "team": PADRES, "fromTeam": YANKEES, "description": "..."},

    # A separate trade on the SAME DAY with a different club. Must not merge.
    {"id": 5, "date": "2023-12-06", "typeCode": "TR", "typeDesc": "Trade",
     "person": {"id": 111111, "fullName": "Some Reliever"},
     "team": YANKEES, "fromTeam": RANGERS, "description": "..."},

    # A free-agent signing.
    {"id": 6, "date": "2019-12-18", "typeCode": "SFA", "typeDesc": "Signed as Free Agent",
     "person": {"id": 543037, "fullName": "Gerrit Cole"},
     "team": YANKEES,
     "description": "New York Yankees signed free agent RHP Gerrit Cole."},

    # A departure: the API still lists the Yankees in `team`.
    {"id": 7, "date": "2021-11-03", "typeCode": "FA", "typeDesc": "Free Agency",
     "person": {"id": 222222, "fullName": "Departing Veteran"},
     "team": YANKEES,
     "description": "New York Yankees' Departing Veteran elected free agency."},

    # Roster paperwork: filtered out by default.
    {"id": 8, "date": "2022-05-01", "typeCode": "OPT", "typeDesc": "Optioned",
     "person": {"id": 333333, "fullName": "Shuttle Arm"},
     "team": YANKEES, "description": "..."},
]

# (mlb_id, year, team, WAR, salary)
WAR_ROWS = [
    # Soto: one Yankees season, then leaves.
    (665742, 2024, "NYA", 7.9, 31000000.0),
    (665742, 2025, "NYN", 5.0, 51000000.0),
    # Grisham: two Yankees seasons.
    (663757, 2024, "NYA", 0.4, 5500000.0),
    (663757, 2025, "NYA", 2.1, 5000000.0),
    # King: pre-trade Yankees WAR must NOT count against the move.
    (650633, 2023, "NYA", 1.9, 750000.0),
    (650633, 2024, "SDN", 3.5, 1000000.0),
    (650633, 2025, "SDN", 1.1, 7750000.0),
    # Higashioka after leaving.
    (543877, 2024, "SDN", 1.2, 2000000.0),
    # Cole: signed Dec 2019, so 2019 (if any) must be excluded.
    (543037, 2019, "PIT", 6.9, 13500000.0),
    (543037, 2020, "NYA", 2.1, 36000000.0),
    (543037, 2021, "NYA", 4.4, 36000000.0),
]

WAR_INDEX: dict[int, list[dict]] = {}
for mlb_id, year, team, war, salary in WAR_ROWS:
    WAR_INDEX.setdefault(mlb_id, []).append(
        {"year": year, "team": team, "war": war, "salary": salary}
    )


# --- tests ------------------------------------------------------------------

print("effective season")
check("December move rolls to next season", _effective_season("2019-12-18"), 2020)
check("November move rolls to next season", _effective_season("2021-11-03"), 2022)
check("deadline trade uses current season", _effective_season("2021-07-30"), 2021)
check("January move uses current season", _effective_season("2019-01-11"), 2019)

print("\ngrouping")
moves = group_into_moves(TRANSACTION_ROWS)
by_date_type = {(m["move_date"], m["move_type"]): m for m in moves}
check("roster paperwork filtered out", len(moves), 4)

padres = next(m for m in moves if m["counterparty"] == "San Diego Padres")
check("multi-player trade collapses to one move",
      sorted(p["name"] for p in padres["players_acquired"]),
      ["Juan Soto", "Trent Grisham"])
check("outgoing side captured",
      sorted(p["name"] for p in padres["players_sent_away"]),
      ["Kyle Higashioka", "Michael King"])
check("same-day trade with another club stays separate",
      sum(1 for m in moves if m["move_type"] == "Trade"), 2)
check("trade summary is synthesized",
      padres["summary"].startswith("Trade with San Diego Padres: acquired"), True)

signing = by_date_type[("2019-12-18", "Signed as Free Agent")]
check("signing counts as acquisition",
      [p["name"] for p in signing["players_acquired"]], ["Gerrit Cole"])
check("signing summary uses the API sentence",
      signing["summary"], "New York Yankees signed free agent RHP Gerrit Cole")

departure = by_date_type[("2021-11-03", "Free Agency")]
check("elected free agency counts as a departure",
      ([p["name"] for p in departure["players_acquired"]],
       [p["name"] for p in departure["players_sent_away"]]),
      ([], ["Departing Veteran"]))

check("move_id is deterministic",
      group_into_moves(TRANSACTION_ROWS)[0]["move_id"], moves[0]["move_id"])
check("newest move first", moves[0]["move_date"], "2023-12-06")

print("\nscoring")
enrich_moves(moves, WAR_INDEX, dollars_per_war=8_000_000)

check("acquired WAR counts Yankees stints only", padres["war_acquired"], 10.4)
check("departing WAR excludes pre-trade Yankees stint", padres["war_sent_away"], 5.8)
check("net WAR exchange", padres["net_war_exchange"], 4.6)
check("salary summed from Yankees stints", padres["salary_paid"], 41500000.0)
check("salary source recorded", padres["salary_source"], "bref")
check("surplus value", padres["surplus_value"], 10.4 * 8_000_000 - 41500000.0)

check("December signing ignores prior-season WAR", signing["war_acquired"], 6.5)
check("signing surplus", signing["surplus_value"], 6.5 * 8_000_000 - 72000000.0)
check("departure-only move has no acquired WAR", departure["war_acquired"], 0.0)
check("unknown player leaves salary null",
      by_date_type[("2023-12-06", "Trade")] is not None, True)

rangers = next(m for m in moves if m["counterparty"] == "Texas Rangers")
check("no WAR data means null surplus, not zero", rangers["surplus_value"], None)
check("no WAR data means null salary", rangers["salary_paid"], None)

print("\noverrides")
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "overrides.json"
    path.write_text(json.dumps([
        {"_comment": ["ignored — no move_id and no match"]},
        {"match": {"player": "Gerrit Cole", "date": "2019-12-18"},
         "salary_paid": 324000000, "contract_years": 9},
    ]))
    applied = apply_overrides(moves, path)

check("override applied once", applied, 1)
check("override sets salary", signing["salary_paid"], 324000000)
check("override sets contract years", signing["contract_years"], 9)
check("override source recorded", signing["salary_source"], "override")
check("comment-only entry ignored", padres["salary_source"], "bref")

print()
if failures:
    print(f"{len(failures)} failure(s): {', '.join(failures)}")
    raise SystemExit(1)
print("all checks passed")
