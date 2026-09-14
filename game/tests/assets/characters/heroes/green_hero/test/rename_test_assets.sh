#!/bin/sh
# Keep this entry point usable from any working directory, including paths with spaces.
set -eu

test_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
repository_dir=$(CDPATH='' cd -- "$test_dir/../../../../../../.." && pwd)
importer="$repository_dir/game/tools/prepare_green_hero_test.py"

if [ -x "$repository_dir/.venv/bin/python" ]; then
    exec "$repository_dir/.venv/bin/python" "$importer" "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 "$importer" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$importer" "$@"
else
    printf '%s\n' 'Python 3.11+ is required. Install Python and run this script again.' >&2
    exit 1
fi
