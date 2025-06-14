from __future__ import annotations
import os, sys
from pathlib import Path
from setuptools import Extension, setup

try:
    from Cython.Build import cythonize

    CYTHON_EXTS = cythonize(
        [
            Extension(
                "metify._speedups",
                ["metify/_speedups.pyx"],
                extra_compile_args=(
                    ["/O2"] if sys.platform == "win32" else ["-O3", "-march=native", "-ffast-math"]
                ),
                language="c",
            )
        ],
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
            "wraparound": False,
            "cdivision": True,
            "initializedcheck": False,
            "nonecheck": False,
            "profile": False,
        },
    )
except ImportError:  # wheel install path
    CYTHON_EXTS = []

# ── mypyc (opt-in) ─────────────────────────────────────────────────────────────
try:
    from mypyc.build import mypycify
except ImportError:
    mypycify = None  # type: ignore[assignment]

USE_MYPYC = (
    "--use-mypyc" in sys.argv or os.getenv("USE_MYPYC") == "1"
) and mypycify is not None
if "--use-mypyc" in sys.argv:
    sys.argv.remove("--use-mypyc")

MYPYC_EXTS = []
if USE_MYPYC:
    targets = [
        str(p) for p in Path("metify").glob("*.py") if p.name != "__init__.py"
    ]
    MYPYC_EXTS = mypycify(targets, opt_level="3")

setup(ext_modules=CYTHON_EXTS + MYPYC_EXTS)
