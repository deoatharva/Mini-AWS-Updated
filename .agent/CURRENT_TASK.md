# Current Task

Task: IAM-001 end-to-end upgrade.

Status: COMPLETE and verified (2026-11-19).

Completed implementation:

1. Accounts/IAM models, in-place legacy backfill, built-in policy seeding, and
   unique 12-digit Local Account IDs.
2. Owner and IAM authentication, generic failures, login throttling, mandatory
   first-login password change, account-aware sessions, and audit events.
3. Central action registry, `require_permission` on every endpoint, IAM
   user/group/policy/attachment/audit APIs, account isolation, owner safety,
   and self-escalation protection.
4. IAM frontend routes/pages, permission-aware navigation, mandatory password
   flow, dashboard, users, groups, policies, and audit log.
5. Group policy detach confirmation dialog with a cancel path that keeps the
   policy attached; `.account-id-row` and `.modal-search` styles present.
6. Frontend and backend workflow tests, production build, and dependency audit.

Verification (2026-11-19):

- Backend: 63 passed (1 non-failing Starlette/httpx deprecation warning).
- Frontend: 13 files, 39 tests passed.
- Production build: 1623 modules transformed successfully.
- `npm audit --audit-level=moderate`: 0 vulnerabilities.
- `data/mini_aws.db` backed up to
  `data/backups/mini_aws.db.bak-2026-11-19` with `PRAGMA integrity_check = ok`
  and matching row counts. The live database was not modified.
- Migration dry run on a copy of that backup preserved every existing row,
  created the IAM tables, backfilled both existing users into 12-digit local
  accounts, seeded 7 built-in policies, and passed `foreign_key_check` and
  `integrity_check`. The temporary copy was deleted.
- The Section 13 real-server demonstration passed in the prior verification
  session; not rerun because this session changed only a frontend test and
  documentation.

No commits or pushes were made. Do not commit unless explicitly requested.
