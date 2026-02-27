"""Gemini API client wrapper."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from server.ai.settings import GEMINI_MODEL

logger = logging.getLogger(__name__)


class GeminiClient:
    """Rate-limited Gemini client with JSON output mode."""

    def __init__(self, api_key: str, requests_per_second: float = 1.0):
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.min_interval = 1.0 / requests_per_second
        self._last_request = 0.0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.time()

    def generate(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> dict[str, Any]:
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
                text = (resp.text or "").strip()
                return json.loads(text) if text else {}
            except json.JSONDecodeError:
                logger.warning("Gemini returned non-JSON (attempt %d/%d), retrying", attempt, max_retries)
                if attempt < max_retries:
                    time.sleep(2)
            except Exception as exc:
                logger.warning("Gemini error (attempt %d/%d): %s", attempt, max_retries, exc)
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
        return {}

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return self.generate(system_prompt, user_prompt)

