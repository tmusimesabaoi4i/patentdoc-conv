"""Static assets (CSS / JS) for the generated HTML viewers.

The files in this package are copied to the user's ``HTML/assets/`` tree
at build time. Reading is done through :func:`read_asset` so that the
same code path works for:

* an editable / installed package (``importlib.resources``)
* a frozen PyInstaller bundle (``sys._MEIPASS`` fallback)
* a plain source checkout (filesystem fallback via ``__file__``)
"""
from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path

ASSET_FILENAMES: tuple[str, ...] = (
    "common.css",
    "text_viewer.css",
    "text_viewer.js",
    "fig_viewer.css",
    "fig_viewer.js",
)


def _fallback_assets_dir() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled = Path(meipass) / "patentdoc_conv" / "assets"
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parent


def read_asset(name: str) -> str:
    """Return the contents of a packaged asset file as a UTF-8 string."""
    try:
        return resources.files(__name__).joinpath(name).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError, AttributeError, NotADirectoryError):
        return (_fallback_assets_dir() / name).read_text(encoding="utf-8")
