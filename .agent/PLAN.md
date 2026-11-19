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

## Phase 10 — IAM data model, migration, and authentication (complete)

- [x] Add accounts, IAM users, groups, memberships, policy attachments, policies, and audit models.
- [x] Add a lightweight SQLite migration/backfill for existing owner-only metadata and seed built-in policies.
- [x] Generate unique 12-digit Local Account IDs and scope resources to the account owner.
- [x] Add IAM login, mandatory first-login password change, account-aware sessions, and login throttling.
- [x] Add backend tests for accounts, IAM login, disabled identities, forced password change, and persistence.

## Phase 11 — IAM backend and authorization (complete)

- [x] Implement IAM user, group, membership, policy, attachment, overview, and audit APIs.
- [x] Centralize action identifiers and built-in policy documents in one backend registry.
- [x] Enforce owner/bypass and IAM union-of-group-policies allow-list authorization on every endpoint.
- [x] Enforce account isolation, duplicate prevention, owner safety, and self-escalation protection.
- [x] Record required audit events without secrets and add positive/negative authorization tests.

## Phase 12 — IAM frontend (complete)

- [x] Add API client methods, account/permission-aware auth context, and mandatory password route guard.
- [x] Add owner and IAM sign-in flows plus first-login password change.
- [x] Add IAM overview, users, groups, policies, policy details, and audit pages.
- [x] Add real create/edit/delete/reset/member/attach/detach actions and permission-aware navigation.
- [x] Add frontend workflow tests with mocked network and verify the production build.
- [x] Require confirmation before detaching a group policy; cancel keeps it attached.

## Phase 13 — IAM end-to-end verification and documentation (complete)

- [x] Run the complete Section 13 demonstration against a real uvicorn server and isolated data directory.
- [x] Verify HTTP 403 denials, cross-account isolation, audit records, and restart persistence.
- [x] Clean up workers and temporary data.
- [x] Update all root and `.agent/` documentation with real results and limitations.
- [x] Create and verify a backup of `data/mini_aws.db` before any migration is applied to real data (2026-11-19).
