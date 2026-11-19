'use strict';
(() => {
  const M = window.GlyphModel;
  const dialog = document.createElement('dialog');
  dialog.id = 'glyph-editor'; dialog.className = 'editor-dialog';
  dialog.setAttribute('aria-labelledby', 'editor-title');
  dialog.innerHTML = `
    <div class="editor-head"><h2 id="editor-title">字形编辑 <small>Hunter Font Design 2.0.3</small></h2><button id="editor-save" type="button">暂存此字</button><button id="editor-save-source" type="button">保存源稿</button><button id="editor-handoff-open" type="button">交给 Codex</button><button id="editor-export" class="primary" type="button">导出新字体</button><button id="editor-close" type="button">关闭</button></div>
    <p class="editor-connection" id="editor-connection" hidden></p>
    <div class="editor-toolbar" aria-label="绘制工具">
      <label>字符 <input id="editor-char" type="text" value="A" aria-label="编辑字符" autocomplete="off"></label><button id="editor-load" type="button">载入字形</button><button id="editor-blank" type="button">从空白绘制</button>
      <button id="editor-select" type="button" aria-pressed="true" title="选择节点 V">选择 V</button><button id="editor-pen" type="button" aria-pressed="false" title="钢笔 P：单击直线，按住拖出曲线">钢笔 P</button><button id="editor-close-path" type="button">闭合轮廓 ↵</button>
      <button id="editor-undo" type="button" title="⌘ / Ctrl Z">撤销</button><button id="editor-redo" type="button" title="⌘ / Ctrl Shift Z">重做</button>
      <label class="editor-zoom-action">缩放 <select id="editor-zoom"><option value="fit">适合画布</option><option value="1">100%</option><option value="2">200%</option><option value="4">400%</option></select></label>
    </div>
    <div class="editor-body"><div class="editor-workspace" id="editor-workspace" data-tool="select"><svg id="editor-svg" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="可编辑字形画布"></svg></div>
      <aside class="editor-properties" aria-label="字形与节点属性">
        <section><h3 id="editor-glyph-label">字形</h3><p id="editor-units"></p><label>占位宽度 <input id="editor-advance" type="number" min="0" max="65535" step="1"></label>
        <hr><h3>选中节点</h3><label>节点 <select id="editor-node" aria-label="选择节点"><option value="">请选择</option></select></label><p id="editor-selection">点击锚点或控制柄</p><label>X <input id="editor-x" type="number" step="1" min="-32767" max="32767" disabled></label><label>Y <input id="editor-y" type="number" step="1" min="-32767" max="32767" disabled></label>
        <div class="editor-row"><button id="editor-line" type="button">转为直线</button><button id="editor-curve" type="button">转为曲线</button><button id="editor-delete" type="button">删除节点</button></div><div class="editor-row"><button id="editor-reverse" type="button">反转轮廓方向</button><button id="editor-delete-contour" type="button">删除轮廓</button></div></section>
        <section><h3>辅助层</h3><label><span>显示填充</span><input id="editor-fill" type="checkbox" checked></label><label for="editor-opacity"><span>字形透明度</span><output id="editor-opacity-value">88%</output></label><input id="editor-opacity" class="editor-opacity-range" type="range" min="0" max="100" step="1" value="88" aria-label="字形透明度"><p class="editor-help">仅影响黑色填充显示，不改变导出字形。</p><label><span>原字对照</span><input id="editor-ghost" type="checkbox" checked></label><label><span>显示网格</span><input id="editor-grid" type="checkbox" checked></label><label><span>吸附网格</span><input id="editor-snap" type="checkbox"></label><label>网格间隔 <input id="editor-step" type="number" value="25" min="1" max="500"></label>
        <hr><h3>参考底图</h3><button id="editor-reference" type="button">载入图片</button><button id="editor-remove-reference" type="button">移除</button><input id="editor-image-file" type="file" accept="image/png,image/jpeg,image/webp" hidden>
        <label>X <input id="reference-x" type="number" value="0" step="1"></label><label>顶部 Y <input id="reference-y" type="number" value="700" step="1"></label><label>宽度 <input id="reference-width" type="number" min="1" value="700" step="1"></label><label>透明度 <input id="reference-opacity" type="number" min="0" max="1" step="0.05" value="0.25"></label></section>
        <section id="editor-handoff-panel"><hr><h3>交给 Codex</h3><p>保存当前及已暂存字形，直接发送到本工具绑定的 Codex 对话，无需复制粘贴。</p><label for="editor-handoff-note">接下来怎么改</label><textarea id="editor-handoff-note" rows="3" maxlength="4000" placeholder="可留空，只接收并确认字形；或填写下一步修改要求。"></textarea><div class="editor-row"><button id="editor-handoff-send" class="primary" type="button">发送到 Codex</button><button id="editor-handoff-copy" type="button" hidden>复制接续消息（备用）</button></div><p id="editor-handoff-status" role="status">先保存完整源稿，再直接投递。Codex 正在回复时，本轮结束后接续处理。</p><textarea id="editor-handoff-message" rows="4" aria-label="可复制的接续消息" readonly hidden></textarea></section>
        <section><hr><h3>源稿</h3><div class="editor-row"><button id="editor-save-draft" type="button">保存 JSON 源稿</button><button id="editor-open-draft" type="button">载入源稿</button><button id="editor-svg-export" type="button">导出 SVG</button><button id="editor-new-font" type="button">新建空白字体</button></div><input id="editor-draft-file" type="file" accept=".json,application/json" hidden>
        <label>暂存字形 <select id="editor-staged" aria-label="查看暂存字形"><option value="">尚无暂存</option></select></label><p id="editor-draft-count">尚无暂存字形</p><p class="editor-help">暂存仅在当前页面内存。以后继续修改请保存源稿；直接使用请导出新字体，下载后安装到系统。关闭编辑器也可试排新导出的字体。</p><p class="editor-help">钢笔：单击落点，按住拖出曲线；点起点或 Enter 闭合，可继续画内腔。双击线段插入节点；方向键微调，Shift 每次 10 u。空格拖动画布。修改原字的节点会同时带动相邻手柄。</p></section>
      </aside></div>
    <div class="editor-footer"><p class="editor-status" id="editor-status" role="status">选择一个字形开始。</p><span>橙色：轮廓 / 锚点　灰蓝：控制柄 / 原字</span></div>`;
  document.body.append(dialog);
  const launcherHelp = document.createElement('dialog');
  launcherHelp.id = 'editor-launcher-help';
  launcherHelp.className = 'glyph-zoom-dialog';
  launcherHelp.style.maxWidth = '32rem';
  launcherHelp.setAttribute('aria-labelledby', 'editor-launcher-title');
  launcherHelp.setAttribute('aria-describedby', 'editor-launcher-message');
  launcherHelp.innerHTML = '<div class="glyph-zoom-head"><h2 id="editor-launcher-title">打开字形编辑器</h2><form method="dialog"><button autofocus>关闭</button></form></div><p id="editor-launcher-message"></p>';
  document.body.append(launcherHelp);
  const e = id => dialog.querySelector('#' + id);
  const svg = e('editor-svg'), workspace = e('editor-workspace');
  const drafts = new Map();
  let glyph, original, info, baseFont, selected, tool = 'select', history = [], cursor = -1, clean = '', scale = 1;
  let opener, drag, pendingOut, firstIn, space = false, busy = false, requestId = 0, viewBox;
  let queuedHandoff = '';
  const webPage = /^https?:$/.test(location.protocol);
  const launchHint = '请双击试排目录里的「打开字体编辑器.command」，再到新打开的页面编辑。';
  const serviceError = '无法连接到本机编辑服务。' + launchHint;
  const message = (text, error = false) => {e('editor-status').textContent = text; e('editor-status').classList.toggle('error', error);};
  const currentFont = () => fonts.get($('#font-select').value);
  const snapshot = () => JSON.stringify(glyph);
  const dirty = () => glyph && snapshot() !== clean;
  const draftFor = () => {
    if (!drafts.has(info.sha256)) drafts.set(info.sha256, {format:'hunter-glyph-edits', version:1, baseSha256:info.sha256, unitsPerEm:info.unitsPerEm, glyphs:[]});
    return drafts.get(info.sha256);
  };
  function commit() {
    const value = snapshot();
    if (history[cursor] !== value) {history.splice(cursor + 1); history.push(value); cursor = history.length - 1;}
    updateProperties();
  }
  function restore(index) {
    if (index < 0 || index >= history.length) return;
    cursor = index; glyph = JSON.parse(history[cursor]); selected = null; pendingOut = firstIn = null; draw();
  }
  function chooseTool(value) {
    tool = value; workspace.dataset.tool = value;
    for (const key of ['select','pen']) e('editor-' + key).setAttribute('aria-pressed', String(key === tool));
  }
  async function requireService() {
    if (!webPage) throw Error('当前是离线试排页。' + launchHint);
    try {
      const response = await fetch('/api/editor', {cache:'no-store', signal:AbortSignal.timeout(2500)});
      if (response.ok && (await response.json()).version === 2) return;
    } catch {}
    throw Error(serviceError);
  }
  async function api(route, body, json = false) {
    if (!webPage) throw Error(launchHint);
    let response;
    let data;
    try {
      response = await fetch(route, {method:'POST', headers:{'Content-Type':json ? 'application/json' : 'application/octet-stream', 'X-Hunter-Editor':'2'}, body:json ? JSON.stringify(body) : body});
      data = await response.json();
    } catch { throw Error(serviceError); }
    if (!response.ok) throw Error(data.error || '无法处理字体。');
    return data;
  }
  async function bytes(font) {
    if (!font.editorBytes) {
      const response = await fetch(font.url);
      if (!response.ok) throw Error('无法读取当前字体文件。');
      font.editorBytes = await response.arrayBuffer();
    }
    return font.editorBytes;
  }
  const decode = value => Uint8Array.from(atob(value), c => c.charCodeAt(0)).buffer;
  function encode(value) {
    let result = ''; const array = new Uint8Array(value);
    for (let i = 0; i < array.length; i += 32768) result += String.fromCharCode(...array.subarray(i, i + 32768));
    return btoa(result);
  }
  async function install(buffer, meta, filename) {
    const family = 'EditedFont' + (++importSequence), face = new FontFace(family, buffer);
    await face.load(); document.fonts.add(face);
    const font = {...meta, filename, editorBytes:buffer, label:meta.family + ' / ' + meta.style + ' · ' + meta.version,
      url:URL.createObjectURL(new Blob([buffer])), loaded:true, coverage:new Set(meta.codepoints), note:'本地绘制审校稿。请检查字形、字距、hinting 与目标软件后再发行。'};
    fonts.set(family, font); $('#font-select').add(new Option(font.label, family)); $('#font-select').value = family; selectFont();
    return font;
  }
  async function newFont() {
    const data = await api('/api/new-font', {}, true);
    return install(decode(data.font), data.info, 'Hunter-Draw-Draft.ttf');
  }
  async function loadGlyph(char, blank = false, force = false) {
    if (busy) return;
    if (!force && dirty() && !confirm('当前字形尚未暂存。继续将丢弃这些修改，是否继续？')) {e('editor-char').value = glyph.char; return;}
    if (Array.from(char).length !== 1) {message('请输入一个字符。', true); return;}
    busy = true; const id = ++requestId; message('正在读取真实轮廓…');
    try {
      let font = currentFont();
      if (!font.url) font = await newFont();
      const data = await api('/api/glyph?filename=' + encodeURIComponent(font.filename) + '&char=' + encodeURIComponent(char), await bytes(font));
      if (id !== requestId || !dialog.open) return;
      info = data.info; baseFont = font; original = M.clone(data.glyph); glyph = M.clone(data.glyph);
      const saved = draftFor().glyphs.find(g => g.char === char);
      if (saved && !blank) glyph = M.clone(saved);
      if (blank) glyph.contours = [];
      selected = null; pendingOut = firstIn = null; history = []; cursor = -1; clean = snapshot(); commit();
      e('editor-char').value = char; e('editor-zoom').value = 'fit'; viewBox = null;
      chooseTool(blank || !glyph.contours.length ? 'pen' : 'select');
      e('editor-connection').hidden = true; draw();
      message(blank ? '空白轮廓已就绪。单击落点，拖动绘制曲线，点击起点闭合。' : '已载入真实轮廓。拖动锚点与控制柄，双击线段可加点。');
    } catch (error) {
      e('editor-connection').hidden = false; e('editor-connection').textContent = error.message; message(error.message, true);
    } finally {busy = false;}
  }
  function node(tag, attrs = {}) {
    const value = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, v] of Object.entries(attrs)) value.setAttribute(key, v);
    return value;
  }
  function layout() {
    if (!glyph) return;
    if (!viewBox) {
      const points = [...glyph.contours, ...original.contours].flat().filter(c => c[0] !== 'Z').flatMap(c => Array.from({length:(c.length - 1) / 2}, (_, i) => c.slice(1 + i * 2, 3 + i * 2)));
      const upm = info.unitsPerEm, pad = upm * .12;
      const left = Math.min(0, ...points.map(p => p[0])) - pad, right = Math.max(upm, glyph.advanceWidth, ...points.map(p => p[0])) + pad;
      const top = Math.max(upm * .9, ...points.map(p => p[1])) + pad, bottom = Math.min(-upm * .25, ...points.map(p => p[1])) - pad;
      viewBox = [left, -top, right - left, top - bottom];
    }
    const [x, y, width, height] = viewBox;
    const fit = Math.max(.05, Math.min((workspace.clientWidth - 32) / width, (workspace.clientHeight - 32) / height));
    scale = e('editor-zoom').value === 'fit' ? fit : Number(e('editor-zoom').value) * 1000 / info.unitsPerEm;
    svg.setAttribute('viewBox', [x, y, width, height].join(' ')); svg.setAttribute('width', width * scale); svg.setAttribute('height', height * scale);
  }
  function draw() {
    if (!glyph) return;
    layout(); svg.replaceChildren();
    const [x, y, width, height] = viewBox, step = Number(e('editor-step').value) || 25;
    if (e('editor-grid').checked) {
      const defs = node('defs'), pattern = node('pattern', {id:'editor-grid-pattern', width:step, height:step, patternUnits:'userSpaceOnUse'});
      pattern.append(node('path', {d:`M ${step} 0 H 0 V ${step}`, fill:'none', stroke:'#aab9c2', 'stroke-opacity':'.35', 'stroke-width':.6 / scale})); defs.append(pattern); svg.append(defs);
      svg.append(node('rect', {x, y, width, height, fill:'url(#editor-grid-pattern)', 'pointer-events':'none'}));
    }
    if (glyph.reference) {
      const r = glyph.reference;
      svg.append(node('image', {href:r.data, x:r.x, y:-r.y, width:r.width, height:r.width / r.ratio, opacity:r.opacity, 'pointer-events':'none'}));
    }
    const world = node('g', {transform:'scale(1,-1)'});
    for (const [key, v] of Object.entries(info.guides)) world.append(node('line', {class:'editor-guide ' + key, x1:x, x2:x + width, y1:v * info.unitsPerEm / 1000, y2:v * info.unitsPerEm / 1000}));
    for (const v of [0, glyph.advanceWidth]) world.append(node('line', {class:'editor-guide', x1:v, x2:v, y1:-y, y2:-y - height}));
    if (e('editor-ghost').checked) world.append(node('path', {class:'editor-ghost', d:M.path(original.contours)}));
    const outline = node('path', {class:'editor-outline', d:M.path(glyph.contours), 'fill-rule':'nonzero', style:e('editor-fill').checked ? '' : 'fill:none;stroke-width:1.5'});
    world.append(outline);
    const handles = node('g'), anchors = node('g'), radius = 4 / scale;
    function point(ci, i, offset, handle) {
      const c = glyph.contours[ci][i], attrs = {'data-contour':ci, 'data-command':i, 'data-offset':offset, class:'editor-point' + (handle ? ' handle' : '') + (selected && selected.ci === ci && selected.i === i && selected.offset === offset ? ' selected' : '')};
      const item = handle ? node('circle', {...attrs, cx:c[offset], cy:c[offset + 1], r:radius}) : node('rect', {...attrs, x:c[offset] - radius, y:c[offset + 1] - radius, width:radius * 2, height:radius * 2});
      (handle ? handles : anchors).append(item);
    }
    for (const [ci, contour] of glyph.contours.entries()) {
      for (let i = 0; i < contour.length; i++) {
        const c = contour[i]; if (c[0] === 'Z') continue;
        if (c[0] === 'Q' || c[0] === 'C') {
          const prev = M.end(contour[i - 1]);
          handles.append(node('line', {class:'editor-handle-line', x1:prev[0], y1:prev[1], x2:c[1], y2:c[2]})); point(ci, i, 1, true);
          const end = M.end(c), j = c[0] === 'C' ? 3 : 1;
          handles.append(node('line', {class:'editor-handle-line', x1:end[0], y1:end[1], x2:c[j], y2:c[j + 1]}));
          if (c[0] === 'C') point(ci, i, 3, true);
        }
        const duplicate = i === contour.length - 2 && contour.at(-1)[0] === 'Z' && M.same(M.end(c), M.end(contour[0]));
        if (!duplicate) point(ci, i, c.length - 2, false);
      }
    }
    world.append(handles, anchors); svg.append(world); updateProperties();
  }
  function updateProperties() {
    if (!glyph) return;
    e('editor-glyph-label').textContent = glyph.char + ' · U+' + glyph.char.codePointAt(0).toString(16).toUpperCase().padStart(4, '0');
    e('editor-units').textContent = info.unitsPerEm + ' UPM · 原始字体坐标，Y 轴向上';
    e('editor-advance').value = glyph.advanceWidth;
    const c = selected && glyph.contours[selected.ci]?.[selected.i];
    const select = e('editor-node'); select.replaceChildren(new Option('请选择', ''));
    for (const [ci, contour] of glyph.contours.entries()) for (const [i, command] of contour.entries()) {
      if (command[0] === 'Z') continue;
      const duplicate = i === contour.length - 2 && contour.at(-1)[0] === 'Z' && M.same(M.end(command), M.end(contour[0]));
      for (let offset = 1; offset < command.length; offset += 2) {
        if (duplicate && offset === command.length - 2) continue;
        select.add(new Option(`${ci + 1}.${i + 1} ${offset === command.length - 2 ? '锚点' : '手柄 ' + offset}`, [ci, i, offset].join(':')));
      }
    }
    select.value = selected ? [selected.ci, selected.i, selected.offset].join(':') : '';
    for (const axis of ['x','y']) {
      const input = e('editor-' + axis); input.disabled = !c;
      input.value = c ? Number(c[selected.offset + (axis === 'y' ? 1 : 0)].toFixed(3)) : '';
    }
    e('editor-selection').textContent = c ? `轮廓 ${selected.ci + 1} · ${selected.offset === c.length - 2 ? '锚点' : '控制柄'}` : '点击锚点或控制柄';
    e('editor-undo').disabled = cursor <= 0; e('editor-redo').disabled = cursor >= history.length - 1;
    for (const id of ['delete','line','curve','reverse','delete-contour']) e('editor-' + id).disabled = !c;
    const staged = draftFor().glyphs;
    e('editor-staged').replaceChildren(new Option(staged.length ? '选择以继续编辑' : '尚无暂存', ''));
    for (const g of staged) e('editor-staged').add(new Option(g.char + ' · U+' + g.char.codePointAt(0).toString(16).toUpperCase().padStart(4, '0'), g.char));
    e('editor-staged').value = staged.some(g => g.char === glyph.char) ? glyph.char : '';
    e('editor-draft-count').textContent = '当前页面内存中已暂存 ' + staged.length + ' 个字形' + (dirty() ? ' · 当前字形未暂存' : '');
    e('editor-opacity').disabled = !e('editor-fill').checked;
    for (const key of ['x','y','width','opacity']) {const input = e('reference-' + key); input.disabled = !glyph.reference; if (glyph.reference) input.value = glyph.reference[key];}
  }
  function coordinate(event, snap = true) {
    const p = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
    const step = snap && e('editor-snap').checked ? Math.max(1, Number(e('editor-step').value)) : 1;
    return [Math.round(p.x / step) * step, Math.round(-p.y / step) * step];
  }
  function activeContour() {const c = glyph?.contours.at(-1); return c && c.at(-1)[0] !== 'Z' ? c : null;}
  function closePath() {
    const contour = activeContour(); if (!contour) return;
    if (contour.length < 2) {message('至少再添加一个节点。', true); return;}
    const start = M.end(contour[0]), prev = M.end(contour.at(-1));
    if (pendingOut || firstIn) contour.push(['C', ...(pendingOut || prev), ...(firstIn || start), ...start]);
    else if (!M.same(prev, start)) contour.push(['L', ...start]);
    contour.push(['Z']); pendingOut = firstIn = null; selected = null; commit(); draw(); message('轮廓已闭合。继续单击可绘制另一条轮廓或内腔。');
  }
  svg.addEventListener('pointerdown', event => {
    if (!glyph || busy) return;
    svg.focus();
    if (space || event.button === 1) {event.preventDefault(); svg.setPointerCapture(event.pointerId); drag = {kind:'pan', x:event.clientX, y:event.clientY, left:workspace.scrollLeft, top:workspace.scrollTop}; return;}
    if (event.button !== 0) return;
    const p = coordinate(event), target = event.target.closest('[data-command]');
    if (tool === 'select' && target) {
      event.preventDefault(); svg.setPointerCapture(event.pointerId);
      selected = {ci:Number(target.dataset.contour), i:Number(target.dataset.command), offset:Number(target.dataset.offset)};
      drag = {kind:'node', before:snapshot(), start:p, selected:{...selected}}; draw(); return;
    }
    if (tool === 'select') {selected = null; for (const point of svg.querySelectorAll('.selected')) point.classList.remove('selected'); updateProperties(); return;}
    event.preventDefault(); svg.setPointerCapture(event.pointerId);
    let contour = activeContour();
    if (contour && contour.length > 1 && Math.hypot(p[0] - contour[0][1], p[1] - contour[0][2]) * scale < 10) {closePath(); return;}
    const before = snapshot();
    if (!contour) {contour = [['M', ...p]]; glyph.contours.push(contour); pendingOut = firstIn = null;}
    else {const prev = M.end(contour.at(-1)); contour.push(pendingOut ? ['C', ...pendingOut, ...p, ...p] : ['L', ...p]);}
    drag = {kind:'pen', before, start:p, previousOut:pendingOut, previousEnd:contour.length > 1 ? M.end(contour.at(-2)) : p, ci:glyph.contours.length - 1, i:contour.length - 1};
    selected = {ci:drag.ci, i:drag.i, offset:contour.at(-1).length - 2}; draw();
  });
  svg.addEventListener('pointermove', event => {
    if (!drag) return;
    if (drag.kind === 'pan') {workspace.scrollLeft = drag.left - event.clientX + drag.x; workspace.scrollTop = drag.top - event.clientY + drag.y; return;}
    const p = coordinate(event);
    if (drag.kind === 'node') {
      glyph = JSON.parse(drag.before);
      const s = drag.selected, c = glyph.contours[s.ci][s.i];
      M.move(glyph.contours[s.ci], s.i, s.offset, [c[s.offset] + p[0] - drag.start[0], c[s.offset + 1] + p[1] - drag.start[1]]);
    } else {
      const contour = glyph.contours[drag.ci], dx = p[0] - drag.start[0], dy = p[1] - drag.start[1];
      if (Math.hypot(dx, dy) * scale > 2) {
        pendingOut = p;
        drag.out = p;
        const incoming = [drag.start[0] - dx, drag.start[1] - dy];
        if (drag.i === 0) firstIn = incoming;
        else contour[drag.i] = ['C', ...(drag.previousOut || drag.previousEnd), ...incoming, ...drag.start];
        selected.offset = contour[drag.i].length - 2;
      }
    }
    draw();
  });
  function finishDrag(event) {
    if (!drag) return;
    if (event.type === 'pointercancel' && drag.before) glyph = JSON.parse(drag.before);
    else if (drag.kind === 'pen') pendingOut = drag.out || null;
    if (drag.kind !== 'pan') commit();
    drag = null; draw();
  }
  svg.addEventListener('pointerup', finishDrag); svg.addEventListener('pointercancel', finishDrag);
  svg.addEventListener('dblclick', event => {
    if (!glyph || tool !== 'select' || event.target.closest('[data-command]')) return;
    const p = coordinate(event, false); let best = null;
    for (const [ci, contour] of glyph.contours.entries()) for (let i = 1; i < contour.length; i++) {
      if (contour[i][0] === 'Z') continue;
      for (let k = 1; k < 80; k++) {const t = k / 80, v = M.sample(contour, i, t), distance = Math.hypot(v[0] - p[0], v[1] - p[1]); if (!best || distance < best.distance) best = {ci, i, t, distance};}
    }
    if (best && best.distance * scale < 14) {M.split(glyph.contours[best.ci], best.i, best.t); const c = glyph.contours[best.ci][best.i]; selected = {ci:best.ci, i:best.i, offset:c.length - 2}; commit(); draw(); message('已插入节点，曲线形状保持。');}
  });
  function editSelected(axis) {
    if (!selected) return;
    const c = glyph.contours[selected.ci][selected.i], p = c.slice(selected.offset, selected.offset + 2);
    const input = e('editor-' + axis); if (!Number.isFinite(input.valueAsNumber) || Math.abs(input.valueAsNumber) > 32767) {draw(); return;}
    p[axis === 'x' ? 0 : 1] = input.valueAsNumber; M.move(glyph.contours[selected.ci], selected.i, selected.offset, p); commit(); draw();
  }
  function deleteNode() {
    if (!selected) return;
    const contour = glyph.contours[selected.ci], c = contour[selected.i];
    if (selected.offset !== c.length - 2) {message('请选择锚点；控制柄可通过“转为直线”移除。', true); return;}
    if (selected.i === 0) {
      if (contour.length <= 3) glyph.contours.splice(selected.ci, 1);
      else {const start = M.end(contour[1]), duplicate = contour.at(-1)[0] === 'Z' && M.same(M.end(contour.at(-2)), M.end(contour[0])); contour.splice(0, 2, ['M', ...start]); if (duplicate) contour.at(-2).splice(-2, 2, ...start);}
    } else contour.splice(selected.i, 1);
    selected = null; pendingOut = firstIn = null; commit(); draw();
  }
  function convert(curve) {
    if (!selected) return;
    let {ci, i} = selected; const contour = glyph.contours[ci];
    if (i === 0) i = contour.at(-1)[0] === 'Z' ? contour.length - 2 : 1;
    if (i < 1 || !contour[i] || contour[i][0] === 'Z') return;
    const c = contour[i], a = M.end(contour[i - 1]), b = M.end(c);
    contour[i] = !curve ? ['L', ...b] : c[0] === 'Q' ? ['C', ...M.mix(a, c.slice(1, 3), 2/3), ...M.mix(b, c.slice(1, 3), 2/3), ...b] : c[0] === 'C' ? c : ['C', ...M.mix(a, b, 1/3), ...M.mix(a, b, 2/3), ...b];
    selected = {ci, i, offset:contour[i].length - 2}; commit(); draw();
  }
  function stage() {
    if (!glyph) throw Error('请先载入或新建一个字形。');
    M.validate(glyph);
    const draft = draftFor(), previous = draft.glyphs.findIndex(g => g.char === glyph.char);
    if (previous < 0) draft.glyphs.push(M.clone(glyph)); else draft.glyphs[previous] = M.clone(glyph);
    draft.downloaded = false; clean = snapshot(); updateProperties(); message('已暂存 ' + glyph.char + ' 到当前页面内存（共 ' + draft.glyphs.length + ' 个字形）。直接使用点“导出新字体”；保留以后修改点“保存源稿”。');
    return draft;
  }
  function download(data, filename, type) {
    const url = URL.createObjectURL(new Blob([data], {type})), link = document.createElement('a');
    link.href = url; link.download = filename; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const act = fn => async () => {try {await fn();} catch (error) {message(error.message, true);}};
  e('editor-select').onclick = () => chooseTool('select'); e('editor-pen').onclick = () => chooseTool('pen');
  e('editor-load').onclick = () => loadGlyph(e('editor-char').value); e('editor-blank').onclick = () => loadGlyph(e('editor-char').value, true);
  e('editor-close-path').onclick = closePath; e('editor-undo').onclick = () => restore(cursor - 1); e('editor-redo').onclick = () => restore(cursor + 1);
  e('editor-save').onclick = act(stage); e('editor-delete').onclick = deleteNode; e('editor-line').onclick = () => convert(false); e('editor-curve').onclick = () => convert(true);
  e('editor-reverse').onclick = () => {if (!selected) return; const ci = selected.ci; glyph.contours[ci] = M.reverse(glyph.contours[ci]); selected = null; commit(); draw();};
  e('editor-delete-contour').onclick = () => {if (!selected) return; glyph.contours.splice(selected.ci, 1); selected = null; commit(); draw();};
  e('editor-x').onchange = () => editSelected('x'); e('editor-y').onchange = () => editSelected('y');
  e('editor-node').onchange = event => {if (!event.target.value) selected = null; else {const [ci, i, offset] = event.target.value.split(':').map(Number); selected = {ci, i, offset};} draw();};
  e('editor-staged').onchange = async event => {if (!event.target.value) return; await loadGlyph(event.target.value); updateProperties();};
  e('editor-advance').onchange = event => {if (glyph && Number.isFinite(event.target.valueAsNumber) && event.target.valueAsNumber >= 0 && event.target.valueAsNumber <= 65535) {glyph.advanceWidth = event.target.valueAsNumber; commit(); draw();}};
  for (const id of ['fill','ghost','grid','zoom','step']) e('editor-' + id).addEventListener('change', draw);
  e('editor-opacity').addEventListener('input', () => {const value = e('editor-opacity').valueAsNumber; svg.style.setProperty('--editor-fill-opacity', value / 100); e('editor-opacity-value').value = value + '%';});
  e('editor-new-font').onclick = act(async () => {if (dirty() && !confirm('当前字形尚未暂存，继续将丢弃这些修改。是否继续？')) return; await newFont(); await loadGlyph(e('editor-char').value, true, true);});
  e('editor-save-draft').onclick = act(async () => {const draft = stage(); draft.sourceFont = {filename:baseFont.filename, data:encode(await bytes(baseFont))}; download(JSON.stringify(draft, null, 2) + '\n', 'Hunter-Glyphs-' + info.sha256.slice(0, 8) + '.json', 'application/json'); draft.downloaded = true; message('已发起 JSON 源稿下载，位置由浏览器下载设置决定。以后点“载入源稿”继续修改。');});
  e('editor-save-source').onclick = () => e('editor-save-draft').click();
  e('editor-handoff-open').onclick = () => {e('editor-handoff-note').focus(); e('editor-handoff-panel').scrollIntoView({block:'nearest'});};
  e('editor-handoff-send').onclick = act(async () => {
    if (busy) return;
    const draft = stage();
    const handoffKey = JSON.stringify([info.sha256, draft.glyphs, e('editor-handoff-note').value]);
    if (handoffKey === queuedHandoff) {draft.downloaded = true; e('editor-handoff-status').textContent = '相同修改已发到当前 Codex 对话，请等待接续处理。'; return;}
    const controls = [...dialog.querySelectorAll('button,input,select,textarea')].map(el => [el, el.disabled]);
    busy = true; for (const [el] of controls) el.disabled = true;
    e('editor-handoff-copy').hidden = true; e('editor-handoff-message').value = '';
    e('editor-handoff-status').textContent = '正在保存接续包…';
    try {
      const receipt = await api('/api/handoff/send', {font:encode(await bytes(baseFont)), filename:baseFont.filename, draft, instruction:e('editor-handoff-note').value}, true);
      draft.downloaded = true;
      e('editor-handoff-message').value = receipt.prompt;
      if (receipt.status === 'queued') {
        queuedHandoff = handoffKey;
        const text = '已发到当前 Codex 对话队列，无需复制粘贴。正在回复时，本轮结束后接续处理。';
        e('editor-handoff-status').textContent = text; message(text);
      } else {
        e('editor-handoff-copy').hidden = false;
        const text = '源稿已保存，直接发送尚未确认：' + (receipt.detail || '请检查本地 Codex 连接。');
        e('editor-handoff-status').textContent = text; message(text, true);
      }
    } catch (error) {
      e('editor-handoff-status').textContent = '未确认发送结果：' + error.message;
      throw error;
    } finally {
      busy = false; for (const [el, disabled] of controls) el.disabled = disabled; updateProperties();
    }
  });
  e('editor-handoff-copy').onclick = act(async () => {
    try {await navigator.clipboard.writeText(e('editor-handoff-message').value); e('editor-handoff-status').textContent = '接续消息已复制。粘贴到 Codex 对话并发送即可。';}
    catch {e('editor-handoff-message').hidden = false; e('editor-handoff-message').select(); e('editor-handoff-status').textContent = '请复制选中的接续消息，粘贴到 Codex 对话并发送。';}
  });
  e('editor-open-draft').onclick = () => e('editor-draft-file').click();
  e('editor-draft-file').onchange = act(async () => {
    const file = e('editor-draft-file').files[0]; e('editor-draft-file').value = ''; if (!file || !info) return;
    if (file.size > 32 * 1024 * 1024) throw Error('源稿超出 32 MB 限制。');
    const draft = JSON.parse(await file.text());
    if (draft.format !== 'hunter-glyph-edits' || draft.version !== 1) throw Error('不是本工具支持的字形源稿。');
    if (!Array.isArray(draft.glyphs) || !draft.glyphs.length || draft.glyphs.length > 1000) throw Error('源稿字形数量无效。');
    const chars = new Set();
    for (const g of draft.glyphs) {
      if (typeof g.char !== 'string' || Array.from(g.char).length !== 1 || chars.has(g.char)) throw Error('源稿存在无效或重复字符。');
      chars.add(g.char); M.validate(g);
      if (g.reference && (!/^data:image\/(png|jpeg|webp);base64,/.test(g.reference.data) || !['x','y','width','ratio','opacity'].every(k => Number.isFinite(g.reference[k])) || g.reference.width <= 0 || g.reference.ratio <= 0 || g.reference.opacity < 0 || g.reference.opacity > 1)) throw Error('参考图数据无效。');
    }
    let restored;
    if (draft.baseSha256 !== info.sha256 || draft.unitsPerEm !== info.unitsPerEm) {
      if (!draft.sourceFont?.data) throw Error('源稿与当前原字体不匹配；请载入对应的原字体。');
      const buffer = decode(draft.sourceFont.data), digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', buffer)), b => b.toString(16).padStart(2, '0')).join('');
      if (digest !== draft.baseSha256) throw Error('源稿内嵌原字体的 SHA-256 校验失败。');
      const data = await api('/api/glyph?filename=' + encodeURIComponent(draft.sourceFont.filename) + '&char=' + encodeURIComponent(draft.glyphs[0].char), buffer);
      if (data.info.unitsPerEm !== draft.unitsPerEm) throw Error('源稿 UPM 与原字体不符。');
      restored = {buffer, info:data.info, filename:draft.sourceFont.filename};
    }
    if ((dirty() || drafts.get(draft.baseSha256)?.glyphs.length) && !confirm('载入源稿将替换对应的暂存内容，是否继续？')) return;
    if (restored) await install(restored.buffer, restored.info, restored.filename);
    drafts.set(draft.baseSha256, draft); await loadGlyph(draft.glyphs[0].char, false, true); message('源稿及原字体已载入，可继续编辑。');
  });
  e('editor-export').onclick = act(async () => {
    if (busy) return;
    const draft = stage(); busy = true; e('editor-export').disabled = true; message('正在生成并回读新字体…');
    try {
      const data = await api('/api/export', {font:encode(await bytes(baseFont)), filename:baseFont.filename, draft}, true);
      const buffer = decode(data.font), filename = baseFont.filename.replace(/\.(ttf|otf|woff2?)$/i, '-edited.$1');
      await install(buffer, data.report.info, filename);
      download(buffer, filename, 'application/octet-stream');
      draft.lastExportReport = data.report;
      message('已导出 ' + data.report.editedGlyphs.length + ' 个修改字形，关联组件 ' + data.report.dependentGlyphs.length + ' 个。关闭后查看新字体试排；正式使用前需完成光学与平台检查。');
      draft.downloaded = false;
      // Keep the original font selected while this draft is being edited; the new font is available in the selector.
      baseFont.exportedKey = $('#font-select').value;
      for (const [key, font] of fonts) if (font === baseFont) {$('#font-select').value = key; selectFont(); break;}
    } finally {busy = false; e('editor-export').disabled = false;}
  });
  e('editor-svg-export').onclick = act(() => {M.validate(glyph); const data = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox.join(' ')}"><path transform="scale(1,-1)" fill-rule="nonzero" d="${M.path(glyph.contours)}"/></svg>\n`; download(data, 'U+' + glyph.char.codePointAt(0).toString(16).toUpperCase() + '.svg', 'image/svg+xml');});
  e('editor-reference').onclick = () => e('editor-image-file').click();
  e('editor-image-file').onchange = act(async () => {
    const file = e('editor-image-file').files[0]; e('editor-image-file').value = ''; if (!file || !glyph) return;
    if (!['image/png','image/jpeg','image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024) throw Error('请选择 10 MB 以内的 PNG、JPG 或 WebP。');
    const data = await new Promise((resolve, reject) => {const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file);});
    const image = new Image(); image.src = data; await image.decode();
    glyph.reference = {data, x:0, y:info.guides.cap * info.unitsPerEm / 1000, width:glyph.advanceWidth || info.unitsPerEm, ratio:image.width / image.height, opacity:.25}; commit(); draw();
  });
  e('editor-remove-reference').onclick = () => {if (!glyph?.reference) return; delete glyph.reference; commit(); draw();};
  for (const key of ['x','y','width','opacity']) e('reference-' + key).onchange = event => {const v = event.target.valueAsNumber; if (!glyph?.reference || !Number.isFinite(v) || (key === 'width' && v <= 0) || (key === 'opacity' && (v < 0 || v > 1))) return; glyph.reference[key] = v; commit(); draw();};
  function close() {
    if (busy) return;
    if (dirty() && !confirm('此字形尚未暂存。关闭将丢弃当前修改，是否继续？')) return;
    dialog.close();
    if (baseFont?.exportedKey) {$('#font-select').value = baseFont.exportedKey; selectFont();}
  }
  e('editor-close').onclick = close;
  dialog.addEventListener('cancel', event => {if (event.target !== dialog) return; event.preventDefault(); close();});
  dialog.addEventListener('close', () => {requestId++; drag = null; space = false; glyph = null; clean = ''; if (opener?.isConnected) opener.focus();});
  dialog.addEventListener('keydown', event => {
    if (['INPUT','TEXTAREA','SELECT'].includes(event.target.tagName)) return;
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'z') {event.preventDefault(); restore(cursor + (event.shiftKey ? 1 : -1)); return;}
    if (event.key === ' ') {event.preventDefault(); space = true;}
    if (event.key.toLowerCase() === 'p') chooseTool('pen'); if (event.key.toLowerCase() === 'v') chooseTool('select');
    if (event.key === 'Enter' && event.target === svg) {event.preventDefault(); closePath();}
    if (event.key === 'Delete' || event.key === 'Backspace') {event.preventDefault(); deleteNode();}
    if (selected && ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)) {
      event.preventDefault(); const c = glyph.contours[selected.ci][selected.i], p = c.slice(selected.offset, selected.offset + 2), distance = event.shiftKey ? 10 : 1;
      p[0] += event.key === 'ArrowLeft' ? -distance : event.key === 'ArrowRight' ? distance : 0; p[1] += event.key === 'ArrowDown' ? -distance : event.key === 'ArrowUp' ? distance : 0;
      M.move(glyph.contours[selected.ci], selected.i, selected.offset, p); commit(); draw();
    }
  });
  dialog.addEventListener('keyup', event => {if (event.key === ' ') space = false;}); svg.setAttribute('tabindex', '0');
  new ResizeObserver(() => {if (dialog.open) draw();}).observe(workspace);
  window.addEventListener('beforeunload', event => {if (dirty() || [...drafts.values()].some(d => d.glyphs.length && !d.downloaded)) {event.preventDefault(); event.returnValue = '';}});
  async function open(char = 'A', blank = false, source) {
    if (busy) return;
    busy = true;
    try { await requireService(); }
    catch (error) {
      launcherHelp.querySelector('#editor-launcher-message').textContent = error.message;
      if (!launcherHelp.open) launcherHelp.showModal();
      return;
    } finally {busy = false;}
    opener = source || document.activeElement; if (!dialog.open) dialog.showModal();
    await loadGlyph(char, blank); svg.focus();
  }
  window.fontEditor = {open};
  const start = document.createElement('button'); start.type = 'button'; start.id = 'pen-editor-button'; start.textContent = '钢笔绘制';
  start.addEventListener('click', () => open(Array.from($('#text-input').value).find(c => !/\s/u.test(c)) || 'A', true, start));
  $('#import-button').after(start);
})();
