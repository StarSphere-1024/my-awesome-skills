#!/usr/bin/env bash
set -u

if [ $# -lt 1 ]; then
  echo "usage: $0 <executable> [args...]" >&2
  echo "env: BREAK=main STEPS=30 MODE=next|step|nexti|stepi" >&2
  exit 2
fi

if ! command -v gdb >/dev/null 2>&1; then
  echo "error: gdb not found in PATH" >&2
  exit 127
fi

EXE="$1"
shift

BREAK="${BREAK:-main}"
STEPS="${STEPS:-30}"
MODE="${MODE:-next}"

case "$MODE" in
  next|step|nexti|stepi) ;;
  *)
    echo "error: MODE must be one of: next, step, nexti, stepi" >&2
    exit 2
    ;;
esac

case "$STEPS" in
  ''|*[!0-9]*)
    echo "error: STEPS must be a positive integer" >&2
    exit 2
    ;;
esac

if [ "$STEPS" -lt 1 ] || [ "$STEPS" -gt 200 ]; then
  echo "error: STEPS must be between 1 and 200" >&2
  exit 2
fi

mkdir -p .debug
CMDS="${GDB_CMDS:-.debug/gdb-step-commands-$$.gdb}"
LOG="${GDB_LOG:-.debug/gdb-step-$$.log}"

{
  echo "set pagination off"
  echo "set print pretty on"
  echo "set print frame-arguments all"
  echo "set confirm off"
  echo "break $BREAK"
  echo "run"

  i=1
  while [ "$i" -le "$STEPS" ]; do
    echo "echo \\n\\n===== STEP $i BEFORE $MODE =====\\n"
    echo "frame"
    echo "list"
    echo "info args"
    echo "info locals"
    echo "bt 5"
    echo "$MODE"
    i=$((i + 1))
  done

  echo "echo \\n\\n===== FINAL STATE =====\\n"
  echo "frame"
  echo "info args"
  echo "info locals"
  echo "bt full"
} > "$CMDS"

gdb -q -batch -x "$CMDS" --args "$EXE" "$@" 2>&1 | tee "$LOG"
status=${PIPESTATUS[0]}

echo
echo "GDB command file: $CMDS"
echo "GDB log saved to: $LOG"
exit "$status"
