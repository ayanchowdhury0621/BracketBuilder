"""
BracketBuilder Analytics Engine.

Reads raw CSVs from data/raw/, computes percentiles, power scores,
pace estimates, SOS rankings, identifies key players from boxscore data,
and writes enriched CSVs to data/.
"""

import logging
import os
import time

import numpy as np
import pandas as pd

from pipeline.config import (
    POWER_SCORE_WEIGHTS,
    INVERT_STATS,
    TEAM_STAT_EXTRACTION,
    get_team_color,
    normalize_team_name,
)

logger = logging.getLogger(__name__)

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_raw(name: str) -> pd.DataFrame:
    path = os.path.join(RAW_DIR, f"{name}.csv")
    if not os.path.exists(path):
        logger.warning("Raw file not found: %s", path)
        return pd.DataFrame()
    return pd.read_csv(path)


def coerce_numeric(df: pd.DataFrame, exclude: set[str] | None = None) -> pd.DataFrame:
    exclude = exclude or set()
    string_cols = {"team_name", "team_name_normalized", "team_slug", "player_name",
                   "conference", "record", "recent_form", "streak", "player_class",
                   "height", "position", "updated", "team_color",
                   "home_record", "road_record", "neutral_record", "non_d1_record",
                   "quad_1", "quad_2", "quad_3", "quad_4", "stat_summary"}
    string_cols |= exclude

    for col in df.columns:
        if col in string_cols:
            continue
        if df[col].dtype == object:
            cleaned = df[col].astype(str).str.replace("%", "", regex=False).str.strip()
            cleaned = cleaned.replace({"-": np.nan, "": np.nan})
            df[col] = pd.to_numeric(cleaned, errors="coerce")
    return df


# ── Percentile Ranks ─────────────────────────────────────────────────────────

def compute_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    stat_cols = [cfg["rename"] for cfg in TEAM_STAT_EXTRACTION.values()]
    stat_cols_present = [c for c in stat_cols if c in df.columns and df[c].notna().sum() > 10]

    for col in stat_cols_present:
        pctl_col = f"{col}_pctl"
        if col in INVERT_STATS:
            df[pctl_col] = (1 - df[col].rank(ascending=True, pct=True, na_option="bottom")) * 100
        else:
            df[pctl_col] = df[col].rank(ascending=True, pct=True, na_option="bottom") * 100

    logger.info("  Percentiles computed for %d stat columns", len(stat_cols_present))
    return df


# ── Power Score ──────────────────────────────────────────────────────────────

def compute_power_score(df: pd.DataFrame) -> pd.DataFrame:
    score = pd.Series(0.0, index=df.index)
    weight_sum = 0.0

    for stat_name, weight in POWER_SCORE_WEIGHTS.items():
        pctl_col = f"{stat_name}_pctl"
        if pctl_col in df.columns:
            valid = df[pctl_col].notna()
            score = score.where(~valid, score + df[pctl_col].fillna(50) * weight)
            weight_sum += weight

    if weight_sum > 0:
        df["power_score"] = (score / weight_sum).round(1)
    else:
        df["power_score"] = 50.0

    df["power_score"] = df["power_score"].clip(0, 100)
    logger.info("  Power scores computed (weight coverage: %.0f%%)", weight_sum * 100)
    return df


# ── Pace Estimation ──────────────────────────────────────────────────────────

def compute_pace(df: pd.DataFrame) -> pd.DataFrame:
    required = ["fga_total", "games_played", "fta_total", "oreb_pg", "topg"]
    available = [c for c in required if c in df.columns]

    if len(available) < 4:
        if "ppg" in df.columns and "fg_pct" in df.columns:
            fg_pct = df["fg_pct"].fillna(45) / 100
            fga_est = df["ppg"].fillna(70) / (fg_pct * 2)
            topg = df["topg"].fillna(13) if "topg" in df.columns else 13
            df["pace"] = (fga_est + topg + 15).round(1)
        else:
            df["pace"] = np.nan
        return df

    games = pd.to_numeric(df["games_played"], errors="coerce").fillna(1).clip(lower=1)
    fga_pg = pd.to_numeric(df["fga_total"], errors="coerce").fillna(0) / games
    fta_pg = pd.to_numeric(df["fta_total"], errors="coerce").fillna(0) / games
    oreb_pg = pd.to_numeric(df["oreb_pg"], errors="coerce").fillna(0)
    topg = pd.to_numeric(df["topg"], errors="coerce").fillna(0)

    df["pace"] = (fga_pg + 0.44 * fta_pg - oreb_pg + topg).round(1)
    logger.info("  Pace estimated: mean=%.1f, range=[%.1f, %.1f]",
                df["pace"].mean(), df["pace"].min(), df["pace"].max())
    return df


# ── SOS from Quad Records ───────────────────────────────────────────────────

def parse_quad_record(quad_str: str) -> tuple[int, int]:
    if not isinstance(quad_str, str) or "-" not in quad_str:
        return 0, 0
    parts = quad_str.strip().split("-")
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 0, 0


def compute_sos(df: pd.DataFrame, net_df: pd.DataFrame) -> pd.DataFrame:
    if net_df.empty:
        df["sos_rank"] = np.nan
        df["sos_raw"] = np.nan
        return df

    sos_rows = []
    for _, row in net_df.iterrows():
        q1w, q1l = parse_quad_record(str(row.get("quad_1", "")))
        q2w, q2l = parse_quad_record(str(row.get("quad_2", "")))
        q3w, q3l = parse_quad_record(str(row.get("quad_3", "")))
        q4w, q4l = parse_quad_record(str(row.get("quad_4", "")))

        total = q1w + q1l + q2w + q2l + q3w + q3l + q4w + q4l
        if total == 0:
            sos_raw = 0
        else:
            sos_raw = ((q1w + q1l) * 4 + (q2w + q2l) * 3 + (q3w + q3l) * 2 + (q4w + q4l) * 1) / total

        sos_rows.append({
            "team_name_normalized": normalize_team_name(str(row.get("team_name", ""))),
            "sos_raw": round(sos_raw, 3),
            "q1_record": f"{q1w}-{q1l}",
            "q2_record": f"{q2w}-{q2l}",
            "q3_record": f"{q3w}-{q3l}",
            "q4_record": f"{q4w}-{q4l}",
        })

    sos_df = pd.DataFrame(sos_rows)
    sos_df["sos_rank"] = sos_df["sos_raw"].rank(ascending=False, method="min").astype(int)

    df = df.merge(
        sos_df[["team_name_normalized", "sos_raw", "sos_rank", "q1_record", "q2_record", "q3_record", "q4_record"]],
        on="team_name_normalized", how="left",
    )
    logger.info("  SOS computed from quad records: %d teams", sos_df["sos_raw"].notna().sum())
    return df


# ── Key Players from Boxscores ───────────────────────────────────────────────

def identify_key_players(player_stats: pd.DataFrame, leaderboard: pd.DataFrame) -> pd.DataFrame:
    """
    Build the individual leaders table from boxscore aggregates.
    Falls back to leaderboard data for players not in recent boxscores.
    Top 3 per team by PPG with full stat lines.
    """
    if player_stats.empty:
        logger.warning("  No boxscore player stats available")
        if not leaderboard.empty and "ppg" in leaderboard.columns:
            logger.info("  Falling back to leaderboard data")
            return _leaders_from_leaderboard(leaderboard)
        return pd.DataFrame()

    df = player_stats.copy()
    df = df[df["games_played"] >= 1].copy()

    # Filter out very low-minute players (likely walk-ons or garbage time)
    if "mpg" in df.columns:
        df = df[df["mpg"] >= 5.0].copy()

    df = df.sort_values("ppg", ascending=False)
    top3 = df.groupby("team_name").head(3).copy()
    top3["team_rank"] = top3.groupby("team_name").cumcount() + 1

    # Enrich with class/height from leaderboard if available
    if not leaderboard.empty:
        meta_cols = ["player_name", "team_name"]
        for col in ["player_class", "height"]:
            if col in leaderboard.columns:
                meta_cols.append(col)
        if len(meta_cols) > 2:
            meta = leaderboard[meta_cols].drop_duplicates(subset=["player_name", "team_name"])
            top3 = top3.merge(meta, on=["player_name", "team_name"], how="left")

    # Build stat summary string
    summaries = []
    for _, row in top3.iterrows():
        parts = []
        if pd.notna(row.get("ppg")) and row["ppg"] > 0:
            parts.append(f"{row['ppg']:.1f} PPG")
        if pd.notna(row.get("rpg")) and row["rpg"] > 0:
            parts.append(f"{row['rpg']:.1f} RPG")
        if pd.notna(row.get("apg")) and row["apg"] > 0:
            parts.append(f"{row['apg']:.1f} APG")
        if pd.notna(row.get("spg")) and row["spg"] >= 1.5:
            parts.append(f"{row['spg']:.1f} SPG")
        if pd.notna(row.get("bpg")) and row["bpg"] >= 1.5:
            parts.append(f"{row['bpg']:.1f} BPG")
        summaries.append(" / ".join(parts) if parts else "")
    top3["stat_summary"] = summaries

    top3["team_name_normalized"] = top3["team_name"].apply(normalize_team_name)

    logger.info("  Key players (boxscore): %d players across %d teams, avg %.1f GP",
                len(top3), top3["team_name"].nunique(), top3["games_played"].mean())

    null_check = {
        "ppg": top3["ppg"].isna().sum(),
        "rpg": top3["rpg"].isna().sum(),
        "apg": top3["apg"].isna().sum(),
        "fg_pct": top3["fg_pct"].isna().sum() if "fg_pct" in top3.columns else -1,
    }
    logger.info("  Null counts in top3: %s", null_check)

    return top3


def _leaders_from_leaderboard(leaderboard: pd.DataFrame) -> pd.DataFrame:
    """Fallback: build leaders from national leaderboard when no boxscores."""
    df = leaderboard.copy()
    df = coerce_numeric(df, exclude={"player_name", "team_name", "team_name_normalized",
                                      "player_class", "height", "position"})
    df = df.dropna(subset=["ppg"])
    df = df.sort_values("ppg", ascending=False)
    top3 = df.groupby("team_name").head(3).copy()
    top3["team_rank"] = top3.groupby("team_name").cumcount() + 1
    top3["team_name_normalized"] = top3["team_name"].apply(normalize_team_name)
    return top3


def merge_leaderboard_into_player_stats(
    player_stats: pd.DataFrame,
    leaderboard: pd.DataFrame,
) -> pd.DataFrame:
    """
    Override boxscore-derived stats with NCAA official leaderboard stats when
    we have a match (player_name + team_name). Fixes cases where boxscores
    are incomplete but the NCAA API has full-season PPG/rpg/apg/etc.
    """
    if player_stats.empty or leaderboard.empty:
        return player_stats
    lb = leaderboard.copy()
    lb = coerce_numeric(lb, exclude={"player_name", "team_name", "player_class", "height", "position"})
    stat_cols = [c for c in ["ppg", "rpg", "apg", "spg", "bpg", "mpg", "fg_pct", "ft_pct", "three_pt_pct"]
                 if c in lb.columns]
    if not stat_cols:
        return player_stats
    ps = player_stats.copy()
    ps["_pn"] = ps["player_name"].astype(str).str.strip().str.lower()
    ps["_tn"] = ps["team_name"].astype(str).str.strip().str.lower()
    lb["_pn"] = lb["player_name"].astype(str).str.strip().str.lower()
    lb["_tn"] = lb["team_name"].astype(str).str.strip().str.lower()
    merge_cols = ["_pn", "_tn"]
    lb_sub = lb[merge_cols + stat_cols].drop_duplicates(merge_cols, keep="first")
    ps = ps.merge(lb_sub, on=merge_cols, how="left", suffixes=("", "_lb"))
    for c in stat_cols:
        if f"{c}_lb" in ps.columns:
            ps[c] = ps[f"{c}_lb"].fillna(ps[c])
            ps = ps.drop(columns=[f"{c}_lb"])
    ps = ps.drop(columns=["_pn", "_tn"], errors="ignore")
    logger.info("  Merged NCAA leaderboard into player_stats (%d stat columns)", len(stat_cols))
    return ps


# ── Team Style Profiles ──────────────────────────────────────────────────────

def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{'st' if n % 10 == 1 else 'nd' if n % 10 == 2 else 'rd' if n % 10 == 3 else 'th'}"


def compute_style_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build concrete, data-driven identity copy — not generic tags.
    Output: 2–3 sentence identity with real stats and conference/national context,
    scouting bullets with numbers, and one clear weakness for matchup narrative.
    """
    # Conference ranks (1 = best in conf for that stat)
    if "conference" in df.columns:
        df["_cr_pace"] = df.groupby("conference")["pace"].rank(ascending=False, method="min").astype("Int64")
        df["_cr_ppg"] = df.groupby("conference")["ppg"].rank(ascending=False, method="min").astype("Int64")
        df["_cr_oppg"] = df.groupby("conference")["oppg"].rank(ascending=True, method="min").astype("Int64")
        df["_cr_efg"] = df.groupby("conference")["efg_pct"].rank(ascending=False, method="min").astype("Int64")
        df["_cr_fg_def"] = df.groupby("conference")["fg_pct_defense"].rank(ascending=True, method="min").astype("Int64")
        df["_cr_oreb"] = df.groupby("conference")["oreb_pg"].rank(ascending=False, method="min").astype("Int64")
        df["_cr_to_forced"] = df.groupby("conference")["turnovers_forced_pg"].rank(ascending=False, method="min").astype("Int64")
        df["_conf_size"] = df.groupby("conference")["conference"].transform("count")
    else:
        for c in ["_cr_pace", "_cr_ppg", "_cr_oppg", "_cr_efg", "_cr_fg_def", "_cr_oreb", "_cr_to_forced", "_conf_size"]:
            df[c] = np.nan

    # National percentiles (already in df from compute_percentiles)
    def pctl(col: str) -> pd.Series:
        if col in df.columns:
            return df[col].fillna(50)
        return pd.Series(50.0, index=df.index)

    identities = []
    bullets_list = []
    weaknesses = []
    tags_col = []  # keep 1–2 very specific phrases, not generic

    for i in range(len(df)):
        r = df.iloc[i]
        conf = str(r.get("conference", ""))
        conf_size = int(r.get("_conf_size", 0)) or 1

        # Raw stats (with safe defaults)
        pace = float(r.get("pace", 68) or 68)
        ppg = float(r.get("ppg", 70) or 70)
        oppg = float(r.get("oppg", 70) or 70)
        efg = float(r.get("efg_pct", 50) or 50)
        fg_def = float(r.get("fg_pct_defense", 45) or 45)
        oreb = float(r.get("oreb_pg", 10) or 10)
        three_pa = float(r.get("three_pt_attempts_pg", 20) or 20)
        three_pct = float(r.get("three_pt_pct", 33) or 33)
        to_forced = float(r.get("turnovers_forced_pg", 12) or 12)
        topg = float(r.get("topg", 12) or 12)
        ast_to = float(r.get("ast_to_ratio", 1.0) or 1.0)
        ft_pct = float(r.get("ft_pct", 70) or 70)
        bench = float(r.get("bench_ppg", 20) or 20)
        fastbreak = float(r.get("fastbreak_ppg", 8) or 8)
        margin = float(r.get("scoring_margin", 0) or 0)

        pace_p = pctl("pace_pctl").iloc[i] if "pace_pctl" in df.columns else 50
        ppg_p = pctl("ppg_pctl").iloc[i] if "ppg_pctl" in df.columns else 50
        # oppg_pctl and fg_pct_defense_pctl already inverted in compute_percentiles (higher = better D)
        oppg_p = pctl("oppg_pctl").iloc[i] if "oppg_pctl" in df.columns else 50
        efg_p = pctl("efg_pct_pctl").iloc[i] if "efg_pct_pctl" in df.columns else 50
        fg_def_p = pctl("fg_pct_defense_pctl").iloc[i] if "fg_pct_defense_pctl" in df.columns else 50

        cr_pace = r.get("_cr_pace")
        cr_oppg = r.get("_cr_oppg")
        cr_efg = r.get("_cr_efg")
        cr_fg_def = r.get("_cr_fg_def")
        cr_oreb = r.get("_cr_oreb")
        cr_to_forced = r.get("_cr_to_forced")

        # ── Identity (2–3 sentences: how they play + one trade-off) ──
        sent_parts = []

        # Tempo + scoring
        if pace_p >= 75:
            sent_parts.append(f"Plays at {pace:.1f} possessions per 40 (top 25% nationally) and scores {ppg:.1f} PPG.")
        elif pace_p <= 25:
            sent_parts.append(f"Slows the game to {pace:.1f} poss/40 and scores {ppg:.1f} PPG in the half-court.")
        else:
            sent_parts.append(f"Averages {ppg:.1f} PPG at {pace:.1f} poss/40.")

        # Shot profile
        if three_pa >= 26 and three_pct >= 35:
            sent_parts.append(f"Heavy three-point attack ({three_pa:.1f} 3PA/G at {three_pct:.1f}%).")
        elif three_pa <= 18 and oreb >= 11:
            sent_parts.append(f"Lives at the rim and on the glass ({oreb:.1f} OREB/G); doesn't rely on the three.")
        elif efg_p >= 70:
            sent_parts.append(f"Elite shot quality — {efg:.1f}% eFG (top tier nationally).")

        # Defense
        if oppg_p >= 80 and fg_def_p >= 80:
            sent_parts.append(f"Defense is the identity: {oppg:.1f} opp PPG, {fg_def:.1f}% opponent FG.")
        elif oppg_p >= 75:
            sent_parts.append(f"Stout defensively ({oppg:.1f} opp PPG).")
        elif oppg_p <= 30:
            sent_parts.append(f"Defense is a concern — allows {oppg:.1f} PPG.")

        # Conference flavor (one concrete line)
        if conf and pd.notna(cr_oppg) and int(cr_oppg) <= 3:
            sent_parts.append(f"Top-3 in the {conf} in defensive efficiency.")
        elif conf and pd.notna(cr_efg) and int(cr_efg) <= 2:
            sent_parts.append(f"One of the {conf}'s most efficient offenses.")
        elif conf and pd.notna(cr_pace) and int(cr_pace) == 1:
            sent_parts.append(f"Fastest pace in the {conf}.")

        identity = " ".join(sent_parts[:4])  # cap 4 clauses
        identities.append(identity)

        # ── Bullets (concrete stats + context) ──
        bullet_parts = []
        if pace_p >= 70:
            bullet_parts.append(f"{pace:.1f} pace (top 30% D1)")
        if oppg_p >= 80:
            bullet_parts.append(f"{oppg:.1f} opp PPG")
        if fg_def_p >= 80:
            bullet_parts.append(f"{fg_def:.1f}% opp FG")
        if efg_p >= 75:
            bullet_parts.append(f"{efg:.1f}% eFG")
        if to_forced >= 14:
            bullet_parts.append(f"{to_forced:.1f} TO forced/G")
        if oreb >= 12:
            bullet_parts.append(f"{oreb:.1f} OREB/G")
        if ast_to >= 1.4 and topg <= 11:
            bullet_parts.append(f"1.4+ A/TO, {topg:.1f} TO/G")
        if conf and pd.notna(cr_oppg):
            bullet_parts.append(f"{_ordinal(int(cr_oppg))} in {conf} (def)")
        if conf and pd.notna(cr_efg):
            bullet_parts.append(f"{_ordinal(int(cr_efg))} in {conf} (off)")
        bullets_list.append(" • ".join(bullet_parts[:5]))

        # ── Weakness (one clear vulnerability) ──
        weak = ""
        if ft_pct < 68 and pctl("ft_pct_pctl").iloc[i] < 35 if "ft_pct_pctl" in df.columns else ft_pct < 68:
            weak = f"Vulnerable at the line ({ft_pct:.1f}% FT)."
        elif topg >= 14 and ast_to < 1.0:
            weak = "Turnover-prone; pressure can speed them up."
        elif oppg_p < 35:
            weak = "Defense has been exploitable."
        elif oreb < 9 and pctl("oreb_pg_pctl").iloc[i] < 30 if "oreb_pg_pctl" in df.columns else oreb < 9:
            weak = "Limited on the offensive glass."
        elif bench < 18:
            weak = "Thin bench — starters carry the load."
        else:
            weak = "No glaring weakness; balanced profile."
        weaknesses.append(weak)

        # ── One specific tag phrase (not generic) ──
        tag_parts = []
        if pace_p >= 78:
            tag_parts.append(f"Fast ({pace:.0f} poss)")
        elif pace_p <= 22:
            tag_parts.append(f"Slow ({pace:.0f} poss)")
        if oppg_p >= 85 and fg_def_p >= 85:
            tag_parts.append(f"Elite D ({oppg:.0f} opp)")
        if three_pa >= 26 and three_pct >= 36:
            tag_parts.append("3-heavy")
        if oreb >= 12:
            tag_parts.append("Crash glass")
        if to_forced >= 14:
            tag_parts.append("Turnover-driven")
        # Fallback: if no extreme tags, pick the team's single best trait
        if not tag_parts:
            best_label, best_val = "", 0
            candidates = [
                (efg_p, f"Efficient ({efg:.1f}% eFG)"),
                (oppg_p, f"Solid D ({oppg:.0f} opp)"),
                (pace_p, f"Pace {pace:.0f}"),
                (ppg_p, f"{ppg:.0f} PPG"),
            ]
            for pval, label in candidates:
                if pval > best_val:
                    best_val, best_label = pval, label
            if best_label:
                tag_parts.append(best_label)

        tags_col.append(" | ".join(tag_parts[:3]) if tag_parts else "")

    df["style_identity"] = identities
    df["style_bullets"] = bullets_list
    df["style_weakness"] = weaknesses
    df["style_tags"] = tags_col
    df["style_summary"] = df["style_identity"] + " " + df["style_weakness"]

    drop_cols = [c for c in ["_cr_pace", "_cr_ppg", "_cr_oppg", "_cr_efg", "_cr_fg_def", "_cr_oreb", "_cr_to_forced", "_conf_size"] if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    logger.info("  Style profiles: identity + bullets + weakness for %d teams", len(df))
    return df


# ── Build Master Table ───────────────────────────────────────────────────────

def build_team_master(
    team_stats: pd.DataFrame,
    net_df: pd.DataFrame,
    ap_df: pd.DataFrame,
    standings_df: pd.DataFrame,
    recent_form_df: pd.DataFrame,
) -> pd.DataFrame:
    if team_stats.empty:
        logger.error("  No team stats to build master table")
        return pd.DataFrame()

    df = team_stats.copy()
    df = coerce_numeric(df)

    # Merge NET rankings
    if not net_df.empty:
        net_cols = ["team_name_normalized", "net_rank", "conference", "record",
                    "road_record", "neutral_record", "home_record",
                    "quad_1", "quad_2", "quad_3", "quad_4"]
        net_subset = net_df[[c for c in net_cols if c in net_df.columns]].copy()
        net_subset = coerce_numeric(net_subset)
        df = df.merge(net_subset, on="team_name_normalized", how="left", suffixes=("", "_net"))
        if "conference" not in df.columns and "conference_net" in df.columns:
            df["conference"] = df["conference_net"]

    # Merge AP rankings
    if not ap_df.empty:
        ap_subset = ap_df[["team_name_normalized", "ap_rank"]].copy()
        ap_subset = coerce_numeric(ap_subset)
        df = df.merge(ap_subset, on="team_name_normalized", how="left")

    # Merge standings
    if not standings_df.empty:
        standings_subset = standings_df[[
            "team_name_normalized", "conf_wins", "conf_losses", "conf_pct", "streak"
        ]].copy()
        standings_subset = coerce_numeric(standings_subset)
        df = df.merge(standings_subset, on="team_name_normalized", how="left", suffixes=("", "_standings"))

    # Merge recent form
    if not recent_form_df.empty:
        form_subset = recent_form_df[["team_name_normalized", "recent_form", "team_slug"]].copy()
        df = df.merge(form_subset, on="team_name_normalized", how="left")

    # Fix eFG% scale
    if "efg_pct" in df.columns and df["efg_pct"].max() < 1.0:
        df["efg_pct"] = (df["efg_pct"] * 100).round(1)

    # Compute percentiles
    df = compute_percentiles(df)

    # Compute pace
    df = compute_pace(df)

    # Compute SOS
    df = compute_sos(df, load_raw("net_rankings") if net_df.empty else net_df)

    # NET rank percentile
    if "net_rank" in df.columns and df["net_rank"].notna().sum() > 10:
        df["net_rank_pctl"] = (1 - df["net_rank"].rank(ascending=True, pct=True)) * 100

    # Compute power score
    df = compute_power_score(df)

    # Add team colors
    df["team_color"] = df["team_name"].apply(get_team_color)

    # Add pace percentile
    if "pace" in df.columns and df["pace"].notna().sum() > 10:
        df["pace_pctl"] = df["pace"].rank(ascending=True, pct=True) * 100

    # Derive team style profiles
    df = compute_style_profiles(df)

    df = df.sort_values("power_score", ascending=False).reset_index(drop=True)
    logger.info("  Master table: %d teams, %d columns", len(df), len(df.columns))
    return df


# ── Save ─────────────────────────────────────────────────────────────────────

def save_final(teams_master, individual_leaders, net_df, ap_df, standings_df, player_stats):
    os.makedirs(DATA_DIR, exist_ok=True)

    datasets = {
        "teams_stats.csv": teams_master,
        "individual_leaders.csv": individual_leaders,
        "rankings_net.csv": net_df,
        "rankings_ap.csv": ap_df,
        "standings.csv": standings_df,
    }

    # Also save the full player stats table (all players, not just top 3)
    if player_stats is not None and not player_stats.empty:
        datasets["player_stats_full.csv"] = player_stats

    for filename, df in datasets.items():
        if df is not None and not df.empty:
            path = os.path.join(DATA_DIR, filename)
            df.to_csv(path, index=False)
            logger.info("  Saved %s (%d rows)", path, len(df))


# ── Main ─────────────────────────────────────────────────────────────────────

def run_analytics():
    start = time.time()

    logger.info("=" * 60)
    logger.info("BracketBuilder Analytics Engine (Enhanced)")
    logger.info("=" * 60)

    logger.info("\n📂 Loading raw data...")
    team_stats = load_raw("team_stats")
    individual_leaderboard = load_raw("individual_leaderboard")
    player_stats = load_raw("player_stats")
    net_rankings = load_raw("net_rankings")
    ap_rankings = load_raw("ap_rankings")
    standings = load_raw("standings")
    recent_form = load_raw("recent_form")

    logger.info("\n🔧 Building team master table...")
    teams_master = build_team_master(team_stats, net_rankings, ap_rankings, standings, recent_form)

    logger.info("\n📊 Prefer NCAA official stats over boxscore aggregates where available...")
    player_stats = merge_leaderboard_into_player_stats(player_stats, individual_leaderboard)

    logger.info("\n🏀 Identifying key players (boxscore-driven)...")
    individual_leaders = identify_key_players(player_stats, individual_leaderboard)

    logger.info("\n💾 Saving final CSVs...")
    save_final(teams_master, individual_leaders, net_rankings, ap_rankings, standings, player_stats)

    elapsed = time.time() - start
    logger.info("\n✅ Analytics complete in %.1fs", elapsed)
    return teams_master, individual_leaders
