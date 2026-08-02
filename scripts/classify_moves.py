"""Classify Yankees front-office moves: channel, both-sides talent, money, light context.

Spine = net talent exchange (trades) / acquired WAR (one-way) and ledger when salary
is known. Remaining control years are *context* when we actually know them from
overrides — not a fake precision grade. Jul/Aug deals get a win-now window flag
(October-aimed is often the intent) without inventing clutch metrics.

Used by build_moves.py and can re-annotate data/moves.json without re-downloading WAR.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOLLARS_PER_WAR = 8_000_000

CHANNEL_BY_TYPE = {
    "Trade": "trade",
    "Signed as Free Agent": "free_agent",
    "Signed": "signing",
    "Claimed Off Waivers": "waiver",
    "Selected": "rule5_or_selected",
    "Purchase": "purchase",
    "Released": "release",
    "Outrighted": "outright",
    "Elected Free Agency": "free_agency_exit",
}

# Only trust control math when we have hand-entered terms.
KNOWN_CONTROL_SOURCES = frozenset({"contract_through", "contract_years"})


def _parse_ymd(iso: str) -> tuple[int, int, int]:
    return int(iso[0:4]), int(iso[5:7]), int(iso[8:10])


def championship_season(year: int, month: int) -> int:
    """Nov/Dec moves belong to next season."""
    return year + 1 if month >= 11 else year


def estimate_control_years(move: dict[str, Any]) -> tuple[float | None, str]:
    """Return (years of club control remaining, source_tag).

    Only invent a number when contract_through / contract_years are on the move.
    Jul/Aug without terms → unknown (not a hard-coded 0.3y rental) — packages often
    include multi-year pieces; faking control blows up WAR/ctrl-yr.
    """
    date = move.get("move_date") or ""
    if len(date) < 10:
        return None, "unknown"
    year, month, _day = _parse_ymd(date)
    season = championship_season(year, month)
    move_type = move.get("move_type") or ""
    through = move.get("contract_through")
    years = move.get("contract_years")

    if through is not None:
        try:
            through_i = int(through)
        except (TypeError, ValueError):
            through_i = None
        if through_i is not None:
            full_seasons_after = max(0, through_i - season)
            # Midseason only for Jul–Sep (not Nov/Dec offseason filings).
            if 7 <= month <= 9:
                partial = max(0.2, (10 - month) / 6.0)
                remaining = full_seasons_after + partial
            else:
                remaining = float(full_seasons_after + 1)
            return round(max(0.2, remaining), 2), "contract_through"

    if years is not None:
        try:
            y = float(years)
            if move_type == "Trade" and 7 <= month <= 9:
                y = max(0.25, y - (month - 4) / 12.0)
            return round(y, 2), "contract_years"
        except (TypeError, ValueError):
            pass

    return None, "unknown"


def control_bucket(years: float | None, source: str) -> str:
    if years is None or source not in KNOWN_CONTROL_SOURCES:
        return "unknown"
    if years <= 0.5:
        return "rental"
    if years <= 1.25:
        return "one_year"
    if years <= 3.5:
        return "multi_year"
    return "long_term"


def classify_move(move: dict[str, Any], dollars_per_war: float = DEFAULT_DOLLARS_PER_WAR) -> None:
    """Mutate move with channel, optional control context, archetype, grades."""
    move_type = move.get("move_type") or ""
    channel = CHANNEL_BY_TYPE.get(move_type, "other")
    move["acquisition_channel"] = channel

    war_acq = move.get("war_acquired")
    war_sent = move.get("war_sent_away")
    net = move.get("net_war_exchange")
    salary = move.get("salary_paid")
    summary = (move.get("summary") or "").lower()
    n_acq = len(move.get("players_acquired") or [])
    n_sent = len(move.get("players_sent_away") or [])

    date = move.get("move_date") or ""
    month = int(date[5:7]) if len(date) >= 7 else 0

    control_years, control_source = estimate_control_years(move)
    move["control_years_remaining"] = control_years
    move["control_source"] = control_source
    move["control_bucket"] = control_bucket(control_years, control_source)

    # Deadline / August window: often win-now / October-aimed. Annotation only.
    move["win_now_window"] = bool(channel == "trade" and month in {7, 8})

    # Talent grade: net WAR for trades; acquired WAR for one-way deals.
    if channel == "trade" and net is not None:
        talent = float(net)
    elif war_acq is not None:
        talent = float(war_acq)
    else:
        talent = None
    move["talent_grade"] = round(talent, 2) if talent is not None else None

    # WAR/ctrl-yr only when control is known from overrides — never from guesses.
    if (
        talent is not None
        and control_years
        and control_years > 0
        and control_source in KNOWN_CONTROL_SOURCES
    ):
        move["talent_per_control_year"] = round(talent / control_years, 2)
    else:
        move["talent_per_control_year"] = None

    if move.get("surplus_value") is not None:
        ledger = float(move["surplus_value"])
    elif salary is not None and war_acq is not None:
        ledger = float(war_acq) * dollars_per_war - float(salary)
    else:
        ledger = None
    move["ledger_grade"] = round(ledger, 2) if ledger is not None else None

    if (
        salary is not None
        and control_years
        and control_years > 0
        and control_source in KNOWN_CONTROL_SOURCES
    ):
        move["salary_per_control_year"] = round(float(salary) / control_years, 2)
    else:
        move["salary_per_control_year"] = None

    mentions_cash = bool(re.search(r"\bcash\b|player to be named|ptbnl", summary))
    expensive = salary is not None and salary >= 40_000_000
    cheap_talent = war_acq is not None and war_acq < 1.5
    strong_talent_in = war_acq is not None and war_acq >= 5
    dumped_talent = war_sent is not None and war_sent >= 4 and (war_acq or 0) < 2
    is_rental = move["control_bucket"] == "rental"
    is_long = move["control_bucket"] in {"multi_year", "long_term"}

    # Archetypes from value exchange first; control/win-now only as light tags.
    archetype = "other"
    if channel == "trade":
        if expensive and is_long and cheap_talent:
            archetype = "contract_assumption"
        elif expensive and cheap_talent:
            archetype = "contract_dump_or_win_now"
        elif dumped_talent and (salary is None or (salary or 0) < 15_000_000):
            archetype = "talent_sold"
        elif strong_talent_in and (war_sent or 0) < 2:
            archetype = "prospect_or_talent_haul"
        elif is_rental and move["win_now_window"]:
            archetype = "deadline_rental"
        elif move["win_now_window"] and net is not None and net >= 1:
            archetype = "deadline_add_hit"
        elif move["win_now_window"] and net is not None and net <= -1:
            archetype = "deadline_add_miss"
        elif move["win_now_window"]:
            archetype = "deadline_add"
        elif mentions_cash:
            archetype = "cash_involved"
        elif net is not None and net >= 2:
            archetype = "trade_win"
        elif net is not None and net <= -2:
            archetype = "trade_loss"
        elif net is not None and abs(net) < 1 and n_acq + n_sent >= 2:
            archetype = "talent_swap"
        else:
            archetype = "talent_swap"
    elif channel == "free_agent":
        if expensive and cheap_talent:
            archetype = "expensive_bust_or_active"
        elif ledger is not None and ledger > 20_000_000:
            archetype = "bargain_fa"
        elif ledger is not None and ledger < -30_000_000:
            archetype = "overpay_fa"
        else:
            archetype = "free_agent"
    elif channel == "waiver":
        archetype = "waiver_claim"
    elif channel == "rule5_or_selected":
        archetype = "selected_or_rule5"
    elif channel in {"release", "outright", "free_agency_exit"}:
        archetype = "departure"
    else:
        archetype = channel

    move["deal_archetype"] = archetype
    move["mentions_cash"] = mentions_cash


def annotate_file(
    path: Path,
    dollars_per_war: float = DEFAULT_DOLLARS_PER_WAR,
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for move in payload.get("moves") or []:
        classify_move(move, dollars_per_war)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--moves", type=Path, default=REPO_ROOT / "data" / "moves.json")
    parser.add_argument("--dollars-per-war", type=float, default=DEFAULT_DOLLARS_PER_WAR)
    args = parser.parse_args()
    payload = annotate_file(args.moves, args.dollars_per_war)
    from collections import Counter

    arcs = Counter(m.get("deal_archetype") for m in payload["moves"])
    buckets = Counter(
        m.get("control_bucket") for m in payload["moves"] if m.get("move_type") == "Trade"
    )
    win_now = sum(
        1
        for m in payload["moves"]
        if m.get("move_type") == "Trade" and m.get("win_now_window")
    )
    print(f"Annotated {payload.get('move_count')} moves")
    print("Trade control buckets:", dict(buckets))
    print(f"Win-now window trades: {win_now}")
    for k, v in arcs.most_common(15):
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
