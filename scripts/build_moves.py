#!/usr/bin/env python3
"""Build data/moves.json for the Front Office Index (single-club convenience).

Prefer scripts/build_league_moves.py for all 30 clubs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify_moves import classify_move
from team_codes import (
    TEAM_BREF_CODES,
    YANKEES_MLBAM_ID,
    bref_codes,
    team_abbr,
    team_name,
)

# Back-compat alias for tests / older imports.
YANKEES_BREF_CODES = TEAM_BREF_CODES[YANKEES_MLBAM_ID]

STATS_API = "https://statsapi.mlb.com/api/v1/transactions"

# ~$8M per win is the commonly cited free-agent market rate in recent seasons.
# Override with --dollars-per-war to re-run the whole index at a different price.
DEFAULT_DOLLARS_PER_WAR = 8_000_000

AS_OF = dt.date(2026, 8, 2)  # overwritten from data/weights.json


def load_as_of() -> dt.date:
    """Pin scored outputs to weights.json as_of (never wall-clock)."""
    global AS_OF
    path = REPO_ROOT / "data" / "weights.json"
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("as_of"):
            AS_OF = dt.date.fromisoformat(str(raw["as_of"])[:10])
    return AS_OF

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


def fetch_transactions(
    start: dt.date,
    end: dt.date,
    team_id: int = YANKEES_MLBAM_ID,
    pause: float = 0.35,
) -> list[dict]:
    """Fetch one club's transactions, one calendar year per request."""
    # Imported here, not at module scope, so the grouping and scoring logic can
    # be imported and tested with no third-party packages installed at all.
    import requests

    rows: list[dict] = []
    session = requests.Session()
    session.headers["User-Agent"] = "front-office-index/0.1 (personal project)"
    label = team_abbr(team_id)

    for year in range(start.year, end.year + 1):
        window_start = max(start, dt.date(year, 1, 1))
        window_end = min(end, dt.date(year, 12, 31))
        params = {
            "teamId": team_id,
            "startDate": window_start.strftime("%m/%d/%Y"),
            "endDate": window_end.strftime("%m/%d/%Y"),
        }
        print(f"  {label} {window_start} .. {window_end}", file=sys.stderr)
        response = session.get(STATS_API, params=params, timeout=60)
        response.raise_for_status()
        year_rows = response.json().get("transactions", []) or []
        print(f"    {len(year_rows)} rows", file=sys.stderr)
        rows.extend(year_rows)
        time.sleep(pause)

    return rows


def _row_date(row: dict) -> str | None:
    """The date the move was made.

    `date` (announcement) comes first rather than `effectiveDate`, for two
    it is identical across every row of a trade. Effective dates can drift a
    day between players in the same deal, which would split one trade into two.
    """
    for key in ("date", "effectiveDate", "resolutionDate"):
        value = row.get(key)
        if value:
            return str(value)[:10]
    return None


def _direction(row: dict, team_id: int = YANKEES_MLBAM_ID) -> str:
    """'acquired' if the player is joining the focal club, else 'sent_away'."""
    if row.get("typeCode") in DEPARTURE_TYPE_CODES:
        return "sent_away"
    to_team = (row.get("team") or {}).get("id")
    if to_team == team_id:
        return "acquired"
    from_team = (row.get("fromTeam") or {}).get("id")
    if from_team == team_id:
        return "sent_away"
    return "acquired"


def _counterparty_id(rows: list[dict], team_id: int = YANKEES_MLBAM_ID) -> int | None:
    for row in rows:
        for side in ("team", "fromTeam"):
            club = row.get(side) or {}
            cid = club.get("id")
            if cid and cid != team_id:
                return int(cid)
    return None


def _group_key(row: dict, team_id: int = YANKEES_MLBAM_ID) -> tuple:
    """Rows that belong to the same real-world move share a key.

    Trades group by counterparty. Non-trades group by player identity — never
    the Stats API row ``id``, which duplicates the same signing/release.
    """
    date = _row_date(row)
    type_code = row.get("typeCode")
    if type_code == "TR":
        to_team = (row.get("team") or {}).get("id")
        from_team = (row.get("fromTeam") or {}).get("id")
        counterparty = from_team if to_team == team_id else to_team
        return (date, "TR", counterparty)
    person_id = (row.get("person") or {}).get("id")
    direction = _direction(row, team_id)
    # Content key (date, type, direction, player) — merges redundant API rows.
    return (date, type_code, direction, person_id)


def _make_move_id(
    date: str, type_code: str, player_ids: Iterable[int], extra: Any,
    team_id: int = YANKEES_MLBAM_ID,
) -> str:
    digest = hashlib.sha1(
        f"{team_id}|{date}|{type_code}|{sorted(player_ids)}|{extra}".encode()
    ).hexdigest()[:6]
    return f"{team_id}-{date}-{type_code}-{digest}"


def _counterparty_name(rows: list[dict], team_id: int = YANKEES_MLBAM_ID) -> str | None:
    for row in rows:
        for side in ("team", "fromTeam"):
            club = row.get(side) or {}
            if club.get("id") and club.get("id") != team_id:
                return club.get("name")
    return None


def _summarize(
    type_code: str,
    type_desc: str,
    rows: list[dict],
    acquired: list[dict],
    sent_away: list[dict],
    team_id: int = YANKEES_MLBAM_ID,
) -> str:
    if type_code == "TR":
        other = _counterparty_name(rows, team_id) or "another club"
        parts = []
        if acquired:
            parts.append("acquired " + ", ".join(p["name"] for p in acquired))
        if sent_away:
            parts.append("sent " + ", ".join(p["name"] for p in sent_away))
        if parts:
            return f"Trade with {other}: " + "; ".join(parts)

    descriptions = [
        str(row.get("description")).strip().rstrip(".")
        for row in rows
        if row.get("description")
    ]
    if descriptions:
        return "; ".join(dict.fromkeys(descriptions))

    names = ", ".join(p["name"] for p in acquired + sent_away) or "unknown player"
    return f"{type_desc}: {names}"


def group_into_moves(
    rows: list[dict],
    all_types: bool = False,
    team_id: int = YANKEES_MLBAM_ID,
) -> list[dict]:
    """Fold per-player transaction rows into one record per move for team_id."""
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        if not _row_date(row):
            continue
        if not all_types and row.get("typeCode") not in FRONT_OFFICE_TYPE_CODES:
            continue
        buckets[_group_key(row, team_id)].append(row)

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
            bucket = acquired if _direction(row, team_id) == "acquired" else sent_away
            if not any(p["mlbam_id"] == entry["mlbam_id"] for p in bucket):
                bucket.append(entry)

        player_ids = [p["mlbam_id"] for p in acquired + sent_away]
        cp_id = _counterparty_id(group, team_id) if type_code == "TR" else None
        moves.append(
            {
                "move_id": _make_move_id(date, type_code, player_ids, key[2], team_id),
                "team_id": team_id,
                "team_abbr": team_abbr(team_id),
                "team_name": team_name(team_id),
                "move_date": date,
                "move_type": type_desc,
                "move_type_code": type_code,
                "counterparty": _counterparty_name(group, team_id),
                "counterparty_id": cp_id,
                "summary": _summarize(
                    type_code, type_desc, group, acquired, sent_away, team_id
                ),
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
    return _dedupe_non_trade_moves(moves)


def _dedupe_non_trade_moves(moves: list[dict]) -> list[dict]:
    """Merge non-trade FO moves that share date/type/player names.

    Stats API row ids used to split one signing into many; content identity
    (date, type, acquired names, sent names) collapses those duplicates.
    Trades stay grouped by counterparty only.
    """
    seen: dict[tuple, dict] = {}
    out: list[dict] = []
    for move in moves:
        if move.get("move_type_code") == "TR":
            out.append(move)
            continue
        key = (
            move["move_date"],
            move.get("move_type_code") or move.get("move_type"),
            tuple(sorted(p.get("name") or "" for p in move.get("players_acquired") or [])),
            tuple(sorted(p.get("name") or "" for p in move.get("players_sent_away") or [])),
        )
        if key in seen:
            continue
        seen[key] = move
        out.append(move)
    out.sort(key=lambda m: (m["move_date"], m["move_id"]), reverse=True)
    return out


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

            # pandas fills blanks with NaN, and float(nan) succeeds. Left alone,
            # a single NaN poisons every sum it touches and json.dump writes the
            # literal `NaN`, which is not valid JSON and breaks the web build.
            if math.isnan(war):
                continue

            salary = None
            if has_salary:
                try:
                    salary = float(record["salary"])
                except (TypeError, ValueError, KeyError):
                    salary = None
                else:
                    if math.isnan(salary):
                        salary = None

            index[mlbam].append(
                {
                    "year": year,
                    "team": str(record.get("team_ID") or ""),
                    "war": war,
                    "salary": salary,
                }
            )

    # A team-code mismatch would zero out every acquired-player score while
    # still producing a plausible-looking file, so fail loudly instead.
    yankees_rows = sum(
        1
        for seasons in index.values()
        for season in seasons
        if season["team"] in YANKEES_BREF_CODES
    )
    if not yankees_rows:
        observed = sorted({s["team"] for seasons in index.values() for s in seasons})
        raise SystemExit(
            "No Baseball Reference rows matched the Yankees team codes "
            f"{sorted(YANKEES_BREF_CODES)}. Add the right code to "
            f"YANKEES_BREF_CODES. Codes present in the data: {observed}"
        )

    print(f"  indexed {len(index)} players, {yankees_rows} Yankees player-seasons",
          file=sys.stderr)
    return index


def _sum_seasons(
    index: dict[int, list[dict]],
    mlbam_id: int,
    *,
    club_codes: frozenset[str] | None = None,
    for_club: bool | None = None,
    yankees: bool | None = None,
    from_season: int | None = None,
    before_season: int | None = None,
    through_season: int | None = None,
) -> tuple[float, float | None]:
    """Sum (WAR, salary) with optional season / club filters.

    `for_club=True` → focal-club stints only; `False` → elsewhere; `None` → any.
    `yankees=` is a back-compat alias for `for_club=` (Yankees codes).
    """
    codes = club_codes or YANKEES_BREF_CODES
    if for_club is None and yankees is not None:
        for_club = yankees
    war_total = 0.0
    salary_total = 0.0
    saw_salary = False
    for season in index.get(mlbam_id, []):
        year = season["year"]
        if from_season is not None and year < from_season:
            continue
        if before_season is not None and year >= before_season:
            continue
        if through_season is not None and year > through_season:
            continue
        is_club = season["team"] in codes
        if for_club is not None and is_club != for_club:
            continue
        war = season["war"]
        if war is not None and not math.isnan(war):
            war_total += war
        salary = season["salary"]
        if salary is not None and not math.isnan(salary):
            salary_total += salary
            saw_salary = True
    return round(war_total, 2), (round(salary_total, 2) if saw_salary else None)


def _last_club_season_from(
    index: dict[int, list[dict]],
    mlbam_id: int,
    from_season: int,
    club_codes: frozenset[str],
) -> int | None:
    """Last focal-club season at/after from_season."""
    years = [
        s["year"]
        for s in index.get(mlbam_id, [])
        if s["year"] >= from_season and s["team"] in club_codes
    ]
    return max(years) if years else None


def _last_yankees_season_from(
    index: dict[int, list[dict]], mlbam_id: int, from_season: int
) -> int | None:
    return _last_club_season_from(index, mlbam_id, from_season, YANKEES_BREF_CODES)


def enrich_moves(
    moves: list[dict],
    index: dict[int, list[dict]],
    dollars_per_war: float,
    team_id: int | None = None,
    *,
    through_season: int | None = None,
) -> None:
    """Fill in WAR splits, salary and both scores. Mutates `moves` in place.

    Closed-market net WAR (symmetric horizons):
      war_acquired  = WAR for the focal club after the move (through leave)
      war_sent_away = WAR for the *receiving* club after the move (not “anywhere
                      forever”). When counterparty codes are unknown, fall back
                      to non-focal WAR (legacy asymmetry).
    Optional ``through_season`` caps both sides (point-in-time / as-of resumes).
    ``war_after_exit_acquired`` remains diagnostic only (not in the net).
    """
    for move in moves:
        tid = team_id if team_id is not None else move.get("team_id", YANKEES_MLBAM_ID)
        codes = bref_codes(tid)
        first_season = _effective_season(move["move_date"])
        cp_id = move.get("counterparty_id")
        try:
            recv_codes = bref_codes(int(cp_id)) if cp_id is not None else None
        except (KeyError, TypeError, ValueError):
            recv_codes = None

        war_acquired = 0.0
        war_prior_in = 0.0
        war_after_exit = 0.0
        salary_acquired = 0.0
        saw_salary = False
        for player in move["players_acquired"]:
            mid = player["mlbam_id"]
            prior, _ = _sum_seasons(index, mid, before_season=first_season)
            during, salary = _sum_seasons(
                index,
                mid,
                from_season=first_season,
                through_season=through_season,
                club_codes=codes,
                for_club=True,
            )
            last_club = _last_club_season_from(index, mid, first_season, codes)
            if last_club is not None:
                after_from = last_club + 1
                if through_season is not None and after_from > through_season:
                    after = 0.0
                else:
                    after, _ = _sum_seasons(
                        index,
                        mid,
                        from_season=after_from,
                        through_season=through_season,
                        club_codes=codes,
                        for_club=False,
                    )
            else:
                after = 0.0
            player["war_prior"] = prior
            player["war_after_move"] = during
            player["war_during"] = during
            player["war_after_exit"] = after
            war_prior_in += prior
            war_acquired += during
            war_after_exit += after
            if salary is not None:
                salary_acquired += salary
                saw_salary = True

        war_sent_away = 0.0
        war_prior_out = 0.0
        for player in move["players_sent_away"]:
            mid = player["mlbam_id"]
            prior, _ = _sum_seasons(
                index,
                mid,
                before_season=first_season,
                club_codes=codes,
                for_club=True,
            )
            # Symmetric debit: WAR produced for the receiving club only.
            if recv_codes is not None:
                after, _ = _sum_seasons(
                    index,
                    mid,
                    from_season=first_season,
                    through_season=through_season,
                    club_codes=recv_codes,
                    for_club=True,
                )
            else:
                after, _ = _sum_seasons(
                    index,
                    mid,
                    from_season=first_season,
                    through_season=through_season,
                    club_codes=codes,
                    for_club=False,
                )
            player["war_prior"] = prior
            player["war_after_move"] = after
            player["war_during"] = prior
            player["war_after_exit"] = after
            war_prior_out += prior
            war_sent_away += after

        move["team_id"] = tid
        move["team_abbr"] = team_abbr(tid)
        move["team_name"] = team_name(tid)
        move["war_acquired"] = round(war_acquired, 2)
        move["war_sent_away"] = round(war_sent_away, 2)
        # net = during(focal) − during(receiver); league sum ≈ 0 for peer trades.
        move["net_war_exchange"] = round(war_acquired - war_sent_away, 2)
        move["war_prior_acquired"] = round(war_prior_in, 2)
        move["war_prior_sent"] = round(war_prior_out, 2)
        move["war_after_exit_acquired"] = round(war_after_exit, 2)

        if move["salary_paid"] is None and saw_salary:
            move["salary_paid"] = round(salary_acquired, 2)
            move["salary_source"] = "bref"

        if move["salary_paid"] is not None:
            move["surplus_value"] = round(
                war_acquired * dollars_per_war - move["salary_paid"], 2
            )
        else:
            move["surplus_value"] = None

        classify_move(move, dollars_per_war)


# ---------------------------------------------------------------------------
# Manual salary / contract overrides
# ---------------------------------------------------------------------------


def _fold_name(name: str) -> str:
    """Lowercase and strip accents, so "Carlos Rodon" matches "Carlos Rodón".

    Overrides are typed by hand from news coverage, which is inconsistent about
    accents; the MLB API is not. Folding both sides avoids a whole class of
    override that silently fails to match.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).strip().lower()


def _days_apart(left: str, right: str) -> int:
    try:
        a = dt.date.fromisoformat(left)
        b = dt.date.fromisoformat(right)
    except ValueError:
        return 10**6
    return abs((a - b).days)


def apply_overrides(
    moves: list[dict],
    overrides_path: Path,
    date_tolerance: int = 14,
    as_of: dt.date | None = None,
) -> tuple[int, list[str]]:
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

    pin = as_of or load_as_of()
    entries = json.loads(overrides_path.read_text())
    applied = 0
    unmatched: list[str] = []

    for entry in entries:
        match = entry.get("match") or {}
        target_id = entry.get("move_id")
        player = _fold_name(match.get("player") or "")
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
            # Hand overrides are Yankees-first; skip other clubs unless move_id set.
            if move.get("team_id") not in (None, YANKEES_MLBAM_ID):
                continue
            names = [
                _fold_name(p["name"])
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
            move["contract_active"] = entry["contract_through"] >= pin.year
        applied += 1

    return applied, unmatched


# ---------------------------------------------------------------------------


def public_fields(move: dict) -> dict:
    """The shape the web app consumes."""
    return {
        "move_id": move["move_id"],
        "team_id": move.get("team_id"),
        "team_abbr": move.get("team_abbr"),
        "team_name": move.get("team_name"),
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
        "war_prior_acquired": move.get("war_prior_acquired"),
        "war_prior_sent": move.get("war_prior_sent"),
        "war_after_exit_acquired": move.get("war_after_exit_acquired"),
        "salary_source": move["salary_source"],
        "counterparty": move["counterparty"],
        "counterparty_id": move.get("counterparty_id"),
        "acquisition_channel": move.get("acquisition_channel"),
        "deal_archetype": move.get("deal_archetype"),
        "talent_grade": move.get("talent_grade"),
        "talent_per_control_year": move.get("talent_per_control_year"),
        "ledger_grade": move.get("ledger_grade"),
        "control_years_remaining": move.get("control_years_remaining"),
        "control_bucket": move.get("control_bucket"),
        "control_source": move.get("control_source"),
        "salary_per_control_year": move.get("salary_per_control_year"),
        "win_now_window": move.get("win_now_window"),
        "mentions_cash": move.get("mentions_cash"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", type=int, default=None,
                        help="how many years back to pull (default: since --start-year)")
    parser.add_argument("--start-year", type=int, default=2006,
                        help="first calendar year to include (default: 2006)")
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

    today = load_as_of()
    if args.years is not None:
        start = today.replace(year=today.year - args.years)
    else:
        start = dt.date(args.start_year, 1, 1)

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

    applied, unmatched = apply_overrides(moves, args.overrides, as_of=today)
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
            apply_overrides(moves, args.overrides, as_of=today)
            for move in moves:
                if move["salary_source"] == "override" and move["war_acquired"] is not None:
                    move["surplus_value"] = round(
                        move["war_acquired"] * args.dollars_per_war - move["salary_paid"], 2
                    )

    # Always classify channels / archetypes / talent vs ledger grades.
    for move in moves:
        classify_move(move, args.dollars_per_war)

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
        "as_of": today.isoformat(),
        "dollars_per_war": args.dollars_per_war,
        "move_count": len(moves),
        "moves": [public_fields(m) for m in moves],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")

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
