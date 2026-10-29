"""Форматирование админских значений под ru-RU."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

from app.formatting import format_datetime, format_money

NBSP = "\u00a0"


def test_money_groups_thousands() -> None:
    assert format_money(5_000_000) == f"5{NBSP}000{NBSP}000 ₽"
    assert format_money(90092.60) == f"90{NBSP}093 ₽"
    assert format_money(Decimal("1234.50")) == f"1{NBSP}235 ₽"


def test_money_small_and_negative() -> None:
    assert format_money(0) == "0 ₽"
    assert format_money(-1500) == f"-1{NBSP}500 ₽"


def test_datetime_uses_local_time() -> None:
    moment = datetime(2026, 10, 29, 12, 5, 9, tzinfo=UTC)

    expected = moment.astimezone().strftime("%d.%m.%Y, %H:%M:%S")
    assert format_datetime(moment) == expected
    assert format_datetime(moment).count(":") == 2


def test_datetime_converts_offset_to_local_time() -> None:
    moment = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone(timedelta(hours=3)))

    assert format_datetime(moment) == moment.astimezone().strftime("%d.%m.%Y, %H:%M:%S")
