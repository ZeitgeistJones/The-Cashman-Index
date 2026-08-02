#!/usr/bin/env python3
"""League-wide acquisition-channel scoreboard (all 30 clubs).

Reuses per-team transaction caches from build_league_moves.py, scores FO moves
with BRef WAR, and writes data/acquisition_index.json with per-club + league
channel aggregates (no giant move dump in the web bundle).

Usage:
  python scripts/build_league_acquisition.py --use-cache
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_league_moves import load_or_fetch_rows  # noqa: E402
from build_moves import (  # noqa: E402
    DEFAULT_DOLLARS_PER_WAR,
    enrich_moves,
    group_into_moves,
    load_bref_war,
)
from classify_moves import classify_move  # noqa: E402
from team_codes import all_team_ids, team_abbr, team_name  # noqa: E402

DATA = REPO_ROOT / "data"


def _sum(moves: list[dict], field: str) -> float | None:
    vals = [m[field] for m in moves if m.get(field) is not None]
    if not vals:
        return None
    return round(sum(vals), 2)


def channel_rows(moves: list[dict]) -> list[dict[str, Any]]:
    by_ch: dict[str, list[dict]] = defaultdict(list)
    for m in moves:
        by_ch[m.get("acquisition_channel") or "other"].append(m)
    rows = []
    for channel, group in sorted(by_ch.items(), key=lambda kv: -len(kv[1])):
        rows.append(
            {
                "channel": channel,
                "moves": len(group),
                "war_acquired": _sum(group, "war_acquired"),
                "net_war": _sum(group, "net_war_exchange"),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2006)
    parser.add_argument("--use-cache", action="store_true")
    parser.add_argument("--no-war", action="store_true")
    parser.add_argument("--pause", type=float, default=0.25)
    parser.add_argument("--dollars-per-war", type=float, default=DEFAULT_DOLLARS_PER_WAR)
    args = parser.parse_args()

    today = dt.date.today()
    start = dt.date(args.start_year, 1, 1)
    war_index = None if args.no_war else load_bref_war()

    clubs: list[dict[str, Any]] = []
    league_moves: list[dict] = []

    for tid in all_team_ids():
        print(f"=== {team_abbr(tid)} ===", file=sys.stderr)
        rows = load_or_fetch_rows(tid, start, today, args.use_cache, args.pause)
        moves = group_into_moves(rows, team_id=tid)
        if war_index is not None:
            enrich_moves(moves, war_index, args.dollars_per_war, team_id=tid)
        for m in moves:
            classify_move(m, args.dollars_per_war)
        league_moves.extend(moves)
        clubs.append(
            {
                "team_id": tid,
                "team_abbr": team_abbr(tid),
                "team_name": team_name(tid),
                "moves": len(moves),
                "war_acquired": _sum(moves, "war_acquired"),
                "net_war": _sum(moves, "net_war_exchange"),
                "channels": channel_rows(moves),
            }
        )
        print(f"  {len(moves)} FO moves", file=sys.stderr)

    clubs.sort(key=lambda c: -(c["war_acquired"] or 0))
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope": "league",
        "season_range": [start.year, today.year],
        "framing": (
            "How every club acquired value by channel. WAR in = production for "
            "that club after the move; net WAR uses trade exchange when applicable. "
            "Same definitions for all thirty franchises."
        ),
        "clubs": clubs,
        "league_channels": channel_rows(league_moves),
        "limitations": [
            "Salary / ledger sparse outside clubs with hand overrides.",
            "Prospects grade at 0 WAR until they produce in MLB.",
            "International amateur signing pools not scored yet.",
            "Transaction history thin before ~2009 for some clubs.",
        ],
    }
    out = DATA / "acquisition_index.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(clubs)} clubs)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
