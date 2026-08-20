#!/bin/sh
set -e

# Run pending migrations before the app starts.
alembic upgrade head

# Seed fixture data. Idempotent: safe to run on every startup.
python scripts/generate_fixtures.py seed

exec uvicorn app.main:app --host 0.0.0.0 --port 8000