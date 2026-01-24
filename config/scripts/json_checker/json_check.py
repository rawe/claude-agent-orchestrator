#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Validate whether a file contains valid JSON."""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check if a file is valid JSON")
    parser.add_argument("--file", required=True, help="Path to the file to validate")
    args = parser.parse_args()

    file_path = Path(args.file)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1

    if not file_path.is_file():
        print(f"Error: Not a file: {file_path}", file=sys.stderr)
        return 1

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json.load(f)
        print(f"Valid JSON: {file_path}")
        return 0
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}", file=sys.stderr)
        return 1
    except UnicodeDecodeError as e:
        print(f"Error: File encoding issue: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
