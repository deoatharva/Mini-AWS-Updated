# Implementation Plan

## Phase 1 — Foundation (complete)

- [x] Inspect documentation, source, and existing state.
- [x] Fix password hashing dependency failure (direct bcrypt).
- [x] Anchor metadata DB at `data/mini_aws.db`.
- [x] Make health endpoint database-aware and errors consistent.
- [x] Add isolated backend test fixtures and foundation tests.
- [x] Verify real uvicorn health response and metadata tables.
- [x] Verify React production build and dev server.
- [x] Repair Windows setup/start scripts and add a test runner.
- [x] Record actual commands and results.

## Phase 2 — Accounts (complete)

- [x] Add API tests for register, login, logout, `/me`, duplicate email,
      invalid credentials, expiry, and unauthorized access.
- [x] Add frontend API client and authentication context.
- [x] Connect Login and Register screens; protect console routes.
- [x] Add logout and account settings UI.
- [x] Add ownership helper used by later resource services.

## Phase 3 — Compute (complete)

- [x] Implement process-based compute adapter with honest labels.
- [x] Persist instance metadata and enforce ownership.
- [x] Implement create/list/get/start/stop/delete API and tests.
- [x] Connect the Instances page.
- [x] Evaluate optional VirtualBox adapter only if installed.

## Phase 4 — Application deployment (complete)

- [x] Add controlled sample application template.
- [x] Implement safe port allocation and managed process lifecycle.
- [x] Verify the deployed app responds before reporting running.
- [x] Expose URL, state, and logs; implement stop/delete.
- [x] Connect the App Deployment page and test end to end.

## Phase 5 — Object storage (complete)

- [x] Implement filesystem bucket/object adapter with path containment.
- [x] Persist object metadata and enforce ownership.
- [x] Implement upload/download/list/delete APIs and tests.
- [x] Connect the Buckets page.

## Phase 6 — Database service (complete)

- [x] Create isolated SQLite files under `data/databases/`.
- [x] Implement safe SQL execution with clear errors and result limits.
- [x] Enforce ownership and path containment.
- [x] Connect the Databases page and SQL editor.

## Phase 7 — Integration and completion

- [x] Connect dashboard counts/status to real backend data.
- [x] Add real recent activity from resource timestamps.
- [x] Run all tests and the production build.
- [x] Verify practicals 11–15 end to end on this machine.
- [x] Fix discovered bugs and update documentation/tracker.

## Phase 9 — Durable activity history

- [x] Add an `activity_events` model and repository.
- [x] Record create/start/stop/upload/deploy/fail/delete events for all services.
- [x] Read dashboard activity from the durable log, newest first.
- [x] Test persistence after deletion, ordering, 10-event limit, and isolation.
- [x] Verify the live workflow and clean up.

## Phase 8 — Account self-service

- [x] Add display-name update endpoint and UI.
- [x] Add password change with current-password verification.
- [x] Revoke other sessions on password change while keeping the current one.
- [x] Add backend/frontend tests and a live end-to-end check.
