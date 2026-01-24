#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""A test script for verification."""

import json
import sys


def main():
    print(json.dumps({"status": "ok", "args": sys.argv[1:]}))


if __name__ == "__main__":
    main()
