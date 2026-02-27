"""Bracketology engine backed by Postgres tables."""

from __future__ import annotations

import logging
import os
import random
from collections import Counter, defaultdict
from itertools import permutations
from typing import Any

import numpy as np
import pandas as pd

from server.db import fetch_all

logger = logging.getLogger(__name__)

REGIONS = ["East", "West", "South", "Midwest"]
SEED_MATCHUPS = [
    (1, 16), (8, 9), (5, 12), (4, 13),
    (2, 15), (7, 10), (6, 11), (3, 14),
]
POWER_CONFERENCES = {"SEC", "Big Ten", "Big 12", "ACC", "Big East"}
UPPER_MID = {"WCC", "Mountain West", "American", "Atlantic 10", "MVC"}


def _slugify(value: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "-" for ch in (value or "").strip())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def _team_key(row: dict[str, Any]) -> str:
    for key in ("team_slug", "slug", "team_id", "id", "team_name_normalized", "team_name", "name"):
        val = row.get(key)
        if val is None:
            continue
        s = str(val).strip()
        if not s:
            continue
        return _slugify(s) if (" " in s or any(ch.isupper() for ch in s)) else s.lower()
    return ""


def _team_id_key(row: dict[str, Any]) -> str:
    val = row.get("team_id")
    if val is None:
        return ""
    return str(val).strip()


def _to_num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _parse_quad(quad_str: Any) -> tuple[int, int]:
    if not isinstance(quad_str, str) or "-" not in quad_str:
        return 0, 0
    parts = quad_str.strip().split("-")
    try:
        return int(parts[0]), int(parts[1])
    except Exception:
        return 0, 0


def compute_committee_score(row: pd.Series) -> float:
    net_rank = float(row.get("net_rank", 365) or 365)
    sos_rank = float(row.get("sos_rank", 365) or 365)
    win_pct = float(row.get("win_pct", 50) or 50)
    power_score = float(row.get("power_score", 50) or 50)

    net_pctl = max(0, (365 - net_rank) / 365) * 100
    if net_rank <= 10:
        net_pctl += 8
    elif net_rank <= 20:
        net_pctl += 4
    elif net_rank <= 30:
        net_pctl += 2
    net_component = min(100, net_pctl)

    q1w, q1l = _parse_quad(row.get("q1_record", "0-0"))
    q2w, q2l = _parse_quad(row.get("q2_record", "0-0"))
    q3w, q3l = _parse_quad(row.get("q3_record", "0-0"))
    q4w, q4l = _parse_quad(row.get("q4_record", "0-0"))

    quad_raw = (
        q1w * 5.0 +
        q2w * 2.5 +
        q3w * 0.5 +
        q4w * 0.2 -
        q3l * 8.0 -
        q4l * 15.0
    )
    if q1w == 0:
        quad_raw -= 10.0
    if q1w >= 8:
        quad_raw += 6.0
    elif q1w >= 6:
        quad_raw += 3.0
    quad_component = np.clip((quad_raw + 20) / 60 * 100, 0, 100)

    sos_pctl = max(0, (365 - sos_rank) / 365) * 100
    win_component = np.clip(win_pct, 0, 100)
    ps_component = np.clip(power_score, 0, 100)

    conf = str(row.get("conference", ""))
    if conf in POWER_CONFERENCES:
        conf_bonus = 70
    elif conf in UPPER_MID:
        conf_bonus = 55
    else:
        conf_bonus = 35

    total_games = q1w + q1l + q2w + q2l + q3w + q3l + q4w + q4l
    pct_tough = (q1w + q1l + q2w + q2l) / max(total_games, 1)
    if pct_tough > 0.5:
        conf_bonus += 10
    conf_component = np.clip(conf_bonus, 0, 100)

    record_penalty = 0.0
    record_str = str(row.get("record", "0-0"))
    try:
        parts = record_str.split("-")
        wins = int(parts[0])
        losses = int(parts[1]) if len(parts) > 1 else 0
        total = wins + losses
        if total > 0 and wins / total < 0.500:
            record_penalty = -25.0
        elif wins < 15:
            record_penalty = -15.0
        elif total > 0 and wins / total < 0.550:
            record_penalty = -8.0
    except Exception:
        pass

    score = (
        0.35 * net_component +
        0.30 * quad_component +
        0.10 * sos_pctl +
        0.10 * win_component +
        0.10 * ps_component +
        0.05 * conf_component
    ) + record_penalty
    return round(max(0, score), 2)


def _latest_by_team(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for row in rows:
        slug = _team_key(row)
        if not slug:
            continue
        cur = idx.get(slug)
        if cur is None:
            idx[slug] = row
            continue
        lhs = str(row.get("updated_at") or row.get("as_of") or row.get("created_at") or "")
        rhs = str(cur.get("updated_at") or cur.get("as_of") or cur.get("created_at") or "")
        if lhs >= rhs:
            idx[slug] = row
    return idx


def _latest_by_team_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _team_id_key(row)
        if not key:
            continue
        cur = idx.get(key)
        if cur is None:
            idx[key] = row
            continue
        lhs = str(row.get("updated_at") or row.get("as_of") or row.get("created_at") or "")
        rhs = str(cur.get("updated_at") or cur.get("as_of") or cur.get("created_at") or "")
        if lhs >= rhs:
            idx[key] = row
    return idx


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    teams_rows = fetch_all("SELECT * FROM ncaab_teams")
    stats_rows = _latest_by_team_id(fetch_all("SELECT * FROM ncaab_team_stats"))
    power_rows = _latest_by_team_id(fetch_all("SELECT * FROM ncaab_team_power_scores"))
    standings_rows = _latest_by_team_id(fetch_all("SELECT * FROM ncaab_standings"))
    rankings_rows_all = fetch_all("SELECT * FROM ncaab_rankings")

    net_rank_map: dict[str, int] = {}
    for row in rankings_rows_all:
        team_id = _team_id_key(row)
        if not team_id:
            continue
        rank = row.get("net_rank")
        if rank is None:
            typ = str(row.get("ranking_type") or row.get("ranking_name") or row.get("poll") or "").lower()
            if "net" in typ:
                rank = row.get("rank") or row.get("ranking") or row.get("value")
        if rank is not None:
            net_rank_map[team_id] = _to_int(rank, 999)

    team_records: list[dict[str, Any]] = []
    standings_records: list[dict[str, Any]] = []
    for row in teams_rows:
        slug = _team_key(row)
        if not slug:
            continue
        team_id = _team_id_key(row)
        stats = stats_rows.get(team_id, {})
        power = power_rows.get(team_id, {})
        standing = standings_rows.get(team_id, {})

        wins = _to_int(standing.get("overall_wins") or standing.get("wins"), 0)
        losses = _to_int(standing.get("overall_losses") or standing.get("losses"), 0)
        record = str(standing.get("record") or standing.get("overall_record") or f"{wins}-{losses}")

        team_records.append(
            {
                "team_name_normalized": slug,
                "team_name": str(row.get("team_name") or row.get("name") or slug.replace("-", " ").title()),
                "team_slug": slug,
                "conference": str(row.get("conference") or row.get("conference_name") or ""),
                "record": record,
                "net_rank": _to_int(net_rank_map.get(team_id, row.get("net_rank")), 999),
                "sos_rank": _to_int(stats.get("sos_rank") or stats.get("strength_of_schedule_rank"), 999),
                "win_pct": _to_num(stats.get("win_pct"), 50.0),
                "power_score": _to_num(power.get("power_score") or power.get("score"), 50.0),
                "q1_record": str(standing.get("quad1_record") or standing.get("q1_record") or "0-0"),
                "q2_record": str(standing.get("quad2_record") or standing.get("q2_record") or "0-0"),
                "q3_record": str(standing.get("quad3_record") or standing.get("q3_record") or "0-0"),
                "q4_record": str(standing.get("quad4_record") or standing.get("q4_record") or "0-0"),
            }
        )

        conf_w = _to_int(standing.get("conference_wins") or standing.get("conf_wins"), 0)
        conf_l = _to_int(standing.get("conference_losses") or standing.get("conf_losses"), 0)
        conf_pct = _to_num(standing.get("conf_pct"), conf_w / max(conf_w + conf_l, 1))
        standings_records.append(
            {
                "team_name_normalized": slug,
                "conference": str(row.get("conference") or row.get("conference_name") or ""),
                "conf_pct": conf_pct,
                "record": record,
            }
        )

    return pd.DataFrame(team_records), pd.DataFrame(standings_records)


def project_conference_champions(
    standings: pd.DataFrame,
    teams: pd.DataFrame,
    rng: random.Random | None = None,
    variance: float = 0.0,
) -> dict[str, str]:
    standings_with_net = standings.merge(
        teams[["team_name_normalized", "net_rank", "committee_score"]],
        on="team_name_normalized",
        how="left",
    )
    standings_with_net["net_rank"] = pd.to_numeric(standings_with_net["net_rank"], errors="coerce").fillna(999)
    standings_with_net["conf_pct"] = pd.to_numeric(standings_with_net["conf_pct"], errors="coerce").fillna(0)
    standings_with_net["committee_score"] = pd.to_numeric(standings_with_net["committee_score"], errors="coerce").fillna(0)

    champions: dict[str, str] = {}
    for conf in standings_with_net["conference"].dropna().unique():
        conf_teams = standings_with_net[standings_with_net["conference"] == conf].copy()
        conf_teams = conf_teams.sort_values(["conf_pct", "net_rank"], ascending=[False, True]).reset_index(drop=True)
        if conf_teams.empty:
            continue
        if variance == 0 or rng is None:
            champions[conf] = conf_teams.iloc[0]["team_name_normalized"]
            continue

        n = min(len(conf_teams), 6)
        candidates = conf_teams.head(n)
        base_weights = np.array([0.50, 0.25, 0.12, 0.07, 0.04, 0.02][:n])
        if conf in POWER_CONFERENCES:
            upset_factor = 1.0 + variance * 0.8
        elif conf in UPPER_MID:
            upset_factor = 1.0 + variance * 0.5
        else:
            upset_factor = 1.0 + variance * 0.3
        weights = (base_weights ** (1.0 / upset_factor))
        weights = weights / weights.sum()
        idx = rng.choices(range(n), weights=weights.tolist(), k=1)[0]
        champions[conf] = candidates.iloc[idx]["team_name_normalized"]
    return champions


def select_at_large(
    teams: pd.DataFrame,
    auto_bid_teams: set[str],
    n_spots: int = 36,
    rng: random.Random | None = None,
    variance: float = 0.0,
) -> list[str]:
    candidates = teams[~teams["team_name_normalized"].isin(auto_bid_teams)].copy()
    candidates = candidates.sort_values("committee_score", ascending=False).reset_index(drop=True)
    if variance == 0 or rng is None:
        return candidates.head(n_spots)["team_name_normalized"].tolist()

    lock_in_count = max(0, n_spots - 6)
    bubble_pool_size = 12
    locks = candidates.head(lock_in_count)["team_name_normalized"].tolist()
    bubble_candidates = candidates.iloc[lock_in_count:lock_in_count + bubble_pool_size]
    scores = bubble_candidates["committee_score"].values
    if len(scores) == 0:
        return locks
    weights = np.exp((scores - scores.min()) * variance * 0.1)
    weights = weights / weights.sum()
    remaining_spots = n_spots - lock_in_count
    bubble_indices = rng.choices(range(len(bubble_candidates)), weights=weights.tolist(), k=min(remaining_spots, len(bubble_candidates)))
    seen: set[int] = set()
    unique_indices: list[int] = []
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
    return locks + bubble_selected[:remaining_spots]


def assign_seeds(
    teams: pd.DataFrame,
    field_teams: list[str],
    rng: random.Random | None = None,
    variance: float = 0.0,
) -> list[dict[str, Any]]:
    field = teams[teams["team_name_normalized"].isin(field_teams)].copy()
    field = field.sort_values("committee_score", ascending=False).reset_index(drop=True)
    if variance > 0 and rng is not None:
        noise = np.array([rng.gauss(0, variance * 1.5) for _ in range(len(field))])
        for i in range(len(noise)):
            if i >= 16:
                noise[i] *= 1.5
            elif i >= 8:
                noise[i] *= 1.2
        field["seed_score"] = field["committee_score"] + noise
        field = field.sort_values("seed_score", ascending=False).reset_index(drop=True)

    seeded: list[dict[str, Any]] = []
    for i, (_, row) in enumerate(field.iterrows()):
        seed_line = min(16, (i // 4) + 1)
        seeded.append(
            {
                "team_name_normalized": row["team_name_normalized"],
                "team_name": row.get("team_name", ""),
                "team_slug": str(row.get("team_slug", "")),
                "overall_rank": i + 1,
                "seed": seed_line,
                "committee_score": row["committee_score"],
                "net_rank": int(row.get("net_rank", 999) or 999),
                "conference": str(row.get("conference", "")),
                "record": str(row.get("record", "")),
                "is_auto_bid": bool(row.get("is_auto_bid", False)),
            }
        )
    return seeded


def place_into_regions(seeded: list[dict[str, Any]], rng: random.Random | None = None) -> dict[str, list[dict[str, Any]]]:
    regions: dict[str, list[dict[str, Any]]] = {r: [] for r in REGIONS}
    region_confs = {r: defaultdict(int) for r in REGIONS}
    conf_totals = defaultdict(int)
    for team in seeded:
        conf_totals[team["conference"]] += 1
    conf_caps = {conf: max(2, (total + 3) // 4 + 1) for conf, total in conf_totals.items()}
    top_half = {1, 16, 8, 9, 4, 13, 5, 12}
    bot_half = {2, 15, 7, 10, 3, 14, 6, 11}

    def _conflict_score(team: dict[str, Any], region_name: str) -> int:
        conf = team["conference"]
        seed = team["seed"]
        penalty = 0
        if region_confs[region_name][conf] >= conf_caps.get(conf, 4):
            penalty += 200
        for existing in regions[region_name]:
            if existing["conference"] != conf:
                continue
            es = existing["seed"]
            if (seed in top_half and es in top_half) or (seed in bot_half and es in bot_half):
                penalty += 100
            if frozenset({seed, es}) in (frozenset({1, 2}), frozenset({3, 4})):
                penalty += 80
            penalty += 8
        return penalty

    seed_lines = defaultdict(list)
    for team in seeded:
        seed_lines[team["seed"]].append(team)

    for seed_num in range(1, 17):
        teams_at_seed = seed_lines.get(seed_num, [])
        if not teams_at_seed:
            continue
        region_list = list(REGIONS)
        for chunk_start in range(0, len(teams_at_seed), 4):
            chunk = teams_at_seed[chunk_start:chunk_start + 4]
            n_chunk = len(chunk)
            if n_chunk < 4:
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

            best_perm = None
            best_total = float("inf")
            for perm in permutations(range(4)):
                total = sum(_conflict_score(chunk[ti], region_list[ri]) for ri, ti in enumerate(perm))
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


def generate_matchups(regions: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    game_counter = 0
    for region_name in REGIONS:
        region_teams = {t["seed"]: t for t in regions[region_name]}
        for seed_a, seed_b in SEED_MATCHUPS:
            team_a = region_teams.get(seed_a)
            team_b = region_teams.get(seed_b)
            if team_a is None or team_b is None:
                continue
            game_counter += 1
            games.append(
                {
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
                    "analysis": "",
                    "proTeam1": [],
                    "proTeam2": [],
                    "rotobotPick": "",
                    "rotobotConfidence": 55,
                    "pickReasoning": "",
                }
            )
    return games


def run_bracketology(shuffle: bool = False, variance: float = 0.3, seed: int | None = None) -> dict[str, Any]:
    rng = random.Random(seed) if shuffle else None
    teams, standings = _load_inputs()
    if teams.empty:
        return {
            "mode": "deterministic",
            "variance": 0.0,
            "seed": seed,
            "field": {"total": 0, "autoBids": 0, "atLarge": 0},
            "regions": {r: {"teams": []} for r in REGIONS},
            "matchups": [],
            "seedList": [],
            "conferenceBids": {},
        }

    for col in ["net_rank", "sos_rank", "win_pct", "power_score"]:
        if col in teams.columns:
            teams[col] = pd.to_numeric(teams[col], errors="coerce")
    teams["committee_score"] = teams.apply(compute_committee_score, axis=1)
    teams = teams.sort_values("committee_score", ascending=False).reset_index(drop=True)

    champions = project_conference_champions(standings, teams, rng, variance if shuffle else 0.0)
    auto_bid_teams = set(champions.values())
    teams["is_auto_bid"] = teams["team_name_normalized"].isin(auto_bid_teams)

    n_at_large = max(0, 68 - len(auto_bid_teams))
    at_large_teams = select_at_large(teams, auto_bid_teams, n_at_large, rng, variance if shuffle else 0.0)
    field_teams = list(auto_bid_teams) + at_large_teams

    seeded = assign_seeds(teams, field_teams, rng, variance if shuffle else 0.0)
    regions = place_into_regions(seeded, rng)
    matchups = generate_matchups(regions)

    teams_by_slug = {str(r["team_slug"]): r for r in seeded}
    for g in matchups:
        g["team1Full"] = teams_by_slug.get(g["team1Slug"], {})
        g["team2Full"] = teams_by_slug.get(g["team2Slug"], {})

    field_df = teams[teams["team_name_normalized"].isin(field_teams)]
    return {
        "mode": "shuffle" if shuffle else "deterministic",
        "variance": variance if shuffle else 0.0,
        "seed": seed,
        "field": {
            "total": len(field_teams),
            "autoBids": len(auto_bid_teams),
            "atLarge": len(at_large_teams),
        },
        "regions": {r: {"teams": regions[r], "topSeed": regions[r][0] if regions[r] else None} for r in REGIONS},
        "matchups": matchups,
        "seedList": seeded,
        "conferenceBids": dict(Counter(field_df["conference"]).most_common(15)),
    }
