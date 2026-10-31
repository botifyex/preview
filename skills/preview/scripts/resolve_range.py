#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
import sys

from resolve_range.cli import main

if __name__ == "__main__":
    sys.exit(main())
