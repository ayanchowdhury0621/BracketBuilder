"""Rate-limited client for the NCAA API (https://github.com/henrygd/ncaa-api)."""

import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://ncaa-api.henrygd.me"


class NcaaApiClient:
    """HTTP client with rate limiting, retry logic, and pagination for the NCAA API."""

    def __init__(self, requests_per_second: float = 4.0, max_retries: int = 3):
        self.min_interval = 1.0 / requests_per_second
        self.max_retries = max_retries
        self._last_request_time = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "BracketBuilder/1.0"})
        self.request_count = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_time = time.time()

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{BASE_URL}{path}"
        for attempt in range(1, self.max_retries + 1):
            self._rate_limit()
            try:
                resp = self.session.get(url, params=params, timeout=20)
                self.request_count += 1

                if resp.status_code == 429:
                    wait = min(2 ** attempt, 10)
                    logger.warning("Rate limited on %s, waiting %ds (attempt %d)", url, wait, attempt)
                    time.sleep(wait)
                    continue

                if resp.status_code == 404:
                    logger.debug("404 on %s", url)
                    return {}

                resp.raise_for_status()
                return resp.json()

            except requests.exceptions.Timeout:
                logger.warning("Timeout on %s (attempt %d/%d)", url, attempt, self.max_retries)
                if attempt == self.max_retries:
                    raise
            except requests.exceptions.HTTPError:
                if resp.status_code >= 500 and attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise
        return {}

    def get_all_pages(self, path: str) -> tuple[list[dict], dict]:
        """Fetch all pages of a paginated endpoint. Returns (all_data, first_page_metadata)."""
        first = self._get(path, params={"page": 1})
        if not first:
            return [], {}
        total_pages = first.get("pages", 1)
        all_data = list(first.get("data", []))

        for page in range(2, total_pages + 1):
            resp = self._get(path, params={"page": page})
            all_data.extend(resp.get("data", []))

        return all_data, first

    def get_team_stat(self, stat_id: int, season: str = "current") -> tuple[list[dict], dict]:
        return self.get_all_pages(f"/stats/basketball-men/d1/{season}/team/{stat_id}")

    def get_individual_stat(self, stat_id: int, season: str = "current") -> tuple[list[dict], dict]:
        return self.get_all_pages(f"/stats/basketball-men/d1/{season}/individual/{stat_id}")

    def get_net_rankings(self) -> tuple[list[dict], dict]:
        return self.get_all_pages("/rankings/basketball-men/d1/ncaa-mens-basketball-net-rankings")

    def get_ap_rankings(self) -> tuple[list[dict], dict]:
        return self.get_all_pages("/rankings/basketball-men/d1/associated-press")

    def get_standings(self) -> tuple[list[dict], dict]:
        resp = self._get("/standings/basketball-men/d1")
        return resp.get("data", []), resp

    def get_scoreboard(self, date_str: Optional[str] = None) -> tuple[list[dict], dict]:
        """Fetch scoreboard. date_str: 'YYYY/MM/DD' for a specific date, None for today."""
        if date_str:
            path = f"/scoreboard/basketball-men/d1/{date_str}/all-conf"
        else:
            path = "/scoreboard/basketball-men/d1"

        resp = self._get(path)
        if not resp:
            if date_str:
                resp = self._get(f"/scoreboard/basketball-men/d1/{date_str}")
            if not resp:
                return [], {}
        return resp.get("games", []), resp

    def get_game(self, game_id: str) -> dict:
        return self._get(f"/game/{game_id}")

    def get_schedule(self, year: int, month: int) -> list[dict]:
        resp = self._get(f"/schedule/basketball-men/d1/{year}/{month:02d}")
        return resp.get("gameDates", [])

    def get_schools_index(self) -> list[dict]:
        resp = self._get("/schools-index")
        return resp if isinstance(resp, list) else []
