# Architecture
- Frontend: React + Vite
- Backend: Python + FastAPI
- Metadata: SQLite through a repository/service layer
- Resource adapters: process-based compute, optional VirtualBox, local app runner, filesystem object storage, per-resource SQLite databases
- Communication: JSON REST API under `/api/v1`
- Local development only; bind services to localhost by default.

## IAM data model

All IAM metadata lives in the same SQLite database (`data/mini_aws.db`):

- `accounts`: internal ID, unique 12-digit `account_id` (Local Account ID),
  name, status, `owner_user_id`, timestamps.
- `users`: legacy login fields plus `account_id`, `username`, `user_type`
  (`OWNER` or `IAM`), `status`, `console_access_enabled`,
  `must_change_password`, `updated_at`, and `last_login_at`. A unique
  `(account_id, username)` constraint scopes names per local account.
- `groups`, `group_memberships`, `policies`, `group_policy_attachments`:
  account-scoped groups, memberships, structured policy documents, and
  attachments. Uniqueness prevents duplicate members and duplicate attachments.
- `auth_sessions`: user/account-scoped opaque session tokens; only an HMAC hash
  is stored.
- `audit_logs`: account, actor, event type, target, success/failure, safe JSON
  metadata, and timestamp. Passwords, hashes, tokens, and secrets are never
  recorded.
- `activity_events`: existing resource activity history, now shared by all
  identities in the same local account through the account owner's resource
  metadata.

`backend/app/database/legacy_schema.py` performs the in-place forward migration
for owner-only databases created before IAM: it adds the new user columns,
creates one local account per existing user, backfills the owner identity and
session account links, and adds the unique/index constraints. New databases are
created directly from the SQLAlchemy models.

## Authentication

- Owners continue to sign in with email and password at `/auth/login`.
- IAM users sign in at `/auth/iam/login` with Local Account ID, username, and
  password. Failures use one generic message and never reveal which field was
  wrong.
- Sessions are opaque bearer tokens. The database stores only a keyed token
  hash; logout revokes the session row.
- Login throttling is applied per account/email or account ID/username.
- `must_change_password` restricts the session to the mandatory password-change
  endpoint and logout until a new password is set.

## Authorization

- `backend/app/core/action_registry.py` is the single source of truth for
  action identifiers, descriptions, and built-in policy documents.
- `backend/app/core/authorization.py::require_permission(action)` protects every
  API endpoint. It resolves the authenticated identity, checks the mandatory
  password state, computes effective actions, and returns HTTP 403 when the
  action is not allowed.
- Owners implicitly hold every registered action inside their own account.
- IAM users are deny-by-default. Their effective actions are the union of
  `Allow` statements in policies attached to groups they belong to.
- Resource services resolve the account owner's user ID for storage and
  queries, so IAM users operate on the same local account resources while
  direct cross-account IDs remain rejected by ownership checks.
- This is a deliberately simplified allow-list model: no wildcards, explicit
  Deny precedence, conditions, or permission boundaries.

## IAM frontend

Routes live under `/iam` (overview, users, groups, policies, audit) plus
`/login/iam` and `/account/change-password`. Navigation and buttons are
permission-aware, but hiding UI is never the security boundary: every action is
re-checked by the API.
