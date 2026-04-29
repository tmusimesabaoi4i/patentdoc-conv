"""Small filesystem / encoding helpers used throughout the package."""
from __future__ import annotations

import base64
import json
import re
import shutil
from pathlib import Path
from typing import Optional, Union

IMAGE_EXTS: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff",
})
TEXT_EXTS: frozenset[str] = frozenset({".txt"})


def natural_key(path_or_name: Union[Path, str]):
    s = path_or_name.name if isinstance(path_or_name, Path) else str(path_or_name)
    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r"(\d+)", s)]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_stem(path: Path) -> str:
    """Normalize a filename stem so it is safe for Windows / browsers.

    Japanese characters are preserved; only forbidden punctuation and
    whitespace are replaced.
    """
    stem = path.stem.strip()
    stem = re.sub(r"[\\/:*?\"<>|]", "_", stem)
    stem = re.sub(r"\s+", "_", stem)
    return stem or "untitled"


def read_text_auto(path: Path, preferred: str = "auto") -> tuple[str, str]:
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


def b64_text(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def json_script(obj) -> str:
    """Serialize an object so that it is safe to embed inside a <script>."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def write_text(path: Path, content: str, overwrite: bool = True) -> bool:
    if path.exists() and not overwrite:
        return False
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def copy_asset(src: Path, dst: Path, overwrite: bool = True) -> bool:
    if dst.exists() and not overwrite:
        return False
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    return True


def image_size(path: Path) -> tuple[Optional[int], Optional[int]]:
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None, None


def discover_files(base_dir: Path) -> tuple[list[Path], list[Path]]:
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
