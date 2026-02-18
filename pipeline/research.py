"""
3-Layer Smart Research Engine: Tavily → Trafilatura → Perplexity.

Layer 1 (Tavily): Targeted web search with domain locking to basketball sources.
Layer 2 (Trafilatura): Deep content extraction from URLs where raw content is thin.
Layer 3 (Perplexity): Synthesize extracted articles into a structured scouting report.

Fallback chain: Tavily → Perplexity-only → raw snippets.
"""

import logging
import os
import time

import trafilatura
from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

load_dotenv()

logger = logging.getLogger(__name__)

PERPLEXITY_MODEL = "sonar"

BASKETBALL_DOMAINS = [
    "espn.com",
    "cbssports.com",
    "theathletic.com",
    "sports-reference.com",
    "barttorvik.com",
    "kenpom.com",
    "247sports.com",
    "si.com",
    "ncaa.com",
    "bleacherreport.com",
    "yahoo.com/sports",
]

MAX_ARTICLE_CHARS = 3000
MAX_CONTEXT_CHARS = 15000


def _tavily_search(query: str, topic: str = "news", max_results: int = 8) -> list[dict]:
    """Layer 1: Tavily search locked to basketball domains."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        logger.warning("TAVILY_API_KEY not set — skipping Tavily layer")
        return []

    try:
        client = TavilyClient(api_key=api_key)
        results = client.search(
            query=query,
            topic=topic,
            search_depth="advanced",
            max_results=max_results,
            include_domains=BASKETBALL_DOMAINS,
            include_raw_content=True,
            include_answer=True,
        )
        items = results.get("results", [])
        answer = results.get("answer", "")
        logger.info("  Tavily returned %d results (answer: %d chars)", len(items), len(answer or ""))
        return items
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
        return []


def _extract_articles(tavily_results: list[dict]) -> str:
    """Layer 2: Extract full article text via Trafilatura for thin results."""
    articles = []
    for r in tavily_results:
        title = r.get("title", "")
        url = r.get("url", "")
        raw = r.get("raw_content", "") or ""

        if len(raw) < 200:
            try:
                html = trafilatura.fetch_url(url)
                if html:
                    extracted = trafilatura.extract(html) or ""
                    if len(extracted) > len(raw):
                        raw = extracted
            except Exception:
                pass

        if not raw:
            raw = r.get("content", "")

        raw = raw[:MAX_ARTICLE_CHARS]

        if raw:
            articles.append(f"### {title}\nSource: {url}\n\n{raw}")

    combined = "\n\n---\n\n".join(articles)
    if len(combined) > MAX_CONTEXT_CHARS:
        combined = combined[:MAX_CONTEXT_CHARS] + "\n\n[...truncated]"

    logger.info("  Extracted %d articles (%d chars total)", len(articles), len(combined))
    return combined


def _perplexity_synthesize(prompt: str) -> str:
    """Layer 3: Perplexity synthesizes extracted content (no independent search)."""
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key:
        logger.warning("PERPLEXITY_API_KEY not set — skipping synthesis")
        return ""

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        resp = client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.warning("Perplexity synthesis failed: %s", e)
        return ""


def _perplexity_direct_search(prompt: str) -> str:
    """Fallback: Use Perplexity as a direct search (old behavior)."""
    return _perplexity_synthesize(prompt)


def research_team_news(team_name: str, conference: str) -> str:
    """
    Full 3-layer research for a team's latest news/injury/roster context.

    Returns a structured scouting report string.
    """
    logger.info("Researching team news: %s (%s)", team_name, conference)

    query = (
        f"{team_name} men's basketball injuries roster news "
        f"2025-26 NCAA tournament March Madness"
    )
    tavily_results = _tavily_search(query, topic="news", max_results=8)

    if tavily_results:
        article_text = _extract_articles(tavily_results)

        if article_text:
            synthesis_prompt = f"""You are given several recent news articles about {team_name} men's basketball ({conference} conference).
Synthesize them into a scouting report with these sections:
1. INJURIES — current injuries, day-to-day status, returns. Player names and roles.
2. ROSTER CHANGES — transfers, suspensions, eligibility changes this season.
3. RECENT FORM — results from last 5-10 games, quality wins, concerning losses.
4. TOURNAMENT OUTLOOK — projected seed, bracket region, bubble status.
5. ANALYST TAKES — what ESPN/CBS analysts say about their March ceiling.

SOURCE ARTICLES:
{article_text}

Rules:
- Only discuss men's basketball. Ignore any football or other sport content.
- Use specific player names, dates, and numbers from the articles.
- Use bullet points within each section.
- If a section has no relevant info in the articles, write "No recent reports."
"""
            report = _perplexity_synthesize(synthesis_prompt)
            if report:
                return report

        snippets = "\n".join(
            f"- {r.get('title', '')}: {r.get('content', '')[:200]}"
            for r in tavily_results[:5]
        )
        if snippets:
            logger.info("  Falling back to raw Tavily snippets")
            return f"## Recent News for {team_name}\n\n{snippets}"

    logger.info("  Tavily returned nothing — falling back to Perplexity direct search")
    fallback_prompt = f"""SPORT: NCAA Division I Men's Basketball (NOT football, NOT women's basketball).
TEAM: {team_name} men's basketball team, {conference} conference.
SEASON: 2025-26 college basketball season.
CONTEXT: Preparing for the 2026 NCAA Men's Basketball Tournament (March Madness).

Search for the latest MEN'S BASKETBALL news about {team_name}. Report on:
1. INJURIES: Current basketball injuries, day-to-day players, recent returns.
2. ROSTER: Basketball transfers, suspensions, eligibility issues.
3. RECENT GAMES: Last 5-10 men's basketball games — wins/losses, scores.
4. MARCH MADNESS SEED: Projected NCAA Tournament seed and bracket region.
5. ANALYST TAKES: What basketball analysts say about their NCAA Tournament ceiling.

IMPORTANT: Only report on MEN'S COLLEGE BASKETBALL. No football.
Use bullet points. Be specific with player names and dates."""
    return _perplexity_direct_search(fallback_prompt)


def research_matchup_trends(
    team1_name: str, team2_name: str,
    seed1: int, seed2: int,
    style1: str, style2: str,
) -> str:
    """
    Full 3-layer research for historical tournament trends relevant to a matchup.

    Returns a structured trends report string.
    """
    logger.info("Researching matchup trends: (%d) %s vs (%d) %s", seed1, team1_name, seed2, team2_name)

    query = (
        f"NCAA March Madness basketball #{seed1} seed vs #{seed2} seed "
        f"historical results upsets trends"
    )
    tavily_results = _tavily_search(query, topic="general", max_results=6)

    style_query = (
        f"{team1_name} vs {team2_name} men's basketball 2026 NCAA tournament preview matchup"
    )
    tavily_results_style = _tavily_search(style_query, topic="news", max_results=4)
    tavily_results.extend(tavily_results_style)

    if tavily_results:
        article_text = _extract_articles(tavily_results)

        if article_text:
            synthesis_prompt = f"""You are given articles about NCAA Men's Basketball Tournament history and a specific matchup preview.
MATCHUP: ({seed1}) {team1_name} vs ({seed2}) {team2_name}.

Synthesize into a trends report with these sections:

1. SEED HISTORY — All-time win rate for #{seed1} vs #{seed2} in March Madness. Name 2-3 notable upsets at this seed line.
2. STYLE CLASH — {team1_name} style: {style1}. {team2_name} style: {style2}. How these styles match up historically in tournament play.
3. CONFERENCE PERFORMANCE — How these conferences have performed recently in March Madness.
4. WHAT DECIDES IT — At this seed line, what factors decide games (defense, FT shooting, experience, etc.)?
5. UPSET WATCH — If applicable, recent tournament upsets with similar profiles and what caused them.

SOURCE ARTICLES:
{article_text}

Rules:
- Only discuss NCAA Men's Basketball. No football.
- Use specific years, scores, team names from the articles.
- Bullet points within each section."""
            report = _perplexity_synthesize(synthesis_prompt)
            if report:
                return report

        snippets = "\n".join(
            f"- {r.get('title', '')}: {r.get('content', '')[:200]}"
            for r in tavily_results[:5]
        )
        if snippets:
            return f"## Tournament Trends: ({seed1}) {team1_name} vs ({seed2}) {team2_name}\n\n{snippets}"

    logger.info("  Tavily returned nothing — falling back to Perplexity direct search")
    fallback_prompt = f"""SPORT: NCAA Division I Men's Basketball Tournament (March Madness). NOT football.
MATCHUP: ({seed1}) {team1_name} vs ({seed2}) {team2_name}.

Research BASKETBALL-ONLY historical trends:
1. SEED HISTORY: #{seed1} vs #{seed2} all-time win rate in March Madness. Notable basketball upsets (2018-2025).
2. STYLE CLASH: {team1_name} style: {style1}. {team2_name} style: {style2}. Historical implications.
3. CONFERENCE PERFORMANCE: How these conferences perform in March Madness.
4. WHAT DECIDES IT: Key factors at this seed line.
5. UPSET WATCH: Recent upsets with similar profiles.

CRITICAL: Only NCAA MEN'S BASKETBALL. No football.
Bullet points with specific years, scores, team names."""
    return _perplexity_direct_search(fallback_prompt)
