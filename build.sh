#!/usr/bin/env bash
# Builds the standalone LUBV Studio application on macOS and Linux.
set -e
cd "$(dirname "$0")"

PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
done

if [ -z "$PY" ]; then
    echo "  Python 3 was not found."
    exit 1
fi

exec "$PY" build_exe.py "$@"
