#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${ROOT_DIR}/reports/backend"

mkdir -p "${REPORT_DIR}"
cd "${ROOT_DIR}"

poetry install --no-interaction
poetry run pytest \
  --junitxml "${REPORT_DIR}/pytest.xml" \
  --cov=log_parser_engine \
  --cov-report=term-missing \
  --cov-report=xml:"${REPORT_DIR}/coverage.xml"
poetry run ruff check .
poetry run mypy src
poetry build

ls -1 dist > "${REPORT_DIR}/build-artifacts.txt"
