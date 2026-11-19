# Agent Tracker

Detailed feature status lives in the root `TRACKER.md`. This file records the
agent-level status of the IAM-001 upgrade.

## IAM-001 — complete (2026-11-19)

- [x] Accounts and 12-digit Local Account IDs
- [x] Owner and IAM authentication with throttling and generic errors
- [x] Mandatory first-login password change
- [x] IAM users, groups, memberships, and account isolation
- [x] Built-in policies, validated custom policies, attach/detach
- [x] Central backend authorization with HTTP 403 denials
- [x] Owner safety and self-escalation protection
- [x] IAM frontend pages, permission-aware navigation, and audit log
- [x] Policy-detach confirmation and cancel behavior
- [x] Legacy forward migration/backfill
- [x] Backend and frontend tests, production build, and dependency audit
- [x] Verified backup of `data/mini_aws.db` before migration

## Remaining / limitations

- [ ] Full AWS IAM semantics (wildcards, Deny, conditions, boundaries, MFA)
- [ ] Cookie-based sessions with CSRF protection (local bearer-token lab only)
- [ ] Optional VirtualBox compute adapter
