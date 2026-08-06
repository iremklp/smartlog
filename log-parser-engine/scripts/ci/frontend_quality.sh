#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${ROOT_DIR}/reports/frontend"

mkdir -p "${REPORT_DIR}"
cd "${ROOT_DIR}/frontend"

npm ci --no-audit --prefer-offline
npm run typecheck
npm run lint
npm run format:check
npm run test -- --reporter=junit --outputFile "${REPORT_DIR}/vitest-junit.xml"
npm run build

ls -1 dist > "${REPORT_DIR}/dist-artifacts.txt"
