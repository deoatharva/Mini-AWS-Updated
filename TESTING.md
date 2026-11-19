# Testing Strategy
- Backend unit tests for auth, IAM authorization, resource services, and adapters
- API tests for success cases, validation failures, and unauthorized access
- Frontend build and component tests
- End-to-end tests for practicals 11–15 and the IAM Section 13 scenario
- Verify real filesystem/database/process effects; never test only mocked success paths

## IAM coverage (2026-11-19)

Backend (`tests/backend/test_iam.py`, `test_migration.py`):

- 12-digit Local Account ID generation and account scoping
- Owner creates IAM users and groups; duplicates are rejected within an account
- Password hashes are stored but never returned by the API
- IAM login with account ID, username, and password; generic failures
- Disabled console access and deactivated identities cannot sign in
- Forced first-login password change blocks normal APIs until completed
- Groups: add/remove members, duplicate prevention, deletion without deleting users
- Policy attach/detach, duplicate prevention, and self-escalation protection
- Read-only policy permits list calls and returns HTTP 403 for writes
- Cross-account isolation and owner-only endpoint rejection
- Audit events are written without secrets
- Legacy database migration/backfill preserves existing users and data
- IAM data survives a fresh database session/restart

Frontend:

- `src/routes/IAMFlow.test.jsx`: owner and IAM sign-in, forced password change,
  permission-aware navigation, and denied-action presentation
- `src/pages/iam/IAMUserCreate.test.jsx`: create-user validation and flow
- `src/pages/iam/IAMGroupDetail.test.jsx`: add member, attach policy, detach with
  confirmation, and cancel-detach leaves the policy attached
- `src/pages/iam/IAMPolicyWorkflow.test.jsx`: custom policy create/edit/delete
- `src/pages/iam/IAMAudit.test.jsx`: audit list/search behavior

The real-server demonstration is `scripts/verify_iam_e2e.py`. It uses an
isolated temporary data directory and database, exercises the Section 13
workflow (including HTTP 403 and restart persistence), and never touches
`data/mini_aws.db`.
