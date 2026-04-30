"""Module entry point: ``python -m patentdoc_conv``.

Launches the tkinter GUI. There is no CLI in this build.
"""
from __future__ import annotations

from .gui.main_window import main

if __name__ == "__main__":
    main()
