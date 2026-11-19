#!/usr/bin/env python3
"""Create an offline proof tool from one real font without modifying the font."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import shlex
import sys

from fontTools.pens.boundsPen import BoundsPen, ControlBoundsPen
from fontTools.ttLib import TTFont


def inspect_font(source, raw):
    suffix = source.suffix.lower()
    if suffix not in ('.ttf', '.otf', '.woff', '.woff2'):
        raise ValueError('Use a single TTF, OTF, WOFF or WOFF2 font, not a collection.')
    with TTFont(io.BytesIO(raw), recalcTimestamp=False) as font:
        if (font.flavor or '') != (suffix[1:] if suffix.startswith('.woff') else ''):
            raise ValueError('Font container and filename extension disagree.')
        if not any(tag in font for tag in ('glyf', 'CFF ', 'CFF2')):
            raise ValueError('This proof generator requires an outline font.')
        upm = font['head'].unitsPerEm
        if upm <= 0:
            raise ValueError('Invalid unitsPerEm.')
        cmap = {cp: name for cp, name in (font.getBestCmap() or {}).items() if name != '.notdef'}
        if not cmap or any(cp < 0 or cp > 0x10ffff or 0xd800 <= cp <= 0xdfff for cp in cmap):
            raise ValueError('A valid Unicode cmap is required.')
        glyphs = font.getGlyphSet()

        def bounds(char):
            if ord(char) not in cmap:
                return None
            pen = BoundsPen(glyphs)
            glyphs[cmap[ord(char)]].draw(pen)
            return pen.bounds

        def ink(char, index, fallback):
            box = bounds(char)
            return (box[index], f'{char} outline bounds') if box else fallback

        os2 = font.get('OS/2')
        cap = (getattr(os2, 'sCapHeight', 0), 'OS/2.sCapHeight')
        if not cap[0]:
            cap = ink('H', 3, (font['hhea'].ascent, 'hhea.ascent fallback; adjust for design'))
        xheight = (getattr(os2, 'sxHeight', 0), 'OS/2.sxHeight')
        if not xheight[0]:
            xheight = ink('x', 3, (cap[0] * .7, 'estimated from cap; adjust for design'))
        guides = {'baseline': (0, 'font origin'), 'cap': cap, 'xheight': xheight,
                  'ascender': ink('d', 3, (font['hhea'].ascent, 'hhea.ascent fallback')),
                  'descender': ink('p', 1, (font['hhea'].descent, 'hhea.descent fallback'))}
        probe = ''.join(c for c in 'HOBDIMQRSagmnos09258&?ÇÆœß|' if ord(c) in cmap)
        if not probe:
            probe = ''.join(chr(cp) for cp in sorted(cmap) if chr(cp).isprintable())[:20]
        metrics = {}
        for char in probe:
            box = bounds(char)
            if box:
                glyph_name = cmap[ord(char)]
                advance, bearing = font['hmtx'][glyph_name]
                browser_box = list(box)
                if 'glyf' in font:
                    glyph = font['glyf'][glyph_name]
                    browser_box = [bearing, glyph.yMin, bearing + glyph.xMax - glyph.xMin, glyph.yMax]
                else:
                    control = ControlBoundsPen(glyphs)
                    glyphs[glyph_name].draw(control)
                    browser_box = list(control.bounds)
                metrics[char] = {'bounds': list(box), 'browserBounds': browser_box, 'advance': advance}
        name = font['name']
        features = sorted({record.FeatureTag for tag in ('GPOS', 'GSUB') if tag in font
                           for record in getattr(font[tag].table.FeatureList, 'FeatureRecord', [])})
        return {
            'family': name.getDebugName(16) or name.getDebugName(1) or source.stem,
            'style': name.getDebugName(17) or name.getDebugName(2) or 'Unnamed style',
            'version': name.getDebugName(5) or str(font['head'].fontRevision),
            'postscriptName': name.getDebugName(6), 'filename': source.name,
            'file': 'fonts/proof' + suffix, 'sha256': hashlib.sha256(raw).hexdigest(),
            'unitsPerEm': upm, 'codepoints': sorted(cmap), 'glyphCount': len(font.getGlyphOrder()),
            'outline': 'glyf' if 'glyf' in font else 'CFF2' if 'CFF2' in font else 'CFF',
            'container': font.flavor or 'sfnt', 'features': features,
            'variableAxes': [axis.axisTag for axis in font['fvar'].axes] if 'fvar' in font else [],
            'guides': {key: round(value * 1000 / upm, 3) for key, (value, _) in guides.items()},
            'guideSources': {key: origin for key, (_, origin) in guides.items()},
            'probeMetrics': metrics,
        }


def create_proof(source, output):
    source, output = Path(source).resolve(), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f'Use a new output directory: {output}')
    raw = source.read_bytes()
    info = inspect_font(source, raw)
    template = Path(__file__).resolve().parents[1] / 'assets/proof-tool'
    shutil.copytree(template, output)
    runtime = output / 'editor-runtime'
    runtime.mkdir()
    for name in ('serve_editor.py', 'glyph_editor.py', 'create_proof.py'):
        shutil.copy2(Path(__file__).resolve().parent / name, runtime / name)
    launcher = output / '打开字体编辑器.command'
    launcher.write_text('#!/bin/zsh\ncd -- "$(dirname -- "$0")"\nexec ' + shlex.quote(sys.executable)
                        + ' ./editor-runtime/serve_editor.py . --open\n', encoding='utf-8')
    launcher.chmod(0o755)
    target = {'threadId': os.environ.get('CODEX_THREAD_ID'), 'codexExecutable': shutil.which('codex')}
    (output / 'codex-target.json').write_text(json.dumps(target, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'fonts').mkdir()
    (output / info['file']).write_bytes(raw)
    (output / 'font-info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    config = {key: info[key] for key in ('family', 'style', 'version', 'filename', 'file', 'sha256',
                                        'unitsPerEm', 'codepoints', 'guides', 'guideSources')}
    (output / 'font-config.js').write_text('window.FONT_PROOF_CONFIG = ' + json.dumps(config, ensure_ascii=True) + ';\n', encoding='utf-8')
    index = output / 'index.html'
    markup = index.read_text(encoding='utf-8').replace('./font-config.js', './font-config.js?v=' + info['sha256'][:12])
    for asset in ('grid.js', 'grid.css', 'editor-model.js', 'editor.js', 'editor.css'):
        digest = hashlib.sha256((output / asset).read_bytes()).hexdigest()[:12]
        markup = markup.replace('./' + asset, './' + asset + '?v=' + digest)
    index.write_text(markup, encoding='utf-8')
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('font', type=Path)
    parser.add_argument('output', type=Path, help='New directory; existing directories are never overwritten')
    args = parser.parse_args()
    info = create_proof(args.font, args.output)
    print(json.dumps({'index': str(args.output.absolute() / 'index.html'), 'font_sha256': info['sha256'],
                      'version': info['version'], 'unitsPerEm': info['unitsPerEm']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
