#!/usr/bin/env python3
"""Offline tests for single-season FO construction helpers."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_season_index import (  # noqa: E402
    horizon_through_season,
    sample_shrink,
    season_attribution_window,
    stock_share_for_team_season,
    vintage_tag,
)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_attribution_window() -> None:
    lo, hi = season_attribution_window(2015)
    check(lo == dt.date(2014, 11, 1), f"lo {lo}")
    check(hi == dt.date(2015, 10, 31), f"hi {hi}")


def test_horizon_clip() -> None:
    as_of = dt.date(2026, 8, 1)
    # Deal mid-2018 + 3y → through 2021
    through = horizon_through_season(dt.date(2018, 7, 31), as_of, 3)
    check(through == 2021, f"expected 2021 got {through}")
    # Recent deal clipped by as_of
    through2 = horizon_through_season(dt.date(2025, 7, 31), as_of, 3)
    check(through2 == 2026, f"as_of clip got {through2}")


def test_vintage_tags() -> None:
    stint = dt.date(2012, 1, 1)
    lo, hi = season_attribution_window(2015)
    check(vintage_tag(dt.date(2010, 6, 1), stint, lo, hi) == "inherited", "prior regime")
    check(vintage_tag(dt.date(2013, 6, 1), stint, lo, hi) == "own_prior", "own prior")
    check(vintage_tag(dt.date(2015, 7, 31), stint, lo, hi) == "same_year", "deadline")
    check(vintage_tag(None, stint, lo, hi) == "inherited", "unknown → inherited")


def test_stock_share_inherited_vs_own() -> None:
    lo, hi = season_attribution_window(2015)
    stint = dt.date(2012, 1, 1)
    team_season_war = {
        (147, 2015): [
            (1, 4.0),  # inherited
            (2, 2.0),  # own prior
            (3, 2.0),  # same year
        ]
    }
    acq = {
        (1, 147): dt.date(2010, 1, 1),
        (2, 147): dt.date(2013, 1, 1),
        (3, 147): dt.date(2015, 7, 1),
    }
    out = stock_share_for_team_season(147, 2015, stint, lo, hi, team_season_war, acq)
    check(out["inherited_war"] == 4.0, out)
    check(out["own_prior_war"] == 2.0, out)
    check(out["same_year_war"] == 2.0, out)
    check(abs(out["stock_share"] - 0.5) < 1e-9, out)


def test_sample_shrink() -> None:
    check(sample_shrink(10.0, 0, 3) == 0.0, "n=0")
    check(sample_shrink(10.0, 3, 3) == 5.0, "half shrink")


def main() -> int:
    test_attribution_window()
    test_horizon_clip()
    test_vintage_tags()
    test_stock_share_inherited_vs_own()
    test_sample_shrink()
    print("all season-index checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
