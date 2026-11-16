# Test Results

## 2026-11-16 — Phase 1 verification

Environment: Windows, Python 3.13.17 (`backend/.venv`), Node.js 24.11.1,
npm 11.6.2.

### Backend unit/API tests

Command (from `backend/`):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Also verified from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -q .\tests\backend
```

Result: **8 passed**, 1 warning, ~2.2s (both invocations). Root and backend
`pytest.ini` files were added so discovery works from either directory.

`scripts/run_tests.ps1` was run after the final config change:
**8 passed + Vite build succeeded + "All checks passed."**

Warning: `StarletteDeprecationWarning: Using httpx with starlette.testclient is
deprecated; install httpx2 instead.` Non-failing dependency deprecation.

Tests cover:

- health 200 with connected database
- health 503 with unavailable database
- consistent 404 error envelope
- schema and data folder initialization
- bcrypt password hash/verify and malformed-hash fail-closed behavior
- bcrypt length limit
- session token randomness and HMAC hashing

### Real backend process

Command: started uvicorn on `127.0.0.1:8010`, then used `curl.exe`.

Result:

```text
GET /api/v1/health ->
{"status":"ok","service":"mini-aws-api","version":"0.1.0","mode":"local","database":"connected"}

GET /api/v1/missing ->
{"error":{"code":"not_found","message":"Not Found"}}
HTTP 404
```

Metadata database check after startup:

```text
tables: ['auth_sessions', 'users']
```

### Auth API smoke check (foundation validation, not Phase 2 sign-off)

Against a temporary database with dependency overrides:

```text
register: 201
me: 200
logout: 204
me after logout: 401
duplicate registration: 409
bad login: 401
```

This confirms bcrypt hashing, token issuance, session invalidation, and the
error envelope work together. Phase 2 still requires committed automated API
tests and frontend integration.

### Frontend production build

Command (from `frontend/`):

```powershell
npm run build
```

Result: Vite 6.4.6 built successfully; 1599 modules transformed; `dist/` created.

### Frontend dependency audit

```powershell
npm audit --audit-level=moderate
```

Result: `found 0 vulnerabilities` after upgrading `react-router-dom` to 7.18.5.

### Frontend dev server

Started `npm run dev`, requested `http://127.0.0.1:5173/`.

Result: HTTP 200 and page title `Mini AWS Console`.

### Windows setup script

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

Result: completed successfully; dependencies already satisfied; existing
`backend/.env` preserved.

All PowerShell scripts in `scripts/` were parsed with the PowerShell parser:
no syntax errors.

### Issue found and fixed

The initial scaffold installed `passlib 1.7.4` with `bcrypt 5.0.0`. Hashing
failed at runtime with `ValueError: password cannot be longer than 72 bytes`
inside passlib's backend detection. `app/core/security.py` now uses bcrypt
directly, `passlib` was removed from requirements, and the security tests above
verify real hashing and verification.

## 2026-11-16 — Phase 2 verification (accounts)

Commands:

```powershell
.\scripts\run_tests.ps1
```

Result: **17 backend tests passed**, **13 frontend tests passed**, Vite
production build succeeded, and the script printed `All checks passed.`

Real uvicorn API check on `127.0.0.1:8000` with a temporary account:

```text
register=201 user_id=1 email_match=True
me=200 name=E2E User email_match=True
logout=204 after_logout=401
cors_preflight=200 allow_origin=http://127.0.0.1:5173
cleanup_deleted_users=1
```

The temporary E2E account was removed afterward. The frontend dev server
returned HTTP 200 with the app root. A desktop browser was not connected to this
session, so UI workflows were verified with jsdom/Testing Library rather than a
real browser.

## 2026-11-16 — Phase 3 verification (compute)

Full checks after adding compute:

- Backend: `22 passed, 1 warning in 18.19s` (the warning is the non-failing
  Starlette/httpx deprecation).
- Frontend: `3 test files passed; 16 tests passed` in 12.55s.
- Production build: 1607 modules transformed successfully.
- `npm audit --audit-level=moderate`: `found 0 vulnerabilities`.

Real uvicorn lifecycle on `127.0.0.1:8000`:

```text
created=201 id=1 status=stopped adapter=process
started=200 status=running pid=20816 port=18000 url=http://127.0.0.1:18000/
health_status=ok health_instance=1 health_pid=20816 not_vm=True
logs_listening=True
stopped=200 status=stopped url_cleared=True endpoint_closed=True
deleted=204
```

The temporary account/session was removed afterward. No Python worker process
remained. Compute tests use real subprocesses, real localhost health requests,
real log files, and cleanup in fixtures; they do not fake running state.

## 2026-11-16 — Phase 4 verification (application deployment)

Full checks:

- Backend: **32 passed**, 1 warning (non-failing Starlette/httpx deprecation).
- Frontend: **5 files, 22 tests passed**, including 3 Applications workflow
  tests.
- Production build: 1607 modules transformed successfully.

Real uvicorn lifecycle on `127.0.0.1:8020` with a temporary account:

```text
register=201 user_id=2
created=201 id=1 status=stopped url=None
started=200 status=running pid=13716 port=19000 url=http://127.0.0.1:19000/
app_page=200 has_title=True has_template_marker=True
app_health=200 status=ok instance_id=1 not_vm=True
app_info=200 deployment_id=1 template=sample-web-app port=19000
logs=200 listening=True
stopped=200 status=stopped url=None port_closed=True
deleted=204
after_delete=404
```

The temporary account, deployment metadata, application data directory, and
API process were removed afterward; ports 8020 and 19000 were closed and no
application worker process remained.

## 2026-11-16 — Phase 6 verification (isolated databases)

Added 8 backend tests in `tests/backend/test_databases.py` covering creation,
validation, duplicates, authentication, ownership, schema inspection, real
CREATE/INSERT/SELECT execution, honest SQL errors, blocked ATTACH/DETACH/
PRAGMA/VACUUM and file-reading functions, the 200-row limit, BLOB labeling,
deletion of the SQLite file, and missing-file reporting.

Added 3 frontend tests in
`frontend/src/pages/databases/Databases.test.jsx` covering schema loading, a
real query result table, create/delete, and an honest SQL error path.

Full checks after the additions:

- Backend: **40 passed**, 1 warning, ~32s.
- Frontend: **6 files, 25 tests passed**, ~13s.
- Production build: 1607 modules transformed successfully.

Real uvicorn lifecycle on `127.0.0.1:8021` with a temporary account:

```text
register=201 user_id=1
created=201 id=1 engine=sqlite status=available tables=0
create_table=200 type=CREATE rows_affected=None
insert=200 rows_affected=1
select=200 columns=['id','title'] rows=[[1,'Verify isolated database']] truncated=False
tables=200 names=['tasks'] cols=['id','title']
attach_denied=422 code=sql_error
listed=200 table_count=1 status=available
deleted=204
after_delete=404
```

The temporary account and API process were removed afterward; no database
resource or SQLite file remained under `data/databases/` except `.gitkeep`.

Phase 5 (object storage) was verified by its 5 backend tests (real files on
disk, overwrite, path/name rejection, ownership, authenticated download) and 3
frontend Buckets workflow tests; those suites passed in the full runs above.

## 2026-11-16 — Phase 7 dashboard verification

Added `GET /api/v1/dashboard` with real counts and recent activity, plus 4
backend tests in `tests/backend/test_dashboard.py` and 3 frontend tests in
`frontend/src/pages/Dashboard.test.jsx`.

Full checks:

- Backend: **44 passed**, 1 warning, ~42s.
- Frontend: **7 files, 28 tests passed**, ~15s.
- Production build: 1607 modules transformed successfully.

Real uvicorn dashboard lifecycle on `127.0.0.1:8022` with a temporary account:

```text
empty_dashboard=200 counts all zero, activity=0
create_instance=201 stopped
start_instance=200 running url=http://127.0.0.1:18000/
create_app=201 stopped
create_bucket=201 dash-bucket
upload_object=201 notes.txt 16
create_database=201 sqlite
dashboard=200
counts={'compute_total':1,'compute_running':1,'applications_total':1,
        'applications_running':0,'buckets_total':1,'objects_total':1,
        'storage_bytes':16,'databases_total':1}
activity_count=5
  compute started Dash host 2026-11-16T09:06:40.361770Z
  applications deployed Dash app 2026-11-16T09:06:40Z
  storage created dash-bucket 2026-11-16T09:06:40Z
  storage uploaded dash-bucket/notes.txt 2026-11-16T09:06:40Z
  databases created Dash DB 2026-11-16T09:06:40Z
stop_instance=200 stopped
delete_app=204 delete_object=204 delete_bucket=204
 delete_database=204 delete_instance=204
final_counts all zero, final_activity=0
```

The temporary account and API process were removed afterward; every resource
table was empty and port 8022 was closed.

## 2026-11-16 — Practicals 11–15 end-to-end walkthrough

One live uvicorn instance on `127.0.0.1:8023` with a temporary account. Every
flow ran against the real API and real local processes/files.

```text
11 register=201 me=200 logout=204 me_after_logout=401 login=200
12 create_instance=201 start=running pid=21028 url=http://127.0.0.1:18000/
   worker_health=200 logs_listening=True stop=stopped url_cleared delete=204
13 deploy=201 start=running url=http://127.0.0.1:19000/
   page=200 (title + controlled-template marker) health=200 logs_listening=True
   stop=stopped delete=204
14 create_bucket=201 upload=201 (33 bytes) download=200 (bytes match)
   list=200 delete_object=204 delete_bucket=204
15 create_database=201 CREATE TABLE=200 INSERT rows_affected=2
   SELECT rows=[[1,'Ada'],[2,'Grace']] schema=students(2 columns)
   ATTACH denied=422 sql_error delete_database=204
   dashboard clean state: all counts zero, activity empty
```

Result: **30/30 walkthrough checks passed**, plus the separately confirmed
database deletion and clean dashboard state (the long inline script was
truncated by the shell before its final two checks, so they were rerun).

Cleanup confirmed afterward: temporary account removed, all five resource
tables empty, no Python worker processes remained, `data/` contained only
`.gitkeep` files, and port 8023 was closed.

## 2026-11-16 — Account self-service verification

Added display-name updates (`PATCH /auth/me`) and password changes
(`POST /auth/password`), plus 3 backend tests and 3 frontend Account tests.

Full checks:

- Backend: **47 passed**, 1 warning, ~62s.
- Frontend: **8 files, 31 tests passed**, ~22s.
- Production build: 1607 modules transformed successfully.

Live uvicorn workflow on `127.0.0.1:8024`:

```text
register=201, second_session=200
rename=200 (name='Renamed E2E', whitespace trimmed)
blank_name=422 validation_error
wrong_current_password=422 invalid_current_password
session_after_wrong_password=200 (still signed in)
change_password=204
current_session_after_change=200
other_session_after_change=401 (revoked)
old_password_login=401 invalid_credentials
new_password_login=200 (name='Renamed E2E')
ACCOUNT_E2E passed=11/11
```

Cleanup confirmed: temporary account deleted and port 8024 closed.

## 2026-11-16 — Durable activity history verification

Added `activity_events` and recorded resource actions from compute,
application, storage, and database services. Dashboard activity now reads this
log. Added 2 backend tests in `tests/backend/test_activity.py` and extended the
Dashboard test fixture with a deletion event.

Full checks:

- Backend: **49 passed**, 1 warning, ~52s.
- Frontend: **8 files, 31 tests passed**, ~20s.
- Production build: 1607 modules transformed successfully.

Live uvicorn workflow on `127.0.0.1:8025`:

```text
empty_history=True
bucket_created=201 object_uploaded=201 database_created=201
app_deployed=201 instance_created=201
activity_before_delete=5
object_delete=204 bucket_delete=204 database_delete=204
application_delete=204 instance_delete=204
counts_after_delete=all zero
activity_after_delete=10 events (history retained)
deletion_events=5
deleted_object_name=history-e2e/kept.txt retained
deleted_instance_name=History E2E host retained
ACTIVITY_E2E passed=18/18
```

Cleanup confirmed: the 10 test events cascaded away with the temporary
account, no activity rows remained, and port 8025 was closed.

