"""toHTML_PDF - 審査用 TXT / IMG 一括 HTML・PDF 化ツール。

公開エントリーポイント:

* ``patentdoc_conv.run_build`` - HTML/PDF を生成するオーケストレーション
* ``patentdoc_conv.cli.main``  - コマンドライン入口
* ``patentdoc_conv.gui.run_app`` - tkinter GUI アプリ
"""
from __future__ import annotations

from .builder import build_html, build_report, run_build
from .models import FigDoc, TextDoc

__all__ = [
    "FigDoc",
    "TextDoc",
    "build_html",
    "build_report",
    "run_build",
]

__version__ = "3.1.0"
