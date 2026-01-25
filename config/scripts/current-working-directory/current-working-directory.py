#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Print the current working directory."""

import os


def main() -> None:
    print(os.getcwd())


if __name__ == "__main__":
    main()
