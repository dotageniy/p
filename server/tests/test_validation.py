"""Валидация заявки: форматы, сообщения и границы продуктов."""

from __future__ import annotations

import math

import pytest

from app.schemas import ApplicationIn, parse_application


def valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "loanType": "mortgage",
        "amount": 5_000_000,
        "termMonths": 120,
        "fullName": "Иванов Иван Иванович",
        "monthlyIncome": 300_000,
        "hasCitizenship": True,
        "consentGiven": True,
    }
    payload.update(overrides)
    return payload


def test_valid_application() -> None:
    application, issues = parse_application(valid_payload())

    assert issues == []
    assert application is not None
    assert application.loan_type == "mortgage"
    assert application.full_name == "Иванов Иван Иванович"


def test_full_name_is_trimmed_and_stored() -> None:
    application, issues = parse_application(valid_payload(fullName="  Иванов Иван  "))

    assert issues == []
    assert application is not None
    assert application.full_name == "Иванов Иван"


def test_unknown_keys_are_ignored() -> None:
    application, issues = parse_application(valid_payload(extra="ignored"))

    assert issues == []
    assert application is not None


def test_integer_valued_float_is_accepted() -> None:
    application, issues = parse_application(valid_payload(amount=5_000_000.0))

    assert issues == []
    assert application is not None
    assert application.amount == 5_000_000
    assert isinstance(application.amount, int)


@pytest.mark.parametrize(
    ("overrides", "path", "message"),
    [
        ({"loanType": "unknown"}, "loanType", None),
        ({"amount": "5000000"}, "amount", "Сумма должна быть числом"),
        ({"amount": 5_000_000.5}, "amount", "Сумма должна быть целым числом"),
        ({"amount": math.inf}, "amount", "Сумма обязательна"),
        ({"termMonths": 0}, "termMonths", "Срок должен быть положительным"),
        ({"termMonths": 12.5}, "termMonths", "Срок должен быть целым числом месяцев"),
        ({"fullName": "И"}, "fullName", "Укажите ФИО (минимум 2 символа)"),
        ({"fullName": "Иванов 123"}, "fullName", "ФИО может содержать только буквы, пробелы и дефисы"),
        ({"monthlyIncome": 0}, "monthlyIncome", "Доход должен быть положительным"),
        ({"monthlyIncome": "300000"}, "monthlyIncome", "Доход должен быть числом"),
        ({"hasCitizenship": False}, "hasCitizenship", "Требуется гражданство РФ"),
        ({"consentGiven": False}, "consentGiven", "Требуется согласие на обработку персональных данных"),
    ],
)
def test_invalid_fields(overrides: dict[str, object], path: str, message: str | None) -> None:
    application, issues = parse_application(valid_payload(**overrides))

    assert application is None
    assert [issue.path for issue in issues] == [path]
    if message is not None:
        assert issues[0].message == message


def test_missing_field_reports_russian_message() -> None:
    payload = valid_payload()
    payload.pop("fullName")

    _, issues = parse_application(payload)

    assert issues[0].path == "fullName"
    assert issues[0].message == "Обязательное поле"


@pytest.mark.parametrize(
    ("loan_type", "amount", "term_months", "expected_paths"),
    [
        ("mortgage", 100_000, 120, ["amount"]),
        ("mortgage", 5_000_000, 400, ["termMonths"]),
        ("auto", 500_000, 6, ["termMonths"]),
        ("payday", 200_000, 13, ["amount", "termMonths"]),
    ],
)
def test_product_limits(
    loan_type: str,
    amount: int,
    term_months: int,
    expected_paths: list[str],
) -> None:
    application, issues = parse_application(valid_payload(loanType=loan_type, amount=amount, termMonths=term_months))

    assert application is None
    assert [issue.path for issue in issues] == expected_paths


def test_product_limit_message() -> None:
    _, issues = parse_application(valid_payload(amount=100_000))

    assert issues[0].message == "Сумма для «Ипотека»: от 300000 до 30000000 ₽"


def test_payload_must_be_object() -> None:
    application, issues = parse_application([valid_payload()])

    assert application is None
    assert issues[0].message == "Ожидается JSON-объект"


def test_snake_case_keys_also_accepted() -> None:
    application, issues = parse_application(
        {
            "loan_type": "auto",
            "amount": 500_000,
            "term_months": 60,
            "full_name": "Петров Пётр",
            "monthly_income": 120_000,
            "has_citizenship": True,
            "consent_given": True,
        }
    )

    assert issues == []
    assert isinstance(application, ApplicationIn)
