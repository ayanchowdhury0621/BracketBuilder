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


# State abbreviations that should stay uppercase
STATE_ABBREVS = {"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"}


def _format_team_name(name: str) -> str:
    """Format team name preserving acronyms and state abbreviations."""
    if not name:
        return ""
    # If the name is all caps (acronym), keep it that way
    if name.isupper() and len(name) <= 5:
        return name
    # Handle special cases like "Miami (FL)", "Miami (OH)"
    if "(" in name and ")" in name:
        # Keep the state code uppercase inside parentheses
        parts = name.rsplit("(", 1)
        if len(parts) == 2:
            prefix = parts[0].strip()
            state_code = parts[1].replace(")", "").strip().upper()
            return f"{prefix.title()} ({state_code})"
    # Handle "Fla." -> "Fla." (preserve the period)
    if "fla" in name.lower():
        name = name.replace("Fla.", "Fla.").replace("fla.", "Fla.")
        name = name.replace("FLA", "FLA").replace("Fla", "Fla")
    # Otherwise use title case
    return name.title()


def _format_short_name(slug: str, full_name: str = "") -> str:
    """Generate short name from slug, preserving acronyms and state abbreviations."""
    if not slug:
        return ""
    # Check if full name is an acronym (all caps, short)
    if full_name and full_name.isupper() and len(full_name) <= 5:
        return full_name
    # Handle state abbreviation patterns in slugs like "miami-oh", "miami-fl"
    slug_parts = slug.split("-")
    if len(slug_parts) >= 2:
        last_part = slug_parts[-1].upper()
        if last_part in STATE_ABBREVS:
            # State abbreviation at the end - keep it uppercase
            return " ".join(slug_parts[:-1]).title() + " " + last_part
    # Convert slug to name and check if it looks like an acronym
    name = slug.replace("-", " ").upper()
    # If it's 4 chars or less, likely an acronym
    if len(name.replace(" ", "")) <= 4:
        return name
    return name.title()


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


def _last10_to_wl_list(value: Any) -> list[str]:
    """Convert last_10 string like '9-1' to ['W', ..., 'L'] so frontend shows correct W-L and 'last N'."""
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    m = re.match(r"^(\d+)-(\d+)$", s)
    if m:
        w, l = int(m.group(1)), int(m.group(2))
        return ["W"] * w + ["L"] * l
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip() in ("W", "L")]
    if s.startswith("[") and s.endswith("]"):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(v) for v in parsed if str(v).strip() in ("W", "L")]
        except json.JSONDecodeError:
            pass
    return []


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


def _compute_recent_form_all() -> dict[str, list[str]]:
    """
    Build last-10 W/L lists for every team by querying completed games.
    Returns {team_id_str: ["W", "L", ...]}.
    """
    try:
        rows = fetch_all(
            """
            SELECT home_team_id, away_team_id, home_score, away_score, game_date
            FROM ncaab_games
            WHERE home_score IS NOT NULL AND away_score IS NOT NULL
            ORDER BY game_date DESC
            """
        )
    except Exception as exc:
        logger.warning("Could not fetch ncaab_games for form: %s", exc)
        return {}

    # Collect games per team, newest first (already sorted)
    team_games: dict[str, list[str]] = {}
    for row in rows:
        home_id = str(row.get("home_team_id", "")).strip()
        away_id = str(row.get("away_team_id", "")).strip()
        home_score = _to_int(row.get("home_score"), -1)
        away_score = _to_int(row.get("away_score"), -1)
        if not home_id or not away_id or home_score < 0 or away_score < 0:
            continue
        if home_score > away_score:
            home_result, away_result = "W", "L"
        elif away_score > home_score:
            home_result, away_result = "L", "W"
        else:
            home_result, away_result = "W", "W"  # tie — treat as W

        for team_id, result in ((home_id, home_result), (away_id, away_result)):
            lst = team_games.setdefault(team_id, [])
            if len(lst) < 10:
                lst.append(result)

    return team_games


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
    recent_form_by_team_id = _compute_recent_form_all()

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

        team_name = str(_pick(row, "team_name", "name", default=""))
        if not team_name:
            team_name = _format_short_name(slug)
        teams[slug] = {
            "id": slug,
            "name": _format_team_name(team_name),
            "shortName": str(_pick(row, "team_abbreviation", "short_name", "abbreviation", "display_name", default=_format_short_name(slug, team_name))),
            "seed": seed,
            "record": rec,
            "conference": str(_pick(row, "conference", "conference_name", default="")),
            "ppg": _to_float(_pick(stats, "ppg"), 0.0),
            "oppg": _to_float(_pick(stats, "opp_ppg"), 0.0),
            "pace": _to_float(_pick(stats, "pace"), 0.0),
            "eFGPct": _to_float(_pick(stats, "efg_pct"), 0.0),
            "tovPerGame": _to_float(_pick(stats, "tpg"), 0.0),
            "orebPerGame": _to_float(_pick(stats, "oreb_pg"), 0.0),
            "_sosScore": _to_float(_pick(power, "sos_score"), 0.0),
            "sosRank": 999,
            "netRank": _to_int(_pick(ranks, "netRank", "net_rank"), 999),
            "recentForm": (
                # Prefer DB last_10 (e.g. "9-1") converted to W/L list; fall back to game-log computed form
                _last10_to_wl_list(_pick(standing, "recent_form", "last_10"))[:10]
                or recent_form_by_team_id.get(team_id, [])
            ),
            "q1Record": _pick(standing, "quad1_record", "q1_record") or None,
            "q2Record": _pick(standing, "quad2_record", "q2_record") or None,
            "q3Record": _pick(standing, "quad3_record", "q3_record") or None,
            "q4Record": _pick(standing, "quad4_record", "q4_record") or None,
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
                    "ppg": _to_float(_pick(stats, "ppg"), 0.0),
                    "oppg": _to_float(_pick(stats, "opp_ppg"), 0.0),
                    "scoringMargin": _to_float(_pick(stats, "scoring_margin"), 0.0),
                    "benchPPG": _to_float(_pick(stats, "bench_ppg"), 0.0),
                    "fastbreakPPG": _to_float(_pick(stats, "fastbreak_ppg"), 0.0),
                },
                "shooting": {
                    "fgPct": _to_float(_pick(stats, "fg_pct"), 0.0),
                    "fgPctDefense": _to_float(_pick(stats, "opp_fg_pct"), 0.0),
                    "threePtPct": _to_float(_pick(stats, "three_pt_pct"), 0.0),
                    "threePtPctDefense": _to_float(_pick(stats, "opp_three_pt_pct"), 0.0),
                    "threePG": _to_float(_pick(stats, "three_pt_made_pg"), 0.0),
                    "threePtAttemptsPG": _to_float(_pick(stats, "three_pt_attempts_pg"), 0.0),
                    "ftPct": _to_float(_pick(stats, "ft_pct"), 0.0),
                    "ftMadePG": _to_float(_pick(stats, "ft_made_pg"), 0.0),
                    "eFGPct": _to_float(_pick(stats, "efg_pct"), 0.0),
                },
                "rebounding": {
                    "rpg": _to_float(_pick(stats, "rpg"), 0.0),
                    "rebMargin": _to_float(_pick(stats, "reb_margin"), 0.0),
                    "orebPG": _to_float(_pick(stats, "oreb_pg"), 0.0),
                    "drebPG": _to_float(_pick(stats, "dreb_pg"), 0.0),
                    "orebPct": _to_float(_pick(stats, "oreb_pg"), 0.0),  # per game, not %
                },
                "ballControl": {
                    "apg": _to_float(_pick(stats, "apg"), 0.0),
                    "topg": _to_float(_pick(stats, "tpg"), 0.0),
                    "astToRatio": _to_float(_pick(stats, "ast_to_ratio"), 0.0),
                    "tovPct": _to_float(_pick(stats, "tpg"), 0.0),  # per game, not %
                    "turnoverMargin": _to_float(_pick(stats, "turnover_margin"), 0.0),
                    "turnoversForcedPG": _to_float(_pick(stats, "opp_tpg"), 0.0),
                },
                "defense": {
                    "spg": _to_float(_pick(stats, "spg"), 0.0),
                    "bpg": _to_float(_pick(stats, "bpg"), 0.0),
                    "fpg": _to_float(_pick(stats, "fouls_pg"), 0.0),
                    "oppg": _to_float(_pick(stats, "opp_ppg"), 0.0),
                    "fgPctDefense": _to_float(_pick(stats, "opp_fg_pct"), 0.0),
                    "threePtPctDefense": _to_float(_pick(stats, "opp_three_pt_pct"), 0.0),
                },
                "tempo": {
                    "pace": _to_float(_pick(stats, "pace"), 0.0),
                    "winPct": 0.0,
                },
                "rankings": {
                    "netRank": _to_int(_pick(ranks, "netRank"), 999),
                    "apRank": _pick(ranks, "apRank", default=None),
                    "sosRank": 999,
                    "powerScore": _to_float(_pick(power, "power_score", "score"), 50.0),
                },
                "schedule": {
                    "q1Record": _pick(standing, "quad1_record", "q1_record") or None,
                    "q2Record": _pick(standing, "quad2_record", "q2_record") or None,
                    "q3Record": _pick(standing, "quad3_record", "q3_record") or None,
                    "q4Record": _pick(standing, "quad4_record", "q4_record") or None,
                },
                "percentiles": _pick(power, "percentiles", default={}) or {},
            },
        }

    # Compute SOS rank from sos_score (higher score = better SOS = lower rank)
    slugs_by_sos = sorted(
        teams.keys(),
        key=lambda s: teams[s].get("_sosScore", 0),
        reverse=True,
    )
    for rank, slug in enumerate(slugs_by_sos, start=1):
        teams[slug]["sosRank"] = rank
        teams[slug]["stats"]["rankings"]["sosRank"] = rank
        del teams[slug]["_sosScore"]

    # Compute win % from the record string (more reliable than stats.wins)
    for slug, team in teams.items():
        rec = team.get("record", "")
        if rec and "-" in rec:
            parts = rec.split("-")
            try:
                w = int(parts[0])
                total = sum(int(p) for p in parts)
                if total > 0:
                    team["stats"]["tempo"]["winPct"] = w / total
            except (ValueError, IndexError):
                pass

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
    return teams.get(slug, {"id": slug, "name": _format_short_name(slug), "shortName": _format_short_name(slug)})


def _round_from_row(row: dict[str, Any]) -> int:
    return _to_int(_pick(row, "round", "round_number", "tournament_round"), 1)


def _load_team_odds() -> dict[str, dict[str, Any]]:
    """Load latest moneyline/spread/total odds by joining odds -> games -> teams."""
    try:
        rows = fetch_all(
            """
            SELECT o.game_id, o.market_type, o.selection_side, o.line, o.price, o.fetched_at,
                   g.home_team_id, g.away_team_id
            FROM ncaab_event_odds o
            JOIN ncaab_games g ON g.game_id = o.game_id
            WHERE g.game_date >= CURRENT_DATE - interval '1 day'
            """
        )
    except Exception as exc:
        logger.warning("Could not load joined odds rows: %s", exc)
        return {}
    if not rows:
        return {}

    teams_rows = _safe_table("ncaab_teams")
    team_id_to_slug: dict[str, str] = {}
    for tr in teams_rows:
        tid = str(tr.get("team_id", "")).strip()
        slug = _team_key(tr)
        if tid and slug:
            team_id_to_slug[tid] = slug

    game_market_rows: dict[int, dict[str, dict[str, Any]]] = {}
    game_info: dict[int, dict[str, Any]] = {}
    for row in rows:
        game_id = _to_int(row.get("game_id"), 0)
        if game_id <= 0:
            continue
        mtype = str(row.get("market_type", "")).strip().lower()
        side = str(row.get("selection_side", "")).strip().lower()
        if not mtype or not side:
            continue

        market_key = f"{mtype}:{side}"
        ts = str(row.get("fetched_at") or "")
        bucket = game_market_rows.setdefault(game_id, {})
        cur = bucket.get(market_key)
        if cur is not None and ts <= str(cur.get("_ts", "")):
            continue
        bucket[market_key] = {
            "_ts": ts,
            "line": _to_float(row.get("line"), 0.0),
            "price": _to_int(row.get("price"), 0),
        }
        game_info[game_id] = {
            "home_id": str(row.get("home_team_id", "")).strip(),
            "away_id": str(row.get("away_team_id", "")).strip(),
        }

    def _pick_market(
        bucket: dict[str, dict[str, Any]],
        market_names: tuple[str, ...],
        sides: tuple[str, ...],
    ) -> dict[str, Any] | None:
        for market_name in market_names:
            for side in sides:
                key = f"{market_name}:{side}"
                if key in bucket:
                    return bucket[key]
        return None

    flat: dict[str, dict[str, Any]] = {}
    for game_id, bucket in game_market_rows.items():
        info = game_info.get(game_id, {})
        home_slug = team_id_to_slug.get(info.get("home_id", ""), "")
        away_slug = team_id_to_slug.get(info.get("away_id", ""), "")
        if not home_slug or not away_slug:
            continue

        home_ml = _pick_market(bucket, ("moneyline", "h2h"), ("home",))
        away_ml = _pick_market(bucket, ("moneyline", "h2h"), ("away",))
        spread_row = _pick_market(bucket, ("point_spread", "spread"), ("home", "away"))
        total_row = _pick_market(bucket, ("total_points", "total"), ("over", "under"))

        game_odds = {
            "homeSlug": home_slug,
            "awaySlug": away_slug,
            "homeML": _to_int((home_ml or {}).get("price"), 0),
            "awayML": _to_int((away_ml or {}).get("price"), 0),
            "spread": _to_float((spread_row or {}).get("line"), 0.0),
            "total": _to_float((total_row or {}).get("line"), 0.0),
        }

        flat[home_slug] = game_odds
        flat[away_slug] = game_odds

    return flat


def get_bracket(teams: dict[str, dict[str, Any]]) -> dict[str, Any]:
    bracket = run_bracketology(shuffle=False, variance=0.0, seed=None)

    team_odds = _load_team_odds()

    try:
        analysis_rows = fetch_all(
            """
            SELECT a.*,
                   ht.team_slug AS home_team_slug,
                   at.team_slug AS away_team_slug
            FROM ncaab_matchup_analyses a
            JOIN ncaab_games g ON g.game_id = a.game_id
            LEFT JOIN ncaab_teams ht ON ht.team_id = g.home_team_id
            LEFT JOIN ncaab_teams at ON at.team_id = g.away_team_id
            """
        )
    except Exception as exc:
        logger.warning("Could not load matchup analyses with team slugs: %s", exc)
        analysis_rows = []

    bracket_narratives: dict[str, dict[str, Any]] = {}
    try:
        narrative_rows = fetch_all(
            """
            SELECT title, content
            FROM ncaab_matchup_notes
            WHERE note_type = 'bracket_narrative'
            """
        )
        for nr in narrative_rows:
            title = str(nr.get("title", "")).strip()
            match = re.match(r"^bracket:([^:]+):vs:([^:]+)$", title)
            if not match:
                continue
            slug1, slug2 = match.group(1), match.group(2)
            try:
                parsed = json.loads(str(nr.get("content", "{}")))
                bracket_narratives[(slug1, slug2)] = parsed
                bracket_narratives[(slug2, slug1)] = parsed
            except (json.JSONDecodeError, TypeError):
                continue
    except Exception as exc:
        logger.warning("Could not load bracket narratives: %s", exc)
    analysis_by_slugs: dict[tuple[str, str], dict[str, Any]] = {}
    for row in analysis_rows:
        s1 = _team_key({"team_slug": _pick(row, "home_team_slug", default="")})
        s2 = _team_key({"team_slug": _pick(row, "away_team_slug", default="")})
        if s1 and s2:
            # Store under both orderings for lookup
            analysis_by_slugs[(s1, s2)] = row
            analysis_by_slugs[(s2, s1)] = row
    
    # Merge full team data and analysis into matchups
    for matchup in bracket.get("matchups", []):
        slug1 = matchup.get("team1Slug")
        slug2 = matchup.get("team2Slug")
        
        if slug1 and slug1 in teams:
            matchup["team1Full"] = teams[slug1]
        if slug2 and slug2 in teams:
            matchup["team2Full"] = teams[slug2]

        odds = team_odds.get(slug1) or team_odds.get(slug2)
        if odds and odds.get("total"):
            matchup["odds"] = {
                "homeML": odds["homeML"],
                "awayML": odds["awayML"],
                "spread": odds["spread"],
                "total": odds["total"],
            }
        
        # Merge matchup analysis if available
        analysis_row = analysis_by_slugs.get((slug1, slug2))
        if analysis_row:
            rec = str(_pick(analysis_row, "recommendation", default="")).strip()
            factors = _pick(analysis_row, "factors", default={})
            if isinstance(factors, dict):
                analysis_text = json.dumps(factors)
            else:
                analysis_text = str(factors or "")
            if rec and not analysis_text:
                analysis_text = rec
            
            # Only override if we have actual data
            if analysis_text:
                matchup["analysis"] = analysis_text
            if rec:
                matchup["rotobotPick"] = rec
                matchup["pickReasoning"] = str(_pick(factors if isinstance(factors, dict) else {}, "pick_reasoning", default=""))
            confidence = _to_int(_pick(analysis_row, "confidence", "confidence_score", default=0), 0)
            if confidence > 0:
                matchup["rotobotConfidence"] = confidence

        if not matchup.get("analysis") or matchup["analysis"] == "":
            narrative = bracket_narratives.get((slug1, slug2))
            if narrative:
                matchup["analysis"] = narrative.get("analysis", "")
                matchup["proTeam1"] = narrative.get("proTeam1", [])
                matchup["proTeam2"] = narrative.get("proTeam2", [])
                if narrative.get("rotobotPick"):
                    matchup["rotobotPick"] = narrative["rotobotPick"]
                if narrative.get("rotobotConfidence"):
                    matchup["rotobotConfidence"] = int(narrative["rotobotConfidence"])
                if narrative.get("pickReasoning"):
                    matchup["pickReasoning"] = narrative["pickReasoning"]

    return bracket


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
    try:
        row = fetch_one(
            """
            SELECT a.*
            FROM ncaab_matchup_analyses a
            JOIN ncaab_games g ON g.game_id = a.game_id
            JOIN ncaab_teams ht ON ht.team_id = g.home_team_id
            JOIN ncaab_teams at ON at.team_id = g.away_team_id
            WHERE (LOWER(ht.team_slug) = %s AND LOWER(at.team_slug) = %s)
               OR (LOWER(ht.team_slug) = %s AND LOWER(at.team_slug) = %s)
            ORDER BY COALESCE(a.updated_at, a.created_at) DESC
            LIMIT 1
            """,
            (team1_slug, team2_slug, team2_slug, team1_slug),
        )
    except Exception:
        return None
    if not row:
        return None
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
