"""Маршруты заявок и админки с подменённым пулом соединений (без PostgreSQL)."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import admin, applications


class FakeCursor:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row

    async def fetchone(self) -> dict[str, Any] | None:
        return self._row

    async def fetchall(self) -> list[dict[str, Any]]:
        return [self._row] if self._row else []


class FakeConnection:
    def __init__(self, pool: FakePool) -> None:
        self._pool = pool

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> FakeCursor:
        self._pool.queries.append((query, params))
        if "INSERT" in query:
            return FakeCursor(self._pool.insert_row)
        if "SELECT" in query:
            return FakeCursor(self._pool.select_row)
        return FakeCursor(None)

    async def __aenter__(self) -> FakeConnection:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


class FakePool:
    def __init__(
        self,
        insert_row: dict[str, Any] | None = None,
        select_row: dict[str, Any] | None = None,
    ) -> None:
        self.insert_row = insert_row
        self.select_row = select_row
        self.queries: list[tuple[str, tuple[Any, ...] | None]] = []

    def connection(self) -> FakeConnection:
        return FakeConnection(self)


def stored_row() -> dict[str, Any]:
    return {
        "id": 7,
        "loan_type": "mortgage",
        "amount": Decimal("5000000.00"),
        "term_months": 120,
        "monthly_income": Decimal("300000.00"),
        "full_name": "Иванов Иван Иванович",
        "monthly_payment": Decimal("90092.60"),
        "total_repaid": Decimal("10811112.00"),
        "total_interest": Decimal("5811112.00"),
        "status": "new",
        "created_at": datetime(2026, 10, 29, 12, 0, 0, tzinfo=UTC),
    }


def valid_payload() -> dict[str, Any]:
    return {
        "loanType": "mortgage",
        "amount": 5_000_000,
        "termMonths": 120,
        "fullName": "Иванов Иван Иванович",
        "monthlyIncome": 300_000,
        "hasCitizenship": True,
        "consentGiven": True,
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, FakePool]:
    pool = FakePool(insert_row=stored_row(), select_row=stored_row())
    monkeypatch.setattr(applications, "get_pool", lambda: pool)
    monkeypatch.setattr(admin, "get_pool", lambda: pool)
    return TestClient(app), pool


def test_health() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_create_application(client: tuple[TestClient, FakePool]) -> None:
    http, pool = client

    response = http.post("/api/applications", json=valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 7
    assert body["monthly_payment"] == "90092.60"
    assert body["total_repaid"] == "10811112.00"
    assert body["created_at"] == "2026-10-29T12:00:00+00:00"

    query, params = pool.queries[0]
    assert query.count("%s") == 8
    assert params is not None
    assert params[0] == "mortgage"
    assert params[4] == "Иванов Иван Иванович"
    assert params[5] == pytest.approx(90092.60)
    assert params[7] == pytest.approx(5811112.00)


def test_create_application_validation_error(client: tuple[TestClient, FakePool]) -> None:
    http, pool = client

    response = http.post("/api/applications", json={**valid_payload(), "amount": 100})

    assert response.status_code == 400
    assert response.json() == {
        "error": "validation_error",
        "issues": [{"path": "amount", "message": "Сумма для «Ипотека»: от 300000 до 30000000 ₽"}],
    }
    assert pool.queries == []


def test_create_application_malformed_json(client: tuple[TestClient, FakePool]) -> None:
    http, pool = client

    response = http.post(
        "/api/applications",
        content=b'{"loanType": ',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "validation_error",
        "issues": [{"path": "", "message": "Некорректный JSON"}],
    }
    assert pool.queries == []


def test_admin_requires_basic_auth(client: tuple[TestClient, FakePool]) -> None:
    http, _ = client

    response = http.get("/admin")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Basic realm="admin"'
    assert response.text == "Требуется авторизация"


def test_admin_page_renders_applications(client: tuple[TestClient, FakePool]) -> None:
    http, pool = client
    credentials = base64.b64encode(b"admin:admin").decode()

    response = http.get("/admin", headers={"Authorization": f"Basic {credentials}"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Заявки на кредиты (1)" in response.text
    assert "Иванов Иван Иванович" in response.text
    assert "90\u00a0093 ₽" in response.text
    assert 'value="new" selected' in response.text
    assert pool.queries[0][1] == ()


def test_admin_page_status_filter(client: tuple[TestClient, FakePool]) -> None:
    http, pool = client
    credentials = base64.b64encode(b"admin:admin").decode()

    response = http.get("/admin?status=approved", headers={"Authorization": f"Basic {credentials}"})

    assert response.status_code == 200
    assert pool.queries[0][1] == ("approved",)
    assert 'style="font-weight:bold"' in response.text


def test_admin_page_ignores_unknown_status(client: tuple[TestClient, FakePool]) -> None:
    http, pool = client
    credentials = base64.b64encode(b"admin:admin").decode()

    response = http.get("/admin?status=hacked", headers={"Authorization": f"Basic {credentials}"})

    assert response.status_code == 200
    assert pool.queries[0][1] == ()


def test_change_status(client: tuple[TestClient, FakePool]) -> None:
    http, pool = client
    credentials = base64.b64encode(b"admin:admin").decode()

    response = http.post(
        "/admin/7/status",
        data={"status": "approved"},
        headers={"Authorization": f"Basic {credentials}"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    query, params = pool.queries[0]
    assert "UPDATE applications" in query
    assert params == ("approved", 7)


@pytest.mark.parametrize("application_id", ["abc", "1.5"])
def test_change_status_bad_id(client: tuple[TestClient, FakePool], application_id: str) -> None:
    http, pool = client
    credentials = base64.b64encode(b"admin:admin").decode()

    response = http.post(
        f"/admin/{application_id}/status",
        data={"status": "approved"},
        headers={"Authorization": f"Basic {credentials}"},
    )

    assert response.status_code == 400
    assert response.text == "Некорректные данные"
    assert pool.queries == []


def test_change_status_bad_status(client: tuple[TestClient, FakePool]) -> None:
    http, pool = client
    credentials = base64.b64encode(b"admin:admin").decode()

    response = http.post(
        "/admin/7/status",
        data={"status": "deleted"},
        headers={"Authorization": f"Basic {credentials}"},
    )

    assert response.status_code == 400
    assert pool.queries == []
