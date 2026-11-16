# Activity History

- Every user-visible resource action is stored in `activity_events` under the
  account that performed it.
- Recorded actions: bucket/object/database/compute/application created,
  deployed, uploaded, started, stopped, failed, and deleted.
- Events are written in the same transaction as the resource change, so an
  action that rolls back does not appear in history.
- History survives resource deletion and account isolation is enforced by
  `user_id`.
- `GET /api/v1/dashboard` returns the 10 newest events, newest first.
- Deleting an account cascades to its activity events.
