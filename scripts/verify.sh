#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv run --project backend pytest backend/tests -q
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:e2e
