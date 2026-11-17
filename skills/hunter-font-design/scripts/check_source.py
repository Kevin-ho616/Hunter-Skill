"""Audit UFO, Designspace or Glyphs source dependencies and contour health without changing it."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import pathops
import ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument
from fontTools.pens.recordingPen import DecomposingRecordingPen

from font_common import save_json


def audit_ufo(font):
    errors, candidates, dependencies, signatures = [], [], {}, {}
    for glyph in font:
        dependencies[glyph.name] = [c.baseGlyph for c in glyph.components]
        signatures[glyph.name] = [[p.type for p in contour] for contour in glyph.contours]
        if not math.isfinite(glyph.width) or glyph.width < 0:
            errors.append([glyph.name, 'invalid advance'])
        for component in glyph.components:
            values = list(component.transformation)
            if not all(math.isfinite(v) for v in values) or values[0]*values[3] == values[1]*values[2]:
                errors.append([glyph.name, 'invalid component transform'])
        for contour in glyph.contours:
            if not contour or contour.open:
                errors.append([glyph.name, 'empty/open contour'])
            if any(not math.isfinite(v) for point in contour for v in [point.x,point.y]):
                errors.append([glyph.name, 'nonfinite point'])
    visited, active = set(), set()
    def visit(name):
        if name not in dependencies:
            raise ValueError('Missing component: '+name)
        if name in active:
            raise ValueError('Component cycle: '+name)
        if name in visited: return
        active.add(name)
        for child in dependencies[name]: visit(child)
        active.remove(name); visited.add(name)
    try:
        for name in dependencies: visit(name)
    except ValueError as error:
        errors.append(['components', str(error)])
    if not errors:
        for glyph in font:
            path = pathops.Path(); pen = DecomposingRecordingPen(font); glyph.draw(pen)
            pen.replay(path.getPen())
            if not path: continue
            simple = pathops.simplify(path)
            if abs(path.area-simple.area) > .1 or len(list(path.contours)) != len(list(simple.contours)):
                candidates.append({'glyph':glyph.name,'area_before':path.area,'area_after':simple.area,
                                   'reason':'overlap/self-intersection/winding candidate; inspect intended construction'})
    reverse = {name:[] for name in dependencies}
    for name, children in dependencies.items():
        for child in children:
            if child in reverse: reverse[child].append(name)
    return {'errors':errors,'geometry_candidates':candidates,'dependencies':dependencies,
            'direct_dependents':reverse,'topology':signatures}


def check_source(path):
    path = Path(path).resolve()
    if path.suffix == '.designspace':
        doc = DesignSpaceDocument.fromfile(path)
        sources = [(s.name or str(s.path),ufoLib2.Font.open(s.path)) for s in doc.sources]
    elif path.suffix == '.glyphs':
        import glyphsLib
        sources = [(str(i),f) for i,f in enumerate(glyphsLib.to_ufos(glyphsLib.load(str(path)), ufo_module=ufoLib2))]
    elif path.suffix == '.ufo':
        sources = [(path.name,ufoLib2.Font.open(path))]
    else:
        raise ValueError('Expected .ufo, .designspace or .glyphs source.')
    if not sources: raise ValueError('No source masters.')
    reports = {name:audit_ufo(font) for name,font in sources}
    baseline = next(iter(reports.values()))
    compatible = all(r['topology']==baseline['topology'] and r['dependencies']==baseline['dependencies'] for r in reports.values())
    files = []
    for _, font in sources:
        if font.path:
            files.extend(p for p in Path(font.path).rglob('*') if p.is_file() and p.name!='.DS_Store')
    if path.is_file(): files.append(path)
    return {'status':'pass' if compatible and not any(r['errors'] for r in reports.values()) else 'fail',
            'source':str(path),'masters':reports,'topology_compatible':compatible,
            'input_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))},
            'limits':['Topology equality is necessary, not sufficient for interpolation. Compile with compatibility checks and inspect intermediate shapes.',
                      'Geometry candidates require review; finite sampling does not certify all curve geometry or optical extrema.']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('source',type=Path); parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(); result=check_source(args.source); save_json(args.out,result)
    print(json.dumps({'status':result['status'],'out':str(args.out)})); raise SystemExit(result['status']!='pass')
