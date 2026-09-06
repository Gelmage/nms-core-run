#!/bin/bash
# Double-click this to start The Run To Core.
# Recent macOS versions ship no Python, so check before blaming the tool.
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    echo
    echo "  Python is not installed, and this tool needs it."
    echo
    echo "  Get it from   https://www.python.org/downloads/"
    echo "  Then double-click this file again."
    echo
    read -r -p "Press return to close."
    exit 1
fi

python3 core_run.py --app "$@"
