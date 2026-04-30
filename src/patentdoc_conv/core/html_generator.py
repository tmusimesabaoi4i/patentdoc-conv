"""HTML site generator.

Produces a self-contained HTML/ tree from TextDocument and ImageDocument
objects. The generated pages can be opened from file:///.../HTML/index_all.html.
"""
from __future__ import annotations

import base64
import shutil
from pathlib import Path

from ..assets import ASSET_FILENAMES, read_asset
from .document_loader import ImageDocument, TextDocument, safe_stem
from .templates import fig_viewer_html, index_all_html, text_viewer_html
from .models import FigDoc, TextDoc


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_text(path: Path, content: str, overwrite: bool = True) -> bool:
    if path.exists() and not overwrite:
        return False
    _ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def _copy_asset(src: Path, dst: Path, overwrite: bool = True) -> bool:
    if dst.exists() and not overwrite:
        return False
    _ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    return True


def _b64_text(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def _write_assets(html_dir: Path, overwrite: bool) -> None:
    assets_dir = html_dir / "assets"
    for name in ASSET_FILENAMES:
        _write_text(assets_dir / name, read_asset(name), overwrite)


def generate_html(
    base_dir: Path,
    text_docs: list[TextDocument],
    image_docs: list[ImageDocument],
    overwrite: bool = True,
    auto_landscape: bool = True,
) -> tuple[list[TextDoc], list[FigDoc]]:
    """Generate the HTML viewer site.

    Returns (text_doc_metadata, fig_doc_metadata) for use by the PDF
    generator or report builder.
    """
    html_dir = base_dir / "HTML"
    text_html_dir = html_dir / "text"
    fig_html_dir = html_dir / "fig"
    img_asset_dir = html_dir / "assets" / "img"
    _ensure_dir(text_html_dir)
    _ensure_dir(fig_html_dir)
    _ensure_dir(img_asset_dir)
    _write_assets(html_dir, overwrite=overwrite)

    text_meta: list[TextDoc] = []
    for doc in text_docs:
        stem = safe_stem(doc.source_path)
        text_meta.append(TextDoc(
            source_path=str(doc.source_path),
            title=doc.title,
            html_rel=f"text/{stem}.html",
            pdf_rel=f"text/{stem}.pdf",
            encoding=doc.encoding,
            char_count=doc.char_count,
            line_count=doc.line_count,
        ))

    text_nav = [{"title": m.title, "href": Path(m.html_rel).name} for m in text_meta]
    for idx, (doc, meta) in enumerate(zip(text_docs, text_meta)):
        docs_for_page: list[dict] = []
        for i, nav in enumerate(text_nav):
            item: dict = {"title": nav["title"], "href": nav["href"]}
            if i == idx:
                item["b64"] = _b64_text(doc.content)
            docs_for_page.append(item)
        page_data = {"title": meta.title, "currentIndex": idx, "docs": docs_for_page}
        _write_text(html_dir / meta.html_rel, text_viewer_html(page_data, "../assets"), overwrite)

    index_text_docs = [
        {"title": m.title, "href": m.html_rel, "b64": _b64_text(d.content)}
        for d, m in zip(text_docs, text_meta)
    ]
    _write_text(
        html_dir / "index_text.html",
        text_viewer_html({"title": "index_text", "currentIndex": 0, "docs": index_text_docs}, "assets"),
        overwrite,
    )

    fig_meta: list[FigDoc] = []
    used_asset_names: set[str] = set()
    for doc in image_docs:
        stem = safe_stem(doc.source_path)
        suffix = doc.source_path.suffix.lower()
        asset_name = stem + suffix
        if asset_name in used_asset_names:
            n = 2
            while f"{stem}_{n}{suffix}" in used_asset_names:
                n += 1
            asset_name = f"{stem}_{n}{suffix}"
        used_asset_names.add(asset_name)
        asset_rel = f"assets/img/{asset_name}"
        _copy_asset(doc.source_path, html_dir / asset_rel, overwrite=overwrite)
        fig_meta.append(FigDoc(
            source_path=str(doc.source_path),
            title=doc.title,
            html_rel=f"fig/{stem}.html",
            pdf_rel=f"fig/{stem}.pdf",
            asset_rel_from_html_root=asset_rel,
            width=doc.width,
            height=doc.height,
        ))

    fig_manifest_for_index = [
        {"title": m.title, "src": m.asset_rel_from_html_root, "href": m.html_rel, "w": m.width, "h": m.height}
        for m in fig_meta
    ]
    _write_text(
        html_dir / "index_fig.html",
        fig_viewer_html(
            {"title": "index_fig", "currentIndex": 0, "autoLandscape": auto_landscape, "figures": fig_manifest_for_index},
            "assets",
        ),
        overwrite,
    )
    for idx, m in enumerate(fig_meta):
        fig_manifest_for_page = [
            {"title": x.title, "src": "../" + x.asset_rel_from_html_root, "href": Path(x.html_rel).name, "w": x.width, "h": x.height}
            for x in fig_meta
        ]
        _write_text(
            html_dir / m.html_rel,
            fig_viewer_html(
                {"title": m.title, "currentIndex": idx, "autoLandscape": auto_landscape, "figures": fig_manifest_for_page},
                "../assets",
            ),
            overwrite,
        )

    _write_text(html_dir / "index_all.html", index_all_html(text_meta, fig_meta), overwrite)
    _write_text(
        html_dir / "index.html",
        "<!doctype html><meta charset='utf-8'>"
        "<meta http-equiv='refresh' content='0; url=index_all.html'>"
        "<a href='index_all.html'>index_all.html</a>\n",
        overwrite,
    )

    return text_meta, fig_meta
