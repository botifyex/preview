#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright==1.64.1"]
# ///
import sys

from capture.cli import main

if __name__ == "__main__":
    sys.exit(main())
