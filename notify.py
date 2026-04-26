#!/usr/bin/env python3
"""
Recursively searches a directory for scrape folders containing major_updates.json
or minor_updates.json, combines their contents, and writes them to stdout.

Crash-resilience strategy:
  - .visited  is touched immediately before reading a directory, so a crash
              mid-read won't cause double-processing on re-run.
  - .processed is touched only after stdout output is complete, confirming the
              full pipeline succeeded for that directory.
  - On skip check, only .processed is consulted — a directory that has .visited
    but not .processed was interrupted and will be retried.
"""

import json
import sys
from pathlib import Path


def load_json_file(path: Path) -> list:
    """Load a JSON file, returning an empty list if the file is empty."""
    if path.stat().st_size == 0:
        print(f"Skipping empty file: {path}", file=sys.stderr)
        return []
    with path.open() as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def main(root_dir: str) -> None:
    root = Path(root_dir)
    if not root.is_dir():
        print(f"Error: '{root_dir}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    # Remove any stale .visited files from previous interrupted runs
    for visited_file in root.rglob(".visited"):
        visited_file.unlink()
        print(f"Cleared stale: {visited_file}", file=sys.stderr)

    all_major_updates = []
    all_minor_updates = []
    dirs_to_finalize = []

    # Walk all subdirectories, sorted for deterministic ordering
    for directory in sorted(root.rglob("*")):
        if not directory.is_dir():
            continue

        major_file = directory / "major_updates.json"
        minor_file = directory / "minor_updates.json"
        processed_file = directory / ".processed"

        # Skip if neither updates file exists, or already fully processed
        if not (major_file.exists() or minor_file.exists()):
            continue
        if processed_file.exists():
            continue

        # Touch .visited immediately — marks that we've started this directory.
        # If we crash before .processed is written, the next run will retry.
        visited_file = directory / ".visited"
        visited_file.touch()

        if major_file.exists():
            all_major_updates.extend(load_json_file(major_file))

        if minor_file.exists():
            all_minor_updates.extend(load_json_file(minor_file))

        dirs_to_finalize.append(directory)
        print(f"Read: {directory}", file=sys.stderr)

    if not all_major_updates:
        print("No major updates found.")
        return

    print("=== Major Updates ===")
    print(json.dumps(all_major_updates, indent=2))

    print("\n=== Minor Updates ===")
    print(json.dumps(all_minor_updates, indent=2))

    # stdout output is complete — now mark each directory as fully processed
    for directory in dirs_to_finalize:
        (directory / ".processed").touch()
        print(f"Finalized: {directory}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <scrapes_directory>", file=sys.stderr)
        sys.exit(1)

    main(sys.argv[1])