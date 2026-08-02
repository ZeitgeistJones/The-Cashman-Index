#!/usr/bin/env python3
"""Franchise + GM trade-rate index from data/league_moves.json.

Metric: net_war_per_season = sum(net_war_exchange on trades) / seasons in window
(or GM tenure seasons). Shrinks short samples toward league mean like draft VOS.

Writes data/trade_index.json.
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

from scoring import tenure_shrink  # noqa: E402
from team_codes import (  # noqa: E402
    TEAMS,
    team_abbr,
)

DATA = REPO_ROOT / "data"
AS_OF = dt.date.today()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(REPO_ROOT)}", file=sys.stderr)


def load_gm_stints() -> list[dict[str, Any]]:
    raw = load_json(DATA / "gm_tenures.json")
    return raw["stints"] if isinstance(raw, dict) else raw


def gm_for_move(team_id: int, move_date: str, stints: list[dict[str, Any]]) -> str | None:
    day = dt.date.fromisoformat(move_date)
    for stint in stints:
        if stint["team_id"] != team_id:
            continue
        start = dt.date.fromisoformat(stint["start"]) if stint.get("start") else dt.date(1900, 1, 1)
        end = dt.date.fromisoformat(stint["end"]) if stint.get("end") else AS_OF
        if start <= day <= end:
            return stint["person_id"]
    return None


def stint_seasons(stint: dict[str, Any], window: tuple[int, int]) -> float:
    start = dt.date.fromisoformat(stint["start"]) if stint.get("start") else dt.date(window[0], 1, 1)
    end = dt.date.fromisoformat(stint["end"]) if stint.get("end") else AS_OF
    lo = max(start, dt.date(window[0], 1, 1))
    hi = min(end, dt.date(window[1], 12, 31))
    if hi < lo:
        return 0.0
    # Approximate seasons as year span (same spirit as rankings).
    return max(0.5, (hi.year - lo.year) + (hi.month - lo.month) / 12.0)


def grade_rows(
    groups: dict[Any, dict[str, Any]],
    prior_seasons: float = 4.0,
) -> list[dict[str, Any]]:
    """Attach shrunk net_war_per_season and rank."""
    for g in groups.values():
        seasons = max(0.5, float(g["seasons"]))
        g["net_war"] = round(g["net_war_sum"], 2)
        g["trades"] = int(g["trade_count"])
        g["net_war_per_season_raw"] = round(g["net_war_sum"] / seasons, 4)

    rows = []
    for g in groups.values():
        seasons = max(0.5, float(g["seasons"]))
        shrunk = tenure_shrink(
            g["net_war_per_season_raw"],
            int(round(seasons)),
            int(round(prior_seasons)),
        )
        row = {
            **{k: v for k, v in g.items() if not k.endswith("_sum") and k != "trade_count"},
            "net_war_per_season": round(shrunk, 4),
            "trade_net_rate": round(shrunk, 4),
        }
        rows.append(row)

    rows.sort(key=lambda r: (-r["net_war_per_season"], -r["net_war"], r.get("name") or r.get("team_abbr") or ""))
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--moves", type=Path, default=DATA / "league_moves.json")
    parser.add_argument("--prior-seasons", type=float, default=4.0)
    args = parser.parse_args()

    if not args.moves.exists():
        print(f"Missing {args.moves}; run build_league_moves.py first.", file=sys.stderr)
        return 1

    payload = load_json(args.moves)
    moves = payload.get("moves") or []
    window = tuple(payload.get("season_range") or [2006, AS_OF.year])
    stints = load_gm_stints()
    names = {s["person_id"]: s["name"] for s in stints}

    by_team: dict[int, dict[str, Any]] = {}
    for tid, meta in TEAMS.items():
        by_team[tid] = {
            "team_id": tid,
            "team_abbr": meta["abbr"],
            "team_name": meta["name"],
            "net_war_sum": 0.0,
            "trade_count": 0,
            "seasons": float(window[1] - window[0] + 1),
        }

    by_gm: dict[str, dict[str, Any]] = {}

    for move in moves:
        net = move.get("net_war_exchange")
        if net is None:
            continue
        tid = move.get("team_id")
        if tid not in by_team:
            continue
        by_team[tid]["net_war_sum"] += float(net)
        by_team[tid]["trade_count"] += 1

        pid = gm_for_move(tid, move["move_date"], stints)
        if not pid:
            continue
        if pid not in by_gm:
            # Seasons = sum of this person's stint lengths in window.
            seasons = sum(
                stint_seasons(s, window) for s in stints if s["person_id"] == pid
            )
            by_gm[pid] = {
                "person_id": pid,
                "name": names.get(pid, pid),
                "teams": sorted(
                    {
                        team_abbr(s["team_id"])
                        for s in stints
                        if s["person_id"] == pid
                    }
                ),
                "net_war_sum": 0.0,
                "trade_count": 0,
                "seasons": max(0.5, seasons),
            }
        by_gm[pid]["net_war_sum"] += float(net)
        by_gm[pid]["trade_count"] += 1

    franchises = grade_rows(by_team, args.prior_seasons)
    gms = grade_rows(by_gm, args.prior_seasons)

    out = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "window": list(window),
        "framing": (
            "Trade grade = shrunk net WAR per season from club-perspective trades. "
            "Same definition for every franchise and GM."
        ),
        "franchises": franchises,
        "gms": gms,
    }
    write_json(DATA / "trade_index.json", out)
    print(
        f"Top trade franchise: {franchises[0]['team_abbr']}  "
        f"Top trade GM: {gms[0]['name'] if gms else '?'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
