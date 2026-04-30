"""HTML site builder.

Reads ``TXT/`` and ``IMG/`` from the user's directory and produces a
self-contained ``HTML/`` tree whose pages can be opened from
``file:///.../HTML/index_all.html``.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from typing import Optional

from .assets import ASSET_FILENAMES, read_asset
from .models import FigDoc, TextDoc
from .templates import fig_viewer_html, index_all_html, text_viewer_html
from .utils import (
    b64_text,
    copy_asset,
    discover_files,
    ensure_dir,
    image_size,
    read_text_auto,
    safe_stem,
    write_text,
)


def _write_assets(html_dir: Path, overwrite: bool) -> None:
    assets_dir = html_dir / "assets"
    for name in ASSET_FILENAMES:
        write_text(assets_dir / name, read_asset(name), overwrite)


def build_html(
    base_dir: Path,
    text_files: list[Path],
    image_files: list[Path],
    overwrite: bool,
    encoding: str,
    auto_landscape: bool,
) -> tuple[list[TextDoc], list[FigDoc]]:
    html_dir = base_dir / "HTML"
    text_html_dir = html_dir / "text"
    fig_html_dir = html_dir / "fig"
    img_asset_dir = html_dir / "assets" / "img"
    ensure_dir(text_html_dir)
    ensure_dir(fig_html_dir)
    ensure_dir(img_asset_dir)
    _write_assets(html_dir, overwrite=overwrite)

    text_docs: list[TextDoc] = []
    raw_texts: list[str] = []
    for src in text_files:
        text, enc = read_text_auto(src, preferred=encoding)
        raw_texts.append(text)
        stem = safe_stem(src)
        text_docs.append(TextDoc(
            source_path=str(src),
            title=src.stem,
            html_rel=f"text/{stem}.html",
            pdf_rel=f"text/{stem}.pdf",
            encoding=enc,
            char_count=len(text),
            line_count=len(text.splitlines()) if text else 0,
        ))

    text_nav = [{"title": d.title, "href": Path(d.html_rel).name} for d in text_docs]
    for idx, (doc, raw) in enumerate(zip(text_docs, raw_texts)):
        docs: list[dict] = []
        for i, nav in enumerate(text_nav):
            item: dict = {"title": nav["title"], "href": nav["href"]}
            if i == idx:
                item["b64"] = b64_text(raw)
            docs.append(item)
        page_data = {"title": doc.title, "currentIndex": idx, "docs": docs}
        write_text(html_dir / doc.html_rel, text_viewer_html(page_data, "../assets"), overwrite)

    index_text_docs = [
        {"title": d.title, "href": d.html_rel, "b64": b64_text(raw)}
        for d, raw in zip(text_docs, raw_texts)
    ]
    write_text(
        html_dir / "index_text.html",
        text_viewer_html({"title": "index_text", "currentIndex": 0, "docs": index_text_docs}, "assets"),
        overwrite,
    )

    fig_docs: list[FigDoc] = []
    used_asset_names: set[str] = set()
    for src in image_files:
        stem = safe_stem(src)
        suffix = src.suffix.lower()
        asset_name = stem + suffix
        if asset_name in used_asset_names:
            n = 2
            while f"{stem}_{n}{suffix}" in used_asset_names:
                n += 1
            asset_name = f"{stem}_{n}{suffix}"
        used_asset_names.add(asset_name)
        asset_rel = f"assets/img/{asset_name}"
        copy_asset(src, html_dir / asset_rel, overwrite=overwrite)
        w, h = image_size(src)
        fig_docs.append(FigDoc(
            source_path=str(src),
            title=src.stem,
            html_rel=f"fig/{stem}.html",
            pdf_rel=f"fig/{stem}.pdf",
            asset_rel_from_html_root=asset_rel,
            width=w,
            height=h,
        ))

    fig_manifest_for_index = [
        {"title": d.title, "src": d.asset_rel_from_html_root, "href": d.html_rel, "w": d.width, "h": d.height}
        for d in fig_docs
    ]
    write_text(
        html_dir / "index_fig.html",
        fig_viewer_html(
            {"title": "index_fig", "currentIndex": 0, "autoLandscape": auto_landscape, "figures": fig_manifest_for_index},
            "assets",
        ),
        overwrite,
    )
    for idx, d in enumerate(fig_docs):
        fig_manifest_for_page = [
            {"title": x.title, "src": "../" + x.asset_rel_from_html_root, "href": Path(x.html_rel).name, "w": x.width, "h": x.height}
            for x in fig_docs
        ]
        write_text(
            html_dir / d.html_rel,
            fig_viewer_html(
                {"title": d.title, "currentIndex": idx, "autoLandscape": auto_landscape, "figures": fig_manifest_for_page},
                "../assets",
            ),
            overwrite,
        )

    write_text(html_dir / "index_all.html", index_all_html(text_docs, fig_docs), overwrite)
    write_text(
        html_dir / "index.html",
        "<!doctype html><meta charset='utf-8'>"
        "<meta http-equiv='refresh' content='0; url=index_all.html'>"
        "<a href='index_all.html'>index_all.html</a>\n",
        overwrite,
    )

    return text_docs, fig_docs


def build_report(
    base_dir: Path,
    text_docs: list[TextDoc],
    fig_docs: list[FigDoc],
    pdf_results: list[dict],
    settings: dict,
    command: str = "",
) -> Path:
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_dir": str(base_dir),
        "command": command,
        "settings": settings,
        "text_count": len(text_docs),
        "figure_count": len(fig_docs),
        "texts": [asdict(d) for d in text_docs],
        "figures": [asdict(d) for d in fig_docs],
        "pdf_results": pdf_results,
    }
    ensure_dir(base_dir / "PDF")
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
    """High level orchestrator used by both the CLI and the GUI app.

    ``progress`` is an optional callable ``(message: str) -> None`` for
    streaming status updates back to a UI.
    """
    from .pdf_export import make_image_pdfs, make_text_pdfs_with_playwright

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

    text_docs, fig_docs = build_html(
        base_dir=base_dir,
        text_files=text_files,
        image_files=image_files,
        overwrite=overwrite,
        encoding=encoding,
        auto_landscape=auto_landscape_html,
    )
    log(f"HTML 作成完了: {base_dir / 'HTML'}")

    pdf_results: list[dict] = []
    if not skip_pdf:
        if text_docs:
            log("テキストPDFを生成中（Playwright）...")
            pdf_results.extend(make_text_pdfs_with_playwright(base_dir, text_docs, overwrite=overwrite))
        if fig_docs:
            log("画像PDFを生成中（Pillow）...")
            pdf_results.extend(make_image_pdfs(base_dir, fig_docs, overwrite=overwrite, orientation=pdf_image_orientation))
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
    build_report(base_dir, text_docs, fig_docs, pdf_results, settings, command=command)
    log(f"完了。Open: {(base_dir / 'HTML' / 'index_all.html').resolve()}")

    return text_docs, fig_docs, pdf_results
