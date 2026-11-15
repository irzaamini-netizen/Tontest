#!/usr/bin/env bash
# Safe baseline runner for TON Security Engine
# - Prepares dataset if needed
# - Runs tonsec in read-only mode
# - Never overwrites existing non-empty report directories

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DATASET="${ROOT}/tonsec_v020/benchmark/datasets/real_projects.json"
PROJECTS_DIR="${HOME}/tonsec-baseline-projects"
STAMP="$(date +%Y%m%d-%H%M%S)"
REPORT_DIR="${HOME}/tonsec-baseline-report-${STAMP}"

echo "=== TON Security Engine — Baseline Runner ==="
echo "Dataset     : ${DATASET}"
echo "Projects dir: ${PROJECTS_DIR}"
echo "Report dir  : ${REPORT_DIR}"
echo

if [[ ! -f "${DATASET}" ]]; then
  echo "ERROR: dataset not found: ${DATASET}" >&2
  exit 2
fi

echo "[1/3] Preparing dataset (shallow clones)..."
python3 "${ROOT}/tonsec_v020/benchmark/tools/prepare_dataset.py" \
  --dataset "${DATASET}" \
  --outdir "${PROJECTS_DIR}"

echo
echo "[2/3] Checking tonsec availability..."
if ! command -v tonsec >/dev/null 2>&1; then
  echo "WARNING: 'tonsec' not found in PATH."
  echo "Trying module form..."
  TONSEC_CMD=(python3 -m tonsec.cli)
else
  TONSEC_CMD=(tonsec)
fi

echo
echo "[3/3] Running baseline (read-only)..."
"${TONSEC_CMD[@]}" run "${PROJECTS_DIR}" --out "${REPORT_DIR}"

echo
echo "Baseline finished."
echo "Report directory: ${REPORT_DIR}"
echo "Please review full_report.json / full_report.md and share the summary."
