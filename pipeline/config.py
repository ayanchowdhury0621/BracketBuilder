"""Configuration for the BracketBuilder data pipeline.

Stat IDs, extraction rules, power score weights, team colors, name normalization.
"""

import hashlib

# =============================================================================
# TEAM STAT EXTRACTION RULES
# Maps stat_id -> {primary_col, rename, extra_cols, tier}
# primary_col: the API column name for the main metric
# rename: what we call it in our merged table
# extra_cols: additional columns to keep (API name -> our name)
# tier: 1 = power score input, 2 = matchup context
# =============================================================================

TEAM_STAT_EXTRACTION = {
    # --- TIER 1: Power Score inputs ---
    145: {"primary": "PPG",     "rename": "ppg",                 "extra": {"GM": "games_played", "PTS": "total_pts"}, "tier": 1},
    146: {"primary": "OPP PPG", "rename": "oppg",                "extra": {},                                         "tier": 1},
    147: {"primary": "SCR MAR", "rename": "scoring_margin",      "extra": {},                                         "tier": 1},
    148: {"primary": "FG%",     "rename": "fg_pct",              "extra": {"FGM": "fgm_total", "FGA": "fga_total"},   "tier": 1},
    149: {"primary": "OPP FG%", "rename": "fg_pct_defense",      "extra": {},                                         "tier": 1},
    152: {"primary": "3FG%",    "rename": "three_pt_pct",        "extra": {"3FG": "three_fgm", "3FGA": "three_fga"},  "tier": 1},
    518: {"primary": "Pct",     "rename": "three_pt_pct_defense","extra": {},                                         "tier": 1},
    1288:{"primary": "Pct",     "rename": "efg_pct",             "extra": {},                                         "tier": 1},
    932: {"primary": "RPG",     "rename": "rpg",                 "extra": {},                                         "tier": 1},
    151: {"primary": "REB MAR", "rename": "reb_margin",          "extra": {},                                         "tier": 1},
    216: {"primary": "APG",     "rename": "apg",                 "extra": {},                                         "tier": 1},
    474: {"primary": "Ratio",   "rename": "ast_to_ratio",        "extra": {},                                         "tier": 1},
    217: {"primary": "TOPG",    "rename": "topg",                "extra": {"TO": "to_total"},                         "tier": 1},
    519: {"primary": "Ratio",   "rename": "turnover_margin",     "extra": {},                                         "tier": 1},
    215: {"primary": "STPG",    "rename": "spg",                 "extra": {},                                         "tier": 1},
    214: {"primary": "BKPG",    "rename": "bpg",                 "extra": {},                                         "tier": 1},
    168: {"primary": "Pct",     "rename": "win_pct",             "extra": {"W": "wins", "L": "losses"},               "tier": 1},

    # --- TIER 2: Matchup context ---
    150: {"primary": "FT%",     "rename": "ft_pct",              "extra": {"FT": "ft_total", "FTA": "fta_total"},     "tier": 2},
    633: {"primary": "Avg",     "rename": "ft_made_pg",          "extra": {},                                         "tier": 2},
    638: {"primary": "Avg",     "rename": "ft_attempts_pg",      "extra": {},                                         "tier": 2},
    857: {"primary": "RPG",     "rename": "oreb_pg",             "extra": {"ORebs": "oreb_total"},                    "tier": 2},
    859: {"primary": "RPG",     "rename": "dreb_pg",             "extra": {},                                         "tier": 2},
    153: {"primary": "3PG",     "rename": "three_pg",            "extra": {},                                         "tier": 2},
    625: {"primary": "Avg",     "rename": "three_pt_attempts_pg","extra": {},                                         "tier": 2},
    1284:{"primary": "PPG",     "rename": "bench_ppg",           "extra": {},                                         "tier": 2},
    1285:{"primary": "PPG",     "rename": "fastbreak_ppg",       "extra": {},                                         "tier": 2},
    286: {"primary": "PFPG",    "rename": "fpg",                 "extra": {},                                         "tier": 2},
    931: {"primary": "Avg",     "rename": "turnovers_forced_pg", "extra": {},                                         "tier": 2},
}


# =============================================================================
# INDIVIDUAL STAT EXTRACTION RULES
# =============================================================================

INDIVIDUAL_STAT_EXTRACTION = {
    136: {"primary": "PPG",   "rename": "ppg"},
    137: {"primary": "RPG",   "rename": "rpg"},
    140: {"primary": "APG",   "rename": "apg"},
    139: {"primary": "STPG",  "rename": "spg"},
    138: {"primary": "BKPG",  "rename": "bpg"},
    141: {"primary": "FG%",   "rename": "fg_pct"},
    143: {"primary": "3FG%",  "rename": "three_pt_pct"},
    628: {"primary": "MPG",   "rename": "mpg"},
}

INDIVIDUAL_COMMON_COLS = ["Name", "Team", "Cl", "Height", "Position", "G"]


# =============================================================================
# POWER SCORE WEIGHTS (must sum to 1.0)
# Higher percentile = better for all of these (some need inversion)
# =============================================================================

POWER_SCORE_WEIGHTS = {
    "scoring_margin":       0.15,
    "efg_pct":              0.12,
    "fg_pct_defense":       0.10,   # lower is better → invert percentile
    "three_pt_pct_defense": 0.08,   # lower is better → invert percentile
    "turnover_margin":      0.10,
    "ast_to_ratio":         0.08,
    "reb_margin":           0.10,
    "spg":                  0.035,
    "bpg":                  0.035,
    "three_pt_pct":         0.08,
    "win_pct":              0.07,
    "net_rank":             0.05,   # lower is better → invert percentile
}

# Stats where LOWER raw values are BETTER (need percentile inversion)
INVERT_STATS = {"fg_pct_defense", "three_pt_pct_defense", "oppg", "topg", "fpg"}


# =============================================================================
# TEAM NAME NORMALIZATION
# Manual overrides for names that differ between API endpoints
# Maps variant names → canonical name (as it appears in team stats)
# =============================================================================

NAME_OVERRIDES = {
    "UConn": "Connecticut",
    "UCONN": "Connecticut",
    "N.C. State": "NC State",
    "UNC": "North Carolina",
    "UNC Wilmington": "NC-Wilmington",
    "UNC Greensboro": "NC-Greensboro",
    "UNC Asheville": "NC-Asheville",
    "UMass": "Massachusetts",
    "UMBC": "MD-Baltimore County",
    "Ole Miss": "Mississippi",
    "Pitt": "Pittsburgh",
    "SMU": "Southern Methodist",
    "VCU": "Virginia Commonwealth",
    "UCF": "Central Florida",
    "UTEP": "UT El Paso",
    "UTSA": "UT San Antonio",
    "SIUE": "SIU Edwardsville",
    "LMU (CA)": "Loyola Marymount",
    "USC": "Southern California",
    "LSU": "Louisiana State",
    "BYU": "Brigham Young",
    "TCU": "Texas Christian",
    "UAB": "Alabama-Birmingham",
    "UNLV": "Nevada-Las Vegas",
}


def normalize_team_name(name: str) -> str:
    """Normalize a team name for matching across endpoints."""
    if not name:
        return ""
    name = name.strip()
    if name in NAME_OVERRIDES:
        return NAME_OVERRIDES[name]
    return name


# =============================================================================
# TEAM COLORS (primary hex, keyed by canonical team name)
# Comprehensive map for Power conferences + notable mid-majors.
# Teams not listed get a deterministic hash-based color.
# =============================================================================

TEAM_COLORS = {
    # --- ACC ---
    "Boston College": "#8C2633", "California": "#003262", "Clemson": "#F56600",
    "Duke": "#002F87", "Florida St.": "#782F40", "Georgia Tech": "#B3A369",
    "Louisville": "#AD0000", "Miami (FL)": "#005030", "North Carolina": "#4B9CD3",
    "NC State": "#CC0000", "Notre Dame": "#0C2340", "Pittsburgh": "#003594",
    "SMU": "#CC0000", "Stanford": "#8C1515", "Syracuse": "#D44500",
    "Virginia": "#232D4B", "Virginia Tech": "#660000", "Wake Forest": "#9E7E38",
    # --- Big Ten ---
    "Illinois": "#E84A27", "Indiana": "#990000", "Iowa": "#FFCD00",
    "Maryland": "#E03C31", "Michigan": "#00274C", "Michigan St.": "#18453B",
    "Minnesota": "#7A0019", "Nebraska": "#E41C38", "Northwestern": "#4E2A84",
    "Ohio St.": "#BB0000", "Oregon": "#007030", "Penn St.": "#003087",
    "Purdue": "#CEB888", "Rutgers": "#CC0033", "UCLA": "#003B5C",
    "USC": "#990000", "Washington": "#4B2E83", "Wisconsin": "#C5050C",
    # --- Big 12 ---
    "Arizona": "#003366", "Arizona St.": "#8C1D40", "Baylor": "#003015",
    "BYU": "#005DAA", "Cincinnati": "#E00122", "Colorado": "#CFB87C",
    "Houston": "#C8102E", "Iowa St.": "#C8102E", "Kansas": "#003087",
    "Kansas St.": "#512888", "Oklahoma St.": "#FF6600", "TCU": "#4D1979",
    "Texas Tech": "#CC0000", "UCF": "#BA9B37", "Utah": "#CC0000",
    "West Virginia": "#002855",
    # --- SEC ---
    "Alabama": "#9E1B32", "Arkansas": "#9D2235", "Auburn": "#0C2340",
    "Florida": "#0021A5", "Georgia": "#BA0C2F", "Kentucky": "#005DAA",
    "LSU": "#461D7C", "Mississippi": "#CE1126", "Mississippi St.": "#660000",
    "Missouri": "#F1B82D", "Oklahoma": "#841617", "South Carolina": "#73000A",
    "Tennessee": "#FF8200", "Texas": "#BF5700", "Texas A&M": "#500000",
    "Vanderbilt": "#866D4B",
    # --- Big East ---
    "Butler": "#13294B", "Creighton": "#005CA9", "DePaul": "#005EB8",
    "Georgetown": "#041E42", "Marquette": "#003366", "Providence": "#000000",
    "Seton Hall": "#004488", "St. John's (NY)": "#CC0000",
    "UConn": "#000E2F", "Connecticut": "#000E2F", "Villanova": "#003DA5",
    "Xavier": "#0C2340",
    # --- Pac-12 remnants / WCC / Mountain West / AAC / A-10 ---
    "Gonzaga": "#002469", "San Diego St.": "#A6192E", "Boise St.": "#0033A0",
    "Nevada": "#003366", "UNLV": "#CF0A2C", "Colorado St.": "#1E4D2B",
    "New Mexico": "#BA0C2F", "Wyoming": "#492F24", "Air Force": "#0033A0",
    "Fresno St.": "#DB0032", "San Jose St.": "#0055A2", "Utah St.": "#003263",
    "Memphis": "#003087", "Tulane": "#006747", "Wichita St.": "#FFC72C",
    "SMU": "#CC0000", "Temple": "#9D2235", "East Carolina": "#4B1869",
    "Dayton": "#004B8D", "Saint Louis": "#005DAA", "VCU": "#FFCC00",
    "Richmond": "#990000", "George Mason": "#006633", "St. Bonaventure": "#6F4E37",
    "Davidson": "#CC0000", "Rhode Island": "#003DA5", "Fordham": "#6D0023",
    "George Washington": "#004C97", "La Salle": "#002F6C", "Loyola Chicago": "#862633",
    # --- Notable mid-majors / frequent tourney teams ---
    "Oral Roberts": "#002D6A", "Saint Mary's (CA)": "#004C97",
    "Drake": "#004477", "Belmont": "#003366", "Murray St.": "#002144",
    "Chattanooga": "#002F6C", "UAB": "#1E6B52", "Loyola Marymount": "#6D2E46",
    "San Francisco": "#006633", "Santa Clara": "#AA1F2E",
    "Vermont": "#005A43", "Iona": "#6D2E46", "Fairleigh Dickinson": "#002D72",
    "Grand Canyon": "#522398", "Liberty": "#002D62",
    "North Texas": "#00853E", "Louisiana Tech": "#002F8B",
    "Troy": "#8B2332", "James Madison": "#450084",
    "Yale": "#00356B", "Princeton": "#FF8F00", "Harvard": "#A41034",
    "Penn": "#002855", "Columbia": "#003399", "Brown": "#4E3629",
    "Cornell": "#B31B1B", "Dartmouth": "#00693E",
    "Colgate": "#821019", "Bucknell": "#FF5F05", "Lehigh": "#653600",
    "Holy Cross": "#602D89", "Navy": "#003B5C", "Army": "#000000",
    "McNeese": "#0067A0", "Samford": "#CC2244", "High Point": "#440099",
    "Norfolk St.": "#007041", "Stetson": "#006747", "Morehead St.": "#003087",
    "Robert Morris": "#005CB9", "Georgia St.": "#0039A6",
    "Cleveland St.": "#006747",
}


def get_team_color(team_name: str) -> str:
    """Get hex color for a team. Falls back to hash-based color for unknowns."""
    if team_name in TEAM_COLORS:
        return TEAM_COLORS[team_name]
    h = hashlib.md5(team_name.encode()).hexdigest()
    r = int(h[0:2], 16) % 180 + 40
    g = int(h[2:4], 16) % 180 + 40
    b = int(h[4:6], 16) % 180 + 40
    return f"#{r:02x}{g:02x}{b:02x}"


# =============================================================================
# QA THRESHOLDS (reasonable ranges for men's D1 basketball)
# =============================================================================

QA_RANGES = {
    "ppg":            (55.0, 100.0),
    "oppg":           (55.0, 95.0),
    "scoring_margin": (-25.0, 30.0),
    "fg_pct":         (35.0, 55.0),
    "fg_pct_defense": (35.0, 55.0),
    "three_pt_pct":   (25.0, 45.0),
    "efg_pct":        (40.0, 62.0),
    "ft_pct":         (55.0, 85.0),
    "rpg":            (25.0, 45.0),
    "reb_margin":     (-12.0, 12.0),
    "apg":            (8.0, 22.0),
    "topg":           (8.0, 20.0),
    "spg":            (3.0, 12.0),
    "bpg":            (1.0, 7.0),
    "win_pct":        (3.0, 100.0),
    "ast_to_ratio":   (0.5, 2.2),
}

EXPECTED_D1_TEAM_COUNT = 362
