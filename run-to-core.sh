#!/bin/bash
# Linux and Steam Deck. In Desktop Mode you can double-click this,
# or run it from a terminal.
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required but was not found."
    exit 1
fi

exec python3 core_run.py --app "$@"
