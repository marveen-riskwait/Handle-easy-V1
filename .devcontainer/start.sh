#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
export FLASK_APP=src/app.py ODOO_MOCK=1 DATABASE_URL=""
export FRONTEND_URL="https://${CODESPACE_NAME}-3000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
[ -d node_modules ] || npm install
python -c "import flask" 2>/dev/null || pip install --user -r requirements.txt
flask db upgrade
flask seed || true
pkill -f "src/app.py" 2>/dev/null || true
pkill -f "node_modules/.bin/vite" 2>/dev/null || true
sleep 1
nohup python src/app.py > .devcontainer/backend.log 2>&1 &
nohup npm run dev -- --host > .devcontainer/frontend.log 2>&1 &
echo "Handle Easy up on port 3000 — login admin@demo.com / demo1234"
