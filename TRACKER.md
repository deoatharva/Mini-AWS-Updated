# Feature Tracker

## Complete and verified

- [x] Project foundation and health endpoint
- [x] SQLite metadata initialization under `data/mini_aws.db`
- [x] Consistent API error envelopes and validation errors
- [x] Isolated backend test suite and Windows test runner
- [x] Windows setup, start, and reset scripts
- [x] Local registration/login and authorization
- [x] Account settings and logout UI
- [x] Compute instance lifecycle (process adapter)
- [x] Controlled sample application deployment
  - Real managed Python process serving the built-in template.
  - Deploy/list/get/start/stop/logs/delete API verifies `/health` before
    reporting `running`; failures persist an honest `error` state.
  - App deployment page with real local URLs, logs, and cleanup.
- [x] Bucket/object operations
  - Filesystem-backed buckets under `data/buckets/`, path containment and
    object-name validation, authenticated downloads, overwrite and delete.
  - Buckets page with upload, download, and empty-bucket deletion.
- [x] Isolated database creation and SQL execution
  - Per-user SQLite files under `data/databases/`, ownership checks, schema
    inspection, 200-row result limit, and blocked ATTACH/DETACH/PRAGMA/VACUUM
    and file-reading functions.
  - Databases page with create, schema display, SQL editor, results, and delete.
- [x] Dashboard counts and durable activity history
  - `GET /api/v1/dashboard` refreshes managed process states and aggregates
    compute, application, bucket, object, byte, and database totals.
  - Resource actions are stored in `activity_events`; history survives
    resource deletion and stays isolated per account.
  - Dashboard page shows live summary cards and the 10 newest recorded events.
- [x] Self-service account updates
  - Rename via `PATCH /auth/me`; password change via `POST /auth/password`
    with current-password verification and revocation of other sessions.
  - Account page forms for both, with honest validation and error states.
- [x] End-to-end practicals 11–15 walkthrough
  - 30 live checks passed across accounts, compute, deployment, storage,
    databases, and dashboard cleanup on a real uvicorn server.

## Optional / future

- [ ] VirtualBox compute adapter
  - Only relevant if VirtualBox is installed; process compute is the default.
- [ ] Multi-user hardening beyond the local learning scope
  - The project is intentionally local-only and not production multi-tenant.

## Notes

Placeholder pages are not completed features. A feature is marked complete only
after its real local operation is implemented, connected to the UI, and tested.
All current feature pages are connected and covered by automated tests.
