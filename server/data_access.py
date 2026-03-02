"""Read models for BracketBuilder backed by Postgres ncaab_* tables."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from server.bracketology import run_bracketology
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


def _first_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, list):
        for v in value:
            s = str(v).strip()
            if s:
                return s
        return default
    if isinstance(value, str):
        s = value.strip()
        return s if s else default
    return str(value)


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


def _team_id_key(row: dict[str, Any]) -> str:
    val = row.get("team_id")
    if val is None:
        return ""
    s = str(val).strip()
    return s


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


def _latest_by_team_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _team_id_key(row)
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
        key = _team_id_key(row)
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
    stats_idx = _latest_by_team_id(_safe_table("ncaab_team_stats"))
    power_idx = _latest_by_team_id(_safe_table("ncaab_team_power_scores"))
    standings_idx = _latest_by_team_id(_safe_table("ncaab_standings"))
    rankings_idx = _parse_rankings(_safe_table("ncaab_rankings"))

    teams: dict[str, dict[str, Any]] = {}
    for row in teams_rows:
        slug = _team_key(row)
        if not slug:
            continue
        team_id = _team_id_key(row)
        stats = stats_idx.get(team_id, {})
        power = power_idx.get(team_id, {})
        standing = standings_idx.get(team_id, {})
        ranks = rankings_idx.get(team_id, {})

        seed = _to_int(_pick(standing, "seed", "tournament_seed", "projected_seed"), 0)
        rec = _record_from_wl(standing) or _record_from_wl(row)

        style_tags = _to_list(_pick(power, "style_tags", "tags"))
        style_identity = str(_pick(power, "style_identity", "identity", default=""))

        teams[slug] = {
            "id": slug,
            "name": str(_pick(row, "team_name", "name", default=slug.replace("-", " ").title())),
            "shortName": str(_pick(row, "team_abbreviation", "short_name", "abbreviation", "display_name", default=slug.replace("-", " ").title())),
            "seed": seed,
            "record": rec,
            "conference": str(_pick(row, "conference", "conference_name", default="")),
            "ppg": _to_float(_pick(stats, "ppg", "points_per_game"), 0.0),
            "oppg": _to_float(_pick(stats, "opp_ppg", "oppg", "opp_points_per_game"), 0.0),
            "pace": _to_float(_pick(stats, "pace", "tempo"), 0.0),
            "eFGPct": _to_float(_pick(stats, "efg_pct", "efg", "effective_fg_pct"), 0.0),
            "tovPct": _to_float(_pick(stats, "tov_pct", "turnover_pct"), 0.0),
            "orebPct": _to_float(_pick(stats, "oreb_pct", "off_reb_pct"), 0.0),
            "sosRank": _to_int(_pick(stats, "sos_rank", "strength_of_schedule_rank"), 999),
            "netRank": _to_int(_pick(ranks, "netRank", "net_rank"), 999),
            "recentForm": _to_list(_pick(standing, "recent_form", "last_10"))[:10],
            "color": str(_pick(row, "color_hex", "primary_color", "color", default="#1f2937")),
            "rotobotScore": _to_float(_pick(power, "power_score", "score"), 50.0),
            "rotobotBlurb": str(_pick(power, "rotobot_blurb", "team_blurb", default="")),
            "keyPlayer": str(_pick(power, "key_player", default="")),
            "keyPlayerStat": str(_pick(power, "key_player_stat", default="")),
            "styleTags": style_tags,
            "styleSummary": str(_pick(power, "style_summary", default="")),
            "styleIdentity": style_identity,
            "styleBullets": str(_pick(power, "style_bullets", default="")),
            "styleWeakness": _first_text(_pick(power, "style_weakness", "weaknesses", default=""), ""),
            "stats": {
                "scoring": {
                    "ppg": _to_float(_pick(stats, "ppg", "points_per_game"), 0.0),
                    "oppg": _to_float(_pick(stats, "opp_ppg", "oppg", "opp_points_per_game"), 0.0),
                    "scoringMargin": _to_float(_pick(stats, "scoring_margin"), 0.0),
                    "benchPPG": _to_float(_pick(stats, "bench_ppg"), 0.0),
                    "fastbreakPPG": _to_float(_pick(stats, "fastbreak_ppg"), 0.0),
                },
                "shooting": {
                    "fgPct": _to_float(_pick(stats, "fg_pct"), 0.0),
                    "fgPctDefense": _to_float(_pick(stats, "opp_fg_pct"), 0.0),
                    "threePtPct": _to_float(_pick(stats, "three_pt_pct", "3p_pct"), 0.0),
                    "threePtPctDefense": _to_float(_pick(stats, "opp_three_pt_pct", "opp_3p_pct"), 0.0),
                    "threePG": _to_float(_pick(stats, "three_pt_made_pg", "three_made_pg", "three_pg"), 0.0),
                    "threePtAttemptsPG": _to_float(_pick(stats, "three_pt_attempts_pg", "three_att_pg"), 0.0),
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
                    "topg": _to_float(_pick(stats, "tpg", "topg", "turnovers_per_game"), 0.0),
                    "astToRatio": _to_float(_pick(stats, "ast_to_ratio"), 0.0),
                    "tovPct": _to_float(_pick(stats, "tov_pct", "turnover_pct"), 0.0),
                    "turnoverMargin": _to_float(_pick(stats, "turnover_margin"), 0.0),
                    "turnoversForcedPG": _to_float(_pick(stats, "opp_tpg", "turnovers_forced_pg"), 0.0),
                },
                "defense": {
                    "spg": _to_float(_pick(stats, "spg", "steals_per_game"), 0.0),
                    "bpg": _to_float(_pick(stats, "bpg", "blocks_per_game"), 0.0),
                    "fpg": _to_float(_pick(stats, "fouls_pg"), 0.0),
                    "oppg": _to_float(_pick(stats, "opp_ppg", "oppg", "opp_points_per_game"), 0.0),
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
                    "q1Record": str(_pick(standing, "quad1_record", "q1_record", default="")),
                    "q2Record": str(_pick(standing, "quad2_record", "q2_record", default="")),
                    "q3Record": str(_pick(standing, "quad3_record", "q3_record", default="")),
                    "q4Record": str(_pick(standing, "quad4_record", "q4_record", default="")),
                },
                "percentiles": _pick(power, "percentiles", default={}) or {},
            },
        }
    return teams


def get_all_players() -> dict[str, list[dict[str, Any]]]:
    rows = _safe_table("ncaab_player_season_stats")
    teams_rows = _safe_table("ncaab_teams")
    team_id_to_slug: dict[str, str] = {}
    team_id_to_name: dict[str, str] = {}
    for tr in teams_rows:
        tid = str(tr.get("team_id", "")).strip()
        slug = _team_key(tr)
        if tid and slug:
            team_id_to_slug[tid] = slug
            team_id_to_name[tid] = str(_pick(tr, "team_name", default=slug.replace("-", " ").title()))

    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        team_id = str(row.get("team_id", "")).strip()
        team_slug = team_id_to_slug.get(team_id, "")
        if not team_slug:
            continue
        rec = {
            "name": str(_pick(row, "player_name", "name", "roto_player_id", default="")),
            "team": team_id_to_name.get(team_id, ""),
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
                "topg": _to_float(_pick(row, "tpg", "topg"), 0.0),
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
                "threePM": _to_float(_pick(row, "three_pm", "three_pt_made_pg", "3pm"), 0.0),
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
    # Deterministic bracket generation from Postgres-backed bracketology engine.
    return run_bracketology(shuffle=False, variance=0.0, seed=None)


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
    team1_slug = team1_slug.lower()
    team2_slug = team2_slug.lower()
    teams_rows = _safe_table("ncaab_teams")
    slug_to_team_id: dict[str, int] = {}
    for tr in teams_rows:
        slug = _team_key(tr)
        if slug:
            slug_to_team_id[slug] = _to_int(tr.get("team_id"), 0)
    team1_id = slug_to_team_id.get(team1_slug, 0)
    team2_id = slug_to_team_id.get(team2_slug, 0)
    if not team1_id or not team2_id:
        return None

    games = _safe_table("ncaab_games")
    relevant_game_ids: set[int] = set()
    for g in games:
        h = _to_int(g.get("home_team_id"), 0)
        a = _to_int(g.get("away_team_id"), 0)
        if {h, a} == {team1_id, team2_id}:
            relevant_game_ids.add(_to_int(g.get("game_id"), 0))

    if not relevant_game_ids:
        return None
    rows = _safe_table("ncaab_matchup_analyses")
    candidates = [r for r in rows if _to_int(r.get("game_id"), 0) in relevant_game_ids]
    if not candidates:
        return None
    candidates.sort(key=lambda r: str(_pick(r, "updated_at", "created_at", default="")), reverse=True)
    row = candidates[0]
    rec = str(_pick(row, "recommendation", default="")).strip()
    factors = _pick(row, "factors", default={})
    if isinstance(factors, dict):
        analysis = json.dumps(factors)
    else:
        analysis = str(factors or "")
    if rec and not analysis:
        analysis = rec
    if not rec and not analysis:
        return None
    return {
        "analysis": analysis,
        "proTeam1": [],
        "proTeam2": [],
        "rotobotPick": rec,
        "rotobotConfidence": _to_int(_pick(row, "confidence_score", default=55), 55),
        "pickReasoning": "",
    }


def get_news_context(teams: dict[str, dict[str, Any]]) -> dict[str, str]:
    rows = _safe_table("ncaab_matchup_notes")
    teams_rows = _safe_table("ncaab_teams")
    team_id_to_slug: dict[str, str] = {}
    for tr in teams_rows:
        tid = str(tr.get("team_id", "")).strip()
        slug = _team_key(tr)
        if tid and slug:
            team_id_to_slug[tid] = slug
    out: dict[str, str] = {}
    for row in rows:
        slug = team_id_to_slug.get(str(row.get("team_id", "")).strip(), "")
        text = str(_pick(row, "content", "news_context", "note", "notes", "context", default="")).strip()
        if slug and text:
            existing = out.get(slug, "")
            out[slug] = (existing + "\n\n" + text).strip() if existing else text
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
