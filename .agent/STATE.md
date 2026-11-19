# Agent State

Status: All planned phases, including the IAM-001 upgrade, are implemented and
verified. Last verification: 2026-11-19.

Current milestone: none required. Optional VirtualBox adapter remains future
work and is only relevant when VirtualBox is installed.

Verified capabilities:

- FastAPI app starts under uvicorn and creates the SQLite metadata schema.
- `GET /api/v1/health` returns real database status.
- `data/mini_aws.db` contains the account, compute, deployment, storage,
  database, IAM, session, activity, and audit metadata tables after migration.
- API errors use a consistent JSON envelope, including 404s.
- Password hashing works with bcrypt directly (passlib incompatibility removed).
- Registration, owner login, IAM login, `/me`, logout, duplicate-email
  rejection, invalid credentials, expiry, and disabled identities are covered
  by API tests.
- Passwords are stored only as bcrypt hashes; session tokens only as HMAC
  hashes. UTC timestamps are returned with explicit timezone information.
- Ownership helpers are implemented and tested for every resource service.
- The React login/register screens call the real API and show loading and error
  states. Console routes require a session.
- Account settings shows the real local account, Local Account ID, and signs out
  through the API.
- IAM accounts have unique 12-digit Local Account IDs. Owner-only databases are
  backfilled in place by `legacy_schema.py` without deleting existing data.
- IAM users, groups, memberships, built-in policies, validated custom policies,
  group policy attachments, and audit logs are persisted and API-managed.
- Central action registry plus `require_permission` protect every endpoint;
  IAM users are deny-by-default, get HTTP 403 for ungranted actions, and cannot
  escalate their own permissions. Owners have full access within their account.
- IAM login uses account ID + username + password, generic error messages, and
  login throttling. First-login password change is mandatory and blocks normal
  APIs until completed.
- The IAM frontend includes overview, users (list/create/edit), groups
  (list/create/detail with members and policies), policies (list/details/
  custom create-edit-delete), audit log, IAM sign-in, and forced password change.
- Detaching a group policy requires confirmation; cancelling leaves the policy
  attached.
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
- The Instances, App deployment, Buckets, Databases, IAM, and Account pages are
  connected to the real backend and covered by frontend workflow tests.
- The Dashboard shows live compute/application running counts, bucket/object/
  byte totals, database totals, and the 10 newest durable activity events.
- Resource actions are persisted in `activity_events`, so history survives
  deletion and is isolated per account.
- Backend (63) and frontend (39) tests pass; the production build succeeds and
  `npm audit --audit-level=moderate` reports 0 vulnerabilities.
- Setup, start, reset, and test scripts parse and run on this Windows machine.
- The IAM-001 Section 13 real-server demonstration passed in the prior
  verification session using `scripts/verify_iam_e2e.py` against an isolated
  temporary data directory. It was not rerun on 2026-11-19 because that session
  changed only a frontend test and documentation.

Known limitations:

- Simplified IAM model: no wildcards, explicit Deny precedence, conditions,
  permission boundaries, federated identities, or MFA.
- Bearer tokens are kept in `localStorage`; no cookie/CSRF scheme. Local use
  only.
- The VirtualBox adapter is not implemented; process compute is the default.

Known environment:

- Windows, Python 3.13.17 in `backend/.venv`, Node.js 24.11.1, npm 11.6.2.
- `python` is not on PATH; scripts use `py -3` or the venv executable.
- No dedicated GPU; keep resource adapters lightweight.
