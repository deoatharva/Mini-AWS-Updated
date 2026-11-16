# Current Task

Task: Durable activity history — complete.

Status: COMPLETE (verified 2026-11-16).

Completed:

- Added an `activity_events` table with per-account service, action,
  resource type/id/name, and timestamp.
- Compute, application, storage, and database services record create, start,
  stop, upload, deploy, failure, and delete events in the same transaction as
  the resource change.
- Dashboard activity now reads the durable log instead of deriving one event
  per current resource, so history survives resource deletion.
- Activity is limited to the 10 newest events per account, newest first.
- Dashboard labels deletion events and states the feed is recorded actions.
- Added 2 backend tests for persistence/ordering/limits/isolation and updated
  dashboard/frontend tests.

Verification totals:

- Backend: 49 passed (1 non-failing Starlette/httpx deprecation warning).
- Frontend: 31 passed across 8 test files.
- Production Vite build succeeds (1607 modules).
- Live workflow: 18/18 checks passed; after deleting all five resources the
  dashboard kept all 10 events, including deleted object and instance names,
  while every count returned to zero.
- Cleanup confirmed: temp account, its events, and server port removed.

Remaining optional work:

- VirtualBox compute adapter, only if VirtualBox is installed.
- Further hardening beyond the intentional local-learning scope.
