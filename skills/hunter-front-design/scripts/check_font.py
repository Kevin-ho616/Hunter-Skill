#!/usr/bin/env python3
"""Check declared font scope and optional pure container equivalence without modifying fonts."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from font_common import FontData, font_measurements, load_targets, save_json
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont


def pair_gap(face, text):
    shaped = face.shape(text)
    if len(shaped) != 2:
        return None
    names = [face.font.getGlyphName(g[0]) for g in shaped]
    boxes = [face.bounds(n) for n in names]
    if not all(boxes):
        return None
    a,b = shaped
    lo,hi = max(boxes[0][1]+a[4],boxes[1][1]+b[4]), min(boxes[0][3]+a[4],boxes[1][3]+b[4])
    step = face.upm/250
    gaps = []
    for index in range(math.ceil(lo/step),math.ceil(hi/step)):
        y = index*step+.01
        left = face.spans(names[0],y-a[4])
        right = face.spans(names[1],y-b[4])
        if left and right:
            gaps.append(a[1]+b[3]+right[0][0]-a[3]-left[-1][1])
    return min(gaps)*1000/face.upm if gaps else None


def check_font(path, targets, codes):
    rows = []
    def add(gate, state, detail):
        rows.append({'gate':gate,'state':state,'detail':detail})
    try:
        face = FontData(path)
        font = face.font
        add('parse/container','PASS',face.info['outline']+' / '+face.info['container'])
        # Compile and re-read all tables in memory; original bytes stay untouched.
        for tag in font.keys():
            if tag != 'GlyphOrder':
                font.getTableData(tag)
        restored = TTFont(io.BytesIO(face.sfnt_bytes()),recalcTimestamp=False)
        assert restored.getBestCmap() == font.getBestCmap()
        add('table round trip','PASS','All tables compiled and Unicode mapping survived re-read.')
        missing = [cp for cp in codes if cp not in face.cmap or face.cmap[cp] == '.notdef']
        add('coverage','FAIL' if missing else 'PASS',{'required':len(codes),'missing':[f'U+{cp:04X}' for cp in missing]})
        bad, ymax, ymin = [], 0, 0
        for name in font.getGlyphOrder():
            advance,bearing = font['hmtx'][name]
            box = face.bounds(name)
            if not all(math.isfinite(v) for v in (advance,bearing)) or advance < 0 or box and not all(math.isfinite(v) for v in box):
                bad.append(name)
            if box:
                ymax,ymin = max(ymax,box[3]),min(ymin,box[1])
        blanks = [cp for cp in codes if cp in face.cmap and not face.bounds(face.cmap[cp])
                  and not chr(cp).isspace() and unicodedata.category(chr(cp)) not in ('Cc','Cf','Zl','Zp')]
        add('finite outlines/advances','FAIL' if bad else 'PASS',bad)
        add('unexpected blank glyphs','FAIL' if blanks else 'PASS',[f'U+{cp:04X}' for cp in blanks])
        os2 = font['OS/2']
        fits = os2.usWinAscent >= math.ceil(ymax) and os2.usWinDescent >= math.ceil(-ymin)
        add('vertical ink bounds','PASS' if fits else 'FAIL',{'win':[os2.usWinAscent,os2.usWinDescent],'ink':[ymax,ymin]})
        ps = face.info['postscriptName'] or ''
        valid_name = bool(ps) and len(ps) <= 63 and not re.search(r'[\s\[\](){}<>/%]',ps) and all(33 <= ord(c) <= 126 for c in ps)
        add('PostScript name','PASS' if valid_name else 'FAIL',ps)
        expected = targets.get('expect',{})
        for key in ('family','style'):
            if expected.get(key):
                add('expected '+key,'PASS' if face.info[key] == expected[key] else 'FAIL',face.info[key])
        metrics = font_measurements(face)
        for key,spec in targets.get('metrics',{}).items():
            if key not in metrics:
                raise ValueError(f'Unknown measurement target {key}; supported keys: {list(metrics)}')
            actual = metrics[key]
            state = 'SKIP' if actual is None else 'PASS' if abs(actual-spec['value']) <= spec['tolerance'] else 'FAIL'
            add('metric '+key,state,{'actual':actual,'target':spec['value'],'tolerance':spec['tolerance']})
        shape = targets.get('shaping',{})
        try:
            for text in shape.get('samples',[]):
                glyphs = [g for line in text.splitlines() for g in face.shape(line)]
                add('shape '+text,'PASS' if glyphs and all(g[0] for g in glyphs) else 'FAIL','No .notdef in shaped output.')
            for test in shape.get('features',[]):
                tag,text = test['tag'],test['text']
                present = tag in face.info['features']
                enabled,disabled = face.shape(text,{tag:True}),face.shape(text,{tag:False})
                changed = enabled != disabled
                covered = bool(enabled and disabled) and all(g[0] for g in enabled+disabled)
                add('feature '+tag,'PASS' if present and covered and (changed or not test.get('must_change',True)) else 'FAIL',
                    {'present':present,'sample':text,'changed':changed})
            limit = shape.get('minimum_gap')
            if limit is not None and (not isinstance(limit,(int,float)) or not math.isfinite(limit)):
                raise ValueError('shaping.minimum_gap must be finite or null, in em-normalised 1000 units.')
            for pair in shape.get('pairs',[]):
                if len(pair) != 2:
                    raise ValueError('Gap probes require exactly two characters.')
                gap = pair_gap(face,pair)
                exception = shape.get('exceptions',{}).get(pair)
                state = 'INFO' if gap is None or limit is None or exception else 'PASS' if gap >= limit else 'FAIL'
                if any(g[0] == 0 for g in face.shape(pair)):
                    state = 'FAIL'
                add('ink gap '+pair,state,{'gap':round(gap,3) if gap is not None else None,'minimum':limit,
                                         'exception':exception,'method':'HarfBuzz; horizontal cuts every 4/1000 em; not a visual verdict'})
        except ImportError:
            add('HarfBuzz shaping','SKIP','uharfbuzz unavailable; declared shaping probes were not run.')
        if face.info['variableAxes']:
            add('variable instances','INFO','Default instance only; axis extremes and interpolation are outside this check.')
        add('visual review','SKIP','Use current-font control sheets, full optical review and interactive proof.')
        add('platform review','SKIP','Browser loading, system install, native apps and printing are separate evidence.')
        return {'font':face.info,'metrics':metrics,'checks':rows}
    except Exception as error:
        add('read/validate','FAIL',f'{type(error).__name__}: {error}')
        return {'font':{'path':str(Path(path).resolve())},'checks':rows}


def check_container(desktop, web, targets):
    a,b = FontData(desktop),FontData(web)
    if a.info['container'] != 'sfnt' or b.info['container'] not in ('woff','woff2') or a.info['outline'] != b.info['outline']:
        raise ValueError('Container comparison requires a desktop font and WOFF/WOFF2 with the same outline type.')
    gids = lambda f: {cp:f.font.getGlyphID(n) for cp,n in f.cmap.items()}
    if gids(a) != gids(b) or a.upm != b.upm:
        raise ValueError('Character-to-glyph IDs or em changed; this is not an equivalent full container.')
    order_a,order_b = a.font.getGlyphOrder(),b.font.getGlyphOrder()
    if len(order_a) != len(order_b):
        raise ValueError('Glyph count differs; declared subsets need a separate subset review.')
    for x,y in zip(order_a,order_b):
        if a.font['hmtx'][x] != b.font['hmtx'][y]:
            raise ValueError(f'Container metrics changed at glyph ID {a.font.getGlyphID(x)}.')
        left,right = DecomposingRecordingPen(a.glyphs),DecomposingRecordingPen(b.glyphs)
        a.glyphs[x].draw(left)
        b.glyphs[y].draw(right)
        if left.value != right.value:
            raise ValueError(f'Container outlines changed at glyph ID {a.font.getGlyphID(x)}.')
    shape = targets.get('shaping',{})
    probes = shape.get('samples',[]) + shape.get('pairs',[])
    for text in probes:
        for line in text.splitlines():
            if a.shape(line) != b.shape(line):
                raise ValueError(f'Container shaping differs for {line!r}.')
    for test in shape.get('features',[]):
        for enabled in (True,False):
            if a.shape(test['text'],{test['tag']:enabled}) != b.shape(test['text'],{test['tag']:enabled}):
                raise ValueError(f'Container feature {test["tag"]} differs.')
    return {'desktop_sha256':a.info['sha256'],'web_sha256':b.info['sha256'],
            'state':'PASS','detail':'Glyph IDs, outlines, advances and declared shaping probes agree; glyph-name spelling is not identity.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fonts',nargs='+',type=Path)
    parser.add_argument('--targets',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--container-pair',nargs=2,action='append',default=[])
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Use a fresh report path; existing evidence is not overwritten.')
    targets,codes = load_targets(args.targets)
    reports = [check_font(path,targets,codes) for path in args.fonts]
    containers = []
    for desktop,web in args.container_pair:
        try:
            containers.append(check_container(desktop,web,targets))
        except ImportError:
            containers.append({'state':'SKIP','detail':'uharfbuzz unavailable; container shaping was not checked.'})
        except Exception as error:
            containers.append({'state':'FAIL','detail':str(error)})
    failed = sum(r['state']=='FAIL' for f in reports for r in f['checks']) + sum(c['state']=='FAIL' for c in containers)
    incomplete = any(r['state']=='SKIP' and r['gate'] not in ('visual review','platform review') for f in reports for r in f['checks']) or any(c['state']=='SKIP' for c in containers)
    status = 'fail' if failed else 'incomplete' if incomplete else 'pass'
    result = {'schema_version':1,'kind':'font_validation','status':status,'targets':str(args.targets.resolve()),
              'targets_sha256':hashlib.sha256(args.targets.read_bytes()).hexdigest(),
              'fonts':reports,'container_pairs':containers,
              'scope':'Configured engineering gates only; optical review, installation and app compatibility are not certified.'}
    save_json(args.out,result)
    print(json.dumps({'status':status,'failed':failed,'report':str(args.out.resolve())},ensure_ascii=False))
    return 1 if failed else 2 if incomplete else 0


if __name__ == '__main__':
    sys.exit(main())
