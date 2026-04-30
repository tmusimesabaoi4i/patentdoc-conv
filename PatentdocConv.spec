# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PatentdocConv.

Build with:
    python -m PyInstaller --noconfirm --clean PatentdocConv.spec

This spec is the *recommended* way to build the distributable exe:

* runs the absolute-import-safe entry script (``src/patentdoc_conv/__main__.py``)
* bundles the static assets (CSS / JS) used by the HTML viewers
* explicitly collects everything from ``reportlab`` and ``PIL`` so that
  their dynamic-import plugins (image codecs, font hooks, etc.) are not
  silently dropped from the onefile build
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
PROJECT_ROOT = Path(SPECPATH).resolve()
ENTRY = str(PROJECT_ROOT / "src" / "patentdoc_conv" / "__main__.py")
ASSETS_SRC = str(PROJECT_ROOT / "src" / "patentdoc_conv" / "assets")
ICON_PATH = PROJECT_ROOT / "src" / "patentdoc_conv" / "assets" / "app.ico"

# Pull every submodule + data file from libraries that lazily import.
rl_datas, rl_binaries, rl_hidden = collect_all("reportlab")
pil_datas, pil_binaries, pil_hidden = collect_all("PIL")

datas = [
    (ASSETS_SRC, "patentdoc_conv/assets"),
]
datas.extend(rl_datas)
datas.extend(pil_datas)

binaries = []
binaries.extend(rl_binaries)
binaries.extend(pil_binaries)

hiddenimports = []
hiddenimports.extend(rl_hidden)
hiddenimports.extend(pil_hidden)
hiddenimports.extend([
    "patentdoc_conv",
    "patentdoc_conv.assets",
    "patentdoc_conv.core",
    "patentdoc_conv.core.document_loader",
    "patentdoc_conv.core.html_generator",
    "patentdoc_conv.core.pdf_generator",
    "patentdoc_conv.core.service",
    "patentdoc_conv.core.models",
    "patentdoc_conv.core.templates",
    "patentdoc_conv.gui",
    "patentdoc_conv.gui.main_window",
])


a = Analysis(
    [ENTRY],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "playwright",
        "selenium",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PatentdocConv",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_PATH) if ICON_PATH.exists() else None,
)
