#!/usr/bin/env python3
"""Offline checks for the grouping and scoring logic in build_moves.py.

Uses hand-built fixtures shaped like real MLB Stats API rows and Baseball
Reference WAR rows, so it runs with no network access.

    python scripts/test_build_moves.py
"""

import datetime as dt
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
    # Soto: prior elsewhere, one Yankees season, then leaves.
    (665742, 2022, "SDN", 5.8, 17000000.0),
    (665742, 2023, "SDN", 6.2, 23000000.0),
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
check("prior WAR on acquired side (buy-high/low context)", padres["war_prior_acquired"], 12.0)
check("prior Yankees WAR on sent side", padres["war_prior_sent"], 1.9)
check("after-exit WAR for acquired who left", padres["war_after_exit_acquired"], 5.0)
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
        # Reported dates drift from league filing dates; 4 days off must still land.
        {"match": {"player": "Juan Soto", "date": "2023-12-02"},
         "salary_paid": 31000000, "contract_years": 1},
        # Right player, date far outside tolerance -> must be reported, not applied.
        {"match": {"player": "Trent Grisham", "date": "2020-01-01"},
         "salary_paid": 999},
        # Player who appears in no move at all.
        {"match": {"player": "Nobody At All", "date": "2023-12-06"},
         "salary_paid": 123},
    ]))
    applied, unmatched = apply_overrides(moves, path)

check("overrides applied", applied, 2)
check("override sets salary", signing["salary_paid"], 324000000)
check("override sets contract years", signing["contract_years"], 9)
check("override source recorded", signing["salary_source"], "override")
check("near-miss date still matches", padres["salary_paid"], 31000000)
check("comment-only entry ignored silently", len(unmatched), 2)
check("out-of-tolerance date reported",
      any("Trent Grisham" in u for u in unmatched), True)
check("unknown player reported",
      any("Nobody At All" in u for u in unmatched), True)

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "ambiguous.json"
    # Grisham appears in exactly one move here; an override must never fan out
    # across several moves even when the date is loose.
    path.write_text(json.dumps([
        {"match": {"player": "Trent Grisham", "date": "2023-12-08"},
         "salary_paid": 5500000},
    ]))
    applied2, unmatched2 = apply_overrides(moves, path)
check("override lands on exactly one move", (applied2, len(unmatched2)), (1, 0))

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "active.json"
    this_year = dt.date.today().year
    path.write_text(json.dumps([
        {"match": {"player": "Juan Soto", "date": "2023-12-06"},
         "salary_paid": 31000000, "contract_through": 2024},
        {"match": {"player": "Gerrit Cole", "date": "2019-12-18"},
         "salary_paid": 324000000, "contract_through": this_year + 2},
    ]))
    apply_overrides(moves, path)
check("finished contract not marked active", padres["contract_active"], False)
check("running contract marked active", signing["contract_active"], True)

print("\nbaseball reference team codes")
# The first live run scored every move 0.0 because Baseball Reference labels
# Yankees stints "NYY", not the Lahman-style "NYA" this originally assumed.
# Wrong code => no Yankees stint ever matches => silent zeroes, not an error.
for code in ("NYA", "NYY"):
    coded_moves = group_into_moves(TRANSACTION_ROWS)
    coded_index = {
        665742: [{"year": 2024, "team": code, "war": 7.9, "salary": 31000000.0}],
        663757: [{"year": 2024, "team": code, "war": 0.4, "salary": 5500000.0}],
    }
    enrich_moves(coded_moves, coded_index, dollars_per_war=8_000_000)
    sd = next(m for m in coded_moves if m["counterparty"] == "San Diego Padres")
    check(f"{code} counts as a Yankees stint", sd["war_acquired"], 8.3)

other = group_into_moves(TRANSACTION_ROWS)
enrich_moves(other, {665742: [{"year": 2024, "team": "SDN", "war": 7.9, "salary": 1.0}]},
             dollars_per_war=8_000_000)
sd_other = next(m for m in other if m["counterparty"] == "San Diego Padres")
check("a non-Yankees stint is not credited as acquired", sd_other["war_acquired"], 0.0)

print("\nNaN handling")
# pandas fills blanks with NaN and float(nan) succeeds, so a single NaN used to
# poison every sum and land the literal `NaN` in moves.json — invalid JSON that
# broke the web build.
nan_moves = group_into_moves(TRANSACTION_ROWS)
enrich_moves(nan_moves, {
    665742: [{"year": 2024, "team": "NYY", "war": float("nan"), "salary": float("nan")},
             {"year": 2025, "team": "NYY", "war": 3.0, "salary": 20000000.0}],
    650633: [{"year": 2024, "team": "SDN", "war": float("nan"), "salary": None}],
}, dollars_per_war=8_000_000)
nan_sd = next(m for m in nan_moves if m["counterparty"] == "San Diego Padres")
check("NaN WAR does not poison the acquired sum", nan_sd["war_acquired"], 3.0)
check("NaN WAR does not poison the departing sum", nan_sd["war_sent_away"], 0.0)
check("NaN salary is dropped, not summed", nan_sd["salary_paid"], 20000000.0)
try:
    json.dumps({"moves": nan_moves}, allow_nan=False)
    serialisable = True
except ValueError:
    serialisable = False
check("output is valid JSON", serialisable, True)

print("\naccented names")
accented = group_into_moves([
    {"id": 99, "date": "2022-12-21", "typeCode": "SFA",
     "typeDesc": "Signed as Free Agent",
     "person": {"id": 607074, "fullName": "Carlos Rodón"},
     "team": YANKEES, "description": "New York Yankees signed free agent LHP Carlos Rodón."},
])
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "accent.json"
    path.write_text(json.dumps([
        {"match": {"player": "Carlos Rodon", "date": "2022-12-18"},
         "salary_paid": 162000000, "contract_years": 6},
    ]))
    applied3, unmatched3 = apply_overrides(accented, path)
check("unaccented override matches accented name", (applied3, unmatched3), (1, []))
check("accented override sets salary", accented[0]["salary_paid"], 162000000)

print("\nreal overrides file")
REAL_OVERRIDES = Path(__file__).resolve().parent.parent / "data" / "salary_overrides.json"
real = json.loads(REAL_OVERRIDES.read_text())
real_entries = [e for e in real if e.get("move_id") or e.get("match")]
check("file parses and has entries", len(real_entries) > 0, True)

problems: list[str] = []
seen: set[tuple[str, str]] = set()
for entry in real_entries:
    match = entry.get("match") or {}
    label = f"{match.get('player')} @ {match.get('date')}"
    if not entry.get("move_id"):
        if not match.get("player") or not match.get("date"):
            problems.append(f"{label}: needs both player and date")
            continue
        try:
            dt.date.fromisoformat(match["date"])
        except ValueError:
            problems.append(f"{label}: date is not YYYY-MM-DD")
        key = (match["player"].lower(), match["date"])
        if key in seen:
            problems.append(f"{label}: duplicate entry")
        seen.add(key)
    salary = entry.get("salary_paid")
    if not isinstance(salary, (int, float)) or salary <= 0:
        problems.append(f"{label}: salary_paid must be a positive number")
    # Guards against an AAV being pasted in where a total belongs.
    elif salary < 1_000_000:
        problems.append(f"{label}: salary_paid looks too small to be a total guarantee")
    years = entry.get("contract_years")
    if years is not None and not (isinstance(years, int) and 1 <= years <= 15):
        problems.append(f"{label}: contract_years out of range")
    through = entry.get("contract_through")
    if through is not None and not (isinstance(through, int) and 2015 <= through <= 2045):
        problems.append(f"{label}: contract_through out of range")
    if through is not None and years is not None and match.get("date"):
        # A 9-year deal signed in 2022 should end around 2031, not 2025.
        expected = int(match["date"][:4]) + years
        if abs(through - expected) > 2:
            problems.append(
                f"{label}: contract_through {through} disagrees with "
                f"{years} years from {match['date'][:4]}"
            )

check("every entry is well formed", problems, [])

print()
if failures:
    print(f"{len(failures)} failure(s): {', '.join(failures)}")
    raise SystemExit(1)
print("all checks passed")
