"""Пул соединений с PostgreSQL и миграция при старте."""

from __future__ import annotations

from pathlib import Path

from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from .config import settings

MIGRATE_SQL = Path(__file__).with_name("migrate.sql")

_pool: AsyncConnectionPool | None = None


def build_conninfo() -> str:
    return make_conninfo(
        host=settings.pghost,
        port=settings.pgport,
        dbname=settings.pgdatabase,
        user=settings.pguser,
        password=settings.pgpassword,
    )


async def open_pool() -> AsyncConnectionPool:
    global _pool
    _pool = AsyncConnectionPool(
        conninfo=build_conninfo(),
        min_size=1,
        max_size=10,
        open=False,
        kwargs={"row_factory": dict_row},
    )
    await _pool.open(wait=True, timeout=30)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Пул соединений не инициализирован")
    return _pool


async def migrate() -> None:
    """Применяет миграцию при старте (идемпотентно)."""
    async with get_pool().connection() as conn:
        await conn.execute(MIGRATE_SQL.read_text(encoding="utf-8"))
