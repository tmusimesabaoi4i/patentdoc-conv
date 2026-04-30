"""Module entry point: ``python -m patentdoc_conv``.

Launches the tkinter GUI. There is no CLI in this build.

Uses an *absolute* import on purpose: this file is also used as the
PyInstaller entry script (``src/patentdoc_conv/__main__.py``). When
PyInstaller (or a direct ``python __main__.py`` invocation) runs the
file as a top-level script, there is no parent package, so a relative
import (``from .gui.main_window import main``) fails with::

    ImportError: attempted relative import with no known parent package

The absolute import below works in *all* of the following cases:

* ``python -m patentdoc_conv`` (run as a module)
* ``python src/patentdoc_conv/__main__.py`` (run as a script)
* PyInstaller-built ``PatentdocConv.exe`` (frozen)
"""
from __future__ import annotations

from patentdoc_conv.gui.main_window import main

if __name__ == "__main__":
    main()
