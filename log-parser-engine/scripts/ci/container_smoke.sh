#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${ROOT_DIR}/reports/container"
IMAGE_TAG="log-parser-engine:ci-smoke"
CONTAINER_NAME="log-parser-engine-ci-smoke"
PORT="18080"

mkdir -p "${REPORT_DIR}"
cd "${ROOT_DIR}"

RUNTIME=""
if command -v docker >/dev/null 2>&1; then
  RUNTIME="docker"
elif command -v podman >/dev/null 2>&1; then
  RUNTIME="podman"
fi

if [[ -z "${RUNTIME}" ]]; then
  echo "SKIPPED: docker/podman runtime not available" | tee "${REPORT_DIR}/container-smoke.txt"
  exit 0
fi

echo "Using runtime: ${RUNTIME}" | tee "${REPORT_DIR}/container-smoke.txt"
"${RUNTIME}" build -t "${IMAGE_TAG}" -f Containerfile . | tee -a "${REPORT_DIR}/container-smoke.txt"

CID=$("${RUNTIME}" run -d \
  --rm \
  --name "${CONTAINER_NAME}" \
  -p "${PORT}:8080" \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  "${IMAGE_TAG}")

cleanup() {
  "${RUNTIME}" rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/v1/health" >/dev/null; then
    echo "Health check passed" | tee -a "${REPORT_DIR}/container-smoke.txt"
    curl -fsSI "http://127.0.0.1:${PORT}/" | tee -a "${REPORT_DIR}/container-smoke.txt"
    exit 0
  fi
  sleep 1
done

echo "Container health check failed" | tee -a "${REPORT_DIR}/container-smoke.txt"
"${RUNTIME}" logs "${CID}" | tee -a "${REPORT_DIR}/container-smoke.txt"
exit 1
