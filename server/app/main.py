"""Точка сборки FastAPI-приложения (аналог server/src/index.js)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse

from .db import close_pool, migrate, open_pool
from .routes import admin, applications
from .routes.admin import AdminAuthRequired

logger = logging.getLogger("calc.api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await open_pool()
    await migrate()
    yield
    await close_pool()


app = FastAPI(title="BIS-225 Calc API", version="1.0.0", lifespan=lifespan)

app.include_router(applications.router, prefix="/api")
app.include_router(admin.router, prefix="/admin")


@app.get("/api/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.exception_handler(AdminAuthRequired)
async def admin_auth_handler(_: Request, __: AdminAuthRequired) -> PlainTextResponse:
    return PlainTextResponse(
        "Требуется авторизация",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="admin"'},
    )


def _body_issue(error: dict[str, Any]) -> dict[str, str]:
    if error["type"] == "json_invalid":
        return {"path": "", "message": "Некорректный JSON"}
    path = ".".join(str(part) for part in error["loc"] if part != "body")
    return {"path": path, "message": "Некорректное значение"}


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Битое тело запроса — 400 в том же формате, что и ошибки схемы."""
    return JSONResponse(
        status_code=400,
        content={"error": "validation_error", "issues": [_body_issue(error) for error in exc.errors()]},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Необработанная ошибка при %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse({"error": "internal_error"}, status_code=500)
