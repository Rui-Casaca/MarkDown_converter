"""Entry point used when building the standalone executable with PyInstaller."""

from __future__ import annotations

import sys

from doc2md.cli import main

if __name__ == "__main__":
    sys.exit(main())
