#!/usr/bin/env bash

set -x;
set -Eeuo pipefail
trap cleanup SIGINT SIGTERM ERR EXIT

cleanup() {
    rv=$?
    trap - SIGINT SIGTERM ERR EXIT

    echo "Exit code $rv"
    exit $rv
}

if [ -z "$1" ]; then
    echo "Usage: $0 <thread_id_or_url>"
    exit 1
fi

THREAD_INPUT=$1
THREAD_ID=""
# Extract thread ID from URL
if [[ $THREAD_INPUT =~ /status/([0-9]+) ]]; then
    THREAD_ID="${BASH_REMATCH[1]}"
else
    # Assuming the input is the ID itself if it doesn't match the URL pattern
    THREAD_ID="$THREAD_INPUT"
fi

RAW_OUTPUT="threads/thread_${THREAD_ID}.json"
TREE_OUTPUT="app/public/tree_${THREAD_ID}.json"

mkdir -p threads

python3 load_thread_async.py "$THREAD_INPUT" "$RAW_OUTPUT"
python3 thread_to_tree_grouped.py "$RAW_OUTPUT" "$TREE_OUTPUT"
open --background "http://localhost:5000/#${THREAD_ID}"
