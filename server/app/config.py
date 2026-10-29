"""Конфигурация сервиса из переменных окружения (аналог dotenv/config в Node)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class Settings:
    pghost: str
    pgport: int
    pgdatabase: str
    pguser: str
    pgpassword: str
    admin_user: str
    admin_password: str
    port: int


@lru_cache
def get_settings() -> Settings:
    return Settings(
        pghost=os.getenv("PGHOST", "localhost"),
        pgport=_int_env("PGPORT", 5432),
        pgdatabase=os.getenv("PGDATABASE", "calc"),
        pguser=os.getenv("PGUSER", "calc"),
        pgpassword=os.getenv("PGPASSWORD", "calc"),
        admin_user=os.getenv("ADMIN_USER", "admin"),
        admin_password=os.getenv("ADMIN_PASSWORD", "admin"),
        port=_int_env("PORT", 4000),
    )


settings = get_settings()
