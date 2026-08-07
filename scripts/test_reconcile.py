#!/usr/bin/env python3
"""Offline checks for the closed-market reconciliation.

The league sum of net WAR must be zero: one club's gain from a trade is exactly
another club's loss. These fixtures cover the shapes that broke the previous
per-club formulation, above all the multi-team trade.

    python scripts/test_reconcile.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reconcile_trades import reconcile  # noqa: E402

failures: list[str] = []


def check(label: str, actual, expected) -> None:
    if actual == expected:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}: expected {expected!r}, got {actual!r}")
        failures.append(label)


def move(team: int, date: str, acquired=(), sent=()) -> dict:
    """One club's record of one trade. `acquired` is (id, name, war_for_us)."""
    return {
        "move_id": f"{team}-{date}-TR",
        "team_id": team,
        "move_date": date,
        "move_type": "Trade",
        "move_type_code": "TR",
        "players_acquired": [
            {"mlbam_id": i, "name": n, "war_during": w, "war_after_exit": 0.0}
            for i, n, w in acquired
        ],
        "players_sent_away": [
            {"mlbam_id": i, "name": n, "war_during": 0.0, "war_after_exit": w}
            for i, n, w in sent
        ],
    }


def league_net(moves: list[dict]) -> float:
    return round(sum(m["net_war_exchange"] for m in moves), 2)


# --- a plain two-club trade -------------------------------------------------

print("two-club trade")
A, B = 100, 200
two = [
    move(A, "2020-07-01", acquired=[(1, "Incoming", 6.0)], sent=[(2, "Outgoing", 4.0)]),
    move(B, "2020-07-01", acquired=[(2, "Outgoing", 4.0)], sent=[(1, "Incoming", 6.0)]),
]
reconcile(two)
check("buyer nets what it gained minus what it gave", two[0]["net_war_exchange"], 2.0)
check("seller nets the exact mirror", two[1]["net_war_exchange"], -2.0)
check("league sums to zero", league_net(two), 0.0)

# --- the case that broke: a three-club trade --------------------------------
#
# Grouping on (date, counterparty) splits this into two-club fragments, so each
# club's own record is an incomplete view of the deal. Scoring the player
# movement instead makes the three sides cancel anyway.

print("\nthree-club trade")
C = 300
three = [
    # A sends Star to B, receives Prospect from C
    move(A, "2020-02-10", acquired=[(11, "Prospect", 1.5)], sent=[(10, "Star", 9.0)]),
    # B receives Star from A, sends Arm to C
    move(B, "2020-02-10", acquired=[(10, "Star", 9.0)], sent=[(12, "Arm", 3.0)]),
    # C receives Arm from B, sends Prospect to A
    move(C, "2020-02-10", acquired=[(12, "Arm", 3.0)], sent=[(11, "Prospect", 1.5)]),
]
res = reconcile(three)
check("club A net", three[0]["net_war_exchange"], 1.5 - 9.0)
check("club B net", three[1]["net_war_exchange"], 9.0 - 3.0)
check("club C net", three[2]["net_war_exchange"], 3.0 - 1.5)
check("three-club league sums to zero", league_net(three), 0.0)
check("every departure matched", res["unmatched_departures"], 0)

# --- asymmetric records: clubs disagree about who moved ---------------------
#
# One club lists a player the other never records. The charge must still equal
# whatever the acquiring club actually booked, never the sender's own guess.

print("\ndisagreeing records")
skew = [
    move(A, "2021-07-30", acquired=[], sent=[(20, "Traded", 5.0), (21, "Ghost", 7.0)]),
    move(B, "2021-07-30", acquired=[(20, "Traded", 2.0)], sent=[]),
]
res = reconcile(skew)
check("charge uses the acquirer's figure, not the sender's",
      skew[0]["war_sent_away"], 2.0)
check("unrecorded departure is reported, not invented",
      res["unmatched_departures"], 1)
check("the matched part still cancels",
      round(skew[0]["net_war_exchange"] + skew[1]["net_war_exchange"], 2), 0.0)
check("orphan is named", any("Ghost" in o for o in res["orphan_examples"]), True)

# --- a club cannot charge itself --------------------------------------------

print("\nself-dealing guard")
self_deal = [
    move(A, "2022-01-01", acquired=[(30, "Same Guy", 4.0)], sent=[(30, "Same Guy", 4.0)]),
]
res = reconcile(self_deal)
check("own acquisition never offsets own departure",
      self_deal[0]["war_sent_away"], 0.0)
check("counted as unmatched instead", res["unmatched_departures"], 1)

# --- same player, different dates -------------------------------------------

print("\nsame player traded twice")
twice = [
    move(A, "2019-07-31", acquired=[], sent=[(40, "Journeyman", 2.0)]),
    move(B, "2019-07-31", acquired=[(40, "Journeyman", 2.0)], sent=[]),
    move(B, "2020-07-31", acquired=[], sent=[(40, "Journeyman", 5.0)]),
    move(C, "2020-07-31", acquired=[(40, "Journeyman", 5.0)], sent=[]),
]
res = reconcile(twice)
check("first move charges the first stint", twice[0]["war_sent_away"], 2.0)
check("second move charges the second stint", twice[2]["war_sent_away"], 5.0)
check("both deals cancel", league_net(twice), 0.0)

# --- non-trades are left alone ----------------------------------------------

print("\nnon-trades untouched")
signing = {
    "move_id": "x", "team_id": A, "move_date": "2023-01-01",
    "move_type": "Signed as Free Agent", "move_type_code": "SFA",
    "players_acquired": [{"mlbam_id": 50, "name": "FA", "war_during": 3.0}],
    "players_sent_away": [],
    "net_war_exchange": 3.0, "war_acquired": 3.0, "war_sent_away": 0.0,
}
reconcile([signing])
check("a signing keeps its score", signing["net_war_exchange"], 3.0)
check("reconciliation counts trades only", reconcile([signing])["trades"], 0)

print()
if failures:
    print(f"{len(failures)} failure(s): {', '.join(failures)}")
    raise SystemExit(1)
print("all checks passed")
