#!/usr/bin/env python3
"""Wrapper: delegates to src/bigquery_load.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from bigquery_load import main  # noqa: E402

if __name__ == "__main__":
    main()
