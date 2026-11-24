"""Check declared shaping, family, variation, subset, color, math, mono and SMuFL cases."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import tempfile

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from font_common import FontData, save_json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run_options(spec):
    return {k: spec[k] for k in ['features', 'language', 'script', 'direction', 'variations'] if k in spec}


def shape_case(spec, base):
    face = FontData(base / spec['font'])
    options = run_options(spec)
    run = face.shape_run(spec['text'], **options)
    glyphs = run['glyphs']
    require(bool(glyphs) and all(g['gid'] for g in glyphs), 'Missing glyph in declared shaped run.')
    clusters = [g['cluster'] for g in glyphs]
    require(all(0 <= c < len(spec['text']) for c in clusters), 'Cluster outside source text.')
    reverse = run['direction'] in ['rtl', 'btt']
    require(clusters == sorted(clusters, reverse=reverse), 'Non-monotone grapheme clusters.')
    for key, actual in [('min_glyphs', len(glyphs)), ('max_glyphs', len(glyphs))]:
        if key in spec:
            require(actual >= spec[key] if key == 'min_glyphs' else actual <= spec[key], key + ' violated.')
    if 'expected_gids' in spec:
        require([g['gid'] for g in glyphs] == spec['expected_gids'], 'Shaping glyph IDs differ from the reviewed expectation.')
    if spec.get('zero_advance_mark'):
        require(any(g['x_advance'] == g['y_advance'] == 0 for g in glyphs), 'No zero-advance mark in required mark sample.')
    if run['direction'] in ['ttb', 'btt']:
        require(run['advance'][1] < 0 if run['direction'] == 'ttb' else run['advance'][1] > 0, 'Vertical advance has wrong sign.')
    if 'compare' in spec:
        other = face.shape_run(spec.get('compare_text', spec['text']), **(options | spec['compare']))
        fields = ['gid', 'x_advance', 'y_advance', 'x_offset', 'y_offset']
        a = [[g[k] for k in fields] for g in glyphs]
        b = [[g[k] for k in fields] for g in other['glyphs']]
        require((a != b) == spec.get('must_change', True), 'Expected shaping comparison did not hold.')
        run['comparison'] = other
    return run


def family_case(spec, base):
    family = None
    codes = None
    psnames = set()
    result = []
    for style in spec['styles']:
        font = TTFont(base / style['font'])
        name = font['name']
        current = name.getDebugName(16) or name.getDebugName(1)
        family = current if family is None else family
        require(current == family, 'Typographic family grouping differs.')
        require(font['OS/2'].usWeightClass == style['weight'], 'Wrong weight metadata.')
        italic = style['italic']
        require(bool(font['OS/2'].fsSelection & 1) == italic, 'Wrong OS/2 italic bit.')
        require(bool(font['head'].macStyle & 2) == italic, 'Wrong head italic bit.')
        require((font['post'].italicAngle != 0) == italic, 'Wrong italic angle.')
        require((name.getDebugName(17) or name.getDebugName(2)) == style['style'], 'Wrong style name.')
        ps = name.getDebugName(6)
        require(ps and ps not in psnames, 'Missing or duplicate PostScript name.')
        psnames.add(ps)
        current_codes = set(font.getBestCmap())
        codes = current_codes if codes is None else codes
        require(codes == current_codes, 'Family styles promise different encoded scope.')
        result.append({'font': style['font'], 'family': current, 'style': style['style'], 'weight': style['weight'], 'italic': italic, 'postscript': ps})
    require(bool(result), 'Family needs at least one declared style.')
    return result


def outline(face, gid):
    pen = DecomposingRecordingPen(face.glyphs)
    face.glyphs[face.font.getGlyphName(gid)].draw(pen)
    return pen.value


def subset_case(spec, base):
    original, subset = FontData(base / spec['original']), FontData(base / spec['font'])
    require(original.upm == subset.upm, 'Subset changed UPM.')
    expected = set(map(ord, spec['characters']))
    require(expected <= set(subset.cmap), 'Subset omitted promised Unicode characters.')
    records = []
    for probe in spec['runs']:
        a = original.shape_run(probe['text'], **run_options(probe))
        b = subset.shape_run(probe['text'], **run_options(probe))
        require(len(a['glyphs']) == len(b['glyphs']), 'Subset changed shaped glyph count.')
        for x, y in zip(a['glyphs'], b['glyphs']):
            require(x['gid'] and y['gid'], 'Subset shaping contains .notdef.')
            require(all(x[k] == y[k] for k in ['cluster', 'x_advance', 'y_advance', 'x_offset', 'y_offset']), 'Subset changed shaping positions or clusters.')
            require(outline(original, x['gid']) == outline(subset, y['gid']), 'Subset changed a shaped outline.')
        records.append({'text': probe['text'], 'glyphs': len(a['glyphs']), 'shaping_and_outlines': 'equal'})
    return {'original_glyphs': len(original.font.getGlyphOrder()), 'subset_glyphs': len(subset.font.getGlyphOrder()), 'runs': records,
            'limits': ['Color paints and bitmap image bytes require the color/browser checks in addition to base outlines.']}


def variable_case(spec, base):
    face = FontData(base / spec['font'])
    require('fvar' in face.font and 'STAT' in face.font, 'Variable example needs fvar and STAT.')
    axes = face.font['fvar'].axes
    require(all(math.isfinite(v) for a in axes for v in [a.minValue, a.defaultValue, a.maxValue]), 'Nonfinite axis range.')
    require(all(a.minValue <= a.defaultValue <= a.maxValue for a in axes), 'Invalid axis/default range.')
    defaults = {a.axisTag: a.defaultValue for a in axes}
    if 'locations' in spec:
        locations = spec['locations']
    else:
        require(len(axes) <= 3, 'Declare explicit test locations for more than three axes.')
        values = [sorted(set([a.minValue, a.defaultValue, (a.minValue + a.maxValue) / 2, a.maxValue])) for a in axes]
        locations = [dict(zip(defaults, coords)) for coords in itertools.product(*values)]
    require(0 < len(locations) <= 128, 'Declare 1–128 representative axis locations.')
    names = {n.nameID for n in face.font['name'].names}
    for instance in face.font['fvar'].instances:
        require(instance.subfamilyNameID in names, 'Unnamed variable instance.')
        require(all(a.minValue <= instance.coordinates[a.axisTag] <= a.maxValue for a in axes), 'Named instance outside range.')
    results = []
    signatures = set()
    with tempfile.TemporaryDirectory(prefix='font-specialty-instances-') as tmp:
        for index, partial in enumerate(locations):
            location = defaults | partial
            expected = face.shape_run(spec['text'], variations=location, **run_options({k: v for k, v in spec.items() if k != 'variations'}))
            require(all(g['gid'] for g in expected['glyphs']), 'Variable sample has missing glyphs.')
            font = instantiateVariableFont(face.font, location, inplace=False, updateFontNames=False)
            require('fvar' not in font, 'All declared axes were not pinned.')
            path = Path(tmp) / f'{index}.ttf'; font.save(path)
            static = FontData(path)
            actual = static.shape_run(spec['text'], **run_options({k: v for k, v in spec.items() if k != 'variations'}))
            require([g['gid'] for g in actual['glyphs']] == [g['gid'] for g in expected['glyphs']], 'Static instance changed glyph sequence.')
            for a, b in zip(expected['glyphs'], actual['glyphs']):
                require(all(abs(a[k] - b[k]) <= 1 for k in ['x_advance', 'y_advance', 'x_offset', 'y_offset']), 'Static instance differs from variable shaping by more than one font unit.')
            for name in font.getGlyphOrder():
                width, bearing = font['hmtx'][name]
                bounds = static.bounds(name)
                require(width >= 0 and all(math.isfinite(x) for x in (width, bearing, *(bounds or ()))), 'Invalid outline/metric at axis location.')
            signature = hashlib.sha256(repr([outline(static, g['gid']) for g in actual['glyphs']]).encode()).hexdigest()
            signatures.add(signature)
            results.append({'location': location, 'advance': actual['advance'], 'outline_signature': signature})
    if spec.get('must_vary', False):
        require(len(signatures) > 1, 'Declared variable sample does not vary in its tested outlines.')
    return {'axes': [{'tag': a.axisTag, 'minimum': a.minValue, 'default': a.defaultValue, 'maximum': a.maxValue} for a in axes], 'locations': results,
            'limits': ['Finite location sampling does not prove every coordinate or interpolation path.']}


def color_case(spec, base):
    face = FontData(base / spec['font'])
    font = face.font
    formats = [t for t in ['COLR', 'CPAL', 'CBDT', 'CBLC', 'sbix', 'SVG '] if t in font]
    require(bool(formats), 'No color/bitmap format found.')
    for tag in spec.get('tables', []):
        require(tag in font, 'Missing required color table: ' + tag)
    if 'COLR' in font:
        require('CPAL' in font and bool(font['CPAL'].palettes), 'COLR needs CPAL palettes.')
        require(all(0 <= c.alpha <= 255 for p in font['CPAL'].palettes for c in p), 'Invalid palette alpha.')
        if 'version' in spec:
            require(font['COLR'].version == spec['version'], 'Unexpected COLR version.')
    if 'CBDT' in font:
        require('CBLC' in font, 'CBDT needs CBLC.')
    if 'sbix' in font:
        require(bool(font['sbix'].strikes), 'No bitmap strike.')
        for strike in font['sbix'].strikes.values():
            require(strike.ppem > 0 and any(g.imageData for g in strike.glyphs.values()), 'Empty bitmap strike.')
    for tag in formats:
        font.getTableData(tag)
    runs = [shape_case(dict(p, font=spec['font']), base) for p in spec['runs']]
    return {'tables': formats, 'runs': runs, 'limits': ['OTS and actual color pixel/rendering checks are separate required evidence; parsing alone is insufficient.']}


def math_case(spec, base):
    import uharfbuzz as hb
    face = FontData(base / spec['font'])
    font = hb.Font(hb.Face(face.sfnt_bytes())); font.scale = (face.upm, face.upm)
    require(font.face.has_math_data, 'No MATH layout data.')
    axis = font.get_math_constant(hb.OTMathConstant.AXIS_HEIGHT)
    require(0 < axis < face.upm, 'Invalid math axis.')
    results = []
    for c in spec.get('stretch', '()√'):
        require(ord(c) in face.cmap, 'Missing math glyph.')
        gid = face.font.getGlyphID(face.cmap[ord(c)])
        variants = font.get_math_glyph_variants(gid, 'ttb')
        assembly = font.get_math_glyph_assembly(gid, 'ttb')
        require(bool(variants) or bool(assembly[0]), 'No stretch variants or assembly for ' + c)
        results.append({'character': c, 'variants': [v._asdict() for v in variants], 'assembly_parts': [p._asdict() for p in assembly[0]]})
    return {'axis_height': axis, 'stretch': results, 'limits': ['Actual formula layout is checked in MathML specimens.']}


def mono_case(spec, base):
    face = FontData(base / spec['font'])
    advances = {face.font['hmtx'][face.cmap[ord(c)]][0] for c in spec['characters'] if ord(c) in face.cmap}
    require(set(map(ord, spec['characters'])) <= set(face.cmap), 'Missing promised code characters.')
    require(len(advances) == 1 and next(iter(advances)) > 0, 'Promised characters are not fixed width.')
    width = next(iter(advances))
    for text in spec['texts']:
        run = face.shape_run(text, language='en', script='Latn', direction='ltr')
        require(all(g['gid'] for g in run['glyphs']), 'Code sample has missing glyphs.')
        require(run['advance'][0] == width * len(text), 'Code sample column advance changed.')
    return {'cell_advance': width, 'characters': len(spec['characters']), 'texts': spec['texts']}


def smufl_case(spec, base):
    face = FontData(base / spec['font'])
    metadata = json.loads((base / spec['metadata']).read_text())
    require(metadata.get('fontName') == face.font['name'].getBestFamilyName(), 'SMuFL metadata font name differs.')
    for name, cp in spec['glyphs'].items():
        require(cp in face.cmap, 'Missing SMuFL symbol ' + name)
        require(name in metadata['glyphBBoxes'], 'Missing SMuFL symbol bounding metadata: ' + name)
        require(face.char_bounds(chr(cp)) is not None, 'Blank music symbol ' + name)
    require(bool(metadata.get('glyphsWithAnchors')), 'No SMuFL anchor metadata.')
    return {'glyphs': spec['glyphs'], 'metadata_version': metadata.get('fontVersion'), 'limits': ['Notation-engine engraving is tested separately; a PUA glyph alone is not a score.']}


CHECKS = {'shape': shape_case, 'family': family_case, 'subset': subset_case, 'variable': variable_case, 'color': color_case, 'math': math_case, 'mono': mono_case, 'smufl': smufl_case}


def check_plan(plan_path):
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text())
    require(plan.get('schema_version') == 1 and isinstance(plan.get('cases'), list) and plan['cases'], 'Need a schema_version 1 plan with nonempty cases.')
    rows = []
    seen = set()
    inputs = {}
    for spec in plan['cases']:
        require(isinstance(spec.get('id'), str) and spec['id'] and spec['id'] not in seen, 'Case IDs must be nonempty and unique.')
        seen.add(spec['id'])
        try:
            paths = [spec[k] for k in ['font','original','metadata'] if k in spec]
            paths += [style['font'] for style in spec.get('styles',[])]
            for relative in paths:
                path = (plan_path.parent / relative).resolve()
                inputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            require(spec.get('kind') in CHECKS, 'Unsupported specialty check kind.')
            detail = CHECKS[spec['kind']](spec, plan_path.parent)
            rows.append({'id': spec['id'], 'kind': spec['kind'], 'state': 'PASS', 'detail': detail})
        except ImportError as error:
            rows.append({'id': spec['id'], 'kind': spec.get('kind'), 'state': 'SKIP', 'detail': str(error)})
        except Exception as error:
            rows.append({'id': spec['id'], 'kind': spec.get('kind'), 'state': 'FAIL', 'detail': f'{type(error).__name__}: {error}'})
    status = 'fail' if any(r['state'] == 'FAIL' for r in rows) else 'incomplete' if any(r['state'] == 'SKIP' for r in rows) else 'pass'
    return {'schema_version': 1, 'kind': 'font_specialty_checks', 'status': status, 'plan': str(plan_path), 'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(), 'input_sha256': inputs, 'checks': rows,
            'scope': 'Declared engineering sample conditions only; optical, language, browser and native-platform results are separate.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), 'Use a fresh report path.')
    report = check_plan(args.plan)
    save_json(args.out, report)
    print(json.dumps({'status': report['status'], 'cases': len(report['checks']), 'out': str(args.out)}, ensure_ascii=False))
    raise SystemExit({'pass': 0, 'fail': 1, 'incomplete': 2}[report['status']])
