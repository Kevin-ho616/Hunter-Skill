#!/usr/bin/env python3
"""Read static outlines and apply hash-bound glyph drafts without overwriting a font."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path

from fontTools.misc.roundTools import otRound
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

from create_proof import inspect_font


class OutlinePen(BasePen):
    def __init__(self, glyphs):
        super().__init__(glyphs)
        self.contours = []

    def _moveTo(self, p):
        self.contours.append([['M', *p]])

    def _lineTo(self, p):
        self.contours[-1].append(['L', *p])

    def _qCurveToOne(self, a, p):
        self.contours[-1].append(['Q', *a, *p])

    def _curveToOne(self, a, b, p):
        self.contours[-1].append(['C', *a, *b, *p])

    def _closePath(self):
        contour = self.contours[-1]
        if contour[-1][-2:] != contour[0][-2:]:
            contour.append(['L', *contour[0][-2:]])
        self.contours[-1].append(['Z'])

    def _endPath(self):
        raise ValueError('Open source contours must be repaired before editing.')


def editable(font):
    unsupported = {'fvar', 'CFF2', 'COLR', 'SVG ', 'sbix', 'CBDT', 'EBDT'} & set(font.keys())
    if unsupported:
        raise ValueError('本版仅编辑静态轮廓字体；不支持：' + ', '.join(sorted(unsupported)))
    if 'glyf' not in font and 'CFF ' not in font:
        raise ValueError('需要 glyf 或 CFF 轮廓。')
    if 'CFF ' in font:
        top = font['CFF '].cff.topDictIndex[0]
        if hasattr(top, 'ROS'):
            raise ValueError('本版暂不回写 CID CFF，请使用静态 TTF 或普通 CFF。')


def codepoint(value):
    if not isinstance(value, str) or len(value) != 1 or 0xD800 <= ord(value) <= 0xDFFF:
        raise ValueError('请选择一个有效 Unicode 字符。')
    return ord(value)


def read_glyph(raw, filename, char):
    cp = codepoint(char)
    info = inspect_font(Path(filename), raw)
    with TTFont(io.BytesIO(raw), recalcTimestamp=False) as font:
        editable(font)
        name = (font.getBestCmap() or {}).get(cp)
        pen = OutlinePen(font.getGlyphSet())
        if name:
            font.getGlyphSet()[name].draw(pen)
        width = font['hmtx'][name][0] if name else info['unitsPerEm']
        return {'info': info, 'glyph': {'char': char, 'glyphName': name,
                'advanceWidth': width, 'contours': pen.contours}}


def validate_glyph(glyph):
    if not isinstance(glyph, dict):
        raise ValueError('Invalid glyph draft.')
    codepoint(glyph.get('char'))
    width = glyph.get('advanceWidth')
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not math.isfinite(width) or not 0 <= width <= 65535:
        raise ValueError('占位宽度必须在 0–65535 之间。')
    contours = glyph.get('contours')
    if not isinstance(contours, list) or not contours or len(contours) > 2000:
        raise ValueError('请至少绘制一个闭合轮廓。')
    count = 0
    for contour in contours:
        if not isinstance(contour, list) or len(contour) < 3 or not isinstance(contour[0], list) or not contour[0] or contour[0][0] != 'M' or contour[-1] != ['Z']:
            raise ValueError('每个轮廓必须从起点开始并闭合。')
        for i, command in enumerate(contour):
            if not isinstance(command, list) or not command or not isinstance(command[0], str):
                raise ValueError('Invalid path command.')
            kind = command[0]
            if kind not in {'M', 'L', 'Q', 'C', 'Z'} or len(command) != {'M': 3, 'L': 3, 'Q': 5, 'C': 7, 'Z': 1}[kind]:
                raise ValueError('Invalid path command.')
            if (i > 0 and kind == 'M') or (i < len(contour) - 1 and kind == 'Z'):
                raise ValueError('轮廓中的起点或闭合位置无效。')
            for value in command[1:]:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not -32767 <= value <= 32767:
                    raise ValueError('节点坐标必须是 -32767–32767 内的有限数值。')
            count += 1
    if count > 20000:
        raise ValueError('单字节点数量超出本工具范围。')


def draw(glyph, pen):
    for contour in glyph['contours']:
        for command in contour:
            kind, *v = command
            if kind == 'M':
                pen.moveTo(tuple(v))
            elif kind == 'L':
                pen.lineTo(tuple(v))
            elif kind == 'Q':
                pen.qCurveTo(tuple(v[:2]), tuple(v[2:]))
            elif kind == 'C':
                pen.curveTo(tuple(v[:2]), tuple(v[2:4]), tuple(v[4:]))
            else:
                pen.closePath()


def apply_edits(raw, filename, draft):
    digest = hashlib.sha256(raw).hexdigest()
    if not isinstance(draft, dict) or draft.get('format') != 'hunter-glyph-edits' or draft.get('version') != 1:
        raise ValueError('不是本工具支持的字形源稿。')
    if draft.get('baseSha256') != digest:
        raise ValueError('源稿与当前字体 SHA-256 不一致；请载入源稿对应的原字体。')
    edits = draft.get('glyphs')
    if not isinstance(edits, list) or not 1 <= len(edits) <= 1000:
        raise ValueError('源稿需要包含 1–1000 个修改字形。')
    for glyph in edits:
        validate_glyph(glyph)
    with TTFont(io.BytesIO(raw), recalcTimestamp=False) as font:
        editable(font)
        if draft.get('unitsPerEm') != font['head'].unitsPerEm:
            raise ValueError('源稿 UPM 与原字体不符。')
        cmap = dict(font.getBestCmap() or {})
        names = set()
        for glyph in edits:
            expected = cmap.get(ord(glyph['char']))
            if glyph.get('glyphName') != expected:
                raise ValueError('源稿字符与原字体字形映射不符。')
            name = expected or f'hunter_u{ord(glyph["char"]):04X}'
            if name in names or (not expected and name in font.getGlyphOrder()):
                raise ValueError('源稿重复修改同一字形或新字形名称冲突。')
            names.add(name)
        dependents = set()
        if 'glyf' in font:
            changed = set(names)
            while True:
                more = {name for name in font.getGlyphOrder() if font['glyf'][name].isComposite()
                        and any(c.glyphName in changed for c in font['glyf'][name].components)} - changed
                if not more:
                    break
                dependents.update(more)
                changed.update(more)
            for name in dependents:
                if any(not hasattr(c, 'x') for c in font['glyf'][name].components):
                    raise ValueError('关联复合字形使用节点绑定；须回原始字体源修改：' + name)
                font['glyf'][name].removeHinting()
        order = list(font.getGlyphOrder())
        for glyph in edits:
            cp = ord(glyph['char'])
            name = cmap.get(cp) or f'hunter_u{cp:04X}'
            width = otRound(glyph['advanceWidth'])
            if 'glyf' in font:
                pen = TTGlyphPen(None)
                draw(glyph, Cu2QuPen(pen, max_err=.5))
                font['glyf'][name] = pen.glyph()
                font['glyf'][name].recalcBounds(font['glyf'])
                lsb = getattr(font['glyf'][name], 'xMin', 0)
            else:
                top = font['CFF '].cff.topDictIndex[0]
                pen = T2CharStringPen(width, None)
                draw(glyph, pen)
                charstring = pen.getCharString(top.Private, font['CFF '].cff.GlobalSubrs)
                strings = top.CharStrings
                if name not in strings.charStrings:
                    if strings.charStringsAreIndexed:
                        strings.charStrings[name] = len(strings.charStringsIndex)
                        strings.charStringsIndex.append(charstring)
                    else:
                        strings.charStrings[name] = charstring
                else:
                    strings[name] = charstring
                box = BoundsPen(None)
                draw(glyph, box)
                lsb = otRound(box.bounds[0]) if box.bounds else 0
            font['hmtx'][name] = width, lsb
            if cp not in cmap:
                order.append(name)
                cmap[cp] = name
                for table in font['cmap'].tables:
                    if table.isUnicode() and hasattr(table, 'cmap') and (cp <= 0xFFFE or table.format in (12, 13)):
                        table.cmap[cp] = name
        font.setGlyphOrder(order)
        if 'CFF ' in font:
            font['CFF '].cff.topDictIndex[0].charset = order
        if any(cp >= 0xFFFF for cp in cmap) and not any(t.format == 12 and t.isUnicode() for t in font['cmap'].tables):
            table = CmapSubtable.newSubtable(12)
            table.platformID, table.platEncID, table.language = 3, 10, 0
            table.cmap = dict(cmap)
            font['cmap'].tables.append(table)
        if 'OS/2' in font and any(glyph['glyphName'] is None for glyph in edits):
            font['OS/2'].recalcUnicodeRanges(font)
        dropped = [tag for tag in ('DSIG', 'hdmx', 'LTSH', 'VDMX') if tag in font]
        for tag in dropped:
            del font[tag]
        revision = round(font['head'].fontRevision + .001, 3)
        font['head'].fontRevision = revision
        edit_content = [{key: glyph[key] for key in ('char', 'glyphName', 'advanceWidth', 'contours')} for glyph in edits]
        edit_hash = hashlib.sha256(json.dumps(edit_content, sort_keys=True).encode()).hexdigest()[:12]
        for record in font['name'].names:
            if record.nameID in (3, 5):
                text = f'Version {revision:.3f}; Hunter Editor draft' if record.nameID == 5 else f'{record.toUnicode()}; HE-{edit_hash}'
                record.string = text.encode(record.getEncoding())
        target = io.BytesIO()
        font.save(target)
    result = target.getvalue()
    info = inspect_font(Path(filename), result)
    return result, {'baseSha256': digest, 'sha256': info['sha256'], 'info': info,
                    'editedGlyphs': sorted(names), 'dependentGlyphs': sorted(dependents),
                    'droppedTables': dropped, 'curveTolerance': .5,
                    'reviewRequired': ['光学与字距审校', '修改字形及关联组件的 hinting', '目标软件与平台验收']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('font', type=Path)
    parser.add_argument('draft', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.suffix.lower() != args.font.suffix.lower():
        parser.error('Output must keep the original container extension.')
    result, report = apply_edits(args.font.read_bytes(), args.font.name,
                                 json.loads(args.draft.read_text(encoding='utf-8')))
    with args.output.open('xb') as stream:
        stream.write(result)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
