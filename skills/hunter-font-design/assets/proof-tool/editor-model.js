'use strict';
(() => {
  const clone = value => JSON.parse(JSON.stringify(value));
  const end = command => command.slice(-2);
  const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
  const same = (a, b) => a.every((v, i) => Math.abs(v - b[i]) < 1e-6);
  const path = contours => contours.map(c => c.map(p => p.join(' ')).join(' ')).join(' ');

  function split(contour, index, t) {
    const c = contour[index], a = end(contour[index - 1]), b = end(c);
    let first, second;
    if (c[0] === 'L') {
      const p = mix(a, b, t);
      first = ['L', ...p]; second = ['L', ...b];
    } else if (c[0] === 'Q') {
      const u = mix(a, c.slice(1, 3), t), v = mix(c.slice(1, 3), b, t), p = mix(u, v, t);
      first = ['Q', ...u, ...p]; second = ['Q', ...v, ...b];
    } else if (c[0] === 'C') {
      const u = mix(a, c.slice(1, 3), t), v = mix(c.slice(1, 3), c.slice(3, 5), t), w = mix(c.slice(3, 5), b, t);
      const r = mix(u, v, t), s = mix(v, w, t), p = mix(r, s, t);
      first = ['C', ...u, ...r, ...p]; second = ['C', ...s, ...w, ...b];
    } else return;
    contour.splice(index, 1, first, second);
  }

  function sample(contour, index, t) {
    const c = contour[index], a = end(contour[index - 1]), b = end(c);
    if (c[0] === 'L') return mix(a, b, t);
    const u = mix(a, c.slice(1, 3), t), v = mix(c.slice(1, 3), c[0] === 'Q' ? b : c.slice(3, 5), t);
    return c[0] === 'Q' ? mix(u, v, t) : mix(mix(u, v, t), mix(v, mix(c.slice(3, 5), b, t), t), t);
  }

  function reverse(contour) {
    const commands = clone(contour), start = end(commands[0]);
    if (commands.at(-1)[0] === 'Z') commands.pop();
    if (!same(end(commands.at(-1)), start)) commands.push(['L', ...start]);
    const result = [['M', ...start]];
    for (let i = commands.length - 1; i > 0; i--) {
      const c = commands[i], p = end(commands[i - 1]);
      result.push(c[0] === 'C' ? ['C', ...c.slice(3, 5), ...c.slice(1, 3), ...p]
        : c[0] === 'Q' ? ['Q', ...c.slice(1, 3), ...p] : ['L', ...p]);
    }
    result.push(['Z']);
    return result;
  }

  function move(contour, index, offset, point) {
    const c = contour[index], dx = point[0] - c[offset], dy = point[1] - c[offset + 1];
    const refs = [[index, offset]];
    if (offset === c.length - 2) {
      const last = contour.length - (contour.at(-1)[0] === 'Z' ? 2 : 1);
      const closedJoin = contour.at(-1)[0] === 'Z' && same(end(contour[last]), end(contour[0]));
      let anchor = index;
      if (closedJoin && (index === 0 || index === last)) {
        refs.push([index === 0 ? last : 0, index === 0 ? contour[last].length - 2 : 1]);
        anchor = last;
      }
      const current = contour[anchor];
      if (current[0] === 'C') refs.push([anchor, 3]);
      if (current[0] === 'Q') refs.push([anchor, 1]);
      const next = anchor === last && closedJoin ? 1 : anchor + 1;
      if (['Q', 'C'].includes(contour[next]?.[0])) refs.push([next, 1]);
    }
    const seen = new Set();
    for (const [i, j] of refs) {
      const key = i + ':' + j;
      if (seen.has(key)) continue;
      seen.add(key); contour[i][j] += dx; contour[i][j + 1] += dy;
    }
  }

  function validate(glyph, closed = true) {
    if (!glyph || !Number.isFinite(glyph.advanceWidth) || glyph.advanceWidth < 0 || glyph.advanceWidth > 65535 || !Array.isArray(glyph.contours)) throw Error('占位宽度或轮廓无效。');
    if (closed && !glyph.contours.length) throw Error('请至少绘制一个闭合轮廓。');
    let count = 0;
    for (const contour of glyph.contours) {
      if (!Array.isArray(contour) || !contour.length || contour[0]?.[0] !== 'M' || (closed && (contour.length < 3 || contour.at(-1)?.[0] !== 'Z'))) throw Error('请闭合全部轮廓后再暂存。');
      for (const [i, c] of contour.entries()) {
        if (!Array.isArray(c) || !Object.hasOwn({M:3, L:3, Q:5, C:7, Z:1}, c[0]) || c.length !== {M:3, L:3, Q:5, C:7, Z:1}[c[0]] || (i && c[0] === 'M') || (i < contour.length - 1 && c[0] === 'Z')) throw Error('源稿轮廓结构无效。');
        if (c.slice(1).some(v => !Number.isFinite(v) || Math.abs(v) > 32767)) throw Error('节点坐标超出有效范围。');
        if (++count > 20000) throw Error('单字节点数量超出本工具范围。');
      }
    }
    return glyph;
  }
  const model = {clone, end, mix, same, path, split, sample, reverse, move, validate};
  if (typeof module !== 'undefined') module.exports = model;
  else window.GlyphModel = model;
})();
