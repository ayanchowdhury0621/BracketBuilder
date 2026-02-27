"""Database helpers and query adapters for BracketBuilder."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger(__name__)


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def _connect_timeout() -> int:
    return int(os.getenv("PG_CONNECT_TIMEOUT", "10"))


def _env_conn_kwargs() -> dict[str, Any]:
    env_host = os.getenv("DB_HOST")
    env_port = os.getenv("DB_PORT", "5432")
    env_user = os.getenv("DB_USER")
    env_password = os.getenv("DB_PASSWORD")
    env_database = os.getenv("DB_NAME") or os.getenv("DB_DATABASE")
    if not all([env_host, env_user, env_password, env_database]):
        return {}
    return {
        "host": env_host,
        "port": env_port,
        "user": env_user,
        "password": env_password,
        "dbname": env_database,
    }


@contextmanager
def get_conn() -> Iterator[Any]:
    kwargs = _env_conn_kwargs()
    connect_timeout = _connect_timeout()

    # Preferred path requested by user: psycopg2 with explicit host/port credentials.
    if kwargs:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except Exception as exc:
            raise RuntimeError("psycopg2 is not installed; install server requirements") from exc

        conn = psycopg2.connect(
            host=kwargs["host"],
            port=kwargs["port"],
            user=kwargs["user"],
            password=kwargs["password"],
            dbname=kwargs["dbname"],
            connect_timeout=connect_timeout,
        )
        try:
            yield conn
        finally:
            conn.close()
        return

    # Backward-compatible fallback: DATABASE_URL with psycopg3.
    db_url = _database_url()
    if not db_url:
        raise RuntimeError(
            "Database is not configured. Set DB_HOST/DB_USER/DB_PASSWORD/DB_NAME "
            "or DATABASE_URL."
        )
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception as exc:
        raise RuntimeError("psycopg is not installed; install server requirements") from exc

    conn = psycopg.connect(
        db_url,
        row_factory=dict_row,
        connect_timeout=connect_timeout,
        sslmode=os.getenv("PGSSLMODE", "require"),
    )
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_conn() as conn:
        # psycopg2 path
        if conn.__class__.__module__.startswith("psycopg2"):
            from psycopg2.extras import RealDictCursor

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]

        # psycopg3 path
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with get_conn() as conn:
        # psycopg2 path
        if conn.__class__.__module__.startswith("psycopg2"):
            from psycopg2.extras import RealDictCursor

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None

        # psycopg3 path
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None

