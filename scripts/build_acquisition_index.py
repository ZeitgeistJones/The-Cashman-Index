#!/usr/bin/env python3
"""Alias — acquisition index is league-wide now.

Prefer: python scripts/build_league_acquisition.py --use-cache
This wrapper forwards to that script so old CI/docs still work.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "build_league_acquisition.py"
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")
