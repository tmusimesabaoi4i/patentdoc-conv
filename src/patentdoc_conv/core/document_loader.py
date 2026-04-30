"""Document loading utilities.

Handles discovering and reading TXT / IMG files from the user's
directory structure. This module is used by both the HTML generator and
the PDF generator.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

IMAGE_EXTS: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff",
})
TEXT_EXTS: frozenset[str] = frozenset({".txt"})


def natural_key(path_or_name):
    """Natural sort key for filenames (e.g. 1, 2, 10 instead of 1, 10, 2)."""
    s = path_or_name.name if isinstance(path_or_name, Path) else str(path_or_name)
    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r"(\d+)", s)]


def safe_stem(path: Path) -> str:
    """Normalize a filename stem so it is safe for Windows / browsers."""
    stem = path.stem.strip()
    stem = re.sub(r"[\\/:*?\"<>|]", "_", stem)
    stem = re.sub(r"\s+", "_", stem)
    return stem or "untitled"


def read_text_auto(path: Path, preferred: str = "auto") -> tuple[str, str]:
    """Read a text file with automatic encoding detection.

    Returns (content, detected_encoding).
    """
    data = path.read_bytes()
    encodings: list[str] = []
    if preferred and preferred != "auto":
        encodings.append(preferred)
    encodings.extend(["utf-8-sig", "utf-8", "cp932", "shift_jis", "euc_jp"])
    seen: set[str] = set()
    for enc in encodings:
        if enc in seen:
            continue
        seen.add(enc)
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def discover_files(base_dir: Path) -> tuple[list[Path], list[Path]]:
    """Find TXT and IMG files in the standard directory structure.

    Expects:
        base_dir/
        ├─ TXT/  (*.txt)
        └─ IMG/  (*.png, *.jpg, etc.)

    Returns (text_files, image_files) sorted naturally.
    """
    txt_dir = base_dir / "TXT"
    img_dir = base_dir / "IMG"
    text_files: list[Path] = []
    image_files: list[Path] = []
    if txt_dir.exists():
        text_files = sorted(
            (p for p in txt_dir.iterdir() if p.is_file() and p.suffix.lower() in TEXT_EXTS),
            key=natural_key,
        )
    if img_dir.exists():
        image_files = sorted(
            (p for p in img_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS),
            key=natural_key,
        )
    return text_files, image_files


def image_size(path: Path) -> tuple[Optional[int], Optional[int]]:
    """Get image dimensions using Pillow. Returns (width, height) or (None, None)."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None, None


@dataclass
class TextDocument:
    """Represents a loaded text document."""
    source_path: Path
    title: str
    content: str
    encoding: str
    char_count: int
    line_count: int


@dataclass
class ImageDocument:
    """Represents a loaded image document."""
    source_path: Path
    title: str
    width: Optional[int]
    height: Optional[int]


def load_text_documents(
    text_files: list[Path],
    encoding: str = "auto",
) -> list[TextDocument]:
    """Load multiple text files into TextDocument objects."""
    docs: list[TextDocument] = []
    for src in text_files:
        content, enc = read_text_auto(src, preferred=encoding)
        docs.append(TextDocument(
            source_path=src,
            title=src.stem,
            content=content,
            encoding=enc,
            char_count=len(content),
            line_count=len(content.splitlines()) if content else 0,
        ))
    return docs


def load_image_documents(image_files: list[Path]) -> list[ImageDocument]:
    """Load multiple image files into ImageDocument objects."""
    docs: list[ImageDocument] = []
    for src in image_files:
        w, h = image_size(src)
        docs.append(ImageDocument(
            source_path=src,
            title=src.stem,
            width=w,
            height=h,
        ))
    return docs
