#!/usr/bin/env python3
"""Assemble draft glyphs from named UFO parts and explicit positions."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
import ufoLib2

from check_source import audit_ufo
from font_common import load_targets, save_json


def assemble(font, codes, layout):
    if not isinstance(layout, dict):
        raise ValueError('Layout must be a JSON object.')
    advance, recipes = layout.get('advance'), layout.get('glyphs')
    if type(advance) is not int or not 0 < advance <= 65535:
        raise ValueError('advance must be a positive integer in font units (up to 65535).')
    if not isinstance(recipes, dict) or not recipes:
        raise ValueError('glyphs must map at least one character to part placements.')

    scope = set(codes)
    encoded = {}
    for glyph in font:
        if glyph.name == '.notdef':
            continue
        for cp in set(glyph.unicodes) & scope:
            if cp in encoded:
                raise ValueError(f'Duplicate source mapping for U+{cp:04X}.')
            encoded[cp] = glyph.name

    names = {}
    for char in recipes:
        if len(char) != 1 or ord(char) not in scope:
            raise ValueError(f'Recipe outside declared character scope: {char!r}.')
        cp = ord(char)
        name = f'uni{cp:04X}' if cp <= 0xFFFF else f'u{cp:X}'
        if cp in encoded or name in font:
            raise ValueError(f'{char} already exists in the source. Keep the source glyph or use a new trial source.')
        names[char] = name

    available = set(font.keys()) | set(names.values())
    for char, parts in recipes.items():
        if not isinstance(parts, list) or not parts:
            raise ValueError(f'{char} has no part placements.')
        for placement in parts:
            if not isinstance(placement, list) or len(placement) != 3:
                raise ValueError(f'{char} needs each placement as [part name, x, y].')
            part, x, y = placement
            if not isinstance(part, str) or part not in available:
                raise ValueError(f'{char} references missing part {part!r}.')
            if any(type(v) not in (int, float) or not -32768 <= v <= 32767 for v in (x, y)):
                raise ValueError(f'{char} needs finite offsets in the signed 16-bit font unit range.')

    for char, name in names.items():
        glyph = font.newGlyph(name)
        glyph.unicode, glyph.width = ord(char), advance
        for part, x, y in recipes[char]:
            glyph.getPen().addComponent(part, (1, 0, 0, 1, x, y))

    audit = audit_ufo(font)
    if audit['errors']:
        raise ValueError(f'Invalid UFO source: {audit["errors"][:5]}')
    generated = {}
    for char, name in names.items():
        pen = BoundsPen(font)
        font[name].draw(pen)
        if (not pen.bounds or not all(math.isfinite(v) for v in pen.bounds)
                or pen.bounds[0] >= pen.bounds[2] or pen.bounds[1] >= pen.bounds[3]):
            raise ValueError(f'{char} has no visible outline.')
        generated[char] = {'glyph': name, 'parts': audit['dependencies'][name], 'bounds': pen.bounds}
    missing = sorted(scope - encoded.keys() - set(map(ord, generated)))
    return {
        'status': 'draft',
        'target_count': len(scope),
        'source_encoded_count': len(encoded),
        'assembled_count': len(generated),
        'missing': [{'char': chr(cp), 'codepoint': f'U+{cp:04X}'} for cp in missing],
        'assembled': generated,
        'geometry_candidates': audit['geometry_candidates'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Single-master UFO containing the approved parts')
    parser.add_argument('layout', type=Path, help='JSON with advance and glyphs')
    parser.add_argument('--targets', type=Path, required=True, help='Project font-targets.json')
    parser.add_argument('output', type=Path, help='New output directory for the draft and report')
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.source.resolve()):
        parser.error('Output must be outside the source UFO.')
    _, codes = load_targets(args.targets)
    layout = args.layout.read_bytes()
    font = ufoLib2.Font.open(args.source)
    report = assemble(font, codes, json.loads(layout))
    report['layout_sha256'] = hashlib.sha256(layout).hexdigest()
    report['targets_sha256'] = hashlib.sha256(args.targets.read_bytes()).hexdigest()
    args.output.mkdir(parents=True, exist_ok=False)
    font.save(args.output / 'draft.ufo')
    save_json(args.output / 'layout-report.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'target_count', 'source_encoded_count', 'assembled_count')}
                     | {'missing_count': len(report['missing'])}))


if __name__ == '__main__':
    main()
