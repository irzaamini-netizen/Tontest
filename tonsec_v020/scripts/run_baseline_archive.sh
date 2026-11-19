#!/data/data/com.termux/files/usr/bin/bash
# Archive baseline for pinned real projects using current tonsec install.
set -euo pipefail
ROOT="${1:-$HOME/tonsec-real-projects}"
OUT="${2:-$HOME/tonsec-baseline-archive-$(date +%Y%m%d-%H%M%S)}"
if [ ! -d "$ROOT" ]; then
  echo "missing projects dir: $ROOT" >&2
  exit 1
fi
mkdir -p "$(dirname "$OUT")"
tonsec doctor
tonsec run "$ROOT" --out "$OUT"
echo "BASELINE_OUT=$OUT"
if [ -f "$OUT/batch_report.md" ]; then
  sed -n '1,80p' "$OUT/batch_report.md"
elif [ -f "$OUT/full_report.md" ]; then
  sed -n '1,80p' "$OUT/full_report.md"
else
  ls -la "$OUT"
fi
