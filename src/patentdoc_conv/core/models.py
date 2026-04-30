"""Data models used across the package."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TextDoc:
    source_path: str
    title: str
    html_rel: str
    pdf_rel: str
    encoding: str
    char_count: int
    line_count: int


@dataclass
class FigDoc:
    source_path: str
    title: str
    html_rel: str
    pdf_rel: str
    asset_rel_from_html_root: str
    width: Optional[int]
    height: Optional[int]
