"""Tavily search client wrapper."""

from __future__ import annotations

import logging
import os
from typing import Any

from server.ai.settings import BASKETBALL_DOMAINS

logger = logging.getLogger(__name__)


class TavilySearchClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")

    def search(self, query: str, topic: str = "news", max_results: int = 8) -> list[dict[str, Any]]:
        if not self.api_key:
            return []
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=self.api_key)
            results = client.search(
                query=query,
                topic=topic,
                search_depth="advanced",
                max_results=max_results,
                include_domains=BASKETBALL_DOMAINS,
                include_raw_content=True,
                include_answer=True,
            )
            return results.get("results", [])
        except Exception as exc:
            logger.warning("Tavily search failed: %s", exc)
            return []

