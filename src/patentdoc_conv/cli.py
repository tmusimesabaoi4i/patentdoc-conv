"""Command line interface for patentdoc_conv."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .builder import run_build


RUN_MODES: tuple[str, ...] = ("all", "text", "img")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="patentdoc-conv",
        description="TXT/IMG を審査用のローカルHTML・PDFへ一括変換します。",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("command", nargs="?", choices=["run"], help="実行コマンド（省略可）")
    parser.add_argument("--dir", help="TXT/IMG を含む親ディレクトリ。省略時は GUI を起動します。")
    parser.add_argument("--run", dest="run_mode", choices=RUN_MODES, default="all", help="実行対象: all / text / img")
    parser.add_argument("--gui", action="store_true", help="GUI アプリを起動します。")
    parser.add_argument("--encoding", default="auto", help="TXTの文字コード。通常は auto。例: utf-8, cp932")
    parser.add_argument("--overwrite", action="store_true", default=True, help="既存HTML/PDFを上書きします（既定）")
    parser.add_argument("--no-overwrite", dest="overwrite", action="store_false", help="既存HTML/PDFを上書きしません")
    parser.add_argument("--clean", action="store_true", help="先に HTML/PDF ディレクトリを削除して作り直します")
    parser.add_argument("--skip-pdf", action="store_true", help="HTMLのみ作成します")
    parser.add_argument(
        "--pdf-image-orientation",
        choices=["original", "landscape"],
        default="original",
        help="画像PDFの向き。既定は original",
    )
    parser.add_argument(
        "--no-auto-landscape-html",
        action="store_true",
        help="HTMLの図面初期表示で縦長画像を横長へ自動回転しません",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    if args.gui or (not args.dir and args.command != "run"):
        from .gui import run_app
        run_app(initial_dir=args.dir)
        return 0

    if not args.dir:
        print("ERROR: --dir を指定してください（例: patentdoc-conv run --dir samples/）", file=sys.stderr)
        return 2

    base_dir = Path(args.dir).expanduser().resolve()
    try:
        run_build(
            base_dir=base_dir,
            run_mode=args.run_mode,
            overwrite=args.overwrite,
            encoding=args.encoding,
            skip_pdf=args.skip_pdf,
            clean=args.clean,
            pdf_image_orientation=args.pdf_image_orientation,
            auto_landscape_html=not args.no_auto_landscape_html,
            progress=lambda msg: print(msg),
            command=" ".join(sys.argv),
        )
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
