"""Запуск сервиса: python -m app (порт берётся из PORT, по умолчанию 4000)."""

from __future__ import annotations

import uvicorn

from .config import settings


def main() -> None:
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
