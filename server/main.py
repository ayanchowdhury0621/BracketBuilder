"""
BracketBuilder API Server.

Serves pipeline data (teams, bracket, players) and proxies Gemini matchup generation.

Usage:
    uvicorn server.main:app --port 8002 --reload
"""

import json
import logging
import os
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = PROJECT_ROOT / "data" / "export"

sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="BracketBuilder API", version="1.0.0")

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "https://bracketbuilder.vercel.app",
]

_extra_origin = os.getenv("CORS_ORIGIN", "")
if _extra_origin:
    ALLOWED_ORIGINS.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root route so Render health check and browser visits don't 404."""
    return {
        "name": "BracketBuilder API",
        "docs": "/docs",
        "health": "/api/health",
    }


# ── JSON Data Loading (file-backed, refreshable) ────────────────────────────

_data_cache: dict[str, Any] = {}
_data_timestamps: dict[str, float] = {}
CACHE_TTL = 60  # seconds


def _load_json(filename: str) -> Any:
    """Load JSON file with TTL caching."""
    path = EXPORT_DIR / filename
    now = time.time()

    if filename in _data_cache and (now - _data_timestamps.get(filename, 0)) < CACHE_TTL:
        return _data_cache[filename]

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {filename}")

    with open(path) as f:
        data = json.load(f)

    _data_cache[filename] = data
    _data_timestamps[filename] = now
    return data


# ── Data Endpoints ───────────────────────────────────────────────────────────

@app.get("/api/teams")
def get_teams():
    """All teams with full stats, style profiles, and key player info."""
    return _load_json("teams.json")


@app.get("/api/bracket")
def get_bracket():
    """Full bracket: field, regions, matchups (R1 with Gemini narratives)."""
    return _load_json("bracket.json")


@app.get("/api/players")
def get_all_players():
    """All players grouped by team slug (top 8 per team by PPG)."""
    full = _load_json("players_full.json")
    trimmed = {}
    for slug, players in full.items():
        sorted_p = sorted(players, key=lambda p: p.get("stats", {}).get("ppg", 0), reverse=True)
        trimmed[slug] = sorted_p[:8]
    return trimmed


@app.get("/api/players/{team_slug}")
def get_team_players(team_slug: str):
    """Top 8 players for a specific team (starters + key bench guys)."""
    all_players = _load_json("players_full.json")
    players = all_players.get(team_slug)
    if players is None:
        raise HTTPException(status_code=404, detail=f"No players found for team: {team_slug}")
    sorted_p = sorted(players, key=lambda p: p.get("stats", {}).get("ppg", 0), reverse=True)
    return sorted_p[:8]


@app.get("/api/summary")
def get_summary():
    """Pipeline summary stats."""
    return _load_json("summary.json")


@app.get("/api/conferences")
def get_conferences():
    """Conference data."""
    return _load_json("conferences.json")


@app.get("/api/power-rankings")
def get_power_rankings():
    """Power rankings."""
    return _load_json("power_rankings.json")


# ── Gemini Matchup Proxy ────────────────────────────────────────────────────

class MatchupRequest(BaseModel):
    team1Slug: str
    team2Slug: str
    round: int = 2
    region: str = "East"


_narrative_memory_cache: dict[str, dict] = {}

_gemini_client = None
_perplexity_news: dict[str, str] = {}


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        from pipeline.gemini_narrative import GeminiClient
        _gemini_client = GeminiClient(gemini_key)
    return _gemini_client


def _load_news_cache():
    """Load cached Perplexity news from file system."""
    global _perplexity_news
    if _perplexity_news:
        return _perplexity_news

    # Check gemini_cache/news first
    cache_dir = PROJECT_ROOT / "data" / "gemini_cache" / "news"
    if cache_dir.exists():
        for f in cache_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                slug = f.stem
                _perplexity_news[slug] = data.get("content", data.get("news", ""))
            except Exception:
                pass

    # Also pull newsContext from teams.json if populated
    try:
        teams = _load_json("teams.json")
        for slug, t in teams.items():
            ctx = t.get("newsContext", "")
            if ctx and slug not in _perplexity_news:
                _perplexity_news[slug] = ctx
    except Exception:
        pass

    logger.info("Loaded %d cached news entries", len(_perplexity_news))
    return _perplexity_news


@app.get("/api/news")
def get_all_news():
    """All cached Perplexity news/injury context by team slug."""
    return _load_news_cache()


@app.get("/api/news/{team_slug}")
def get_team_news(team_slug: str):
    """Perplexity news/injury context for a specific team."""
    news = _load_news_cache()
    return {"slug": team_slug, "news": news.get(team_slug, "")}


@app.post("/api/matchup")
def generate_matchup(req: MatchupRequest):
    """
    Generate a Gemini matchup analysis for any two teams.
    Uses dual caching: in-memory LRU + file-based cache.
    """
    cache_key = f"{req.team1Slug}_vs_{req.team2Slug}"

    if cache_key in _narrative_memory_cache:
        logger.info("Memory cache hit: %s", cache_key)
        return _narrative_memory_cache[cache_key]

    teams = _load_json("teams.json")
    team1 = teams.get(req.team1Slug)
    team2 = teams.get(req.team2Slug)

    if not team1:
        raise HTTPException(status_code=404, detail=f"Team not found: {req.team1Slug}")
    if not team2:
        raise HTTPException(status_code=404, detail=f"Team not found: {req.team2Slug}")

    game = {
        "id": f"{req.region.lower()}-r{req.round}-live",
        "round": req.round,
        "region": req.region,
        "team1Seed": team1.get("seed", 0),
        "team2Seed": team2.get("seed", 0),
        "team1": team1.get("name", req.team1Slug),
        "team1Slug": req.team1Slug,
        "team2": team2.get("name", req.team2Slug),
        "team2Slug": req.team2Slug,
    }

    news = _load_news_cache()
    news1 = news.get(req.team1Slug, "")
    news2 = news.get(req.team2Slug, "")

    gemini = _get_gemini_client()
    from pipeline.gemini_narrative import generate_matchup_narrative
    narrative = generate_matchup_narrative(gemini, game, team1, team2, news1, news2)

    result = {
        "analysis": narrative.get("analysis", ""),
        "proTeam1": narrative.get("proTeam1", []),
        "proTeam2": narrative.get("proTeam2", []),
        "rotobotPick": narrative.get("rotobotPick", ""),
        "rotobotConfidence": narrative.get("rotobotConfidence", 50),
        "pickReasoning": narrative.get("pickReasoning", ""),
    }

    _narrative_memory_cache[cache_key] = result
    logger.info("Generated matchup: %s vs %s → pick: %s (%d%%)",
                req.team1Slug, req.team2Slug,
                result["rotobotPick"], result["rotobotConfidence"])
    return result


class NewsFetchRequest(BaseModel):
    teamSlug: str
    force: bool = False


@app.post("/api/news/fetch")
def fetch_news_live(req: NewsFetchRequest):
    """Fetch fresh news via the smart research pipeline (Tavily → Trafilatura → Perplexity)."""
    news = _load_news_cache()
    if news.get(req.teamSlug) and not req.force:
        return {"slug": req.teamSlug, "news": news[req.teamSlug], "cached": True}

    teams = _load_json("teams.json")
    team = teams.get(req.teamSlug)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team not found: {req.teamSlug}")

    from pipeline.gemini_narrative import _cache_path
    if req.force:
        cache_file = _cache_path("news", req.teamSlug)
        if os.path.exists(cache_file):
            os.remove(cache_file)

    try:
        from pipeline.research import research_team_news
        content = research_team_news(team.get("name", ""), team.get("conference", ""))
    except Exception as e:
        logger.warning("Research engine failed for %s: %s — trying Perplexity fallback", req.teamSlug, e)
        pplx_key = os.getenv("PERPLEXITY_API_KEY", "")
        if pplx_key:
            from pipeline.gemini_narrative import PerplexityClient
            pplx = PerplexityClient(pplx_key)
            content = pplx.search(
                f"Latest NCAA men's basketball news for {team.get('name', '')}. No football."
            )
        else:
            content = ""

    from pipeline.gemini_narrative import _write_cache
    _write_cache("news", req.teamSlug, {"content": content, "team": team.get("name", "")})
    _perplexity_news[req.teamSlug] = content
    return {"slug": req.teamSlug, "news": content, "cached": False}


class TrendsFetchRequest(BaseModel):
    team1Slug: str
    team2Slug: str


_trends_cache: dict[str, str] = {}


@app.post("/api/trends/fetch")
def fetch_trends_live(req: TrendsFetchRequest):
    """Fetch historical tournament trends via the smart research pipeline."""
    cache_key = f"{req.team1Slug}_vs_{req.team2Slug}"

    if cache_key in _trends_cache:
        return {"key": cache_key, "trends": _trends_cache[cache_key], "cached": True}

    teams = _load_json("teams.json")
    team1 = teams.get(req.team1Slug)
    team2 = teams.get(req.team2Slug)
    if not team1 or not team2:
        raise HTTPException(status_code=404, detail="Team not found")

    try:
        from pipeline.research import research_matchup_trends
        content = research_matchup_trends(
            team1.get("name", ""), team2.get("name", ""),
            team1.get("seed", 0), team2.get("seed", 0),
            team1.get("styleIdentity", ""), team2.get("styleIdentity", ""),
        )
    except Exception as e:
        logger.warning("Research engine failed for trends %s: %s — trying Perplexity fallback", cache_key, e)
        pplx_key = os.getenv("PERPLEXITY_API_KEY", "")
        if pplx_key:
            from pipeline.gemini_narrative import PerplexityClient
            pplx = PerplexityClient(pplx_key)
            content = pplx.search(
                f"NCAA March Madness #{team1.get('seed', 0)} vs #{team2.get('seed', 0)} "
                f"{team1.get('name', '')} vs {team2.get('name', '')} basketball trends. No football."
            )
        else:
            content = ""

    from pipeline.gemini_narrative import _write_cache
    _write_cache("trends", cache_key, {
        "content": content,
        "team1": team1.get("name", ""),
        "team2": team2.get("name", ""),
    })
    _trends_cache[cache_key] = content
    return {"key": cache_key, "trends": content, "cached": False}


# ── ESPN Integration (Logos + Headshots via S3 manifest) ─────────────────────

_espn_manifest: dict | None = None


def _load_espn_manifest() -> dict:
    """Load the S3 manifest written by pipeline/sync_espn_assets.py."""
    global _espn_manifest
    if _espn_manifest is not None:
        return _espn_manifest

    manifest_path = EXPORT_DIR / "espn_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            _espn_manifest = json.load(f)
        logger.info("Loaded ESPN manifest: %d logos, %d headshot teams",
                     len(_espn_manifest.get("logos", {})),
                     len(_espn_manifest.get("headshots", {})))
    else:
        logger.warning("ESPN manifest not found at %s — run sync_espn_assets first", manifest_path)
        _espn_manifest = {"logos": {}, "headshots": {}}

    return _espn_manifest


@app.get("/api/espn/logos")
def get_espn_logos():
    """Return {our_slug: s3_logo_url} for all teams with synced logos."""
    manifest = _load_espn_manifest()
    return manifest.get("logos", {})


@app.get("/api/espn/roster/{team_slug}")
def get_espn_roster(team_slug: str):
    """Return headshot S3 URLs for a team's players from manifest."""
    manifest = _load_espn_manifest()
    team_headshots = manifest.get("headshots", {}).get(team_slug, {})
    roster = [{"name": name, "headshot": url} for name, url in team_headshots.items()]
    return roster


# ── Health / Meta ────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "data_dir": str(EXPORT_DIR),
        "files": [f.name for f in EXPORT_DIR.glob("*.json")] if EXPORT_DIR.exists() else [],
    }


@app.post("/api/cache/clear")
def clear_cache():
    """Clear all in-memory caches."""
    _data_cache.clear()
    _data_timestamps.clear()
    _narrative_memory_cache.clear()
    return {"status": "cleared"}
