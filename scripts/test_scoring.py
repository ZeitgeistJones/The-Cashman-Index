#!/usr/bin/env python3
"""Offline tests for ranking composite scoring."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring import (
    attach_rates,
    composite_scores,
    efficiency_wins,
    rank_descending,
    tenure_shrink,
    wins_per_100m,
    zscore,
)

WEIGHTS = {
    "world_series_rate": 0.12,
    "pennants_rate": 0.07,
    "playoff_depth_rate": 0.12,
    "win_pct": 0.10,
    "payroll_efficiency": 0.36,
    "draft_vos": 0.11,
    "trade_net_rate": 0.12,
}


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_zscore_identity() -> None:
    zs = zscore([1.0, 2.0, 3.0])
    check(abs(sum(zs)) < 1e-9, "z-scores should sum ~0")
    check(zs[2] > zs[1] > zs[0], "higher raw → higher z")


def test_wins_per_100m() -> None:
    check(abs(wins_per_100m(90, 180_000_000) - 50.0) < 1e-9, "90 wins / $180M = 50")
    check(wins_per_100m(90, None) == 0.0, "missing payroll → 0")


def test_efficiency_wins_2020_proration() -> None:
    # 40-20 in 60 games → 108 paced wins (40 * 162/60)
    paced = efficiency_wins(2020, 40, 20)
    check(abs(paced - 108.0) < 1e-9, f"2020 40-20 → 108 paced, got {paced}")
    check(efficiency_wins(2019, 40, 20) == 40.0, "non-2020 wins unchanged")
    check(efficiency_wins(2020, 0, 0) == 0.0, "zero games → 0")
    # Relative efficiency preserved: better 2020 team still scores higher.
    good = wins_per_100m(efficiency_wins(2020, 40, 20), 120_000_000)
    bad = wins_per_100m(efficiency_wins(2020, 20, 40), 120_000_000)
    check(good > bad, "proration keeps 2020 relative order")


def test_rates_normalize_longevity() -> None:
    short = attach_rates({"seasons": 2, "world_series": 1, "pennants": 1, "playoff_depth": 6})
    long = attach_rates({"seasons": 20, "world_series": 1, "pennants": 1, "playoff_depth": 6})
    check(short["world_series_rate"] > long["world_series_rate"], "same titles: short tenure has higher rate")
    check(short["playoff_depth_rate"] > long["playoff_depth_rate"], "same depth: short tenure has higher rate")


def test_payroll_heavy_prefers_cheap_contention() -> None:
    rows = [
        {
            "world_series_rate": 0.15,
            "pennants_rate": 0.2,
            "playoff_depth_rate": 2.2,
            "win_pct": 0.58,
            "payroll_efficiency": 40.0,
            "draft_vos": 0.0,
            "trade_net_rate": 0.0,
        },
        {
            "world_series_rate": 0.0,
            "pennants_rate": 0.1,
            "playoff_depth_rate": 1.4,
            "win_pct": 0.53,
            "payroll_efficiency": 120.0,
            "draft_vos": 0.1,
            "trade_net_rate": 0.5,
        },
        {
            "world_series_rate": 0.05,
            "pennants_rate": 0.05,
            "playoff_depth_rate": 0.9,
            "win_pct": 0.50,
            "payroll_efficiency": 60.0,
            "draft_vos": 0.0,
            "trade_net_rate": 0.0,
        },
        {
            "world_series_rate": 0.0,
            "pennants_rate": 0.0,
            "playoff_depth_rate": 0.2,
            "win_pct": 0.45,
            "payroll_efficiency": 35.0,
            "draft_vos": -0.1,
            "trade_net_rate": -0.2,
        },
    ]
    scores = composite_scores(rows, WEIGHTS)
    check(scores[1] > scores[0], f"cheap club should outrank spendy titles: {scores}")
    check(scores[0] > scores[3], f"titles+spend still beats bad+spend: {scores}")


def test_tenure_shrink() -> None:
    check(tenure_shrink(2.0, 20, 4) > tenure_shrink(2.0, 2, 4), "long tenure keeps more score")
    check(abs(tenure_shrink(2.0, 0, 4)) < 1e-9, "zero seasons → 0")


def test_rank_ties() -> None:
    ranks = rank_descending([1.0, 1.0, 0.5])
    check(ranks == [1, 1, 3], f"tied scores share rank 1, got {ranks}")


def main() -> int:
    test_zscore_identity()
    test_wins_per_100m()
    test_efficiency_wins_2020_proration()
    test_rates_normalize_longevity()
    test_payroll_heavy_prefers_cheap_contention()
    test_tenure_shrink()
    test_rank_ties()
    print("all ranking checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
