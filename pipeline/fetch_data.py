"""
BracketBuilder Data Pipeline — Fetch NCAA Men's Basketball D1 data.

Pulls team stats, individual stats (via boxscores), rankings, standings,
and recent game results from the NCAA API.

Usage:
    python -m pipeline.fetch_data                     # full season boxscores (default)
    python -m pipeline.fetch_data --top-teams 200     # backfill only games for top 200 NET teams
    python -m pipeline.fetch_data --lookback 14       # only last 14 days of boxscores
    python -m pipeline.fetch_data --fetch-only        # fetch raw data, skip analytics
    python -m pipeline.fetch_data --analyze-only      # run analytics on cached raw data
    python -m pipeline.fetch_data --season 2024      # fetch a specific season
"""

import argparse
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from pipeline.ncaa_api import NcaaApiClient
from pipeline.config import (
    TEAM_STAT_EXTRACTION,
    INDIVIDUAL_STAT_EXTRACTION,
    INDIVIDUAL_COMMON_COLS,
    normalize_team_name,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def ensure_dirs():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)


# ── Team Stats ───────────────────────────────────────────────────────────────

def fetch_team_stats(client: NcaaApiClient, season: str = "current") -> pd.DataFrame:
    """Fetch all 28 team stat categories across all pages, merge into one wide table."""
    merged = None
    stat_ids = sorted(TEAM_STAT_EXTRACTION.keys())
    total = len(stat_ids)

    for i, stat_id in enumerate(stat_ids, 1):
        cfg = TEAM_STAT_EXTRACTION[stat_id]
        logger.info("  [%d/%d] Fetching team stat %d (%s)...", i, total, stat_id, cfg["rename"])

        data, meta = client.get_team_stat(stat_id, season=season)
        if not data:
            logger.warning("  No data for stat %d", stat_id)
            continue

        df = pd.DataFrame(data)
        primary_col = cfg["primary"]
        rename_to = cfg["rename"]

        if primary_col not in df.columns:
            logger.warning("  Column '%s' not found in stat %d. Available: %s",
                           primary_col, stat_id, list(df.columns))
            continue

        keep_cols = {"Team": "team_name"}
        keep_cols[primary_col] = rename_to

        if merged is None and "GM" in df.columns:
            keep_cols["GM"] = "games_played"
        elif merged is None and "G" in df.columns:
            keep_cols["G"] = "games_played"

        for api_col, our_col in cfg.get("extra", {}).items():
            if api_col in df.columns:
                keep_cols[api_col] = our_col

        if "Rank" in df.columns:
            keep_cols["Rank"] = f"{rename_to}_rank"

        available = {k: v for k, v in keep_cols.items() if k in df.columns}
        subset = df[list(available.keys())].rename(columns=available)

        if merged is None:
            merged = subset
        else:
            dupe_cols = [c for c in subset.columns if c in merged.columns and c != "team_name"]
            if dupe_cols:
                subset = subset.drop(columns=dupe_cols)
            merged = merged.merge(subset, on="team_name", how="outer")

    if merged is not None:
        merged["team_name_normalized"] = merged["team_name"].apply(normalize_team_name)
        logger.info("  Team stats merged: %d teams, %d columns", len(merged), len(merged.columns))

    return merged


# ── Individual Stats (leaderboard, kept for national ranking context) ────────

def fetch_individual_stats(client: NcaaApiClient, season: str = "current") -> pd.DataFrame:
    """Fetch individual stat leaderboards (used for national ranking context)."""
    merged = None
    stat_ids = sorted(INDIVIDUAL_STAT_EXTRACTION.keys())
    total = len(stat_ids)

    for i, stat_id in enumerate(stat_ids, 1):
        cfg = INDIVIDUAL_STAT_EXTRACTION[stat_id]
        logger.info("  [%d/%d] Fetching individual stat %d (%s)...", i, total, stat_id, cfg["rename"])

        data, meta = client.get_individual_stat(stat_id, season=season)
        if not data:
            continue

        df = pd.DataFrame(data)
        primary_col = cfg["primary"]
        rename_to = cfg["rename"]

        if primary_col not in df.columns:
            continue

        keep = {}
        for col in INDIVIDUAL_COMMON_COLS:
            if col in df.columns:
                mapping = {"Name": "player_name", "Team": "team_name", "Cl": "player_class",
                           "Height": "height", "Position": "position", "G": "games"}
                keep[col] = mapping.get(col, col.lower())
        keep[primary_col] = rename_to

        available = {k: v for k, v in keep.items() if k in df.columns}
        subset = df[list(available.keys())].rename(columns=available)

        if merged is None:
            merged = subset
        else:
            join_cols = [c for c in ["player_name", "team_name"] if c in subset.columns and c in merged.columns]
            if not join_cols:
                continue
            new_cols = [c for c in subset.columns if c not in merged.columns or c in join_cols]
            merged = merged.merge(subset[new_cols], on=join_cols, how="outer")

    if merged is not None:
        merged["team_name_normalized"] = merged["team_name"].apply(normalize_team_name)
        logger.info("  Individual leaderboards: %d players, %d columns", len(merged), len(merged.columns))
    return merged


# ── Rankings ─────────────────────────────────────────────────────────────────

def fetch_net_rankings(client: NcaaApiClient) -> pd.DataFrame:
    logger.info("  Fetching NET rankings...")
    data, meta = client.get_net_rankings()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    rename = {
        "Rank": "net_rank", "School": "team_name", "Record": "record",
        "Conf": "conference", "Road": "road_record", "Neutral": "neutral_record",
        "Home": "home_record", "Prev": "net_prev", "Non-Div I": "non_d1_record",
        "Quad 1": "quad_1", "Quad 2": "quad_2",
        "Quad 3": "quad_3", "Quad 4": "quad_4",
    }
    available = {k: v for k, v in rename.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available)
    df["team_name_normalized"] = df["team_name"].apply(normalize_team_name)
    df["updated"] = meta.get("updated", "")
    logger.info("  NET rankings: %d teams", len(df))
    return df


def fetch_ap_rankings(client: NcaaApiClient) -> pd.DataFrame:
    logger.info("  Fetching AP rankings...")
    data, meta = client.get_ap_rankings()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    rows = []
    for _, row in df.iterrows():
        raw = dict(row)
        school_col = [c for c in raw.keys() if "SCHOOL" in c.upper()]
        school_val = raw[school_col[0]] if school_col else ""
        name = school_val.split("(")[0].strip() if "(" in school_val else school_val.strip()
        first_votes = ""
        if "(" in school_val and ")" in school_val:
            first_votes = school_val.split("(")[1].split(")")[0].strip()
        rows.append({
            "ap_rank": raw.get("RANK", raw.get("Rank", "")),
            "team_name": name,
            "first_votes": first_votes,
            "record": raw.get("RECORD", raw.get("Record", "")),
            "points": raw.get("POINTS", raw.get("Points", "")),
            "previous": raw.get("PREVIOUS", raw.get("Previous", "")),
        })
    result = pd.DataFrame(rows)
    result["team_name_normalized"] = result["team_name"].apply(normalize_team_name)
    result["updated"] = meta.get("updated", "")
    logger.info("  AP rankings: %d teams", len(result))
    return result


# ── Standings ────────────────────────────────────────────────────────────────

def fetch_standings(client: NcaaApiClient) -> pd.DataFrame:
    logger.info("  Fetching standings...")
    data, meta = client.get_standings()
    if not data:
        return pd.DataFrame()

    rows = []
    for conf_block in data:
        conf_name = conf_block.get("conference", "")
        for team in conf_block.get("standings", []):
            rows.append({
                "conference": conf_name,
                "team_name": team.get("School", ""),
                "conf_wins": team.get("Conference W", ""),
                "conf_losses": team.get("Conference L", ""),
                "conf_pct": team.get("Conference PCT", ""),
                "overall_wins": team.get("Overall W", ""),
                "overall_losses": team.get("Overall L", ""),
                "overall_pct": team.get("Overall PCT", ""),
                "streak": team.get("Overall STREAK", ""),
            })
    df = pd.DataFrame(rows)
    df["team_name_normalized"] = df["team_name"].apply(normalize_team_name)
    df["updated"] = meta.get("updated", "")
    logger.info("  Standings: %d teams across %d conferences", len(df), len(data))
    return df


# ── Recent Form + Game ID Collection ────────────────────────────────────────

SEASON_START = datetime(2025, 11, 4)


def _load_cached_game_ids() -> set[str]:
    """Load game IDs we already have boxscores for."""
    path = os.path.join(RAW_DIR, "boxscore_raw.csv")
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, usecols=["game_id"])
            return set(df["game_id"].astype(str).unique())
        except Exception:
            pass
    return set()


def fetch_season_games(
    client: NcaaApiClient,
    lookback_days: int | None = None,
    net_rankings: pd.DataFrame | None = None,
    top_n_teams: int | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Fetch scoreboards for the season (or a lookback window).
    Returns (recent_form_df, list_of_NEW_game_ids_for_boxscores).

    If lookback_days is None, fetches from SEASON_START to today (full season).
    If top_n_teams is set (e.g. 200), only returns game IDs for games where at least
    one team is in the top N by NET rank — use this to backfill full season for
    top teams without fetching every D1 game.
    """
    today = datetime.now()
    if lookback_days is not None:
        start_date = today - timedelta(days=lookback_days)
    else:
        start_date = SEASON_START

    total_days = (today - start_date).days + 1
    scope = "top %d teams" % top_n_teams if top_n_teams else "all games"
    logger.info("  Fetching scoreboards: %s → %s (%d days), scope=%s...",
                start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), total_days, scope)

    cached_ids = _load_cached_game_ids()
    if cached_ids:
        logger.info("  Found %d previously fetched game IDs in cache", len(cached_ids))

    team_results: dict[str, list] = {}
    all_game_ids: list[str] = []
    new_game_ids: list[str] = []
    game_teams: dict[str, tuple[str, str]] = {}  # game_id -> (away_slug, home_slug)
    name_to_slug: dict[str, str] = {}  # normalized short name -> slug (for NET matching)
    dates_with_games = 0

    for day_offset in range(total_days):
        game_date = start_date + timedelta(days=day_offset)
        date_str = f"{game_date.year}/{game_date.month:02d}/{game_date.day:02d}"

        games, _ = client.get_scoreboard(date_str)
        if not games:
            continue

        dates_with_games += 1
        if dates_with_games % 10 == 0:
            logger.info("    Scanned %d dates so far...", dates_with_games)

        for game_wrapper in games:
            game = game_wrapper.get("game", {})
            if game.get("gameState", "") != "final":
                continue

            game_url = game.get("url", "")
            game_id = game_url.replace("/game/", "").strip("/") if game_url else game.get("gameID", "")
            away_data = game.get("away", {})
            home_data = game.get("home", {})
            away_slug = away_data.get("names", {}).get("seo", "")
            home_slug = home_data.get("names", {}).get("seo", "")
            away_short = away_data.get("names", {}).get("short", "")
            home_short = home_data.get("names", {}).get("short", "")

            for slug, short in [(away_slug, away_short), (home_slug, home_short)]:
                if slug and short:
                    name_to_slug[normalize_team_name(short)] = slug

            if game_id:
                gid = str(game_id)
                game_teams[gid] = (away_slug, home_slug)
                all_game_ids.append(gid)
                if gid not in cached_ids:
                    new_game_ids.append(gid)

            date_key = game.get("startDate", date_str)
            for side in ["away", "home"]:
                team_data = game.get(side, {})
                slug = team_data.get("names", {}).get("seo", "")
                short_name = team_data.get("names", {}).get("short", "")
                is_winner = team_data.get("winner", False)
                if slug:
                    if slug not in team_results:
                        team_results[slug] = []
                    team_results[slug].append((date_key, "W" if is_winner else "L", short_name))

    # Optionally filter to games involving top N teams by NET
    if top_n_teams and net_rankings is not None and not net_rankings.empty and name_to_slug:
        nr = net_rankings.copy()
        nr["net_rank"] = pd.to_numeric(nr["net_rank"], errors="coerce").fillna(9999).astype(int)
        nr["_norm"] = nr["team_name"].astype(str).apply(normalize_team_name)
        nr["_slug"] = nr["_norm"].map(name_to_slug)
        nr = nr.dropna(subset=["_slug"])
        top_slugs = set(nr.nsmallest(top_n_teams, "net_rank")["_slug"].astype(str).tolist())
        logger.info("  Top %d teams by NET → %d slugs for filtering", top_n_teams, len(top_slugs))
        new_game_ids = [gid for gid in new_game_ids if gid in game_teams and (
            game_teams[gid][0] in top_slugs or game_teams[gid][1] in top_slugs
        )]
        all_game_ids = [gid for gid in all_game_ids if gid in game_teams and (
            game_teams[gid][0] in top_slugs or game_teams[gid][1] in top_slugs
        )]
        unique_all = list(dict.fromkeys(all_game_ids))
        unique_new = list(dict.fromkeys(new_game_ids))
        logger.info("  Filtered to %d games involving top %d teams, %d NEW for boxscores",
                    len(unique_all), top_n_teams, len(unique_new))
    else:
        unique_new = list(dict.fromkeys(new_game_ids))
        unique_all = list(dict.fromkeys(all_game_ids))
        logger.info("  Season scan: %d teams, %d total games, %d NEW (not in cache), %d dates with games",
                    len(team_results), len(unique_all), len(unique_new), dates_with_games)

    # Build recent form (last 5 results per team)
    rows = []
    for slug, results in team_results.items():
        results.sort(key=lambda x: x[0], reverse=True)
        last_5 = results[:5]
        form = "".join(r[1] for r in last_5)
        team_name = results[0][2] if results else slug
        rows.append({
            "team_slug": slug,
            "team_name": team_name,
            "recent_form": form,
            "games_found": len(results),
        })

    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["team_slug", "team_name", "recent_form", "games_found"])
    df["team_name_normalized"] = df["team_name"].apply(normalize_team_name)

    return df, unique_new


# ── Boxscore Fetching ────────────────────────────────────────────────────────

BOXSCORE_PLAYER_FIELDS = [
    "firstName", "lastName", "position", "minutesPlayed", "starter",
    "fieldGoalsMade", "fieldGoalsAttempted",
    "freeThrowsMade", "freeThrowsAttempted",
    "threePointsMade", "threePointsAttempted",
    "offensiveRebounds", "totalRebounds",
    "assists", "turnovers", "personalFouls", "steals", "blockedShots", "points",
]


def _safe_float(val) -> float:
    """Parse numeric strings from boxscore data."""
    if val is None or val == "":
        return 0.0
    try:
        return float(str(val).replace("%", "").strip())
    except (ValueError, TypeError):
        return 0.0


def fetch_boxscores(client: NcaaApiClient, game_ids: list[str], append_to_existing: bool = True) -> pd.DataFrame:
    """
    Fetch boxscores for all given game IDs.
    Returns a DataFrame with one row per player-game appearance, full stat lines.
    If append_to_existing, loads previously cached boxscores and merges.
    """
    total = len(game_ids)
    logger.info("  Fetching %d new boxscores...", total)

    all_rows = []
    errors = 0

    for i, gid in enumerate(game_ids, 1):
        if i % 50 == 0 or i == 1:
            logger.info("    Boxscore %d/%d (%.0f%%)...", i, total, i / total * 100)

        try:
            data = client.get_game(f"{gid}/boxscore")
        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.warning("    Error fetching boxscore %s: %s", gid, e)
            continue

        if not data:
            continue

        # Map teamId → team info from the boxscore metadata
        team_map = {}
        for t in data.get("teams", []):
            tid = str(t.get("teamId", ""))
            team_map[tid] = {
                "team_name": t.get("nameShort", t.get("nameFull", "")),
                "team_slug": t.get("seoname", ""),
                "team_color": t.get("color", ""),
            }

        for team_box in data.get("teamBoxscore", []):
            tid = str(team_box.get("teamId", ""))
            tinfo = team_map.get(tid, {})

            for ps in team_box.get("playerStats", []):
                first = ps.get("firstName", "")
                last = ps.get("lastName", "")
                if not last:
                    continue

                row = {
                    "game_id": gid,
                    "team_name": tinfo.get("team_name", ""),
                    "team_slug": tinfo.get("team_slug", ""),
                    "player_name": f"{first} {last}".strip(),
                    "position": ps.get("position", ""),
                    "starter": ps.get("starter", False),
                    "minutes": _safe_float(ps.get("minutesPlayed")),
                    "fgm": _safe_float(ps.get("fieldGoalsMade")),
                    "fga": _safe_float(ps.get("fieldGoalsAttempted")),
                    "ftm": _safe_float(ps.get("freeThrowsMade")),
                    "fta": _safe_float(ps.get("freeThrowsAttempted")),
                    "three_pm": _safe_float(ps.get("threePointsMade")),
                    "three_pa": _safe_float(ps.get("threePointsAttempted")),
                    "oreb": _safe_float(ps.get("offensiveRebounds")),
                    "reb": _safe_float(ps.get("totalRebounds")),
                    "ast": _safe_float(ps.get("assists")),
                    "to": _safe_float(ps.get("turnovers")),
                    "pf": _safe_float(ps.get("personalFouls")),
                    "stl": _safe_float(ps.get("steals")),
                    "blk": _safe_float(ps.get("blockedShots")),
                    "pts": _safe_float(ps.get("points")),
                }
                all_rows.append(row)

    new_df = pd.DataFrame(all_rows)
    if errors > 0:
        logger.warning("    %d boxscore fetch errors out of %d", errors, total)
    logger.info("  New boxscores: %d player-game rows from %d games",
                len(new_df), total - errors)

    if append_to_existing:
        existing_path = os.path.join(RAW_DIR, "boxscore_raw.csv")
        if os.path.exists(existing_path):
            existing_df = pd.read_csv(existing_path)
            logger.info("  Merging with %d existing cached rows", len(existing_df))
            df = pd.concat([existing_df, new_df], ignore_index=True)
            df = df.drop_duplicates(subset=["game_id", "player_name", "team_slug"], keep="last")
        else:
            df = new_df
    else:
        df = new_df

    logger.info("  Total boxscore rows: %d (%d unique players, %d games)",
                len(df),
                df["player_name"].nunique() if not df.empty else 0,
                df["game_id"].nunique() if not df.empty else 0)
    return df


def aggregate_boxscores(box_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate player-game boxscore rows into per-player season averages.
    Returns one row per player with per-game averages and totals.
    """
    if box_df.empty:
        return pd.DataFrame()

    counting_stats = ["fgm", "fga", "ftm", "fta", "three_pm", "three_pa",
                      "oreb", "reb", "ast", "to", "pf", "stl", "blk", "pts", "minutes"]

    agg = box_df.groupby(["player_name", "team_name", "team_slug"]).agg(
        games_played=("game_id", "nunique"),
        games_started=("starter", "sum"),
        position=("position", "first"),
        **{f"total_{s}": (s, "sum") for s in counting_stats},
    ).reset_index()

    gp = agg["games_played"].clip(lower=1)
    agg["ppg"] = (agg["total_pts"] / gp).round(1)
    agg["rpg"] = (agg["total_reb"] / gp).round(1)
    agg["apg"] = (agg["total_ast"] / gp).round(1)
    agg["spg"] = (agg["total_stl"] / gp).round(1)
    agg["bpg"] = (agg["total_blk"] / gp).round(1)
    agg["topg"] = (agg["total_to"] / gp).round(1)
    agg["mpg"] = (agg["total_minutes"] / gp).round(1)
    agg["fpg"] = (agg["total_pf"] / gp).round(1)
    agg["oreb_pg"] = (agg["total_oreb"] / gp).round(1)

    agg["fgm_pg"] = (agg["total_fgm"] / gp).round(1)
    agg["fga_pg"] = (agg["total_fga"] / gp).round(1)
    agg["ftm_pg"] = (agg["total_ftm"] / gp).round(1)
    agg["fta_pg"] = (agg["total_fta"] / gp).round(1)
    agg["three_pm_pg"] = (agg["total_three_pm"] / gp).round(1)
    agg["three_pa_pg"] = (agg["total_three_pa"] / gp).round(1)

    # Shooting percentages from totals (more accurate than averaging per-game %)
    agg["fg_pct"] = np.where(agg["total_fga"] > 0,
                             (agg["total_fgm"] / agg["total_fga"] * 100).round(1), np.nan)
    agg["ft_pct"] = np.where(agg["total_fta"] > 0,
                             (agg["total_ftm"] / agg["total_fta"] * 100).round(1), np.nan)
    agg["three_pt_pct"] = np.where(agg["total_three_pa"] > 0,
                                   (agg["total_three_pm"] / agg["total_three_pa"] * 100).round(1), np.nan)
    agg["efg_pct"] = np.where(agg["total_fga"] > 0,
                              ((agg["total_fgm"] + 0.5 * agg["total_three_pm"]) / agg["total_fga"] * 100).round(1),
                              np.nan)

    agg["team_name_normalized"] = agg["team_name"].apply(normalize_team_name)

    logger.info("  Aggregated: %d players across %d teams (avg %.1f games/player)",
                len(agg), agg["team_name"].nunique(), agg["games_played"].mean())
    return agg


# ── Save ─────────────────────────────────────────────────────────────────────

def save_raw(datasets: dict[str, pd.DataFrame]):
    ensure_dirs()
    for name, df in datasets.items():
        if df is not None and not df.empty:
            path = os.path.join(RAW_DIR, f"{name}.csv")
            df.to_csv(path, index=False)
            logger.info("  Saved %s → %s (%d rows, %d cols)", name, path, len(df), len(df.columns))
        else:
            logger.warning("  Skipping %s (empty)", name)


# ── Main ─────────────────────────────────────────────────────────────────────

def run_fetch(
    season: str = "current",
    lookback_days: int | None = None,
    top_n_teams: int | None = None,
):
    """
    Run the full data fetch pipeline.
    lookback_days: None = full season (Nov 4 to today), int = only last N days.
    top_n_teams: If set (e.g. 200), only fetch boxscores for games involving
        the top N teams by NET — backfills full season for those teams without
        pulling every D1 game.
    """
    client = NcaaApiClient(requests_per_second=4.0)
    start = time.time()

    scope = f"last {lookback_days} days" if lookback_days else "full season"
    if top_n_teams:
        scope += f", top {top_n_teams} teams only"
    logger.info("=" * 60)
    logger.info("BracketBuilder Data Pipeline — Fetch (%s)", scope)
    logger.info("Season: %s", season)
    logger.info("=" * 60)

    logger.info("\n📊 TEAM STATS (28 categories, all pages)")
    team_stats = fetch_team_stats(client, season)

    logger.info("\n📈 RANKINGS")
    net_rankings = fetch_net_rankings(client)
    ap_rankings = fetch_ap_rankings(client)

    logger.info("\n🏆 STANDINGS")
    standings = fetch_standings(client)

    logger.info("\n📅 SEASON GAMES + GAME IDs")
    recent_form, game_ids = fetch_season_games(
        client,
        lookback_days=lookback_days,
        net_rankings=net_rankings,
        top_n_teams=top_n_teams,
    )

    logger.info("\n🏀 INDIVIDUAL STATS (leaderboard context)")
    individual_leaderboard = fetch_individual_stats(client, season)

    logger.info("\n📦 BOXSCORES (%d new games)", len(game_ids))
    boxscore_raw = fetch_boxscores(client, game_ids, append_to_existing=True)

    logger.info("\n🔢 AGGREGATING PLAYER STATS FROM BOXSCORES")
    player_stats = aggregate_boxscores(boxscore_raw)

    logger.info("\n💾 SAVING RAW DATA")
    save_raw({
        "team_stats": team_stats,
        "individual_leaderboard": individual_leaderboard,
        "boxscore_raw": boxscore_raw,
        "player_stats": player_stats,
        "net_rankings": net_rankings,
        "ap_rankings": ap_rankings,
        "standings": standings,
        "recent_form": recent_form,
    })

    elapsed = time.time() - start
    logger.info("\n✅ Fetch complete in %.1fs (%d API requests)", elapsed, client.request_count)
    return {
        "team_stats": team_stats, "individual_leaderboard": individual_leaderboard,
        "player_stats": player_stats, "boxscore_raw": boxscore_raw,
        "net_rankings": net_rankings, "ap_rankings": ap_rankings,
        "standings": standings, "recent_form": recent_form,
    }


def main():
    parser = argparse.ArgumentParser(description="BracketBuilder NCAA Data Pipeline")
    parser.add_argument("--season", default="current", help="Season to fetch (e.g., '2024' for 2024-25)")
    parser.add_argument("--lookback", type=int, default=None,
                        help="Only fetch last N days of boxscores (default: full season)")
    parser.add_argument("--top-teams", type=int, default=None, metavar="N",
                        help="Backfill boxscores only for games involving top N teams by NET (e.g. 200)")
    parser.add_argument("--fetch-only", action="store_true", help="Only fetch raw data, skip analytics")
    parser.add_argument("--analyze-only", action="store_true", help="Only run analytics on cached raw data")
    args = parser.parse_args()

    if args.analyze_only:
        from pipeline.analytics import run_analytics
        run_analytics()
        return

    run_fetch(season=args.season, lookback_days=args.lookback, top_n_teams=args.top_teams)

    if not args.fetch_only:
        from pipeline.analytics import run_analytics
        run_analytics()


if __name__ == "__main__":
    main()
