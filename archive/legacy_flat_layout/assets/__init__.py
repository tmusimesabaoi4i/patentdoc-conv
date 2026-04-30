"""Static assets (CSS / JS) for the generated HTML viewers.

Files in this package are read at runtime via importlib.resources so that
they can be edited as plain text with proper editor support.
"""
from __future__ import annotations

from importlib import resources

ASSET_FILENAMES: tuple[str, ...] = (
    "common.css",
    "text_viewer.css",
    "text_viewer.js",
    "fig_viewer.css",
    "fig_viewer.js",
)


def read_asset(name: str) -> str:
    """Return the contents of a packaged asset file as a UTF-8 string."""
    return resources.files(__name__).joinpath(name).read_text(encoding="utf-8")
