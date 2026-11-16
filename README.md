# Mini AWS Cloud Console

A local cloud-lab project with an AWS-console-inspired React interface and a
Python FastAPI backend. It is built for educational practicals 11–15 and is not
a real AWS account or a production cloud platform.

## Current status

All five console services are implemented and tested against real local
resources:

- Local account registration, login, sessions, and logout
- Account settings for display-name changes and password updates
- Compute instances as managed Python worker processes (not VMs), with health,
  logs, ports, and honest lifecycle states
- Controlled sample web application deployment with a real local URL
- Filesystem-backed bucket and object storage with authenticated downloads
- Isolated per-user SQLite databases with schema inspection and a SQL editor
- Dashboard summary counts and recent activity built from real data
- SQLite metadata database at `data/mini_aws.db`
- Isolated backend and frontend test suites plus Windows scripts

See `TRACKER.md` for the exact state and `.agent/TEST_RESULTS.md` for recorded
verification.

## Practicals

1. Local account registration and login
2. Compute instances (process-based adapter; VirtualBox remains optional)
3. Controlled local web application deployment
4. Local object storage with real filesystem objects
5. Isolated local databases with a SQL editor

## Prerequisites

- Windows 10/11
- Python 3.11 or newer (the `py` launcher or `python` on PATH)
- Node.js LTS and npm

## Quick start

From PowerShell in the repository root:

```powershell
.\scripts\setup_windows.ps1
.\scripts\start_all.ps1
```

Then open:

- Console UI: http://127.0.0.1:5173
- API health: http://127.0.0.1:8000/api/v1/health
- API docs: http://127.0.0.1:8000/docs

To run the services in separate terminals instead:

```powershell
.\scripts\start_backend.ps1
.\scripts\start_frontend.ps1
```

## Tests

```powershell
.\scripts\run_tests.ps1
```

This runs the isolated backend test suite and the frontend production build.
See `tests/README.md` and `.agent/TEST_RESULTS.md` for details.

## Project layout

- `frontend/`: React + Vite console
- `backend/`: FastAPI application and local resource adapters
- `data/`: metadata database and real local resource files
- `tests/`: automated tests
- `scripts/`: Windows setup, startup, reset, and test scripts
- `docs/`: feature and architecture documentation
- `.agent/`: implementation state, decisions, and recorded test results

## Local-only notice

This project is for local learning. It does not create real AWS resources,
does not incur cloud charges, and is not hardened for public or production use.
