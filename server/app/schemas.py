"""Схема и валидация заявки — контракт повторяет zod-схему фронтенда.

Источник: src/entities/applicant/model/schema.ts и server/src/lib/validate.js.
Ответ с ошибками имеет ту же форму: {"error": "validation_error", "issues": [...]}.
"""

from __future__ import annotations

import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, ValidationInfo, field_validator
from pydantic.alias_generators import to_camel

from .loan import LOAN_PRODUCTS

FULL_NAME_RE = re.compile(r"^[А-Яа-яЁёA-Za-z\s'-]{2,120}$")

LoanType = Literal["mortgage", "auto", "consumer", "payday"]


class ValidationIssue(BaseModel):
    path: str
    message: str


class ApplicationIn(BaseModel):
    """Заявка на кредит, прошедшая серверную валидацию."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )

    loan_type: LoanType
    amount: int
    term_months: int
    full_name: str
    monthly_income: float
    has_citizenship: bool
    consent_given: bool

    @field_validator("amount", "term_months", mode="before")
    @classmethod
    def _integer(cls, value: Any, info: ValidationInfo) -> int:
        is_amount = info.field_name == "amount"
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("Сумма должна быть числом" if is_amount else "Срок должен быть числом")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Сумма обязательна" if is_amount else "Срок обязателен")
        if isinstance(value, float) and not value.is_integer():
            raise ValueError("Сумма должна быть целым числом" if is_amount else "Срок должен быть целым числом месяцев")
        return int(value)

    @field_validator("term_months")
    @classmethod
    def _positive_term(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Срок должен быть положительным")
        return value

    @field_validator("monthly_income", mode="before")
    @classmethod
    def _income_type(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("Доход должен быть числом")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Доход обязателен")
        return value

    @field_validator("monthly_income")
    @classmethod
    def _income_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Доход должен быть положительным")
        return value

    @field_validator("full_name")
    @classmethod
    def _full_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Укажите ФИО (минимум 2 символа)")
        if len(value) > 120:
            raise ValueError("ФИО слишком длинное")
        if not FULL_NAME_RE.match(value):
            raise ValueError("ФИО может содержать только буквы, пробелы и дефисы")
        return value

    @field_validator("has_citizenship")
    @classmethod
    def _citizenship(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Требуется гражданство РФ")
        return value

    @field_validator("consent_given")
    @classmethod
    def _consent(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Требуется согласие на обработку персональных данных")
        return value


def _issue_path(location: tuple[Any, ...]) -> str:
    """Путь ошибки в camelCase, как в ответе Node-версии."""
    return ".".join(to_camel(str(part)) if isinstance(part, str) else str(part) for part in location)


def _issue_message(error: dict[str, Any]) -> str:
    if error["type"] == "missing":
        return "Обязательное поле"
    return str(error["msg"]).removeprefix("Value error, ")


def _product_issues(application: ApplicationIn) -> list[ValidationIssue]:
    product = LOAN_PRODUCTS[application.loan_type]
    issues: list[ValidationIssue] = []

    if not product.min_amount <= application.amount <= product.max_amount:
        issues.append(
            ValidationIssue(
                path="amount",
                message=f"Сумма для «{product.title}»: от {product.min_amount} до {product.max_amount} ₽",
            )
        )
    if not product.min_term_months <= application.term_months <= product.max_term_months:
        issues.append(
            ValidationIssue(
                path="termMonths",
                message=f"Срок для «{product.title}»: от {product.min_term_months} до {product.max_term_months} мес",
            )
        )
    return issues


def parse_application(payload: Any) -> tuple[ApplicationIn | None, list[ValidationIssue]]:
    """Валидирует тело запроса и возвращает заявку либо список ошибок."""
    if not isinstance(payload, dict):
        return None, [ValidationIssue(path="", message="Ожидается JSON-объект")]

    try:
        application = ApplicationIn.model_validate(payload)
    except ValidationError as exc:
        return None, [
            ValidationIssue(path=_issue_path(error["loc"]), message=_issue_message(error)) for error in exc.errors()
        ]

    issues = _product_issues(application)
    if issues:
        return None, issues
    return application, []
