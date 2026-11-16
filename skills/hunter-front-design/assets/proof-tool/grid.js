'use strict';
(() => {
  const fields = [
    ['step', '网格间隔', 25, 5, 200, 5],
    ['baseline', '基线', 0, -500, 1500, 1],
    ['cap', '大写线', 700, -500, 1500, 1],
    ['xheight', '小写线', 520, -500, 1500, 1],
    ['ascender', '上伸线', 700, -500, 1500, 1],
    ['descender', '下伸线', -205, -1000, 1000, 1]
  ];
  const grid = Object.fromEntries(fields.map(([key,, value]) => [key, value]));
  const context = document.createElement('canvas').getContext('2d');
  const board = $('#glyph-board');
  let frame;
  const zoom = document.createElement('dialog');
  zoom.id = 'glyph-zoom';
  zoom.className = 'glyph-zoom-dialog';
  zoom.setAttribute('aria-labelledby', 'glyph-zoom-title');
  zoom.setAttribute('aria-describedby', 'glyph-zoom-help');
  zoom.innerHTML = '<div class="glyph-zoom-head"><h2 id="glyph-zoom-title"></h2><button type="button" autofocus>关闭</button></div><p id="glyph-zoom-help">已放大，可滚动查看细节。按 Esc 关闭。</p><div class="glyph-zoom-stage"></div><div class="glyph-zoom-metrics"></div>';
  document.body.append(zoom);
  const zoomStage = zoom.querySelector('.glyph-zoom-stage');
  let zoomOpener;
  zoom.querySelector('button').addEventListener('click', () => zoom.close());
  zoom.addEventListener('click', event => { if (event.target === zoom) zoom.close(); });
  zoom.addEventListener('close', () => {
    zoomStage.replaceChildren();
    if (zoomOpener?.isConnected) zoomOpener.focus();
    zoomOpener = null;
  });

  function openZoom(svg, char, code, metrics, opener) {
    const enlarged = svg.cloneNode(true);
    const scale = Math.max(.65, svg.getScreenCTM().a * 2);
    const box = svg.viewBox.baseVal;
    enlarged.setAttribute('width', box.width * scale);
    enlarged.setAttribute('height', box.height * scale);
    enlarged.setAttribute('aria-label', char + ' 的放大校样');
    for (const pattern of enlarged.querySelectorAll('pattern')) {
      const previous = pattern.id;
      pattern.id = 'zoom-' + previous;
      for (const rect of enlarged.querySelectorAll('[fill]')) {
        if (rect.getAttribute('fill') === 'url(#' + previous + ')') rect.setAttribute('fill', 'url(#' + pattern.id + ')');
      }
    }
    for (const path of enlarged.querySelectorAll('pattern path')) path.setAttribute('stroke-width', .6 / scale);
    for (const name of ['hide-grid', 'hide-guides', 'hide-bounds']) zoomStage.classList.toggle(name, board.classList.contains(name));
    $('#glyph-zoom-title').textContent = char + ' · ' + code;
    zoom.querySelector('.glyph-zoom-metrics').replaceChildren(metrics.cloneNode(true));
    zoomStage.replaceChildren(enlarged);
    zoomOpener = opener;
    zoom.showModal();
    zoomStage.scrollTo(0, 0);
  }
  for (const [key, label, value, min, max, step] of fields) {
    const item = document.createElement('label');
    item.htmlFor = 'grid-' + key;
    item.textContent = label;
    const input = document.createElement('input');
    Object.assign(input, {id: 'grid-' + key, type: 'number', min, max, step, value});
    item.append(input);
    $('#grid-fields').append(item);
    input.addEventListener('input', () => {
      if (!Number.isFinite(input.valueAsNumber)) return;
      grid[key] = Math.min(max, Math.max(min, input.valueAsNumber));
      requestRender();
    });
    input.addEventListener('change', () => { input.value = grid[key]; });
  }
  const resetButton = document.createElement('button');
  Object.assign(resetButton, {type: 'button', id: 'grid-reset', textContent: '恢复参考线'});
  $('#grid-fields').append(resetButton);

  function setContext() {
    const family = $('#font-select').value;
    context.font = family === 'sans-serif' ? '1000px sans-serif' : `1000px "${family}"`;
    context.fontKerning = 'none';
    context.textAlign = 'left';
    context.textBaseline = 'alphabetic';
  }

  function setFont() {
    if (!fonts.get($('#font-select').value).loaded) { requestRender(); return; }
    setContext();
    const font = fonts.get($('#font-select').value);
    // shortcut: direct imports use H/x/d/p browser bounds; generated proofs supply cmap and source-derived guides.
    const references = font.guides || {baseline: 0,
      cap: Math.round(context.measureText('H').actualBoundingBoxAscent),
      xheight: Math.round(context.measureText('x').actualBoundingBoxAscent),
      ascender: Math.round(context.measureText('d').actualBoundingBoxAscent),
      descender: -Math.round(context.measureText('p').actualBoundingBoxDescent)};
    Object.assign(grid, references);
    for (const [key] of fields) $('#grid-' + key).value = grid[key];
    $('#grid-source').textContent = font.guides
      ? `参考线读取自当前字体表或控制字轮廓（源文件 ${font.unitsPerEm} UPM），1 em 归一为 1000 u；各参考线来源见 font-info.json。调整仅影响校样。`
      : '参考线根据 H / x / d / p 实测，可手动调整。1 em 归一为 1000 u，不是原始字体单位；直接导入的字体缺字可能显示系统回退，请核对覆盖。';
    requestRender();
  }

  function reset() {
    grid.step = 25;
    for (const id of ['grid-visible', 'guides-visible', 'bounds-visible']) $('#' + id).checked = true;
    setFont();
  }

  function requestRender() {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(render);
  }

  function svgElement(name, attributes, text) {
    const element = document.createElementNS('http://www.w3.org/2000/svg', name);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function render() {
    if (zoom.open) zoom.close();
    if (board.hidden) return;
    board.replaceChildren();
    const family = $('#font-select').value;
    if (!fonts.get(family).loaded) {
      board.textContent = '正在载入字体…';
      return;
    }
    setContext();
    const characters = [...new Set(Array.from($('#text-input').value).filter(c => !/\s/u.test(c)))];
    if (!characters.length) { board.textContent = '输入字母、数字或符号，查看网格校样。'; return; }
    const measurements = characters.map(char => {
      if (fonts.get(family).coverage && !fonts.get(family).coverage.has(char.codePointAt(0))) return {char, missing: true};
      const m = context.measureText(char);
      return {char, advance: m.width, left: -m.actualBoundingBoxLeft, right: m.actualBoundingBoxRight,
        top: m.actualBoundingBoxAscent, bottom: -m.actualBoundingBoxDescent};
    });
    const measured = measurements.filter(m => !m.missing);
    // One common viewport and scale preserve proportional widths and shared baselines.
    const left = Math.min(0, ...measured.map(m => m.left)) - 60;
    const right = Math.max(600, ...measured.map(m => Math.max(m.advance, m.right))) + 60;
    const top = Math.max(800, grid.baseline, grid.cap, grid.xheight, grid.ascender, grid.descender, ...measured.map(m => m.top)) + 50;
    const bottom = Math.min(-260, grid.baseline, grid.cap, grid.xheight, grid.ascender, grid.descender, ...measured.map(m => m.bottom)) - 50;
    const width = right - left, height = top - bottom;
    const scale = Math.min(state.size / 1000, $('#canvas').clientWidth / width);
    board.classList.toggle('hide-grid', !$('#grid-visible').checked);
    board.classList.toggle('hide-guides', !$('#guides-visible').checked);
    board.classList.toggle('hide-bounds', !$('#bounds-visible').checked);
    for (const [index, m] of measurements.entries()) {
      const figure = document.createElement('figure');
      figure.className = 'glyph-cell';
      figure.dataset.char = m.char;
      figure.style.width = Math.max(108, width * scale) + 'px';
      const label = document.createElement('figcaption');
      label.className = 'glyph-label';
      label.textContent = m.char;
      const code = document.createElement('span');
      code.textContent = 'U+' + m.char.codePointAt(0).toString(16).toUpperCase().padStart(4, '0');
      label.append(code);
      figure.append(label);
      if (m.missing) {
        const warning = document.createElement('div');
        warning.className = 'glyph-missing';
        warning.textContent = '当前字体未收录';
        figure.append(warning);
      } else {
        const svg = svgElement('svg', {viewBox: `${left} ${-top} ${width} ${height}`,
          width: width * scale, height: height * scale, role: 'img', 'aria-label': m.char + ' 的网格校样'});
        const defs = svgElement('defs', {});
        for (const [name, interval, color, opacity] of [['minor', grid.step, '#aebdc8', .30], ['major', grid.step * 4, '#8e9faa', .40]]) {
          const id = `grid-${index}-${name}`;
          const pattern = svgElement('pattern', {id, x: 0, y: 0, width: interval, height: interval, patternUnits: 'userSpaceOnUse'});
          pattern.append(svgElement('path', {d: `M ${interval} 0 H 0 V ${interval}`, fill: 'none', stroke: color,
            'stroke-opacity': opacity, 'stroke-width': .6 / scale}));
          defs.append(pattern);
        }
        svg.append(defs);
        const bounds = svgElement('g', {class: 'grid-bounds'});
        for (const [x, w] of [[0, m.left], [m.right, m.advance - m.right]]) {
          if (w > 0) bounds.append(svgElement('rect', {x, y: -top, width: w, height, style: 'fill:#6d91a5;fill-opacity:.09;stroke:none'}));
        }
        svg.append(bounds);
        svg.append(svgElement('text', {class: 'glyph-text', x: 0, y: 0, 'font-family': family, 'font-size': 1000}, m.char));
        const overlay = svgElement('g', {class: 'grid-layer'});
        for (const name of ['minor', 'major']) overlay.append(svgElement('rect', {x: left, y: -top, width, height, fill: `url(#grid-${index}-${name})`}));
        svg.append(overlay);
        const guides = svgElement('g', {class: 'grid-guides'});
        for (const [key] of fields.slice(1)) guides.append(svgElement('line', {class: key, x1: left, x2: right, y1: -grid[key], y2: -grid[key]}));
        svg.append(guides);
        const box = svgElement('g', {class: 'grid-bounds'});
        for (const x of [0, m.advance]) box.append(svgElement('line', {x1: x, x2: x, y1: -top, y2: -bottom}));
        box.append(svgElement('rect', {x: m.left, y: -m.top, width: m.right - m.left, height: m.top - m.bottom}));
        svg.append(box);
        const stage = document.createElement('div');
        stage.className = 'glyph-stage';
        stage.append(svg);
        figure.append(stage);
        const metrics = document.createElement('div');
        metrics.className = 'glyph-metrics';
        metrics.textContent = `字面 ${Math.round(m.right - m.left)} · 占位 ${Math.round(m.advance)}`;
        metrics.append(document.createElement('br'), `左 ${Math.round(m.left)} · 右 ${Math.round(m.advance - m.right)} u`);
        figure.append(metrics);
        const magnify = document.createElement('button');
        Object.assign(magnify, {type: 'button', className: 'glyph-zoom-trigger', title: '放大'});
        magnify.setAttribute('aria-label', '放大 ' + m.char);
        magnify.addEventListener('click', () => openZoom(svg, m.char, code.textContent, metrics, magnify));
        stage.append(magnify);
      }
      board.append(figure);
    }
  }

  for (const button of document.querySelectorAll('[data-view]')) button.addEventListener('click', () => {
    const active = button.dataset.view === 'grid';
    document.body.classList.toggle('grid-mode', active);
    for (const item of document.querySelectorAll('[data-view]')) item.setAttribute('aria-pressed', String(item === button));
    $('#preview').hidden = active;
    for (const id of ['glyph-board', 'grid-settings', 'grid-hint']) $('#' + id).hidden = !active;
    for (const [key] of controlSpecs.filter(([key]) => key !== 'size')) {
      for (const suffix of ['number', 'range']) $(`#${key}-${suffix}`).disabled = active;
    }
    for (const item of document.querySelectorAll('[data-align],.features input')) item.disabled = active;
    requestRender();
  });
  for (const id of ['grid-visible', 'guides-visible', 'bounds-visible']) $('#' + id).addEventListener('change', requestRender);
  resetButton.addEventListener('click', setFont);
  window.fontGrid = {requestRender, setFont, reset};
  document.fonts.ready.then(setFont);
})();
