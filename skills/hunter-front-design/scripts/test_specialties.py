"""Small negative and compatibility tests; the real-font lab supplies format integration tests."""
import json
from pathlib import Path
import tempfile
import unittest

from font_common import FontData
from test_font_tools import fixture
from check_specialties import check_plan
from check_source import audit_ufo
from package_project import digest, package
from build_specialty_samples import original_cjk
from fetch_specialty_samples import fetch_sources
from retire_font_artifacts import retire
from render_small_text import render


class SpecialtyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.font=self.root/'fixture.ttf'; fixture(self.font)

    def test_shape_legacy_and_direction(self):
        face=FontData(self.font)
        for text in ['AV To','iji']:
            old=face.shape(text); new=face.shape_run(text)
            self.assertEqual(old,[(g['gid'],g['x_advance'],g['y_advance'],g['x_offset'],g['y_offset']) for g in new['glyphs']])
        run=face.shape_run('AV',direction='rtl',script='Latn',language='en')
        self.assertEqual([g['cluster'] for g in run['glyphs']],[1,0])

    def test_bad_shape_options_fail_closed(self):
        face=FontData(self.font)
        for options in [{'direction':'sideways'},{'script':'Latin'},{'language':'en;script'},
                        {'variations':{'wght':500}},{'features':{'kern':float('nan')}},{'features':{'kern':-1}}]:
            with self.subTest(options=options), self.assertRaises(ValueError): face.shape_run('AV',**options)

    def test_missing_glyph_and_unknown_kind(self):
        plan=self.root/'plan.json'
        plan.write_text(json.dumps({'schema_version':1,'cases':[
            {'id':'missing','kind':'shape','font':'fixture.ttf','text':'中文'}, {'id':'unknown','kind':'unsupported'}]}))
        report=check_plan(plan)
        self.assertEqual(report['status'],'fail'); self.assertEqual([r['state'] for r in report['checks']],['FAIL','FAIL'])
        self.assertEqual(report['input_sha256'][str(self.font.resolve())],digest(self.font))

    def test_component_dependencies_and_failure(self):
        font=original_cjk(); report=audit_ufo(font)
        self.assertFalse(report['errors']); self.assertEqual(set(report['direct_dependents']['uni6728']),{'uni6797','uni68EE'})
        font['uni6728'].getPen().addComponent('missing',(1,0,0,1,0,0))
        self.assertTrue(audit_ufo(font)['errors'])
        font=original_cjk(); font['uni6728'].getPen().addComponent('uni6797',(1,0,0,1,0,0))
        self.assertTrue(audit_ufo(font)['errors'])

    def test_package_stale_and_pending_gate(self):
        for name in ['source.txt','license.txt','proof.html']: (self.root/name).write_text('test fixture')
        files=[{'path':name,'sha256':digest(self.root/name),'role':role} for name,role in
               [('fixture.ttf','font'),('source.txt','source'),('license.txt','license'),('proof.html','proof')]]
        plan={'release':False,'files':files,'gates':[{'id':'optical','required':True,'state':'pending','reason':'human review not run'}]}
        path=self.root/'delivery.json'; path.write_text(json.dumps(plan))
        result=package(path,self.root/'draft.zip'); self.assertFalse(result['release']); self.assertEqual(result['pending_required'],['optical'])
        plan['release']=True; path.write_text(json.dumps(plan))
        with self.assertRaises(ValueError): package(path,self.root/'release.zip')
        self.assertFalse((self.root/'release.zip').exists())
        plan['release']=False; (self.root/'source.txt').write_text('changed'); path.write_text(json.dumps(plan))
        with self.assertRaises(ValueError): package(path,self.root/'stale.zip')

    def test_release_gate_subjects_and_zip(self):
        import zipfile
        for name in ['source.txt','license.txt','proof.html','review.json']: (self.root/name).write_text('reviewed fixture')
        files=[{'path':name,'sha256':digest(self.root/name),'role':role} for name,role in
               [('fixture.ttf','font'),('source.txt','source'),('license.txt','license'),('proof.html','proof'),('review.json','report')]]
        plan={'release':True,'files':files,'gates':[{'id':'review','required':True,'state':'pass','reason':'fixture review',
              'evidence':['review.json'],'subjects':{'fixture.ttf':digest(self.font)}}]}
        path=self.root/'release.json';path.write_text(json.dumps(plan));result=package(path,self.root/'release.zip')
        self.assertTrue(result['release'])
        with zipfile.ZipFile(self.root/'release.zip') as z: self.assertEqual(z.read('fixture.ttf'),self.font.read_bytes())
        plan['release']='false';path.write_text(json.dumps(plan))
        with self.assertRaises(ValueError): package(path,self.root/'wrong-boolean.zip')

    def test_source_registry_rejects_unknown_or_changed_cache(self):
        with self.assertRaises(ValueError): fetch_sources(self.root,ids=['not-a-font'])
        folder=self.root/'serif'; folder.mkdir(); (folder/'SourceSerif4[opsz,wght].ttf').write_bytes(b'bad')
        with self.assertRaises(ValueError): fetch_sources(self.root,ids=['serif'])

    def test_cleanup_dry_run_protection_and_recovery(self):
        path=self.root/'cleanup.json'
        plan={'authorization':'Only this temporary fixture font','preserve':[],'dependencies':[],
              'candidates':[{'path':'fixture.ttf','sha256':digest(self.font)}]}
        path.write_text(json.dumps(plan)); self.assertEqual(retire(path)['status'],'dry-run'); self.assertTrue(self.font.exists())
        plan['dependencies']=[str(self.font)]; path.write_text(json.dumps(plan))
        with self.assertRaises(ValueError): retire(path,self.root/'recovery')
        plan['dependencies']=[]; plan['preserve']=['fixture.ttf']; path.write_text(json.dumps(plan))
        with self.assertRaises(ValueError): retire(path,self.root/'recovery')
        plan['preserve']=[]; path.write_text(json.dumps(plan)); retire(path,self.root/'recovery')
        self.assertFalse(self.font.exists()); self.assertEqual(digest(self.root/'recovery/fixture.ttf'),plan['candidates'][0]['sha256'])

    def test_real_small_size_pixels(self):
        a,b=render(self.font,'Hnx AV',8),render(self.font,'Hnx AV',16)
        self.assertLess(a.getextrema()[0],255); self.assertGreater(b.width,a.width)


if __name__=='__main__': unittest.main()
