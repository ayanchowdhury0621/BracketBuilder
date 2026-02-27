"""Read models for BracketBuilder backed by Postgres ncaab_* tables."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from server.db import fetch_all, fetch_one

logger = logging.getLogger(__name__)


DEFAULT_REGIONS = ("East", "West", "South", "Midwest")


def _slugify(value: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return s or "unknown"


def _pick(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed if str(v).strip()]
            except json.JSONDecodeError:
                pass
        return [p.strip() for p in raw.split(",") if p.strip()]
    return [str(value)]


def _record_from_wl(row: dict[str, Any]) -> str:
    record = _pick(row, "record", "overall_record")
    if record:
        return str(record)
    wins = _to_int(_pick(row, "wins", "overall_wins"), 0)
    losses = _to_int(_pick(row, "losses", "overall_losses"), 0)
    return f"{wins}-{losses}" if wins or losses else ""


def _sort_key(row: dict[str, Any]) -> tuple[int, str]:
    for k in ("updated_at", "as_of", "created_at", "snapshot_at", "date", "game_date"):
        val = row.get(k)
        if isinstance(val, datetime):
            return (1, val.isoformat())
        if isinstance(val, str) and val:
            return (1, val)
    return (0, str(_pick(row, "season", "id", default="0")))


def _team_key(row: dict[str, Any]) -> str:
    raw = _pick(
        row,
        "team_slug",
        "slug",
        "team_id",
        "id",
        "team_name_normalized",
        "team_name",
        "name",
        default="",
    )
    raw_str = str(raw).strip()
    if not raw_str:
        return ""
    if any(ch.isupper() for ch in raw_str) or " " in raw_str:
        return _slugify(raw_str)
    return raw_str.lower()


def _latest_by_team(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _team_key(row)
        if not key:
            continue
        current = out.get(key)
        if current is None or _sort_key(row) >= _sort_key(current):
            out[key] = row
    return out


def _safe_table(table: str) -> list[dict[str, Any]]:
    try:
        return fetch_all(f"SELECT * FROM {table}")
    except Exception as exc:
        logger.warning("Query failed for %s: %s", table, exc)
        return []


def _safe_scalar(query: str, default: Any) -> Any:
    try:
        row = fetch_one(query)
        if not row:
            return default
        return next(iter(row.values()), default)
    except Exception:
        return default


def _parse_rankings(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _team_key(row)
        if not key:
            continue
        ent = out.setdefault(key, {"apRank": None, "netRank": 999})
        if row.get("ap_rank") is not None:
            ent["apRank"] = _to_int(row.get("ap_rank"), 0)
        if row.get("net_rank") is not None:
            ent["netRank"] = _to_int(row.get("net_rank"), 999)

        rank_value = _to_int(_pick(row, "rank", "ranking", "value"), 0)
        rank_kind = str(_pick(row, "ranking_type", "ranking_name", "poll", default="")).lower()
        if rank_value > 0:
            if "ap" in rank_kind:
                ent["apRank"] = rank_value
            if "net" in rank_kind:
                ent["netRank"] = rank_value
    return out


def get_teams() -> dict[str, dict[str, Any]]:
    teams_rows = _safe_table("ncaab_teams")
    stats_idx = _latest_by_team(_safe_table("ncaab_team_stats"))
    power_idx = _latest_by_team(_safe_table("ncaab_team_power_scores"))
    standings_idx = _latest_by_team(_safe_table("ncaab_standings"))
    rankings_idx = _parse_rankings(_safe_table("ncaab_rankings"))

    teams: dict[str, dict[str, Any]] = {}
    for row in teams_rows:
        slug = _team_key(row)
        if not slug:
            continue
        stats = stats_idx.get(slug, {})
        power = power_idx.get(slug, {})
        standing = standings_idx.get(slug, {})
        ranks = rankings_idx.get(slug, {})

        seed = _to_int(_pick(standing, "seed", "tournament_seed", "projected_seed"), 0)
        rec = _record_from_wl(standing) or _record_from_wl(row)

        style_tags = _to_list(_pick(power, "style_tags", "tags"))
        style_identity = str(_pick(power, "style_identity", "identity", default=""))

        teams[slug] = {
            "id": slug,
            "name": str(_pick(row, "team_name", "name", default=slug.replace("-", " ").title())),
            "shortName": str(_pick(row, "short_name", "abbreviation", "display_name", default=slug.replace("-", " ").title())),
            "seed": seed,
            "record": rec,
            "conference": str(_pick(row, "conference", "conference_name", default="")),
            "ppg": _to_float(_pick(stats, "ppg", "points_per_game"), 0.0),
            "oppg": _to_float(_pick(stats, "oppg", "opp_points_per_game"), 0.0),
            "pace": _to_float(_pick(stats, "pace", "tempo"), 0.0),
            "eFGPct": _to_float(_pick(stats, "efg_pct", "efg", "effective_fg_pct"), 0.0),
            "tovPct": _to_float(_pick(stats, "tov_pct", "turnover_pct"), 0.0),
            "orebPct": _to_float(_pick(stats, "oreb_pct", "off_reb_pct"), 0.0),
            "sosRank": _to_int(_pick(stats, "sos_rank", "strength_of_schedule_rank"), 999),
            "netRank": _to_int(_pick(ranks, "netRank", "net_rank"), 999),
            "recentForm": _to_list(_pick(standing, "recent_form", "last_10"))[:10],
            "color": str(_pick(row, "primary_color", "color", default="#1f2937")),
            "rotobotScore": _to_float(_pick(power, "power_score", "score"), 50.0),
            "rotobotBlurb": str(_pick(power, "rotobot_blurb", "team_blurb", default="")),
            "keyPlayer": str(_pick(power, "key_player", default="")),
            "keyPlayerStat": str(_pick(power, "key_player_stat", default="")),
            "styleTags": style_tags,
            "styleSummary": str(_pick(power, "style_summary", default="")),
            "styleIdentity": style_identity,
            "styleBullets": str(_pick(power, "style_bullets", default="")),
            "styleWeakness": str(_pick(power, "style_weakness", default="")),
            "stats": {
                "scoring": {
                    "ppg": _to_float(_pick(stats, "ppg", "points_per_game"), 0.0),
                    "oppg": _to_float(_pick(stats, "oppg", "opp_points_per_game"), 0.0),
                    "scoringMargin": _to_float(_pick(stats, "scoring_margin"), 0.0),
                    "benchPPG": _to_float(_pick(stats, "bench_ppg"), 0.0),
                    "fastbreakPPG": _to_float(_pick(stats, "fastbreak_ppg"), 0.0),
                },
                "shooting": {
                    "fgPct": _to_float(_pick(stats, "fg_pct"), 0.0),
                    "fgPctDefense": _to_float(_pick(stats, "opp_fg_pct"), 0.0),
                    "threePtPct": _to_float(_pick(stats, "three_pt_pct", "3p_pct"), 0.0),
                    "threePtPctDefense": _to_float(_pick(stats, "opp_three_pt_pct", "opp_3p_pct"), 0.0),
                    "threePG": _to_float(_pick(stats, "three_made_pg", "three_pg"), 0.0),
                    "threePtAttemptsPG": _to_float(_pick(stats, "three_att_pg"), 0.0),
                    "ftPct": _to_float(_pick(stats, "ft_pct"), 0.0),
                    "ftMadePG": _to_float(_pick(stats, "ft_made_pg"), 0.0),
                    "eFGPct": _to_float(_pick(stats, "efg_pct", "effective_fg_pct"), 0.0),
                },
                "rebounding": {
                    "rpg": _to_float(_pick(stats, "rpg", "rebounds_per_game"), 0.0),
                    "rebMargin": _to_float(_pick(stats, "reb_margin"), 0.0),
                    "orebPG": _to_float(_pick(stats, "oreb_pg"), 0.0),
                    "drebPG": _to_float(_pick(stats, "dreb_pg"), 0.0),
                    "orebPct": _to_float(_pick(stats, "oreb_pct", "off_reb_pct"), 0.0),
                },
                "ballControl": {
                    "apg": _to_float(_pick(stats, "apg", "assists_per_game"), 0.0),
                    "topg": _to_float(_pick(stats, "topg", "turnovers_per_game"), 0.0),
                    "astToRatio": _to_float(_pick(stats, "ast_to_ratio"), 0.0),
                    "tovPct": _to_float(_pick(stats, "tov_pct", "turnover_pct"), 0.0),
                    "turnoverMargin": _to_float(_pick(stats, "turnover_margin"), 0.0),
                    "turnoversForcedPG": _to_float(_pick(stats, "turnovers_forced_pg"), 0.0),
                },
                "defense": {
                    "spg": _to_float(_pick(stats, "spg", "steals_per_game"), 0.0),
                    "bpg": _to_float(_pick(stats, "bpg", "blocks_per_game"), 0.0),
                    "fpg": _to_float(_pick(stats, "fouls_pg"), 0.0),
                    "oppg": _to_float(_pick(stats, "oppg", "opp_points_per_game"), 0.0),
                    "fgPctDefense": _to_float(_pick(stats, "opp_fg_pct"), 0.0),
                    "threePtPctDefense": _to_float(_pick(stats, "opp_three_pt_pct"), 0.0),
                },
                "tempo": {
                    "pace": _to_float(_pick(stats, "pace", "tempo"), 0.0),
                    "winPct": _to_float(_pick(stats, "win_pct"), 0.0),
                },
                "rankings": {
                    "netRank": _to_int(_pick(ranks, "netRank"), 999),
                    "apRank": _pick(ranks, "apRank", default=None),
                    "sosRank": _to_int(_pick(stats, "sos_rank"), 999),
                    "powerScore": _to_float(_pick(power, "power_score", "score"), 50.0),
                },
                "schedule": {
                    "q1Record": str(_pick(standing, "q1_record", default="")),
                    "q2Record": str(_pick(standing, "q2_record", default="")),
                    "q3Record": str(_pick(standing, "q3_record", default="")),
                    "q4Record": str(_pick(standing, "q4_record", default="")),
                },
                "percentiles": _pick(power, "percentiles", default={}) or {},
            },
        }
    return teams


def get_all_players() -> dict[str, list[dict[str, Any]]]:
    rows = _safe_table("ncaab_player_season_stats")
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        team_slug = _team_key(row)
        if not team_slug:
            continue
        rec = {
            "name": str(_pick(row, "player_name", "name", default="")),
            "team": str(_pick(row, "team_name", default="")),
            "teamSlug": team_slug,
            "position": str(_pick(row, "position", default="")),
            "class": str(_pick(row, "class", "year", default="")),
            "height": str(_pick(row, "height", default="")),
            "gamesPlayed": _to_int(_pick(row, "games_played", "gp"), 0),
            "gamesStarted": _to_int(_pick(row, "games_started", "gs"), 0),
            "stats": {
                "ppg": _to_float(_pick(row, "ppg"), 0.0),
                "rpg": _to_float(_pick(row, "rpg"), 0.0),
                "apg": _to_float(_pick(row, "apg"), 0.0),
                "spg": _to_float(_pick(row, "spg"), 0.0),
                "bpg": _to_float(_pick(row, "bpg"), 0.0),
                "topg": _to_float(_pick(row, "topg"), 0.0),
                "mpg": _to_float(_pick(row, "mpg"), 0.0),
                "fgPct": _pick(row, "fg_pct", default=None),
                "ftPct": _pick(row, "ft_pct", default=None),
                "threePtPct": _pick(row, "three_pt_pct", "3p_pct", default=None),
                "eFGPct": _pick(row, "efg_pct", default=None),
            },
            "perGame": {
                "fgm": _to_float(_pick(row, "fgm"), 0.0),
                "fga": _to_float(_pick(row, "fga"), 0.0),
                "ftm": _to_float(_pick(row, "ftm"), 0.0),
                "fta": _to_float(_pick(row, "fta"), 0.0),
                "threePM": _to_float(_pick(row, "three_pm", "3pm"), 0.0),
                "threePA": _to_float(_pick(row, "three_pa", "3pa"), 0.0),
                "oreb": _to_float(_pick(row, "oreb"), 0.0),
            },
            "totals": {
                "pts": _to_float(_pick(row, "points", "pts"), 0.0),
                "reb": _to_float(_pick(row, "rebounds", "reb"), 0.0),
                "ast": _to_float(_pick(row, "assists", "ast"), 0.0),
                "stl": _to_float(_pick(row, "steals", "stl"), 0.0),
                "blk": _to_float(_pick(row, "blocks", "blk"), 0.0),
                "fgm": _to_float(_pick(row, "fgm"), 0.0),
                "fga": _to_float(_pick(row, "fga"), 0.0),
            },
            "statSummary": str(_pick(row, "stat_summary", default="")),
        }
        out.setdefault(team_slug, []).append(rec)

    for slug, players in out.items():
        out[slug] = sorted(players, key=lambda p: p.get("stats", {}).get("ppg", 0), reverse=True)
    return out


def _team_for_bracket(teams: dict[str, dict[str, Any]], slug: str) -> dict[str, Any]:
    return teams.get(slug, {"id": slug, "name": slug.replace("-", " ").title(), "shortName": slug})


def _round_from_row(row: dict[str, Any]) -> int:
    return _to_int(_pick(row, "round", "round_number", "tournament_round"), 1)


def get_bracket(teams: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = _safe_table("ncaab_matchup_analyses")
    matchups: list[dict[str, Any]] = []

    for row in rows:
        team1_slug = _team_key(
            {
                "team_slug": _pick(
                    row,
                    "team1_slug",
                    "team_1_slug",
                    "home_team_slug",
                    "home_slug",
                    "team1",
                    default="",
                )
            }
        )
        team2_slug = _team_key(
            {
                "team_slug": _pick(
                    row,
                    "team2_slug",
                    "team_2_slug",
                    "away_team_slug",
                    "away_slug",
                    "team2",
                    default="",
                )
            }
        )
        if not team1_slug or not team2_slug:
            continue

        round_no = _round_from_row(row)
        region = str(_pick(row, "region", "bracket_region", default="East")).title()
        game_id = str(
            _pick(
                row,
                "game_id",
                "matchup_id",
                "id",
                default=f"{region.lower()}-r{round_no}-{team1_slug}-vs-{team2_slug}",
            )
        )
        team1 = _team_for_bracket(teams, team1_slug)
        team2 = _team_for_bracket(teams, team2_slug)

        matchups.append(
            {
                "id": game_id,
                "round": round_no,
                "region": region,
                "team1Seed": _to_int(_pick(row, "team1_seed", "seed1", default=team1.get("seed", 0)), 0),
                "team2Seed": _to_int(_pick(row, "team2_seed", "seed2", default=team2.get("seed", 0)), 0),
                "team1": team1.get("name", team1_slug),
                "team1Slug": team1_slug,
                "team1NetRank": _to_int(_pick(row, "team1_net_rank", default=team1.get("netRank", 999)), 999),
                "team1Score": _to_float(_pick(row, "team1_score", default=team1.get("rotobotScore", 50)), 50.0),
                "team1Record": team1.get("record", ""),
                "team1Conference": team1.get("conference", ""),
                "team1AutoBid": bool(_pick(row, "team1_auto_bid", default=False)),
                "team2": team2.get("name", team2_slug),
                "team2Slug": team2_slug,
                "team2NetRank": _to_int(_pick(row, "team2_net_rank", default=team2.get("netRank", 999)), 999),
                "team2Score": _to_float(_pick(row, "team2_score", default=team2.get("rotobotScore", 50)), 50.0),
                "team2Record": team2.get("record", ""),
                "team2Conference": team2.get("conference", ""),
                "team2AutoBid": bool(_pick(row, "team2_auto_bid", default=False)),
                "analysis": str(_pick(row, "analysis", "matchup_preview", default="")),
                "proTeam1": _to_list(_pick(row, "pro_team1", "pros_team1")),
                "proTeam2": _to_list(_pick(row, "pro_team2", "pros_team2")),
                "rotobotPick": str(_pick(row, "rotobot_pick", "pick", "winner_pick", default=team1.get("name", ""))),
                "rotobotConfidence": _to_int(_pick(row, "rotobot_confidence", "confidence", default=55), 55),
                "pickReasoning": str(_pick(row, "pick_reasoning", "reasoning", default="")),
                "team1Full": team1,
                "team2Full": team2,
            }
        )

    matchups.sort(key=lambda m: (m["round"], m["region"], m["team1Seed"], m["team2Seed"], m["id"]))

    regions: dict[str, dict[str, list[dict[str, Any]]]] = {name: {"teams": []} for name in DEFAULT_REGIONS}
    region_seen: dict[str, set[str]] = {name: set() for name in regions}
    for game in matchups:
        if game["round"] != 1:
            continue
        region = game["region"] if game["region"] in regions else "East"
        for slug, seed, score, net, team_name, conference, record, auto_bid in (
            (
                game["team1Slug"],
                game["team1Seed"],
                game["team1Score"],
                game["team1NetRank"],
                game["team1"],
                game["team1Conference"],
                game["team1Record"],
                game["team1AutoBid"],
            ),
            (
                game["team2Slug"],
                game["team2Seed"],
                game["team2Score"],
                game["team2NetRank"],
                game["team2"],
                game["team2Conference"],
                game["team2Record"],
                game["team2AutoBid"],
            ),
        ):
            if slug in region_seen[region]:
                continue
            regions[region]["teams"].append(
                {
                    "team_name_normalized": slug,
                    "team_name": team_name,
                    "team_slug": slug,
                    "overall_rank": 0,
                    "seed": seed,
                    "committee_score": score,
                    "net_rank": net,
                    "conference": conference,
                    "record": record,
                    "is_auto_bid": auto_bid,
                }
            )
            region_seen[region].add(slug)

    for region in regions:
        regions[region]["teams"].sort(key=lambda t: (t.get("seed", 99), t.get("team_name", "")))

    return {
        "mode": "postgres",
        "variance": 0.0,
        "seed": 0,
        "field": [],
        "regions": regions,
        "matchups": matchups,
        "seedList": [],
        "conferenceBids": [],
    }


def get_summary(teams: dict[str, dict[str, Any]], players: dict[str, list[dict[str, Any]]], bracket: dict[str, Any]) -> dict[str, Any]:
    return {
        "totalTeams": len(teams),
        "totalPlayers": sum(len(v) for v in players.values()),
        "totalMatchups": len(bracket.get("matchups", [])),
        "source": "postgres",
        "dataOpsRefresh": "09:00 UTC daily",
        "oddsRefresh": "Every 30 minutes",
    }


def get_conferences(teams: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for slug, team in teams.items():
        conf = (team.get("conference") or "Unknown").strip() or "Unknown"
        out.setdefault(conf, []).append(slug)
    for conf in out:
        out[conf].sort()
    return out


def get_power_rankings(teams: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ranks = [
        {
            "slug": slug,
            "team": team.get("name", slug),
            "conference": team.get("conference", ""),
            "score": _to_float(team.get("rotobotScore"), 0.0),
            "netRank": _to_int(team.get("netRank"), 999),
        }
        for slug, team in teams.items()
    ]
    ranks.sort(key=lambda x: (-x["score"], x["netRank"], x["team"]))
    return ranks


def get_precomputed_matchup(team1_slug: str, team2_slug: str) -> dict[str, Any] | None:
    rows = _safe_table("ncaab_matchup_analyses")
    team1_slug = team1_slug.lower()
    team2_slug = team2_slug.lower()
    for row in rows:
        a = _team_key({"team_slug": _pick(row, "team1_slug", "team_1_slug", "home_team_slug", "home_slug", default="")})
        b = _team_key({"team_slug": _pick(row, "team2_slug", "team_2_slug", "away_team_slug", "away_slug", default="")})
        if {a, b} == {team1_slug, team2_slug}:
            return {
                "analysis": str(_pick(row, "analysis", "matchup_preview", default="")),
                "proTeam1": _to_list(_pick(row, "pro_team1", "pros_team1")),
                "proTeam2": _to_list(_pick(row, "pro_team2", "pros_team2")),
                "rotobotPick": str(_pick(row, "rotobot_pick", "pick", default="")),
                "rotobotConfidence": _to_int(_pick(row, "rotobot_confidence", "confidence", default=55), 55),
                "pickReasoning": str(_pick(row, "pick_reasoning", "reasoning", default="")),
            }
    return None


def get_news_context(teams: dict[str, dict[str, Any]]) -> dict[str, str]:
    rows = _safe_table("ncaab_matchup_notes")
    out: dict[str, str] = {}
    for row in rows:
        slug = _team_key({"team_slug": _pick(row, "team_slug", "slug", default="")})
        text = str(_pick(row, "news_context", "note", "notes", "context", default="")).strip()
        if slug and text:
            out[slug] = text
    for slug, team in teams.items():
        if slug not in out and team.get("rotobotBlurb"):
            out[slug] = str(team.get("rotobotBlurb", ""))
    return out


def get_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "db": {
            "teams": _safe_scalar("SELECT COUNT(*) FROM ncaab_teams", 0),
            "teamStats": _safe_scalar("SELECT COUNT(*) FROM ncaab_team_stats", 0),
            "powerScores": _safe_scalar("SELECT COUNT(*) FROM ncaab_team_power_scores", 0),
            "players": _safe_scalar("SELECT COUNT(*) FROM ncaab_player_season_stats", 0),
            "rankings": _safe_scalar("SELECT COUNT(*) FROM ncaab_rankings", 0),
            "standings": _safe_scalar("SELECT COUNT(*) FROM ncaab_standings", 0),
            "games": _safe_scalar("SELECT COUNT(*) FROM ncaab_games", 0),
            "eventOdds": _safe_scalar("SELECT COUNT(*) FROM ncaab_event_odds", 0),
            "matchupNotes": _safe_scalar("SELECT COUNT(*) FROM ncaab_matchup_notes", 0),
            "matchupAnalyses": _safe_scalar("SELECT COUNT(*) FROM ncaab_matchup_analyses", 0),
        },
    }

