# patentdoc-conv

審査用 **TXT / IMG** を一括で **HTML / PDF** 化する Windows 向けデスクトップ GUI アプリ。

- TXT ファイルを 6 色キーワードハイライトつきの読みやすい HTML ビューアに変換
- IMG ファイルをペン・蛍光ペン・矢印などで書き込める HTML 図面ビューアに変換
- PDF は ReportLab で直接生成（ブラウザエンジン不要）
- 画面は tkinter 製のシンプルな単一ウィンドウ

---

## ディレクトリ構成

```text
patentdoc-conv/
├─ README.md
├─ pyproject.toml
├─ requirements.txt
├─ src/
│  └─ patentdoc_conv/
│     ├─ __init__.py
│     ├─ __main__.py            # python -m patentdoc_conv で起動
│     ├─ gui/
│     │  ├─ __init__.py
│     │  └─ main_window.py      # tkinter のメインウィンドウ
│     ├─ core/
│     │  ├─ __init__.py
│     │  ├─ service.py          # GUI から呼ばれる業務ロジック (run_build)
│     │  ├─ document_loader.py  # ファイル読み込み
│     │  ├─ html_generator.py   # HTML 生成
│     │  ├─ pdf_generator.py    # PDF 生成 (ReportLab)
│     │  ├─ models.py
│     │  └─ templates.py
│     └─ assets/
│        ├─ common.css
│        ├─ text_viewer.css / .js
│        └─ fig_viewer.css / .js
├─ tests/
├─ build/                        # PyInstaller の作業ディレクトリ
├─ dist/                         # PyInstaller の出力先 (PatentdocConv.exe)
└─ archive/                      # 旧 CLI など参考用
```

---

## 1. セットアップ (Windows / cmd or PowerShell)

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

requirements.txt 経由で依存だけ入れたい場合:

```bat
python -m pip install -r requirements.txt
```

---

## 2. GUI の起動

```bat
python -m patentdoc_conv
```

起動すると単一ウィンドウが開きます。

1. 「対象ディレクトリ」に **TXT/** と **IMG/** を含む親フォルダを指定
2. 必要に応じて文字コード／PDF 向きなどを設定
3. **実行** ボタンを押すとログ欄に進捗が流れます
4. 終わったら **index_all.html を開く** で結果を確認

`pip install -e .` を行った環境では、`patentdoc-conv` コマンドからも GUI を起動できます (Windows ではコンソールが開きません)。

```bat
patentdoc-conv
```

---

## 3. 想定する入力フォルダ

```text
指定ディレクトリ/
├─ TXT/    ← 変換元テキスト (.txt)
├─ IMG/    ← 変換元画像 (.png .jpg .jpeg .webp .bmp .gif .tif .tiff)
├─ HTML/   ← 自動生成
└─ PDF/    ← 自動生成
```

---

## 4. PDF 生成について

本アプリでは、PDF 生成に **Playwright / Chromium は使用しません**。

PDF は `reportlab` により直接生成します。そのため、以下のような追加コマンドは不要です：

```bat
# 不要 (このコマンドは実行しなくて OK)
python -m playwright install chromium
```

GUI アプリを起動し、**実行** ボタンを押すことで HTML と PDF の両方が作成されます。
「HTMLのみ作成（PDFをスキップ）」にチェックを入れると、PDF 生成をスキップできます。

### 日本語フォントについて

PDF 生成時には Windows にインストールされている日本語フォントを自動的に検出して使用します。

- Yu Gothic (`C:\Windows\Fonts\YuGothM.ttc`)
- Meiryo (`C:\Windows\Fonts\meiryo.ttc`)
- MS Gothic (`C:\Windows\Fonts\msgothic.ttc`)

上記のいずれかがあれば日本語テキストが正しく表示されます。
フォントが見つからない場合はエラーメッセージがログに表示されます。

---

## 5. exe 形式でビルドする方法 (PyInstaller)

ビルド前にまず `python -m patentdoc_conv` で通常起動できることを確認してください。

```bat
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PatentdocConv --paths src --add-data "src\patentdoc_conv\assets;patentdoc_conv\assets" src\patentdoc_conv\__main__.py
```

成功すると、以下の場所に実行ファイルが出力されます。

```text
dist\PatentdocConv.exe
```

`--windowed` を付けているので、ダブルクリックしても黒いコンソール画面は出ません。

### アイコンを付ける場合

`src\patentdoc_conv\assets\app.ico` のようにアイコンを置いておき、`--icon` を追加します。

```bat
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PatentdocConv --icon src\patentdoc_conv\assets\app.ico --paths src --add-data "src\patentdoc_conv\assets;patentdoc_conv\assets" src\patentdoc_conv\__main__.py
```

### `--add-data` の意味

`src\patentdoc_conv\assets` を、exe 内の `patentdoc_conv\assets` に同梱する設定です。
ビューア用の CSS / JS はこのフォルダから読み込まれるため、付け忘れると HTML 出力が崩れます。

---

## 6. アンインストール

```bat
python -m pip uninstall patentdoc-conv
```

---

## 7. 主な機能

### テキストビューア

- 6 色キーワードハイライト、手動マーカー、メモ
- 自動目次、段落ジャンプ、しおり、文中検索
- 表示設定（フォント / 行間 / 幅 / ダークモード / 紙モード）
- ショートカット一覧: `?`

### 図面ビューア

- ペン / 蛍光ペン / 直線 / 矩形 / 楕円 / 矢印 / テキスト
- Undo / Redo、PNG 保存、JSON 書き出し / 読み込み
- ダーク反転表示
- ショートカット一覧: `?`

---

## 8. トラブルシューティング

| 症状 | 対処 |
|---|---|
| PDF に日本語が表示されない | Windows フォント (Yu Gothic / Meiryo / MS Gothic) が必要です |
| `pip install -e .` が失敗する | `python -m pip install --upgrade pip` 後に再実行 |
| exe ダブルクリック後にウィンドウが出ない | `--windowed` を外して再ビルドし、コンソールにエラーを出して確認 |
| HTML のスタイルが当たらない | `--add-data "src\patentdoc_conv\assets;patentdoc_conv\assets"` の指定漏れを確認 |
| PDF 出力先に書き込めない | 出力フォルダに書き込み権限があるか確認 |
