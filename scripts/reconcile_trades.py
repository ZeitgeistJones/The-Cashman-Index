#!/usr/bin/env python3
"""Make the closed-market identity hold by construction, not by coincidence.

A trade moves a player from one club to another. Whatever WAR that player then
produces is simultaneously the buyer's gain and the seller's loss, so summing
`net_war_exchange` across all 30 clubs must give zero.

Computing each club's net from its own transaction record almost achieves that
— 1,899 of 2,081 two-club trades already cancelled exactly — but it breaks
wherever the two clubs' records disagree about who moved:

  * **Multi-team trades.** Grouping on (date, counterparty) splits a three-club
    deal into two-club fragments. Each fragment sees only part of the deal, so
    the buyer's credit and the seller's charge are computed over different
    players. All 182 non-cancelling pairs were multi-team deals — the Mookie
    Betts trade (LAD/BOS/MIN, 2020-02-10) among them.
  * **One-sided records.** 1,058 trades appeared from only one club's feed.

This module removes the whole class of problem by scoring the *player movement*
rather than the *club pairing*. Each player who changes hands on a date carries
exactly one number: the WAR they produce for whoever acquired them. That number
is credited to the acquiring club and charged to the sending club. Both sides
read the same value from the same place, so they cancel no matter how many
clubs the deal involved or how the records are grouped.

Anything that stays unmatched is reported rather than absorbed: a charge with
nowhere to land is missing information, and quietly dropping it would let the
identity pass while the underlying record was still incomplete.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"


def is_trade(move: dict[str, Any]) -> bool:
    return move.get("move_type_code") == "TR" or move.get("move_type") == "Trade"


def build_movement_ledger(moves: list[dict]) -> dict[tuple[int, str], tuple[int, float]]:
    """(player, date) -> (acquiring club, WAR produced for that club).

    Keyed on the acquiring side because that is where the value actually lands:
    a player's post-trade WAR belongs to whoever received him, and that single
    figure is what both clubs must book.
    """
    ledger: dict[tuple[int, str], tuple[int, float]] = {}
    for move in moves:
        if not is_trade(move):
            continue
        for player in move.get("players_acquired") or []:
            pid = player.get("mlbam_id")
            if not pid:
                continue
            ledger[(pid, move["move_date"])] = (
                move.get("team_id"),
                float(player.get("war_during") or 0.0),
            )
    return ledger


def reconcile(moves: list[dict]) -> dict[str, Any]:
    """Recompute `war_sent_away` and `net_war_exchange` from the ledger.

    Mutates `moves` in place. Returns a report; callers should surface it,
    because unmatched departures are the honest residual and should not be
    silently rounded away.
    """
    ledger = build_movement_ledger(moves)
    matched = unmatched = 0
    unmatched_war = 0.0
    orphans: list[str] = []

    for move in moves:
        if not is_trade(move):
            continue
        charged = 0.0
        for player in move.get("players_sent_away") or []:
            pid = player.get("mlbam_id")
            entry = ledger.get((pid, move["move_date"])) if pid else None
            # A club cannot charge itself: if the only record of this player
            # moving on this date is the focal club's own acquisition, the deal
            # is not represented from both sides.
            if entry and entry[0] != move.get("team_id"):
                charged += entry[1]
                player["war_charged"] = round(entry[1], 2)
                matched += 1
            else:
                player["war_charged"] = None
                unmatched += 1
                unmatched_war += float(player.get("war_after_exit") or 0.0)
                if len(orphans) < 12:
                    orphans.append(f"{player.get('name')} @ {move['move_date']}")

        credited = sum(
            float(p.get("war_during") or 0.0) for p in move.get("players_acquired") or []
        )
        move["war_acquired"] = round(credited, 2)
        move["war_sent_away"] = round(charged, 2)
        move["net_war_exchange"] = round(credited - charged, 2)

    trades = [m for m in moves if is_trade(m)]
    total = sum(m.get("net_war_exchange") or 0.0 for m in trades)
    credited_all = sum(m.get("war_acquired") or 0.0 for m in trades)
    return {
        "trades": len(trades),
        "matched_departures": matched,
        "unmatched_departures": unmatched,
        "unmatched_war": round(unmatched_war, 2),
        "league_net": round(total, 2),
        "credited": round(credited_all, 2),
        "residual_share": round(abs(total) / credited_all, 4) if credited_all else None,
        "orphan_examples": orphans,
    }


def report(res: dict[str, Any], stream=sys.stderr) -> None:
    print(
        f"  reconciled {res['trades']} trades: "
        f"{res['matched_departures']} departures matched to an acquiring club, "
        f"{res['unmatched_departures']} unmatched",
        file=stream,
    )
    share = res["residual_share"]
    print(
        f"  league net {res['league_net']:+,.1f} of {res['credited']:,.0f} credited"
        + (f" ({share:.1%})" if share is not None else ""),
        file=stream,
    )
    if res["unmatched_departures"]:
        print(
            f"  {res['unmatched_departures']} departures had no matching acquisition "
            f"({res['unmatched_war']:+,.1f} WAR unbooked): "
            + ", ".join(res["orphan_examples"][:5]),
            file=stream,
        )


def _apply_to_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    moves = payload["moves"] if isinstance(payload, dict) else payload
    res = reconcile(moves)
    if isinstance(payload, dict):
        payload["reconciliation"] = {
            k: v for k, v in res.items() if k != "orphan_examples"
        }
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return res


def main() -> int:
    """Re-score already-built files in place, without refetching anything."""
    league = DATA / "league_moves.json"
    if not league.exists():
        print("data/league_moves.json not found; run build_league_moves.py first",
              file=sys.stderr)
        return 1

    print(f"Reconciling {league}", file=sys.stderr)
    res = _apply_to_file(league)
    report(res)

    # The single-club file is a slice of the same trades, so it must be scored
    # from the league-wide ledger — a club cannot see the other side on its own.
    club = DATA / "moves.json"
    if club.exists():
        league_moves = json.loads(league.read_text(encoding="utf-8"))["moves"]
        ledger = build_movement_ledger(league_moves)
        payload = json.loads(club.read_text(encoding="utf-8"))
        touched = 0
        for move in payload["moves"]:
            if not is_trade(move):
                continue
            charged = 0.0
            for player in move.get("players_sent_away") or []:
                entry = ledger.get((player.get("mlbam_id"), move["move_date"]))
                if entry and entry[0] != move.get("team_id"):
                    charged += entry[1]
                    player["war_charged"] = round(entry[1], 2)
                else:
                    player["war_charged"] = None
            credited = sum(
                float(p.get("war_during") or 0.0)
                for p in move.get("players_acquired") or []
            )
            move["war_acquired"] = round(credited, 2)
            move["war_sent_away"] = round(charged, 2)
            move["net_war_exchange"] = round(credited - charged, 2)
            touched += 1
        club.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n",
                        encoding="utf-8")
        print(f"  re-scored {touched} trades in {club}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
