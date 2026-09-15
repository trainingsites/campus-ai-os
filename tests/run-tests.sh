#!/usr/bin/env bash
# Campus AI OS kernel - one command, one PASS/FAIL line, exit code (5.2.0 Phase 1.7).
# Runs every fixture under tests/ against THIS tree (or KERNEL_SRC= another tree).
# Nothing here touches a live campus; fixtures copy the tree into a temp dir.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
KERNEL="${KERNEL_SRC:-$(cd "$HERE/.." && pwd)}"
export KERNEL_SRC="$KERNEL"
command -v python3 >/dev/null 2>&1 || { echo "FAIL: python3 not available"; exit 1; }
[ -f "$KERNEL/tools/package.py" ] || { echo "FAIL: not a kernel tree: $KERNEL"; exit 1; }

echo "kernel: $KERNEL"
OUT="$(python3 -m unittest discover -s "$HERE" -p 'test_*.py' 2>&1)"; RC=$?
echo "$OUT" | tail -n 12
RAN="$(echo "$OUT" | grep -oE '^Ran [0-9]+ tests?' | head -1)"
if [ "$RC" -eq 0 ]; then
  echo "PASS: ${RAN:-tests} - kernel fixtures green"
else
  echo "FAIL: ${RAN:-tests} - see above"
fi
exit $RC
