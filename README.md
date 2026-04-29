# patentdoc-conv

審査用 TXT / IMG 一括 HTML・PDF 化ツール（CLI + GUI）

---

## クイックスタート

```bat
cd patentdoc-conv
python -m pip install -e .
python -m playwright install chromium

patentdoc-conv run --dir samples/
```

PDFが不要な場合は `--skip-pdf` を付けてください（Chromiumインストールも不要）。

---

## コマンド一覧

| 目的 | コマンド |
|---|---|
| すべて処理 | `patentdoc-conv run --dir samples/` |
| テキストのみ | `patentdoc-conv --run text --dir samples/` |
| 画像のみ | `patentdoc-conv --run img --dir samples/` |
| HTMLのみ作成 | `patentdoc-conv run --dir samples/ --skip-pdf` |
| GUIを起動 | `patentdoc-conv --gui` |

---

## 想定フォルダ構成

```
指定ディレクトリ/
├─ TXT/          ← 変換元テキスト (.txt)
├─ IMG/          ← 変換元画像 (.png, .jpg, 等)
├─ HTML/         ← 自動生成
└─ PDF/          ← 自動生成
```

---

## 主なオプション

| オプション | 説明 |
|---|---|
| `--skip-pdf` | HTMLのみ作成 |
| `--clean` | 出力先を削除して作り直す |
| `--no-overwrite` | 既存ファイルを上書きしない |
| `--encoding utf-8` | 文字コード指定（通常は auto） |

---

## HTMLビューアの機能

### テキストビューア
- 6色キーワードハイライト、手動マーカー、メモ
- 自動目次、段落ジャンプ、しおり、文中検索
- 表示設定（フォント/行間/幅/ダークモード）
- ショートカット一覧: `?`

### 図面ビューア
- ペン/蛍光ペン/直線/矩形/楕円/矢印/テキスト
- Undo/Redo、PNG保存、JSON書き出し
- ダーク反転表示
- ショートカット一覧: `?`

---

## 対応形式

- **テキスト**: `.txt`
- **画像**: `.png` `.jpg` `.jpeg` `.webp` `.bmp` `.gif` `.tif` `.tiff`

---

## トラブルシューティング

PDF生成に失敗する場合:
```bat
python -m playwright install chromium
```
