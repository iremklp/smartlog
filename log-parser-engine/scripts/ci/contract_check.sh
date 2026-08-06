#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${ROOT_DIR}/reports/contract"

mkdir -p "${REPORT_DIR}"
cd "${ROOT_DIR}/frontend"

npm run contract:check | tee "${REPORT_DIR}/contract-check.txt"
