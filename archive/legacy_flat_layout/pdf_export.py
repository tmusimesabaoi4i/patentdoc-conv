"""PDF generation backends.

Text PDFs are produced by rendering the existing HTML viewer pages with a
headless Chromium (Playwright) so the output matches the on-screen view.
Image PDFs are produced directly from the source images via Pillow.
"""
from __future__ import annotations

from pathlib import Path

from .models import FigDoc, TextDoc
from .utils import ensure_dir


def make_text_pdfs_with_playwright(
    base_dir: Path,
    text_docs: list[TextDoc],
    overwrite: bool,
    timeout_ms: int = 120_000,
) -> list[dict]:
    results: list[dict] = []
    if not text_docs:
        return results
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return [{"type": "text_pdf", "status": "skipped", "reason": f"playwright import failed: {e}"}]

    html_root = base_dir / "HTML"
    pdf_root = base_dir / "PDF" / "text"
    ensure_dir(pdf_root)

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e:
                return [{
                    "type": "text_pdf",
                    "status": "skipped",
                    "reason": "Chromium launch failed. Run: python -m playwright install chromium",
                    "detail": str(e),
                }]
            page = browser.new_page(viewport={"width": 1280, "height": 1800}, device_scale_factor=1)
            for doc in text_docs:
                out_pdf = base_dir / "PDF" / doc.pdf_rel
                if out_pdf.exists() and not overwrite:
                    results.append({"source": doc.source_path, "pdf": str(out_pdf), "status": "exists_skipped"})
                    continue
                ensure_dir(out_pdf.parent)
                src_html = html_root / doc.html_rel
                try:
                    page.goto(src_html.resolve().as_uri(), wait_until="networkidle", timeout=timeout_ms)
                    page.pdf(
                        path=str(out_pdf),
                        format="A4",
                        print_background=True,
                        margin={"top": "16mm", "right": "14mm", "bottom": "16mm", "left": "14mm"},
                        prefer_css_page_size=False,
                    )
                    results.append({"source": doc.source_path, "pdf": str(out_pdf), "status": "ok"})
                except Exception as e:
                    results.append({"source": doc.source_path, "pdf": str(out_pdf), "status": "error", "reason": str(e)})
            browser.close()
    except Exception as e:
        return [{"type": "text_pdf", "status": "skipped", "reason": str(e)}]
    return results


def make_image_pdfs(
    base_dir: Path,
    fig_docs: list[FigDoc],
    overwrite: bool,
    orientation: str = "original",
) -> list[dict]:
    results: list[dict] = []
    if not fig_docs:
        return results
    try:
        from PIL import Image, ImageOps
    except Exception as e:
        return [{"type": "fig_pdf", "status": "skipped", "reason": f"Pillow import failed: {e}"}]

    for fig in fig_docs:
        src = Path(fig.source_path)
        out_pdf = base_dir / "PDF" / fig.pdf_rel
        if out_pdf.exists() and not overwrite:
            results.append({"source": str(src), "pdf": str(out_pdf), "status": "exists_skipped"})
            continue
        ensure_dir(out_pdf.parent)
        try:
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im)
                if orientation == "landscape" and im.height > im.width:
                    im = im.rotate(90, expand=True)
                if im.mode in ("RGBA", "LA"):
                    bg = Image.new("RGB", im.size, "white")
                    bg.paste(im, mask=im.split()[-1])
                    im = bg
                else:
                    im = im.convert("RGB")
                im.save(out_pdf, "PDF", resolution=150.0)
            results.append({"source": str(src), "pdf": str(out_pdf), "status": "ok"})
        except Exception as e:
            results.append({"source": str(src), "pdf": str(out_pdf), "status": "error", "reason": str(e)})
    return results
