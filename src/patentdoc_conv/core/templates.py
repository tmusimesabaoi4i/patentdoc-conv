"""HTML templates produced by the builder.

The CSS / JS referenced from the templates lives in
:mod:`patentdoc_conv.assets` and is copied to ``HTML/assets/`` at build
time.
"""
from __future__ import annotations

import html
import json

from .models import FigDoc, TextDoc


def json_script(obj) -> str:
    """Serialize an object so that it is safe to embed inside a <script>."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

KEYWORD_COLORS: tuple[str, ...] = ("red", "blue", "yellow", "green", "purple", "orange")
KEYWORD_LABELS: dict[str, str] = {
    "red": "赤",
    "blue": "青",
    "yellow": "黄",
    "green": "緑",
    "purple": "紫",
    "orange": "橙",
}


def _term_inputs_html() -> str:
    parts: list[str] = []
    for color in KEYWORD_COLORS:
        label = KEYWORD_LABELS[color]
        parts.append(
            f'<input id="term_{color}" class="term t-{color}" '
            f'placeholder="{label}キーワード" '
            f'title="{label}でハイライトする単語（空白区切りで複数可）">'
        )
    return "\n    ".join(parts)


_HELP_ROWS_TEXT: tuple[tuple[str, str], ...] = (
    ("[ / ←", "前の文献"),
    ("] / →", "次の文献"),
    ("/", "キーワード入力欄にフォーカス"),
    ("n / p", "次 / 前のキーワードヒット"),
    ("Ctrl+F", "文中検索を開く（Esc で閉じる）"),
    ("g", "段落[XXXX]ジャンプ（特許文書）"),
    ("1〜6", "選択したテキストに色マーカーを引く（1=赤,2=青,3=黄,4=緑,5=紫,6=橙）"),
    ("0", "選択範囲のマーカーを消す"),
    ("c", "選択範囲にメモを書く"),
    ("b", "サイドバー（目次/しおり/メモ）を開閉"),
    ("Shift+B", "現在位置をしおりとして保存"),
    ("s", "表示設定パネル（フォント・サイズ・幅）"),
    ("d", "ダークモード切替"),
    ("z", "集中表示（バーを全て隠す）"),
    ("?", "ヘルプ"),
    ("Esc", "ダイアログ・パネルを閉じる"),
)


def _help_table(rows: tuple[tuple[str, str], ...]) -> str:
    body = "\n".join(
        f"      <tr><th><kbd>{html.escape(k)}</kbd></th><td>{html.escape(v)}</td></tr>"
        for k, v in rows
    )
    return f"""<table class="kbdTable"><tbody>
{body}
    </tbody></table>"""


def text_viewer_html(data: dict, asset_prefix: str) -> str:
    """Render a text-viewer HTML page.

    ``asset_prefix`` is ``"../assets"`` for files placed in ``HTML/text/``
    and ``"assets"`` for ``HTML/index_text.html``.
    """
    data_with_colors = dict(data)
    data_with_colors.setdefault("colors", list(KEYWORD_COLORS))
    help_table = _help_table(_HELP_ROWS_TEXT)
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(data.get('title', 'Text Viewer'))}</title>
  <link rel="stylesheet" href="{asset_prefix}/common.css">
  <link rel="stylesheet" href="{asset_prefix}/text_viewer.css">
</head>
<body class="textBody">
  <div id="progressBar" class="progressBar noPrint"></div>

  <div class="topbarStack noPrint">
    <div class="topbar">
      <button id="toggleSidebar" class="iconBtn" title="目次 / しおり / メモ (b)">≡</button>
      <button id="prevDoc" class="iconBtn" title="前の文献 / [">←</button>
      <button id="nextDoc" class="iconBtn" title="次の文献 / ]">→</button>
      <select id="docSelect" title="文献を選択"></select>
      <span id="titleText" class="titleText"></span>
      <span class="spacer"></span>
      <button id="findBtn" title="文中検索 (Ctrl+F)">検索</button>
      <button id="paraBtn" title="段落へジャンプ (g)">段落</button>
      <button id="settingsBtn" title="表示設定 (s)">表示</button>
      <button id="zenBtn" title="集中表示 / z">集中</button>
      <button id="helpBtn" class="iconBtn" title="ヘルプ (?)">?</button>
    </div>
    <div class="searchbar">
      <span class="termList">
      {_term_inputs_html()}
      </span>
      <span class="spacer"></span>
      <span id="hitCount" class="small muted">0件</span>
      <button id="prevHit" class="iconBtn" title="前のヒット / p">↑</button>
      <button id="nextHit" class="iconBtn" title="次のヒット / n / Enter">↓</button>
      <button id="clearTerms" title="色付けを解除">解除</button>
    </div>
  </div>

  <aside id="sidebar" class="sidebar noPrint">
    <div class="sidebarTabs">
      <button class="sidebarTab active" data-target="tocPane">目次</button>
      <button class="sidebarTab" data-target="bookmarkPane">しおり</button>
      <button class="sidebarTab" data-target="notesPane">メモ</button>
    </div>
    <div id="tocPane" class="sidebarPane active">
      <h4>自動目次（【...】見出し）</h4>
      <ol id="tocList"></ol>
    </div>
    <div id="bookmarkPane" class="sidebarPane">
      <div class="bookmarkAddRow">
        <button id="addBookmark" title="現在位置を追加 (Shift+B)">＋ 現在位置をしおり</button>
      </div>
      <ol id="bookmarkList"></ol>
    </div>
    <div id="notesPane" class="sidebarPane">
      <h4>メモ（テキスト選択 → c で追加）</h4>
      <ol id="notesList"></ol>
    </div>
  </aside>

  <div id="markerBar" class="markerBar noPrint" title="ヒット位置"></div>

  <div id="findBar" class="findBar hidden">
    <input id="findInput" placeholder="文中検索（Enter で次, Shift+Enter で前）">
    <span id="findCount" class="small muted"></span>
    <button id="findPrev" class="iconBtn" title="前">↑</button>
    <button id="findNext" class="iconBtn" title="次">↓</button>
    <button id="findClose" class="iconBtn" title="閉じる (Esc)">×</button>
  </div>

  <div id="settingsPanel" class="floatPanel hidden">
    <h3>表示設定</h3>
    <div class="row"><span>フォントサイズ</span><input type="range" id="fontSizeR" min="13" max="22" step="1"></div>
    <div class="row"><span>行間</span><input type="range" id="lineHeightR" min="1.5" max="2.4" step="0.05"></div>
    <div class="row"><span>本文幅</span><input type="range" id="readerWidthR" min="640" max="1180" step="20"></div>
    <div class="row"><span>書体</span>
      <select id="fontFamilyS">
        <option value="sans">ゴシック</option>
        <option value="serif">明朝（読み物）</option>
      </select>
    </div>
    <div class="row"><span>ダークモード</span><input type="checkbox" id="darkMode"></div>
    <div class="row"><span>紙モード（セピア）</span><input type="checkbox" id="paperMode"></div>
    <div class="actions"><button id="settingsClose">閉じる</button></div>
  </div>

  <div id="commentDialog" class="dialog hidden" role="dialog" aria-modal="true">
    <div class="dialogBox">
      <h3>選択範囲にメモを書く</h3>
      <textarea id="commentInput" placeholder="メモを入力（保存するとアンダーライン＋ホバーで表示）"></textarea>
      <div class="actions">
        <button id="commentCancel">キャンセル</button>
        <button id="commentSave">保存</button>
      </div>
    </div>
  </div>

  <div id="helpDialog" class="dialog hidden" role="dialog" aria-modal="true">
    <div class="dialogBox">
      <h3>キーボードショートカット</h3>
      {help_table}
      <div class="actions"><button id="helpClose">閉じる</button></div>
    </div>
  </div>

  <main class="reader">
    <div id="docMeta" class="docHeader">
      <span class="docMetaText"></span>
    </div>
    <div id="textContent"></div>
  </main>

  <script>window.TEXT_VIEWER_DATA = {json_script(data_with_colors)};</script>
  <script src="{asset_prefix}/text_viewer.js"></script>
</body>
</html>
"""


_HELP_ROWS_FIG: tuple[tuple[str, str], ...] = (
    ("[ / ←", "前の図"),
    ("] / →", "次の図"),
    ("p", "ペン"),
    ("h", "蛍光ペン"),
    ("l", "直線"),
    ("o", "矩形（四角）"),
    ("e", "楕円"),
    ("a", "矢印"),
    ("t", "テキスト注釈（クリック後に入力、Ctrl+Enterで確定）"),
    ("x", "消しゴム"),
    ("Space", "手のひら（ドラッグでパン）"),
    ("r / Shift+R", "右回転 / 左回転"),
    ("f", "横幅に合わせる"),
    ("+ / -", "拡大 / 縮小"),
    ("Ctrl+Z / Ctrl+Shift+Z", "戻す / やり直し"),
    ("Ctrl+S", "PNG として保存"),
    ("d", "ダーク反転表示"),
    ("z", "集中表示（ツールバーを薄く）"),
    ("?", "ヘルプ"),
    ("Esc", "テキスト編集／ヘルプを閉じる"),
)


def fig_viewer_html(data: dict, asset_prefix: str) -> str:
    help_table = _help_table(_HELP_ROWS_FIG)
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(data.get('title', 'Figure Viewer'))}</title>
  <link rel="stylesheet" href="{asset_prefix}/common.css">
  <link rel="stylesheet" href="{asset_prefix}/fig_viewer.css">
</head>
<body class="figBody tool-pen">
  <div class="topbar noPrint">
    <button id="prevFig" class="toolBtn" title="前の図 / [ / ←">←</button>
    <button id="nextFig" class="toolBtn" title="次の図 / ] / →">→</button>
    <select id="figSelect" title="図を選択"></select>
    <span id="titleText" class="titleText"></span>
    <span id="figMeta" class="small muted"></span>

    <span class="toolDivider"></span>
    <button id="rotL" class="toolBtn" title="左回転 / Shift+R">↺</button>
    <button id="rotR" class="toolBtn" title="右回転 / r">↻</button>
    <button id="fitBtn" class="toolBtn" title="横幅に合わせる / f">幅</button>
    <button id="zoomOut" class="toolBtn" title="縮小 / -">−</button>
    <button id="zoomIn" class="toolBtn" title="拡大 / +">＋</button>

    <span class="toolDivider"></span>
    <button class="toolBtn active" data-tool="pen"       title="ペン (p)">✎</button>
    <button class="toolBtn"        data-tool="highlight" title="蛍光ペン (h)">▮</button>
    <button class="toolBtn"        data-tool="line"      title="直線 (l)">／</button>
    <button class="toolBtn"        data-tool="rect"      title="矩形 (o)">▭</button>
    <button class="toolBtn"        data-tool="ellipse"   title="楕円 (e)">◯</button>
    <button class="toolBtn"        data-tool="arrow"     title="矢印 (a)">→</button>
    <button class="toolBtn"        data-tool="text"      title="テキスト (t)">A</button>
    <button class="toolBtn"        data-tool="erase"     title="消しゴム (x)">⌫</button>
    <button class="toolBtn"        data-tool="pan"       title="手のひら / 移動 (Space)">✋</button>

    <span class="toolDivider"></span>
    <button class="toolColor active" data-color="#111111" title="黒"></button>
    <button class="toolColor"        data-color="#cc0000" title="赤"></button>
    <button class="toolColor"        data-color="#0058ff" title="青"></button>
    <button class="toolColor"        data-color="#ffd200" title="黄"></button>
    <button class="toolColor"        data-color="#1e9e4a" title="緑"></button>
    <button class="toolColor"        data-color="#8a2cd1" title="紫"></button>
    <input id="brushSize" type="range" min="1" max="22" value="4" title="太さ">

    <span class="spacer"></span>
    <button id="undoBtn" class="toolBtn" title="戻す / Ctrl+Z">戻す</button>
    <button id="redoBtn" class="toolBtn" title="やり直し / Ctrl+Shift+Z">やり直し</button>
    <button id="clearBtn" class="toolBtn" title="この向きの書き込みを全消去">消す</button>
    <button id="savePng" class="toolBtn" title="PNG保存 / Ctrl+S">PNG</button>
    <button id="exportJson" class="toolBtn" title="書き込みをJSONエクスポート">出力</button>
    <label class="toolBtn" style="cursor:pointer;display:inline-flex;align-items:center;justify-content:center;" title="JSONを読み込む">
      入力<input id="importJson" type="file" accept="application/json" style="display:none">
    </label>
    <button id="darkBtn" class="toolBtn" title="ダーク反転表示 / d">夜</button>
    <button id="helpBtn" class="toolBtn" title="ヘルプ (?)">?</button>
  </div>

  <div id="figShell" class="figShell">
    <div class="canvasWrap">
      <canvas id="figCanvas"></canvas>
      <div id="canvasOverlay" class="canvasOverlay"></div>
    </div>
  </div>

  <div id="helpDialog" class="dialog hidden" role="dialog" aria-modal="true">
    <div class="dialogBox">
      <h3>キーボードショートカット（図面）</h3>
      {help_table}
      <div class="actions"><button id="helpClose">閉じる</button></div>
    </div>
  </div>

  <script>window.FIG_VIEWER_DATA = {json_script(data)};</script>
  <script src="{asset_prefix}/fig_viewer.js"></script>
</body>
</html>
"""


def index_all_html(text_docs: list[TextDoc], fig_docs: list[FigDoc]) -> str:
    text_items = "\n".join(
        f'<li><a href="{html.escape(d.html_rel)}">{html.escape(d.title)}</a>'
        f'<span class="badge">TXT</span></li>'
        for d in text_docs
    ) or '<li class="muted">TXT が見つかりませんでした。</li>'
    fig_items = "\n".join(
        f'<li><a href="{html.escape(d.html_rel)}">{html.escape(d.title)}</a>'
        f'<span class="badge">IMG</span></li>'
        for d in fig_docs
    ) or '<li class="muted">IMG が見つかりませんでした。</li>'
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>審査用HTML index_all</title>
  <link rel="stylesheet" href="assets/common.css">
</head>
<body>
  <main class="indexPage">
    <h1>審査用HTML index_all</h1>
    <p class="lead">白黒・ローカル実行用。テキストは6色キーワードで指定したときだけ色付け、図面は回転・書き込み・PNG保存に対応。</p>
    <div class="indexGrid">
      <section class="indexCard">
        <h2>テキスト文献</h2>
        <p><a href="index_text.html">index_text を開く</a></p>
        <ul class="simpleList">{text_items}</ul>
      </section>
      <section class="indexCard">
        <h2>図面</h2>
        <p><a href="index_fig.html">index_fig を開く</a></p>
        <ul class="simpleList">{fig_items}</ul>
      </section>
    </div>
  </main>
</body>
</html>
"""
