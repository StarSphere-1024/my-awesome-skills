#!/usr/bin/env bash
set -u

if [ $# -lt 1 ]; then
  echo "usage: $0 <executable> [args...]" >&2
  exit 2
fi

if ! command -v gdb >/dev/null 2>&1; then
  echo "error: gdb not found in PATH" >&2
  exit 127
fi

EXE="$1"
shift

mkdir -p .debug
LOG="${GDB_LOG:-.debug/gdb-crash-$$.log}"

GDB_ARGS=(-q -batch \
  -ex "set pagination off" \
  -ex "set print pretty on" \
  -ex "set print frame-arguments all" \
  -ex "set confirm off" \
  -ex "run" \
  -ex "echo \n\n===== FAILURE STATE =====\n" \
  -ex "info program" \
  -ex "echo \n\n===== CURRENT FRAME =====\n" \
  -ex "frame" \
  -ex "info args" \
  -ex "info locals" \
  -ex "list" \
  -ex "echo \n\n===== FIRST BACKTRACE =====\n" \
  -ex "bt full" \
  -ex "echo \n\n===== ALL THREADS BACKTRACE FULL =====\n" \
  -ex "thread apply all bt full" \
  -ex "echo \n\n===== REGISTERS =====\n" \
  -ex "info registers" \
  --args "$EXE" "$@")

if [ -n "${STDIN:-}" ]; then
  if [ ! -r "$STDIN" ]; then
    echo "error: STDIN file is not readable: $STDIN" >&2
    exit 2
  fi
  gdb "${GDB_ARGS[@]}" < "$STDIN" 2>&1 | tee "$LOG"
  status=${PIPESTATUS[0]}
else
  gdb "${GDB_ARGS[@]}" 2>&1 | tee "$LOG"
  status=${PIPESTATUS[0]}
fi

echo
echo "GDB log saved to: $LOG"
exit "$status"
