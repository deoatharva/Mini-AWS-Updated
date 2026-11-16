# Architecture
- Frontend: React + Vite
- Backend: Python + FastAPI
- Metadata: SQLite through a repository/service layer
- Resource adapters: process-based compute, optional VirtualBox, local app runner, filesystem object storage, per-resource SQLite databases
- Communication: JSON REST API under `/api/v1`
- Local development only; bind services to localhost by default.
