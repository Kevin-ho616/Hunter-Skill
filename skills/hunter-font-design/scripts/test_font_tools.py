"""Small deterministic fonts exercise the read-only measurement, checks and book tools."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from font_common import FontData, font_measurements, load_targets, save_json
from measure_reference import calibrate, font_report, image_report, pixel_runs
from check_font import check_font, check_container, pair_gap
from create_font_book import create_book


def fixture(path, cff=False, punctuation_top=None, extra_codes=()):
    codes = [*range(32,127),*extra_codes]
    names = ['.notdef']+[f'c{cp:04X}' for cp in codes]
    builder = FontBuilder(1000,isTTF=not cff)
    builder.setupGlyphOrder(names)
    builder.setupCharacterMap({cp:f'c{cp:04X}' for cp in codes})
    glyphs = {}
    for name in names:
        pen = T2CharStringPen(600,None) if cff else TTGlyphPen(None)
        def rect(x0,y0,x1,y1,reverse=False):
            points = [(x0,y0),(x0,y1),(x1,y1),(x1,y0)]
            if reverse:
                points.reverse()
            pen.moveTo(points[0])
            for point in points[1:]:
                pen.lineTo(point)
            pen.closePath()
        cp = int(name[1:],16) if name != '.notdef' else 72
        if cp == 111:
            rect(40,0,540,500)
            rect(120,80,460,420,True)
        elif cp != 32:
            height = 700 if chr(cp).isupper() or chr(cp) in 'bdhkl' else 500
            if cp == 40 and punctuation_top is not None:
                height = punctuation_top
            if cp > 127:
                height = 900
            if cp in (110,72):
                rect(40,0,120,height)
                rect(480,0,560,height)
                rect(120,300 if cp == 72 else 420,480,380 if cp == 72 else 500)
            else:
                rect(40,-150 if chr(cp) in 'pq,' else 0,540,height)
        glyphs[name] = pen.getCharString() if cff else pen.glyph()
    if cff:
        builder.setupCFF('Fixture-Regular',{'FullName':'Fixture Regular','FamilyName':'Fixture','Weight':'Regular'},glyphs,{})
    else:
        builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({name:(600,40) for name in names})
    builder.setupHorizontalHeader(ascent=800,descent=-200)
    builder.setupNameTable({'familyName':'Fixture','styleName':'Regular','uniqueFontIdentifier':'Fixture 1.000',
                            'fullName':'Fixture Regular','psName':'Fixture-Regular','version':'Version 1.000'})
    builder.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=1000 if extra_codes else 800,usWinDescent=200,sxHeight=500,sCapHeight=700)
    builder.setupPost()
    addOpenTypeFeaturesFromString(builder.font,'feature kern { pos c0041 c0056 -40; } kern;')
    builder.save(path)


class FontToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ttf = self.root/'fixture.ttf'
        fixture(self.ttf)
        self.targets = {'schema_version':1,'coverage':{'ranges':['U+0020-007E']},
                        'metrics':{'n_stem':{'value':80,'tolerance':.01}},
                        'shaping':{'samples':['HnxodnH AV'],'pairs':['AV'],
                                   'features':[{'tag':'kern','text':'AV'}]}}

    def write(self,name,data):
        path = self.root/name
        save_json(path,data)
        return path

    def failed(self,path,targets=None,codes=None):
        result = check_font(path,targets or self.targets,codes or list(range(32,127)))
        return [r['gate'] for r in result['checks'] if r['state']=='FAIL']

    def test_exact_metrics_and_readonly_ttf_cff(self):
        otf = self.root/'fixture.otf'
        fixture(otf,True)
        for path in (self.ttf,otf):
            before = path.read_bytes()
            values = font_measurements(FontData(path))
            self.assertEqual(values['xh'],500)
            self.assertEqual(values['n_stem'],80)
            self.assertEqual(values['o_side'],80)
            self.assertEqual(values['contrast'],1)
            self.assertEqual(self.failed(path),[])
            self.assertEqual(path.read_bytes(),before)

    def test_localized_names_require_exact_language_and_preserve_english(self):
        otf = self.root/'fixture.otf'
        fixture(otf,True)
        names = {1:'示例字体',2:'常规',4:'示例字体 常规',16:'示例字体',17:'常规'}
        records = [{'name_id':k,'platform_id':3,'encoding_id':1,'language_id':2052,'value':v}
                   for k,v in names.items()]
        records += [{'name_id':1,'platform_id':3,'encoding_id':1,'language_id':1033,'value':'Fixture'},
                    {'name_id':6,'platform_id':3,'encoding_id':1,'language_id':1033,'value':'Fixture-Regular'}]
        targets = {**self.targets,'expect':{'name_records':records}}
        for source in (self.ttf,otf):
            before = source.read_bytes()
            self.assertIn('name record 16/3/1/2052',self.failed(source,targets))
            localized = self.root/('localized'+source.suffix)
            with TTFont(source,recalcTimestamp=False) as font:
                for key,value in names.items():
                    font['name'].setName(value,key,3,1,2052)
                font.save(localized)
            exported = localized.read_bytes()
            self.assertEqual(self.failed(localized,targets),[])
            wrong = {**targets,'expect':{'name_records':[
                {**records[0],'language_id':1033}, {**records[3],'value':'错误名称'}]}}
            self.assertIn('name record 1/3/1/1033',self.failed(localized,wrong))
            self.assertIn('name record 16/3/1/2052',self.failed(localized,wrong))
            invalid = {**targets,'expect':{'name_records':[{**records[0],'language_id':'0x0804'}]}}
            self.assertIn('read/validate',self.failed(localized,invalid))
            self.assertEqual(localized.read_bytes(),exported)
            self.assertEqual(source.read_bytes(),before)

    def test_pixel_calibration_and_missing_anchors(self):
        result = calibrate(self.ttf,240,self.root/'calibration.json')
        self.assertLess(abs(result['errors']['n_stem']),5)
        self.assertLess(abs(result['errors']['xh']),5)
        from PIL import Image,ImageDraw,ImageFont
        image = Image.new('RGB',(900,300),'white')
        ImageDraw.Draw(image).text((20,20),'Ardor',font=ImageFont.truetype(str(self.ttf),180),fill='black')
        path = self.root/'logo.png'
        image.save(path)
        self.assertIsNone(image_report(path,'Ardor')['metrics']['cap']['value'])
        proxy = image_report(path,'Ardor','A','r','rd')
        self.assertEqual(proxy['metrics']['cap']['confidence'],'low')
        with self.assertRaises(ValueError):
            image_report(path,'Ardors')
        with self.assertRaises(FileExistsError):
            calibrate(self.ttf,240,self.root/'calibration.json')

    def test_targets_reject_invalid_ranges_and_thresholds(self):
        for i,change in enumerate(({'coverage':{'ranges':['U+D800-DFFF']}},
                                   {'metrics':{'xh':{'value':500,'tolerance':-1}}},
                                   {'metrics':{'nonsense':{'value':1,'tolerance':0}}},
                                   {'punctuation_height':{'max_above_cap':True}},
                                   {'punctuation_height':{'max_above_cap':-1}},
                                   {'punctuation_height':{'max_above_cap':float('nan')}},
                                   {'punctuation_height':{'max_above_cap':0,'extra_characters':['1']}},
                                   {'punctuation_height':{'max_above_cap':0,'extra_characters':'¹'}},
                                   {'shaping':{'features':[{'tag':"bad'",'text':'AV'}]}},
                                   {'shaping':{'pairs':['AVX']}})):
            with self.assertRaises(ValueError):
                load_targets(self.write(f'bad{i}.json',{**self.targets,**change}))

    def test_punctuation_upper_bounds_real_outlines_and_exceptions(self):
        codes = [*range(32,127),0x00C1,0x0301,0x00B9]
        targets = {**self.targets,'punctuation_height':{'max_above_cap':0}}
        for cff,suffix in ((False,'ttf'),(True,'otf')):
            for top,state in ((700,'PASS'),(720,'FAIL')):
                path = self.root/f'punct-{top}.{suffix}'
                fixture(path,cff,punctuation_top=top,extra_codes=codes[95:])
                before = path.read_bytes()
                result = check_font(path,targets,codes)
                row = next(r for r in result['checks'] if r['gate']=='punctuation upper bounds')
                self.assertEqual(row['state'],state)
                self.assertEqual(row['detail']['cap_height'],700)
                self.assertEqual([r['character'] for r in row['detail']['violations']],['('] if top > 700 else [])
                self.assertTrue(any(r['character']==',' and r['y_min']<0 for r in row['detail']['measurements']))
                extended = {**targets,'punctuation_height':{'max_above_cap':0,'extra_characters':'¹'}}
                extra = next(r for r in check_font(path,extended,codes)['checks'] if r['gate']=='punctuation upper bounds')
                self.assertIn('¹',[r['character'] for r in extra['detail']['violations']])
                self.assertNotIn('punctuation upper bounds',[r['gate'] for r in check_font(path,self.targets,codes)['checks']])
                self.assertEqual(path.read_bytes(),before)
        font = TTFont(self.ttf)
        for table in font['cmap'].tables:
            table.cmap.pop(72,None)
        noH = self.root/'punct-no-H.ttf';font.save(noH)
        row = next(r for r in check_font(noH,targets,[40])['checks'] if r['gate']=='punctuation upper bounds')
        self.assertEqual(row['state'],'SKIP')

    def test_isolated_jpeg_fringe_does_not_become_a_stroke(self):
        from PIL import Image,ImageDraw
        gray = Image.new('L',(60,20),255)
        draw = ImageDraw.Draw(gray)
        draw.rectangle((10,0,14,19),fill=0)
        draw.rectangle((40,0,44,19),fill=0)
        gray.putpixel((25,10),248)
        self.assertEqual(pixel_runs(gray,(0,0,60,20),10),[5,5])

    def test_missing_blank_clipped_corrupt_and_feature_fail(self):
        font = TTFont(self.ttf)
        for table in font['cmap'].tables:
            table.cmap.pop(65,None)
        missing = self.root/'missing.ttf'
        font.save(missing)
        self.assertIn('coverage',self.failed(missing))
        font = TTFont(self.ttf)
        font['glyf']['c0041'] = TTGlyphPen(None).glyph()
        font['OS/2'].usWinAscent = 100
        bad = self.root/'blank-clipped.ttf'
        font.save(bad)
        self.assertIn('unexpected blank glyphs',self.failed(bad))
        self.assertIn('vertical ink bounds',self.failed(bad))
        corrupt = self.root/'corrupt.ttf'
        corrupt.write_bytes(b'not a font')
        self.assertIn('read/validate',self.failed(corrupt))
        font = TTFont(self.ttf)
        del font['GPOS']
        nofeature = self.root/'no-feature.ttf'
        font.save(nofeature)
        self.assertIn('feature kern',self.failed(nofeature))
        with self.assertRaises(ValueError):
            load_targets(self.write('negative.json',{**self.targets,'shaping':{'minimum_gap':True}}))

    def test_container_ignores_names_but_catches_changed_geometry_and_shaping(self):
        font = TTFont(self.ttf)
        font['post'].formatType = 3
        font.flavor = 'woff2'
        web = self.root/'fixture.woff2'
        font.save(web)
        self.assertEqual(check_container(self.ttf,web,self.targets)['state'],'PASS')
        self.assertNotEqual(FontData(self.ttf).font.getGlyphOrder(),FontData(web).font.getGlyphOrder())
        self.assertIsNotNone(pair_gap(FontData(web),'AV'))
        changed = TTFont(web)
        a = changed.getBestCmap()[65]
        changed['hmtx'][a] = (601,40)
        changed.save(self.root/'changed.woff2')
        with self.assertRaisesRegex(ValueError,'metrics changed'):
            check_container(self.ttf,self.root/'changed.woff2',self.targets)
        changed = TTFont(web)
        del changed['GPOS']
        changed.save(self.root/'shaping.woff2')
        with self.assertRaisesRegex(ValueError,'shaping differs'):
            check_container(self.ttf,self.root/'shaping.woff2',self.targets)
        changed = TTFont(web)
        changed['glyf'][a].coordinates[0] = (41,0)
        changed.save(self.root/'outline.woff2')
        with self.assertRaisesRegex(ValueError,'outlines changed'):
            check_container(self.ttf,self.root/'outline.woff2',self.targets)

    def test_cli_book_hashes_references_and_stale_reports(self):
        self.write('measure.json',font_report(self.ttf))
        self.targets['reference_measurements'] = ['measure.json']
        target = self.write('targets.json',self.targets)
        report = self.root/'check.json'
        run = subprocess.run([sys.executable,str(Path(__file__).with_name('check_font.py')),str(self.ttf),
                              '--targets',str(target),'--out',str(report)],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr+run.stdout)
        book = self.root/'book'
        result = create_book([self.ttf],target,book,report)
        self.assertGreaterEqual(result['pages'],6)
        self.assertIn('Reference evidence:',(book/'index.html').read_text())
        meta = json.loads((book/'book-info.json').read_text())
        self.assertEqual(meta['missing_codepoints'],0)
        self.assertEqual(hashlib.sha256((book/meta['fonts'][0]['book_file']).read_bytes()).hexdigest(),meta['fonts'][0]['sha256'])
        with self.assertRaises(FileExistsError):
            create_book([self.ttf],target,book,report)
        target.write_text(target.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'another target'):
            create_book([self.ttf],target,self.root/'stale',report)
        self.assertFalse((self.root/'stale').exists())

    def test_declared_unknown_metric_is_incomplete(self):
        font = TTFont(self.ttf)
        for table in font['cmap'].tables:
            table.cmap.pop(72,None)
        noH = self.root/'noH.ttf'
        font.save(noH)
        self.assertIsNone(font_measurements(FontData(noH))['xh'])
        target = self.write('targets.json',{'schema_version':1,'coverage':{'characters':'n'},'metrics':{'xh':{'value':500,'tolerance':5}}})
        run = subprocess.run([sys.executable,str(Path(__file__).with_name('check_font.py')),str(noH),'--targets',str(target),
                              '--out',str(self.root/'incomplete.json')],capture_output=True,text=True)
        self.assertEqual(run.returncode,2,run.stdout+run.stderr)
        self.assertEqual(json.loads((self.root/'incomplete.json').read_text())['status'],'incomplete')


if __name__ == '__main__':
    unittest.main()
