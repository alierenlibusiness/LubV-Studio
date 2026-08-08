#!/usr/bin/env bash
# Launches LUBV Studio from source on macOS and Linux.
set -e
cd "$(dirname "$0")"

PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
done

if [ -z "$PY" ]; then
    echo
    echo "  Python 3 was not found."
    echo "  macOS:  brew install python"
    echo "  Linux:  use your package manager"
    echo
    exit 1
fi

if ! "$PY" -c "import PySide6, requests" >/dev/null 2>&1; then
    echo "  First run: installing dependencies, this may take a minute..."
    "$PY" -m pip install --disable-pip-version-check -r requirements.txt
fi

exec "$PY" -m lubv_studio "$@"
