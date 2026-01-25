#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Hello World script that greets a user by name.
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Hello World script")
    parser.add_argument("--username", required=True, help="The username to greet")
    args = parser.parse_args()

    print(f"Hello, {args.username}!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
