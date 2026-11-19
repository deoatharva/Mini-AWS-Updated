# Security Notes
- Local educational use only; not production-hardened
- Hash passwords with bcrypt; never store or log plaintext passwords, hashes, session tokens, or secrets
- Keep secrets in environment variables; never commit `.env`
- Enforce ownership and authorization on every resource endpoint
- Validate filenames, sizes, SQL operations, ports, and deployment inputs
- Avoid arbitrary code execution and unrestricted shell commands
- Bind to localhost by default; do not expose to LAN or internet without security review

## IAM controls

- Every protected endpoint uses `require_permission(action)`; authorization is
  evaluated server-side and forbidden requests return HTTP 403. Hiding a
  frontend button is not treated as access control.
- IAM users are deny-by-default. Effective permissions are the union of actions
  allowed by policies attached to their groups within the same local account.
- Account isolation is enforced in queries and ownership checks. Cross-account
  resource IDs and IAM identifiers are rejected.
- IAM users cannot change the owner identity, delete themselves through
  owner-only operations, or attach/detach policies for a group they belong to
  (self-escalation protection).
- The last active owner identity cannot be deleted or deactivated.
- Session tokens are stored only as HMAC hashes and revoked on logout.
- Login attempts are throttled per identity key, and authentication failures
  use generic messages that do not reveal which credential was wrong.
- Temporary passwords set `must_change_password`; normal console APIs are
  blocked until the user completes the password change.
- Audit records include account, actor, event, target, outcome, and safe
  metadata only. Passwords, hashes, tokens, and secrets are never recorded.
- Built-in policies are immutable. Custom policy documents are validated
  server-side against the registered action list; executable code is never
  accepted as a policy.

## Limitations

- This is not AWS IAM: there are no wildcards, explicit Deny precedence,
  conditions, permission boundaries, federated identities, or MFA.
- The bearer token is kept in browser `localStorage` for this local lab; there
  are no HTTP-only SameSite cookies or CSRF tokens. Do not deploy publicly.
- The simplified model treats all identities in a local account as sharing that
  account's resource data, subject to policy checks.
