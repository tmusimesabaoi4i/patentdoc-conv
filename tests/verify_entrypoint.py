"""Verify that __main__.py works under both invocation styles.

This is what PyInstaller does internally: it runs the entry script
with no parent package context. If the entry script uses a relative
import, this raises ImportError.

Run with:  python tests/verify_entrypoint.py
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    entry = project_root / "src" / "patentdoc_conv" / "__main__.py"

    src_path = str(project_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    sys.argv = ["__main__.py", "--no-mainloop"]

    print(f"Loading {entry} as a top-level script (no parent package)...")
    try:
        runpy.run_path(str(entry), run_name="__not_main__")
    except ImportError as e:
        print(f"FAIL: ImportError: {e}")
        return 1
    except SystemExit:
        pass
    print("OK: no ImportError when running __main__.py as a script.")

    print("Loading patentdoc_conv as a module (-m style)...")
    try:
        import importlib
        m = importlib.import_module("patentdoc_conv.__main__")
        assert hasattr(m, "main"), "main() entry not found"
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        return 1
    print("OK: 'python -m patentdoc_conv' style import works.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
