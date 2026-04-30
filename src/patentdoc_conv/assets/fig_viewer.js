/* =========================================================================
 * fig_viewer.js
 *   - 自由ペン / 蛍光ペン / 直線 / 矩形 / 楕円 / 矢印 / テキスト / 消しゴム
 *   - Undo / Redo
 *   - 書き込みのJSON エクスポート / インポート
 *   - パン（手のひら）モード、フィット、ズームイン/アウト
 *   - ダーク反転表示、ヘルプ
 * ========================================================================= */
(() => {
  "use strict";

  const data = window.FIG_VIEWER_DATA;
  const figures = data.figures || [];
  let currentIndex = data.currentIndex || 0;

  const TOOLS = ["pen", "highlight", "line", "rect", "ellipse", "arrow", "text", "erase", "pan"];
  const COLORS = ["#111111", "#cc0000", "#0058ff", "#ffd200", "#1e9e4a", "#8a2cd1"];

  let img = new Image();
  let rotation = 0;
  let zoom = 0.3;
  const DEFAULT_ZOOM = 0.3;
  let drawing = false;
  let currentTool = "pen";
  let currentColor = "#111111";
  let currentSize = 4;

  /** stroke schema:
   *   { id, rotation, tool, color, size, points?:[{x,y}], rect?:{x,y,w,h}, text? } */
  let strokes = [];
  let undone = [];
  let liveStroke = null;
  let textOverlayEl = null;

  const $ = (id) => document.getElementById(id);
  const canvas = $("figCanvas");
  const ctx = canvas.getContext("2d", { willReadFrequently: false });
  const figSelect = $("figSelect");
  const titleText = $("titleText");
  const figMeta = $("figMeta");
  const shell = $("figShell");
  const overlay = $("canvasOverlay");
  const helpDialog = $("helpDialog");

  /* ----- 永続化 ----- */

  function storageKey(idx = currentIndex) {
    const f = figures[idx] || { title: "unknown" };
    return "tHP_fig_strokes_v2:" + f.title;
  }
  function rotationKey(idx = currentIndex) {
    const f = figures[idx] || { title: "unknown" };
    return "tHP_fig_rotation:" + f.title;
  }
  function settingsKey() { return "tHP_fig_settings_v1"; }
  function loadStrokes() {
    try {
      const raw = JSON.parse(localStorage.getItem(storageKey()) || "[]");
      // 旧フォーマット互換: tool 未指定なら "pen" 扱い
      strokes = raw.map(s => Object.assign({ tool: "pen", id: "s" + Math.random().toString(36).slice(2, 9) }, s));
    } catch (e) { strokes = []; }
    undone = [];
  }
  function saveStrokes() {
    try { localStorage.setItem(storageKey(), JSON.stringify(strokes)); }
    catch (e) { console.warn("localStorage保存に失敗しました", e); }
  }
  function loadGlobalSettings() {
    try { return JSON.parse(localStorage.getItem(settingsKey()) || "{}"); }
    catch (e) { return {}; }
  }
  function saveGlobalSettings(s) {
    try { localStorage.setItem(settingsKey(), JSON.stringify(s)); } catch (e) {}
  }

  /* ----- サイズ計算 ----- */

  function rotatedSize() {
    const odd = rotation % 180 !== 0;
    return {
      w: odd ? img.naturalHeight : img.naturalWidth,
      h: odd ? img.naturalWidth : img.naturalHeight,
    };
  }
  function fitZoom() {
    const s = rotatedSize();
    const maxW = Math.max(400, shell.clientWidth - 48);
    zoom = Math.min(1.0, maxW / Math.max(1, s.w));
    if (!Number.isFinite(zoom) || zoom <= 0) zoom = 1;
  }

  /* ----- 描画 ----- */

  function drawBaseImage() {
    const s = rotatedSize();
    canvas.width = s.w;
    canvas.height = s.h;
    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    if (rotation === 0) {
      ctx.drawImage(img, 0, 0);
    } else if (rotation === 90) {
      ctx.translate(canvas.width, 0);
      ctx.rotate(Math.PI / 2);
      ctx.drawImage(img, 0, 0);
    } else if (rotation === 180) {
      ctx.translate(canvas.width, canvas.height);
      ctx.rotate(Math.PI);
      ctx.drawImage(img, 0, 0);
    } else if (rotation === 270) {
      ctx.translate(0, canvas.height);
      ctx.rotate(3 * Math.PI / 2);
      ctx.drawImage(img, 0, 0);
    }
    ctx.restore();
  }

  function drawStroke(st) {
    if (!st) return;
    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = st.color;
    ctx.fillStyle = st.color;
    ctx.lineWidth = st.size;
    ctx.globalAlpha =
      st.tool === "highlight" ? 0.30
      : (st.color === "#ffd200" ? 0.65 : 0.95);

    if (st.tool === "pen" || st.tool === "highlight") {
      const p = st.points || [];
      if (!p.length) { ctx.restore(); return; }
      if (st.tool === "highlight") {
        ctx.lineWidth = st.size * 4;
        ctx.lineCap = "butt";
      }
      ctx.beginPath();
      ctx.moveTo(p[0].x, p[0].y);
      for (let i = 1; i < p.length; i++) ctx.lineTo(p[i].x, p[i].y);
      ctx.stroke();
    } else if (st.tool === "line" || st.tool === "arrow") {
      const p = st.points || [];
      if (p.length < 2) { ctx.restore(); return; }
      const a = p[0], b = p[p.length - 1];
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      if (st.tool === "arrow") {
        const ang = Math.atan2(b.y - a.y, b.x - a.x);
        const head = Math.max(10, st.size * 3);
        ctx.beginPath();
        ctx.moveTo(b.x, b.y);
        ctx.lineTo(b.x - head * Math.cos(ang - Math.PI / 7), b.y - head * Math.sin(ang - Math.PI / 7));
        ctx.lineTo(b.x - head * Math.cos(ang + Math.PI / 7), b.y - head * Math.sin(ang + Math.PI / 7));
        ctx.closePath();
        ctx.fill();
      }
    } else if (st.tool === "rect") {
      const r = st.rect; if (!r) { ctx.restore(); return; }
      ctx.strokeRect(r.x, r.y, r.w, r.h);
    } else if (st.tool === "ellipse") {
      const r = st.rect; if (!r) { ctx.restore(); return; }
      ctx.beginPath();
      ctx.ellipse(r.x + r.w / 2, r.y + r.h / 2, Math.abs(r.w / 2), Math.abs(r.h / 2), 0, 0, Math.PI * 2);
      ctx.stroke();
    } else if (st.tool === "text") {
      if (st.text == null || st.rect == null) { ctx.restore(); return; }
      const fontSize = Math.max(12, st.size * 4);
      ctx.font = `${fontSize}px "Yu Gothic UI", "Yu Gothic", Meiryo, "Noto Sans JP", sans-serif`;
      ctx.textBaseline = "top";
      ctx.globalAlpha = 1.0;
      const lines = String(st.text).split(/\r\n|\r|\n/);
      for (let i = 0; i < lines.length; i++) {
        ctx.fillText(lines[i], st.rect.x, st.rect.y + i * fontSize * 1.25);
      }
    }
    ctx.restore();
  }

  function render() {
    drawBaseImage();
    for (const st of strokes.filter(s => s.rotation === rotation)) drawStroke(st);
    if (liveStroke && liveStroke.rotation === rotation) drawStroke(liveStroke);
    canvas.style.width = Math.round(canvas.width * zoom) + "px";
    canvas.style.height = Math.round(canvas.height * zoom) + "px";
    figMeta.textContent = `${currentIndex + 1}/${figures.length}　${img.naturalWidth}×${img.naturalHeight}px　表示${Math.round(zoom * 100)}%　回転${rotation}°　[${TOOL_LABEL[currentTool] || currentTool}]`;
  }

  const TOOL_LABEL = {
    pen: "ペン", highlight: "蛍光", line: "直線", rect: "矩形",
    ellipse: "楕円", arrow: "矢印", text: "テキスト", erase: "消しゴム", pan: "手"
  };

  /* ----- 入力 ----- */

  function canvasPoint(e) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) * canvas.width / rect.width,
      y: (e.clientY - rect.top) * canvas.height / rect.height,
    };
  }

  function setTool(name) {
    currentTool = name;
    document.querySelectorAll(".toolBtn[data-tool]").forEach(b => {
      b.classList.toggle("active", b.dataset.tool === name);
    });
    document.body.classList.remove(
      "tool-pen", "tool-highlight", "tool-line", "tool-rect",
      "tool-ellipse", "tool-arrow", "tool-text", "tool-erase", "tool-pan"
    );
    document.body.classList.add("tool-" + name);
  }

  function setColor(color) {
    currentColor = color;
    document.querySelectorAll(".toolColor").forEach(b => {
      b.classList.toggle("active", b.dataset.color === color);
    });
  }

  function beginInteract(e) {
    if (currentTool === "pan") return;
    e.preventDefault();
    const p = canvasPoint(e);

    if (currentTool === "erase") {
      eraseAt(p);
      drawing = true;
      return;
    }
    if (currentTool === "text") {
      drawing = false;
      openTextEditor(p);
      return;
    }

    drawing = true;
    if (currentTool === "pen" || currentTool === "highlight") {
      liveStroke = { id: newId(), rotation, tool: currentTool, color: currentColor, size: currentSize, points: [p] };
    } else if (currentTool === "line" || currentTool === "arrow") {
      liveStroke = { id: newId(), rotation, tool: currentTool, color: currentColor, size: currentSize, points: [p, p] };
    } else if (currentTool === "rect" || currentTool === "ellipse") {
      liveStroke = { id: newId(), rotation, tool: currentTool, color: currentColor, size: currentSize, rect: { x: p.x, y: p.y, w: 0, h: 0 } };
    }
    render();
  }

  function moveInteract(e) {
    if (!drawing) return;
    e.preventDefault();
    const p = canvasPoint(e);
    if (currentTool === "erase") {
      eraseAt(p);
      return;
    }
    if (!liveStroke) return;
    if (currentTool === "pen" || currentTool === "highlight") {
      liveStroke.points.push(p);
    } else if (currentTool === "line" || currentTool === "arrow") {
      liveStroke.points[1] = p;
    } else if (currentTool === "rect" || currentTool === "ellipse") {
      liveStroke.rect.w = p.x - liveStroke.rect.x;
      liveStroke.rect.h = p.y - liveStroke.rect.y;
    }
    render();
  }

  function endInteract(e) {
    if (!drawing) return;
    e && e.preventDefault();
    drawing = false;
    if (currentTool === "erase") return;
    if (!liveStroke) return;
    /* 0 サイズの図形は破棄 */
    if (liveStroke.rect && Math.abs(liveStroke.rect.w) < 2 && Math.abs(liveStroke.rect.h) < 2) {
      liveStroke = null; render(); return;
    }
    if (liveStroke.points && liveStroke.points.length === 2) {
      const a = liveStroke.points[0], b = liveStroke.points[1];
      if (Math.hypot(a.x - b.x, a.y - b.y) < 2) { liveStroke = null; render(); return; }
    }
    if (liveStroke.rect) {
      if (liveStroke.rect.w < 0) { liveStroke.rect.x += liveStroke.rect.w; liveStroke.rect.w = -liveStroke.rect.w; }
      if (liveStroke.rect.h < 0) { liveStroke.rect.y += liveStroke.rect.h; liveStroke.rect.h = -liveStroke.rect.h; }
    }
    strokes.push(liveStroke);
    undone = [];
    liveStroke = null;
    saveStrokes();
    render();
  }

  function eraseAt(p) {
    const radius = currentSize * 4;
    let removed = false;
    strokes = strokes.filter(s => {
      if (s.rotation !== rotation) return true;
      if (strokeContainsPoint(s, p, radius)) { removed = true; return false; }
      return true;
    });
    if (removed) { saveStrokes(); render(); }
  }
  function strokeContainsPoint(s, p, radius) {
    if (s.tool === "pen" || s.tool === "highlight") {
      const r = (s.tool === "highlight" ? s.size * 4 : s.size) / 2 + radius;
      return (s.points || []).some(q => Math.hypot(q.x - p.x, q.y - p.y) <= r);
    }
    if (s.tool === "line" || s.tool === "arrow") {
      const [a, b] = s.points || [];
      if (!a || !b) return false;
      return distancePointToSeg(p, a, b) <= radius + s.size / 2;
    }
    if (s.tool === "rect" || s.tool === "ellipse" || s.tool === "text") {
      const r = s.rect || { x: 0, y: 0, w: 0, h: 0 };
      return p.x >= r.x - radius && p.x <= r.x + r.w + radius && p.y >= r.y - radius && p.y <= r.y + r.h + radius;
    }
    return false;
  }
  function distancePointToSeg(p, a, b) {
    const dx = b.x - a.x, dy = b.y - a.y;
    const len2 = dx * dx + dy * dy;
    if (len2 === 0) return Math.hypot(p.x - a.x, p.y - a.y);
    let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / len2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
  }

  function newId() { return "s" + Math.random().toString(36).slice(2, 9); }

  /* ----- テキスト注釈 ----- */

  function openTextEditor(p) {
    if (textOverlayEl) finishTextEditor(false);
    const wrap = document.querySelector(".canvasWrap");
    const wrapRect = wrap.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();
    const ta = document.createElement("textarea");
    ta.className = "textInputOverlay";
    /* canvas座標 -> 画面座標 へ */
    const left = (canvasRect.left - wrapRect.left) + (p.x / canvas.width) * canvasRect.width;
    const top = (canvasRect.top - wrapRect.top) + (p.y / canvas.height) * canvasRect.height;
    ta.style.left = left + "px";
    ta.style.top = top + "px";
    ta.style.minWidth = "120px";
    ta.style.minHeight = "1.4em";
    ta.style.color = currentColor;
    ta.dataset.canvasX = String(p.x);
    ta.dataset.canvasY = String(p.y);
    wrap.appendChild(ta);
    textOverlayEl = ta;
    setTimeout(() => ta.focus(), 30);
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { e.preventDefault(); finishTextEditor(false); }
      else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); finishTextEditor(true); }
    });
    ta.addEventListener("blur", () => finishTextEditor(true));
  }
  function finishTextEditor(commit) {
    const ta = textOverlayEl;
    if (!ta) return;
    textOverlayEl = null;
    const text = ta.value.trim();
    const x = Number(ta.dataset.canvasX);
    const y = Number(ta.dataset.canvasY);
    ta.remove();
    if (commit && text) {
      const fontSize = Math.max(12, currentSize * 4);
      const lines = text.split(/\r\n|\r|\n/);
      const w = 1; // 後で extend 可。最低幅
      const h = lines.length * fontSize * 1.25;
      strokes.push({ id: newId(), rotation, tool: "text", color: currentColor, size: currentSize, text, rect: { x, y, w, h } });
      undone = [];
      saveStrokes();
      render();
    }
  }

  /* ----- 図切替 ----- */

  function setFigure(idx) {
    if (idx < 0) idx = figures.length - 1;
    if (idx >= figures.length) idx = 0;
    currentIndex = idx;
    const fig = figures[idx];
    titleText.textContent = fig.title;
    document.title = fig.title;
    if (figSelect) figSelect.value = String(idx);
    img = new Image();
    img.onload = () => {
      const savedRot = Number(localStorage.getItem(rotationKey()));
      if ([0, 90, 180, 270].includes(savedRot)) rotation = savedRot;
      else rotation = (data.autoLandscape && img.naturalHeight > img.naturalWidth) ? 90 : 0;
      loadStrokes();
      zoom = DEFAULT_ZOOM;
      render();
      shell.scrollTo({ top: 0, left: 0 });
    };
    img.onerror = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      titleText.textContent = "画像を読み込めません: " + fig.title;
    };
    img.src = fig.src;
  }
  function moveFigure(delta) { setFigure(currentIndex + delta); }
  function rotate(delta) {
    rotation = (rotation + delta + 360) % 360;
    localStorage.setItem(rotationKey(), String(rotation));
    zoom = DEFAULT_ZOOM; render();
  }

  /* ----- Undo / Redo ----- */

  function undo() {
    /* 最後の "現在の回転" のストロークを 1 つ取り消す */
    for (let i = strokes.length - 1; i >= 0; i--) {
      if (strokes[i].rotation === rotation) {
        undone.push(strokes.splice(i, 1)[0]);
        saveStrokes(); render();
        return;
      }
    }
  }
  function redo() {
    if (!undone.length) return;
    const s = undone.pop();
    strokes.push(s);
    saveStrokes();
    render();
  }

  /* ----- 書き込みエクスポート / インポート ----- */

  function exportJSON() {
    const fig = figures[currentIndex];
    const payload = {
      type: "tHP_fig_strokes",
      version: 2,
      figure: fig.title,
      exportedAt: new Date().toISOString(),
      strokes,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    const base = (fig.title || "figure").replace(/[\\/:*?\"<>|\s]+/g, "_");
    a.download = `${base}_annotations.json`;
    a.href = URL.createObjectURL(blob);
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1500);
  }
  function importJSONFile(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const j = JSON.parse(reader.result);
        const next = Array.isArray(j) ? j : (j.strokes || []);
        const repl = confirm("読み込み内容で現在の書き込みを置き換えますか？\n（OK=置換 / キャンセル=追加）");
        if (repl) strokes = [];
        for (const s of next) {
          strokes.push(Object.assign({ tool: "pen", id: newId() }, s));
        }
        undone = [];
        saveStrokes();
        render();
      } catch (e) {
        alert("読み込みに失敗しました: " + e.message);
      }
    };
    reader.readAsText(file, "utf-8");
  }

  /* ----- パン（手のひら） ----- */

  let panState = null;
  function panStart(e) {
    if (currentTool !== "pan") return;
    panState = { x: e.clientX, y: e.clientY, sx: shell.scrollLeft, sy: shell.scrollTop };
    document.body.classList.add("panning");
    e.preventDefault();
  }
  function panMove(e) {
    if (!panState) return;
    shell.scrollLeft = panState.sx - (e.clientX - panState.x);
    shell.scrollTop = panState.sy - (e.clientY - panState.y);
    e.preventDefault();
  }
  function panEnd() {
    panState = null;
    document.body.classList.remove("panning");
  }

  /* ----- PNG保存 ----- */

  function downloadPng() {
    render();
    const a = document.createElement("a");
    const base = (figures[currentIndex].title || "figure").replace(/[\\/:*?\"<>|\s]+/g, "_");
    a.download = `${base}_annotated.png`;
    a.href = canvas.toDataURL("image/png");
    a.click();
  }

  /* ----- セレクト・ヘルプ ----- */

  function initSelect() {
    figSelect.innerHTML = "";
    figures.forEach((f, i) => {
      const opt = document.createElement("option");
      opt.value = String(i);
      opt.textContent = `${i + 1}. ${f.title}`;
      figSelect.appendChild(opt);
    });
    figSelect.addEventListener("change", () => setFigure(Number(figSelect.value)));
  }

  function init() {
    /* 設定復元 */
    const gs = loadGlobalSettings();
    if (gs.tool && TOOLS.includes(gs.tool)) currentTool = gs.tool;
    if (gs.color && COLORS.includes(gs.color)) currentColor = gs.color;
    if (gs.size) currentSize = Number(gs.size) || 4;
    if (gs.dark) document.body.classList.add("dark");
    setTool(currentTool);
    setColor(currentColor);
    $("brushSize").value = currentSize;

    initSelect();

    $("prevFig").addEventListener("click", () => moveFigure(-1));
    $("nextFig").addEventListener("click", () => moveFigure(1));
    $("rotL").addEventListener("click", () => rotate(270));
    $("rotR").addEventListener("click", () => rotate(90));
    $("fitBtn").addEventListener("click", () => { fitZoom(); render(); });
    $("zoomIn").addEventListener("click", () => { zoom = Math.min(4, zoom * 1.2); render(); });
    $("zoomOut").addEventListener("click", () => { zoom = Math.max(0.1, zoom / 1.2); render(); });
    $("undoBtn").addEventListener("click", undo);
    $("redoBtn").addEventListener("click", redo);
    $("clearBtn").addEventListener("click", () => {
      if (confirm("この図の書き込みをすべて消しますか？")) {
        strokes = strokes.filter(s => s.rotation !== rotation);
        undone = [];
        saveStrokes();
        render();
      }
    });
    $("savePng").addEventListener("click", downloadPng);
    $("exportJson").addEventListener("click", exportJSON);
    $("importJson").addEventListener("change", (e) => {
      const f = e.target.files && e.target.files[0];
      if (f) importJSONFile(f);
      e.target.value = "";
    });
    $("darkBtn").addEventListener("click", () => {
      document.body.classList.toggle("dark");
      const s = loadGlobalSettings();
      s.dark = document.body.classList.contains("dark");
      saveGlobalSettings(s);
    });
    $("helpBtn").addEventListener("click", () => helpDialog.classList.toggle("hidden"));
    $("helpClose").addEventListener("click", () => helpDialog.classList.add("hidden"));
    helpDialog.addEventListener("click", (e) => { if (e.target === helpDialog) helpDialog.classList.add("hidden"); });

    document.querySelectorAll(".toolBtn[data-tool]").forEach(b => {
      b.addEventListener("click", () => {
        setTool(b.dataset.tool);
        const s = loadGlobalSettings(); s.tool = currentTool; saveGlobalSettings(s);
      });
    });
    document.querySelectorAll(".toolColor").forEach(b => {
      b.addEventListener("click", () => {
        setColor(b.dataset.color);
        const s = loadGlobalSettings(); s.color = currentColor; saveGlobalSettings(s);
      });
    });
    $("brushSize").addEventListener("input", (e) => {
      currentSize = Number(e.target.value) || 4;
      const s = loadGlobalSettings(); s.size = currentSize; saveGlobalSettings(s);
    });

    canvas.addEventListener("pointerdown", (e) => {
      if (currentTool === "pan") panStart(e);
      else beginInteract(e);
    });
    canvas.addEventListener("pointermove", (e) => {
      if (panState) panMove(e);
      else moveInteract(e);
    });
    canvas.addEventListener("pointerup", (e) => {
      if (panState) panEnd();
      else endInteract(e);
    });
    canvas.addEventListener("pointerleave", (e) => {
      if (panState) panEnd();
      else if (drawing) endInteract(e);
    });
    window.addEventListener("resize", () => { fitZoom(); render(); });

    document.addEventListener("keydown", (e) => {
      const tag = e.target && e.target.tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (e.ctrlKey || e.metaKey) {
        if (e.key.toLowerCase() === "z") { e.preventDefault(); if (e.shiftKey) redo(); else undo(); return; }
        if (e.key.toLowerCase() === "y") { e.preventDefault(); redo(); return; }
        if (e.key.toLowerCase() === "s") { e.preventDefault(); downloadPng(); return; }
        return;
      }
      if (e.key === "ArrowRight" || e.key === "]") moveFigure(1);
      else if (e.key === "ArrowLeft" || e.key === "[") moveFigure(-1);
      else if (e.key === "r") rotate(90);
      else if (e.key === "R") rotate(270);
      else if (e.key === "f") { fitZoom(); render(); }
      else if (e.key === "+" || e.key === "=") { zoom = Math.min(4, zoom * 1.2); render(); }
      else if (e.key === "-") { zoom = Math.max(0.1, zoom / 1.2); render(); }
      else if (e.key === "z") document.body.classList.toggle("zen");
      else if (e.key === "d") $("darkBtn").click();
      else if (e.key === "?") helpDialog.classList.toggle("hidden");
      else if (e.key === "Escape") {
        document.body.classList.remove("zen");
        helpDialog.classList.add("hidden");
        if (textOverlayEl) finishTextEditor(false);
      }
      /* ツール切替 (キー1文字) */
      else if (e.key === "p") setTool("pen");
      else if (e.key === "h") setTool("highlight");
      else if (e.key === "l") setTool("line");
      else if (e.key === "o") setTool("rect");
      else if (e.key === "e") setTool("ellipse");
      else if (e.key === "a") setTool("arrow");
      else if (e.key === "t") setTool("text");
      else if (e.key === "x") setTool("erase");
      else if (e.key === " ") { e.preventDefault(); setTool("pan"); }
    });

    setFigure(currentIndex);
  }

  init();
})();
