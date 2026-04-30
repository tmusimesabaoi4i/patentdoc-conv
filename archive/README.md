# archive/

旧構成で使われていたが、現在の GUI アプリには不要なファイルの退避先です。
削除はしていません。安心してから消してください。

## 中身

- `legacy_flat_layout/` - `src/` 化する前の `patentdoc_conv/` 直置きパッケージ
  - `cli.py` ... 旧 CLI (`patentdoc-conv run --dir ...`)。GUI 専用化に伴い退避
  - `__init__.py` / `__main__.py` ... 旧エントリーポイント
  - `builder.py` / `models.py` / `pdf_export.py` / `templates.py` / `utils.py`
    ... `src/patentdoc_conv/core/` 配下に移植済み (内容はほぼ同等)
  - `assets/` ... `src/patentdoc_conv/assets/` に移植済み
- `patentdoc-conv.bat` - 旧 CLI ラッパー
- `patentdoc-conv-gui.bat` - 旧 `--gui` 起動用ラッパー (現行は `python -m patentdoc_conv`)

## 完全に消してよくなったら

```powershell
Remove-Item archive -Recurse -Force
```
