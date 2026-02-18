"""
Download ESPN logos + headshots, convert to WebP, upload to Linode S3.

Writes a manifest at data/export/espn_manifest.json so the server
can serve S3 URLs without hitting ESPN CDN at runtime.

Usage:
    python -m pipeline.sync_espn_assets               # full sync
    python -m pipeline.sync_espn_assets --logos-only   # skip headshots
"""

import io
import json
import logging
import os
import time
from pathlib import Path

import boto3
import httpx
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = PROJECT_ROOT / "data" / "export"

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "rotobot-data")
S3_REGION = os.getenv("S3_REGION", "us-ord")

ESPN_TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams"
ESPN_ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{espn_id}/roster"

MANIFEST_PATH = EXPORT_DIR / "espn_manifest.json"

HTTP_TIMEOUT = 15


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
    )


def _normalize(name: str) -> str:
    return (name.lower()
            .replace(".", "")
            .replace("(", "").replace(")", "")
            .replace("st ", "state ")
            .replace("'", "")
            .strip())


def _download_image(url: str, client: httpx.Client) -> bytes | None:
    try:
        resp = client.get(url, timeout=HTTP_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.debug("Download failed %s: %s", url, e)
        return None


def _convert_to_webp(raw_bytes: bytes, max_size: int = 256) -> bytes | None:
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img = img.convert("RGBA")
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=85)
        return buf.getvalue()
    except Exception as e:
        logger.debug("WebP conversion failed: %s", e)
        return None


def _upload_to_s3(s3, key: str, data: bytes, content_type: str = "image/webp") -> str:
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
        ACL="public-read",
    )
    return f"{S3_ENDPOINT}/{S3_BUCKET}/{key}"


def _fetch_espn_teams(http: httpx.Client) -> list[dict]:
    resp = http.get(ESPN_TEAMS_URL, params={"limit": 500}, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    raw = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
    teams = []
    for t in raw:
        ti = t.get("team", {})
        teams.append({
            "espnId": ti.get("id", ""),
            "displayName": ti.get("displayName", ""),
            "short": ti.get("shortDisplayName", ""),
            "abbr": ti.get("abbreviation", ""),
            "logo": (ti.get("logos") or [{}])[0].get("href", ""),
        })
    return teams


def _build_espn_lookup(espn_teams: list[dict]) -> dict[str, dict]:
    lookup = {}
    for t in espn_teams:
        for key in [_normalize(t["short"]), _normalize(t["displayName"]), _normalize(t["abbr"])]:
            if key:
                lookup[key] = t
    return lookup


def _resolve(our_name: str, lookup: dict[str, dict]) -> dict | None:
    norm = _normalize(our_name)
    if norm in lookup:
        return lookup[norm]
    for key, val in lookup.items():
        if norm in key or key in norm:
            return val
    return None


def sync_logos(s3, http: httpx.Client, espn_teams: list[dict], our_teams: dict) -> dict[str, str]:
    """Download every ESPN logo, convert to WebP, upload to S3. Returns {our_slug: s3_url}."""
    lookup = _build_espn_lookup(espn_teams)
    logos: dict[str, str] = {}
    total = len(our_teams)

    for i, (slug, team) in enumerate(our_teams.items()):
        name = team.get("shortName", team.get("name", slug))
        espn = _resolve(name, lookup)
        if not espn or not espn["logo"]:
            logger.debug("No ESPN match for %s", slug)
            continue

        raw = _download_image(espn["logo"], http)
        if not raw:
            continue

        webp = _convert_to_webp(raw, max_size=256)
        if not webp:
            continue

        s3_key = f"logos/{slug}.webp"
        url = _upload_to_s3(s3, s3_key, webp)
        logos[slug] = url

        if (i + 1) % 50 == 0 or (i + 1) == total:
            logger.info("  Logos: %d/%d uploaded", i + 1, total)

    logger.info("Uploaded %d logos to S3", len(logos))
    return logos


def sync_headshots(s3, http: httpx.Client, espn_teams: list[dict], our_teams: dict, bracket_slugs: set[str]) -> dict[str, dict[str, str]]:
    """Download headshots for bracket teams. Returns {our_slug: {player_name_lower: s3_url}}."""
    lookup = _build_espn_lookup(espn_teams)
    headshots: dict[str, dict[str, str]] = {}
    total = len(bracket_slugs)

    for i, slug in enumerate(sorted(bracket_slugs)):
        team = our_teams.get(slug)
        if not team:
            continue
        name = team.get("shortName", team.get("name", slug))
        espn = _resolve(name, lookup)
        if not espn:
            continue

        espn_id = espn["espnId"]
        try:
            resp = http.get(ESPN_ROSTER_URL.format(espn_id=espn_id), timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            athletes = resp.json().get("athletes", [])
        except Exception as e:
            logger.debug("Roster fetch failed for %s: %s", slug, e)
            continue

        team_headshots: dict[str, str] = {}
        for a in athletes:
            hs_url = a.get("headshot", {}).get("href", "")
            player_name = a.get("displayName", "")
            a_id = a.get("id", "")
            if not hs_url or not a_id:
                continue

            raw = _download_image(hs_url, http)
            if not raw:
                continue
            webp = _convert_to_webp(raw, max_size=200)
            if not webp:
                continue

            s3_key = f"headshots/{slug}/{a_id}.webp"
            url = _upload_to_s3(s3, s3_key, webp)
            team_headshots[player_name.lower()] = url

        if team_headshots:
            headshots[slug] = team_headshots

        if (i + 1) % 10 == 0 or (i + 1) == total:
            logger.info("  Headshots: %d/%d teams processed", i + 1, total)

        time.sleep(0.3)

    total_hs = sum(len(v) for v in headshots.values())
    logger.info("Uploaded %d headshots across %d teams", total_hs, len(headshots))
    return headshots


def run_sync(logos_only: bool = False):
    if not S3_ACCESS_KEY or not S3_SECRET_KEY or not S3_ENDPOINT:
        logger.error("S3 credentials not set in .env")
        return

    with open(EXPORT_DIR / "teams.json") as f:
        our_teams = json.load(f)

    bracket_slugs: set[str] = set()
    with open(EXPORT_DIR / "bracket.json") as f:
        bracket = json.load(f)
    for m in bracket.get("matchups", []):
        bracket_slugs.add(m.get("team1Slug", ""))
        bracket_slugs.add(m.get("team2Slug", ""))
    bracket_slugs.discard("")

    s3 = _get_s3_client()
    http = httpx.Client()

    logger.info("Fetching ESPN team directory...")
    espn_teams = _fetch_espn_teams(http)
    logger.info("Found %d ESPN teams", len(espn_teams))

    logger.info("Syncing logos...")
    logos = sync_logos(s3, http, espn_teams, our_teams)

    headshots: dict[str, dict[str, str]] = {}
    if not logos_only:
        logger.info("Syncing headshots for %d bracket teams...", len(bracket_slugs))
        headshots = sync_headshots(s3, http, espn_teams, our_teams, bracket_slugs)

    http.close()

    manifest = {"logos": logos, "headshots": headshots}
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info("Manifest written to %s (%d logos, %d headshot teams)",
                MANIFEST_PATH, len(logos), len(headshots))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync ESPN assets to S3")
    parser.add_argument("--logos-only", action="store_true", help="Skip headshot sync")
    args = parser.parse_args()
    run_sync(logos_only=args.logos_only)
