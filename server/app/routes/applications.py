"""Публичные эндпоинты заявок."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from ..db import get_pool
from ..loan import calculate_loan
from ..schemas import parse_application

router = APIRouter()

MONEY_FIELDS = ("amount", "monthly_income", "monthly_payment", "total_repaid", "total_interest")


def serialize_application(row: dict[str, Any]) -> dict[str, Any]:
    """Приводит строку БД к JSON: NUMERIC → строка (как отдавал pg в Node), дата → ISO 8601."""
    result = dict(row)
    for field in MONEY_FIELDS:
        value = result.get(field)
        if isinstance(value, Decimal):
            result[field] = f"{value:.2f}"
    created_at = result.get("created_at")
    if isinstance(created_at, datetime):
        result["created_at"] = created_at.isoformat()
    return result


@router.post("/applications", status_code=201)
async def create_application(payload: Any = Body(...)) -> JSONResponse:  # noqa: B008
    application, issues = parse_application(payload)
    if application is None:
        return JSONResponse(
            status_code=400,
            content={"error": "validation_error", "issues": [issue.model_dump() for issue in issues]},
        )

    calc = calculate_loan(application.loan_type, application.amount, application.term_months)

    async with get_pool().connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO applications
              (loan_type, amount, term_months, monthly_income, full_name,
               monthly_payment, total_repaid, total_interest)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                application.loan_type,
                application.amount,
                application.term_months,
                application.monthly_income,
                application.full_name,
                calc.monthly_payment,
                calc.total_repaid,
                calc.total_interest,
            ),
        )
        row = await cursor.fetchone()

    return JSONResponse(status_code=201, content=serialize_application(row or {}))


async def list_applications(status: str | None = None) -> list[dict[str, Any]]:
    if status:
        query = "SELECT * FROM applications WHERE status = %s ORDER BY created_at DESC"
        params: tuple[Any, ...] = (status,)
    else:
        query = "SELECT * FROM applications ORDER BY created_at DESC"
        params = ()

    async with get_pool().connection() as conn:
        cursor = await conn.execute(query, params)
        return list(await cursor.fetchall())
