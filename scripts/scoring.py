"""Shared z-score composite scoring for franchise and GM indexes."""

from __future__ import annotations

import math
import statistics
from typing import Any


# Rate-based components — titles/depth per season so longevity does not accumulate a free pass.
COMPONENT_KEYS = (
    "world_series_rate",
    "pennants_rate",
    "playoff_depth_rate",
    "win_pct",
    "payroll_efficiency",
    "draft_vos",
    "trade_net_rate",
)

CATEGORY_KEYS = COMPONENT_KEYS

ROUND_DEPTH = {
    "F": 1,
    "D": 2,
    "L": 3,
    "W": 4,
}

# 2020 COVID season: ~60 games, roughly full opening-day payrolls.
# Rate metrics (win%) need no special case. Counting wins vs full payroll would
# systematically tank payroll efficiency for that year — prorate wins to a
# 162-game pace for efficiency only. Titles / pennants / playoff depth still
# count as one full championship season (a World Series is a World Series).
COVID_SEASON = 2020
FULL_SEASON_GAMES = 162


def efficiency_wins(season: int, wins: int, losses: int) -> float:
    """Wins counted toward payroll efficiency (2020 paced to 162 games)."""
    if int(season) != COVID_SEASON:
        return float(wins)
    games = int(wins) + int(losses)
    if games <= 0:
        return 0.0
    return float(wins) * (FULL_SEASON_GAMES / games)


def zscore(values: list[float]) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [0.0]
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values)
    if stdev < 1e-12:
        return [0.0 for _ in values]
    return [(v - mean) / stdev for v in values]


def _is_missing(value: Any) -> bool:
    """True when a component is absent. Legitimate 0.0 is present."""
    return value is None


def composite_scores(
    rows: list[dict[str, Any]],
    weights: dict[str, float],
) -> list[float]:
    """Weighted z-score sum with per-row missing → drop + renormalize.

    Missing components (None) are not coerced to 0.0. Z-scores for each key use
    only peers that have that key; each row renormalizes weights over its
    present components so a blank trade_net cannot look above-average.
    """
    if not rows:
        return []

    z_by_key: dict[str, list[float | None]] = {}
    for key in COMPONENT_KEYS:
        present_idx = [
            i for i, r in enumerate(rows) if not _is_missing(r.get(key))
        ]
        present_vals = [float(rows[i][key]) for i in present_idx]
        zs_present = zscore(present_vals) if present_vals else []
        slot: list[float | None] = [None] * len(rows)
        for j, i in enumerate(present_idx):
            slot[i] = zs_present[j]
        z_by_key[key] = slot

    out: list[float] = []
    for i in range(len(rows)):
        active: dict[str, float] = {}
        for key in COMPONENT_KEYS:
            if z_by_key[key][i] is None:
                continue
            w = float(weights.get(key, 0.0) or 0.0)
            if w > 0:
                active[key] = w
        total_w = sum(active.values())
        if total_w <= 0:
            out.append(0.0)
            continue
        score = 0.0
        for key, w in active.items():
            score += (w / total_w) * float(z_by_key[key][i])  # type: ignore[arg-type]
        out.append(round(score, 4))
    return out


def category_ranks(rows: list[dict[str, Any]]) -> list[dict[str, int]]:
    """Per-component competition ranks (1 = best). Missing → rank after all present."""
    result: list[dict[str, int]] = [{} for _ in rows]
    for key in CATEGORY_KEYS:
        present_idx = [
            i for i, r in enumerate(rows) if not _is_missing(r.get(key))
        ]
        present_vals = [float(rows[i][key]) for i in present_idx]
        present_ranks = rank_descending(present_vals) if present_vals else []
        missing_rank = len(present_idx) + 1
        for j, i in enumerate(present_idx):
            result[i][key] = present_ranks[j]
        for i, r in enumerate(rows):
            if _is_missing(r.get(key)):
                result[i][key] = missing_rank
    return result


def tenure_shrink(score: float, seasons: int, prior: int = 4) -> float:
    """Shrink score toward 0 (not the peer mean) for short samples."""
    if seasons <= 0:
        return 0.0
    weight = seasons / (seasons + max(prior, 0))
    return round(score * weight, 4)


def rank_descending(scores: list[float]) -> list[int]:
    indexed = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
    ranks = [0] * len(scores)
    i = 0
    ordered = indexed
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and math.isclose(ordered[j + 1][1], ordered[i][1]):
            j += 1
        shared = i + 1
        for k in range(i, j + 1):
            ranks[ordered[k][0]] = shared
        i = j + 1
    return ranks


def wins_per_100m(wins: float | int, payroll: float | None) -> float:
    if not payroll or payroll <= 0:
        return 0.0
    return float(wins) / (payroll / 100_000_000.0)


def raw_season_payroll_efficiency(row: dict[str, Any]) -> float | None:
    """Paced wins / $100M for one team-season, or None if payroll missing."""
    pay = row.get("payroll")
    if not pay:
        return None
    paced = efficiency_wins(
        int(row["season"]), int(row["wins"]), int(row["losses"])
    )
    return wins_per_100m(paced, float(pay))


def attach_era_relative_payroll(seasons: list[dict[str, Any]]) -> dict[int, float]:
    """Attach per-season raw PE and era-relative ratio (raw / league-year mean).

    Mutates each season row: payroll_efficiency_raw, payroll_efficiency_era.
    Returns {year: league mean raw PE} for tests/diagnostics.
    """
    by_year: dict[int, list[float]] = {}
    for row in seasons:
        raw = raw_season_payroll_efficiency(row)
        if raw is None:
            continue
        by_year.setdefault(int(row["season"]), []).append(raw)
    year_mean = {
        year: statistics.fmean(vals) for year, vals in by_year.items() if vals
    }
    for row in seasons:
        raw = raw_season_payroll_efficiency(row)
        row["payroll_efficiency_raw"] = (
            round(raw, 4) if raw is not None else None
        )
        mean = year_mean.get(int(row["season"]))
        if raw is None or not mean or mean <= 0:
            row["payroll_efficiency_era"] = None
        else:
            row["payroll_efficiency_era"] = round(raw / mean, 4)
    return year_mean


def payroll_efficiency_from_seasons(
    season_rows: list[dict[str, Any]],
    year_means: dict[int, float] | None = None,
) -> tuple[float, int | None]:
    """Era-relative thrift: mean of (wins/$100M ÷ that year's league mean).

    Seasons missing payroll are dropped. 1.0 ≈ league-average thrift for the
    years played; >1 is thriftier than peers that season. Prefers pre-attached
    ``payroll_efficiency_era``; otherwise uses ``year_means`` when provided.
    """
    ratios: list[float] = []
    payroll_sum = 0
    for row in season_rows:
        pay = row.get("payroll")
        if not pay:
            continue
        era = row.get("payroll_efficiency_era")
        if era is None:
            raw = raw_season_payroll_efficiency(row)
            mean = (year_means or {}).get(int(row["season"]))
            if raw is None or not mean or mean <= 0:
                continue
            era = raw / mean
        ratios.append(float(era))
        payroll_sum += int(pay)
    if not ratios or payroll_sum <= 0:
        return 0.0, None
    return round(statistics.fmean(ratios), 4), payroll_sum


def last_complete_season(as_of: Any, window_end: int) -> int:
    """Last finished championship season for ranking aggregates.

    Before October, the current calendar year's season is still in progress
    (or just ended without a settled postseason book), so drop it.
    """
    year = int(as_of.year)
    month = int(as_of.month)
    complete = year if month >= 10 else year - 1
    return min(int(window_end), complete)


def attach_rates(metrics: dict[str, Any]) -> dict[str, Any]:
    """Add per-season rates; keep counts under *_count aliases when present."""
    seasons = max(int(metrics.get("seasons") or 0), 1)
    ws = int(metrics.get("world_series") or metrics.get("world_series_count") or 0)
    pennants = int(metrics.get("pennants") or metrics.get("pennants_count") or 0)
    depth = int(metrics.get("playoff_depth") or metrics.get("playoff_depth_count") or 0)
    metrics["world_series_count"] = ws
    metrics["pennants_count"] = pennants
    metrics["playoff_depth_count"] = depth
    metrics["world_series_rate"] = round(ws / seasons, 4)
    metrics["pennants_rate"] = round(pennants / seasons, 4)
    metrics["playoff_depth_rate"] = round(depth / seasons, 4)
    # Composite keys expect rates; keep legacy names as counts for display.
    metrics["world_series"] = ws
    metrics["pennants"] = pennants
    metrics["playoff_depth"] = depth
    return metrics
