"""Админка: Basic-авторизация, список заявок и смена статуса."""

from __future__ import annotations

import base64
import hmac
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..db import get_pool
from ..formatting import format_datetime, format_money
from ..loan import LOAN_PRODUCTS
from .applications import list_applications

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

STATUSES = ("new", "in_review", "approved", "rejected")
STATUS_LABELS = {
    "new": "Новая",
    "in_review": "На рассмотрении",
    "approved": "Одобрена",
    "rejected": "Отклонена",
}


class AdminAuthRequired(Exception):
    """Нет корректного Basic-заголовка — отвечаем 401 и просим логин/пароль."""


def expected_authorization() -> str:
    credentials = f"{settings.admin_user}:{settings.admin_password}".encode()
    return "Basic " + base64.b64encode(credentials).decode("ascii")


def require_admin(request: Request) -> None:
    header = request.headers.get("authorization", "")
    expected = expected_authorization()
    # Сравнение за постоянное время, чтобы не подсказывать префикс пароля.
    if len(header) != len(expected) or not hmac.compare_digest(header, expected):
        raise AdminAuthRequired


templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters["money"] = format_money
templates.env.filters["datetime"] = format_datetime
templates.env.globals["statuses"] = STATUSES
templates.env.globals["status_labels"] = STATUS_LABELS
templates.env.globals["product_titles"] = {key: product.title for key, product in LOAN_PRODUCTS.items()}

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_page(request: Request, status: str | None = None) -> HTMLResponse:
    current_status = status if status in STATUSES else None
    rows = await list_applications(current_status)
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"rows": rows, "current_status": current_status},
    )


@router.post("/{application_id}/status", response_model=None, include_in_schema=False)
async def change_status(
    application_id: str,
    status: Annotated[str | None, Form()] = None,
) -> PlainTextResponse | RedirectResponse:
    try:
        parsed_id: int | None = int(application_id)
    except (TypeError, ValueError):
        parsed_id = None

    if parsed_id is None or status not in STATUSES:
        return PlainTextResponse("Некорректные данные", status_code=400)

    async with get_pool().connection() as conn:
        await conn.execute("UPDATE applications SET status = %s WHERE id = %s", (status, parsed_id))

    return RedirectResponse("/admin", status_code=303)
