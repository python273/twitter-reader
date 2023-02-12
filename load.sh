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

python3 load_thread_async.py $1
python3 thread_to_tree_grouped.py $1
mv tree_$1.json app/public/
open --background "http://localhost:5000/#$1"
