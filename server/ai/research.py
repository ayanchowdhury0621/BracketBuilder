"""Smart research engine: Tavily + Trafilatura + Perplexity."""

from __future__ import annotations

import logging
import os
from typing import Any

from .cache import _read_cache, _write_cache
from .clients.perplexity_client import PerplexityClient
from .clients.tavily_client import TavilySearchClient
from .settings import MAX_ARTICLE_CHARS, MAX_CONTEXT_CHARS

logger = logging.getLogger(__name__)


def _extract_articles(tavily_results: list[dict[str, Any]]) -> str:
    articles: list[str] = []
    try:
        import trafilatura
    except Exception:
        trafilatura = None  # type: ignore

    for r in tavily_results:
        title = r.get("title", "")
        url = r.get("url", "")
        raw = r.get("raw_content", "") or ""

        if len(raw) < 200 and trafilatura is not None:
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
    return combined


def research_team_news(team_name: str, conference: str) -> str:
    query = (
        f"{team_name} men's basketball injuries roster news "
        f"2025-26 NCAA tournament March Madness"
    )
    tavily_results = TavilySearchClient().search(query, topic="news", max_results=8)

    if tavily_results:
        article_text = _extract_articles(tavily_results)
        if article_text:
            pplx_key = os.getenv("PERPLEXITY_API_KEY", "")
            if pplx_key:
                pplx = PerplexityClient(pplx_key)
                prompt = f"""You are given several recent news articles about {team_name} men's basketball ({conference} conference).
                    Synthesize them into a scouting report with these sections:
                    1. INJURIES - current injuries, day-to-day status, returns. Player names and roles.
                    2. ROSTER CHANGES - transfers, suspensions, eligibility changes this season.
                    3. RECENT FORM - results from last 5-10 games, quality wins, concerning losses.
                    4. TOURNAMENT OUTLOOK - projected seed, bracket region, bubble status.
                    5. ANALYST TAKES - what ESPN/CBS analysts say about their March ceiling.

                    SOURCE ARTICLES:
                    {article_text}

                    Rules:
                    - Only discuss men's basketball. Ignore any football or other sport content.
                    - Use specific player names, dates, and numbers from the articles.
                    - Use bullet points within each section.
                    - If a section has no relevant info in the articles, write "No recent reports."
                    """
                report = pplx.search(prompt)
                if report:
                    return report

        snippets = "\n".join(
            f"- {r.get('title', '')}: {str(r.get('content', ''))[:200]}" for r in tavily_results[:5]
        )
        if snippets:
            return f"## Recent News for {team_name}\n\n{snippets}"

    pplx_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not pplx_key:
        return ""
    pplx = PerplexityClient(pplx_key)
    fallback_prompt = f"""SPORT: NCAA Division I Men's Basketball (NOT football, NOT women's basketball).
        TEAM: {team_name} men's basketball team, {conference} conference.
        SEASON: 2025-26 college basketball season.
        CONTEXT: Preparing for the 2026 NCAA Men's Basketball Tournament (March Madness).

        Search for the latest MEN'S BASKETBALL news about {team_name}. Report on:
        1. INJURIES: Current basketball injuries, day-to-day players, recent returns.
        2. ROSTER: Basketball transfers, suspensions, eligibility issues.
        3. RECENT GAMES: Last 5-10 men's basketball games - wins/losses, scores.
        4. MARCH MADNESS SEED: Projected NCAA Tournament seed and bracket region.
        5. ANALYST TAKES: What basketball analysts say about their NCAA Tournament ceiling.

        IMPORTANT: Only report on MEN'S COLLEGE BASKETBALL. No football.
        Use bullet points. Be specific with player names and dates."""
    return pplx.search(fallback_prompt)


def research_matchup_trends(
    team1_name: str,
    team2_name: str,
    seed1: int,
    seed2: int,
    style1: str,
    style2: str,
) -> str:
    q1 = (
        f"NCAA March Madness basketball #{seed1} seed vs #{seed2} seed "
        f"historical results upsets trends"
    )
    q2 = f"{team1_name} vs {team2_name} men's basketball 2026 NCAA tournament preview matchup"
    tavily = TavilySearchClient()
    tavily_results = tavily.search(q1, topic="general", max_results=6) + tavily.search(q2, topic="news", max_results=4)

    if tavily_results:
        article_text = _extract_articles(tavily_results)
        if article_text:
            pplx_key = os.getenv("PERPLEXITY_API_KEY", "")
            if pplx_key:
                pplx = PerplexityClient(pplx_key)
                prompt = f"""You are given articles about NCAA Men's Basketball Tournament history and a specific matchup preview.
                MATCHUP: ({seed1}) {team1_name} vs ({seed2}) {team2_name}.

                Synthesize into a trends report with these sections:

                1. SEED HISTORY - All-time win rate for #{seed1} vs #{seed2} in March Madness. Name 2-3 notable upsets at this seed line.
                2. STYLE CLASH - {team1_name} style: {style1}. {team2_name} style: {style2}. How these styles match up historically in tournament play.
                3. CONFERENCE PERFORMANCE - How these conferences have performed recently in March Madness.
                4. WHAT DECIDES IT - At this seed line, what factors decide games (defense, FT shooting, experience, etc.)?
                5. UPSET WATCH - If applicable, recent tournament upsets with similar profiles and what caused them.

                SOURCE ARTICLES:
                {article_text}

                Rules:
                - Only discuss NCAA Men's Basketball. No football.
                - Use specific years, scores, team names from the articles.
                - Bullet points within each section."""
                report = pplx.search(prompt)
                if report:
                    return report
        snippets = "\n".join(
            f"- {r.get('title', '')}: {str(r.get('content', ''))[:200]}" for r in tavily_results[:5]
        )
        if snippets:
            return f"## Tournament Trends: ({seed1}) {team1_name} vs ({seed2}) {team2_name}\n\n{snippets}"

    pplx_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not pplx_key:
        return ""
    pplx = PerplexityClient(pplx_key)
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
    return pplx.search(fallback_prompt)


def fetch_team_news(pplx: PerplexityClient, team_name: str, conference: str, slug: str) -> str:
    cached = _read_cache("news", slug, max_age_hours=6)
    if cached and cached.get("content"):
        return str(cached["content"])
    try:
        content = research_team_news(team_name, conference)
    except Exception as exc:
        logger.warning("Smart research failed for %s, fallback to Perplexity direct: %s", slug, exc)
        content = pplx.search(
            f"Latest NCAA men's basketball news injuries roster for {team_name} ({conference}) "
            "2025-26 season March Madness tournament. Only basketball, no football."
        )
    _write_cache("news", slug, {"content": content, "team": team_name})
    return content


def fetch_matchup_trends(
    pplx: PerplexityClient,
    team1_name: str,
    team2_name: str,
    seed1: int,
    seed2: int,
    style1: str,
    style2: str,
    cache_key: str,
) -> str:
    cached = _read_cache("trends", cache_key, max_age_hours=24)
    if cached and cached.get("content"):
        return str(cached["content"])
    try:
        content = research_matchup_trends(team1_name, team2_name, seed1, seed2, style1, style2)
    except Exception as exc:
        logger.warning("Smart research failed for trends %s, fallback to Perplexity: %s", cache_key, exc)
        content = pplx.search(
            f"NCAA March Madness basketball historical trends #{seed1} seed vs #{seed2} seed "
            f"{team1_name} vs {team2_name} upsets. Only basketball, no football."
        )
    _write_cache("trends", cache_key, {"content": content, "team1": team1_name, "team2": team2_name})
    return content
