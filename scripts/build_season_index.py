#!/usr/bin/env python3
"""Build single-season front-office construction grades.

Distinct from yearly resume boards (career-to-date through Oct of Y).

For each complete championship season Y and each GM active on Jul 1:
  - Trade / FA vintages: moves & arrivals in Nov 1 (Y-1) … Oct 31 Y,
    WAR observed through min(as_of, event_date + H years)
  - Draft vintage: June Y class once mature (as_of.year − lag); else null
  - StockShare: (own_prior + same_year) club WAR / total club WAR in Y
  - Thin season results: win%, depth, payroll efficiency for the Jul-1 chair

Writes data/season_index.json.
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

from build_moves import (  # noqa: E402
    _effective_season,
    _sum_seasons,
    load_bref_war,
)
from scoring import (  # noqa: E402
    efficiency_wins,
    last_complete_season,
    rank_descending,
    wins_per_100m,
)
from team_codes import TEAM_BREF_CODES, TEAMS, bref_codes  # noqa: E402

DATA = REPO_ROOT / "data"

# Defaults mirrored in weights.json season block; overridden when file present.
HORIZON_YEARS = 3
MATURE_LAG = 6
TRADE_PRIOR = 3
DRAFT_PRIOR = 20
FA_PRIOR = 5
AS_OF = dt.date(2026, 8, 2)
WINDOW_START = 2006
WINDOW_END = 2026

SEASON_WEIGHTS = {
    "trade_vintage_net": 0.35,
    "draft_vintage_vos": 0.25,
    "fa_vintage_war": 0.2,
    "stock_share": 0.1,
    "season_results": 0.1,
}
RESULTS_BLEND = {"win_pct": 0.4, "playoff_depth": 0.35, "payroll_efficiency": 0.25}


def load_weights() -> dict[str, Any]:
    global HORIZON_YEARS, MATURE_LAG, TRADE_PRIOR, DRAFT_PRIOR, FA_PRIOR
    global AS_OF, WINDOW_START, WINDOW_END, SEASON_WEIGHTS, RESULTS_BLEND
    path = DATA / "weights.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    WINDOW_START = int(raw.get("window_start", WINDOW_START))
    WINDOW_END = int(raw.get("window_end", WINDOW_END))
    if raw.get("as_of"):
        AS_OF = dt.date.fromisoformat(str(raw["as_of"])[:10])
    season = raw.get("season") or {}
    HORIZON_YEARS = int(season.get("horizon_years", HORIZON_YEARS))
    MATURE_LAG = int(season.get("mature_lag_years", MATURE_LAG))
    TRADE_PRIOR = int(season.get("trade_prior_moves", TRADE_PRIOR))
    DRAFT_PRIOR = int(season.get("draft_prior_picks", DRAFT_PRIOR))
    FA_PRIOR = int(season.get("fa_prior_arrivals", FA_PRIOR))
    if season.get("components"):
        SEASON_WEIGHTS = {k: float(v) for k, v in season["components"].items()}
    if season.get("results_blend"):
        RESULTS_BLEND = {k: float(v) for k, v in season["results_blend"].items()}
    return raw


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(REPO_ROOT)}", file=sys.stderr)


def season_attribution_window(year: int) -> tuple[dt.date, dt.date]:
    """Nov 1 of Y-1 through Oct 31 of Y."""
    return dt.date(year - 1, 11, 1), dt.date(year, 10, 31)


def horizon_through_season(event_date: dt.date, as_of: dt.date, horizon: int) -> int:
    """Last championship season credited for an event (inclusive)."""
    end = dt.date(
        event_date.year + horizon,
        event_date.month,
        min(event_date.day, 28),
    )
    return min(as_of, end).year


def sample_shrink(value: float, n: int, prior: int) -> float:
    if n <= 0:
        return 0.0
    return round(value * (n / (n + max(prior, 0))), 4)


def parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    return dt.date.fromisoformat(str(value)[:10])


def gm_on_date(
    team_id: int, day: dt.date, stints: list[dict[str, Any]], as_of: dt.date
) -> str | None:
    for stint in stints:
        if stint["team_id"] != team_id:
            continue
        start = parse_date(stint.get("start")) or dt.date(1900, 1, 1)
        end = parse_date(stint.get("end")) or as_of
        if start <= day <= end:
            return stint["person_id"]
    return None


def season_gm(
    team_id: int, season: int, stints: list[dict[str, Any]], as_of: dt.date
) -> str | None:
    return gm_on_date(team_id, dt.date(season, 7, 1), stints, as_of)


def move_in_window(move_date: str, lo: dt.date, hi: dt.date) -> bool:
    day = parse_date(move_date)
    return bool(day and lo <= day <= hi)


def horizon_trade_net(
    move: dict[str, Any],
    war_index: dict[int, list[dict]],
    as_of: dt.date,
    horizon: int,
) -> float:
    """Club-perspective net WAR clipped to deal_date + H years."""
    tid = int(move["team_id"])
    codes = bref_codes(tid)
    first_season = _effective_season(move["move_date"])
    event = parse_date(move["move_date"]) or dt.date(first_season, 7, 1)
    through = horizon_through_season(event, as_of, horizon)

    war_acquired = 0.0
    for player in move.get("players_acquired") or []:
        mid = player.get("mlbam_id")
        if not mid:
            continue
        during, _ = _sum_seasons(
            war_index,
            int(mid),
            from_season=first_season,
            through_season=through,
            club_codes=codes,
            for_club=True,
        )
        war_acquired += during

    war_sent = 0.0
    for player in move.get("players_sent_away") or []:
        mid = player.get("mlbam_id")
        if not mid:
            continue
        after, _ = _sum_seasons(
            war_index,
            int(mid),
            from_season=first_season,
            through_season=through,
            club_codes=codes,
            for_club=False,
        )
        war_sent += after

    return round(war_acquired - war_sent, 4)


def franchise_war_through(
    war_index: dict[int, list[dict]],
    mlbam: int | None,
    team_id: int,
    through_year: int,
    from_year: int | None = None,
) -> float:
    if not mlbam:
        return 0.0
    codes = TEAM_BREF_CODES.get(team_id) or frozenset()
    total = 0.0
    for row in war_index.get(int(mlbam), []):
        year = int(row["year"])
        if from_year is not None and year < from_year:
            continue
        if year > through_year:
            continue
        if row["team"] in codes:
            total += float(row["war"])
    return round(total, 4)


# ---------------------------------------------------------------------------
# Acquisition vintage map (player, team) → earliest acquisition event
# ---------------------------------------------------------------------------


def build_acquisition_events(
    moves: list[dict[str, Any]],
    picks: list[dict[str, Any]],
    war_index: dict[int, list[dict]],
) -> dict[tuple[int, int], dt.date]:
    """Earliest known acquisition date for (mlbam_id, team_id)."""
    events: dict[tuple[int, int], dt.date] = {}
    code_to_team: dict[str, int] = {}
    for tid, codes in TEAM_BREF_CODES.items():
        for c in codes:
            code_to_team[c] = tid

    def note(mid: int, tid: int, day: dt.date) -> None:
        key = (mid, tid)
        prev = events.get(key)
        if prev is None or day < prev:
            events[key] = day

    for pick in picks:
        mid = pick.get("mlbam_id")
        tid = pick.get("team_id")
        year = pick.get("draft_year")
        if mid and tid and year:
            note(int(mid), int(tid), dt.date(int(year), 6, 15))

    for move in moves:
        tid = int(move["team_id"])
        day = parse_date(move.get("move_date"))
        if not day:
            continue
        for player in move.get("players_acquired") or []:
            mid = player.get("mlbam_id")
            if mid:
                note(int(mid), tid, day)

    # First BRef season on club as fallback FA / unknown arrival proxy.
    first_year: dict[tuple[int, int], int] = {}
    for mid, rows in war_index.items():
        for row in rows:
            tid = code_to_team.get(row["team"])
            if tid is None:
                continue
            key = (int(mid), tid)
            y = int(row["year"])
            prev = first_year.get(key)
            if prev is None or y < prev:
                first_year[key] = y
    for (mid, tid), year in first_year.items():
        note(mid, tid, dt.date(year, 4, 1))

    return events


def vintage_tag(
    acq: dt.date | None,
    stint_start: dt.date,
    window_lo: dt.date,
    window_hi: dt.date,
) -> str:
    if acq is None:
        return "inherited"
    if window_lo <= acq <= window_hi:
        return "same_year"
    if acq >= stint_start and acq < window_lo:
        return "own_prior"
    if acq < stint_start:
        return "inherited"
    # Acquired after window (mid-season already covered) → same_year-ish later
    if acq > window_hi:
        return "same_year"
    return "inherited"


def build_team_season_war(
    war_index: dict[int, list[dict]],
) -> dict[tuple[int, int], list[tuple[int, float]]]:
    """(team_id, season) → [(mlbam_id, war), ...]."""
    out: dict[tuple[int, int], list[tuple[int, float]]] = defaultdict(list)
    code_to_team: dict[str, int] = {}
    for tid, codes in TEAM_BREF_CODES.items():
        for c in codes:
            code_to_team[c] = tid
    for mid, rows in war_index.items():
        for row in rows:
            tid = code_to_team.get(row["team"])
            if tid is None:
                continue
            out[(tid, int(row["year"]))].append((int(mid), float(row["war"])))
    return out


def stock_share_for_team_season(
    team_id: int,
    season: int,
    stint_start: dt.date,
    window_lo: dt.date,
    window_hi: dt.date,
    team_season_war: dict[tuple[int, int], list[tuple[int, float]]],
    acq_events: dict[tuple[int, int], dt.date],
) -> dict[str, float]:
    inherited = 0.0
    own_prior = 0.0
    same_year = 0.0
    for mid, season_war in team_season_war.get((team_id, season), []):
        if abs(season_war) < 1e-12:
            continue
        acq = acq_events.get((int(mid), team_id))
        tag = vintage_tag(acq, stint_start, window_lo, window_hi)
        if tag == "inherited":
            inherited += season_war
        elif tag == "own_prior":
            own_prior += season_war
        else:
            same_year += season_war
    club = inherited + own_prior + same_year
    share = (own_prior + same_year) / club if abs(club) > 1e-9 else 0.0
    return {
        "inherited_war": round(inherited, 3),
        "own_prior_war": round(own_prior, 3),
        "same_year_war": round(same_year, 3),
        "club_war": round(club, 3),
        "stock_share": round(share, 4),
    }


def fa_arrivals_war(
    team_id: int,
    window_lo: dt.date,
    window_hi: dt.date,
    war_index: dict[int, list[dict]],
    acq_events: dict[tuple[int, int], dt.date],
    drafted: set[tuple[int, int]],
    traded_in: set[tuple[int, int]],
    as_of: dt.date,
    horizon: int,
) -> tuple[float, int]:
    """Horizon WAR for non-draft, non-trade arrivals whose acq falls in window."""
    total = 0.0
    n = 0
    for (mid, tid), day in acq_events.items():
        if tid != team_id:
            continue
        if not (window_lo <= day <= window_hi):
            continue
        if (mid, tid) in drafted or (mid, tid) in traded_in:
            continue
        through = horizon_through_season(day, as_of, horizon)
        from_year = day.year if day.month >= 11 else day.year
        # Effective season start for Nov–Mar arrivals rolls forward.
        if day.month >= 11:
            from_year = day.year + 1
        war = franchise_war_through(war_index, mid, tid, through, from_year=from_year)
        total += war
        n += 1
    return round(total, 4), n


def results_score(season_row: dict[str, Any] | None) -> float:
    """Unit-ish blend of win%, depth, efficiency for one club-season."""
    if not season_row:
        return 0.0
    wins = int(season_row["wins"])
    losses = int(season_row["losses"])
    games = wins + losses
    win_pct = wins / games if games else 0.0
    depth = float(season_row.get("playoff_depth") or 0) / 4.0  # 0–1
    paced = efficiency_wins(int(season_row["season"]), wins, losses)
    pay = season_row.get("payroll")
    eff = wins_per_100m(paced, float(pay) if pay else None)
    # Soft-normalize efficiency around ~50 wins/$100M → ~0.5
    eff_n = max(0.0, min(1.0, eff / 100.0))
    return round(
        RESULTS_BLEND["win_pct"] * win_pct
        + RESULTS_BLEND["playoff_depth"] * depth
        + RESULTS_BLEND["payroll_efficiency"] * eff_n,
        4,
    )


def build_season_index(
    war_index: dict[int, list[dict]],
    moves: list[dict[str, Any]],
    picks: list[dict[str, Any]],
    stints: list[dict[str, Any]],
    team_seasons: list[dict[str, Any]],
) -> dict[str, Any]:
    names = {s["person_id"]: s["name"] for s in stints}
    complete_end = last_complete_season(AS_OF, WINDOW_END)
    mature_through = AS_OF.year - MATURE_LAG

    slot_curve: dict[str, float] = {}
    picks_path = DATA / "draft_index.json"
    if picks_path.exists():
        slot_curve = {
            str(k): float(v)
            for k, v in (json.loads(picks_path.read_text(encoding="utf-8")).get("slot_curve") or {}).items()
        }

    acq_events = build_acquisition_events(moves, picks, war_index)
    team_season_war = build_team_season_war(war_index)

    drafted = {
        (int(p["mlbam_id"]), int(p["team_id"]))
        for p in picks
        if p.get("mlbam_id") and p.get("team_id")
    }
    traded_in: set[tuple[int, int]] = set()
    for move in moves:
        tid = int(move["team_id"])
        for player in move.get("players_acquired") or []:
            if player.get("mlbam_id"):
                traded_in.add((int(player["mlbam_id"]), tid))

    seasons_by_key = {(r["team_id"], r["season"]): r for r in team_seasons}
    years_out: list[dict[str, Any]] = []

    for year in range(WINDOW_START, complete_end + 1):
        window_lo, window_hi = season_attribution_window(year)
        active: dict[str, dict[str, Any]] = {}

        # Jul-1 GM per club → results + stock share seat
        for tid in TEAMS:
            pid = season_gm(tid, year, stints, AS_OF)
            if not pid:
                continue
            stint_start = dt.date(1900, 1, 1)
            for stint in stints:
                if stint["person_id"] != pid or stint["team_id"] != tid:
                    continue
                start = parse_date(stint.get("start")) or dt.date(1900, 1, 1)
                end = parse_date(stint.get("end")) or AS_OF
                mid = dt.date(year, 7, 1)
                if start <= mid <= end:
                    stint_start = start
                    break

            row = active.setdefault(
                pid,
                {
                    "person_id": pid,
                    "name": names.get(pid, pid),
                    "teams": [],
                    "trade_nets": [],
                    "draft_vos_list": [],
                    "fa_wars": [],
                    "fa_n": 0,
                    "stock_shares": [],
                    "results": [],
                },
            )
            abbr = TEAMS[tid]["abbr"]
            if abbr not in row["teams"]:
                row["teams"].append(abbr)

            stock = stock_share_for_team_season(
                tid, year, stint_start, window_lo, window_hi, team_season_war, acq_events
            )
            row["stock_shares"].append(stock["stock_share"])

            srow = seasons_by_key.get((tid, year))
            row["results"].append(results_score(srow))

            fa_war, fa_n = fa_arrivals_war(
                tid,
                window_lo,
                window_hi,
                war_index,
                acq_events,
                drafted,
                traded_in,
                AS_OF,
                HORIZON_YEARS,
            )
            if fa_n:
                row["fa_wars"].append(fa_war)
                row["fa_n"] += fa_n

        # Trades in window → GM on move date
        for move in moves:
            if not move_in_window(move.get("move_date") or "", window_lo, window_hi):
                continue
            day = parse_date(move["move_date"])
            if not day:
                continue
            tid = int(move["team_id"])
            pid = gm_on_date(tid, day, stints, AS_OF)
            if not pid:
                continue
            row = active.setdefault(
                pid,
                {
                    "person_id": pid,
                    "name": names.get(pid, pid),
                    "teams": [],
                    "trade_nets": [],
                    "draft_vos_list": [],
                    "fa_wars": [],
                    "fa_n": 0,
                    "stock_shares": [],
                    "results": [],
                },
            )
            abbr = TEAMS.get(tid, {}).get("abbr")
            if abbr and abbr not in row["teams"]:
                row["teams"].append(abbr)
            row["trade_nets"].append(horizon_trade_net(move, war_index, AS_OF, HORIZON_YEARS))

        # Draft class Y
        draft_immature = year > mature_through
        for pick in picks:
            if int(pick.get("draft_year") or 0) != year:
                continue
            pid = pick.get("gm_person_id")
            if not pid:
                continue
            row = active.setdefault(
                pid,
                {
                    "person_id": pid,
                    "name": names.get(pid, pid),
                    "teams": [],
                    "trade_nets": [],
                    "draft_vos_list": [],
                    "fa_wars": [],
                    "fa_n": 0,
                    "stock_shares": [],
                    "results": [],
                },
            )
            if draft_immature:
                continue
            tid = int(pick["team_id"])
            expected = float(slot_curve.get(str(pick.get("slot_bin")), 0.0))
            through = horizon_through_season(dt.date(year, 6, 15), AS_OF, max(HORIZON_YEARS, MATURE_LAG))
            # Once mature, use franchise WAR through as_of (living revision), not tiny H.
            through = min(AS_OF.year, through)
            war = franchise_war_through(
                war_index, pick.get("mlbam_id"), tid, through, from_year=year
            )
            row["draft_vos_list"].append(war - expected)

        leaderboard: list[dict[str, Any]] = []
        for pid, row in active.items():
            trades = row["trade_nets"]
            trade_raw = sum(trades) if trades else 0.0
            trade_vintage = sample_shrink(trade_raw, len(trades), TRADE_PRIOR)

            if draft_immature:
                draft_vintage = None
            elif row["draft_vos_list"]:
                avg = sum(row["draft_vos_list"]) / len(row["draft_vos_list"])
                draft_vintage = sample_shrink(avg, len(row["draft_vos_list"]), DRAFT_PRIOR)
            else:
                draft_vintage = 0.0

            fa_raw = sum(row["fa_wars"]) if row["fa_wars"] else 0.0
            fa_vintage = sample_shrink(fa_raw, max(row["fa_n"], len(row["fa_wars"])), FA_PRIOR)

            stock = (
                sum(row["stock_shares"]) / len(row["stock_shares"])
                if row["stock_shares"]
                else 0.0
            )
            results = (
                sum(row["results"]) / len(row["results"]) if row["results"] else 0.0
            )

            # For z-score composite, immature draft → neutral 0 so it does not dominate.
            draft_for_score = 0.0 if draft_vintage is None else draft_vintage

            leaderboard.append(
                {
                    "person_id": pid,
                    "name": row["name"],
                    "teams": row["teams"],
                    "trade_vintage_net": round(trade_vintage, 4),
                    "trade_count": len(trades),
                    "draft_vintage_vos": draft_vintage,
                    "draft_immature": draft_immature,
                    "draft_picks": len(row["draft_vos_list"]),
                    "fa_vintage_war": round(fa_vintage, 4),
                    "fa_arrivals": row["fa_n"],
                    "stock_share": round(stock, 4),
                    "season_results": round(results, 4),
                    "_draft_for_score": draft_for_score,
                }
            )

        if not leaderboard:
            continue

        score_rows = [
            {
                "trade_vintage_net": r["trade_vintage_net"],
                "draft_vintage_vos": r["_draft_for_score"],
                "fa_vintage_war": r["fa_vintage_war"],
                "stock_share": r["stock_share"],
                "season_results": r["season_results"],
            }
            for r in leaderboard
        ]
        scores = _season_composites(score_rows, SEASON_WEIGHTS)
        ranks = rank_descending(scores)
        for r, score, rank in zip(leaderboard, scores, ranks):
            r["composite"] = score
            r["rank"] = rank
            del r["_draft_for_score"]

        leaderboard.sort(key=lambda r: r["rank"])
        years_out.append(
            {
                "season": year,
                "attribution_window": [window_lo.isoformat(), window_hi.isoformat()],
                "draft_immature": draft_immature,
                "gm_count": len(leaderboard),
                "leaderboard": leaderboard,
            }
        )

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "as_of": AS_OF.isoformat(),
        "window": [WINDOW_START, complete_end],
        "horizon_years": HORIZON_YEARS,
        "mature_lag_years": MATURE_LAG,
        "weights": SEASON_WEIGHTS,
        "framing": (
            "Single-season FO construction grade: trades/FA in Nov–Oct window "
            f"with WAR through deal_date+{HORIZON_YEARS}y; draft VOS after "
            f"{MATURE_LAG}-year mature lag; StockShare = own-regime WAR share; "
            "thin club results for the Jul-1 GM. Living revision, not "
            "contemporaneous grades. Distinct from Resume-as-of-Y."
        ),
        "years": years_out,
    }


def _season_composites(
    rows: list[dict[str, Any]], weights: dict[str, float]
) -> list[float]:
    """Z-score weighted sum over season construction keys only."""
    from scoring import zscore

    keys = list(weights.keys())
    z_by: dict[str, list[float]] = {}
    for key in keys:
        z_by[key] = zscore([float(r.get(key) or 0.0) for r in rows])
    out: list[float] = []
    for i in range(len(rows)):
        total = 0.0
        for key in keys:
            total += weights.get(key, 0.0) * z_by[key][i]
        out.append(round(total, 4))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-war",
        action="store_true",
        help="Skip BRef download (fixture/dev only — grades will be empty/zero)",
    )
    args = parser.parse_args()
    load_weights()

    moves_path = DATA / "league_moves.json"
    if not moves_path.exists():
        print(f"Missing {moves_path}", file=sys.stderr)
        return 1
    moves = json.loads(moves_path.read_text(encoding="utf-8")).get("moves") or []

    picks_path = DATA / "draft_picks.json"
    picks = []
    if picks_path.exists():
        picks = json.loads(picks_path.read_text(encoding="utf-8")).get("picks") or []

    stints_raw = json.loads((DATA / "gm_tenures.json").read_text(encoding="utf-8"))
    stints = stints_raw["stints"] if isinstance(stints_raw, dict) else stints_raw

    seasons_path = DATA / "team_seasons.json"
    team_seasons = []
    if seasons_path.exists():
        team_seasons = json.loads(seasons_path.read_text(encoding="utf-8")).get("seasons") or []

    if args.skip_war:
        war_index: dict[int, list[dict]] = {}
        print("WARNING: --skip-war; season construction WAR will be zero", file=sys.stderr)
    else:
        print("loading Baseball Reference WAR…", file=sys.stderr)
        war_index = load_bref_war()

    print("building season construction index", file=sys.stderr)
    payload = build_season_index(war_index, moves, picks, stints, team_seasons)
    write_json(DATA / "season_index.json", payload)
    print(
        f"Seasons: {len(payload['years'])}; "
        f"latest {payload['years'][-1]['season'] if payload['years'] else '—'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
