#!/usr/bin/env python3
"""Build data/moves.json for The Cashman Index.

Two stages, both in this one script:

  1. Pull New York Yankees transactions from the MLB Stats API for the last N
     years and fold the per-player rows into one record per front-office move.
  2. Attach two calculated fields per move using Baseball Reference WAR
     (downloaded via pybaseball):

       surplus_value    = (WAR the acquired players produced for the Yankees
                          after the move) x $/WAR benchmark - salary paid
       net_war_exchange = that same acquired WAR
                          - WAR the departing players produced elsewhere
                            after the move

Usage:
    python scripts/build_moves.py                  # fetch + enrich, write data/moves.json
    python scripts/build_moves.py --no-war         # transactions only, scores left null
    python scripts/build_moves.py --use-cache      # re-run enrichment on cached transactions
    python scripts/build_moves.py --years 5 --dollars-per-war 9000000

Requires: pip install -r scripts/requirements.txt
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent

YANKEES_MLBAM_ID = 147
YANKEES_BREF_CODE = "NYA"

STATS_API = "https://statsapi.mlb.com/api/v1/transactions"

# ~$8M per win is the commonly cited free-agent market rate in recent seasons.
# Override with --dollars-per-war to re-run the whole index at a different price.
DEFAULT_DOLLARS_PER_WAR = 8_000_000

# Transaction typeCodes that represent an actual front-office decision. Everything
# else the API returns (options, recalls, status changes, uniform numbers, DFAs)
# is roster paperwork and would drown out the real moves. Pass --all-types to keep
# everything.
FRONT_OFFICE_TYPE_CODES = {
    "TR",   # Trade
    "SFA",  # Signed as Free Agent
    "SGN",  # Signed
    "CLW",  # Claimed off Waivers
    "PUR",  # Purchased
    "SE",   # Selected (incl. Rule 5)
    "REL",  # Released
    "FA",   # Elected / declared free agency
    "OUT",  # Outrighted off the 40-man
}

# Type codes where the player is leaving the organization even though the API
# still lists the Yankees in the `team` field.
DEPARTURE_TYPE_CODES = {"FA", "REL", "OUT"}


# ---------------------------------------------------------------------------
# Stage 1: transactions
# ---------------------------------------------------------------------------


def fetch_transactions(start: dt.date, end: dt.date, pause: float = 0.5) -> list[dict]:
    """Fetch Yankees transactions, one calendar year per request."""
    rows: list[dict] = []
    session = requests.Session()
    session.headers["User-Agent"] = "the-cashman-index/0.1 (personal project)"

    for year in range(start.year, end.year + 1):
        window_start = max(start, dt.date(year, 1, 1))
        window_end = min(end, dt.date(year, 12, 31))
        params = {
            "teamId": YANKEES_MLBAM_ID,
            "startDate": window_start.strftime("%m/%d/%Y"),
            "endDate": window_end.strftime("%m/%d/%Y"),
        }
        print(f"  fetching {window_start} .. {window_end}", file=sys.stderr)
        response = session.get(STATS_API, params=params, timeout=60)
        response.raise_for_status()
        year_rows = response.json().get("transactions", []) or []
        print(f"    {len(year_rows)} transaction rows", file=sys.stderr)
        rows.extend(year_rows)
        time.sleep(pause)

    return rows


def _row_date(row: dict) -> str | None:
    """The date the move was made.

    `date` (announcement) comes first rather than `effectiveDate`, for two
    reasons: it is what "when did Cashman make this move" actually means, and
    it is identical across every row of a trade. Effective dates can drift a
    day between players in the same deal, which would split one trade into two.
    """
    for key in ("date", "effectiveDate", "resolutionDate"):
        value = row.get(key)
        if value:
            return str(value)[:10]
    return None


def _direction(row: dict) -> str:
    """'acquired' if the player is joining the Yankees, else 'sent_away'."""
    if row.get("typeCode") in DEPARTURE_TYPE_CODES:
        return "sent_away"
    to_team = (row.get("team") or {}).get("id")
    if to_team == YANKEES_MLBAM_ID:
        return "acquired"
    from_team = (row.get("fromTeam") or {}).get("id")
    if from_team == YANKEES_MLBAM_ID:
        return "sent_away"
    # Neither side is the Yankees (minor-league affiliate rows can look like
    # this). Treat as an acquisition so the row is at least visible.
    return "acquired"


def _group_key(row: dict) -> tuple:
    """Rows that belong to the same real-world move share a key.

    A trade shows up as one API row per player, so trades are grouped by
    (date, the other club). Everything else stands on its own.
    """
    date = _row_date(row)
    type_code = row.get("typeCode")
    if type_code == "TR":
        to_team = (row.get("team") or {}).get("id")
        from_team = (row.get("fromTeam") or {}).get("id")
        counterparty = from_team if to_team == YANKEES_MLBAM_ID else to_team
        return (date, "TR", counterparty)
    return (date, type_code, row.get("id"))


def _make_move_id(date: str, type_code: str, player_ids: Iterable[int], extra: Any) -> str:
    digest = hashlib.sha1(
        f"{date}|{type_code}|{sorted(player_ids)}|{extra}".encode()
    ).hexdigest()[:6]
    return f"{date}-{type_code}-{digest}"


def _counterparty_name(rows: list[dict]) -> str | None:
    for row in rows:
        for side in ("team", "fromTeam"):
            club = row.get(side) or {}
            if club.get("id") and club.get("id") != YANKEES_MLBAM_ID:
                return club.get("name")
    return None


def _summarize(type_code: str, type_desc: str, rows: list[dict],
               acquired: list[dict], sent_away: list[dict]) -> str:
    if type_code == "TR":
        other = _counterparty_name(rows) or "another club"
        parts = []
        if acquired:
            parts.append("acquired " + ", ".join(p["name"] for p in acquired))
        if sent_away:
            parts.append("sent " + ", ".join(p["name"] for p in sent_away))
        if parts:
            return f"Trade with {other}: " + "; ".join(parts)

    # For non-trades the API's own sentence is already the cleanest summary.
    descriptions = [
        str(row.get("description")).strip().rstrip(".")
        for row in rows
        if row.get("description")
    ]
    if descriptions:
        return "; ".join(dict.fromkeys(descriptions))

    names = ", ".join(p["name"] for p in acquired + sent_away) or "unknown player"
    return f"{type_desc}: {names}"


def group_into_moves(rows: list[dict], all_types: bool = False) -> list[dict]:
    """Fold per-player transaction rows into one record per move."""
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        if not _row_date(row):
            continue
        if not all_types and row.get("typeCode") not in FRONT_OFFICE_TYPE_CODES:
            continue
        buckets[_group_key(row)].append(row)

    moves: list[dict] = []
    for key, group in buckets.items():
        date = key[0]
        type_code = key[1] or "UNK"
        type_desc = group[0].get("typeDesc") or type_code

        acquired: list[dict] = []
        sent_away: list[dict] = []
        for row in group:
            person = row.get("person") or {}
            if not person.get("id"):
                continue
            entry = {"mlbam_id": person["id"], "name": person.get("fullName") or "Unknown"}
            bucket = acquired if _direction(row) == "acquired" else sent_away
            if not any(p["mlbam_id"] == entry["mlbam_id"] for p in bucket):
                bucket.append(entry)

        player_ids = [p["mlbam_id"] for p in acquired + sent_away]
        moves.append(
            {
                "move_id": _make_move_id(date, type_code, player_ids, key[2]),
                "move_date": date,
                "move_type": type_desc,
                "move_type_code": type_code,
                "counterparty": _counterparty_name(group),
                "summary": _summarize(type_code, type_desc, group, acquired, sent_away),
                "players_acquired": acquired,
                "players_sent_away": sent_away,
                "salary_paid": None,
                "salary_source": None,
                "contract_years": None,
                "contract_through": None,
                "contract_active": None,
                "surplus_value": None,
                "net_war_exchange": None,
                "war_acquired": None,
                "war_sent_away": None,
            }
        )

    moves.sort(key=lambda m: (m["move_date"], m["move_id"]), reverse=True)
    return moves


# ---------------------------------------------------------------------------
# Stage 2: WAR + salary enrichment
# ---------------------------------------------------------------------------


def _effective_season(move_date: str) -> int:
    """First season whose Yankees playing time counts as 'after the move'.

    A move made in November or December belongs to the following season — this
    also stops a re-signed free agent's pre-signing Yankees WAR from counting.
    In-season moves use the current year, and the Baseball Reference team/stint
    split then keeps only the post-move portion.
    """
    year, month = int(move_date[:4]), int(move_date[5:7])
    return year + 1 if month >= 11 else year


def load_bref_war() -> dict[int, list[dict]]:
    """Player-season WAR and salary from Baseball Reference, keyed by MLBAM id.

    Each entry is one player-season-stint, so a mid-season trade splits into a
    Yankees row and a non-Yankees row.
    """
    try:
        from pybaseball import bwar_bat, bwar_pitch
    except ImportError:
        raise SystemExit(
            "pybaseball is not installed.\n"
            "  pip install -r scripts/requirements.txt\n"
            "Or re-run with --no-war to build transactions only."
        )

    print("  downloading Baseball Reference WAR tables...", file=sys.stderr)
    frames = [bwar_bat(return_all=True), bwar_pitch(return_all=True)]

    index: dict[int, list[dict]] = defaultdict(list)
    for frame in frames:
        columns = set(frame.columns)
        missing = {"mlb_ID", "year_ID", "team_ID", "WAR"} - columns
        if missing:
            raise SystemExit(f"Unexpected pybaseball schema, missing columns: {sorted(missing)}")
        has_salary = "salary" in columns

        for record in frame.to_dict("records"):
            mlbam = record.get("mlb_ID")
            war = record.get("WAR")
            year = record.get("year_ID")
            try:
                mlbam = int(mlbam)
                year = int(year)
                war = float(war)
            except (TypeError, ValueError):
                continue  # unmatched or non-numeric rows

            salary = None
            if has_salary:
                try:
                    salary = float(record["salary"])
                except (TypeError, ValueError, KeyError):
                    salary = None

            index[mlbam].append(
                {
                    "year": year,
                    "team": str(record.get("team_ID") or ""),
                    "war": war,
                    "salary": salary,
                }
            )

    print(f"  indexed {len(index)} players", file=sys.stderr)
    return index


def _sum_seasons(index: dict[int, list[dict]], mlbam_id: int, from_season: int,
                 yankees: bool) -> tuple[float, float | None]:
    """Sum (WAR, salary) over seasons at/after `from_season`.

    `yankees=True` counts only Yankees stints — what an acquired player produced
    for the club. `yankees=False` counts only non-Yankees stints — what a
    departing player produced once he was gone.
    """
    war_total = 0.0
    salary_total = 0.0
    saw_salary = False
    for season in index.get(mlbam_id, []):
        if season["year"] < from_season:
            continue
        is_yankees = season["team"] == YANKEES_BREF_CODE
        if is_yankees != yankees:
            continue
        war_total += season["war"]
        if season["salary"] is not None:
            salary_total += season["salary"]
            saw_salary = True
    return round(war_total, 2), (round(salary_total, 2) if saw_salary else None)


def enrich_moves(moves: list[dict], index: dict[int, list[dict]],
                 dollars_per_war: float) -> None:
    """Fill in WAR, salary and both scores. Mutates `moves` in place."""
    for move in moves:
        first_season = _effective_season(move["move_date"])

        war_acquired = 0.0
        salary_acquired = 0.0
        saw_salary = False
        for player in move["players_acquired"]:
            war, salary = _sum_seasons(index, player["mlbam_id"], first_season, yankees=True)
            player["war_after_move"] = war
            war_acquired += war
            if salary is not None:
                salary_acquired += salary
                saw_salary = True

        war_sent_away = 0.0
        for player in move["players_sent_away"]:
            war, _ = _sum_seasons(index, player["mlbam_id"], first_season, yankees=False)
            player["war_after_move"] = war
            war_sent_away += war

        move["war_acquired"] = round(war_acquired, 2)
        move["war_sent_away"] = round(war_sent_away, 2)
        move["net_war_exchange"] = round(war_acquired - war_sent_away, 2)

        if move["salary_paid"] is None and saw_salary:
            move["salary_paid"] = round(salary_acquired, 2)
            move["salary_source"] = "bref"

        if move["salary_paid"] is not None:
            move["surplus_value"] = round(
                war_acquired * dollars_per_war - move["salary_paid"], 2
            )
        else:
            # No salary figure means no honest surplus number. Leave it null
            # rather than pretending the move was free.
            move["surplus_value"] = None


# ---------------------------------------------------------------------------
# Manual salary / contract overrides
# ---------------------------------------------------------------------------


def _days_apart(left: str, right: str) -> int:
    try:
        a = dt.date.fromisoformat(left)
        b = dt.date.fromisoformat(right)
    except ValueError:
        return 10**6
    return abs((a - b).days)


def apply_overrides(moves: list[dict], overrides_path: Path,
                    date_tolerance: int = 14) -> tuple[int, list[str]]:
    """Layer hand-entered contract terms on top of the scraped data.

    The MLB Stats API carries no contract information at all, and Baseball
    Reference salaries thin out for recent seasons, so `data/salary_overrides.json`
    is where real contract totals get recorded. Each entry matches either by
    `move_id` or by `{player, date}`.

    Hand-entered dates come from news coverage, which routinely disagrees with
    the league's filing date by a few days, so a player match within
    `date_tolerance` days counts. Returns (applied, unmatched labels) — an
    override that matches nothing is a silent wrong number on the site
    otherwise, so callers are expected to surface the unmatched list.
    """
    if not overrides_path.exists():
        return 0, []

    entries = json.loads(overrides_path.read_text())
    applied = 0
    unmatched: list[str] = []

    for entry in entries:
        match = entry.get("match") or {}
        target_id = entry.get("move_id")
        player = (match.get("player") or "").strip().lower()
        date = match.get("date")

        if not target_id and not (player and date):
            continue  # comment-only entry

        # Prefer an exact date hit; fall back to the nearest within tolerance so
        # one override can never land on two different moves.
        candidates: list[tuple[int, dict]] = []
        for move in moves:
            if target_id:
                if move["move_id"] == target_id:
                    candidates.append((0, move))
                continue
            names = [
                p["name"].lower()
                for p in move["players_acquired"] + move["players_sent_away"]
            ]
            if player not in names:
                continue
            distance = _days_apart(move["move_date"], date)
            if distance <= date_tolerance:
                candidates.append((distance, move))

        if not candidates:
            unmatched.append(target_id or f"{match.get('player')} @ {date}")
            continue

        candidates.sort(key=lambda pair: pair[0])
        move = candidates[0][1]

        if "salary_paid" in entry:
            move["salary_paid"] = entry["salary_paid"]
            move["salary_source"] = "override"
        if "contract_years" in entry:
            move["contract_years"] = entry["contract_years"]
        if "contract_through" in entry:
            # A deal still being paid has banked only part of the WAR it was
            # bought for, so its surplus is a midpoint, not a verdict. Flag it
            # so the site can say so instead of calling Judge a $200M mistake.
            move["contract_through"] = entry["contract_through"]
            move["contract_active"] = entry["contract_through"] >= dt.date.today().year
        applied += 1

    return applied, unmatched


# ---------------------------------------------------------------------------


def public_fields(move: dict) -> dict:
    """The shape the web app consumes."""
    return {
        "move_id": move["move_id"],
        "move_date": move["move_date"],
        "move_type": move["move_type"],
        "summary": move["summary"],
        "players_acquired": move["players_acquired"],
        "players_sent_away": move["players_sent_away"],
        "salary_paid": move["salary_paid"],
        "contract_years": move["contract_years"],
        "contract_active": move["contract_active"],
        "surplus_value": move["surplus_value"],
        "net_war_exchange": move["net_war_exchange"],
        "war_acquired": move["war_acquired"],
        "war_sent_away": move["war_sent_away"],
        "salary_source": move["salary_source"],
        "counterparty": move["counterparty"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", type=int, default=10,
                        help="how many years back to pull (default: 10)")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "moves.json")
    parser.add_argument("--cache", type=Path,
                        default=REPO_ROOT / "data" / "transactions.raw.json",
                        help="where raw API rows are stored")
    parser.add_argument("--use-cache", action="store_true",
                        help="reuse the cached transactions instead of calling the API")
    parser.add_argument("--overrides", type=Path,
                        default=REPO_ROOT / "data" / "salary_overrides.json")
    parser.add_argument("--no-war", action="store_true",
                        help="skip pybaseball; leave the calculated fields null")
    parser.add_argument("--dollars-per-war", type=float, default=DEFAULT_DOLLARS_PER_WAR)
    parser.add_argument("--all-types", action="store_true",
                        help="keep every transaction type, including roster paperwork")
    parser.add_argument("--strict-overrides", action="store_true",
                        help="exit non-zero if any override matched no move (for CI)")
    args = parser.parse_args()

    today = dt.date.today()
    start = today.replace(year=today.year - args.years)

    if args.use_cache:
        if not args.cache.exists():
            print(f"No cache at {args.cache}; run once without --use-cache.", file=sys.stderr)
            return 1
        print(f"Reading cached transactions from {args.cache}", file=sys.stderr)
        rows = json.loads(args.cache.read_text())
    else:
        print(f"Fetching Yankees transactions {start} .. {today}", file=sys.stderr)
        rows = fetch_transactions(start, today)
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        args.cache.write_text(json.dumps(rows, indent=2))
        print(f"Cached {len(rows)} rows to {args.cache}", file=sys.stderr)

    moves = group_into_moves(rows, all_types=args.all_types)
    print(f"Grouped into {len(moves)} moves", file=sys.stderr)

    applied, unmatched = apply_overrides(moves, args.overrides)
    if applied:
        print(f"Applied {applied} manual contract override(s)", file=sys.stderr)

    if args.no_war:
        print("Skipping WAR enrichment (--no-war)", file=sys.stderr)
    else:
        index = load_bref_war()
        enrich_moves(moves, index, args.dollars_per_war)
        # Overrides win over Baseball Reference salaries, so re-apply and
        # recompute surplus for anything the user specified by hand.
        if applied:
            apply_overrides(moves, args.overrides)
            for move in moves:
                if move["salary_source"] == "override" and move["war_acquired"] is not None:
                    move["surplus_value"] = round(
                        move["war_acquired"] * args.dollars_per_war - move["salary_paid"], 2
                    )

    # An override that matched nothing means a contract you meant to record is
    # missing from the site. Loud, and non-zero exit under --strict-overrides so
    # CI can fail on it.
    if unmatched:
        print(f"\nWARNING: {len(unmatched)} override(s) matched no move:", file=sys.stderr)
        for label in unmatched:
            print(f"  - {label}", file=sys.stderr)
        print("Check the player spelling and date against data/moves.json.\n",
              file=sys.stderr)

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "data_source": "mlb-stats-api+bref",
        "season_range": [start.year, today.year],
        "dollars_per_war": args.dollars_per_war,
        "move_count": len(moves),
        "moves": [public_fields(m) for m in moves],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")

    scored = [m for m in moves if m["net_war_exchange"] is not None]
    priced = [m for m in moves if m["surplus_value"] is not None]
    print(f"\nWrote {len(moves)} moves to {args.out}", file=sys.stderr)
    print(f"  {len(scored)} scored (net WAR exchange)", file=sys.stderr)
    print(f"  {len(priced)} priced (surplus value; the rest have no salary on file)",
          file=sys.stderr)
    if priced:
        best = max(priced, key=lambda m: m["surplus_value"])
        worst = min(priced, key=lambda m: m["surplus_value"])
        print(f"  best:  {best['move_date']} {best['summary'][:60]}"
              f" ({best['surplus_value']:+,.0f})", file=sys.stderr)
        print(f"  worst: {worst['move_date']} {worst['summary'][:60]}"
              f" ({worst['surplus_value']:+,.0f})", file=sys.stderr)

    if unmatched and args.strict_overrides:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
