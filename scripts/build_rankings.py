#!/usr/bin/env python3
"""Build franchise + GM ranking datasets for the Front Office Index.

Pulls team seasons (wins/losses/playoffs/pennants/WS) from the MLB Stats API,
scrapes opening-day payrolls from Baseball Cube, then writes:

  data/team_seasons.json
  data/franchise_index.json
  data/gm_index.json
  data/exit_resumes.json

Requires: pip install -r scripts/requirements.txt
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

# Allow `from scoring import ...` when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring import (
    ROUND_DEPTH,
    attach_rates,
    category_ranks,
    composite_scores,
    efficiency_wins,
    last_complete_season,
    payroll_efficiency_from_seasons,
    rank_descending,
    tenure_shrink,
    wins_per_100m,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"

WINDOW_START = 2006
WINDOW_END = 2026
AS_OF = dt.date(2026, 8, 1)
# Draft VOS shrink prior (matches build_draft_index.grade_groups).
DRAFT_PRIOR_PICKS = 100
DRAFT_MATURE_LAG = 6
TRADE_PRIOR_SEASONS = 4

SESSION_HEADERS = {"User-Agent": "front-office-index/0.1 (personal project)"}

# Canonical franchise ids used throughout the window.
TEAM_META: dict[int, dict[str, str]] = {
    108: {"abbr": "LAA", "name": "Los Angeles Angels"},
    109: {"abbr": "ARI", "name": "Arizona Diamondbacks"},
    110: {"abbr": "BAL", "name": "Baltimore Orioles"},
    111: {"abbr": "BOS", "name": "Boston Red Sox"},
    112: {"abbr": "CHC", "name": "Chicago Cubs"},
    113: {"abbr": "CIN", "name": "Cincinnati Reds"},
    114: {"abbr": "CLE", "name": "Cleveland Guardians"},
    115: {"abbr": "COL", "name": "Colorado Rockies"},
    116: {"abbr": "DET", "name": "Detroit Tigers"},
    117: {"abbr": "HOU", "name": "Houston Astros"},
    118: {"abbr": "KC", "name": "Kansas City Royals"},
    119: {"abbr": "LAD", "name": "Los Angeles Dodgers"},
    120: {"abbr": "WSH", "name": "Washington Nationals"},
    121: {"abbr": "NYM", "name": "New York Mets"},
    133: {"abbr": "OAK", "name": "Athletics"},
    134: {"abbr": "PIT", "name": "Pittsburgh Pirates"},
    135: {"abbr": "SD", "name": "San Diego Padres"},
    136: {"abbr": "SEA", "name": "Seattle Mariners"},
    137: {"abbr": "SF", "name": "San Francisco Giants"},
    138: {"abbr": "STL", "name": "St. Louis Cardinals"},
    139: {"abbr": "TB", "name": "Tampa Bay Rays"},
    140: {"abbr": "TEX", "name": "Texas Rangers"},
    141: {"abbr": "TOR", "name": "Toronto Blue Jays"},
    142: {"abbr": "MIN", "name": "Minnesota Twins"},
    143: {"abbr": "PHI", "name": "Philadelphia Phillies"},
    144: {"abbr": "ATL", "name": "Atlanta Braves"},
    145: {"abbr": "CWS", "name": "Chicago White Sox"},
    146: {"abbr": "MIA", "name": "Miami Marlins"},
    147: {"abbr": "NYY", "name": "New York Yankees"},
    158: {"abbr": "MIL", "name": "Milwaukee Brewers"},
}

# Map Baseball Cube / historical display names → team_id.
NAME_TO_ID: dict[str, int] = {
    "Los Angeles Angels": 108,
    "Los Angeles Angels of Anaheim": 108,
    "Anaheim Angels": 108,
    "Arizona Diamondbacks": 109,
    "Baltimore Orioles": 110,
    "Boston Red Sox": 111,
    "Chicago Cubs": 112,
    "Cincinnati Reds": 113,
    "Cleveland Guardians": 114,
    "Cleveland Indians": 114,
    "Colorado Rockies": 115,
    "Detroit Tigers": 116,
    "Houston Astros": 117,
    "Kansas City Royals": 118,
    "Los Angeles Dodgers": 119,
    "Washington Nationals": 120,
    "New York Mets": 121,
    "Oakland Athletics": 133,
    "Athletics": 133,
    "Pittsburgh Pirates": 134,
    "San Diego Padres": 135,
    "Seattle Mariners": 136,
    "San Francisco Giants": 137,
    "St. Louis Cardinals": 138,
    "Tampa Bay Rays": 139,
    "Tampa Bay Devil Rays": 139,
    "Texas Rangers": 140,
    "Toronto Blue Jays": 141,
    "Minnesota Twins": 142,
    "Philadelphia Phillies": 143,
    "Atlanta Braves": 144,
    "Chicago White Sox": 145,
    "Miami Marlins": 146,
    "Florida Marlins": 146,
    "New York Yankees": 147,
    "Milwaukee Brewers": 158,
}


def _session():
    import requests

    session = requests.Session()
    session.headers.update(SESSION_HEADERS)
    return session


def load_weights() -> dict[str, Any]:
    return json.loads((DATA / "weights.json").read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(REPO_ROOT)}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Team seasons from MLB Stats API
# ---------------------------------------------------------------------------


def fetch_standings_year(session, season: int) -> dict[int, dict[str, Any]]:
    response = session.get(
        "https://statsapi.mlb.com/api/v1/standings",
        params={
            "leagueId": "103,104",
            "season": season,
            "standingsTypes": "regularSeason",
        },
        timeout=60,
    )
    response.raise_for_status()
    by_team: dict[int, dict[str, Any]] = {}
    for block in response.json().get("records", []):
        for row in block.get("teamRecords", []):
            team = row["team"]
            tid = int(team["id"])
            if tid not in TEAM_META:
                continue
            wins = int(row["wins"])
            losses = int(row["losses"])
            pct_raw = str(row.get("winningPercentage") or "")
            if pct_raw.startswith("."):
                win_pct = float("0" + pct_raw)
            elif pct_raw:
                try:
                    win_pct = float(pct_raw)
                except ValueError:
                    games = wins + losses
                    win_pct = wins / games if games else 0.0
            else:
                games = wins + losses
                win_pct = wins / games if games else 0.0
            by_team[tid] = {
                "team_id": tid,
                "season": season,
                "wins": wins,
                "losses": losses,
                "win_pct": round(win_pct, 4),
                "playoffs": False,
                "playoff_depth": 0,
                "pennant": False,
                "world_series": False,
            }
    return by_team


def _series_winner_from_games(games: list[dict]) -> int | None:
    """Return team_id that won a best-of series, using clinching game if present."""
    if not games:
        return None
    last = games[-1]
    if last["teams"]["away"].get("isWinner"):
        return int(last["teams"]["away"]["team"]["id"])
    if last["teams"]["home"].get("isWinner"):
        return int(last["teams"]["home"]["team"]["id"])
    return None


def fetch_postseason_year(session, season: int, by_team: dict[int, dict[str, Any]]) -> None:
    response = session.get(
        "https://statsapi.mlb.com/api/v1/schedule",
        params={
            "sportId": 1,
            "season": season,
            "gameTypes": "F,D,L,W",
        },
        timeout=60,
    )
    response.raise_for_status()
    series_games: dict[tuple[str, frozenset[int]], list[dict]] = defaultdict(list)

    for day in response.json().get("dates", []):
        for game in day.get("games", []):
            if game.get("status", {}).get("detailedState") not in {
                "Final",
                "Completed Early",
                "Game Over",
            }:
                continue
            away_id = int(game["teams"]["away"]["team"]["id"])
            home_id = int(game["teams"]["home"]["team"]["id"])
            gtype = game.get("gameType") or "?"
            depth = ROUND_DEPTH.get(gtype, 0)
            for tid in (away_id, home_id):
                if tid not in by_team:
                    continue
                by_team[tid]["playoffs"] = True
                if depth > by_team[tid]["playoff_depth"]:
                    by_team[tid]["playoff_depth"] = depth
            key = (gtype, frozenset({away_id, home_id}))
            series_games[key].append(game)

    # Pennants = LCS winners; WS = World Series winner.
    for (gtype, _pair), games in series_games.items():
        games_sorted = sorted(games, key=lambda g: g.get("officialDate") or "")
        winner = _series_winner_from_games(games_sorted)
        if winner is None or winner not in by_team:
            continue
        if gtype == "L":
            by_team[winner]["pennant"] = True
        elif gtype == "W":
            by_team[winner]["world_series"] = True


def build_team_seasons(session, start: int, end: int, pause: float) -> list[dict[str, Any]]:
    seasons: list[dict[str, Any]] = []
    for year in range(start, end + 1):
        print(f"  seasons {year}", file=sys.stderr)
        try:
            by_team = fetch_standings_year(session, year)
        except Exception as exc:  # noqa: BLE001 — keep going for in-progress years
            print(f"    standings failed: {exc}", file=sys.stderr)
            continue
        if not by_team:
            print(f"    no standings for {year}", file=sys.stderr)
            continue
        try:
            fetch_postseason_year(session, year, by_team)
        except Exception as exc:  # noqa: BLE001
            print(f"    postseason failed: {exc}", file=sys.stderr)
        seasons.extend(sorted(by_team.values(), key=lambda r: r["team_id"]))
        time.sleep(pause)
    return seasons


# ---------------------------------------------------------------------------
# Payroll scrape (Baseball Cube)
# ---------------------------------------------------------------------------


def scrape_payroll_year(session, year: int) -> dict[int, int]:
    url = f"https://thebaseballcube.com/content/payroll_year/{year}/"
    response = session.get(url, timeout=60)
    response.raise_for_status()
    html = response.text
    # Rows look like: >New York Yankees</a></td>...<td class='stat highlight' sortkey='305444574'>305,444,574</td>
    pattern = re.compile(
        r">([A-Za-z .'\-]+)</a></td><td><a href=[^>]+>team roster</a></td>"
        r"<td>[A-Z]{2}</td><td[^>]*>[^<]*</td>"
        r"<td class='stat highlight' sortkey='(\d+)'>",
        re.IGNORECASE,
    )
    out: dict[int, int] = {}
    for name, payroll_s in pattern.findall(html):
        name = name.strip()
        tid = NAME_TO_ID.get(name)
        if tid is None:
            # Try without leading articles quirks
            continue
        out[tid] = int(payroll_s)
    return out


def attach_payroll(session, seasons: list[dict[str, Any]], pause: float) -> dict[str, Any]:
    by_year: dict[int, list[dict]] = defaultdict(list)
    for row in seasons:
        by_year[row["season"]].append(row)

    coverage = {"source": "baseball-cube", "years": {}, "missing": []}
    for year in sorted(by_year):
        print(f"  payroll {year}", file=sys.stderr)
        try:
            payrolls = scrape_payroll_year(session, year)
        except Exception as exc:  # noqa: BLE001
            print(f"    payroll scrape failed: {exc}", file=sys.stderr)
            payrolls = {}
        coverage["years"][str(year)] = len(payrolls)
        for row in by_year[year]:
            pay = payrolls.get(row["team_id"])
            row["payroll"] = pay
            if pay is None:
                coverage["missing"].append(f"{year}-{row['team_id']}")
        time.sleep(pause)
    return coverage


# ---------------------------------------------------------------------------
# Franchise index
# ---------------------------------------------------------------------------


def load_draft_vos() -> tuple[dict[int, float], dict[str, float]]:
    """Optional draft grades keyed by team_id and gm person_id."""
    path = DATA / "draft_index.json"
    if not path.exists():
        return {}, {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_team = {
        int(row["team_id"]): float(row.get("avg_vos") or 0.0)
        for row in payload.get("franchises") or []
    }
    by_gm = {
        str(row["person_id"]): float(row.get("avg_vos") or 0.0)
        for row in payload.get("gms") or []
        if row.get("person_id")
    }
    return by_team, by_gm


def load_trade_rates() -> tuple[dict[int, float], dict[str, float]]:
    """Optional trade net WAR/season keyed by team_id and gm person_id."""
    path = DATA / "trade_index.json"
    if not path.exists():
        return {}, {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_team = {
        int(row["team_id"]): float(row.get("trade_net_rate") or 0.0)
        for row in payload.get("franchises") or []
    }
    by_gm = {
        str(row["person_id"]): float(row.get("trade_net_rate") or 0.0)
        for row in payload.get("gms") or []
        if row.get("person_id")
    }
    return by_team, by_gm


_DRAFT_PICKS: list[dict[str, Any]] | None = None
_LEAGUE_MOVES: list[dict[str, Any]] | None = None


def load_draft_picks() -> list[dict[str, Any]]:
    global _DRAFT_PICKS
    if _DRAFT_PICKS is None:
        path = DATA / "draft_picks.json"
        if not path.exists():
            _DRAFT_PICKS = []
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            _DRAFT_PICKS = list(payload.get("picks") or [])
    return _DRAFT_PICKS


def load_league_moves() -> list[dict[str, Any]]:
    global _LEAGUE_MOVES
    if _LEAGUE_MOVES is None:
        path = DATA / "league_moves.json"
        if not path.exists():
            alt = DATA / "moves.json"
            path = alt if alt.exists() else path
        if not path.exists():
            _LEAGUE_MOVES = []
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            _LEAGUE_MOVES = list(payload.get("moves") or [])
    return _LEAGUE_MOVES


def draft_vos_through(person_id: str, as_of: dt.date) -> float:
    """Shrunk avg VOS for picks drafted on/before as_of (mature relative to as_of)."""
    mature_through = as_of.year - DRAFT_MATURE_LAG
    vos_list: list[float] = []
    for pick in load_draft_picks():
        if pick.get("gm_person_id") != person_id:
            continue
        year = int(pick.get("draft_year") or 0)
        if year <= 0 or year > mature_through:
            continue
        if dt.date(year, 6, 15) > as_of:
            continue
        vos_list.append(float(pick.get("vos") or 0.0))
    if not vos_list:
        return 0.0
    avg = sum(vos_list) / len(vos_list)
    shrink = len(vos_list) / (len(vos_list) + DRAFT_PRIOR_PICKS)
    return round(avg * shrink, 4)


def trade_net_rate_through(
    person_id: str,
    as_of: dt.date,
    stints: list[dict[str, Any]],
    seasons: float,
) -> float:
    """Trade net WAR / season using only deals on/before as_of."""
    net = 0.0
    as_of_s = as_of.isoformat()
    person_stints = [s for s in stints if s["person_id"] == person_id]
    for move in load_league_moves():
        move_date = move.get("move_date")
        if not move_date or str(move_date) > as_of_s:
            continue
        if move.get("net_war_exchange") is None:
            continue
        try:
            tid = int(move["team_id"])
            day = dt.date.fromisoformat(str(move_date)[:10])
        except (KeyError, TypeError, ValueError):
            continue
        attributed = False
        for stint in person_stints:
            if stint["team_id"] != tid:
                continue
            start = (
                dt.date.fromisoformat(stint["start"])
                if stint.get("start")
                else dt.date(1900, 1, 1)
            )
            end = (
                dt.date.fromisoformat(stint["end"])
                if stint.get("end")
                else AS_OF
            )
            if start <= day <= end:
                attributed = True
                break
        if not attributed:
            continue
        net += float(move["net_war_exchange"])
    seasons_n = max(0.5, float(seasons))
    raw = net / seasons_n
    return tenure_shrink(raw, int(round(seasons_n)), TRADE_PRIOR_SEASONS)


def aggregate_franchise(seasons: list[dict[str, Any]], weights: dict[str, float]) -> dict[str, Any]:
    complete_end = last_complete_season(AS_OF, WINDOW_END)
    by_team: dict[int, list[dict]] = defaultdict(list)
    for row in seasons:
        if int(row["season"]) > complete_end:
            continue
        by_team[row["team_id"]].append(row)

    draft_by_team, _ = load_draft_vos()
    trade_by_team, _ = load_trade_rates()

    rows: list[dict[str, Any]] = []
    for tid, meta in TEAM_META.items():
        team_rows = by_team.get(tid, [])
        wins = sum(r["wins"] for r in team_rows)
        losses = sum(r["losses"] for r in team_rows)
        games = wins + losses
        playoff_years = sorted({r["season"] for r in team_rows if r.get("playoffs")})
        playoff_depth = sum(int(r.get("playoff_depth") or 0) for r in team_rows)
        pennants = sum(1 for r in team_rows if r.get("pennant"))
        ws = sum(1 for r in team_rows if r.get("world_series"))
        win_pct = round(wins / games, 4) if games else 0.0
        efficiency, payroll_sum = payroll_efficiency_from_seasons(team_rows)
        row = attach_rates(
            {
                "team_id": tid,
                "team_abbr": meta["abbr"],
                "team_name": meta["name"],
                "seasons": len(team_rows),
                "wins": wins,
                "losses": losses,
                "win_pct": win_pct,
                "playoff_appearances": len(playoff_years),
                "playoff_depth": playoff_depth,
                "playoff_years": playoff_years,
                "pennants": pennants,
                "world_series": ws,
                "payroll_sum": payroll_sum,
                "payroll_efficiency": efficiency,
                "draft_vos": round(draft_by_team.get(tid, 0.0), 4),
                "trade_net_rate": round(trade_by_team.get(tid, 0.0), 4),
            }
        )
        rows.append(row)

    scores = composite_scores(rows, weights)
    ranks = rank_descending(scores)
    cats = category_ranks(rows)
    for row, score, rank, cat in zip(rows, scores, ranks, cats):
        row["composite"] = score
        row["rank"] = rank
        row["category_ranks"] = cat

    rows.sort(key=lambda r: r["rank"])
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "window": [WINDOW_START, complete_end],
        "weights": weights,
        "franchises": rows,
    }


# ---------------------------------------------------------------------------
# GM index + exit resumes
# ---------------------------------------------------------------------------


def parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    return dt.date.fromisoformat(value)


def season_gm(team_id: int, season: int, stints: list[dict[str, Any]]) -> str | None:
    """Attribute a season to the GM who held the job for the majority of the calendar year.

    Uses July 1 as the midpoint of the championship season.
    """
    mid = dt.date(season, 7, 1)
    for stint in stints:
        if stint["team_id"] != team_id:
            continue
        start = parse_date(stint["start"]) or dt.date(1900, 1, 1)
        end = parse_date(stint["end"]) or AS_OF
        if start <= mid <= end:
            return stint["person_id"]
    # Fallback: any overlap with the calendar year
    year_start, year_end = dt.date(season, 1, 1), dt.date(season, 12, 31)
    best = None
    best_days = -1
    for stint in stints:
        if stint["team_id"] != team_id:
            continue
        start = max(parse_date(stint["start"]) or year_start, year_start)
        end = min(parse_date(stint["end"]) or year_end, year_end)
        days = (end - start).days
        if days > best_days:
            best_days = days
            best = stint["person_id"]
    return best


def metrics_from_seasons(season_rows: list[dict[str, Any]]) -> dict[str, Any]:
    wins = sum(r["wins"] for r in season_rows)
    losses = sum(r["losses"] for r in season_rows)
    games = wins + losses
    playoff_years = sorted({r["season"] for r in season_rows if r.get("playoffs")})
    playoff_depth = sum(int(r.get("playoff_depth") or 0) for r in season_rows)
    efficiency, payroll_sum = payroll_efficiency_from_seasons(season_rows)
    return attach_rates(
        {
            "seasons": len(season_rows),
            "wins": wins,
            "losses": losses,
            "win_pct": round(wins / games, 4) if games else 0.0,
            "playoff_appearances": len(playoff_years),
            "playoff_depth": playoff_depth,
            "playoff_years": playoff_years,
            "pennants": sum(1 for r in season_rows if r.get("pennant")),
            "world_series": sum(1 for r in season_rows if r.get("world_series")),
            "payroll_sum": payroll_sum,
            "payroll_efficiency": efficiency,
        }
    )


def build_gm_index(
    seasons: list[dict[str, Any]],
    stints: list[dict[str, Any]],
    weights: dict[str, float],
    min_seasons: int,
    tenure_prior: int,
) -> dict[str, Any]:
    complete_end = last_complete_season(AS_OF, WINDOW_END)
    seasons = [r for r in seasons if int(r["season"]) <= complete_end]

    # Map each team-season → person_id
    attribution: dict[tuple[int, int], str] = {}
    for row in seasons:
        pid = season_gm(row["team_id"], row["season"], stints)
        if pid:
            attribution[(row["team_id"], row["season"])] = pid

    by_person_seasons: dict[str, list[dict]] = defaultdict(list)
    for row in seasons:
        pid = attribution.get((row["team_id"], row["season"]))
        if pid:
            by_person_seasons[pid].append(row)

    names = {s["person_id"]: s["name"] for s in stints}
    teams_by_person: dict[str, list[str]] = defaultdict(list)
    active = set()
    for s in stints:
        abbr = s.get("team_abbr") or TEAM_META.get(s["team_id"], {}).get("abbr", "?")
        if abbr not in teams_by_person[s["person_id"]]:
            teams_by_person[s["person_id"]].append(abbr)
        if s.get("exit_type") == "still_active" or s.get("end") is None:
            active.add(s["person_id"])

    _, draft_by_gm = load_draft_vos()
    _, trade_by_gm = load_trade_rates()

    rows: list[dict[str, Any]] = []
    for pid, season_rows in by_person_seasons.items():
        metrics = metrics_from_seasons(season_rows)
        metrics["draft_vos"] = round(draft_by_gm.get(pid, 0.0), 4)
        metrics["trade_net_rate"] = round(trade_by_gm.get(pid, 0.0), 4)
        rows.append(
            {
                "person_id": pid,
                "name": names.get(pid, pid),
                "teams": teams_by_person.get(pid, []),
                "still_active": pid in active,
                "small_sample": metrics["seasons"] < min_seasons,
                **metrics,
            }
        )

    raw_scores = composite_scores(rows, weights)
    # Light shrink only — rates already remove pure accumulation; shrink damps tiny samples.
    adj_scores = [
        tenure_shrink(score, row["seasons"], tenure_prior)
        for score, row in zip(raw_scores, rows)
    ]
    ranks = rank_descending(adj_scores)
    cats = category_ranks(rows)
    for row, raw, adj, rank, cat in zip(rows, raw_scores, adj_scores, ranks, cats):
        row["composite_raw"] = raw
        row["composite"] = adj
        row["tenure_weight"] = round(
            row["seasons"] / (row["seasons"] + tenure_prior), 4
        ) if row["seasons"] else 0.0
        row["rank"] = rank
        row["category_ranks"] = cat

    rows.sort(key=lambda r: (r["rank"], r["name"]))
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "window": [WINDOW_START, complete_end],
        "weights": weights,
        "tenure_prior_seasons": tenure_prior,
        "gm_count": len(rows),
        "gms": rows,
    }


def resume_through_date(
    person_id: str,
    as_of: dt.date,
    seasons: list[dict[str, Any]],
    stints: list[dict[str, Any]],
) -> dict[str, Any]:
    """Career metrics for person_id using seasons attributed to them with season mid <= as_of.

    Draft VOS and trade net rate are also cut at as_of so yearly/exit composites
    cannot credit picks or deals that had not happened yet.
    """
    attributed: list[dict] = []
    for row in seasons:
        mid = dt.date(row["season"], 7, 1)
        if mid > as_of:
            continue
        if season_gm(row["team_id"], row["season"], stints) == person_id:
            attributed.append(row)
    metrics = metrics_from_seasons(attributed)
    metrics["draft_vos"] = draft_vos_through(person_id, as_of)
    metrics["trade_net_rate"] = trade_net_rate_through(
        person_id, as_of, stints, metrics["seasons"]
    )
    return metrics


def build_exit_resumes(
    seasons: list[dict[str, Any]],
    stints: list[dict[str, Any]],
    weights: dict[str, float],
) -> dict[str, Any]:
    exits: list[dict[str, Any]] = []
    for stint in stints:
        if stint.get("exit_type") == "still_active" or not stint.get("end"):
            continue
        end = parse_date(stint["end"])
        if end is None or end < dt.date(WINDOW_START, 1, 1) or end > AS_OF:
            continue
        resume = resume_through_date(stint["person_id"], end, seasons, stints)
        exits.append(
            {
                "exit_date": stint["end"],
                "exit_type": stint.get("exit_type") or "other",
                "person_id": stint["person_id"],
                "name": stint["name"],
                "team_id": stint["team_id"],
                "team_abbr": stint.get("team_abbr")
                or TEAM_META.get(stint["team_id"], {}).get("abbr"),
                "peer_resume": resume,
            }
        )

    # Score each exit resume within the exit pool (same weights as franchise/GM index).
    if exits:
        scores = composite_scores([e["peer_resume"] for e in exits], weights)
        for exit_row, score in zip(exits, scores):
            exit_row["peer_score"] = score

    exits.sort(key=lambda e: e["exit_date"])
    fired = [e for e in exits if e["exit_type"] in {"fired", "contract_expired"}]
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "window": [WINDOW_START, WINDOW_END],
        "as_of": AS_OF.isoformat(),
        "exit_count": len(exits),
        "summary": {
            "fired_count": len(fired),
        },
        "exits": exits,
    }


def _offseason_exits(
    stints: list[dict[str, Any]],
    season: int,
) -> list[dict[str, Any]]:
    """Exits after season `season` and before the next season's midpoint (Jul 1)."""
    start = dt.date(season, 10, 1)
    end = dt.date(season + 1, 7, 1)
    out = []
    for stint in stints:
        if stint.get("exit_type") not in {"fired", "contract_expired"}:
            continue
        if not stint.get("end"):
            continue
        when = parse_date(stint["end"])
        if when and start <= when < end:
            out.append(stint)
    return out


def build_yearly_index(
    seasons: list[dict[str, Any]],
    stints: list[dict[str, Any]],
    weights: dict[str, float],
) -> dict[str, Any]:
    """Year-by-year rate ranks among active GMs + that offseason's exits."""
    names = {s["person_id"]: s["name"] for s in stints}
    years: list[dict[str, Any]] = []

    last_complete = last_complete_season(AS_OF, WINDOW_END)

    for year in range(WINDOW_START, last_complete + 1):
        active_ids: set[str] = set()
        for stint in stints:
            start = parse_date(stint["start"]) or dt.date(1900, 1, 1)
            end = parse_date(stint["end"]) or AS_OF
            mid = dt.date(year, 7, 1)
            if start <= mid <= end:
                active_ids.add(stint["person_id"])

        active_rows: list[dict[str, Any]] = []
        for pid in sorted(active_ids):
            cutoff = dt.date(year, 10, 15)
            metrics = resume_through_date(pid, cutoff, seasons, stints)
            if metrics["seasons"] <= 0:
                continue
            teams = sorted(
                {
                    s.get("team_abbr")
                    or TEAM_META.get(s["team_id"], {}).get("abbr", "?")
                    for s in stints
                    if s["person_id"] == pid
                    and (parse_date(s["start"]) or dt.date(1900, 1, 1))
                    <= cutoff
                }
            )
            active_rows.append(
                {
                    "person_id": pid,
                    "name": names.get(pid, pid),
                    "teams": teams,
                    **metrics,
                }
            )

        if not active_rows:
            continue

        scores = composite_scores(active_rows, weights)
        ranks = rank_descending(scores)
        cats = category_ranks(active_rows)
        for row, score, rank, cat in zip(active_rows, scores, ranks, cats):
            row["composite"] = score
            row["rank"] = rank
            row["category_ranks"] = cat

        active_rows.sort(key=lambda r: r["rank"])

        exit_stints = _offseason_exits(stints, year)
        exit_profiles: list[dict[str, Any]] = []
        for stint in exit_stints:
            end = parse_date(stint["end"]) or dt.date(year + 1, 1, 1)
            metrics = resume_through_date(stint["person_id"], end, seasons, stints)
            if metrics["seasons"] <= 0:
                continue
            exit_profiles.append(
                {
                    "person_id": stint["person_id"],
                    "name": stint["name"],
                    "team_abbr": stint.get("team_abbr"),
                    "exit_type": stint.get("exit_type"),
                    "exit_date": stint["end"],
                    "seasons": metrics["seasons"],
                    "payroll_efficiency": metrics["payroll_efficiency"],
                    "win_pct": metrics["win_pct"],
                    "world_series_rate": metrics["world_series_rate"],
                    "playoff_depth_rate": metrics["playoff_depth_rate"],
                }
            )

        years.append(
            {
                "season": year,
                "active_gm_count": len(active_rows),
                "job_security": {
                    "exits_in_cycle": len(exit_profiles),
                    "exits": exit_profiles,
                },
                "leaderboard": [
                    {
                        "rank": r["rank"],
                        "person_id": r["person_id"],
                        "name": r["name"],
                        "teams": r["teams"],
                        "composite": r["composite"],
                        "category_ranks": r["category_ranks"],
                        "seasons": r["seasons"],
                        "win_pct": r["win_pct"],
                        "payroll_efficiency": r["payroll_efficiency"],
                        "world_series_rate": r["world_series_rate"],
                        "pennants_rate": r["pennants_rate"],
                        "playoff_depth_rate": r["playoff_depth_rate"],
                        "draft_vos": r["draft_vos"],
                        "trade_net_rate": r["trade_net_rate"],
                    }
                    for r in active_rows
                ],
            }
        )

    cycles_with_exits = sum(1 for y in years if y["job_security"]["exits_in_cycle"] > 0)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "window": [WINDOW_START, last_complete],
        "weights": weights,
        "framing": (
            "Rate-based yearly ranks among active GMs, plus who left that offseason."
        ),
        "summary": {
            "years": len(years),
            "cycles_with_exits": cycles_with_exits,
        },
        "years": years,
    }



# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=WINDOW_START)
    parser.add_argument("--end", type=int, default=WINDOW_END)
    parser.add_argument("--pause", type=float, default=0.35)
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="reuse data/team_seasons.json instead of refetching",
    )
    parser.add_argument("--skip-payroll", action="store_true")
    args = parser.parse_args()

    weights_file = load_weights()
    weights = weights_file["components"]
    min_seasons = int(weights_file.get("min_seasons_for_full_rank", 3))
    tenure_prior = int(weights_file.get("tenure_prior_seasons", 4))

    seasons_path = DATA / "team_seasons.json"
    seasons: list[dict[str, Any]] | None = None
    if args.use_cache and seasons_path.exists():
        cached = json.loads(seasons_path.read_text(encoding="utf-8"))["seasons"]
        if cached and "playoff_depth" in cached[0]:
            print("loading cached team seasons", file=sys.stderr)
            seasons = cached
        else:
            print("cache missing playoff_depth; refetching", file=sys.stderr)

    if seasons is None:
        session = _session()
        print("fetching team seasons from MLB Stats API", file=sys.stderr)
        seasons = build_team_seasons(session, args.start, args.end, args.pause)
        payroll_meta: dict[str, Any] = {"source": None}
        if not args.skip_payroll:
            print("scraping payroll from Baseball Cube", file=sys.stderr)
            payroll_meta = attach_payroll(session, seasons, args.pause)
        payload = {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "window": [args.start, args.end],
            "season_count": len(seasons),
            "payroll": payroll_meta,
            "seasons": seasons,
        }
        write_json(seasons_path, payload)

    stints = json.loads((DATA / "gm_tenures.json").read_text(encoding="utf-8"))
    if isinstance(stints, dict):
        stints = stints["stints"]

    print("building franchise index", file=sys.stderr)
    franchise = aggregate_franchise(seasons, weights)
    write_json(DATA / "franchise_index.json", franchise)

    print("building GM career index", file=sys.stderr)
    gm_index = build_gm_index(seasons, stints, weights, min_seasons, tenure_prior)
    write_json(DATA / "gm_index.json", gm_index)

    print("building exit resumes", file=sys.stderr)
    exits = build_exit_resumes(seasons, stints, weights)
    write_json(DATA / "exit_resumes.json", exits)

    print("building yearly job-security index", file=sys.stderr)
    yearly = build_yearly_index(seasons, stints, weights)
    write_json(DATA / "yearly_index.json", yearly)

    top_f = franchise["franchises"][0] if franchise["franchises"] else None
    top_g = gm_index["gms"][0] if gm_index["gms"] else None
    print(
        f"Top franchise: {top_f['team_abbr'] if top_f else '?'} "
        f"(#{top_f['rank'] if top_f else '?'})",
        file=sys.stderr,
    )
    print(
        f"Top GM: {top_g['name'] if top_g else '?'} "
        f"/ {gm_index['gm_count']} ranked",
        file=sys.stderr,
    )
    print(f"Exits: {exits['exit_count']}", file=sys.stderr)
    print(
        f"Yearly seasons: {yearly['summary']['years']}; "
        f"cycles with exits: {yearly['summary']['cycles_with_exits']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
