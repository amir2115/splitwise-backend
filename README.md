# OfflineSplitwise Backend

Production-oriented FastAPI backend for the OfflineSplitwise Android app, built for local execution without Docker and ready for a future Vue.js client.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- JWT access/refresh auth
- pytest
- Uvicorn

## What it includes

- Auth APIs: register, login, refresh, me
- CRUD APIs for groups, members, expenses, settlements
- Balance calculation and simplified debts
- Incremental sync with UTC cursors
- First-login import for guest/offline Android data
- Soft deletion with tombstones
- Alembic migration for the full schema
- pytest coverage for auth, CRUD, validation, balances, and sync

## Project layout

```text
backend/
  app/
    api/
    auth/
    core/
    db/
    models/
    schemas/
    services/
    sync/
    main.py
  alembic/
  tests/
  .env.example
  alembic.ini
  requirements.txt
```

## Environment variables

Copy `.env.example` to `.env` and set:

- `DATABASE_URL`
- `JWT_SECRET_KEY`

Optional:

- `APP_NAME`
- `ENVIRONMENT`
- `DEBUG`
- `API_V1_PREFIX`
- `HOST`
- `PORT`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`
- `APP_DOWNLOAD_ADMIN_SECRET`

## Local setup

Assumptions:

- PostgreSQL is already running separately on `127.0.0.1:5432`
- A database exists for this backend
- You are running with Python `3.12`

Create a virtual environment and install dependencies:

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Run the migration:

```bash
cd backend
.venv/bin/alembic upgrade head
```

Start the API:

```bash
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Compatibility note for simple hosting panels:

- This repo now also exposes a root entrypoint at `main:app`
- If a platform expects an app string like `main:app`, it should work from the `backend/` root
- The canonical module path remains `app.main:app`

Health checks:

- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/api/v1/health`

## Running tests

```bash
cd backend
PYTHONPYCACHEPREFIX=/tmp .venv/bin/python -m pytest tests
```

## API overview

Base path: `/api/v1`

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`

### Resources

- `GET/POST /groups`
- `GET/PATCH/DELETE /groups/{group_id}`
- `GET /groups/{group_id}/balances`
- `GET/POST /members`
- `GET/PATCH/DELETE /members/{member_id}`
- `GET/POST /expenses`
- `GET/PATCH/DELETE /expenses/{expense_id}`
- `GET/POST /settlements`
- `GET/PATCH/DELETE /settlements/{settlement_id}`

### Sync

- `POST /sync/import`
- `POST /sync`

## Sync model

The backend is the canonical source once a user authenticates.

### First authenticated import

Use `POST /api/v1/sync/import` once after login if the user already has local guest data on Android. The request can upload groups, members, expenses, settlements, and deletion tombstones in one payload. The import is allowed only when the authenticated user has no synced groups yet.

### Ongoing sync

Use `POST /api/v1/sync` with:

- `device_id`
- `last_synced_at`
- optional `push`

`push` can contain changed groups, members, expenses, settlements, plus deleted ID lists. The response returns:

- `server_time`
- `next_cursor`
- all changes since `last_synced_at`
- tombstone ID lists for deleted records

### Conflict strategy

- Last-write-wins using `updated_at`
- All timestamps are UTC
- Deleted records are preserved via `deleted_at`
- Expense payers/shares are treated as part of the expense record during sync

## Domain behavior

- Money is stored as integer minor units only
- `EXACT` splits require shares to sum exactly to the expense total
- `EQUAL` splits are normalized on the backend by:
  - sorting member IDs ascending
  - dividing total by share count
  - distributing the remainder by adding `1` to earlier sorted IDs
- Balance calculation uses:
  - expense payers as paid totals
  - expense shares as owed totals
  - settlements as positive paid total for `from_member`
  - settlements as positive owed total for `to_member`

## Notes and assumptions

- The provided workspace did not contain the Android source tree to inspect, so implementation was matched to the supplied product/domain contract rather than verified Room code.
- v1 ownership is single-user per group on the server.
- Group sharing/collaboration between multiple server users is intentionally out of scope.
