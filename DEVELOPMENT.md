# Development Guide

## Prerequisites

- Windows 10/11
- Python 3.11 or newer
- Node.js LTS and npm

## First-time setup

Run from PowerShell in the repository root:

```powershell
.\scripts\setup_windows.ps1
```

The script:

1. Creates `backend/.venv` with the `py` launcher or `python`.
2. Installs backend production and development dependencies.
3. Creates `backend/.env` with a generated local `SECRET_KEY` if it is missing.
4. Installs frontend dependencies and creates `frontend/.env.local` if missing.

## Start the lab

```powershell
.\scripts\start_all.ps1
```

This opens the backend and frontend in separate PowerShell windows.

URLs:

- Console: http://127.0.0.1:5173
- Health: http://127.0.0.1:8000/api/v1/health
- OpenAPI docs: http://127.0.0.1:8000/docs

Alternative two-terminal workflow:

```powershell
.\scripts\start_backend.ps1
.\scripts\start_frontend.ps1
```

## Run checks

```powershell
.\scripts\run_tests.ps1
```

Exact commands:

```powershell
# From the repository root
.\backend\.venv\Scripts\python.exe -m pytest -q .\tests\backend

# From frontend/
npm run build
```

Backend tests use per-test temporary SQLite databases. They must not touch the
real metadata database or local resource files.

## Configuration

Environment settings are read from `backend/.env` (see
`backend/.env.example`). Do not commit `.env` or real secrets.

| Setting | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Requires a non-default secret outside development |
| `SECRET_KEY` | development placeholder | Signs hashed session tokens |
| `DATABASE_URL` | `sqlite:///<repo>/data/mini_aws.db` | Metadata database |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Local API binding |
| `CORS_ORIGINS` | `http://127.0.0.1:5173,http://localhost:5173` | Allowed UI origins |
| `MAX_UPLOAD_BYTES` | `10485760` | Object upload limit |

The frontend API base URL is configured in `frontend/.env.local`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## Local data

- Metadata database: `data/mini_aws.db`
- Buckets: `data/buckets/`
- Compute instance metadata/files: `data/instances/`
- Deployed applications: `data/applications/`
- User-created databases: `data/databases/`

To clear local resources and the metadata database:

```powershell
.\scripts\reset_local_data.ps1
```

Type `RESET` at the confirmation prompt. `.gitkeep` files are preserved.

## Database schema

The metadata schema is created from the SQLAlchemy models at API startup. There
is no migration tool yet; see `backend/app/database/migrations/README.md`.

## Troubleshooting

- **`python` opens the Microsoft Store**: use the `py` launcher or rerun
  `setup_windows.ps1`, which detects `py -3`.
- **Port already in use**: stop the process using port 8000 or 5173. The
  services are intentionally bound to localhost.
- **Health returns 503**: the API is running but the metadata database is
  unavailable; check the backend log and `data/` write permissions.
- **Frontend cannot reach the API**: confirm both services are running and that
  `CORS_ORIGINS` includes the UI origin.

## Current phase

Phase 1 is complete. Phase 2 (account screen integration and auth API tests) is
next. See `.agent/STATE.md` and `TRACKER.md`.
