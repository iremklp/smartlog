#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${ROOT_DIR}/reports/release"
REPORT_FILE="${REPORT_DIR}/cilt1-readiness.md"
ALLOW_DIRTY="false"

if [[ "${1:-}" == "--allow-dirty" ]]; then
  ALLOW_DIRTY="true"
fi

mkdir -p "${REPORT_DIR}"
cd "${ROOT_DIR}"

pass_count=0
fail_count=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "${cmd}" >/dev/null 2>&1; then
    echo "- [PASS] ${name}" >> "${REPORT_FILE}"
    pass_count=$((pass_count + 1))
  else
    echo "- [FAIL] ${name}" >> "${REPORT_FILE}"
    fail_count=$((fail_count + 1))
  fi
}

{
  echo "# Cilt 1 Release Readiness"
  echo
  echo "Generated at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "## Checklist"
} > "${REPORT_FILE}"

if [[ "${ALLOW_DIRTY}" == "true" ]]; then
  echo "- [INFO] Clean git check skipped (--allow-dirty)." >> "${REPORT_FILE}"
else
  check "Git working tree is clean" "[[ -z \"$(git status --short)\" ]]"
fi

check "Backend docs present" "[[ -s README.md ]]"
check "Architecture doc present" "[[ -s ARCHITECTURE.md ]]"
check "Roadmap doc present" "[[ -s PROJECT_ROADMAP.md ]]"
check "Development status doc present" "[[ -s DEVELOPMENT_STATUS.md ]]"
check "API contract generator script present" "[[ -x frontend/scripts/generate-openapi-contracts.sh ]]"
check "Containerfile present" "[[ -s Containerfile ]]"
check "Docker ignore present" "[[ -s .dockerignore ]]"
check "Security limits exist in options" "grep -q 'max_upload_bytes' src/log_parser_engine/application/options.py"
check "Frontend mode configuration exists" "grep -q 'LOG_PARSER_FRONTEND_MODE' src/log_parser_engine/api/app.py"

{
  echo
  echo "## Summary"
  echo
  echo "- Passed checks: ${pass_count}"
  echo "- Failed checks: ${fail_count}"
} >> "${REPORT_FILE}"

if [[ "${fail_count}" -gt 0 ]]; then
  exit 1
fi
