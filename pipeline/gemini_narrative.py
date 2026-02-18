"""
BracketBuilder Narrative Engine — Gemini 3 Flash + Perplexity Sonar.

Phase 1: Perplexity Sonar fetches real-time news/injury context per bracket team.
Phase 2: Gemini 3 Flash Preview generates stat-backed team blurbs, matchup
         analyses, pro/con bullets, and picks for every Round-of-64 game.

Usage:
    python -m pipeline.gemini_narrative                    # full run
    python -m pipeline.gemini_narrative --skip-news        # reuse cached news
    python -m pipeline.gemini_narrative --bracket bracket_shuffle_42.json
"""

import argparse
import hashlib
import json
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
from google import genai
from openai import OpenAI

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
EXPORT_DIR = os.path.join(DATA_DIR, "export")
CACHE_DIR = os.path.join(DATA_DIR, "gemini_cache")

GEMINI_MODEL = "gemini-3-flash-preview"
PERPLEXITY_MODEL = "sonar"


# ── Clients ──────────────────────────────────────────────────────────────────

class PerplexityClient:
    """Rate-limited Perplexity Sonar client via OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, requests_per_second: float = 2.0):
        self.client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        self.min_interval = 1.0 / requests_per_second
        self._last_request = 0.0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.time()

    def search(self, prompt: str, max_retries: int = 3) -> str:
        for attempt in range(1, max_retries + 1):
            self._rate_limit()
            try:
                resp = self.client.chat.completions.create(
                    model=PERPLEXITY_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                logger.warning("Perplexity error (attempt %d/%d): %s", attempt, max_retries, e)
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
        return ""


class GeminiClient:
    """Rate-limited Gemini client with JSON output mode."""

    def __init__(self, api_key: str, requests_per_second: float = 1.0):
        self.client = genai.Client(api_key=api_key)
        self.min_interval = 1.0 / requests_per_second
        self._last_request = 0.0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.time()

    def generate(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> dict:
        for attempt in range(1, max_retries + 1):
            self._rate_limit()
            try:
                resp = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=user_prompt,
                    config={
                        "system_instruction": system_prompt,
                        "response_mime_type": "application/json",
                    },
                )
                text = resp.text or ""
                return json.loads(text)
            except json.JSONDecodeError:
                logger.warning("Gemini returned non-JSON (attempt %d/%d), retrying", attempt, max_retries)
                if attempt < max_retries:
                    time.sleep(2)
            except Exception as e:
                logger.warning("Gemini error (attempt %d/%d): %s", attempt, max_retries, e)
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
        return {}


# ── Cache ────────────────────────────────────────────────────────────────────

def _cache_path(subdir: str, key: str) -> str:
    safe_key = key.replace("/", "_").replace(" ", "-")
    d = os.path.join(CACHE_DIR, subdir)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{safe_key}.json")


def _read_cache(subdir: str, key: str, max_age_hours: float = 0) -> dict | None:
    path = _cache_path(subdir, key)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        if max_age_hours > 0:
            ts = data.get("_timestamp", 0)
            if time.time() - ts > max_age_hours * 3600:
                return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(subdir: str, key: str, data: dict):
    data["_timestamp"] = time.time()
    path = _cache_path(subdir, key)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _payload_hash(payload: str) -> str:
    return hashlib.md5(payload.encode()).hexdigest()[:12]


# ── Markdown Payload Builders ────────────────────────────────────────────────

def build_team_markdown(team: dict, news: str = "") -> str:
    """Render a compact markdown data block for one team."""
    name = team.get("name", "")
    conf = team.get("conference", "")
    record = team.get("record", "")
    seed = team.get("seed", 0)
    net = team.get("netRank", 999)
    score = team.get("rotobotScore", 50)

    seed_str = f", #{seed} seed" if seed and seed > 0 else ""
    header = f"## {name} ({conf}) — {record}, NET #{net}{seed_str}, RotoBot Score: {score}"

    identity = team.get("styleIdentity", "")
    weakness = team.get("styleWeakness", "")
    bullets = team.get("styleBullets", "")
    key_player = team.get("keyPlayer", "")
    key_stat = team.get("keyPlayerStat", "")

    stats = team.get("stats", {})
    scoring = stats.get("scoring", {})
    shooting = stats.get("shooting", {})
    reb = stats.get("rebounding", {})
    ball = stats.get("ballControl", {})
    defense = stats.get("defense", {})
    tempo = stats.get("tempo", {})

    stat_line = " | ".join(filter(None, [
        f"{scoring.get('ppg', 0)} PPG",
        f"{scoring.get('oppg', 0)} OPPG",
        f"{tempo.get('pace', 0)} pace",
        f"{shooting.get('eFGPct', 0)}% eFG",
        f"{defense.get('fgPctDefense', 0)}% opp FG",
        f"{shooting.get('threePtPct', 0)}% 3P",
        f"{shooting.get('threePtAttemptsPG', 0)} 3PA/G",
        f"{ball.get('turnoversForcedPG', 0)} TO forced/G",
        f"{reb.get('orebPG', 0)} OREB/G",
        f"{shooting.get('ftPct', 0)}% FT",
        f"{scoring.get('benchPPG', 0)} bench PPG",
        f"{ball.get('astToRatio', 0)} A/TO",
    ]))

    parts = [header, ""]
    if identity:
        parts.append(f"**Identity:** {identity}")
    parts.append(f"**Key Stats:** {stat_line}")
    if bullets:
        parts.append(f"**Scouting Bullets:** {bullets}")
    if weakness:
        parts.append(f"**Weakness:** {weakness}")
    if key_player:
        parts.append(f"**Key Player:** {key_player} — {key_stat}")
    if news:
        parts.append(f"**Recent News:** {news}")

    return "\n".join(parts)


def build_matchup_markdown(
    game: dict,
    team1: dict,
    team2: dict,
    news1: str,
    news2: str,
    edges: list[dict],
) -> str:
    """Render a full matchup markdown block for one game."""
    region = game.get("region", "")
    seed1 = game.get("team1Seed", 0)
    seed2 = game.get("team2Seed", 0)
    name1 = team1.get("name", game.get("team1", ""))
    name2 = team2.get("name", game.get("team2", ""))

    header = f"## {region} Region, Round of 64: ({seed1}) {name1} vs ({seed2}) {name2}"

    t1_md = build_team_markdown(team1, news1)
    t2_md = build_team_markdown(team2, news2)

    # Replace top-level ## with ### for nesting
    t1_md = t1_md.replace("## ", "### ", 1)
    t2_md = t2_md.replace("## ", "### ", 1)

    edge_lines = ["### Head-to-Head Edges:"]
    for e in edges:
        label = e.get("label", "")
        v1 = e.get("team1Value", 0)
        v2 = e.get("team2Value", 0)
        winner = e.get("edge", "even")
        arrow = name1 if winner == "team1" else (name2 if winner == "team2" else "Even")
        edge_lines.append(f"- {label}: {name1} {v1} vs {name2} {v2} → {arrow}")

    return "\n\n".join([header, t1_md, t2_md, "\n".join(edge_lines)])


# ── System Prompts ───────────────────────────────────────────────────────────

SYSTEM_PROMPT_BLURB = """You are RotoBot, a veteran NCAAB analyst writing team capsules for a March Madness bracket app.

**Rules:**
- Write 2-4 sentences per team
- Every sentence must reference at least one specific number (PPG, eFG%, opp FG%, etc.)
- Mention the key player by name with their stat line
- If there is relevant injury/news context, weave it into the blurb naturally
- Name the team's biggest weakness with a number
- Do NOT use generic praise like "talented" or "dangerous" without a stat to back it
- Write in present tense, confident analyst voice

**Output format:** Return ONLY a JSON object: {"rotobotBlurb": "your blurb here"}

---

### Example 1: Top Seed

**Input:**

## Iowa St. (Big 12) — 23-3, NET #5, RotoBot Score: 91.7

**Identity:** Averages 83.7 PPG at 67.7 poss/40. Elite shot quality — 58.1% eFG. Defense is the identity: 64.6 opp PPG, 41.6% opponent FG. Top-3 in Big 12 defensive efficiency.

**Key Stats:** 83.7 PPG | 64.6 OPPG | 67.7 pace | 58.1% eFG | 41.6% opp FG | 15.1 TO forced/G | 12.0 OREB/G | 66.5% FT

**Scouting Bullets:** 64.6 opp PPG • 41.6% opp FG • 58.1% eFG • 15.1 TO forced/G • 12.0 OREB/G

**Weakness:** Vulnerable at the line (66.5% FT).

**Key Player:** Milan Momcilovic — 14.5 PPG / 3.8 RPG / 1.5 APG

**Output:**

{"rotobotBlurb": "Iowa St. pairs a 58.1% eFG (top-5 nationally) with a suffocating defense that holds opponents to 41.6% FG and forces 15.1 turnovers per game. Milan Momcilovic (14.5 PPG) leads a balanced attack that scores 83.7 PPG, but the Cyclones' 66.5% free-throw shooting is a March liability — close games could hinge on the stripe."}

---

### Example 2: Mid-Major

**Input:**

## UC Irvine (Big West) — 15-9, NET #120, RotoBot Score: 69.1

**Identity:** Plays at 71.9 poss/40 (top 25% nationally) and scores 77.7 PPG. Lives at the rim and on the glass (11.7 OREB/G); doesn't rely on the three. Defense is the identity: 68.0 opp PPG, 37.8% opponent FG. Top-3 in Big West defensive efficiency.

**Key Stats:** 77.7 PPG | 68.0 OPPG | 71.9 pace | 51.0% eFG | 37.8% opp FG | 11.7 OREB/G | 68.2% FT

**Weakness:** No glaring weakness; balanced profile.

**Key Player:** Jurian Dixon — 14.5 PPG / 3.0 RPG / 2.0 APG

**Output:**

{"rotobotBlurb": "UC Irvine's 37.8% opponent FG is top-15 in D1 and the engine of a defense that holds teams to 68.0 PPG. Jurian Dixon (14.5 PPG) runs the up-tempo attack at 71.9 poss/40, and 11.7 OREB/G means second chances keep coming. The 15-9 record looks modest, but the defensive profile translates — the question is whether 51.0% eFG holds up against elite shooting."}

---

Now write a blurb for the following team:"""


SYSTEM_PROMPT_MATCHUP = """You are RotoBot, a veteran NCAAB analyst writing matchup previews for a March Madness bracket app.

**Rules:**
- `analysis`: 3-5 sentences. Name both key players. Identify the style clash and the decisive edge. Every sentence must have at least one number.
- `proTeam1` and `proTeam2`: 3-5 bullets each. Every bullet MUST contain at least one stat. Frame as reasons that team wins.
- `rotobotPick`: The team name you pick to win.
- `rotobotConfidence`: 55-99. Use the stat edges to calibrate — a 1-vs-16 with massive edges = 95+, a toss-up 8-vs-9 = 55-62.
- `pickReasoning`: 1-2 sentences explaining the pick with specific numbers.
- Do NOT hedge with "could go either way" — commit to a pick and justify it.
- Even for heavy favorites, give the underdog real, stat-backed bullets.

**Output format:** Return ONLY a JSON object with keys: analysis, proTeam1, proTeam2, rotobotPick, rotobotConfidence, pickReasoning

---

### Example: 1 vs 16

**Input:**

## East Region, Round of 64: (1) Michigan vs (16) Portland St.

### Michigan (Big Ten) — 24-1, NET #1, RotoBot Score: 97.4

**Identity:** Plays at 73.1 poss/40 (top 25% nationally) and scores 90.6 PPG. Heavy three-point attack (26.1 3PA/G at 35.4%). Defense is the identity: 68.3 opp PPG, 37.1% opponent FG. One of the Big Ten's most efficient offenses.

**Key Stats:** 90.6 PPG | 68.3 OPPG | 73.1 pace | 58.9% eFG | 37.1% opp FG | 26.1 3PA/G | 32.5 bench PPG

**Weakness:** No glaring weakness; balanced profile.

**Key Player:** Jeremy Fears Jr. — 16.5 PPG / 1.8 RPG / 12.0 APG / 1.5 SPG

### Portland St. (Big Sky) — 14-7, NET #130, RotoBot Score: 28.0

**Identity:** Averages 77.8 PPG at 69.3 poss/40. Stout defensively (69.8 opp PPG). Top-3 in Big Sky defensive efficiency.

**Key Stats:** 77.8 PPG | 69.8 OPPG | 69.3 pace | 53.1% eFG | 40.7% opp FG | 15.3 bench PPG

**Weakness:** Thin bench — starters carry the load.

**Key Player:** Terri Miller Jr. — 22.3 PPG / 5.3 RPG / 2.3 APG

### Head-to-Head Edges:
- PPG: Michigan 90.6 vs Portland St. 77.8 → Michigan
- OPPG: Michigan 68.3 vs Portland St. 69.8 → Michigan
- eFG%: Michigan 58.9% vs Portland St. 53.1% → Michigan
- Opp FG%: Michigan 37.1% vs Portland St. 40.7% → Michigan
- Pace: Michigan 73.1 vs Portland St. 69.3 → Michigan (faster)
- Bench PPG: Michigan 32.5 vs Portland St. 15.3 → Michigan
- NET: Michigan #1 vs Portland St. #130 → Michigan

**Output:**

{"analysis": "Michigan's 90.6 PPG and 58.9% eFG will overwhelm a Portland St. defense allowing 40.7% FG. Jeremy Fears Jr. (12.0 APG) will dissect the Big Sky defense, and Michigan's 32.5 bench PPG means the Wolverines can run 10 deep while Portland St.'s 15.3 bench PPG leaves Terri Miller Jr. (22.3 PPG) shouldering the load for 35+ minutes. The pace gap (73.1 vs 69.3) favors Michigan's transition game, and their 37.1% opponent FG should limit Portland St.'s half-court efficiency.", "proTeam1": ["90.6 PPG and 58.9% eFG — best offense Portland St. has faced all year", "37.1% opponent FG shuts down half-court attacks", "32.5 bench PPG means fresh legs all game vs Portland St.'s 15.3", "Jeremy Fears Jr.'s 12.0 APG will find open shooters against a 40.7% opp FG defense", "26.1 3PA/G at 35.4% stretches the floor beyond Big Sky defensive schemes"], "proTeam2": ["Terri Miller Jr. (22.3 PPG / 5.3 RPG) is a legit scorer who can get his own shot", "69.8 opp PPG shows Portland St. can defend — top-3 in the Big Sky", "53.1% eFG is respectable and could keep it competitive in spurts", "Slower pace (69.3) could limit Michigan's transition opportunities if Portland St. controls tempo"], "rotobotPick": "Michigan", "rotobotConfidence": 97, "pickReasoning": "Michigan is better in every measurable category — 90.6 PPG vs 77.8, 37.1% vs 40.7% opp FG, 32.5 vs 15.3 bench PPG. The talent and depth gap is historic-level; Portland St. would need Michigan to shoot below 30% from three to have a chance."}

---

Now write a matchup analysis for the following game:"""


# ── Phase 1: Perplexity News ────────────────────────────────────────────────

def fetch_team_news(pplx: PerplexityClient, team_name: str, conference: str, slug: str) -> str:
    cached = _read_cache("news", slug, max_age_hours=6)
    if cached and cached.get("content"):
        logger.debug("  News cache hit: %s", slug)
        return cached["content"]

    try:
        from pipeline.research import research_team_news
        content = research_team_news(team_name, conference)
    except Exception as e:
        logger.warning("Smart research failed for %s, falling back to Perplexity direct: %s", slug, e)
        content = pplx.search(
            f"Latest NCAA men's basketball news injuries roster for {team_name} ({conference}) "
            f"2025-26 season March Madness tournament. Only basketball, no football."
        )

    _write_cache("news", slug, {"content": content, "team": team_name})
    return content


def fetch_matchup_trends(pplx: PerplexityClient, team1_name: str, team2_name: str,
                         seed1: int, seed2: int, style1: str, style2: str,
                         cache_key: str) -> str:
    """Fetch historical tournament trends relevant to this specific matchup."""
    cached = _read_cache("trends", cache_key, max_age_hours=24)
    if cached and cached.get("content"):
        return cached["content"]

    try:
        from pipeline.research import research_matchup_trends
        content = research_matchup_trends(team1_name, team2_name, seed1, seed2, style1, style2)
    except Exception as e:
        logger.warning("Smart research failed for trends %s, falling back to Perplexity: %s", cache_key, e)
        content = pplx.search(
            f"NCAA March Madness basketball historical trends #{seed1} seed vs #{seed2} seed "
            f"{team1_name} vs {team2_name} upsets. Only basketball, no football."
        )

    _write_cache("trends", cache_key, {"content": content, "team1": team1_name, "team2": team2_name})
    return content


def run_phase1_news(pplx: PerplexityClient, bracket_teams: list[dict]) -> dict[str, str]:
    """Fetch news for all bracket teams. Returns {slug: news_text}."""
    logger.info("Phase 1: Fetching real-time news for %d teams...", len(bracket_teams))
    news_cache = {}
    for i, team in enumerate(bracket_teams):
        slug = team.get("id", team.get("team1Slug", ""))
        name = team.get("name", team.get("team1", ""))
        conf = team.get("conference", team.get("team1Conference", ""))
        if not slug:
            continue
        logger.info("  [%d/%d] %s", i + 1, len(bracket_teams), name)
        news_cache[slug] = fetch_team_news(pplx, name, conf, slug)
    logger.info("Phase 1 complete: %d teams with news context", len(news_cache))
    return news_cache


# ── Phase 2a: Team Blurbs ────────────────────────────────────────────────────

def generate_blurb(gemini: GeminiClient, team: dict, news: str) -> str:
    slug = team.get("id", "")
    user_md = build_team_markdown(team, news)
    payload_h = _payload_hash(user_md)

    cached = _read_cache("blurbs", slug)
    if cached and cached.get("_hash") == payload_h and cached.get("rotobotBlurb"):
        return cached["rotobotBlurb"]

    result = gemini.generate(SYSTEM_PROMPT_BLURB, user_md)
    blurb = result.get("rotobotBlurb", "")

    if blurb:
        _write_cache("blurbs", slug, {"_hash": payload_h, "rotobotBlurb": blurb})
    return blurb


def run_phase2_blurbs(gemini: GeminiClient, teams: dict[str, dict], news_cache: dict[str, str]) -> dict[str, str]:
    """Generate blurbs for all bracket teams. Returns {slug: blurb}."""
    logger.info("Phase 2a: Generating team blurbs for %d teams...", len(teams))
    blurbs = {}
    for i, (slug, team) in enumerate(teams.items()):
        news = news_cache.get(slug, "")
        logger.info("  [%d/%d] %s", i + 1, len(teams), team.get("name", slug))
        blurb = generate_blurb(gemini, team, news)
        if blurb:
            blurbs[slug] = blurb
        else:
            logger.warning("  Empty blurb for %s", slug)
    logger.info("Phase 2a complete: %d/%d blurbs generated", len(blurbs), len(teams))
    return blurbs


# ── Phase 2b: Matchup Narratives ────────────────────────────────────────────

def _compute_edges(team1: dict, team2: dict) -> list[dict]:
    """Pre-compute head-to-head stat edges for the matchup prompt."""
    categories = [
        ("PPG", "ppg", True),
        ("Opp PPG", "oppg", False),
        ("eFG%", "eFGPct", True),
        ("Opp FG%", None, False),
        ("Pace", "pace", None),
        ("OREB/G", "orebPct", True),
        ("Turnover %", "tovPct", False),
        ("SOS Rank", "sosRank", False),
        ("NET Rank", "netRank", False),
        ("RotoBot Score", "rotobotScore", True),
    ]

    edges = []
    for label, key, higher_is_better in categories:
        if key is None:
            v1 = team1.get("stats", {}).get("defense", {}).get("fgPctDefense", 0)
            v2 = team2.get("stats", {}).get("defense", {}).get("fgPctDefense", 0)
            higher_is_better = False
        else:
            v1 = team1.get(key, 0) or 0
            v2 = team2.get(key, 0) or 0

        if higher_is_better is None:
            edge = "neutral"
        elif higher_is_better:
            edge = "team1" if v1 > v2 else ("team2" if v2 > v1 else "even")
        else:
            edge = "team1" if v1 < v2 else ("team2" if v2 < v1 else "even")

        edges.append({"label": label, "team1Value": v1, "team2Value": v2, "edge": edge})
    return edges


def generate_matchup_narrative(
    gemini: GeminiClient,
    game: dict,
    team1: dict,
    team2: dict,
    news1: str,
    news2: str,
) -> dict:
    game_id = game.get("id", "unknown")
    edges = _compute_edges(team1, team2)
    user_md = build_matchup_markdown(game, team1, team2, news1, news2, edges)
    payload_h = _payload_hash(user_md)

    cached = _read_cache("matchups", game_id)
    if cached and cached.get("_hash") == payload_h and cached.get("analysis"):
        return {k: v for k, v in cached.items() if not k.startswith("_")}

    result = gemini.generate(SYSTEM_PROMPT_MATCHUP, user_md)

    if result.get("analysis"):
        _write_cache("matchups", game_id, {"_hash": payload_h, **result})
    return result


def run_phase2_matchups(
    gemini: GeminiClient,
    matchups: list[dict],
    teams: dict[str, dict],
    news_cache: dict[str, str],
) -> list[dict]:
    """Generate narratives for all matchups. Returns enriched game list."""
    logger.info("Phase 2b: Generating matchup narratives for %d games...", len(matchups))
    enriched = []

    for i, game in enumerate(matchups):
        slug1 = game.get("team1Slug", "")
        slug2 = game.get("team2Slug", "")
        team1 = teams.get(slug1, {})
        team2 = teams.get(slug2, {})
        news1 = news_cache.get(slug1, "")
        news2 = news_cache.get(slug2, "")

        name1 = game.get("team1", slug1)
        name2 = game.get("team2", slug2)
        logger.info("  [%d/%d] (%d) %s vs (%d) %s",
                     i + 1, len(matchups),
                     game.get("team1Seed", 0), name1,
                     game.get("team2Seed", 0), name2)

        narrative = generate_matchup_narrative(gemini, game, team1, team2, news1, news2)

        enriched_game = {**game}
        enriched_game["analysis"] = narrative.get("analysis", "")
        enriched_game["proTeam1"] = narrative.get("proTeam1", [])
        enriched_game["proTeam2"] = narrative.get("proTeam2", [])
        enriched_game["rotobotPick"] = narrative.get("rotobotPick", "")
        enriched_game["rotobotConfidence"] = narrative.get("rotobotConfidence", 50)
        enriched_game["pickReasoning"] = narrative.get("pickReasoning", "")
        enriched_game["team1Full"] = team1
        enriched_game["team2Full"] = team2
        enriched.append(enriched_game)

    success = sum(1 for g in enriched if g.get("analysis"))
    logger.info("Phase 2b complete: %d/%d matchups with narratives", success, len(matchups))
    return enriched


# ── Main Pipeline ────────────────────────────────────────────────────────────

def run_narrative(bracket_file: str = "bracket.json", skip_news: bool = False):
    gemini_key = os.getenv("GEMINI_API_KEY")
    pplx_key = os.getenv("PERPLEXITY_API_KEY")

    if not gemini_key:
        logger.error("GEMINI_API_KEY not set in .env")
        return
    if not pplx_key and not skip_news:
        logger.warning("PERPLEXITY_API_KEY not set — skipping news phase")
        skip_news = True

    gemini = GeminiClient(api_key=gemini_key)
    pplx = PerplexityClient(api_key=pplx_key) if pplx_key else None

    # Load data
    teams_path = os.path.join(EXPORT_DIR, "teams.json")
    bracket_path = os.path.join(EXPORT_DIR, bracket_file)

    if not os.path.exists(teams_path):
        logger.error("teams.json not found at %s — run export first", teams_path)
        return
    if not os.path.exists(bracket_path):
        logger.error("Bracket file not found at %s — run bracketology first", bracket_path)
        return

    with open(teams_path) as f:
        all_teams = json.load(f)
    with open(bracket_path) as f:
        bracket = json.load(f)

    matchups = bracket.get("matchups", [])
    if not matchups:
        logger.error("No matchups found in bracket file")
        return

    # Collect bracket team slugs
    bracket_slugs = set()
    for game in matchups:
        bracket_slugs.add(game.get("team1Slug", ""))
        bracket_slugs.add(game.get("team2Slug", ""))
    bracket_slugs.discard("")

    bracket_teams = {slug: all_teams[slug] for slug in bracket_slugs if slug in all_teams}
    logger.info("Loaded %d bracket teams, %d matchups", len(bracket_teams), len(matchups))

    # Phase 1: News
    news_cache: dict[str, str] = {}
    if not skip_news and pplx:
        team_list = [{"id": slug, "name": t.get("name", ""), "conference": t.get("conference", "")}
                     for slug, t in bracket_teams.items()]
        news_cache = run_phase1_news(pplx, team_list)
    else:
        logger.info("Skipping news phase (--skip-news or no API key)")
        for slug in bracket_slugs:
            cached = _read_cache("news", slug)
            if cached and cached.get("content"):
                news_cache[slug] = cached["content"]
        logger.info("Loaded %d cached news entries", len(news_cache))

    # Phase 2a: Blurbs
    blurbs = run_phase2_blurbs(gemini, bracket_teams, news_cache)

    # Merge blurbs into teams
    for slug, blurb in blurbs.items():
        if slug in all_teams:
            all_teams[slug]["rotobotBlurb"] = blurb
    for slug, news in news_cache.items():
        if slug in all_teams:
            all_teams[slug]["newsContext"] = news

    # Write updated teams
    with open(teams_path, "w") as f:
        json.dump(all_teams, f, indent=2, default=str)
    logger.info("Updated teams.json with %d blurbs", len(blurbs))

    # Phase 2b: Matchup narratives
    enriched_matchups = run_phase2_matchups(gemini, matchups, all_teams, news_cache)

    # Update bracket
    bracket["matchups"] = enriched_matchups
    with open(bracket_path, "w") as f:
        json.dump(bracket, f, indent=2, default=str)
    logger.info("Updated %s with matchup narratives", bracket_file)

    # Summary
    blurb_count = sum(1 for t in all_teams.values() if t.get("rotobotBlurb"))
    analysis_count = sum(1 for g in enriched_matchups if g.get("analysis"))
    pick_count = sum(1 for g in enriched_matchups if g.get("rotobotPick"))
    logger.info("\nNarrative pipeline complete:")
    logger.info("  Teams with blurbs: %d", blurb_count)
    logger.info("  Games with analysis: %d/%d", analysis_count, len(enriched_matchups))
    logger.info("  Games with picks: %d/%d", pick_count, len(enriched_matchups))


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BracketBuilder Narrative Engine")
    parser.add_argument("--skip-news", action="store_true",
                        help="Skip Perplexity news fetch (use cached)")
    parser.add_argument("--bracket", default="bracket.json",
                        help="Bracket JSON filename (default: bracket.json)")
    args = parser.parse_args()

    run_narrative(bracket_file=args.bracket, skip_news=args.skip_news)


if __name__ == "__main__":
    main()
