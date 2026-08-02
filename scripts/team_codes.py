"""Shared MLB team ids and Baseball Reference team codes.

Used by draft VOS (franchise-tenure WAR) and league-wide move scoring
(during-tenure WAR for the focal club).
"""

from __future__ import annotations

# MLBAM team_id → display meta
TEAMS: dict[int, dict[str, str]] = {
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

YANKEES_MLBAM_ID = 147

# Historical BRef aliases so mid-era code flips don't zero tenure WAR.
TEAM_BREF_CODES: dict[int, frozenset[str]] = {
    108: frozenset({"ANA", "LAA", "CAL"}),
    109: frozenset({"ARI"}),
    110: frozenset({"BAL"}),
    111: frozenset({"BOS"}),
    112: frozenset({"CHN", "CHC"}),
    113: frozenset({"CIN"}),
    114: frozenset({"CLE", "CLV"}),
    115: frozenset({"COL"}),
    116: frozenset({"DET"}),
    117: frozenset({"HOU"}),
    118: frozenset({"KCA", "KC"}),
    119: frozenset({"LAN", "LAD"}),
    120: frozenset({"WAS", "WSN", "MON"}),
    121: frozenset({"NYN", "NYM"}),
    133: frozenset({"OAK", "ATH"}),
    134: frozenset({"PIT"}),
    135: frozenset({"SDN", "SD"}),
    136: frozenset({"SEA"}),
    137: frozenset({"SFN", "SF"}),
    138: frozenset({"SLN", "STL"}),
    139: frozenset({"TBA", "TBD", "TB"}),
    140: frozenset({"TEX"}),
    141: frozenset({"TOR"}),
    142: frozenset({"MIN"}),
    143: frozenset({"PHI"}),
    144: frozenset({"ATL"}),
    145: frozenset({"CHA", "CWS", "CHW"}),
    146: frozenset({"MIA", "FLO", "FLA"}),
    147: frozenset({"NYA", "NYY"}),
    158: frozenset({"MIL"}),
}


def bref_codes(team_id: int) -> frozenset[str]:
    codes = TEAM_BREF_CODES.get(team_id)
    if not codes:
        raise KeyError(f"No Baseball Reference codes mapped for team_id={team_id}")
    return codes


def team_abbr(team_id: int) -> str:
    return TEAMS.get(team_id, {}).get("abbr", str(team_id))


def team_name(team_id: int) -> str:
    return TEAMS.get(team_id, {}).get("name", str(team_id))


def all_team_ids() -> list[int]:
    return sorted(TEAMS.keys())
