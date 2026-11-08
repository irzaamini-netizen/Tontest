#!/data/data/com.termux/files/usr/bin/bash
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST="$PREFIX/lib/tonsec"
BIN="$PREFIX/bin/tonsec"
[ ! -e "$DEST" ] && [ ! -e "$BIN" ] || { echo 'ERROR: install target exists; refusing overwrite.'; exit 1; }
mkdir -p "$DEST"; cp -R "$ROOT/tonsec/." "$DEST/"
cat > "$BIN" <<'LAUNCH'
#!/data/data/com.termux/files/usr/bin/bash
export PYTHONPATH="$PREFIX/lib${PYTHONPATH:+:$PYTHONPATH}"
exec python -m tonsec.cli "$@"
LAUNCH
chmod 700 "$BIN"
echo 'Installed TON Security Engine 0.2.0. Run: tonsec doctor'
