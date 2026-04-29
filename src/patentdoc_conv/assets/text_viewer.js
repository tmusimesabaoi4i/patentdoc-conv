/* =========================================================================
 * text_viewer.js
 *   - 紙のような本文 + 6色キーワードハイライト
 *   - 自動目次（特許文書の【...】）
 *   - 段落 [XXXX] ジャンプ
 *   - 手動マーカー（範囲選択 → 1〜6 で色付け / 0 で解除）
 *   - メモ（範囲選択 → c でコメント、注釈付き下線）
 *   - しおり（現在位置を保存）
 *   - 文中検索（Ctrl+F）
 *   - 表示設定（フォント、サイズ、行間、本文幅、ダーク、紙）
 *   - 進捗バー、ヘルプ
 * ========================================================================= */
(() => {
  "use strict";

  const data = window.TEXT_VIEWER_DATA;
  const docs = data.docs || [];
  const COLORS = data.colors || ["red", "blue", "yellow", "green", "purple", "orange"];
  const COLOR_LABELS = { red: "赤", blue: "青", yellow: "黄", green: "緑", purple: "紫", orange: "橙" };

  let currentIndex = data.currentIndex || 0;
  let rawText = "";
  let docKey = "";

  const state = {
    hits: [],
    findHits: [],
    findActiveIdx: -1,
    /** ManualMark: { id, start, end, color, note? } */
    manuals: [],
    findOpen: false,
  };

  /** 表示設定（localStorage で永続化） */
  const settings = loadSettings();

  /* ----- DOM helpers ----- */
  const $ = (id) => document.getElementById(id);
  const content = $("textContent");
  const docSelect = $("docSelect");
  const titleText = $("titleText");
  const docMeta = $("docMeta");
  const markerBar = $("markerBar");
  const progressBar = $("progressBar");
  const sidebar = $("sidebar");
  const tocList = $("tocList");
  const bookmarkList = $("bookmarkList");
  const notesList = $("notesList");
  const findBar = $("findBar");
  const findInput = $("findInput");
  const findCount = $("findCount");
  const settingsPanel = $("settingsPanel");
  const helpDialog = $("helpDialog");
  const commentDialog = $("commentDialog");
  const commentInput = $("commentInput");

  function decodeB64(b64) {
    const bin = atob(b64 || "");
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder("utf-8").decode(bytes);
  }
  function esc(s) {
    return s.replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[ch]));
  }
  function reEsc(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }
  function termInput(color) { return $("term_" + color); }

  /* ----- 設定 ----- */

  function loadSettings() {
    const def = {
      fontSize: 16,
      lineHeight: 1.95,
      readerWidth: 760,
      fontFamily: "sans",
      dark: false,
      paper: false,
    };
    try {
      return Object.assign(def, JSON.parse(localStorage.getItem("tHP_settings_v1") || "{}"));
    } catch (e) { return def; }
  }
  function saveSettings() {
    try { localStorage.setItem("tHP_settings_v1", JSON.stringify(settings)); } catch (e) {}
  }
  function applySettings() {
    const r = document.documentElement;
    r.style.setProperty("--reader-fs", settings.fontSize + "px");
    r.style.setProperty("--reader-lh", String(settings.lineHeight));
    r.style.setProperty("--reader-width", "min(100%, " + settings.readerWidth + "px)");
    document.body.classList.toggle("dark", !!settings.dark);
    document.body.classList.toggle("paper", !!settings.paper && !settings.dark);
    document.body.classList.toggle("serif", settings.fontFamily === "serif");
    if ($("fontSizeR")) $("fontSizeR").value = settings.fontSize;
    if ($("lineHeightR")) $("lineHeightR").value = settings.lineHeight;
    if ($("readerWidthR")) $("readerWidthR").value = settings.readerWidth;
    if ($("fontFamilyS")) $("fontFamilyS").value = settings.fontFamily;
    if ($("darkMode")) $("darkMode").checked = !!settings.dark;
    if ($("paperMode")) $("paperMode").checked = !!settings.paper;
  }

  /* ----- キーワード入力 ----- */

  function getTerms() {
    const terms = [];
    for (const color of COLORS) {
      const el = termInput(color);
      if (!el) continue;
      for (const t of el.value.split(/[\s,，、]+/).map(x => x.trim()).filter(Boolean)) {
        terms.push({ color, text: t });
      }
    }
    terms.sort((a, b) => b.text.length - a.text.length);
    return terms;
  }
  function saveTerms() {
    const obj = {};
    for (const c of COLORS) obj[c] = termInput(c) ? termInput(c).value : "";
    localStorage.setItem("tHP_terms_v2", JSON.stringify(obj));
  }
  function loadTerms() {
    try {
      const v = JSON.parse(localStorage.getItem("tHP_terms_v2") || "{}");
      for (const c of COLORS) {
        const el = termInput(c);
        if (el) el.value = v[c] || "";
      }
    } catch (e) {}
  }

  /* ----- 手動マーカー / メモ ----- */

  function manualKey(idx = currentIndex) {
    const d = docs[idx] || {};
    return "tHP_manual:" + (d.title || idx);
  }
  function loadManuals() {
    try { state.manuals = JSON.parse(localStorage.getItem(manualKey()) || "[]"); }
    catch (e) { state.manuals = []; }
  }
  function saveManuals() {
    try { localStorage.setItem(manualKey(), JSON.stringify(state.manuals)); } catch (e) {}
    refreshNotesPane();
  }

  function bookmarkKey(idx = currentIndex) {
    const d = docs[idx] || {};
    return "tHP_bookmarks:" + (d.title || idx);
  }
  function loadBookmarks() {
    try { return JSON.parse(localStorage.getItem(bookmarkKey()) || "[]"); }
    catch (e) { return []; }
  }
  function saveBookmarks(list) {
    try { localStorage.setItem(bookmarkKey(), JSON.stringify(list)); } catch (e) {}
  }

  /* -------------------------------------------------------------------------
   * 本文レンダリング: rawText -> [segments] にマージしてHTML化
   * セグメントは「文字位置範囲とその種類(kw/manual/find)」の重ね合わせ
   * ----------------------------------------------------------------------- */

  function buildRanges() {
    const terms = getTerms();
    /** range: { start, end, kind: 'kw'|'um'|'find', color, payload } */
    const ranges = [];

    if (terms.length) {
      const pattern = new RegExp(terms.map(t => reEsc(t.text)).join("|"), "gi");
      let m;
      const lower = rawText.toLowerCase();
      while ((m = pattern.exec(rawText)) !== null) {
        const matched = m[0];
        const ml = matched.toLowerCase();
        let found = terms.find(t => t.text.toLowerCase() === ml);
        if (!found) found = terms.find(t => ml.includes(t.text.toLowerCase()));
        ranges.push({
          start: m.index,
          end: m.index + matched.length,
          kind: "kw",
          color: found ? found.color : COLORS[0],
        });
      }
    }

    for (const um of state.manuals) {
      ranges.push({
        start: um.start,
        end: um.end,
        kind: "um",
        color: um.color,
        note: um.note || "",
        id: um.id,
      });
    }

    if (state.findOpen && findInput.value.trim()) {
      const q = findInput.value.trim();
      try {
        const pat = new RegExp(reEsc(q), "gi");
        let m;
        while ((m = pat.exec(rawText)) !== null) {
          ranges.push({ start: m.index, end: m.index + m[0].length, kind: "find" });
        }
      } catch (e) {}
    }
    return ranges;
  }

  function renderText() {
    const ranges = buildRanges();
    if (!ranges.length) {
      content.innerHTML = esc(rawText);
      state.hits = []; state.findHits = [];
      $("hitCount").textContent = "0件";
      updateFindCount();
      renderMarkers();
      buildToc();
      updateProgress();
      return;
    }

    /* 重なり対応: イベントスイープで「いま開いているマーク集合」を持つ */
    const events = [];
    ranges.forEach((r, i) => {
      events.push({ pos: r.start, kind: "open", i });
      events.push({ pos: r.end, kind: "close", i });
    });
    events.sort((a, b) => a.pos - b.pos || (a.kind === "close" ? -1 : 1));

    const open = new Set();
    let cursor = 0;
    let html = "";
    const flush = (toPos) => {
      if (toPos <= cursor) return;
      const piece = esc(rawText.slice(cursor, toPos));
      if (open.size === 0) { html += piece; cursor = toPos; return; }
      // 優先度: kw < um < find （重なったら覚えやすい順序で classes を結合）
      const arr = [...open].map(i => ranges[i]);
      arr.sort((a, b) => ({ kw: 0, um: 1, find: 2 }[a.kind] - { kw: 0, um: 1, find: 2 }[b.kind]));
      const top = arr[arr.length - 1];
      const cls = [top.kind === "find" ? "find" : top.kind, top.color || ""].filter(Boolean).join(" ");
      const noteAttr = top.note ? ` data-note="${esc(top.note)}" title="${esc(top.note)}"` : "";
      const idAttr = top.id ? ` data-mid="${esc(top.id)}"` : "";
      const tag = top.kind === "find" ? "mark" : (top.kind === "um" && top.note ? "mark" : "mark");
      const noteCls = top.kind === "um" && top.note ? " note" : "";
      html += `<${tag} class="${cls}${noteCls}"${noteAttr}${idAttr} data-color="${top.color || ""}">${piece}</${tag}>`;
      cursor = toPos;
    };

    for (const ev of events) {
      flush(ev.pos);
      if (ev.kind === "open") open.add(ev.i);
      else open.delete(ev.i);
    }
    flush(rawText.length);
    content.innerHTML = html;

    state.hits = Array.from(content.querySelectorAll("mark.kw"));
    state.findHits = Array.from(content.querySelectorAll("mark.find"));
    $("hitCount").textContent = state.hits.length ? `${state.hits.length}件` : "0件";
    updateFindCount();
    renderMarkers();
    buildToc();
    updateProgress();
  }

  function renderMarkers() {
    markerBar.innerHTML = "";
    const docH = Math.max(1, document.documentElement.scrollHeight);
    const barH = markerBar.clientHeight || 1;
    for (const hit of state.hits) {
      const dot = document.createElement("div");
      const color = hit.dataset.color || COLORS[0];
      dot.className = "markerDot " + color;
      const pageY = hit.getBoundingClientRect().top + window.scrollY;
      const y = Math.max(0, Math.min(barH - 3, (pageY / docH) * barH));
      dot.style.top = y + "px";
      dot.title = (COLOR_LABELS[color] || color) + ": " + hit.textContent;
      dot.addEventListener("click", () => scrollToHit(hit));
      markerBar.appendChild(dot);
    }
  }

  function scrollToHit(hit) {
    [...state.hits, ...state.findHits].forEach(h => h.classList.remove("active"));
    hit.classList.add("active");
    hit.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  function jumpHit(delta) {
    if (!state.hits.length) return;
    const cur = content.querySelector("mark.kw.active");
    let i = cur ? state.hits.indexOf(cur) : -1;
    i = (i + delta + state.hits.length) % state.hits.length;
    scrollToHit(state.hits[i]);
    $("hitCount").textContent = `${i + 1}/${state.hits.length}`;
  }

  /* ----- 文中検索 ----- */

  function updateFindCount() {
    if (!findCount) return;
    if (state.findOpen && state.findHits.length) {
      const idx = state.findActiveIdx >= 0 ? state.findActiveIdx + 1 : 0;
      findCount.textContent = idx ? `${idx}/${state.findHits.length}` : `${state.findHits.length}件`;
    } else if (state.findOpen) {
      findCount.textContent = findInput.value ? "0件" : "";
    } else {
      findCount.textContent = "";
    }
  }
  function jumpFind(delta) {
    if (!state.findHits.length) return;
    state.findActiveIdx = (state.findActiveIdx + delta + state.findHits.length) % state.findHits.length;
    state.findHits.forEach(h => h.classList.remove("active"));
    state.findHits[state.findActiveIdx].classList.add("active");
    state.findHits[state.findActiveIdx].scrollIntoView({ behavior: "smooth", block: "center" });
    updateFindCount();
  }
  function setFindOpen(open) {
    state.findOpen = open;
    findBar.classList.toggle("hidden", !open);
    if (open) {
      findInput.focus();
      findInput.select();
    } else {
      state.findActiveIdx = -1;
      renderText();
    }
  }

  /* ----- 目次（特許文書の【...】見出し自動抽出） ----- */

  /** 「【発明の名称】」「【0001】」「【特許文献１】」など。
   *  数字/段落番号系（[0-9]+）は本文中の段落番号としてスキップ。 */
  function buildToc() {
    if (!tocList) return;
    tocList.innerHTML = "";
    const re = /^[\u3000\s]*【([^】\n]+)】/gm;
    const items = [];
    let m;
    while ((m = re.exec(rawText)) !== null) {
      const label = m[1].trim();
      if (/^\d+$/.test(label)) continue;
      const level = guessTocLevel(label);
      items.push({ pos: m.index, label, level });
    }
    if (!items.length) {
      const li = document.createElement("li");
      li.className = "muted";
      li.textContent = "(見出し【...】が見つかりませんでした)";
      tocList.appendChild(li);
      return;
    }
    for (const it of items) {
      const li = document.createElement("li");
      li.className = "tocLevel-" + it.level;
      li.textContent = it.label;
      li.title = it.label;
      li.addEventListener("click", () => scrollToCharIndex(it.pos));
      tocList.appendChild(li);
    }
  }
  function guessTocLevel(label) {
    if (/^(特許請求の範囲|明細書|要約書|図面|発明の名称)$/.test(label)) return 1;
    if (/^(技術分野|背景技術|発明の概要|発明が解決しようとする課題|課題を解決するための手段|発明の効果|図面の簡単な説明|発明を実施するための形態|実施例|産業上の利用可能性|符号の説明|請求項.*)$/.test(label)) return 2;
    return 3;
  }

  /* ----- 文字位置(rawText のインデックス) → DOM Range 変換 ----- */

  function nodeAtCharIndex(idx) {
    const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT);
    let acc = 0;
    let node;
    while ((node = walker.nextNode())) {
      const len = node.nodeValue.length;
      if (acc + len >= idx) return { node, offset: idx - acc };
      acc += len;
    }
    return null;
  }
  function scrollToCharIndex(idx) {
    const at = nodeAtCharIndex(idx);
    if (!at) return;
    const range = document.createRange();
    range.setStart(at.node, at.offset);
    range.setEnd(at.node, Math.min(at.node.nodeValue.length, at.offset + 1));
    const rect = range.getBoundingClientRect();
    window.scrollTo({ top: rect.top + window.scrollY - 100, behavior: "smooth" });
  }

  /** 現在の選択範囲を rawText のインデックスに変換 */
  function selectionToCharRange() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null;
    const r = sel.getRangeAt(0);
    if (!content.contains(r.commonAncestorContainer)) return null;

    const charIndexOf = (node, offset) => {
      const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT);
      let acc = 0;
      let n;
      while ((n = walker.nextNode())) {
        if (n === node) return acc + offset;
        acc += n.nodeValue.length;
      }
      return -1;
    };
    const start = charIndexOf(r.startContainer, r.startOffset);
    const end = charIndexOf(r.endContainer, r.endOffset);
    if (start < 0 || end < 0 || end <= start) return null;
    return { start, end };
  }

  /* ----- 段落[XXXX]ジャンプ ----- */

  function jumpToParagraph(num) {
    const padded = String(num).padStart(4, "0");
    const re = new RegExp("【\\s*" + padded + "\\s*】");
    const m = rawText.match(re);
    if (!m) {
      alert("段落[" + padded + "] が見つかりませんでした");
      return false;
    }
    scrollToCharIndex(m.index);
    return true;
  }

  /* ----- メモ・しおり用パネル ----- */

  function refreshNotesPane() {
    if (!notesList) return;
    notesList.innerHTML = "";
    const noted = state.manuals.filter(u => u.note);
    if (!noted.length) {
      const empty = document.createElement("li");
      empty.className = "notesEmpty";
      empty.textContent = "(メモはまだありません。テキストを選択して c でメモ追加)";
      notesList.appendChild(empty);
      return;
    }
    for (const u of noted) {
      const li = document.createElement("li");
      const snippet = rawText.slice(u.start, u.end).slice(0, 28);
      const head = document.createElement("span");
      head.style.color = "var(--dot-" + u.color + ")";
      head.textContent = "■ ";
      const body = document.createElement("span");
      body.textContent = snippet + " — " + u.note;
      li.appendChild(head);
      li.appendChild(body);
      li.addEventListener("click", () => scrollToCharIndex(u.start));
      notesList.appendChild(li);
    }
  }

  function refreshBookmarksPane() {
    if (!bookmarkList) return;
    bookmarkList.innerHTML = "";
    const list = loadBookmarks();
    if (!list.length) {
      const empty = document.createElement("li");
      empty.className = "notesEmpty";
      empty.textContent = "(しおりはまだありません。 + ボタンか B キーで追加)";
      bookmarkList.appendChild(empty);
      return;
    }
    for (const b of list) {
      const li = document.createElement("li");
      const t = b.snippet ? b.snippet.slice(0, 32) : `位置 ${b.charIndex}`;
      li.textContent = t;
      li.title = new Date(b.ts).toLocaleString();
      li.addEventListener("click", () => scrollToCharIndex(b.charIndex));
      bookmarkList.appendChild(li);
    }
  }

  function addBookmarkAtCurrent() {
    const at = topVisibleCharIndex();
    if (at < 0) return;
    const list = loadBookmarks();
    list.push({
      ts: Date.now(),
      charIndex: at,
      snippet: rawText.slice(at, at + 40).replace(/\s+/g, " "),
    });
    saveBookmarks(list);
    refreshBookmarksPane();
  }

  function topVisibleCharIndex() {
    const top = window.scrollY + 100;
    const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT);
    let acc = 0;
    let n;
    while ((n = walker.nextNode())) {
      const r = document.createRange();
      r.selectNodeContents(n);
      const rect = r.getBoundingClientRect();
      const absTop = rect.top + window.scrollY;
      if (absTop + rect.height >= top) {
        return acc;
      }
      acc += n.nodeValue.length;
    }
    return acc;
  }

  /* ----- 文献切替 ----- */

  function setDoc(idx) {
    if (idx < 0 || idx >= docs.length) return;
    const doc = docs[idx];
    if (!doc.b64 && doc.href) {
      location.href = doc.href;
      return;
    }
    currentIndex = idx;
    rawText = decodeB64(doc.b64);
    docKey = doc.title || ("doc_" + idx);
    titleText.textContent = doc.title;
    document.title = doc.title;
    if (docSelect) docSelect.value = String(idx);

    const lines = rawText ? rawText.split(/\r\n|\r|\n/).length : 0;
    const metaText = `${idx + 1}/${docs.length}　${rawText.length.toLocaleString()}字　${lines.toLocaleString()}行`;
    docMeta.querySelector(".docMetaText").textContent = metaText;

    loadManuals();
    refreshBookmarksPane();
    setFindOpen(false);
    window.scrollTo(0, 0);
    renderText();
  }
  function moveDoc(delta) {
    let idx = currentIndex + delta;
    if (idx < 0) idx = docs.length - 1;
    if (idx >= docs.length) idx = 0;
    setDoc(idx);
  }
  function initSelect() {
    if (!docSelect) return;
    docSelect.innerHTML = "";
    docs.forEach((d, i) => {
      const opt = document.createElement("option");
      opt.value = String(i);
      opt.textContent = `${i + 1}. ${d.title}`;
      docSelect.appendChild(opt);
    });
    docSelect.addEventListener("change", () => setDoc(Number(docSelect.value)));
  }

  /* ----- 進捗 ----- */

  function updateProgress() {
    const h = document.documentElement;
    const max = h.scrollHeight - h.clientHeight;
    const v = max > 0 ? (h.scrollTop / max) : 0;
    progressBar.style.width = (v * 100).toFixed(2) + "%";
  }

  /* ----- 手動マーカー操作 ----- */

  function addManualFromSelection(color, opts = {}) {
    const r = selectionToCharRange();
    if (!r) return;
    /* 同色で完全包含されている既存マークがあれば、削除して塗り直す */
    state.manuals = state.manuals.filter(u => !(u.start >= r.start && u.end <= r.end && u.color === color && !u.note));
    state.manuals.push({
      id: "u" + Math.random().toString(36).slice(2, 9),
      start: r.start,
      end: r.end,
      color,
      note: opts.note || "",
    });
    window.getSelection().removeAllRanges();
    saveManuals();
    renderText();
  }
  function removeManualAtSelection() {
    const r = selectionToCharRange();
    if (!r) return;
    const before = state.manuals.length;
    state.manuals = state.manuals.filter(u => !(u.start < r.end && u.end > r.start));
    if (state.manuals.length !== before) {
      saveManuals();
      renderText();
    }
    window.getSelection().removeAllRanges();
  }

  function openCommentDialog() {
    const r = selectionToCharRange();
    if (!r) return;
    pendingComment = r;
    commentInput.value = "";
    commentDialog.classList.remove("hidden");
    setTimeout(() => commentInput.focus(), 30);
  }
  let pendingComment = null;

  /* ----- ヘルプ ----- */

  function toggleDialog(el, show) {
    if (typeof show !== "boolean") show = el.classList.contains("hidden");
    el.classList.toggle("hidden", !show);
  }

  /* ----- 初期化 ----- */

  function init() {
    applySettings();
    loadTerms();
    initSelect();
    setupSidebar();
    setupTopbar();
    setupSettings();
    setupFind();
    setupComment();
    setupHelp();

    window.addEventListener("scroll", () => { updateProgress(); }, { passive: true });
    window.addEventListener("resize", () => setTimeout(renderMarkers, 40));
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("click", onContentClick);

    setDoc(currentIndex);
  }

  function setupTopbar() {
    $("toggleSidebar").addEventListener("click", () => sidebar.classList.toggle("open"));
    $("prevDoc").addEventListener("click", () => moveDoc(-1));
    $("nextDoc").addEventListener("click", () => moveDoc(1));
    $("prevHit").addEventListener("click", () => jumpHit(-1));
    $("nextHit").addEventListener("click", () => jumpHit(1));
    $("clearTerms").addEventListener("click", () => {
      for (const c of COLORS) {
        const el = termInput(c);
        if (el) el.value = "";
      }
      saveTerms();
      renderText();
    });
    for (const c of COLORS) {
      const el = termInput(c);
      if (!el) continue;
      el.addEventListener("input", () => { saveTerms(); renderText(); });
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); jumpHit(e.shiftKey ? -1 : 1); }
      });
    }
    $("zenBtn").addEventListener("click", () => document.body.classList.toggle("zen"));
    $("findBtn").addEventListener("click", () => setFindOpen(!state.findOpen));
    $("paraBtn").addEventListener("click", askParagraphJump);
    $("settingsBtn").addEventListener("click", () => settingsPanel.classList.toggle("hidden"));
    $("helpBtn").addEventListener("click", () => toggleDialog(helpDialog, true));
  }

  function setupSidebar() {
    document.querySelectorAll(".sidebarTab").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelectorAll(".sidebarTab").forEach(x => x.classList.remove("active"));
        document.querySelectorAll(".sidebarPane").forEach(x => x.classList.remove("active"));
        b.classList.add("active");
        document.getElementById(b.dataset.target).classList.add("active");
      });
    });
    $("addBookmark").addEventListener("click", addBookmarkAtCurrent);
  }

  function setupSettings() {
    $("fontSizeR").addEventListener("input", e => { settings.fontSize = Number(e.target.value); applySettings(); saveSettings(); });
    $("lineHeightR").addEventListener("input", e => { settings.lineHeight = Number(e.target.value); applySettings(); saveSettings(); });
    $("readerWidthR").addEventListener("input", e => { settings.readerWidth = Number(e.target.value); applySettings(); saveSettings(); });
    $("fontFamilyS").addEventListener("change", e => { settings.fontFamily = e.target.value; applySettings(); saveSettings(); });
    $("darkMode").addEventListener("change", e => { settings.dark = e.target.checked; applySettings(); saveSettings(); });
    $("paperMode").addEventListener("change", e => { settings.paper = e.target.checked; applySettings(); saveSettings(); });
    $("settingsClose").addEventListener("click", () => settingsPanel.classList.add("hidden"));
  }

  function setupFind() {
    findInput.addEventListener("input", () => { renderText(); state.findActiveIdx = -1; });
    findInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); jumpFind(e.shiftKey ? -1 : 1); }
      else if (e.key === "Escape") setFindOpen(false);
    });
    $("findPrev").addEventListener("click", () => jumpFind(-1));
    $("findNext").addEventListener("click", () => jumpFind(1));
    $("findClose").addEventListener("click", () => setFindOpen(false));
  }

  function setupComment() {
    $("commentSave").addEventListener("click", () => {
      if (!pendingComment) { commentDialog.classList.add("hidden"); return; }
      const note = commentInput.value.trim();
      const r = pendingComment;
      pendingComment = null;
      commentDialog.classList.add("hidden");
      if (!note) return;
      state.manuals.push({
        id: "u" + Math.random().toString(36).slice(2, 9),
        start: r.start,
        end: r.end,
        color: "yellow",
        note,
      });
      saveManuals();
      renderText();
    });
    $("commentCancel").addEventListener("click", () => {
      pendingComment = null;
      commentDialog.classList.add("hidden");
    });
  }

  function setupHelp() {
    $("helpClose").addEventListener("click", () => toggleDialog(helpDialog, false));
    helpDialog.addEventListener("click", (e) => { if (e.target === helpDialog) toggleDialog(helpDialog, false); });
  }

  function askParagraphJump() {
    const v = prompt("段落番号を入力してください（例: 23 または 0023）", "");
    if (!v) return;
    const n = Number(v.replace(/\D+/g, ""));
    if (Number.isFinite(n) && n > 0) jumpToParagraph(n);
  }

  function onContentClick(e) {
    const m = e.target.closest("mark.um.note");
    if (m && m.dataset.note) {
      // メモのトーストを簡易表示
      const note = m.dataset.note;
      alert("メモ:\n" + note);
    }
  }

  function onKeyDown(e) {
    const tag = e.target && e.target.tagName;
    const inField = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
    /* 文中検索 */
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
      e.preventDefault(); setFindOpen(true); return;
    }
    if (inField) return;

    /* 数字キー（手動マーカー）: 1〜6 で色付け、0 で消去 */
    if (/^[1-6]$/.test(e.key)) {
      e.preventDefault();
      addManualFromSelection(COLORS[Number(e.key) - 1]);
      return;
    }
    if (e.key === "0") { e.preventDefault(); removeManualAtSelection(); return; }
    if (e.key === "c") { e.preventDefault(); openCommentDialog(); return; }

    if (e.key === "[" || e.key === "ArrowLeft") moveDoc(-1);
    else if (e.key === "]" || e.key === "ArrowRight") moveDoc(1);
    else if (e.key === "n") jumpHit(1);
    else if (e.key === "p") jumpHit(-1);
    else if (e.key === "/") { e.preventDefault(); const f = termInput(COLORS[0]); if (f) f.focus(); }
    else if (e.key === "g") askParagraphJump();
    else if (e.key === "b") sidebar.classList.toggle("open");
    else if (e.key === "B") addBookmarkAtCurrent();
    else if (e.key === "s") settingsPanel.classList.toggle("hidden");
    else if (e.key === "d") { settings.dark = !settings.dark; applySettings(); saveSettings(); }
    else if (e.key === "z") document.body.classList.toggle("zen");
    else if (e.key === "?") toggleDialog(helpDialog, true);
    else if (e.key === "Escape") {
      document.body.classList.remove("zen");
      sidebar.classList.remove("open");
      settingsPanel.classList.add("hidden");
      toggleDialog(helpDialog, false);
      if (state.findOpen) setFindOpen(false);
    }
  }

  init();
})();
