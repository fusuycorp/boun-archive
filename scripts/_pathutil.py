import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)


def add_import_paths() -> None:
    """Make `app` and top-level modules importable whether invoked from the
    container (cwd=/app) or local dev (cwd=repo root)."""
    cwd = os.getcwd()
    for p in (cwd, ROOT_DIR, os.path.join(ROOT_DIR, "backend"), os.path.join(cwd, "backend")):
        if os.path.exists(p) and p not in sys.path:
            sys.path.insert(0, p)
