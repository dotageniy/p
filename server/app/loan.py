"""Продукты и аннуитетная формула — копия конфигурации фронтенда.

Источник: src/shared/config/loanProducts.ts, src/entities/loan/model/credit.ts.
Сервер считает независимо — клиентским числам не доверяем.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True, slots=True)
class LoanProduct:
    id: str
    title: str
    # Годовая ставка в долях единицы (0.18 = 18%).
    annual_rate: float
    min_amount: int
    max_amount: int
    min_term_months: int
    max_term_months: int


LOAN_PRODUCTS: dict[str, LoanProduct] = {
    "mortgage": LoanProduct("mortgage", "Ипотека", 0.18, 300_000, 30_000_000, 12, 360),
    "auto": LoanProduct("auto", "Автокредит", 0.235, 100_000, 5_000_000, 12, 84),
    "consumer": LoanProduct("consumer", "Потребительский", 0.222, 50_000, 5_000_000, 6, 84),
    "payday": LoanProduct("payday", "Деньги до зарплаты", 0.5, 5_000, 100_000, 1, 12),
}


@dataclass(frozen=True, slots=True)
class LoanCalculation:
    monthly_payment: float
    total_repaid: float
    total_interest: float


def round2(value: float) -> float:
    """Округление до копеек вверх на половине (как Math.round в JS)."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_loan(loan_type: str, amount: int | float, term_months: int) -> LoanCalculation:
    """Аннуитетный платёж: P = S*i*(1+i)^n / ((1+i)^n - 1), i = годовая ставка / 12."""
    product = LOAN_PRODUCTS[loan_type]
    monthly_rate = product.annual_rate / 12
    factor = (1 + monthly_rate) ** term_months
    monthly_payment = round2((amount * monthly_rate * factor) / (factor - 1))
    total_repaid = round2(monthly_payment * term_months)
    return LoanCalculation(
        monthly_payment=monthly_payment,
        total_repaid=total_repaid,
        total_interest=round2(total_repaid - amount),
    )
