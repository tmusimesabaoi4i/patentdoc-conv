"""High level service used by the GUI.

This module is the *only* core entry point the GUI is expected to call
into. It composes document_loader, html_generator, pdf_generator and
exposes:

* :func:`run_build` -- end-to-end orchestration (HTML + PDF + report)
* :func:`build_html` -- HTML site generation only (legacy wrapper)
* :func:`build_report` -- write the JSON report
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path

from .document_loader import (
    ImageDocument,
    TextDocument,
    discover_files,
    load_image_documents,
    load_text_documents,
)
from .html_generator import generate_html
from .models import FigDoc, TextDoc
from .pdf_generator import generate_image_pdfs, generate_text_pdfs


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_html(
    base_dir: Path,
    text_files: list[Path],
    image_files: list[Path],
    overwrite: bool,
    encoding: str,
    auto_landscape: bool,
) -> tuple[list[TextDoc], list[FigDoc]]:
    """Legacy wrapper for HTML generation.

    Kept for backwards compatibility. Prefer using generate_html directly
    with TextDocument/ImageDocument objects.
    """
    text_docs = load_text_documents(text_files, encoding=encoding)
    image_docs = load_image_documents(image_files)
    return generate_html(base_dir, text_docs, image_docs, overwrite, auto_landscape)


def build_report(
    base_dir: Path,
    text_meta: list[TextDoc],
    fig_meta: list[FigDoc],
    pdf_results: list[dict],
    settings: dict,
    command: str = "",
) -> Path:
    """Write a JSON report summarizing the conversion."""
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_dir": str(base_dir),
        "command": command,
        "settings": settings,
        "text_count": len(text_meta),
        "figure_count": len(fig_meta),
        "texts": [asdict(d) for d in text_meta],
        "figures": [asdict(d) for d in fig_meta],
        "pdf_results": pdf_results,
    }
    _ensure_dir(base_dir / "PDF")
    out_path = base_dir / "PDF" / "conversion_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def run_build(
    base_dir: Path,
    *,
    run_mode: str = "all",
    overwrite: bool = True,
    encoding: str = "auto",
    skip_pdf: bool = False,
    clean: bool = False,
    pdf_image_orientation: str = "original",
    auto_landscape_html: bool = True,
    progress=None,
    command: str = "",
) -> tuple[list[TextDoc], list[FigDoc], list[dict]]:
    """Run the full HTML + PDF build for a base directory.

    ``progress`` is an optional callable ``(message: str) -> None`` used
    by the GUI to stream status updates back to its log panel.

    PDF generation uses ReportLab (no browser engine required).
    """

    def log(msg: str) -> None:
        if progress is not None:
            try:
                progress(msg)
            except Exception:
                pass

    if not base_dir.exists():
        raise FileNotFoundError(f"指定ディレクトリが存在しません: {base_dir}")

    txt_dir = base_dir / "TXT"
    img_dir = base_dir / "IMG"
    if not txt_dir.exists() and not img_dir.exists():
        raise FileNotFoundError(f"TXT または IMG ディレクトリが見つかりません: {base_dir}")

    if clean:
        import shutil
        for name in ("HTML", "PDF"):
            p = base_dir / name
            if p.exists():
                log(f"既存の {name}/ を削除します")
                shutil.rmtree(p)

    text_files, image_files = discover_files(base_dir)
    if run_mode == "text":
        image_files = []
    elif run_mode == "img":
        text_files = []
    log(f"TXT: {len(text_files)} files / IMG: {len(image_files)} files")

    text_docs = load_text_documents(text_files, encoding=encoding)
    image_docs = load_image_documents(image_files)

    log("HTML を生成中...")
    text_meta, fig_meta = generate_html(
        base_dir=base_dir,
        text_docs=text_docs,
        image_docs=image_docs,
        overwrite=overwrite,
        auto_landscape=auto_landscape_html,
    )
    log(f"HTML 作成完了: {base_dir / 'HTML'}")

    pdf_results: list[dict] = []
    if not skip_pdf:
        if text_docs:
            log("テキストPDFを生成中（ReportLab）...")
            pdf_results.extend(generate_text_pdfs(text_docs, base_dir, overwrite=overwrite))
        if image_docs:
            log("画像PDFを生成中（Pillow + ReportLab）...")
            pdf_results.extend(generate_image_pdfs(
                image_docs, base_dir, overwrite=overwrite, orientation=pdf_image_orientation
            ))

        errors = [r for r in pdf_results if r.get("status") == "error"]
        if errors:
            for e in errors:
                log(f"PDF ERROR: {e.get('source', '?')}: {e.get('reason', 'unknown')}")
        log(f"PDF 作成完了: {base_dir / 'PDF'}")
    else:
        log("PDF: skipped")

    settings = {
        "run_mode": run_mode,
        "overwrite": overwrite,
        "encoding": encoding,
        "skip_pdf": skip_pdf,
        "clean": clean,
        "pdf_image_orientation": pdf_image_orientation,
        "auto_landscape_html": auto_landscape_html,
    }
    build_report(base_dir, text_meta, fig_meta, pdf_results, settings, command=command)
    log(f"完了。Open: {(base_dir / 'HTML' / 'index_all.html').resolve()}")

    return text_meta, fig_meta, pdf_results
