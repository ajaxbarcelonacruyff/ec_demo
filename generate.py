#!/usr/bin/env python3
"""Wrapper: delegates to src/generate.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from generate import main  # noqa: E402

if __name__ == "__main__":
    main()
