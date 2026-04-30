"""Core (non-UI) business logic for patentdoc_conv.

This package contains everything that the GUI calls into to produce the
HTML viewers and PDF outputs. It must not import from
:mod:`patentdoc_conv.gui` so that headless usage stays cheap.
"""
from __future__ import annotations

from .document_loader import (
    ImageDocument,
    TextDocument,
    discover_files,
    load_image_documents,
    load_text_documents,
)
from .html_generator import generate_html
from .models import FigDoc, TextDoc
from .pdf_generator import (
    FontNotFoundError,
    generate_image_pdf,
    generate_image_pdfs,
    generate_text_pdf,
    generate_text_pdfs,
)
from .service import build_html, build_report, run_build

__all__ = [
    "FigDoc",
    "FontNotFoundError",
    "ImageDocument",
    "TextDoc",
    "TextDocument",
    "build_html",
    "build_report",
    "discover_files",
    "generate_html",
    "generate_image_pdf",
    "generate_image_pdfs",
    "generate_text_pdf",
    "generate_text_pdfs",
    "load_image_documents",
    "load_text_documents",
    "run_build",
]
