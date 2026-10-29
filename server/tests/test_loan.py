"""Расчёт аннуитета — значения сверены с JS-версией (server/src/lib/loan.js)."""

from __future__ import annotations

import pytest

from app.loan import LOAN_PRODUCTS, calculate_loan


@pytest.mark.parametrize(
    ("loan_type", "amount", "term_months", "monthly_payment", "total_repaid", "total_interest"),
    [
        ("mortgage", 5_000_000, 120, 90092.60, 10_811_112.00, 5_811_112.00),
        ("mortgage", 6_000_000, 120, 108111.12, 12_973_334.40, 6_973_334.40),
        ("mortgage", 5_000_000, 240, 77165.58, 18_519_739.20, 13_519_739.20),
        ("auto", 5_000_000, 60, 142392.41, 8_543_544.60, 3_543_544.60),
        ("consumer", 50_000, 6, 8881.16, 53_286.96, 3_286.96),
        ("payday", 5_000, 1, 5208.33, 5_208.33, 208.33),
    ],
)
def test_calculate_loan(
    loan_type: str,
    amount: int,
    term_months: int,
    monthly_payment: float,
    total_repaid: float,
    total_interest: float,
) -> None:
    result = calculate_loan(loan_type, amount, term_months)

    assert result.monthly_payment == pytest.approx(monthly_payment, abs=0.01)
    assert result.total_repaid == pytest.approx(total_repaid, abs=0.01)
    assert result.total_interest == pytest.approx(total_interest, abs=0.01)


def test_calculate_loan_unknown_product() -> None:
    with pytest.raises(KeyError):
        calculate_loan("unknown", 100_000, 12)


def test_products_match_frontend_config() -> None:
    assert set(LOAN_PRODUCTS) == {"mortgage", "auto", "consumer", "payday"}
    assert LOAN_PRODUCTS["mortgage"].annual_rate == 0.18
    assert LOAN_PRODUCTS["auto"].annual_rate == 0.235
    assert LOAN_PRODUCTS["consumer"].annual_rate == 0.222
    assert LOAN_PRODUCTS["payday"].annual_rate == 0.5
