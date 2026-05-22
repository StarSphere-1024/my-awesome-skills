#!/usr/bin/env bash
set -u

if ! command -v gdb >/dev/null 2>&1; then
  echo "error: gdb not found in PATH" >&2
  exit 127
fi

usage() {
  echo "usage: $0 <executable> [args...]" >&2
  echo "or:    PID=<pid> $0 [matching-executable]" >&2
  echo "env:   SNAPSHOTS=2 INTERVAL=2 STARTUP_DELAY=2 GDB_TIMEOUT=20" >&2
  echo "       BT_COMMAND='thread apply all bt full' FRAME_ARGS=all|scalars|none" >&2
}

PID="${PID:-}"
SNAPSHOTS="${SNAPSHOTS:-2}"
INTERVAL="${INTERVAL:-2}"
STARTUP_DELAY="${STARTUP_DELAY:-2}"
GDB_TIMEOUT="${GDB_TIMEOUT:-20}"
PRESERVE_PROCESS="${PRESERVE_PROCESS:-0}"
BT_COMMAND="${BT_COMMAND:-thread apply all bt full}"
FRAME_ARGS="${FRAME_ARGS:-all}"

case "$SNAPSHOTS" in
  ''|*[!0-9]*)
    echo "error: SNAPSHOTS must be a positive integer" >&2
    exit 2
    ;;
esac

if [ "$SNAPSHOTS" -lt 1 ] || [ "$SNAPSHOTS" -gt 20 ]; then
  echo "error: SNAPSHOTS must be between 1 and 20" >&2
  exit 2
fi

mkdir -p .debug
LOG="${GDB_LOG:-.debug/gdb-hang-$$.log}"
: > "$LOG"

LAUNCHED=0
EXE=""

cleanup() {
  if [ "$LAUNCHED" -eq 1 ] && [ "$PRESERVE_PROCESS" != "1" ]; then
    if kill -0 "$PID" >/dev/null 2>&1; then
      kill "$PID" >/dev/null 2>&1 || true
    fi
  fi
}
trap cleanup EXIT

run_gdb_snapshot() {
  local -a gdb_args

  gdb_args=(-q -batch
    -ex "set pagination off"
    -ex "set print pretty on"
    -ex "set print frame-arguments $FRAME_ARGS"
    -ex "attach $PID"
    -ex "echo \n\n===== THREADS =====\n"
    -ex "info threads"
    -ex "echo \n\n===== ALL THREADS BACKTRACE =====\n"
    -ex "$BT_COMMAND"
    -ex "echo \n\n===== CURRENT FRAME =====\n"
    -ex "frame"
    -ex "info args"
    -ex "info locals"
    -ex "detach")

  if [ -n "$EXE" ]; then
    gdb_args+=("$EXE")
  fi

  timeout "$GDB_TIMEOUT" gdb "${gdb_args[@]}" 2>&1 | tee -a "$LOG"
  return "${PIPESTATUS[0]}"
}

if [ -z "$PID" ]; then
  if [ $# -lt 1 ]; then
    usage
    exit 2
  fi

  EXE="$1"
  shift
  "$EXE" "$@" >/dev/null 2>&1 &
  PID="$!"
  LAUNCHED=1
  sleep "$STARTUP_DELAY"
else
  EXE="${1:-}"
fi

if ! kill -0 "$PID" >/dev/null 2>&1; then
  echo "error: process $PID is not running" >&2
  exit 1
fi

i=1
while [ "$i" -le "$SNAPSHOTS" ]; do
  {
    echo
    echo "===== HANG SNAPSHOT $i/$SNAPSHOTS: PID $PID ====="
    date -Is
  } | tee -a "$LOG"

  run_gdb_snapshot
  status=$?

  if [ "$status" -eq 124 ]; then
    echo "warning: gdb snapshot timed out after ${GDB_TIMEOUT}s" | tee -a "$LOG"
  fi

  if [ "$i" -lt "$SNAPSHOTS" ]; then
    sleep "$INTERVAL"
  fi
  i=$((i + 1))
done

echo
echo "GDB hang log saved to: $LOG"
