#!/usr/bin/env bash
# Build one venv per TTS engine. Idempotent — re-running just re-syncs.
#
# Why: the three engine extras (chatterbox, omnivoice, fish-speech) are
# declared mutually exclusive in pyproject.toml due to version-pin conflicts
# in their dependency trees. Each gets its own venv at .venv-<engine>/, and
# the supervisor selects which one is active by starting the matching
# tts@<engine>.service instance.
#
# Usage:
#   ./scripts/bootstrap-engines.sh                  # build all three
#   ./scripts/bootstrap-engines.sh chatterbox       # build just one
#   ./scripts/bootstrap-engines.sh chatterbox omnivoice
#
# Run from anywhere — this script cd's to the project root.

set -euo pipefail

ALL_ENGINES=(chatterbox omnivoice fish-speech)
ENGINES=("${@:-${ALL_ENGINES[@]}}")

project_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_root"

for engine in "${ENGINES[@]}"; do
    case "$engine" in
        chatterbox|omnivoice|fish-speech) ;;
        *) echo "Unknown engine: $engine. Valid: ${ALL_ENGINES[*]}" >&2; exit 2 ;;
    esac
done

for engine in "${ENGINES[@]}"; do
    venv=".venv-$engine"
    echo "===> Syncing $venv (extra: $engine)"
    UV_PROJECT_ENVIRONMENT="$venv" uv sync --extra "$engine"
    if [[ ! -x "$venv/bin/tts" ]]; then
        echo "FAIL: $venv/bin/tts not produced." >&2
        exit 1
    fi
    echo "     $venv/bin/tts ready."

    case "$engine" in
        fish-speech)
            echo "===> Fetching fish-speech model checkpoint"
            "$venv/bin/python" scripts/fetch_fish_speech_weights.py
            ;;
    esac
done

echo ""
echo "Done. Active engine is whichever tts@<engine>.service is started."
