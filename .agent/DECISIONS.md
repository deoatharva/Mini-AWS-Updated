# Decisions Log

- Use React + Vite for the frontend.
- Use FastAPI for the backend.
- Use SQLite for metadata.
- Keep the application local-first.
- Treat VirtualBox as optional; process instances must be labelled honestly.
- Use `bcrypt` directly instead of `passlib`. Passlib 1.7.4 is unmaintained and
  fails at hashing time with bcrypt 5 (`detect_wrap_bug` ValueError).
- Store the metadata database at `data/mini_aws.db` by default so results do not
  depend on the shell's working directory.
- Use `Base.metadata.create_all` at startup for now. Add Alembic only when schema
  changes must preserve existing data; the earlier non-functional `alembic.ini`
  was removed.
- Isolate backend tests with per-test temporary SQLite databases and dependency
  overrides instead of using the real `data/mini_aws.db`.
- Upgrade `react-router-dom` from 6.x to 7.18.5 to clear moderate npm advisories;
  the declarative routing API used by this project is unchanged.
- Store the local bearer token in `localStorage` under
  `mini-aws.access-token`. The API client attaches it to authenticated requests
  and clears the session on a 401; the server stores only a keyed token hash.
- Use one reusable ownership helper (`app.core.permissions.ensure_owner`) that
  rejects another account's resource with HTTP 403 `resource_forbidden`.
- Return explicit UTC-aware timestamps from auth responses so browser date
  formatting is unambiguous.
- Catch registration `IntegrityError` and return the same 409 conflict as the
  normal duplicate-email path, covering the check/insert race.
- Use Vitest + jsdom + React Testing Library for repeatable frontend workflow
  tests. Network calls are mocked in those tests; real API behavior is verified
  separately against a running uvicorn process.
- Represent compute instances as managed Python worker processes with a real
  heartbeat file, a localhost health endpoint, redirected logs, and a reported
  PID. The UI labels them as processes, not virtual machines.
- Use `psutil` only for safe lifecycle checks and termination: before signalling
  a PID, verify its command line still contains the expected worker script and
  instance ID. This avoids acting on a recycled PID.
- Never require `Popen.pid` to equal the worker's reported PID. The Python venv
  launcher observed on this Windows machine can create a small parent wrapper;
  lifecycle operations use the worker-reported PID and verify its command line.
- Allocate compute workers from `COMPUTE_PORT_START`-`COMPUTE_PORT_END`
  (default 18000–18999), bound to `127.0.0.1` only.
- Stop workers gracefully with a stop-request file, then terminate/kill only
  after the real process fails to exit within the timeout.

## IAM decisions (2026-11-19)

- Keep one SQLite metadata database. IAM tables are added to the existing
  schema; no second backend or database was introduced.
- Use a small explicit forward migration (`legacy_schema.py`) on top of
  `create_all` to preserve owner-only databases. Each legacy user becomes the
  owner of a new local account; resources keep pointing at that owner's user ID.
- Store account resources against the account owner's user ID. IAM users in the
  same account therefore work with shared account resources, while authorization
  still decides which actions are allowed and ownership checks block other
  accounts.
- Use the union of policy `Allow` actions as the IAM permission model. No
  wildcards, Deny precedence, conditions, or boundaries are claimed or
  partially implemented.
- Protect every API with `require_permission(action)` and keep the action list
  in `action_registry.py`, so policy documents, UI descriptions, and endpoint
  checks cannot drift apart.
- Reuse bcrypt for password hashing and the existing opaque HMAC-hashed session
  tokens. Do not add cookies/CSRF for this local bearer-token lab; document the
  limitation instead.
- Throttle logins in memory per identity key for the local single-process
  deployment. The throttle is not a distributed rate limiter.
- Record audit events with safe metadata only. Never store credentials, hashes,
  tokens, or secrets.
- Require an explicit confirmation before detaching a group policy; cancel is a
  no-op and never calls the API.
