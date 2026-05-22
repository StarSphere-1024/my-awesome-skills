#!/usr/bin/env bash
set -u

if [ $# -ne 2 ]; then
  echo "usage: $0 <executable> <core-file>" >&2
  exit 2
fi

if ! command -v gdb >/dev/null 2>&1; then
  echo "error: gdb not found in PATH" >&2
  exit 127
fi

EXE="$1"
CORE="$2"

mkdir -p .debug
LOG="${GDB_LOG:-.debug/gdb-core-$$.log}"

gdb -q -batch \
  -ex "set pagination off" \
  -ex "set print pretty on" \
  -ex "set print frame-arguments all" \
  -ex "echo \n\n===== CORE INFO =====\n" \
  -ex "info files" \
  -ex "echo \n\n===== CURRENT FRAME =====\n" \
  -ex "frame" \
  -ex "info args" \
  -ex "info locals" \
  -ex "echo \n\n===== BACKTRACE FULL =====\n" \
  -ex "bt full" \
  -ex "echo \n\n===== ALL THREADS BACKTRACE FULL =====\n" \
  -ex "thread apply all bt full" \
  "$EXE" "$CORE" 2>&1 | tee "$LOG"
status=${PIPESTATUS[0]}

echo
echo "GDB core log saved to: $LOG"
exit "$status"
