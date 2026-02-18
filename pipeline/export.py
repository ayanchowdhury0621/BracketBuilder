"""
BracketBuilder Export — Generates JSON matching the frontend TypeScript interfaces.

Reads enriched CSVs from data/, maps them to the Team/Game interfaces in
src/app/data/bracketData.ts, and writes JSON to data/export/.

Usage:
    python -m pipeline.export          # generate all export JSONs
    python -m pipeline.export --pretty # human-readable JSON
"""

import argparse
import json
import logging
import os
from typing import Any

import numpy as np
import pandas as pd

from pipeline.config import normalize_team_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
EXPORT_DIR = os.path.join(DATA_DIR, "export")


def load(name: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        logger.warning("File not found: %s", path)
        return pd.DataFrame()
    return pd.read_csv(path)


# ── Team → Frontend Interface Mapping ────────────────────────────────────────

def build_team_record(row: pd.Series) -> dict[str, Any]:
    """
    Map a row from teams_stats.csv to the frontend Team interface.
    Missing AI fields (rotobotBlurb) are set to placeholder strings.
    """
    pace = float(row.get("pace", 68) or 68)
    topg = float(row.get("topg", 12) or 12)
    tov_pct = round(topg / max(pace, 1) * 100, 1)

    oreb_pg = float(row.get("oreb_pg", 10) or 10)
    dreb_pg_avg = 24.7  # national average opponent DREB PG
    oreb_pct = round(oreb_pg / (oreb_pg + dreb_pg_avg) * 100, 1)

    # Parse recent form string ("WWLWW") → ["W","W","L","W","W"]
    form_str = str(row.get("recent_form", ""))
    recent_form = list(form_str) if form_str else []

    # Key player + stat from leaders
    key_player = str(row.get("key_player", "")) if pd.notna(row.get("key_player")) else ""
    key_stat = str(row.get("key_player_stat", "")) if pd.notna(row.get("key_player_stat")) else ""

    slug = str(row.get("team_slug", "")).strip()
    if not slug:
        slug = normalize_team_name(str(row.get("team_name", ""))).lower().replace(" ", "-")

    team_name = str(row.get("team_name", ""))
    short_name = team_name

    return {
        "id": slug,
        "name": team_name,
        "shortName": short_name,
        "seed": 0,
        "record": str(row.get("record", "")),
        "conference": str(row.get("conference", "")),
        "ppg": round(float(row.get("ppg", 0) or 0), 1),
        "oppg": round(float(row.get("oppg", 0) or 0), 1),
        "pace": round(pace, 1),
        "eFGPct": round(float(row.get("efg_pct", 50) or 50), 1),
        "tovPct": tov_pct,
        "orebPct": oreb_pct,
        "sosRank": int(row.get("sos_rank", 999) or 999),
        "netRank": int(row.get("net_rank", 999) or 999),
        "recentForm": recent_form,
        "color": str(row.get("team_color", "#333333")),
        "rotobotScore": round(float(row.get("power_score", 50) or 50), 0),
        "rotobotBlurb": "",
        "keyPlayer": key_player,
        "keyPlayerStat": key_stat,
        # Style profile: concrete identity + bullets + weakness (for Gemini / UI)
        "styleTags": [t.strip() for t in str(row.get("style_tags", "")).split("|") if t.strip()],
        "styleSummary": str(row.get("style_summary", "")) if pd.notna(row.get("style_summary")) else "",
        "styleIdentity": str(row.get("style_identity", "")) if pd.notna(row.get("style_identity")) else "",
        "styleBullets": str(row.get("style_bullets", "")) if pd.notna(row.get("style_bullets")) else "",
        "styleWeakness": str(row.get("style_weakness", "")) if pd.notna(row.get("style_weakness")) else "",
        # Extended stats for deep comparisons
        "stats": {
            "scoring": {
                "ppg": round(float(row.get("ppg", 0) or 0), 1),
                "oppg": round(float(row.get("oppg", 0) or 0), 1),
                "scoringMargin": round(float(row.get("scoring_margin", 0) or 0), 1),
                "benchPPG": round(float(row.get("bench_ppg", 0) or 0), 1),
                "fastbreakPPG": round(float(row.get("fastbreak_ppg", 0) or 0), 1),
            },
            "shooting": {
                "fgPct": round(float(row.get("fg_pct", 0) or 0), 1),
                "fgPctDefense": round(float(row.get("fg_pct_defense", 0) or 0), 1),
                "threePtPct": round(float(row.get("three_pt_pct", 0) or 0), 1),
                "threePtPctDefense": round(float(row.get("three_pt_pct_defense", 0) or 0), 1),
                "threePG": round(float(row.get("three_pg", 0) or 0), 1),
                "threePtAttemptsPG": round(float(row.get("three_pt_attempts_pg", 0) or 0), 1),
                "ftPct": round(float(row.get("ft_pct", 0) or 0), 1),
                "ftMadePG": round(float(row.get("ft_made_pg", 0) or 0), 1),
                "eFGPct": round(float(row.get("efg_pct", 0) or 0), 1),
            },
            "rebounding": {
                "rpg": round(float(row.get("rpg", 0) or 0), 1),
                "rebMargin": round(float(row.get("reb_margin", 0) or 0), 1),
                "orebPG": round(float(row.get("oreb_pg", 0) or 0), 1),
                "drebPG": round(float(row.get("dreb_pg", 0) or 0), 1),
                "orebPct": oreb_pct,
            },
            "ballControl": {
                "apg": round(float(row.get("apg", 0) or 0), 1),
                "topg": round(float(row.get("topg", 0) or 0), 1),
                "astToRatio": round(float(row.get("ast_to_ratio", 0) or 0), 2),
                "tovPct": tov_pct,
                "turnoverMargin": round(float(row.get("turnover_margin", 0) or 0), 1),
                "turnoversForcedPG": round(float(row.get("turnovers_forced_pg", 0) or 0), 1),
            },
            "defense": {
                "spg": round(float(row.get("spg", 0) or 0), 1),
                "bpg": round(float(row.get("bpg", 0) or 0), 1),
                "fpg": round(float(row.get("fpg", 0) or 0), 1),
                "oppg": round(float(row.get("oppg", 0) or 0), 1),
                "fgPctDefense": round(float(row.get("fg_pct_defense", 0) or 0), 1),
                "threePtPctDefense": round(float(row.get("three_pt_pct_defense", 0) or 0), 1),
            },
            "tempo": {
                "pace": round(pace, 1),
                "winPct": round(float(row.get("win_pct", 0) or 0), 1),
            },
            "rankings": {
                "netRank": int(row.get("net_rank", 999) or 999),
                "apRank": int(row.get("ap_rank", 0) or 0) if pd.notna(row.get("ap_rank")) else None,
                "sosRank": int(row.get("sos_rank", 999) or 999),
                "powerScore": round(float(row.get("power_score", 50) or 50), 1),
            },
            "schedule": {
                "q1Record": str(row.get("q1_record", "")) if pd.notna(row.get("q1_record")) else "",
                "q2Record": str(row.get("q2_record", "")) if pd.notna(row.get("q2_record")) else "",
                "q3Record": str(row.get("q3_record", "")) if pd.notna(row.get("q3_record")) else "",
                "q4Record": str(row.get("q4_record", "")) if pd.notna(row.get("q4_record")) else "",
            },
            "percentiles": _extract_percentiles(row),
        },
    }


def _extract_percentiles(row: pd.Series) -> dict[str, float]:
    pctls = {}
    for col in row.index:
        if col.endswith("_pctl"):
            key = col.replace("_pctl", "")
            val = row[col]
            if pd.notna(val):
                pctls[key] = round(float(val), 1)
    return pctls


# ── Player Export ────────────────────────────────────────────────────────────

def build_player_record(row: pd.Series) -> dict[str, Any]:
    """Map a player row from individual_leaders.csv or player_stats_full.csv."""
    return {
        "name": str(row.get("player_name", "")),
        "team": str(row.get("team_name", "")),
        "teamSlug": str(row.get("team_slug", "")),
        "position": str(row.get("position", "")) if pd.notna(row.get("position")) else "",
        "class": str(row.get("player_class", "")) if pd.notna(row.get("player_class")) else "",
        "height": str(row.get("height", "")) if pd.notna(row.get("height")) else "",
        "gamesPlayed": int(row.get("games_played", 0) or 0),
        "gamesStarted": int(row.get("games_started", 0) or 0),
        "stats": {
            "ppg": round(float(row.get("ppg", 0) or 0), 1),
            "rpg": round(float(row.get("rpg", 0) or 0), 1),
            "apg": round(float(row.get("apg", 0) or 0), 1),
            "spg": round(float(row.get("spg", 0) or 0), 1),
            "bpg": round(float(row.get("bpg", 0) or 0), 1),
            "topg": round(float(row.get("topg", 0) or 0), 1),
            "mpg": round(float(row.get("mpg", 0) or 0), 1),
            "fgPct": round(float(row.get("fg_pct", 0) or 0), 1) if pd.notna(row.get("fg_pct")) else None,
            "ftPct": round(float(row.get("ft_pct", 0) or 0), 1) if pd.notna(row.get("ft_pct")) else None,
            "threePtPct": round(float(row.get("three_pt_pct", 0) or 0), 1) if pd.notna(row.get("three_pt_pct")) else None,
            "eFGPct": round(float(row.get("efg_pct", 0) or 0), 1) if pd.notna(row.get("efg_pct")) else None,
        },
        "perGame": {
            "fgm": round(float(row.get("fgm_pg", 0) or 0), 1),
            "fga": round(float(row.get("fga_pg", 0) or 0), 1),
            "ftm": round(float(row.get("ftm_pg", 0) or 0), 1),
            "fta": round(float(row.get("fta_pg", 0) or 0), 1),
            "threePM": round(float(row.get("three_pm_pg", 0) or 0), 1),
            "threePA": round(float(row.get("three_pa_pg", 0) or 0), 1),
            "oreb": round(float(row.get("oreb_pg", 0) or 0), 1),
        },
        "totals": {
            "pts": int(row.get("total_pts", 0) or 0),
            "reb": int(row.get("total_reb", 0) or 0),
            "ast": int(row.get("total_ast", 0) or 0),
            "stl": int(row.get("total_stl", 0) or 0),
            "blk": int(row.get("total_blk", 0) or 0),
            "fgm": int(row.get("total_fgm", 0) or 0),
            "fga": int(row.get("total_fga", 0) or 0),
        },
        "statSummary": str(row.get("stat_summary", "")) if pd.notna(row.get("stat_summary")) else "",
    }


# ── Matchup Comparison Helper ────────────────────────────────────────────────

def build_matchup_comparison(team1: dict, team2: dict) -> dict[str, Any]:
    """Generate a head-to-head stat comparison between two teams."""
    categories = [
        ("Points Per Game", "ppg", True),
        ("Opp Points Per Game", "oppg", False),
        ("eFG%", "eFGPct", True),
        ("Pace", "pace", None),
        ("Turnover %", "tovPct", False),
        ("OREB%", "orebPct", True),
        ("SOS Rank", "sosRank", False),
        ("NET Rank", "netRank", False),
        ("RotoBot Score", "rotobotScore", True),
    ]

    comparisons = []
    for label, key, higher_is_better in categories:
        v1 = team1.get(key, 0) or 0
        v2 = team2.get(key, 0) or 0

        if higher_is_better is None:
            edge = "neutral"
        elif higher_is_better:
            edge = "team1" if v1 > v2 else ("team2" if v2 > v1 else "even")
        else:
            edge = "team1" if v1 < v2 else ("team2" if v2 < v1 else "even")

        comparisons.append({
            "label": label,
            "key": key,
            "team1Value": v1,
            "team2Value": v2,
            "edge": edge,
        })

    return {"comparisons": comparisons}


# ── Merge Key Players into Team Data ─────────────────────────────────────────

def merge_key_players(teams_df: pd.DataFrame, leaders_df: pd.DataFrame) -> pd.DataFrame:
    """Add key_player and key_player_stat columns from leaders (rank=1)."""
    if leaders_df.empty:
        teams_df["key_player"] = ""
        teams_df["key_player_stat"] = ""
        return teams_df

    top1 = leaders_df[leaders_df["team_rank"] == 1][
        ["team_name_normalized", "player_name", "stat_summary"]
    ].copy()
    top1 = top1.rename(columns={"player_name": "key_player", "stat_summary": "key_player_stat"})
    top1 = top1.drop_duplicates(subset=["team_name_normalized"])

    teams_df = teams_df.merge(top1, on="team_name_normalized", how="left")
    teams_df["key_player"] = teams_df["key_player"].fillna("")
    teams_df["key_player_stat"] = teams_df["key_player_stat"].fillna("")
    return teams_df


# ── Main Export ──────────────────────────────────────────────────────────────

def run_export(pretty: bool = False):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    indent = 2 if pretty else None

    logger.info("Loading data...")
    teams_df = load("teams_stats.csv")
    leaders_df = load("individual_leaders.csv")
    players_df = load("player_stats_full.csv")

    if teams_df.empty:
        logger.error("No teams data found. Run the pipeline first.")
        return

    # Merge key player info
    teams_df = merge_key_players(teams_df, leaders_df)

    # Build all team records
    logger.info("Building team records...")
    all_teams = {}
    for _, row in teams_df.iterrows():
        team = build_team_record(row)
        all_teams[team["id"]] = team

    # Build all player records (top 3 per team)
    logger.info("Building player records...")
    all_players = {}
    if not leaders_df.empty:
        for _, row in leaders_df.iterrows():
            player = build_player_record(row)
            team_slug = player["teamSlug"]
            if team_slug not in all_players:
                all_players[team_slug] = []
            all_players[team_slug].append(player)

    # Full player database (all players, grouped by team)
    full_players = {}
    if not players_df.empty:
        for _, row in players_df.iterrows():
            player = build_player_record(row)
            team_slug = player["teamSlug"]
            if team_slug not in full_players:
                full_players[team_slug] = []
            full_players[team_slug].append(player)

    # Save exports
    def _write(filename: str, data: Any):
        path = os.path.join(EXPORT_DIR, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=indent, default=str)
        logger.info("  Saved %s", path)

    _write("teams.json", all_teams)
    _write("players_top3.json", all_players)
    _write("players_full.json", full_players)

    # Power rankings (sorted by power_score desc)
    power_rankings = sorted(all_teams.values(), key=lambda t: t["rotobotScore"], reverse=True)
    _write("power_rankings.json", [
        {"rank": i + 1, "id": t["id"], "name": t["name"], "score": t["rotobotScore"],
         "record": t["record"], "conference": t["conference"], "netRank": t["netRank"]}
        for i, t in enumerate(power_rankings)
    ])

    # Conference breakdown
    from collections import defaultdict
    conf_teams = defaultdict(list)
    for t in all_teams.values():
        conf_teams[t["conference"]].append({
            "id": t["id"], "name": t["name"], "rotobotScore": t["rotobotScore"],
            "netRank": t["netRank"], "record": t["record"],
        })
    _write("conferences.json", dict(conf_teams))

    # Summary stats
    summary = {
        "totalTeams": len(all_teams),
        "totalPlayers": sum(len(v) for v in full_players.values()),
        "totalLeaders": sum(len(v) for v in all_players.values()),
        "conferencesCount": len(conf_teams),
        "dataFields": {
            "teamStats": 126,
            "playerStats": 45,
            "percentiles": True,
            "powerScore": True,
            "pace": True,
            "sos": True,
            "quadRecords": True,
            "recentForm": True,
            "teamColors": True,
        },
    }
    _write("summary.json", summary)

    logger.info("\nExport complete: %d teams, %d players (top 3: %d)",
                len(all_teams),
                sum(len(v) for v in full_players.values()),
                sum(len(v) for v in all_players.values()))


def main():
    parser = argparse.ArgumentParser(description="BracketBuilder JSON Export")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    run_export(pretty=args.pretty)


if __name__ == "__main__":
    main()
