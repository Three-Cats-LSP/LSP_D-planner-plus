#!/usr/bin/env python3
"""Compatibility entrypoint for the registry-driven audit platform."""
from __future__ import annotations

import sys

from tools.audit.cli import main


if __name__ == "__main__":
    args = sys.argv[1:]
    # Legacy callers may still pass index.html. The new audit discovers sources
    # from the registry, so the positional path is no longer needed.
    if args and args[0].lower().endswith(".html"):
        args = args[1:]
    raise SystemExit(main(["check", "--profile", "static", *args]))
