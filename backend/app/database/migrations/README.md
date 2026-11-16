# Metadata migrations

The local lab creates its SQLite metadata schema from the SQLAlchemy models at
backend startup (`Base.metadata.create_all`). This is sufficient while the
schema is still being introduced feature by feature.

Alembic is not enabled yet. When schema changes must preserve existing user
data, add Alembic and versioned migrations instead of editing database files by
hand.
