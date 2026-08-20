#!/usr/bin/env python3
"""Cross-platform cleanup helper used by `make clean`."""
import shutil
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]

TARGETS = [
    ROOT / ".venv",
    ROOT / "backend" / ".venv",
    ROOT / ".pytest_cache",
    ROOT / "backend" / ".pytest_cache",
    ROOT / "backend" / "data",
    ROOT / "data",
    ROOT / ".tmp",
    ROOT / "_pylibs",
    ROOT / ".mypy_cache",
    ROOT / ".ruff_cache",
]

def main():
    for t in TARGETS:
        shutil.rmtree(t, ignore_errors=True)
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d, ignore_errors=True)
    for f in list(ROOT.rglob("*.pyc")):
        try:
            f.unlink()
        except OSError:
            pass
    print("cleaned.")


if __name__ == "__main__":
    main()