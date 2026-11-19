# Feature Upgrade Specification: Identity and Access Management (IAM)

**Feature ID:** IAM-001  
**Priority:** Critical  
**Target:** Mini AWS Cloud Console  
**Status:** Required implementation

> This document is the complete specification. The coding agent must implement the feature using only this document and the existing project repository. It does not need to read or refer to any external PDF, practical sheet, screenshot, or other document.

---

## 1. Goal

Upgrade Mini AWS with a fully functional **Identity and Access Management (IAM)** module.

A student must be able to:
- Register and sign in as the account owner.
- Create separate IAM users.
- Enable or disable console access for IAM users.
- Create user groups.
- Create/select permission policies.
- Attach policies to groups.
- Add existing IAM users to groups and remove them.
- Sign in as an IAM user using the account ID, username, and password.
- Force an IAM user to change their temporary password on first login.
- Verify that permissions actually restrict what the IAM user can do.
- Review an audit log of identity-management activity.

This must be a real working feature with frontend, backend, database persistence, authentication, authorization, and tests. Do not build a static mock-up.

## 2. Important architecture rules

1. Inspect the existing repository before changing code.
2. Reuse the current React frontend, FastAPI backend, SQLAlchemy/database setup, routing, authentication, styling, and shared components wherever possible.
3. Do not create a second disconnected backend or database.
4. Do not break existing compute, application deployment, storage, or database modules.
5. Do not replace working features with placeholders.
6. Keep the implementation suitable for a local Windows development environment.
7. Bind local development services to localhost by default.
8. All IAM operations must persist after restarting the application.
9. Do not use fake data as if it were real persisted data.
10. Do not claim that this local educational system creates or manages real AWS accounts or AWS IAM identities.

## 3. Account and identity structure

### 3.1 Local account

When a person registers the Mini AWS application, create a local account/tenant and its owner identity.

Each account must have:
- Internal database ID.
- Unique 12-digit `account_id` displayed as **Local Account ID**.
- Account name.
- Status.
- Creation timestamp.

The Local Account ID is used when an IAM user signs in. Provide a copy button in the UI.

### 3.2 Owner identity

The owner is the root-equivalent administrator for that local account.

Owner capabilities:
- View account details and Local Account ID.
- Create, view, edit, activate/deactivate, and delete IAM users, subject to safety rules.
- Create, edit, and delete groups.
- View and manage policies.
- Attach and detach policies from groups.
- Add and remove users from groups.
- Reset IAM user passwords.
- Require a password change at next login.
- View IAM audit logs.

The owner has full permissions only inside their own local account. Prevent deletion/deactivation of the last active owner identity.

### 3.3 IAM user identity

An IAM user is a separate login identity associated with exactly one local account.

IAM user capabilities:
- Sign in using Local Account ID + username + password.
- Change their own password.
- View their profile, group memberships, and effective permissions.
- Use only the services/actions granted by their policies.
- Sign out.

IAM users must not access owner-only administration features unless explicitly granted the relevant permission.

## 4. Required IAM module structure

Add **Identity & Access Management (IAM)** to the main console navigation, preferably under a Services section.

The IAM module must contain these pages:

```text
IAM
├── Overview
├── Users
│   ├── Users List
│   ├── Create User
│   └── User Details / Edit
├── User Groups
│   ├── Groups List
│   ├── Create Group
│   └── Group Details
│       ├── Members
│       └── Attached Policies
├── Policies
│   ├── Policies List
│   ├── Policy Details
│   └── Create / Edit Policy (if custom policies are supported)
└── Audit Log
```

Also add authentication pages:
```text
Authentication
├── Owner Login / Registration (reuse existing pages)
├── IAM User Login
└── Mandatory First-Login Password Change
```

Suggested React routes (adapt to existing route conventions):
- `/iam`
- `/iam/users`
- `/iam/users/new`
- `/iam/users/:id`
- `/iam/groups`
- `/iam/groups/new`
- `/iam/groups/:id`
- `/iam/policies`
- `/iam/audit`
- `/login/iam`
- `/account/change-password`

### IAM overview dashboard

Display:
- Total IAM users.
- Active IAM users.
- Disabled users.
- Total groups.
- Total policies.
- Recent IAM activity.

Quick actions:
- Create user.
- Create group.
- View policies.

Include useful empty states and links to the relevant pages.

## 5. User management requirements

### 5.1 Create user form

Fields:
- Username — required and unique within the account.
- Display name — optional.
- Console access — enabled/disabled.
- Initial/temporary password.
- Confirm password.
- Require password change at next sign-in — enabled by default.
- Optional group assignment.

Validation:
- Enforce a documented username format.
- Enforce username uniqueness within the account.
- Enforce password strength and confirmation.
- Never store plaintext passwords.
- Never return password hashes from APIs.
- Never show a saved password again after the creation flow.

After creation, show a confirmation containing the username and Local Account ID, but never expose the stored password/hash.

### 5.2 Users list

Show:
- Username.
- Display name.
- Status.
- Console access status.
- Group membership.
- Password-change-required status.
- Creation date.
- Last login, if available.

Actions:
- View details.
- Edit.
- Activate/deactivate.
- Reset password.
- Delete, with confirmation.

Prevent an IAM user from deleting or changing their own identity through owner-only operations.

### 5.3 User details

Show:
- Identity/profile information.
- Account association.
- Status and console access.
- Group memberships.
- Effective permissions and the groups/policies that grant them.
- Last login and recent activity, if available.

## 6. Group management requirements

### 6.1 Create group

Fields:
- Group name — required and unique within the account.
- Description — optional.
- Optional policy selection.

### 6.2 Group list

Show:
- Group name.
- Description.
- Number of users.
- Number of attached policies.
- Creation date.
- Actions to view/edit/delete.

### 6.3 Group details

Provide separate sections/tabs:
- Summary.
- Users/Members.
- Permissions/Attached Policies.

Actions:
- Add users.
- Remove users.
- Attach policies.
- Detach policies.
- Edit group.
- Delete group.

Rules:
- A user may belong to multiple groups.
- A user can be added only to a group in the same account.
- Prevent duplicate membership.
- Deleting a group must not delete its users.
- Deletion must safely remove membership and policy-association records.

### 6.4 Add users workflow

1. Owner opens a group.
2. Owner clicks **Add users**.
3. Display existing eligible IAM users from the same account.
4. Allow selecting one or multiple users.
5. Owner confirms.
6. Persist membership and refresh the group member list.
7. Record the operation in the audit log.

Also support removing a user from a group.

## 7. Policy management and permission model

Policies must be structured data that the backend actually enforces. A policy must not be just a label displayed in the UI.

### 7.1 Built-in policies

Seed these built-in policies:

| Policy | Allowed capability |
|---|---|
| `AdministratorAccess` | All supported application actions |
| `ReadOnlyAccess` | View/list resources; no create, update, delete, start, or stop |
| `ComputeAccess` | Manage compute resources |
| `StorageAccess` | Manage storage buckets and objects |
| `DatabaseAccess` | Manage database resources |
| `IAMReadOnlyAccess` | View IAM users, groups, and policies |
| `IAMManagementAccess` | Manage IAM users, groups, and group policy assignments, but not owner account security |

The UI must explain what each policy allows.

### 7.2 Action identifiers

Centralize action names in one backend permission registry. Use consistent identifiers such as:

```text
iam:ListUsers
iam:CreateUser
iam:UpdateUser
iam:DeleteUser
iam:ListGroups
iam:CreateGroup
iam:UpdateGroup
iam:DeleteGroup
iam:AddUserToGroup
iam:RemoveUserFromGroup
iam:AttachGroupPolicy
iam:DetachGroupPolicy
iam:ListPolicies
compute:ListInstances
compute:CreateInstance
compute:StartInstance
compute:StopInstance
compute:DeleteInstance
storage:ListBuckets
storage:CreateBucket
storage:DeleteBucket
storage:ListObjects
storage:UploadObject
storage:DeleteObject
database:ListDatabases
database:CreateDatabase
database:DeleteDatabase
```

Map each built-in policy to the correct action identifiers. Ensure the policy names and permissions shown in the UI match the backend implementation.

### 7.3 Policy screens

Policies list should show:
- Policy name.
- Description.
- Managed/built-in or custom status.
- Version.
- Number of groups using the policy.

Provide policy details showing its allowed actions. If custom policies are implemented, validate their structured document server-side. Never accept executable code as a policy.

### 7.4 Attach/detach policy workflow

1. Owner opens a group.
2. Clicks **Attach policies**.
3. Searches and selects one or more policies.
4. Confirms.
5. Backend persists the attachment.
6. Group details show the attached policies.
7. Owner can detach a policy after confirmation.

Prevent duplicate attachments.

### 7.5 Effective permission calculation

For V1:
- Owner has full permissions within their own account.
- IAM user's allowed actions are the union of actions granted by policies attached to all groups the user belongs to.
- If no policy grants an action, deny it.
- Use allow-list, deny-by-default semantics.
- Document that this is a simplified educational model, not full AWS IAM policy compatibility.

Do not add wildcards, explicit Deny precedence, conditions, policy boundaries, or other advanced semantics unless fully implemented and tested.

## 8. IAM user authentication

### 8.1 IAM login page

Add a separate **IAM user sign-in** option on the existing login screen.

Fields:
- Local Account ID — exactly 12 digits.
- IAM username.
- Password.

Backend must verify that the account ID, username, and password belong together.

On success:
- Create a secure authenticated session.
- Redirect to the console.
- Show the current signed-in username and account context.
- Load the user's effective permissions.

On failure:
- Show a generic message such as “Invalid account ID, username, or password.”
- Do not reveal which field was incorrect.
- Apply basic login throttling/rate limiting.
- Never log credentials.

A deactivated user or a user with console access disabled must not be able to sign in.

### 8.2 First-login password change

When `must_change_password` is true:
1. Authenticate the user into a restricted session.
2. Redirect immediately to the password-change screen.
3. Require a new password and confirmation.
4. Validate password strength.
5. Save the new password hash.
6. Set `must_change_password` to false.
7. Allow normal console access only after successful completion.

Before password change, block normal console pages and protected APIs. Only password change and logout should be accessible.

Owner password reset must be able to set `must_change_password` to true.

### 8.3 Logout

Logout must invalidate/revoke the active session. To test another identity, sign out and authenticate again. Do not implement a shortcut that changes identity without authentication.

## 9. Backend authorization — mandatory

**Critical:** Hiding buttons in React is not security.

Implement centralized backend authorization:
1. Resolve the authenticated user and account.
2. Resolve group memberships.
3. Resolve policies attached to those groups.
4. Calculate effective actions.
5. Check the required action for every protected endpoint.
6. Return HTTP 403 if the action is not permitted.
7. Enforce account ownership in every query and mutation.

Every API must be protected by the correct permission. Never trust a frontend-supplied account ID or user role as proof of authorization.

Test authorization using direct API requests, not only by checking whether buttons are hidden.

## 10. Audit log

Record at least:
- IAM user created, updated, activated, deactivated, or deleted.
- Password reset and password changed.
- Successful and failed sign-in.
- Group created, updated, or deleted.
- User added to or removed from group.
- Policy created/updated/deleted, attached, or detached.

Each audit entry should include:
- Account ID.
- Actor identity (owner, IAM user, or system/anonymous where appropriate).
- Event/action.
- Target type and ID.
- Timestamp.
- Success/failure.
- Safe metadata.

Never store passwords, password hashes, session tokens, or secrets in audit records.

Provide a searchable/filterable Audit Log page. Owner can view all events for their account. Other users require an explicit audit-read permission if that feature is supported.

## 11. Suggested database structure

Adapt this to the existing SQLAlchemy models and migration system. Do not create a separate unrelated database.

### `accounts`
- `id`
- `account_id` — unique 12-digit string
- `name`
- `status`
- `created_at`

### `users`
- `id`
- `account_id` — foreign key
- `username`
- `display_name`
- `password_hash`
- `user_type` — `OWNER` or `IAM`
- `status`
- `console_access_enabled`
- `must_change_password`
- `created_at`
- `updated_at`
- `last_login_at`

Unique constraint: `(account_id, username)`.

### `groups`
- `id`
- `account_id`
- `name`
- `description`
- `created_at`

Unique constraint: `(account_id, name)`.

### `group_memberships`
- `id`
- `account_id`
- `group_id`
- `user_id`
- `created_at`

Unique constraint: `(group_id, user_id)`.

### `policies`
- `id`
- `account_id` (nullable for immutable built-ins, or use a built-in policy registry)
- `name`
- `description`
- `version`
- `document_json`
- `is_managed`
- `created_at`
- `updated_at`

### `group_policy_attachments`
- `id`
- `account_id`
- `group_id`
- `policy_id`
- `created_at`

Unique constraint: `(group_id, policy_id)`.

### `sessions` (if using database-backed sessions)
- `id`
- `user_id`
- `account_id`
- `token_hash`
- `expires_at`
- `created_at`
- `revoked_at`

Store only a hash of the session token, never the raw token.

### `audit_logs`
- `id`
- `account_id`
- `actor_user_id` (nullable for unauthenticated attempts/system events)
- `event_type`
- `target_type`
- `target_id`
- `success`
- `metadata_json`
- `created_at`

Use foreign keys, indexes, unique constraints, transactions, and database migrations.

## 12. Suggested API structure

Use the existing `/api/v1` prefix and project conventions. Reuse equivalent endpoints if they already exist.

### Authentication
```text
POST   /api/v1/auth/iam/login
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
POST   /api/v1/auth/change-password
```

### Users
```text
GET    /api/v1/iam/users
POST   /api/v1/iam/users
GET    /api/v1/iam/users/{user_id}
PATCH  /api/v1/iam/users/{user_id}
POST   /api/v1/iam/users/{user_id}/reset-password
DELETE /api/v1/iam/users/{user_id}
```

### Groups
```text
GET    /api/v1/iam/groups
POST   /api/v1/iam/groups
GET    /api/v1/iam/groups/{group_id}
PATCH  /api/v1/iam/groups/{group_id}
DELETE /api/v1/iam/groups/{group_id}
POST   /api/v1/iam/groups/{group_id}/users
DELETE /api/v1/iam/groups/{group_id}/users/{user_id}
```

### Policies
```text
GET    /api/v1/iam/policies
POST   /api/v1/iam/policies
GET    /api/v1/iam/policies/{policy_id}
PATCH  /api/v1/iam/policies/{policy_id}
DELETE /api/v1/iam/policies/{policy_id}
POST   /api/v1/iam/groups/{group_id}/policies
DELETE /api/v1/iam/groups/{group_id}/policies/{policy_id}
```

### Audit
```text
GET    /api/v1/iam/audit-logs
```

All endpoints must:
- Validate request/response data using Pydantic.
- Check authentication.
- Check the required permission.
- Enforce account ownership.
- Avoid returning password hashes, raw session tokens, or secrets.

## 13. Exact end-to-end demonstration scenario

The following scenario must work from the browser UI without manually editing the database:

1. Start Mini AWS.
2. Register a new owner account.
3. Sign in as the owner.
4. Open **Services → Identity & Access Management (IAM)**.
5. Open **Users → Create user**.
6. Create a user named `student1`.
7. Enable console access.
8. Set a temporary password and enable **Require password change at next sign-in**.
9. Create a group named `TEST`.
10. Open the policy selector and attach `ReadOnlyAccess`.
11. Open group `TEST`.
12. Click **Add users**.
13. Select `student1` and confirm.
14. Verify `student1` appears in the group member list.
15. Verify `ReadOnlyAccess` appears under attached policies.
16. Copy the Local Account ID.
17. Sign out of the owner account.
18. Open IAM user sign-in.
19. Enter Local Account ID, `student1`, and the temporary password.
20. Verify the application requires a password change.
21. Set and confirm a new password.
22. Verify the user reaches the console.
23. Verify read/list operations are allowed.
24. Attempt a create/update/delete action and verify the backend denies it with HTTP 403.
25. Sign out and sign back in as owner.
26. Verify the user, group, membership, policy attachment, and audit events still exist.
27. Restart the backend and verify persistence again.

The UI should make this flow straightforward to demonstrate in a classroom.

## 14. Security requirements

- Hash passwords with Argon2id, or bcrypt if already established in the project.
- Never store plaintext passwords.
- Never log passwords, password hashes, session tokens, or secrets.
- Use secure HTTP-only SameSite cookies where feasible.
- Protect cookie-authenticated state-changing requests against CSRF.
- Expire sessions and support revocation/logout.
- Rate-limit login attempts.
- Use generic authentication failure messages.
- Enforce account/tenant isolation in every database query and API.
- Enforce permissions server-side.
- Prevent IAM users from granting themselves permissions or modifying owner identities.
- Validate all request bodies and identifiers.
- Never request or store real AWS credentials.
- Keep local services bound to localhost by default.

## 15. Automated tests and acceptance criteria

The feature is not complete until tests verify:

### Accounts and users
- Registration generates a unique 12-digit account ID.
- Owner can create an IAM user.
- Duplicate username within an account is rejected.
- Same username in separate accounts is allowed.
- Password is hashed and never returned.
- Disabled-console and deactivated users cannot sign in.

### Groups and policies
- Owner can create groups.
- Duplicate group names within an account are rejected.
- Owner can add and remove users.
- Duplicate membership is prevented.
- Owner can attach and detach policies.
- Duplicate policy attachment is prevented.
- Deleting a group does not delete its users.

### Authentication
- Correct account ID, username, and password allow login.
- Incorrect credentials produce a generic error.
- First login forces password change.
- Normal console access is blocked until password change.
- New password works and temporary password no longer works.
- Logout ends/revokes the session.

### Authorization and isolation
- ReadOnly user can list resources.
- ReadOnly user cannot create, update, or delete resources.
- Missing permission returns HTTP 403.
- Cross-account access is rejected.
- IAM user cannot grant themselves permissions.
- Owner-only endpoints reject unauthorized IAM users.

### Audit and persistence
- Required operations create audit events.
- Audit events contain no secrets.
- Data survives application restart.
- Backend tests pass.
- Frontend production build passes.

## 16. Implementation phases for the coding agent

### Phase A — repository inspection and plan
- Read `AGENTS.md`, `README.md`, `PRD.md`, `ARCHITECTURE.md`, `DESIGN.md`, `RULES.md`, `SECURITY.md`, `DEVELOPMENT.md`, `TESTING.md`, `TRACKER.md`, and relevant `.agent/` files.
- Inspect actual frontend/backend structure, database, auth, routes, and tests.
- Identify reusable code and gaps.
- Write an implementation plan before editing.

### Phase B — database and authentication
- Add/adjust models and migrations.
- Implement account ID generation.
- Implement IAM login, sessions, logout, current-user endpoint, password reset, and mandatory first-login password change.
- Add tests.

### Phase C — IAM backend
- Implement user, group, policy, membership, attachment, and audit APIs.
- Implement centralized permission evaluation.
- Protect every endpoint and enforce account isolation.
- Add positive and negative authorization tests.

### Phase D — IAM frontend
- Implement IAM dashboard.
- Implement users list/create/details/edit.
- Implement groups list/create/details/member management.
- Implement policies list/details and attach/detach flows.
- Implement audit log.
- Implement IAM login and forced password-change screens.
- Connect every UI action to real backend endpoints.

### Phase E — end-to-end verification
- Complete every step in Section 13.
- Test with owner and restricted IAM user.
- Verify HTTP 403 for forbidden operations.
- Verify persistence after restart.
- Fix all failures.

### Phase F — documentation and delivery
Update:
- `README.md`
- `PRD.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `TESTING.md`
- `TRACKER.md`
- `.agent/STATE.md`
- `.agent/PLAN.md`
- `.agent/CURRENT_TASK.md`
- `.agent/DECISIONS.md`
- `.agent/TEST_RESULTS.md`
- `.agent/FILE_MAP.md`
- `.agent/CHANGELOG.md`

Do not mark a phase complete unless its tests pass.

## 17. Final instructions to the coding agent

This Markdown file is the complete source of requirements for this feature. **Do not depend on, search for, or ask the user to provide a PDF or practical document.**

Before coding:
1. Read this entire specification.
2. Inspect the actual repository and current implementation.
3. Compare existing features with the requirements.
4. Preserve working modules and follow the current architecture.
5. Present a concise plan and identify any conflicts.

Then implement the complete feature. Do not stop at static screens, placeholder buttons, mock APIs, or hardcoded data. All operations must work and persist.

At completion, report:
- Files created and modified.
- Database schema/migration changes.
- API endpoints implemented.
- Frontend pages and flows implemented.
- Security and authorization controls.
- Tests run and actual pass/fail results.
- Exact commands to start the application.
- Exact steps to demonstrate the IAM workflow.
- Remaining limitations or unfinished items.

**Definition of done:** A student can register an owner account, create an IAM user, create a group, attach policies, add the user to the group, sign in as that user, change the temporary password, and demonstrate allowed/denied actions. The implementation is persistent, secure for a local educational application, and covered by passing tests.
