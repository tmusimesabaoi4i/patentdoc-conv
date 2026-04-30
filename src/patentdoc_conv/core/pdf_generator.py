"""PDF generator using ReportLab.

Generates PDFs directly from TextDocument and ImageDocument objects
without requiring a browser engine. Japanese fonts are loaded from
the Windows system fonts directory.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from .document_loader import ImageDocument, TextDocument, safe_stem


PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_TOP = 20 * mm
MARGIN_BOTTOM = 20 * mm
MARGIN_LEFT = 18 * mm
MARGIN_RIGHT = 18 * mm
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
CONTENT_HEIGHT = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM


class FontNotFoundError(Exception):
    """Raised when no suitable Japanese font is found."""
    pass


_FONT_REGISTERED = False
_FONT_NAME = "JapaneseFont"


def _find_japanese_font() -> Optional[Path]:
    """Search for a Japanese TrueType font on the system."""
    candidates = [
        Path(r"C:\Windows\Fonts\YuGothM.ttc"),
        Path(r"C:\Windows\Fonts\YuGothR.ttc"),
        Path(r"C:\Windows\Fonts\yugothic.ttf"),
        Path(r"C:\Windows\Fonts\meiryo.ttc"),
        Path(r"C:\Windows\Fonts\msgothic.ttc"),
        Path(r"C:\Windows\Fonts\msmincho.ttc"),
    ]
    fonts_dir_env = os.environ.get("WINDIR", r"C:\Windows")
    fonts_dir = Path(fonts_dir_env) / "Fonts"
    if fonts_dir.exists():
        for c in candidates:
            if c.exists():
                return c
        for pattern in ["Yu*.ttc", "Yu*.ttf", "meiryo*.ttc", "msgothic*.ttc"]:
            for f in fonts_dir.glob(pattern):
                return f
    return None


def _register_font() -> None:
    """Register a Japanese font with ReportLab (once per process)."""
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return

    font_path = _find_japanese_font()
    if font_path is None:
        raise FontNotFoundError(
            "日本語フォントが見つかりません。\n"
            "Windows環境では C:\\Windows\\Fonts に Yu Gothic / Meiryo / MS Gothic が必要です。"
        )

    try:
        pdfmetrics.registerFont(TTFont(_FONT_NAME, str(font_path), subfontIndex=0))
    except Exception as e:
        raise FontNotFoundError(f"フォント登録に失敗しました: {font_path}\n{e}") from e

    _FONT_REGISTERED = True


def _make_styles() -> dict:
    """Create paragraph styles for the PDF."""
    _register_font()
    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "JpTitle",
        parent=base["Title"],
        fontName=_FONT_NAME,
        fontSize=14,
        leading=20,
        spaceAfter=12,
    )
    body_style = ParagraphStyle(
        "JpBody",
        parent=base["Normal"],
        fontName=_FONT_NAME,
        fontSize=10,
        leading=16,
        spaceAfter=6,
        wordWrap="CJK",
    )
    return {"title": title_style, "body": body_style}


def _add_page_number(canvas, doc):
    """Draw page number at the bottom center of each page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    page_num = canvas.getPageNumber()
    text = f"- {page_num} -"
    canvas.drawCentredString(PAGE_WIDTH / 2, 12 * mm, text)
    canvas.restoreState()


def generate_text_pdf(
    doc: TextDocument,
    output_path: Path,
    overwrite: bool = True,
) -> dict:
    """Generate a PDF from a single TextDocument.

    Returns a result dict with keys: source, pdf, status, (reason).
    """
    if output_path.exists() and not overwrite:
        return {"source": str(doc.source_path), "pdf": str(output_path), "status": "exists_skipped"}

    try:
        styles = _make_styles()
    except FontNotFoundError as e:
        return {"source": str(doc.source_path), "pdf": str(output_path), "status": "error", "reason": str(e)}

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        pdf_doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
        )

        story = []
        story.append(Paragraph(_escape_xml(doc.title), styles["title"]))
        story.append(Spacer(1, 6 * mm))

        for line in doc.content.splitlines():
            if line.strip():
                story.append(Paragraph(_escape_xml(line), styles["body"]))
            else:
                story.append(Spacer(1, 4 * mm))

        pdf_doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
        return {"source": str(doc.source_path), "pdf": str(output_path), "status": "ok"}

    except Exception as e:
        return {"source": str(doc.source_path), "pdf": str(output_path), "status": "error", "reason": str(e)}


def generate_image_pdf(
    doc: ImageDocument,
    output_path: Path,
    overwrite: bool = True,
    orientation: str = "original",
) -> dict:
    """Generate a PDF from a single ImageDocument.

    Returns a result dict with keys: source, pdf, status, (reason).
    """
    if output_path.exists() and not overwrite:
        return {"source": str(doc.source_path), "pdf": str(output_path), "status": "exists_skipped"}

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image, ImageOps

        with Image.open(doc.source_path) as im:
            im = ImageOps.exif_transpose(im)
            img_w, img_h = im.size

            if orientation == "landscape" and img_h > img_w:
                im = im.rotate(90, expand=True)
                img_w, img_h = im.size

            if im.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", im.size, "white")
                bg.paste(im, mask=im.split()[-1])
                im = bg
            else:
                im = im.convert("RGB")

            temp_path = output_path.with_suffix(".tmp.jpg")
            im.save(temp_path, "JPEG", quality=95)

        scale = min(CONTENT_WIDTH / img_w, CONTENT_HEIGHT / img_h, 1.0)
        draw_w = img_w * scale
        draw_h = img_h * scale

        try:
            _register_font()
            styles = _make_styles()
        except FontNotFoundError:
            styles = None

        pdf_doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
        )

        story = []
        if styles:
            story.append(Paragraph(_escape_xml(doc.title), styles["title"]))
            story.append(Spacer(1, 4 * mm))
        story.append(RLImage(str(temp_path), width=draw_w, height=draw_h))

        pdf_doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)

        if temp_path.exists():
            temp_path.unlink()

        return {"source": str(doc.source_path), "pdf": str(output_path), "status": "ok"}

    except Exception as e:
        return {"source": str(doc.source_path), "pdf": str(output_path), "status": "error", "reason": str(e)}


def generate_text_pdfs(
    text_docs: list[TextDocument],
    base_dir: Path,
    overwrite: bool = True,
) -> list[dict]:
    """Generate PDFs for multiple text documents."""
    results = []
    pdf_dir = base_dir / "PDF" / "text"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    for doc in text_docs:
        stem = safe_stem(doc.source_path)
        out_path = pdf_dir / f"{stem}.pdf"
        results.append(generate_text_pdf(doc, out_path, overwrite))

    return results


def generate_image_pdfs(
    image_docs: list[ImageDocument],
    base_dir: Path,
    overwrite: bool = True,
    orientation: str = "original",
) -> list[dict]:
    """Generate PDFs for multiple image documents."""
    results = []
    pdf_dir = base_dir / "PDF" / "fig"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    for doc in image_docs:
        stem = safe_stem(doc.source_path)
        out_path = pdf_dir / f"{stem}.pdf"
        results.append(generate_image_pdf(doc, out_path, overwrite, orientation))

    return results


def _escape_xml(text: str) -> str:
    """Escape XML special characters for ReportLab Paragraph."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
