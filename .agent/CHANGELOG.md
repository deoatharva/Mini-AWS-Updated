# Changelog

## Unreleased

### Phase 1 — Foundation (2026-11-16)

- Added database-aware health response with service version.
- Added consistent JSON error envelope for HTTP errors (including 404).
- Replaced broken passlib/bcrypt 5 password hashing with direct bcrypt.
- Anchored the default SQLite metadata database at `data/mini_aws.db`.
- Added CORS origin configuration and non-development secret validation.
- Added isolated pytest fixtures and foundation/security tests.
- Added root and backend `pytest.ini` files so tests run from either the repo
  root or `backend/`.
- Added `scripts/run_tests.ps1`.
- Reworked Windows setup to detect `py -3`, generate `backend/.env`, and create
  `frontend/.env.local`.
- Made start scripts resilient to missing backend environment files.
- Fixed reset script to preserve `.gitkeep` and remove the metadata DB.
- Upgraded `react-router-dom` to 7.18.5; npm audit is clean.
- Removed non-functional `alembic.ini`; documented current schema strategy.
- Updated README, DEVELOPMENT, trackers, and recorded test results.

### Phase 2 — Accounts (2026-11-16)

- Added automated auth API tests for register/login/logout/me, duplicates,
  invalid credentials, expiry, and unauthorized access.
- Added the frontend API client, auth context, connected login/register pages,
  protected console routes, and account settings with logout.
- Added a reusable ownership helper for resource services.

### Phase 3 — Compute (2026-11-16)

- Added `compute_instances` metadata, ownership checks, and repository/schema/API
  routes.
- Implemented a real managed Python worker process with heartbeat, health
  endpoint, bounded localhost port allocation, captured logs, and graceful stop.
- Added `psutil`-guarded process identity checks and shutdown cleanup.
- Added 5 backend compute tests and 3 frontend Instances workflow tests.
- Connected the Instances page with create/start/stop/logs/delete flows and
  honest process-not-VM labels.
- Verified a real uvicorn create/start/health/logs/stop/delete lifecycle.

### Phase 4 — Application deployment (2026-11-16)

- Added `application_deployments` metadata, ownership checks, repository/schema/
  API routes for deploy/list/get/start/stop/logs/delete.
- Added a controlled `sample-web-app` template served by a real Python process;
  no uploaded code or arbitrary scripts are executed.
- Reused bounded localhost port allocation and psutil-guarded process identity
  checks, with separate 19000–19999 defaults from compute workers.
- Start verifies the app's real `/health` endpoint before reporting `running`;
  failures persist an honest `error` state and return 503.
- Added 5 backend deployment tests and 3 frontend Applications workflow tests.
- Connected the App deployment page with real URLs, states, logs, and cleanup.
- Verified a real uvicorn deploy/page/health/info/logs/stop/delete lifecycle.

### Phase 5 — Object storage (2026-11-16)

- Added filesystem-backed buckets with per-user directories, path containment,
  and strict object-name validation.
- Added authenticated upload/download/list/overwrite/delete APIs with ownership
  checks, size limits, ETags, and usage summaries.
- Connected the Buckets page with object upload, download, and safe empty-bucket
  deletion.
- Added 5 backend storage tests against real files and 3 frontend workflow
  tests.

### Phase 6 — Isolated databases (2026-11-16)

- Added per-user SQLite files under `data/databases/` with ownership checks and
  schema inspection.
- Added safe SQL execution with a 200-row result limit, typed errors, and
  blocked ATTACH/DETACH/PRAGMA/VACUUM and file-reading functions.
- Replaced the Databases placeholder with a connected page offering creation,
  schema display, a SQL editor, result tables, and deletion.
- Added 8 backend database tests and 3 frontend Databases workflow tests.
- Verified a real uvicorn create/table/insert/select/deny/delete lifecycle.

### Phase 9 — Durable activity history (2026-11-16)

- Added the `activity_events` table and a repository/service for recording
  per-account resource events in the same transaction as the change.
- Compute, deployment, storage, and database services now record created,
  started, stopped, deployed, uploaded, failed, and deleted actions.
- Dashboard activity now reads the durable log instead of deriving one event
  per current resource, so deletion no longer erases history.
- Added backend tests for persistence, ordering, the 10-event limit, and
  account isolation; updated the dashboard UI/tests for deletion events.
- Verified live that all 10 events survive after every resource is deleted.

### Phase 8 — Account self-service (2026-11-16)

- Added `PATCH /api/v1/auth/me` for display-name updates.
- Added `POST /api/v1/auth/password` with current-password verification,
  same-password rejection, and revocation of other sessions.
- Added Account page forms for name and password updates with validation,
  success, and error states.
- Added 3 backend tests and 3 frontend Account tests; verified live rename and
  password-change session behavior.

### Phase 7 — Dashboard integration (2026-11-16)

- Added `GET /api/v1/dashboard` with real per-account compute and application
  running totals, bucket/object/byte counts, database totals, and recent
  activity from real resource timestamps.
- Dashboard refreshes managed process states before reporting totals.
- Connected the Dashboard page with live summary cards, an activity feed with
  service links, refresh, loading, error, and empty states.
- Added 4 backend dashboard tests and 3 frontend Dashboard tests.
- Updated README status and feature documentation.
- Verified a live uvicorn dashboard aggregation and cleanup.
- Completed a live practicals 11–15 walkthrough: 30/30 checks passed across
  accounts, compute, deployment, storage, databases, and dashboard state.
- Recorded final test totals (44 backend, 28 frontend) and verification results.

### Initial scaffold

- Created initial project scaffold and documentation.
