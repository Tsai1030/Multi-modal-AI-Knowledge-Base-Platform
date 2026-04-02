#!/bin/sh
set -eu

python /app/scripts/wait_for_dependencies.py
uv run alembic upgrade head

exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
