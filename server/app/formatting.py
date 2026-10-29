"""Форматирование значений для админской страницы (ru-RU, как в Node-версии)."""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

NBSP = "\u00a0"


def format_money(value: object) -> str:
    """1234567 → «1 234 567 ₽» (разряды через неразрывный пробел)."""
    amount = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    sign = "-" if amount < 0 else ""
    digits = f"{abs(amount):,}".replace(",", NBSP)
    return f"{sign}{digits} ₽"


def format_datetime(value: datetime) -> str:
    """29.10.2026, 15:30:00 — как toLocaleString('ru-RU')."""
    return value.astimezone().strftime("%d.%m.%Y, %H:%M:%S")
