#!/usr/bin/env bash
# Dev launcher for the Vite SPA. Used by preview/launch.
set -e
cd "$(dirname "$0")/.."
export VITE_BACKEND_URL=http://localhost:3001
exec node_modules/.bin/vite --host --port 3000
