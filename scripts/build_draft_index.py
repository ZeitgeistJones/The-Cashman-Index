#!/usr/bin/env python3
"""Build draft value-over-slot indexes for the Front Office Index.

Fetches Rule 4 / June Amateur Draft results from the MLB Stats API (2006+),
attaches career Baseball Reference WAR via pybaseball, estimates expected WAR
by pick slot from mature classes, and writes:

  data/draft_picks.json   — every pick with realized / expected / VOS
  data/draft_index.json   — franchise + GM draft grades (avg VOS / pick)

Value over slot (VOS) = career_war − expected_war(pick_number).
Extra competitive-balance picks use the same slot curve (pick # already
encodes opportunity — no second small-market boost).

Recent classes (draft_year > as_of_year − MATURE_LAG) are flagged immature and
excluded from the primary grade (still listed for transparency).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"

WINDOW_START = 2006
# Classes need time to produce MLB WAR before we grade harshly.
MATURE_LAG = 6
AS_OF = dt.date(2026, 8, 2)  # overwritten from weights.json
WINDOW_END = 2026


def load_as_of() -> dt.date:
    global AS_OF, WINDOW_START, WINDOW_END
    path = DATA / "weights.json"
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        WINDOW_START = int(raw.get("window_start", WINDOW_START))
        WINDOW_END = int(raw.get("window_end", WINDOW_END))
        if raw.get("as_of"):
            AS_OF = dt.date.fromisoformat(str(raw["as_of"])[:10])
    return AS_OF


SESSION_HEADERS = {"User-Agent": "front-office-index/0.1 (personal project)"}

# Pick-number bins for expected WAR (inclusive). Late rounds are sparse — wide bins.
SLOT_BINS: list[tuple[int, int, str]] = [
    (1, 1, "1"),
    (2, 5, "2-5"),
    (6, 10, "6-10"),
    (11, 20, "11-20"),
    (21, 30, "21-30"),
    (31, 50, "31-50"),
    (51, 100, "51-100"),
    (101, 200, "101-200"),
    (201, 400, "201-400"),
    (401, 10_000, "401+"),
]


def _session():
    import requests

    session = requests.Session()
    session.headers.update(SESSION_HEADERS)
    return session


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(REPO_ROOT)}", file=sys.stderr)


def bin_label(pick_number: int) -> str:
    for lo, hi, label in SLOT_BINS:
        if lo <= pick_number <= hi:
            return label
    return "401+"


def fetch_draft_year(session, year: int) -> list[dict[str, Any]]:
    response = session.get(
        f"https://statsapi.mlb.com/api/v1/draft/{year}",
        timeout=90,
    )
    response.raise_for_status()
    drafts = response.json().get("drafts") or {}
    picks_out: list[dict[str, Any]] = []
    for rnd in drafts.get("rounds") or []:
        round_name = str(rnd.get("round") or "")
        for pick in rnd.get("picks") or []:
            person = pick.get("person") or {}
            team = pick.get("team") or {}
            mlbam = person.get("id")
            try:
                pick_number = int(pick.get("pickNumber") or pick.get("displayPickNumber") or 0)
            except (TypeError, ValueError):
                continue
            if pick_number <= 0 or not team.get("id"):
                continue
            bonus = pick.get("signingBonus")
            try:
                bonus_val = int(str(bonus).replace(",", "")) if bonus not in (None, "") else None
            except ValueError:
                bonus_val = None
            picks_out.append(
                {
                    "draft_year": year,
                    "pick_number": pick_number,
                    "pick_round": str(pick.get("pickRound") or round_name),
                    "slot_bin": bin_label(pick_number),
                    "team_id": int(team["id"]),
                    "team_name": team.get("name"),
                    "mlbam_id": int(mlbam) if mlbam else None,
                    "player_name": person.get("fullName") or pick.get("person", {}).get("fullName"),
                    "signing_bonus": bonus_val,
                    "draft_type": (pick.get("draftType") or {}).get("description"),
                }
            )
    return picks_out


def load_war_seasons() -> dict[int, list[dict[str, Any]]]:
    """Per-player season WAR rows from Baseball Reference (bat + pitch)."""
    try:
        from pybaseball import bwar_bat, bwar_pitch
    except ImportError as exc:
        raise SystemExit(
            "pybaseball required for draft WAR. pip install -r scripts/requirements.txt"
        ) from exc

    print("  downloading Baseball Reference WAR tables...", file=sys.stderr)
    index: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for frame in (bwar_bat(return_all=True), bwar_pitch(return_all=True)):
        for record in frame.to_dict("records"):
            try:
                mlbam = int(record["mlb_ID"])
                war = float(record["WAR"])
                year = int(record["year_ID"])
            except (TypeError, ValueError, KeyError):
                continue
            if math.isnan(war):
                continue
            index[mlbam].append(
                {
                    "year": year,
                    "team": str(record.get("team_ID") or ""),
                    "war": war,
                }
            )
    return index


# MLBAM team_id → Baseball Reference team codes live in team_codes.py
from team_codes import TEAM_BREF_CODES  # noqa: E402


def franchise_war_for_pick(
    seasons: dict[int, list[dict[str, Any]]], mlbam: int | None, team_id: int
) -> float:
    """WAR produced for the drafting club only (stops double-count with trades)."""
    if not mlbam:
        return 0.0
    codes = TEAM_BREF_CODES.get(team_id)
    if not codes:
        # Unknown mapping: fall back to 0 rather than full career (safer vs double-count).
        return 0.0
    total = 0.0
    for row in seasons.get(mlbam, []):
        if row["team"] in codes:
            total += float(row["war"])
    return round(total, 3)


def load_career_war() -> dict[int, float]:
    """Deprecated path — full career. Prefer franchise_war_for_pick."""
    seasons = load_war_seasons()
    career: dict[int, float] = defaultdict(float)
    for mlbam, rows in seasons.items():
        for row in rows:
            career[mlbam] += float(row["war"])
    return {k: round(v, 3) for k, v in career.items()}


def build_slot_curve(picks: list[dict[str, Any]], mature_through: int) -> dict[str, float]:
    """Mean career WAR by slot bin from mature draft classes."""
    bucket: dict[str, list[float]] = defaultdict(list)
    for pick in picks:
        if pick["draft_year"] > mature_through:
            continue
        bucket[pick["slot_bin"]].append(float(pick.get("career_war") or 0.0))
    curve = {}
    for _lo, _hi, label in SLOT_BINS:
        vals = bucket.get(label) or [0.0]
        curve[label] = round(sum(vals) / len(vals), 4)
    return curve


def load_gm_stints() -> list[dict[str, Any]]:
    raw = json.loads((DATA / "gm_tenures.json").read_text(encoding="utf-8"))
    return raw["stints"] if isinstance(raw, dict) else raw


def gm_on_draft_day(team_id: int, draft_year: int, stints: list[dict[str, Any]]) -> str | None:
    """Attribute draft to whoever held the job on June 15 of the draft year."""
    day = dt.date(draft_year, 6, 15)
    for stint in stints:
        if stint["team_id"] != team_id:
            continue
        start = dt.date.fromisoformat(stint["start"]) if stint.get("start") else dt.date(1900, 1, 1)
        end = (
            dt.date.fromisoformat(stint["end"])
            if stint.get("end")
            else AS_OF
        )
        if start <= day <= end:
            return stint["person_id"]
    return None


def grade_groups(
    picks: list[dict[str, Any]],
    key_fn,
    name_fn,
    prior_picks: int = 100,
) -> list[dict[str, Any]]:
    groups: dict[Any, list[dict]] = defaultdict(list)
    for pick in picks:
        if not pick.get("mature"):
            continue
        key = key_fn(pick)
        if key is None:
            continue
        groups[key].append(pick)

    rows = []
    for key, group in groups.items():
        vos_list = [float(p["vos"]) for p in group]
        n = len(group)
        avg = sum(vos_list) / n
        total = sum(vos_list)
        # Shrink toward 0 so a short early tenure cannot dominate on tiny samples.
        shrink = n / (n + prior_picks)
        rows.append(
            {
                **name_fn(key, group),
                "picks": n,
                "avg_vos_raw": round(avg, 4),
                "avg_vos": round(avg * shrink, 4),
                "vos_shrink": round(shrink, 4),
                "total_vos": round(total, 4),
                "avg_career_war": round(
                    sum(float(p["career_war"]) for p in group) / n, 4
                ),
                "avg_expected_war": round(
                    sum(float(p["expected_war"]) for p in group) / n, 4
                ),
                "small_sample": n < 50,
            }
        )
    rows.sort(key=lambda r: r["avg_vos"], reverse=True)
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=WINDOW_START)
    parser.add_argument("--end", type=int, default=AS_OF.year)
    parser.add_argument("--pause", type=float, default=0.25)
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="reuse data/draft_picks.json picks list (recompute WAR/curve if --refresh-war)",
    )
    parser.add_argument("--skip-war", action="store_true")
    args = parser.parse_args()
    load_as_of()
    from scoring import last_complete_season

    complete_end = last_complete_season(AS_OF, WINDOW_END)
    # Fetch may include the open year for immature listing; scored window matches rankings.
    fetch_end = max(args.end, AS_OF.year)

    mature_through = AS_OF.year - MATURE_LAG
    picks_path = DATA / "draft_picks.json"

    if args.use_cache and picks_path.exists():
        print("loading cached draft picks", file=sys.stderr)
        cached = json.loads(picks_path.read_text(encoding="utf-8"))
        picks = cached["picks"]
    else:
        session = _session()
        picks = []
        for year in range(args.start, fetch_end + 1):
            print(f"  draft {year}", file=sys.stderr)
            try:
                year_picks = fetch_draft_year(session, year)
            except Exception as exc:  # noqa: BLE001
                print(f"    failed: {exc}", file=sys.stderr)
                year_picks = []
            picks.extend(year_picks)
            time.sleep(args.pause)

    war_seasons: dict[int, list[dict[str, Any]]] = {}
    if args.skip_war:
        print(
            "WARNING: --skip-war set; franchise WAR / VOS will be zero. "
            "Do not ship draft_index.json from this run.",
            file=sys.stderr,
        )
    else:
        war_seasons = load_war_seasons()
        if not war_seasons:
            raise SystemExit(
                "WAR tables loaded empty — refusing to overwrite draft indexes with zeros"
            )

    for pick in picks:
        mlbam = pick.get("mlbam_id")
        war = franchise_war_for_pick(war_seasons, mlbam, pick["team_id"])
        pick["career_war"] = war  # kept key name; value is franchise-tenure WAR
        pick["franchise_war"] = war
        pick["mature"] = pick["draft_year"] <= mature_through

    if not args.skip_war:
        mature_with_id = [
            p
            for p in picks
            if p.get("mature") and p.get("mlbam_id")
        ]
        hit = sum(1 for p in mature_with_id if float(p.get("career_war") or 0.0) != 0.0)
        # Most draftees never reach MLB; a healthy attach still lights up several
        # percent of mature picks (stars + role players for drafting clubs).
        hit_rate = hit / len(mature_with_id) if mature_with_id else 0.0
        print(
            f"  franchise-WAR hits: {hit}/{len(mature_with_id)} mature picks "
            f"({hit_rate:.1%})",
            file=sys.stderr,
        )
        if hit_rate < 0.02:
            raise SystemExit(
                f"franchise-WAR hit rate {hit_rate:.1%} looks broken "
                "(team-code join or empty WAR). Refusing to write all-zero draft grades."
            )

    curve = build_slot_curve(picks, mature_through)
    for pick in picks:
        expected = curve.get(pick["slot_bin"], 0.0)
        pick["expected_war"] = expected
        pick["vos"] = round(float(pick["career_war"]) - expected, 4)

    stints = load_gm_stints()
    names = {s["person_id"]: s["name"] for s in stints}
    for pick in picks:
        pid = gm_on_draft_day(pick["team_id"], pick["draft_year"], stints)
        pick["gm_person_id"] = pid
        pick["gm_name"] = names.get(pid) if pid else None

    picks_payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "as_of": AS_OF.isoformat(),
        "window": [args.start, complete_end],
        "mature_through": mature_through,
        "mature_lag_years": MATURE_LAG,
        "slot_curve": curve,
        "pick_count": len(picks),
        "notes": (
            "VOS = franchise-tenure WAR − mean for that pick-number bin among "
            f"mature classes (draft year ≤ {mature_through}). WAR after a trade "
            "away is not draft credit (avoids double-count with trade ledger). "
            "Immature classes listed but excluded from primary grades."
        ),
        "picks": picks,
    }
    write_json(picks_path, picks_payload)

    # Franchise / GM grades from mature picks only.
    team_meta = {
        108: "LAA", 109: "ARI", 110: "BAL", 111: "BOS", 112: "CHC", 113: "CIN",
        114: "CLE", 115: "COL", 116: "DET", 117: "HOU", 118: "KC", 119: "LAD",
        120: "WSH", 121: "NYM", 133: "OAK", 134: "PIT", 135: "SD", 136: "SEA",
        137: "SF", 138: "STL", 139: "TB", 140: "TEX", 141: "TOR", 142: "MIN",
        143: "PHI", 144: "ATL", 145: "CWS", 146: "MIA", 147: "NYY", 158: "MIL",
    }

    franchises = grade_groups(
        picks,
        key_fn=lambda p: p["team_id"],
        name_fn=lambda tid, group: {
            "team_id": tid,
            "team_abbr": team_meta.get(tid, "?"),
            "team_name": group[0].get("team_name"),
        },
    )
    gms = grade_groups(
        picks,
        key_fn=lambda p: p.get("gm_person_id"),
        name_fn=lambda pid, group: {
            "person_id": pid,
            "name": names.get(pid, pid),
            "teams": sorted(
                {
                    team_meta.get(p["team_id"], "?")
                    for p in group
                }
            ),
        },
    )

    index = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "as_of": AS_OF.isoformat(),
        "window": [args.start, complete_end],
        "mature_through": mature_through,
        "slot_curve": curve,
        "framing": (
            "Draft grade = average value over slot among mature picks, using WAR "
            "produced for the drafting club only. Same slot curve for every club — "
            "extra picks mean more chances, not a second grading curve."
        ),
        "franchises": franchises,
        "gms": gms,
    }
    write_json(DATA / "draft_index.json", index)

    top = franchises[0] if franchises else None
    print(
        f"Top draft franchise: {top['team_abbr'] if top else '?'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
