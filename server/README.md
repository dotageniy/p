# API кредитного калькулятора (Python / FastAPI)

Бэкенд переписан с Node.js (Express + pg + zod) на Python 3.12 без изменения
HTTP-контракта: те же маршруты, коды ответов и формат ошибок, поэтому фронтенд
(`src/`) не менялся.

## Стек

| Было (Node)        | Стало (Python)                          |
| ------------------ | --------------------------------------- |
| Express 4          | FastAPI + Uvicorn                       |
| pg (node-postgres) | psycopg 3 + psycopg-pool (async)        |
| zod                | Pydantic v2                             |
| HTML-строки в JS   | Jinja2 (`app/templates/admin.html`)     |
| `node:crypto`      | `hmac.compare_digest`                   |

## Структура

```
app/
  main.py                 # создание приложения, health, обработчики ошибок
  __main__.py             # запуск: python -m app
  config.py               # настройки из переменных окружения
  db.py                   # пул соединений + миграция при старте
  migrate.sql             # схема БД (идемпотентная)
  loan.py                 # продукты и аннуитетная формула
  schemas.py              # валидация заявки (контракт zod-схемы)
  formatting.py           # форматирование сумм/дат для админки (ru-RU)
  routes/applications.py  # POST /api/applications
  routes/admin.py         # GET /admin, POST /admin/{id}/status
  templates/admin.html    # страница админки
tests/                    # pytest: расчёт, валидация, форматирование
```

## Эндпоинты

- `GET /api/health` → `{"ok": true}`
- `POST /api/applications` → `201` и сохранённая заявка; при ошибке валидации —
  `400 {"error": "validation_error", "issues": [{"path", "message"}]}`
- `GET /admin` (Basic-авторизация) — таблица заявок с фильтром `?status=`
- `POST /admin/{id}/status` (form-data, поле `status`) → редирект на `/admin`

Статусы: `new`, `in_review`, `approved`, `rejected`.

## Переменные окружения

Как и раньше (см. `.env.example` в корне):

| Переменная       | По умолчанию |
| ---------------- | ------------ |
| `PGHOST`         | `localhost`  |
| `PGPORT`         | `5432`       |
| `PGDATABASE`     | `calc`       |
| `PGUSER`         | `calc`       |
| `PGPASSWORD`     | `calc`       |
| `ADMIN_USER`     | `admin`      |
| `ADMIN_PASSWORD` | `admin`      |
| `PORT`           | `4000`       |

## Локальный запуск

```bash
cd server
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m app                    # http://localhost:4000
```

Нужен запущенный PostgreSQL — проще всего поднять только БД из корня проекта:
`docker compose up -d db`. Миграция применяется автоматически при старте API.

## Тесты

```bash
cd server
pytest
ruff check .
```

## Docker

`docker compose up --build` из корня проекта — сервис `api` собирается из
`server/Dockerfile` (`python:3.12-slim`, запуск `python -m app`, порт 4000).
