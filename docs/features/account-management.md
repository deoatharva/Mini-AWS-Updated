# Account Management

- Register a local account
- Log in and log out
- Update the display name with `PATCH /auth/me`
- Change the password with `POST /auth/password`
  - Requires the current password; a wrong value returns 422
    `invalid_current_password` so the caller stays signed in.
  - Rejects reusing the current password with 422 `password_unchanged`.
  - Revokes every other session for the account; the calling session stays
    valid.
- Hash passwords securely
- Enforce authentication and resource ownership
- This is a local Mini AWS account, not an AWS account
