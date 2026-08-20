#!/bin/sh
set -e

# Run pending migrations before the app starts.
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000