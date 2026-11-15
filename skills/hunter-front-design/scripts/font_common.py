"""Read-only geometry and project targets shared by the font tools."""
import io
import json
import math
from pathlib import Path
import re
import statistics
import sys

sys.dont_write_bytecode = True
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from create_proof import inspect_font


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def load_targets(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema_version') != 1:
        raise ValueError('Expected font-targets schema_version 1.')
    coverage = data.get('coverage', {})
    codes = {ord(c) for c in coverage.get('characters', '')}
    for token in coverage.get('ranges', []):
        match = re.fullmatch(r'U\+([0-9a-fA-F]{4,6})(?:-([0-9a-fA-F]{4,6}))?', token)
        if not match:
            raise ValueError(f'Invalid Unicode range: {token}')
        lo, hi = int(match[1], 16), int(match[2] or match[1], 16)
        if not 0 <= lo <= hi <= 0x10ffff or lo <= 0xdfff and hi >= 0xd800:
            raise ValueError(f'Not a range of Unicode scalar values: {token}')
        codes.update(range(lo, hi+1))
    if not codes or any(0xd800 <= cp <= 0xdfff for cp in codes):
        raise ValueError('Declare a nonempty Unicode character scope.')
    for key, spec in data.get('metrics', {}).items():
        if key not in ('cap','xh','asc','desc','n_stem','o_side','o_thin','contrast'):
            raise ValueError(f'Unknown measurement target: {key}')
        if not isinstance(spec, dict) or not all(isinstance(spec.get(k), (int, float)) and not isinstance(spec[k], bool)
                                                 and math.isfinite(spec[k]) for k in ('value', 'tolerance')):
            raise ValueError(f'Metric {key} needs finite value and tolerance.')
        if spec['tolerance'] < 0:
            raise ValueError(f'Negative tolerance: {key}')
    shape = data.get('shaping', {})
    for key in ('samples','pairs'):
        if not isinstance(shape.get(key, []), list) or any(not isinstance(s,str) or not s.strip() for s in shape.get(key, [])):
            raise ValueError(f'shaping.{key} must contain nonempty text strings.')
    if any(len(s) != 2 for s in shape.get('pairs', [])):
        raise ValueError('Gap probes require exactly two characters.')
    limit = shape.get('minimum_gap')
    if limit is not None and (isinstance(limit,bool) or not isinstance(limit,(int,float)) or not math.isfinite(limit)):
        raise ValueError('shaping.minimum_gap must be finite or null.')
    if not isinstance(shape.get('exceptions',{}),dict) or any(not isinstance(s,str) or not s.strip() for s in shape.get('exceptions',{}).values()):
        raise ValueError('Gap exceptions need a reason for each pair.')
    for test in shape.get('features', []):
        if not isinstance(test,dict) or not re.fullmatch(r'[A-Za-z0-9]{4}',test.get('tag','')) or not isinstance(test.get('text'),str) or not test['text'].strip():
            raise ValueError('Feature probes need a four-character ASCII tag and nonempty text.')
        if not isinstance(test.get('must_change',True),bool):
            raise ValueError('Feature must_change must be true or false.')
    return data, sorted(codes)


class PolyPen(BasePen):
    """Sample curves for cut measurements; exact bounds use BoundsPen separately."""
    def __init__(self, glyphs):
        super().__init__(glyphs)
        self.contours, self.open_paths = [], 0

    def _moveTo(self, point):
        self.points = [point]

    def _lineTo(self, point):
        self.points.append(point)

    def _curveToOne(self, a, b, end):
        start = self._getCurrentPoint()
        for i in range(1, 65):
            t, s = i/64, 1-i/64
            self.points.append(tuple(s**3*start[j]+3*s*s*t*a[j]+3*s*t*t*b[j]+t**3*end[j] for j in (0, 1)))

    def _qCurveToOne(self, a, end):
        start = self._getCurrentPoint()
        for i in range(1, 65):
            t, s = i/64, 1-i/64
            self.points.append(tuple(s*s*start[j]+2*s*t*a[j]+t*t*end[j] for j in (0, 1)))

    def _closePath(self):
        self.contours.append(self.points + [self.points[0]])

    def _endPath(self):
        self.open_paths += 1
        self._closePath()


class FontData:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.raw = self.path.read_bytes()
        self.info = inspect_font(self.path, self.raw)
        self.font = TTFont(io.BytesIO(self.raw), recalcTimestamp=False)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font['head'].unitsPerEm
        self._polys, self._bounds = {}, {}
        self._hb = None

    def bounds(self, name):
        if name not in self._bounds:
            pen = BoundsPen(self.glyphs)
            self.glyphs[name].draw(pen)
            self._bounds[name] = pen.bounds
        return self._bounds[name]

    def char_bounds(self, char):
        return self.bounds(self.cmap[ord(char)]) if ord(char) in self.cmap else None

    def polygons(self, name):
        if name not in self._polys:
            pen = PolyPen(self.glyphs)
            self.glyphs[name].draw(pen)
            self._polys[name] = pen
        return self._polys[name]

    def spans(self, name, position, vertical=False):
        axis, other = (0, 1) if vertical else (1, 0)
        crossings = []
        for points in self.polygons(name).contours:
            for a, b in zip(points, points[1:]):
                if (a[axis] <= position < b[axis]) or (b[axis] <= position < a[axis]):
                    t = (position-a[axis])/(b[axis]-a[axis])
                    crossings.append((a[other]+t*(b[other]-a[other]), 1 if b[axis] > a[axis] else -1))
        crossings.sort()
        spans, winding = [], 0
        for i, (value, delta) in enumerate(crossings[:-1]):
            winding += delta
            end = crossings[i+1][0]
            if winding and end-value > 1e-7:
                if spans and abs(spans[-1][1]-value) < 1e-6:
                    spans[-1] = (spans[-1][0], end)
                else:
                    spans.append((value, end))
        return spans

    def sfnt_bytes(self):
        original = self.font.flavor
        try:
            self.font.flavor = None
            buffer = io.BytesIO()
            self.font.save(buffer)
            return buffer.getvalue()
        finally:
            self.font.flavor = original

    def shape(self, text, features=None):
        import uharfbuzz as hb
        if self._hb is None:
            self._hb = hb.Font(hb.Face(self.sfnt_bytes()))
            self._hb.scale = (self.upm, self.upm)
        buffer = hb.Buffer()
        buffer.add_str(text)
        buffer.guess_segment_properties()
        hb.shape(self._hb, buffer, features or {})
        return [(i.codepoint, p.x_advance, p.y_advance, p.x_offset, p.y_offset)
                for i, p in zip(buffer.glyph_infos, buffer.glyph_positions)]


def font_measurements(face):
    boxes = {c: face.char_bounds(c) for c in 'Hxnobdhklpq'}
    cap = boxes['H'][3] if boxes['H'] else None
    values = {'cap': 700 if cap else None, 'xh': None, 'asc': None, 'desc': None,
              'n_stem': None, 'o_side': None, 'o_thin': None, 'contrast': None}
    if cap:
        scale = 700/cap
        values['xh'] = boxes['x'][3]*scale if boxes['x'] else None
        for key, chars, index in [('asc', 'bdhkl', 3), ('desc', 'pq', 1)]:
            available = [boxes[c][index]*scale for c in chars if boxes[c]]
            values[key] = statistics.mean(available) if available else None
        for key, char, vertical in [('n_stem', 'n', False), ('o_side', 'o', False), ('o_thin', 'o', True)]:
            if boxes[char]:
                b = boxes[char]
                pos = (b[0]+b[2])/2 if vertical else (b[1]+b[3])/2
                runs = face.spans(face.cmap[ord(char)], pos, vertical)
                if runs:
                    width = min(z-a for a,z in runs) if vertical else runs[0][1]-runs[0][0]
                    values[key] = width*scale
        if values['o_side'] and values['o_thin']:
            values['contrast'] = values['o_thin']/values['o_side']
    return {k: round(v, 4) if v is not None else None for k, v in values.items()}
