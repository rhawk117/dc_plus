#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies    = ["build"]
# ///
"""
Build an optimised wheel (Cython + mypyc) into dist/.
Usage:  ./scripts/release-wheel
"""
import os, subprocess, sys, pathlib

os.environ["USE_MYPYC"] = "1"      # flip the switch for build.py
dist = pathlib.Path("dist")
dist.mkdir(exist_ok=True)

sys.exit(subprocess.call(["uv", "build", "--wheel", "--out", str(dist)]))
