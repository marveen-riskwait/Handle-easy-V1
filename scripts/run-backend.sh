#!/usr/bin/env bash
# Dev launcher for the Flask API (SQLite, mock Odoo). Used by preview/launch.
set -e
cd "$(dirname "$0")/.."

export FLASK_APP=src/app.py
export FLASK_DEBUG=1
export PYTHONPATH=src
export FLASK_APP_KEY=dev-secret
export FRONTEND_URL=http://localhost:3000
export ODOO_MOCK=1
# Use the local SQLite DB created by `flask db upgrade` (no DATABASE_URL).
unset DATABASE_URL

exec .venv/bin/python src/app.py
