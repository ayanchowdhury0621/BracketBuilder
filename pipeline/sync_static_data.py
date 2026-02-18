"""
Upload static JSON data files to S3 and configure CORS on the bucket.

This makes the data fetchable directly from the browser, eliminating
the need for the backend to serve static data.

Usage:
    python -m pipeline.sync_static_data
    python -m pipeline.sync_static_data --cors-only   # just set CORS policy
"""

import json
import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
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

DATA_FILES = [
    "teams.json",
    "bracket.json",
    "players_full.json",
    "espn_manifest.json",
    "conferences.json",
    "power_rankings.json",
    "summary.json",
]


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
    )


def set_bucket_cors(s3):
    """Enable CORS on the S3 bucket so browsers can fetch data directly."""
    cors_config = {
        "CORSRules": [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET", "HEAD"],
                "AllowedOrigins": [
                    "http://localhost:5173",
                    "http://localhost:3000",
                    "http://127.0.0.1:5173",
                    "https://*.vercel.app",
                    "https://bracketbuilder.vercel.app",
                ],
                "ExposeHeaders": ["Content-Length", "Content-Type", "ETag"],
                "MaxAgeSeconds": 86400,
            }
        ]
    }
    try:
        s3.put_bucket_cors(Bucket=S3_BUCKET, CORSConfiguration=cors_config)
        logger.info("CORS policy set on bucket %s", S3_BUCKET)
    except ClientError as e:
        logger.error("Failed to set CORS: %s", e)
        raise


def upload_data_files(s3):
    """Upload static JSON data files to s3://bucket/data/."""
    uploaded = 0
    for filename in DATA_FILES:
        path = EXPORT_DIR / filename
        if not path.exists():
            logger.warning("Skipping %s — not found", filename)
            continue

        s3_key = f"data/{filename}"
        size_kb = path.stat().st_size / 1024

        s3.upload_file(
            str(path),
            S3_BUCKET,
            s3_key,
            ExtraArgs={
                "ContentType": "application/json",
                "ACL": "public-read",
                "CacheControl": "public, max-age=300",
            },
        )
        uploaded += 1
        logger.info("  Uploaded %s (%.1f KB) → s3://%s/%s", filename, size_kb, S3_BUCKET, s3_key)

    logger.info("Uploaded %d/%d data files", uploaded, len(DATA_FILES))
    return uploaded


def run(cors_only: bool = False):
    if not S3_ACCESS_KEY or not S3_SECRET_KEY or not S3_ENDPOINT:
        logger.error("S3 credentials not set in .env")
        return

    s3 = _get_s3_client()

    logger.info("Setting CORS policy on %s...", S3_BUCKET)
    set_bucket_cors(s3)

    if not cors_only:
        logger.info("Uploading static data files to S3...")
        upload_data_files(s3)

    base_url = f"{S3_ENDPOINT}/{S3_BUCKET}/data"
    logger.info("Done. Data accessible at: %s/teams.json (etc.)", base_url)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Upload static data to S3")
    parser.add_argument("--cors-only", action="store_true", help="Only set CORS, don't upload files")
    args = parser.parse_args()
    run(cors_only=args.cors_only)
