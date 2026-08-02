#!/usr/bin/env python3
"""Build league-wide trade moves for all 30 clubs (peer-club trades).

Fetches MLB Stats API transactions per team (cached), scores each trade from
that club's perspective with Baseball Reference WAR, and writes:

  data/league_moves.json  — all clubs' Trade rows (scored)
  data/moves.json         — Yankees full FO ledger (when NYY is in the run)

Usage:
  python scripts/build_league_moves.py
  python scripts/build_league_moves.py --use-cache
  python scripts/build_league_moves.py --teams 147,139
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_moves import (  # noqa: E402
    DEFAULT_DOLLARS_PER_WAR,
    apply_overrides,
    enrich_moves,
    fetch_transactions,
    group_into_moves,
    load_bref_war,
    public_fields,
)
from classify_moves import classify_move  # noqa: E402
from team_codes import (  # noqa: E402
    YANKEES_MLBAM_ID,
    all_team_ids,
    team_abbr,
)

DATA = REPO_ROOT / "data"
CACHE_DIR = DATA / "transactions" / "by_team"


def _parse_teams(raw: str | None) -> list[int]:
    if not raw:
        return all_team_ids()
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def load_or_fetch_rows(
    team_id: int,
    start: dt.date,
    end: dt.date,
    use_cache: bool,
    pause: float,
) -> list[dict]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{team_id}.json"

    legacy = DATA / "transactions.raw.json"
    if team_id == YANKEES_MLBAM_ID and not cache_path.exists() and legacy.exists():
        cache_path.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")

    if use_cache and cache_path.exists():
        print(f"  cache hit {team_abbr(team_id)}", file=sys.stderr)
        return json.loads(cache_path.read_text(encoding="utf-8"))

    if use_cache and not cache_path.exists():
        print(f"  no cache for {team_abbr(team_id)}; fetching", file=sys.stderr)

    rows = fetch_transactions(start, end, team_id=team_id, pause=pause)
    cache_path.write_text(json.dumps(rows), encoding="utf-8")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2006)
    parser.add_argument("--use-cache", action="store_true")
    parser.add_argument("--no-war", action="store_true")
    parser.add_argument("--dollars-per-war", type=float, default=DEFAULT_DOLLARS_PER_WAR)
    parser.add_argument("--pause", type=float, default=0.25)
    parser.add_argument("--teams", type=str, default=None)
    parser.add_argument("--overrides", type=Path, default=DATA / "salary_overrides.json")
    args = parser.parse_args()

    today = dt.date.today()
    start = dt.date(args.start_year, 1, 1)
    team_ids = _parse_teams(args.teams)

    all_trades: list[dict] = []
    yankees_all: list[dict] = []

    war_index = None if args.no_war else load_bref_war()

    for tid in team_ids:
        print(f"\n=== {team_abbr(tid)} ({tid}) ===", file=sys.stderr)
        rows = load_or_fetch_rows(tid, start, today, args.use_cache, args.pause)
        moves = group_into_moves(rows, team_id=tid)
        print(f"  {len(moves)} FO moves", file=sys.stderr)

        applied = 0
        if tid == YANKEES_MLBAM_ID:
            applied, unmatched = apply_overrides(moves, args.overrides)
            if applied:
                print(f"  applied {applied} overrides", file=sys.stderr)
            if unmatched:
                print(f"  unmatched overrides: {len(unmatched)}", file=sys.stderr)

        if war_index is not None:
            enrich_moves(moves, war_index, args.dollars_per_war, team_id=tid)
            if applied:
                apply_overrides(moves, args.overrides)
                for move in moves:
                    if (
                        move.get("salary_source") == "override"
                        and move.get("war_acquired") is not None
                        and move.get("salary_paid") is not None
                    ):
                        move["surplus_value"] = round(
                            move["war_acquired"] * args.dollars_per_war - move["salary_paid"],
                            2,
                        )
        for move in moves:
            classify_move(move, args.dollars_per_war)

        if tid == YANKEES_MLBAM_ID:
            yankees_all = moves

        trades = [
            m
            for m in moves
            if m.get("move_type_code") == "TR" or m.get("move_type") == "Trade"
        ]
        all_trades.extend(trades)
        print(f"  {len(trades)} trades for league file", file=sys.stderr)

    all_trades.sort(
        key=lambda m: (m["move_date"], m["team_id"], m["move_id"]), reverse=True
    )

    league_payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "data_source": "mlb-stats-api+bref",
        "scope": "league_trades",
        "season_range": [start.year, today.year],
        "dollars_per_war": args.dollars_per_war,
        "team_count": len(team_ids),
        "move_count": len(all_trades),
        "framing": (
            "Every club's trades scored the same way: during-tenure WAR for the "
            "focal club minus what leavers produced elsewhere. Peer comparison "
            "for FO trade books — every club scored the same way."
        ),
        "moves": [public_fields(m) for m in all_trades],
    }
    out_league = DATA / "league_moves.json"
    out_league.write_text(json.dumps(league_payload, indent=2, allow_nan=False) + "\n")
    print(f"\nWrote {len(all_trades)} league trades → {out_league}", file=sys.stderr)

    if yankees_all:
        nyy_payload = {
            "generated_at": league_payload["generated_at"],
            "data_source": "mlb-stats-api+bref",
            "season_range": [start.year, today.year],
            "dollars_per_war": args.dollars_per_war,
            "move_count": len(yankees_all),
            "moves": [public_fields(m) for m in yankees_all],
        }
        out_nyy = DATA / "moves.json"
        out_nyy.write_text(json.dumps(nyy_payload, indent=2, allow_nan=False) + "\n")
        print(f"Wrote {len(yankees_all)} Yankees moves → {out_nyy}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
