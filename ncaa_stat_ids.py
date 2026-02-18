"""
Complete mapping of NCAA Men's Basketball D1 stat category IDs.

API Base URL: https://ncaa-api.henrygd.me/stats/basketball-men/d1/current/{type}/{stat_id}
  - type: "team" or "individual"
  - stat_id: numeric ID from the mappings below

Discovered by systematically probing IDs 1-1500 on 2026-02-17.
"""

# ============================================================================
# TEAM STATS (28 categories)
# URL pattern: /stats/basketball-men/d1/current/team/{STAT_ID}
# ============================================================================
TEAM_STATS = {
    # --- Scoring ---
    145: "Scoring Offense",                  # PPG
    146: "Scoring Defense",                  # OPP PPG
    147: "Scoring Margin",                   # SCR MAR

    # --- Shooting ---
    148: "Field Goal Percentage",            # FG%
    149: "Field Goal Percentage Defense",    # OPP FG%
    150: "Free Throw Percentage",            # FT%
    152: "Three Point Percentage",           # 3FG%
    153: "Three Pointers Per Game",          # 3PG
    518: "Three Point Percentage Defense",   # Opp 3FG Pct
    625: "Three Point Attempts Per Game",    # 3FGA Avg
    633: "Free Throws Made Per Game",        # FTM Avg
    638: "Free Throw Attempts Per Game",     # FTA Avg
    1288: "Effective FG pct",                # eFG%

    # --- Rebounds ---
    151: "Rebound Margin",                   # REB MAR
    857: "Rebounds (Offensive) Per Game",     # ORPG
    859: "Rebounds (Defensive) Per Game",     # DRPG
    932: "Rebounds Per Game",                # RPG

    # --- Ball Handling ---
    216: "Assists Per Game",                 # APG
    217: "Turnovers Per Game",               # TOPG
    474: "Assist/Turnover Ratio",            # A/TO
    519: "Turnover Margin",                  # TO MAR
    931: "Turnovers Forced Per Game",        # Opp TO Avg

    # --- Defense ---
    214: "Blocks Per Game",                  # BKPG
    215: "Steals Per Game",                  # STPG

    # --- Other ---
    168: "Winning Percentage",               # W-L Pct
    286: "Fouls Per Game",                   # PFPG
    1284: "Bench Points per game",           # Bench PPG
    1285: "Fastbreak Points",               # FB PPG
}

# ============================================================================
# INDIVIDUAL STATS (24 categories)
# URL pattern: /stats/basketball-men/d1/current/individual/{STAT_ID}
# ============================================================================
INDIVIDUAL_STATS = {
    # --- Per-Game Stats ---
    136: "Points Per Game",                  # PPG
    137: "Rebounds Per Game",                # RPG
    138: "Blocks Per Game",                  # BKPG
    139: "Steals Per Game",                  # STPG
    140: "Assists Per Game",                 # APG
    628: "Minutes Per Game",                 # MPG
    856: "Rebounds (Offensive) Per Game",     # ORPG
    858: "Rebounds (Defensive) Per Game",     # DRPG

    # --- Shooting Percentages ---
    141: "Field Goal Percentage",            # FG%
    142: "Free Throw Percentage",            # FT%
    143: "Three Point Percentage",           # 3FG%
    144: "Three Pointers Per Game",          # 3PG

    # --- Counting Stats (Totals) ---
    600: "Points",                           # PTS total
    601: "Rebounds",                          # REB total
    605: "Assists",                           # AST total
    608: "Blocks",                            # BLKS total
    611: "Field Goals",                       # FGM total
    615: "Steals",                            # ST total
    618: "Field Goal Attempts",              # FGA total
    621: "Total 3-point FGM",                # 3FG total
    624: "Three Point Attempts",             # 3FGA total
    850: "Free Throws",                       # FT total
    851: "Free Throw Attempts",              # FTA total

    # --- Ratio / Milestone Stats ---
    473: "Assist/Turnover Ratio",            # A/TO
    556: "Double Doubles",                   # Dbl Dbl
    557: "Triple Doubles",                   # Trpl Dbl
}


# ============================================================================
# SAMPLE DATA FIELDS (what columns each stat returns)
# ============================================================================
TEAM_STAT_FIELDS = {
    145: ["Rank", "Team", "GM", "PTS", "PPG"],
    146: ["Rank", "Team", "GM", "OPP PTS", "OPP PPG"],
    147: ["Rank", "Team", "GM", "PTS", "PPG", "OPP PTS", "OPP PPG", "SCR MAR"],
    148: ["Rank", "Team", "GM", "FGM", "FGA", "FG%"],
    149: ["Rank", "Team", "GM", "OPP FG", "OPP FGA", "OPP FG%"],
    150: ["Rank", "Team", "GM", "FT", "FTA", "FT%"],
    151: ["Rank", "Team", "GM", "REB", "RPG", "OPP REB", "OPP RPG", "REB MAR"],
    152: ["Rank", "Team", "GM", "3FG", "3FGA", "3FG%"],
    153: ["Rank", "Team", "GM", "3FG", "3PG"],
    168: ["Rank", "Team", "W", "L", "Pct"],
    214: ["Rank", "Team", "GM", "BLKS", "BKPG"],
    215: ["Rank", "Team", "GM", "ST", "STPG"],
    216: ["Rank", "Team", "GM", "AST", "APG"],
    217: ["Rank", "Team", "GM", "TO", "TOPG"],
    286: ["Rank", "Team", "GM", "Fouls", "PFPG", "DQ"],
    474: ["Rank", "Team", "GM", "AST", "TO", "Ratio"],
    518: ["Rank", "Team", "GM", "Opp 3FGA", "Opp 3FG", "Pct"],
    519: ["Rank", "Team", "GM", "Opp TO", "TO", "Ratio"],
    625: ["Rank", "Team", "GM", "3FG", "3FGA", "Avg"],
    633: ["Rank", "Team", "GM", "FT", "FTA", "Avg"],
    638: ["Rank", "Team", "GM", "FT", "FTA", "Avg"],
    857: ["Rank", "Team", "GM", "ORebs", "RPG"],
    859: ["Rank", "Team", "GM", "DRebs", "RPG"],
    931: ["Rank", "Team", "GM", "Opp TO", "Avg"],
    932: ["Rank", "Team", "GM", "ORebs", "DRebs", "REB", "RPG"],
    1284: ["Rank", "Team", "GM", "Bench", "PPG"],
    1285: ["Rank", "Team", "GM", "FB pts", "PPG"],
    1288: ["Rank", "Team", "G", "FGM", "3FG", "FGA", "Pct"],
}

INDIVIDUAL_STAT_FIELDS = {
    136: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "FGM", "3FG", "FT", "PTS", "PPG"],
    137: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "REB", "RPG"],
    138: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "BLKS", "BKPG"],
    139: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "ST", "STPG"],
    140: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "AST", "APG"],
    141: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "FGM", "FGA", "FG%"],
    142: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "FT", "FTA", "FT%"],
    143: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "3FG", "3FGA", "3FG%"],
    144: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "3FG", "3PG"],
    473: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "AST", "TO", "Ratio"],
    556: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "Dbl Dbl"],
    557: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "Trpl Dbl"],
    600: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "FGM", "FT", "PTS"],
    601: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "ORebs", "DRebs", "REB"],
    605: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "AST"],
    608: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "BLKS"],
    611: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "FGM", "FGA"],
    615: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "ST"],
    618: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "FGM", "FGA"],
    621: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "3FG", "3FGA"],
    624: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "3FG", "3FGA"],
    628: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "MP", "MPG"],
    850: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "FT", "FTA"],
    851: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "FT", "FTA"],
    856: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "ORebs", "RPG"],
    858: ["Rank", "Name", "Team", "Cl", "Height", "Position", "G", "DRebs", "RPG"],
}


if __name__ == "__main__":
    print("=" * 70)
    print("NCAA MEN'S BASKETBALL D1 - COMPLETE STAT ID MAPPING")
    print("=" * 70)
    print(f"\nAPI: https://ncaa-api.henrygd.me/stats/basketball-men/d1/current/{{type}}/{{id}}")
    print(f"Pagination: append ?page=N (pages count returned in response)")

    print(f"\n{'='*70}")
    print(f"TEAM STATS ({len(TEAM_STATS)} categories)")
    print(f"{'='*70}")
    for sid in sorted(TEAM_STATS.keys()):
        print(f"  {sid:>5} -> {TEAM_STATS[sid]}")

    print(f"\n{'='*70}")
    print(f"INDIVIDUAL STATS ({len(INDIVIDUAL_STATS)} categories)")
    print(f"{'='*70}")
    for sid in sorted(INDIVIDUAL_STATS.keys()):
        print(f"  {sid:>5} -> {INDIVIDUAL_STATS[sid]}")
