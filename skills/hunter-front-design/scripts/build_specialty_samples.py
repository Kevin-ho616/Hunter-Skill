"""Build reproducible technical fixtures, not a finished typeface or an aesthetic approval."""
import argparse
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import unicodedata

import pathops
import ufoLib2
from fontTools import subset
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor, InstanceDescriptor
from fontTools.ttLib import TTFont, newTable
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.colorLib.builder import buildCOLR, buildCPAL
from fontTools.otlLib.builder import buildStatTable
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib.tables.sbixStrike import Strike
from fontTools.ttLib.tables.sbixGlyph import Glyph

from fetch_specialty_samples import fetch_sources
from font_common import save_json


def compile_source(path, destination, *options):
    subprocess.run([sys.executable, '-m', 'fontmake', str(path), '--output-dir', str(destination),
                    '--no-production-names', '--validate-ufo', '--overlaps-backend', 'pathops', *options], check=True)


def take_subset(font, text):
    options = subset.Options()
    options.layout_features = ['*']
    options.glyph_names = True
    options.notdef_outline = True
    options.name_IDs = ['*']
    options.name_languages = ['*']
    worker = subset.Subsetter(options=options)
    # Thai sara am and compatibility characters can decompose before OpenType substitution.
    worker.populate(text=text+unicodedata.normalize('NFD',text)+unicodedata.normalize('NFKD',text))
    worker.subset(font)
    return font


def rename(font, family):
    style = font['name'].getBestSubFamilyName() or 'Regular'
    for record in list(font['name'].names):
        if record.nameID in [1, 2, 3, 4, 6, 16, 17]:
            font['name'].names.remove(record)
    for key, value in {1: family, 2: style, 3: family + '-' + style + '-1.000',
                       4: family + ' ' + style, 6: family.replace(' ', '') + '-' + style.replace(' ', ''),
                       16: family, 17: style}.items():
        font['name'].setName(value, key, 3, 1, 0x409)


def to_ufo(font, family, style, weight=400, italic=False):
    ufo = ufoLib2.Font()
    info = ufo.info
    info.familyName, info.styleName = family, style
    info.styleMapFamilyName = family
    info.styleMapStyleName = ('bold italic' if weight >= 700 else 'italic') if italic else ('bold' if weight >= 700 else 'regular')
    info.unitsPerEm = font['head'].unitsPerEm
    info.ascender, info.descender = font['hhea'].ascent, font['hhea'].descent
    info.capHeight, info.xHeight = font['OS/2'].sCapHeight, font['OS/2'].sxHeight
    info.openTypeOS2WeightClass = weight
    info.openTypeOS2WidthClass = 5
    info.openTypeOS2VendorID = 'SKIL'
    info.openTypeOS2TypoAscender, info.openTypeOS2TypoDescender = info.ascender, info.descender
    info.openTypeOS2TypoLineGap = 0
    info.openTypeOS2WinAscent, info.openTypeOS2WinDescent = info.ascender, abs(info.descender)
    info.italicAngle = font['post'].italicAngle if italic else 0
    info.versionMajor, info.versionMinor = 1, 0
    info.copyright = font['name'].getDebugName(0)
    info.openTypeNameLicense = font['name'].getDebugName(13)
    info.openTypeNameLicenseURL = font['name'].getDebugName(14)
    info.openTypeNameDesigner = font['name'].getDebugName(9)
    glyphs = font.getGlyphSet()
    encoded = set(font.getBestCmap().values()) | {'.notdef'}
    for name in font.getGlyphOrder():
        if name not in encoded: continue
        glyph = ufo.newGlyph(name)
        glyph.width = font['hmtx'][name][0]
        recording = DecomposingRecordingPen(glyphs)
        glyphs[name].draw(recording); recording.replay(glyph.getPen())
    for cp, name in font.getBestCmap().items():
        ufo[name].unicodes.append(cp)
    ufo.glyphOrder = [n for n in font.getGlyphOrder() if n in encoded]
    # This fixture rebuilds only these features; it does not recover upstream source layout.
    cmap = font.getBestCmap()
    ligatures = [f'sub {cmap[ord("f")]} {cmap[ord(c)]} by {cmap[cp]};' for c, cp in [('i', 0xfb01), ('l', 0xfb02)] if cp in cmap]
    ufo.features.text = 'languagesystem DFLT dflt;\nlanguagesystem latn dflt;\nfeature liga {\n' + '\n'.join(ligatures) + '\n} liga;\n'
    carets = [f'LigatureCaretByPos {cmap[cp]} {round(ufo[cmap[cp]].width/2)};' for cp in [0xfb01,0xfb02] if cp in cmap]
    ufo.features.text += 'table GDEF {\n'+'\n'.join(carets)+'\n} GDEF;\n'
    for a, b in [('A', 'V'), ('T', 'o'), ('V', 'a')]:
        if ord(a) in cmap and ord(b) in cmap:
            ufo.kerning[cmap[ord(a)], cmap[ord(b)]] = -round(info.unitsPerEm * .045)
    return ufo


def original_cjk(stroke=80):
    """Small original geometric control set; full Chinese design still needs its own masters."""
    ufo = ufoLib2.Font()
    ufo.info.familyName, ufo.info.styleName = 'Skill Lab CJK', 'Regular'
    ufo.info.unitsPerEm, ufo.info.ascender, ufo.info.descender = 1000, 880, -120
    ufo.info.versionMajor, ufo.info.versionMinor = 1, 0
    ufo.info.openTypeOS2WeightClass, ufo.info.openTypeOS2WidthClass = 400, 5
    ufo.info.openTypeOS2VendorID = 'SKIL'
    ufo.info.copyright = 'Original technical control glyphs, 2026. Skill test fixture.'
    ufo.info.openTypeNameLicense = 'CC0 1.0 Universal'
    ufo.info.openTypeNameLicenseURL = 'https://creativecommons.org/publicdomain/zero/1.0/'
    def segments(character, lines):
        glyph = ufo.newGlyph('uni%04X' % ord(character)); glyph.unicode = ord(character); glyph.width = 1000
        paths = []
        for x1, y1, x2, y2 in lines:
            length = math.hypot(x2-x1, y2-y1)
            dx, dy = (y2-y1)*stroke/2/length, -(x2-x1)*stroke/2/length
            p = pathops.Path(); pen = p.getPen()
            points = [(x1+dx,y1+dy),(x2+dx,y2+dy),(x2-dx,y2-dy),(x1-dx,y1-dy)]
            pen.moveTo(points[0])
            for point in points[1:]: pen.lineTo(point)
            pen.closePath(); paths.append(p)
        pathops.union(paths, glyph.getPen())
    h = (180,380,820,380); v = (500,80,500,760)
    box = [(200,100,200,740),(200,740,800,740),(800,740,800,100),(800,100,200,100)]
    wood = [(500,80,500,780),(150,570,850,570),(500,530,180,130),(500,530,820,130)]
    for char, lines in {'一':[h], '十':[h,v], '口':box, '日':box+[h], '田':box+[h,(500,100,500,740)],
                        '中':box+[(500,20,500,820)], '人':[(500,720,180,90),(480,680,830,90)],
                        '大':[h,(500,740,200,80),(500,420,820,80)],
                        '小':[v,(300,520,160,180),(700,520,840,180)], '木':wood}.items(): segments(char, lines)
    for char, transforms in {'林':[(.48,0,0,1,10,0),(.48,0,0,1,510,0)],
                             '森':[(.52,0,0,.5,240,400),(.48,0,0,.5,10,0),(.48,0,0,.5,510,0)]}.items():
        glyph = ufo.newGlyph('uni%04X' % ord(char)); glyph.unicode = ord(char); glyph.width = 1000
        for transform in transforms: glyph.getPen().addComponent('uni6728', transform)
    ufo.newGlyph('.notdef').width = 1000
    ufo.newGlyph('space').width = 500; ufo['space'].unicode = 32
    return ufo


def build(sources, out):
    fetch_sources(sources)
    out.mkdir(parents=True, exist_ok=False)
    masters, fonts = out/'masters', out/'fonts'
    masters.mkdir(); fonts.mkdir()
    registry = json.loads((Path(__file__).resolve().parents[1]/'assets/specialty-sources.json').read_text())['sources']
    paths = {s['id']: sources/s['id']/s['font']['file'] for s in registry}
    for s in registry:
        license_out = out/'licenses'/s['id']; license_out.mkdir(parents=True)
        shutil.copyfile(sources/s['id']/s['license']['file'], license_out/'OFL.txt')
    save_json(out/'source-provenance.json', registry)
    latin = ''.join(map(chr, range(32,127))) + ' áÁéÉñÑöÖ́̈ﬁﬂ'
    for italic in [False, True]:
        upstream = TTFont(paths['serif-italic' if italic else 'serif'])
        take_subset(upstream, latin)
        doc = DesignSpaceDocument()
        axis = AxisDescriptor(); axis.name='Weight'; axis.tag='wght'; axis.minimum=200; axis.default=400; axis.maximum=900
        doc.addAxis(axis)
        for weight in [200, 400, 900]:
            font = instantiateVariableFont(upstream, {'wght':weight,'opsz':20}, inplace=False)
            style = f'Master{weight}' + ('Italic' if italic else '')
            ufo = to_ufo(font, 'Skill Lab Serif', style, weight, italic)
            path = masters/(style+'.ufo'); ufo.save(path)
            source = SourceDescriptor(); source.path=str(path); source.name=style
            source.location={'Weight':weight}; source.familyName='Skill Lab Serif'; source.styleName=style
            source.copyInfo=source.copyLib=source.copyFeatures=(weight==400)
            doc.addSource(source)
        for weight, base_style in [(400,'Regular'),(700,'Bold')]:
            style = ('Italic' if weight==400 else 'Bold Italic') if italic else base_style
            instance = InstanceDescriptor(); instance.familyName='Skill Lab Serif'; instance.styleName=style
            instance.name='Skill Lab Serif '+style; instance.location={'Weight':weight}
            instance.styleMapFamilyName='Skill Lab Serif'; instance.styleMapStyleName=style.lower()
            doc.addInstance(instance)
        path = masters/('Italic.designspace' if italic else 'Roman.designspace'); doc.write(path)
        compile_source(path, fonts, '-o','ttf','otf','-i','--check-compatibility')
        compile_source(path, fonts, '-o','variable','--check-compatibility')
    unhinted=out/'unhinted'; unhinted.mkdir()
    for path in fonts.glob('Skill Lab Serif-*'):
        font=TTFont(path); weight=font['OS/2'].usWeightClass; italic=bool(font['OS/2'].fsSelection&1)
        italic_value={'value':1 if italic else 0,'name':'Italic' if italic else 'Roman','flags':0 if italic else 2}
        if not italic: italic_value['linkedValue']=1
        buildStatTable(font,[{'tag':'wght','name':'Weight','ordering':0,'values':[{'value':weight,'name':'Bold' if weight>=700 else 'Regular','flags':0 if weight>=700 else 2}]},
                             {'tag':'ital','name':'Italic','ordering':1,'values':[italic_value]}],macNames=False)
        font.save(path)
        if path.suffix=='.ttf':
            before=unhinted/path.name; path.rename(before)
            subprocess.run([sys.executable,'-m','ttfautohint',str(before),str(path)],check=True)
            hinted=TTFont(path); hinted['head'].flags |= 1<<3; hinted.save(path)
    cjk = original_cjk(); cjk.save(masters/'OriginalCJK.ufo')
    compile_source(masters/'OriginalCJK.ufo', fonts, '-o','ttf','otf')
    import glyphsLib
    glyphs = glyphsLib.to_glyphs([cjk]); glyphs.save(str(masters/'OriginalCJK.glyphs'))
    compile_source(masters/'OriginalCJK.glyphs', out/'glyphs-roundtrip', '-o','ttf')
    save_json(out/'original-cjk-rules.json', {'scope':'一十口日田中人大小木林森', 'stroke':80,
              'route':'original geometric control set; not an original full CJK library',
              'shared_components':{'林':['木','木'],'森':['木','木','木']},
              'exceptions':['Scaled 木 components also scale stroke width; inspect density and correct per design before production.']})
    for key, text in {'arabic':'السَّلَامُ عَلَيْكُمْ', 'devanagari':'हिन्दी क्षि कर्म', 'thai':'ภาษาไทย น้ำ กิ้',
                      'cjk':'中文测试，天地（）「」一二三。123', 'mono':''.join(map(chr,range(32,127))),
                      'emoji':'😀👩‍💻❤️', 'script':'Dancing voices: office AV To aji'}.items():
        font = take_subset(TTFont(paths[key]), text)
        if key=='emoji' and 'SVG ' in font: del font['SVG ']
        # Original fonts retain original names; derived exports receive fixture names and retain rights.
        rename(font, 'Skill Lab '+key.title())
        font.save(fonts/(key+('.otf' if 'CFF ' in font else '.ttf')))
        if key in ['arabic','cjk','mono']:
            font.flavor='woff2'; font.save(fonts/(key+'.woff2'))
    for version in [0,1]:
        font = take_subset(instantiateVariableFont(TTFont(paths['serif']),{'wght':400,'opsz':20}), 'AB ')
        rename(font,'Skill Lab Color'+str(version))
        a,b = [font.getBestCmap()[ord(c)] for c in 'AB']
        colors = {a:[(a,0)],b:[(b,1)]} if version==0 else {
            a:{'Format':10,'Glyph':a,'Paint':{'Format':4,'ColorLine':{'Extend':0,'ColorStop':[
                {'StopOffset':0.,'PaletteIndex':0,'Alpha':1.},{'StopOffset':1.,'PaletteIndex':1,'Alpha':1.}]},
                'x0':0,'y0':0,'x1':600,'y1':600,'x2':600,'y2':0}},
            b:{'Format':10,'Glyph':b,'Paint':{'Format':2,'PaletteIndex':1,'Alpha':.8}}}
        font['CPAL']=buildCPAL([[(.9,.1,.1,1.),(.05,.2,.9,1.)]])
        font['COLR']=buildCOLR(colors,version=version,glyphMap=font.getReverseGlyphMap())
        font.save(fonts/f'colr{version}.ttf')
    import freetype
    from PIL import Image
    font = TTFont(fonts/'colr0.ttf'); del font['COLR']; del font['CPAL']; rename(font,'Skill Lab Bitmap')
    bitmap = newTable('sbix'); bitmap.version=1; bitmap.flags=1; bitmap.strikes={}
    face = freetype.Face(str(fonts/'colr0.ttf'))
    for size in [16,32]:
        face.set_pixel_sizes(0,size); strike = Strike(ppem=size,resolution=72)
        for char in 'AB':
            face.load_char(char, freetype.FT_LOAD_RENDER)
            slot=face.glyph; mask=Image.frombytes('L',(slot.bitmap.width,slot.bitmap.rows),bytes(slot.bitmap.buffer))
            rgba=Image.new('RGBA',mask.size,(220,25,90)); rgba.putalpha(mask); data=io.BytesIO(); rgba.save(data,format='PNG')
            name=font.getBestCmap()[ord(char)]
            strike.glyphs[name]=Glyph(glyphName=name,originOffsetX=slot.bitmap_left,
                                     originOffsetY=slot.bitmap_top-slot.bitmap.rows,graphicType='png ',imageData=data.getvalue())
        bitmap.strikes[size]=strike
    font['sbix']=bitmap; font.save(fonts/'bitmap.ttf')
    print(json.dumps({'output':str(out),'font_files':len(list(fonts.iterdir()))}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources',type=Path); parser.add_argument('out',type=Path)
    args=parser.parse_args(); build(args.sources.resolve(),args.out.resolve())
