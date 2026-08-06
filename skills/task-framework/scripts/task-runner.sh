#!/bin/bash
# Task Runner — execute a command with timestamped stdout/stderr logging
# Usage: task-runner.sh <task-dir> <command...>
#
# Creates:
#   <task-dir>/output/logs/output.YYYYMMDD-HHMMSS.log
#   <task-dir>/output/logs/error.YYYYMMDD-HHMMSS.log
# stdout and stderr also go to terminal.
# Exit code preserved.

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <task-dir> <command...>" >&2
    exit 1
fi

TASK_DIR="$1"
shift

mkdir -p "$TASK_DIR/output/logs"

TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
OUTPUT_LOG="$TASK_DIR/output/logs/output.${TIMESTAMP}.log"
ERROR_LOG="$TASK_DIR/output/logs/error.${TIMESTAMP}.log"

# Header
echo "-------- $(date '+%Y-%m-%d %H:%M:%S') --------" > "$OUTPUT_LOG"
echo "-------- $(date '+%Y-%m-%d %H:%M:%S') --------" > "$ERROR_LOG"
echo "Command: $*" >> "$OUTPUT_LOG"
echo "Command: $*" >> "$ERROR_LOG"
echo "--------" >> "$OUTPUT_LOG"
echo "--------" >> "$ERROR_LOG"

# Run command with split tee
# stdout → both terminal and output log
# stderr → both terminal and error log
"$@" 2> >(tee "$ERROR_LOG" >&2) | tee "$OUTPUT_LOG"

EXIT_CODE=$?
echo "Exit code: $EXIT_CODE" | tee -a "$OUTPUT_LOG" | tee -a "$ERROR_LOG" >/dev/null
exit $EXIT_CODE
