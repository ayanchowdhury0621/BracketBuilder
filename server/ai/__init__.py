"""AI package exports."""

from .cache import _cache_path, _read_cache, _write_cache
from .clients import GeminiClient, PerplexityClient, TavilySearchClient
from .matchup import generate_matchup_narrative
from .research import fetch_matchup_trends, fetch_team_news, research_matchup_trends, research_team_news

__all__ = [
    "GeminiClient",
    "PerplexityClient",
    "TavilySearchClient",
    "_cache_path",
    "_read_cache",
    "_write_cache",
    "generate_matchup_narrative",
    "fetch_team_news",
    "fetch_matchup_trends",
    "research_team_news",
    "research_matchup_trends",
]

