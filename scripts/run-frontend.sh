#!/usr/bin/env bash
# Dev launcher for the Vite SPA. Used by preview/launch.
set -e
cd "$(dirname "$0")/.."
# Leave VITE_BACKEND_URL empty on purpose: the SPA calls same-origin "/api",
# and Vite proxies it to the backend (see vite.config.js). Works both locally
# and in Codespaces without CORS / cross-site cookie issues.
export VITE_BACKEND_URL=""
exec node_modules/.bin/vite --host --port 3000
