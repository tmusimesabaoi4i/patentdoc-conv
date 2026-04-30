"""Minimal tkinter GUI for the patentdoc_conv builder.

Designed to be self-contained: no third-party UI dependencies, just
standard library widgets in a deliberately simple, monochrome layout.
"""
from __future__ import annotations

import queue
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..core.pdf_generator import FontNotFoundError
from ..core.service import run_build


def _looks_like_target_dir(path: Path) -> bool:
    return path.is_dir() and ((path / "TXT").exists() or (path / "IMG").exists())


class App:
    """Thin tkinter wrapper around :func:`patentdoc_conv.core.service.run_build`."""

    def __init__(self, root: tk.Tk, initial_dir: Optional[str] = None) -> None:
        self.root = root
        self.root.title("patentdoc-conv - 審査用 HTML/PDF 変換")
        self.root.geometry("760x560")
        self.root.minsize(640, 480)

        self.dir_var = tk.StringVar(value=initial_dir or "")
        self.encoding_var = tk.StringVar(value="auto")
        self.orientation_var = tk.StringVar(value="original")
        self.skip_pdf_var = tk.BooleanVar(value=False)
        self.clean_var = tk.BooleanVar(value=False)
        self.overwrite_var = tk.BooleanVar(value=True)
        self.auto_landscape_var = tk.BooleanVar(value=True)

        self._build_styles()
        self._build_layout()

        self._log_queue: "queue.Queue[str]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._html_index_path: Optional[Path] = None

        self.root.after(120, self._drain_log_queue)
        self._set_running(False)

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        bg = "#ffffff"
        fg = "#111111"
        muted = "#666666"
        line = "#cccccc"
        soft = "#f3f3f3"
        self.root.configure(bg=bg)
        style.configure(".", background=bg, foreground=fg, fieldbackground=bg, bordercolor=line)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("Muted.TLabel", background=bg, foreground=muted)
        style.configure("Title.TLabel", background=bg, foreground=fg, font=("Yu Gothic UI", 13, "bold"))
        style.configure("Section.TLabel", background=bg, foreground=fg, font=("Yu Gothic UI", 10, "bold"))
        style.configure("TButton", background=bg, foreground=fg, padding=(10, 4), borderwidth=1, focusthickness=0)
        style.map("TButton", background=[("active", soft)], bordercolor=[("focus", fg)])
        style.configure("Accent.TButton", background=fg, foreground=bg, padding=(14, 6))
        style.map("Accent.TButton", background=[("active", "#333333")], foreground=[("disabled", "#aaaaaa")])
        style.configure("TEntry", fieldbackground=bg, foreground=fg, bordercolor=line, padding=4)
        style.configure("TCheckbutton", background=bg, foreground=fg)
        style.configure("TCombobox", fieldbackground=bg, foreground=fg)
        style.configure("Horizontal.TProgressbar", troughcolor=soft, background=fg)

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="patentdoc-conv", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="TXT / IMG を含む親ディレクトリを選び、HTML と PDF を生成します。",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        dir_box = ttk.Frame(outer)
        dir_box.pack(fill="x")
        ttk.Label(dir_box, text="対象ディレクトリ", style="Section.TLabel").pack(anchor="w")
        row = ttk.Frame(dir_box)
        row.pack(fill="x", pady=(4, 0))
        self.dir_entry = ttk.Entry(row, textvariable=self.dir_var)
        self.dir_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="参照…", command=self._choose_dir).pack(side="left", padx=(8, 0))
        ttk.Label(
            dir_box,
            text="この直下に TXT/ と IMG/ を置いてください。",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 14))

        opt = ttk.Frame(outer)
        opt.pack(fill="x")
        ttk.Label(opt, text="オプション", style="Section.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")

        ttk.Label(opt, text="文字コード").grid(row=1, column=0, sticky="w", pady=(8, 4))
        enc_combo = ttk.Combobox(
            opt,
            textvariable=self.encoding_var,
            values=("auto", "utf-8", "utf-8-sig", "cp932", "shift_jis", "euc_jp"),
            state="readonly",
            width=14,
        )
        enc_combo.grid(row=1, column=1, sticky="w", pady=(8, 4), padx=(8, 24))

        ttk.Label(opt, text="画像PDFの向き").grid(row=1, column=2, sticky="w", pady=(8, 4))
        orient_combo = ttk.Combobox(
            opt,
            textvariable=self.orientation_var,
            values=("original", "landscape"),
            state="readonly",
            width=14,
        )
        orient_combo.grid(row=1, column=3, sticky="w", pady=(8, 4), padx=(8, 0))

        ttk.Checkbutton(opt, text="HTMLのみ作成（PDFをスキップ）", variable=self.skip_pdf_var).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=2
        )
        ttk.Checkbutton(opt, text="HTML/PDF を作り直す（clean）", variable=self.clean_var).grid(
            row=2, column=2, columnspan=2, sticky="w", pady=2
        )
        ttk.Checkbutton(opt, text="既存ファイルを上書きする", variable=self.overwrite_var).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=2
        )
        ttk.Checkbutton(
            opt,
            text="HTMLで縦長画像を自動的に横長表示する",
            variable=self.auto_landscape_var,
        ).grid(row=3, column=2, columnspan=2, sticky="w", pady=2)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(14, 8))
        self.run_button = ttk.Button(actions, text="実行", style="Accent.TButton", command=self._on_run)
        self.run_button.pack(side="left")
        self.open_button = ttk.Button(actions, text="index_all.html を開く", command=self._open_index)
        self.open_button.pack(side="left", padx=(8, 0))
        self.open_button.state(["disabled"])
        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=180)
        self.progress.pack(side="right")

        log_frame = ttk.Frame(outer)
        log_frame.pack(fill="both", expand=True, pady=(8, 0))
        ttk.Label(log_frame, text="ログ", style="Section.TLabel").pack(anchor="w")
        text_box = tk.Text(
            log_frame,
            height=14,
            wrap="word",
            bg="#fafafa",
            fg="#111111",
            insertbackground="#111111",
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            font=("Consolas", 10),
        )
        text_box.pack(fill="both", expand=True, pady=(4, 0))
        text_box.configure(state="disabled")
        self.log_text = text_box

    def _choose_dir(self) -> None:
        initial = self.dir_var.get() or str(Path.home())
        chosen = filedialog.askdirectory(title="TXT / IMG を含むディレクトリを選択", initialdir=initial)
        if chosen:
            self.dir_var.set(chosen)

    def _set_running(self, running: bool) -> None:
        if running:
            self.run_button.state(["disabled"])
            self.open_button.state(["disabled"])
            self.progress.start(80)
        else:
            self.run_button.state(["!disabled"])
            self.progress.stop()
            if self._html_index_path and self._html_index_path.exists():
                self.open_button.state(["!disabled"])

    def _log(self, msg: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _enqueue_log(self, msg: str) -> None:
        self._log_queue.put(msg)

    def _drain_log_queue(self) -> None:
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self._log(msg)
        except queue.Empty:
            pass
        self.root.after(120, self._drain_log_queue)

    def _on_run(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        target = self.dir_var.get().strip()
        if not target:
            messagebox.showwarning("ディレクトリ未指定", "対象ディレクトリを選択してください。")
            return
        base_dir = Path(target).expanduser().resolve()
        if not base_dir.exists():
            messagebox.showerror("ディレクトリが存在しません", f"指定ディレクトリが存在しません:\n{base_dir}")
            return
        if not _looks_like_target_dir(base_dir):
            cont = messagebox.askyesno(
                "TXT / IMG が見つかりません",
                f"{base_dir}\nの直下に TXT/ または IMG/ が見当たりません。続行しますか？",
            )
            if not cont:
                return

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._html_index_path = base_dir / "HTML" / "index_all.html"
        self._set_running(True)

        opts = {
            "base_dir": base_dir,
            "overwrite": self.overwrite_var.get(),
            "encoding": self.encoding_var.get() or "auto",
            "skip_pdf": self.skip_pdf_var.get(),
            "clean": self.clean_var.get(),
            "pdf_image_orientation": self.orientation_var.get() or "original",
            "auto_landscape_html": self.auto_landscape_var.get(),
        }

        def worker() -> None:
            try:
                run_build(
                    progress=self._enqueue_log,
                    command="GUI",
                    **opts,
                )
                self._enqueue_log("---")
                self._enqueue_log("完了しました。")
            except FontNotFoundError as e:
                self._enqueue_log("---")
                self._enqueue_log("PDF生成エラー: 日本語フォントが見つかりません")
                self._enqueue_log(str(e))
                self._enqueue_log("HTMLは生成されている可能性があります。")
            except FileNotFoundError as e:
                self._enqueue_log(f"ERROR: ファイルが見つかりません: {e}")
            except PermissionError as e:
                self._enqueue_log(f"ERROR: 書き込み権限がありません: {e}")
            except Exception as e:
                self._enqueue_log(f"ERROR: {type(e).__name__}: {e}")
            finally:
                self.root.after(0, lambda: self._set_running(False))

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _open_index(self) -> None:
        if self._html_index_path and self._html_index_path.exists():
            webbrowser.open(self._html_index_path.resolve().as_uri())


def run_app(initial_dir: Optional[str] = None) -> None:
    """Boot the tkinter event loop with the main window attached."""
    root = tk.Tk()
    App(root, initial_dir=initial_dir)
    root.mainloop()


def main() -> None:
    """GUI entry point used by ``python -m patentdoc_conv``."""
    run_app()


if __name__ == "__main__":
    main()
