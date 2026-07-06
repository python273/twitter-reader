import gzip
import json
import os
import sys
from pathlib import Path

def migrate(directory):
    path = Path(directory)
    if not path.is_dir():
        print(f"Not a directory: {directory}", file=sys.stderr)
        sys.exit(1)

    files = sorted(list(path.glob("tree_*.json")) + list(path.glob("thread_*.json")))
    if not files:
        print("No tree_*.json or thread_*.json files found")
        return

    for f in files:
        gz_path = f.with_suffix(f.suffix + ".gz")
        if gz_path.exists():
            print(f"SKIP (already exists): {gz_path}")
            continue

        print(f"Compressing: {f.name} -> {gz_path.name}")
        with open(f, 'r', encoding='utf-8') as infile:
            data = json.load(infile)

        with gzip.open(gz_path, 'wt', encoding='utf-8') as outfile:
            json.dump(data, outfile, ensure_ascii=False, separators=(',', ':'))

        f.unlink()
        print(f"  Removed: {f.name}")

    print("Done")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <directory>", file=sys.stderr)
        sys.exit(1)
    migrate(sys.argv[1])
