"""Shared AI settings and constants."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "gemini_cache"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar")

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
