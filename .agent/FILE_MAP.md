# File Map

- `frontend/`: React UI
  - `src/routes/AppRoutes.jsx`: public and console routes
  - `src/layouts/ConsoleLayout.jsx`: top bar, sidebar, service navigation
  - `src/pages/`: live dashboard, auth, account, compute, deployment, storage, database pages
  - `src/pages/Dashboard.test.jsx`: summary counts and activity feed tests
  - `src/pages/Account.test.jsx`: display-name and password update tests
  - `src/styles/`: design tokens and global console styling
  - `vite.config.js`: localhost dev server on port 5173
- `backend/`: FastAPI application
  - `app/main.py`: app setup, CORS, lifespan, router mounting
  - `app/config.py`: environment settings and data directory paths
  - `app/database/session.py`: engine, session factory, SQLite foreign keys, init
  - `app/models/`: SQLAlchemy metadata models (`User`, `AuthSession`,
    `ActivityEvent`, `ComputeInstance`, `ApplicationDeployment`, `Bucket`,
    `StorageObject`, `DatabaseResource`)
  - `app/schemas/`: Pydantic request/response validation
  - `app/repositories/`: database access helpers
  - `app/services/auth_service.py`: registration, login, profile/password updates,
    and session lifecycle
  - `app/services/activity_service.py`: durable resource activity recording
  - `app/core/security.py`: bcrypt password hashing and session token hashing
  - `app/core/exceptions.py`: application errors and consistent JSON envelopes
  - `app/api/v1/`: health and auth routes
  - `app/adapters/`: local compute, deployment, storage, database adapters
  - `app/utils/`: time, process, port, and file validation helpers
- `pytest.ini`: root test discovery and `backend` import path
- `backend/pytest.ini`: backend-local test discovery (also supports `cd backend`)
- `tests/backend/`: isolated pytest suite
  - `conftest.py`: temporary metadata DB and dependency overrides
  - `test_health.py`: health success, degraded database, 404 envelope
  - `test_foundation.py`: schema and data folder initialization
  - `test_security.py`: password and session token behavior
  - `test_permissions.py`: resource ownership helper
  - `test_compute.py`: real worker lifecycle, ownership, and failure states
  - `test_applications.py`: real sample-app deployment lifecycle and cleanup
  - `test_storage.py`: real filesystem buckets, objects, and safety checks
  - `test_databases.py`: isolated SQLite files, safe SQL, and schema inspection
  - `test_dashboard.py`: real counts, activity, ownership, and auth
  - `test_activity.py`: history persistence, ordering, limits, and isolation
  - `test_auth.py`: registration, login, profile/password updates, and sessions
- `scripts/`: Windows setup, start, reset, and test scripts
- `data/`: metadata DB and real local resource files
- `docs/`: architecture and feature documentation
- `.agent/`: task state, plan, decisions, changelog, and test records
