# Agent State

Status: All planned phases (1–9) are complete and verified on 2026-11-16.

Current milestone: none required. Optional VirtualBox adapter remains future
work and is only relevant when VirtualBox is installed.

Verified capabilities:

- FastAPI app starts under uvicorn and creates the SQLite metadata schema.
- `GET /api/v1/health` returns real database status.
- `data/mini_aws.db` contains the account, compute, deployment, storage, and
  database metadata tables.
- API errors use a consistent JSON envelope, including 404s.
- Password hashing works with bcrypt directly (passlib incompatibility removed).
- Registration, login, `/me`, logout, duplicate-email rejection, invalid
  credentials, and expired-session rejection are covered by API tests.
- Passwords are stored only as bcrypt hashes; session tokens only as HMAC
  hashes. UTC timestamps are returned with explicit timezone information.
- Ownership helpers are implemented and tested for every resource service.
- The React login/register screens call the real API and show loading and error
  states. Console routes require a session.
- Account settings shows the real local account and signs out through the API.
- Compute instances are real managed Python worker processes with heartbeat,
  health, logs, port, PID, honest lifecycle states, and ownership checks.
- Application deployments run the controlled sample web app as a real managed
  process, are only reported `running` after `/health` succeeds, expose a real
  local URL/logs, and stop/delete cleanly.
- Storage buckets are real directories under `data/buckets/`; uploads are
  validated, downloads require authentication, and objects are listed only for
  their owner.
- Isolated databases are real SQLite files under `data/databases/` with
  ownership checks, schema inspection, 200-row result limits, and blocked
  ATTACH/DETACH/PRAGMA/VACUUM and file-reading functions.
- The Instances, App deployment, Buckets, and Databases pages are connected to
  the real backend and covered by frontend workflow tests.
- The Dashboard shows live compute/application running counts, bucket/object/
  byte totals, database totals, and the 10 newest durable activity events.
- Account settings support display-name updates and password changes with
  current-password verification and other-session revocation.
- Resource actions are persisted in `activity_events`, so history survives
  deletion and is isolated per account.
- Backend (49) and frontend (31) tests pass; the production build succeeds.
- Setup, start, reset, and test scripts parse and run on this Windows machine.

Completed practicals walkthrough:

- Practicals 11–15 passed 30 live checks against one uvicorn server covering
  accounts, compute workers, controlled deployment, object storage download
  integrity, isolated SQL execution/schema, dangerous-SQL denial, dashboard
  totals, and full cleanup.

Optional / future:

- The VirtualBox adapter is not implemented; process compute is the default.

Known environment:

- Windows, Python 3.13.17 in `backend/.venv`, Node.js 24.11.1, npm 11.6.2.
- `python` is not on PATH; scripts use `py -3` or the venv executable.
- No dedicated GPU; keep resource adapters lightweight.
