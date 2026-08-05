#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="$(cd "${FRONTEND_DIR}/.." && pwd)"
SCHEMA_PATH="${FRONTEND_DIR}/src/lib/api/generated/openapi.schema.json"
TYPES_PATH="${FRONTEND_DIR}/src/lib/api/generated/openapi.ts"

mkdir -p "$(dirname "${SCHEMA_PATH}")"

cd "${BACKEND_DIR}"
poetry run python -c "from log_parser_engine.api.main import app; import json; print(json.dumps(app.openapi()))" > "${SCHEMA_PATH}"

cd "${FRONTEND_DIR}"
npx openapi-typescript "${SCHEMA_PATH}" -o "${TYPES_PATH}"

echo "OpenAPI schema and types generated."
