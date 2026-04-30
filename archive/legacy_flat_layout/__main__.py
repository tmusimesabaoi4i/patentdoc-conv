"""Module entry point: ``python -m patentdoc_conv [...]``.

If no ``--dir`` argument is supplied, the GUI app is launched.
"""
from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
