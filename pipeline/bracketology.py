"""
BracketBuilder Bracketology Engine.

Projects a 68-team NCAA Tournament bracket by modeling the Selection Committee's
evaluation process:

1. Project conference tournament champions (auto-bids)
2. Evaluate at-large resumes using a Committee Score
3. Seed all 68 teams on the S-curve
4. Place into 4 regions with conference separation rules
5. Generate all Round of 64 matchups

Supports "shuffle" mode for generating multiple plausible brackets with
controlled randomness around bubble teams and conference tournament outcomes.

Usage:
    python -m pipeline.bracketology              # deterministic best projection
    python -m pipeline.bracketology --shuffle     # random plausible bracket
    python -m pipeline.bracketology --shuffle --variance 0.5
"""

import argparse
import json
import logging
import os
import random
from collections import defaultdict
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

REGIONS = ["East", "West", "South", "Midwest"]

# Conferences the committee treats as "power" — their teams get more benefit of
# the doubt on the bubble and their losses are viewed more favorably.
POWER_CONFERENCES = {"SEC", "Big Ten", "Big 12", "ACC", "Big East"}

# Additional conferences that regularly earn at-large bids
UPPER_MID = {"WCC", "Mountain West", "American", "Atlantic 10", "MVC"}


# ── Quad Record Parsing ──────────────────────────────────────────────────────

def _parse_quad(quad_str) -> tuple[int, int]:
    if not isinstance(quad_str, str) or "-" not in quad_str:
        return 0, 0
    parts = str(quad_str).strip().split("-")
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 0, 0


# ── Committee Score ──────────────────────────────────────────────────────────
#
# This models how the Selection Committee actually evaluates teams.
# The committee does NOT just sort by NET rank. They look at the full resume:
#   - NET rank (primary lens)
#   - Quad 1 wins (the gold standard — beating top opponents)
#   - Quad 3/4 losses (bad losses are devastating)
#   - SOS (were your opponents actually good?)
#   - Win percentage (how many games did you win?)
#   - Conference context (10-loss Big 12 > 3-loss Horizon)
#
# Real committee tendencies encoded:
#   - Q1 wins valued at ~5x Q2 wins
#   - Q3 losses cost ~8 points each; Q4 losses cost ~15
#   - A team with 0 Q1 wins almost never gets an at-large bid
#   - Power conference teams get ~3-5 point boost on the bubble
#   - Recent form matters at the margins

def compute_committee_score(row: pd.Series) -> float:
    """
    Compute a Selection Committee-style evaluation score (0-100 scale).
    Higher = stronger tournament resume.
    """
    net_rank = float(row.get("net_rank", 365) or 365)
    sos_rank = float(row.get("sos_rank", 365) or 365)
    win_pct = float(row.get("win_pct", 50) or 50)
    power_score = float(row.get("power_score", 50) or 50)

    # --- NET Component (35% weight) ---
    # Logarithmic scaling: top-10 teams are tightly grouped, big gaps lower
    net_pctl = max(0, (365 - net_rank) / 365) * 100
    # Boost for elite NET ranks (top 20 get extra credit)
    if net_rank <= 10:
        net_pctl += 8
    elif net_rank <= 20:
        net_pctl += 4
    elif net_rank <= 30:
        net_pctl += 2
    net_component = min(100, net_pctl)

    # --- Quad Record Component (30% weight) ---
    q1w, q1l = _parse_quad(row.get("q1_record", "0-0"))
    q2w, q2l = _parse_quad(row.get("q2_record", "0-0"))
    q3w, q3l = _parse_quad(row.get("q3_record", "0-0"))
    q4w, q4l = _parse_quad(row.get("q4_record", "0-0"))

    # Q1 wins are gold — each one worth 5 points
    # Q2 wins are solid — each worth 2 points
    # Q3/Q4 wins are expected (minimal credit)
    # Q1 losses: playing tough teams is fine, not penalized
    # Q3 losses: bad, -8 each
    # Q4 losses: devastating, -15 each
    quad_raw = (
        q1w * 5.0 +
        q2w * 2.5 +
        q3w * 0.5 +
        q4w * 0.2 -
        q3l * 8.0 -
        q4l * 15.0
    )

    # Zero Q1 wins is a massive red flag for at-large consideration.
    # The committee almost NEVER selects a team with 0 Q1 wins unless
    # they have an extraordinary number of Q2 wins.
    if q1w == 0:
        quad_raw -= 10.0

    # Bonus for elite Q1 resume (6+ Q1 wins is rare and impressive)
    if q1w >= 8:
        quad_raw += 6.0
    elif q1w >= 6:
        quad_raw += 3.0

    # Normalize: typical range is roughly -20 to +40
    quad_component = np.clip((quad_raw + 20) / 60 * 100, 0, 100)

    # --- SOS Component (10% weight) ---
    sos_pctl = max(0, (365 - sos_rank) / 365) * 100

    # --- Win Percentage Component (10% weight) ---
    # Win pct is already 0-100 scale
    win_component = np.clip(win_pct, 0, 100)

    # --- Power Score Component (10% weight) ---
    ps_component = np.clip(power_score, 0, 100)

    # --- Conference Context (5% weight) ---
    conf = str(row.get("conference", ""))
    if conf in POWER_CONFERENCES:
        conf_bonus = 70  # Strong baseline for power conf teams
    elif conf in UPPER_MID:
        conf_bonus = 55
    else:
        conf_bonus = 35  # Mid/low-majors need to prove it more

    # Adjust: teams with great records in power conferences get extra credit
    total_games = q1w + q1l + q2w + q2l + q3w + q3l + q4w + q4l
    pct_tough = (q1w + q1l + q2w + q2l) / max(total_games, 1)
    if pct_tough > 0.5:
        conf_bonus += 10  # More than half your games are Q1/Q2 = tough schedule

    conf_component = np.clip(conf_bonus, 0, 100)

    # --- Record Floor Penalty ---
    # The committee essentially never gives at-large bids to sub-.500 teams.
    # Teams with fewer than 15 wins are extremely rare selections.
    record_str = str(row.get("record", "0-0"))
    try:
        parts = record_str.split("-")
        wins = int(parts[0])
        losses = int(parts[1]) if len(parts) > 1 else 0
        total = wins + losses
        if total > 0 and wins / total < 0.500:
            # Sub-.500 = massive penalty, effectively kills at-large chances
            record_penalty = -25.0
        elif wins < 15:
            record_penalty = -15.0
        elif total > 0 and wins / total < 0.550:
            record_penalty = -8.0
        else:
            record_penalty = 0.0
    except (ValueError, IndexError):
        record_penalty = 0.0

    # --- Combine ---
    committee_score = (
        0.35 * net_component +
        0.30 * quad_component +
        0.10 * sos_pctl +
        0.10 * win_component +
        0.10 * ps_component +
        0.05 * conf_component
    ) + record_penalty

    return round(max(0, committee_score), 2)


# ── Conference Tournament Projection ─────────────────────────────────────────

def project_conference_champions(
    standings: pd.DataFrame,
    teams: pd.DataFrame,
    rng: random.Random | None = None,
    variance: float = 0.0,
) -> dict[str, str]:
    """
    Project the conference tournament champion for each conference.

    Deterministic mode (variance=0): picks the team with the best conference
    record, breaking ties by NET rank.

    Shuffle mode (variance>0): introduces weighted randomness. The regular
    season champion wins ~50-60% of conference tournaments in power conferences.
    Higher variance = more upsets.

    Returns: {conference_name: team_name_normalized}
    """
    # Merge standings with NET + committee data from teams
    standings_with_net = standings.merge(
        teams[["team_name_normalized", "net_rank", "committee_score"]],
        on="team_name_normalized",
        how="left",
    )
    standings_with_net["net_rank"] = pd.to_numeric(standings_with_net["net_rank"], errors="coerce").fillna(999)
    standings_with_net["conf_pct"] = pd.to_numeric(standings_with_net["conf_pct"], errors="coerce").fillna(0)
    standings_with_net["committee_score"] = pd.to_numeric(
        standings_with_net["committee_score"], errors="coerce"
    ).fillna(0)

    champions = {}
    conferences = standings_with_net["conference"].unique()

    for conf in conferences:
        conf_teams = standings_with_net[standings_with_net["conference"] == conf].copy()
        conf_teams = conf_teams.sort_values(
            ["conf_pct", "net_rank"], ascending=[False, True]
        ).reset_index(drop=True)

        if conf_teams.empty:
            continue

        if variance == 0 or rng is None:
            champions[conf] = conf_teams.iloc[0]["team_name_normalized"]
            continue

        # Weighted random selection for shuffle mode.
        # Top seed gets a base probability, declining for lower seeds.
        n = min(len(conf_teams), 6)  # Only top 6 realistically contend
        candidates = conf_teams.head(n)

        # Base weight: top seed gets 50%, 2nd gets 25%, etc. (halving)
        # Variance parameter scales how far from deterministic we go.
        base_weights = np.array([0.50, 0.25, 0.12, 0.07, 0.04, 0.02][:n])

        # Power conferences have more parity → more upset potential
        if conf in POWER_CONFERENCES:
            upset_factor = 1.0 + variance * 0.8
        elif conf in UPPER_MID:
            upset_factor = 1.0 + variance * 0.5
        else:
            # Small conferences: chalk wins more often
            upset_factor = 1.0 + variance * 0.3

        # Flatten weights based on upset factor (higher = more even = more upsets)
        weights = base_weights ** (1.0 / upset_factor)
        weights = weights / weights.sum()

        idx = rng.choices(range(n), weights=weights.tolist(), k=1)[0]
        champions[conf] = candidates.iloc[idx]["team_name_normalized"]

    return champions


# ── At-Large Selection ───────────────────────────────────────────────────────

def select_at_large(
    teams: pd.DataFrame,
    auto_bid_teams: set[str],
    n_spots: int = 36,
    rng: random.Random | None = None,
    variance: float = 0.0,
) -> list[str]:
    """
    Select at-large teams based on committee score.

    In deterministic mode, takes the top N non-auto-bid teams by score.
    In shuffle mode, adds noise around the bubble (last ~8 spots).
    """
    candidates = teams[~teams["team_name_normalized"].isin(auto_bid_teams)].copy()
    candidates = candidates.sort_values("committee_score", ascending=False).reset_index(drop=True)

    if variance == 0 or rng is None:
        selected = candidates.head(n_spots)["team_name_normalized"].tolist()
        last_in = candidates.iloc[n_spots - 1] if n_spots <= len(candidates) else None
        first_out = candidates.iloc[n_spots] if n_spots < len(candidates) else None
        if last_in is not None and first_out is not None:
            logger.info("  Last 4 in: %s",
                        candidates.iloc[n_spots - 4:n_spots]["team_name"].tolist())
            logger.info("  First 4 out: %s",
                        candidates.iloc[n_spots:n_spots + 4]["team_name"].tolist())
        return selected

    # Shuffle mode: lock teams clearly in/out, randomize the bubble
    lock_in_count = max(0, n_spots - 6)  # Top N-6 are locks
    bubble_pool_size = 12  # 6 spots from a pool of 12

    locks = candidates.head(lock_in_count)["team_name_normalized"].tolist()
    bubble_candidates = candidates.iloc[lock_in_count:lock_in_count + bubble_pool_size]

    # Weight by committee score for bubble selection
    scores = bubble_candidates["committee_score"].values
    if len(scores) > 0:
        weights = np.exp((scores - scores.min()) * variance * 0.1)
        weights = weights / weights.sum()
        remaining_spots = n_spots - lock_in_count
        bubble_indices = rng.choices(
            range(len(bubble_candidates)),
            weights=weights.tolist(),
            k=min(remaining_spots, len(bubble_candidates)),
        )
        # Deduplicate
        seen = set()
        unique_indices = []
        for idx in bubble_indices:
            if idx not in seen:
                seen.add(idx)
                unique_indices.append(idx)
        while len(unique_indices) < remaining_spots and len(unique_indices) < len(bubble_candidates):
            for j in range(len(bubble_candidates)):
                if j not in seen:
                    unique_indices.append(j)
                    seen.add(j)
                    if len(unique_indices) >= remaining_spots:
                        break

        bubble_selected = bubble_candidates.iloc[unique_indices]["team_name_normalized"].tolist()
    else:
        bubble_selected = []

    return locks + bubble_selected[:n_spots - len(locks)]


# ── Seeding (S-Curve) ────────────────────────────────────────────────────────

def assign_seeds(
    teams: pd.DataFrame,
    field_teams: list[str],
    rng: random.Random | None = None,
    variance: float = 0.0,
) -> list[dict]:
    """
    Assign seeds 1-16 across 4 regions using the S-curve.

    Overall rank 1-4 → #1 seeds, 5-8 → #2 seeds, etc.
    """
    field = teams[teams["team_name_normalized"].isin(field_teams)].copy()
    field = field.sort_values("committee_score", ascending=False).reset_index(drop=True)

    if variance > 0 and rng is not None:
        # Add small noise to committee score for close teams
        noise = np.array([rng.gauss(0, variance * 1.5) for _ in range(len(field))])
        # Larger noise for teams ranked 15-68 (seed lines 4-16 are more volatile)
        for i in range(len(noise)):
            if i >= 16:
                noise[i] *= 1.5
            elif i >= 8:
                noise[i] *= 1.2
        field["seed_score"] = field["committee_score"] + noise
        field = field.sort_values("seed_score", ascending=False).reset_index(drop=True)

    seeded = []
    for i, (_, row) in enumerate(field.iterrows()):
        overall_rank = i + 1
        seed_line = (i // 4) + 1  # 1-4 → seed 1, 5-8 → seed 2, etc.
        if seed_line > 16:
            seed_line = 16

        seeded.append({
            "team_name_normalized": row["team_name_normalized"],
            "team_name": row.get("team_name", ""),
            "team_slug": str(row.get("team_slug", "")),
            "overall_rank": overall_rank,
            "seed": seed_line,
            "committee_score": row["committee_score"],
            "net_rank": int(row.get("net_rank", 999) or 999),
            "conference": str(row.get("conference", "")),
            "record": str(row.get("record", "")),
            "is_auto_bid": row.get("is_auto_bid", False),
        })

    return seeded


# ── Region Placement ─────────────────────────────────────────────────────────

def place_into_regions(
    seeded: list[dict],
    rng: random.Random | None = None,
) -> dict[str, list[dict]]:
    """
    Place seeded teams into 4 regions following committee rules:

    1. S-curve placement (snake draft across regions)
    2. Conference separation: same-conference teams can't meet before Sweet 16
    3. Conference balance: no region overloaded with one conference
    4. Same-conference teams shouldn't be 1v2 or 3v4 seeds in a region

    Uses optimal assignment: for each seed line, evaluates all 24 permutations
    of 4 teams → 4 regions and picks the lowest total conflict.
    """
    from itertools import permutations

    regions = {r: [] for r in REGIONS}
    region_confs = {r: defaultdict(int) for r in REGIONS}

    conf_totals = defaultdict(int)
    for team in seeded:
        conf_totals[team["conference"]] += 1

    conf_caps = {
        conf: max(2, (total + 3) // 4 + 1)
        for conf, total in conf_totals.items()
    }

    TOP_HALF = {1, 16, 8, 9, 4, 13, 5, 12}
    BOT_HALF = {2, 15, 7, 10, 3, 14, 6, 11}

    def _conflict_score(team: dict, region_name: str) -> int:
        conf = team["conference"]
        seed = team["seed"]
        penalty = 0

        if region_confs[region_name][conf] >= conf_caps.get(conf, 4):
            penalty += 200

        for existing in regions[region_name]:
            if existing["conference"] != conf:
                continue
            es = existing["seed"]

            # Same bracket half = meet before Sweet 16 (HARD)
            if (seed in TOP_HALF and es in TOP_HALF) or (seed in BOT_HALF and es in BOT_HALF):
                penalty += 100

            # 1v2 or 3v4 same conference (Elite Eight) (HARD)
            pair = frozenset({seed, es})
            if pair in (frozenset({1, 2}), frozenset({3, 4})):
                penalty += 80

            # General same-conference in region (SOFT)
            penalty += 8

        return penalty

    seed_lines = defaultdict(list)
    for team in seeded:
        seed_lines[team["seed"]].append(team)

    for seed_num in range(1, 17):
        teams_at_seed = seed_lines.get(seed_num, [])

        if len(teams_at_seed) == 0:
            continue

        # Process in chunks of 4 (handles seed 16 having 8 teams for First Four)
        region_list = list(REGIONS)
        for chunk_start in range(0, len(teams_at_seed), 4):
            chunk = teams_at_seed[chunk_start:chunk_start + 4]
            n_chunk = len(chunk)

            if n_chunk == 0:
                continue

            if n_chunk < 4:
                # Greedy for partial chunks
                used_regions = set()
                for team in chunk:
                    best_region = None
                    best_score = float("inf")
                    for r in region_list:
                        if r in used_regions:
                            continue
                        sc = _conflict_score(team, r)
                        if sc < best_score:
                            best_score = sc
                            best_region = r
                    if best_region:
                        used_regions.add(best_region)
                        regions[best_region].append(team)
                        region_confs[best_region][team["conference"]] += 1
                continue

            # 4 teams → try all 24 permutations for optimal placement
            best_perm = None
            best_total = float("inf")

            for perm in permutations(range(4)):
                total = sum(
                    _conflict_score(chunk[ti], region_list[ri])
                    for ri, ti in enumerate(perm)
                )
                if total < best_total:
                    best_total = total
                    best_perm = perm

            if best_perm:
                for region_idx, team_idx in enumerate(best_perm):
                    team = chunk[team_idx]
                    rname = region_list[region_idx]
                    regions[rname].append(team)
                    region_confs[rname][team["conference"]] += 1

    for region_name in REGIONS:
        regions[region_name].sort(key=lambda t: t["seed"])

    return regions


# ── Generate Matchups ────────────────────────────────────────────────────────

SEED_MATCHUPS = [
    (1, 16), (8, 9), (5, 12), (4, 13),
    (2, 15), (7, 10), (6, 11), (3, 14),
]


def generate_matchups(regions: dict[str, list[dict]], teams_df: pd.DataFrame) -> list[dict]:
    """Generate Round of 64 matchups from region placements."""
    games = []
    game_counter = 0

    for region_name in REGIONS:
        region_teams = {t["seed"]: t for t in regions[region_name]}

        for seed_a, seed_b in SEED_MATCHUPS:
            team_a = region_teams.get(seed_a)
            team_b = region_teams.get(seed_b)

            if team_a is None or team_b is None:
                continue

            game_counter += 1
            games.append({
                "id": f"{region_name.lower()}-r1-{game_counter}",
                "round": 1,
                "region": region_name,
                "team1Seed": seed_a,
                "team2Seed": seed_b,
                "team1": team_a["team_name"],
                "team1Slug": team_a["team_slug"],
                "team1NetRank": team_a["net_rank"],
                "team1Score": team_a["committee_score"],
                "team1Record": team_a["record"],
                "team1Conference": team_a["conference"],
                "team1AutoBid": team_a.get("is_auto_bid", False),
                "team2": team_b["team_name"],
                "team2Slug": team_b["team_slug"],
                "team2NetRank": team_b["net_rank"],
                "team2Score": team_b["committee_score"],
                "team2Record": team_b["record"],
                "team2Conference": team_b["conference"],
                "team2AutoBid": team_b.get("is_auto_bid", False),
            })

    return games


# ── Main Pipeline ────────────────────────────────────────────────────────────

def run_bracketology(
    shuffle: bool = False,
    variance: float = 0.3,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    Run the full bracketology pipeline.

    Args:
        shuffle: Enable randomized bracket generation
        variance: 0.0 (deterministic) to 1.0 (maximum chaos)
        seed: Random seed for reproducibility (None = random)

    Returns:
        Full bracket data structure for the frontend
    """
    rng = None
    if shuffle:
        rng = random.Random(seed)
        if variance == 0:
            variance = 0.3

    logger.info("=" * 60)
    logger.info("BracketBuilder Bracketology Engine")
    logger.info("Mode: %s | Variance: %.1f", "Shuffle" if shuffle else "Deterministic", variance)
    logger.info("=" * 60)

    # Load data
    teams = pd.read_csv(os.path.join(DATA_DIR, "teams_stats.csv"))
    standings = pd.read_csv(os.path.join(DATA_DIR, "standings.csv"))

    # Ensure numeric types
    for col in ["net_rank", "sos_rank", "win_pct", "power_score"]:
        if col in teams.columns:
            teams[col] = pd.to_numeric(teams[col], errors="coerce")

    # Compute committee scores
    logger.info("\n🏛️  Computing Committee Scores...")
    teams["committee_score"] = teams.apply(compute_committee_score, axis=1)
    teams = teams.sort_values("committee_score", ascending=False).reset_index(drop=True)

    top_10 = teams.head(10)
    logger.info("  Top 10 by Committee Score:")
    for _, r in top_10.iterrows():
        q1 = str(r.get("q1_record", ""))
        logger.info("    Score: %.1f  NET #%d  %s (%s)  Q1: %s  Record: %s",
                     r["committee_score"], int(r.get("net_rank", 999)),
                     r["team_name"], r.get("conference", ""), q1, r.get("record", ""))

    # Project conference champions
    logger.info("\n🏆 Projecting Conference Champions...")
    champions = project_conference_champions(standings, teams, rng, variance)
    auto_bid_teams = set(champions.values())
    logger.info("  Auto-bids: %d conferences", len(auto_bid_teams))

    # Mark auto-bid status
    teams["is_auto_bid"] = teams["team_name_normalized"].isin(auto_bid_teams)

    # Select at-large teams
    n_at_large = 68 - len(auto_bid_teams)
    logger.info("\n📋 Selecting %d At-Large Teams...", n_at_large)
    at_large_teams = select_at_large(teams, auto_bid_teams, n_at_large, rng, variance)

    field_teams = list(auto_bid_teams) + at_large_teams
    logger.info("  Total field: %d teams (%d auto + %d at-large)",
                len(field_teams), len(auto_bid_teams), len(at_large_teams))

    # Conference representation
    field_df = teams[teams["team_name_normalized"].isin(field_teams)]
    conf_counts = field_df["conference"].value_counts()
    multi_bid = conf_counts[conf_counts > 1]
    logger.info("  Multi-bid conferences:")
    for conf, count in multi_bid.head(10).items():
        logger.info("    %s: %d teams", conf, count)

    # Seed the field
    logger.info("\n🎯 Seeding the Field (S-Curve)...")
    seeded = assign_seeds(teams, field_teams, rng, variance)

    for s in seeded[:16]:
        tag = "(A)" if s.get("is_auto_bid") else "   "
        logger.info("    #%d seed: %s  (NET #%d, %s) %s",
                     s["seed"], s["team_name"], s["net_rank"], s["conference"], tag)

    # Place into regions
    logger.info("\n🗺️  Placing into Regions...")
    regions = place_into_regions(seeded, rng)

    for region_name in REGIONS:
        seeds_in_region = regions[region_name]
        confs = [t["conference"] for t in seeds_in_region]
        logger.info("  %s: %s", region_name,
                     ", ".join(f"({t['seed']}) {t['team_name']}" for t in seeds_in_region[:4]))
        # Check for conference conflicts
        from collections import Counter
        conf_counts_r = Counter(confs)
        dupes = {c: n for c, n in conf_counts_r.items() if n > 3}
        if dupes:
            logger.warning("    ⚠️ Conference concentration: %s", dupes)

    # Generate matchups
    logger.info("\n🏀 Generating Round of 64 Matchups...")
    matchups = generate_matchups(regions, teams)

    # Build output
    bracket = {
        "mode": "shuffle" if shuffle else "deterministic",
        "variance": variance,
        "seed": seed,
        "field": {
            "total": len(field_teams),
            "autoBids": len(auto_bid_teams),
            "atLarge": len(at_large_teams),
        },
        "regions": {},
        "matchups": matchups,
        "seedList": seeded,
        "conferenceBids": dict(
            field_df["conference"].value_counts().head(15).items()
        ),
    }

    for region_name in REGIONS:
        bracket["regions"][region_name] = {
            "teams": regions[region_name],
            "topSeed": regions[region_name][0] if regions[region_name] else None,
        }

    # Save
    os.makedirs(EXPORT_DIR, exist_ok=True)
    suffix = f"_shuffle_{seed}" if shuffle else ""
    bracket_path = os.path.join(EXPORT_DIR, f"bracket{suffix}.json")
    with open(bracket_path, "w") as f:
        json.dump(bracket, f, indent=2, default=str)
    logger.info("\n💾 Saved bracket → %s", bracket_path)

    logger.info("\n✅ Bracketology complete!")
    return bracket


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BracketBuilder Bracketology")
    parser.add_argument("--shuffle", action="store_true", help="Generate a shuffled bracket")
    parser.add_argument("--variance", type=float, default=0.3,
                        help="Shuffle variance (0.0-1.0, default 0.3)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    run_bracketology(
        shuffle=args.shuffle,
        variance=args.variance if args.shuffle else 0.0,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
