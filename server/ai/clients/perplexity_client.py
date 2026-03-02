"""Perplexity API client wrapper."""

from __future__ import annotations

import logging
import time

from server.ai.settings import PERPLEXITY_MODEL

logger = logging.getLogger(__name__)


class PerplexityClient:
    """Rate-limited Perplexity Sonar client via OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, requests_per_second: float = 2.0):
        from openai import OpenAI

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
                return (resp.choices[0].message.content or "").strip()
            except Exception as exc:
                logger.warning("Perplexity error (attempt %d/%d): %s", attempt, max_retries, exc)
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
        return ""

