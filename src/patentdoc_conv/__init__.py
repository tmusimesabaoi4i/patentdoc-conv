"""patentdoc-conv - 審査用 TXT / IMG を一括 HTML・PDF 化する GUI アプリ。

公開エントリーポイント:

* :func:`patentdoc_conv.gui.main_window.main` - GUI 起動 (``python -m patentdoc_conv``)
* :func:`patentdoc_conv.core.service.run_build` - HTML/PDF を生成するオーケストレーション

PDF 生成には ReportLab を使用し、Playwright / Chromium は不要です。
"""
from __future__ import annotations

from .core import (
    FigDoc,
    FontNotFoundError,
    ImageDocument,
    TextDoc,
    TextDocument,
    build_html,
    build_report,
    generate_html,
    generate_image_pdfs,
    generate_text_pdfs,
    run_build,
)

__all__ = [
    "FigDoc",
    "FontNotFoundError",
    "ImageDocument",
    "TextDoc",
    "TextDocument",
    "build_html",
    "build_report",
    "generate_html",
    "generate_image_pdfs",
    "generate_text_pdfs",
    "run_build",
]

__version__ = "4.0.0"
