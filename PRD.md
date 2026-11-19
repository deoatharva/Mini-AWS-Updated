# Product Requirements Document

## Goal
Build a functional local cloud lab for practicals 11–15 using React and FastAPI.

## Core features
- Local account registration and owner login
- IAM: Local Account IDs, IAM users, groups, policy attachments, server-side
  authorization, forced first-login password change, and an audit log
- Create/start/stop/delete compute instances
- Deploy a controlled sample web application and show its local URL
- Create storage buckets and upload/download/delete files
- Create isolated local databases and execute SQL
- Dashboard, activity history, validation, and useful error messages

## Non-goals
- Creating or representing a real AWS account
- Public cloud hosting or billing
- Production multi-tenant hosting

## Acceptance criteria
Features must operate on real local resources, return accurate status, handle errors, and have automated tests. Do not use fake success states.

IAM acceptance: owner can create users/groups and attach policies; an IAM user
can sign in with account ID, username, and password, must change a temporary
password on first login, and receives HTTP 403 when their effective policy does
not allow an action. IAM data and audit events must persist across restarts and
remain isolated per local account.
