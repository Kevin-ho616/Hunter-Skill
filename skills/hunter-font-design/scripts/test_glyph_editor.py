"""Round-trip real font edits, preserving untouched glyphs, layout and source bytes."""
import copy
import hashlib
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import subprocess
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont, newTable

from glyph_editor import apply_edits, editable, read_glyph
from serve_editor import EditorHandler, blank_font, handoff
from test_font_tools import fixture


class GlyphEditorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make(self, cff=False):
        path = self.root / ('fixture.otf' if cff else 'fixture.ttf')
        fixture(path, cff)
        font = TTFont(path)
        for name_id in (0, 8, 9, 13, 14):
            font['name'].setName('Synthetic rights fixture ' + str(name_id), name_id, 3, 1, 1033)
        addOpenTypeFeaturesFromString(font, 'feature kern { pos c0041 c0056 -40; } kern; feature liga { sub c0066 c0069 by c0061; } liga;')
        font.save(path)
        return path.name, path.read_bytes()

    def draft(self, raw, filename, char='A'):
        data = read_glyph(raw, filename, char)
        return {'format': 'hunter-glyph-edits', 'version': 1,
                'baseSha256': hashlib.sha256(raw).hexdigest(), 'unitsPerEm': data['info']['unitsPerEm'],
                'glyphs': [data['glyph']]}

    def test_ttf_cff_and_web_containers_preserve_untouched_data(self):
        for cff, flavor in [(False, None), (True, None), (False, 'woff'), (True, 'woff2')]:
            with self.subTest(cff=cff, flavor=flavor):
                filename, raw = self.make(cff)
                if flavor:
                    font = TTFont(io.BytesIO(raw)); font.flavor = flavor
                    out = io.BytesIO(); font.save(out); raw = out.getvalue(); filename = 'fixture.' + flavor
                draft = self.draft(raw, filename)
                glyph = draft['glyphs'][0]
                glyph['contours'][0][1][1] += 20
                glyph['advanceWidth'] = 640
                result, report = apply_edits(raw, filename, draft)
                self.assertNotEqual(result, raw)
                self.assertEqual(report['baseSha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(read_glyph(result, filename, 'A')['glyph']['advanceWidth'], 640)
                a, b = TTFont(io.BytesIO(raw)), TTFont(io.BytesIO(result))
                self.assertEqual(a.getBestCmap(), b.getBestCmap())
                self.assertEqual(a['GPOS'].compile(a), b['GPOS'].compile(b))
                self.assertEqual(a['GSUB'].compile(a), b['GSUB'].compile(b))
                decorated = copy.deepcopy(draft); decorated.update(downloaded=True, lastExportReport=report, sourceFont={'filename':filename})
                self.assertEqual(apply_edits(raw, filename, decorated)[0], result, 'UI/save metadata must not change the exported font')
                self.assertEqual(a.flavor, b.flavor)
                for cp in range(33, 127):
                    if cp == 65:
                        continue
                    before, after = read_glyph(raw, filename, chr(cp)), read_glyph(result, filename, chr(cp))
                    self.assertEqual(before['glyph'], after['glyph'])
                for old in a['name'].names:
                    if old.nameID in (3, 5):
                        continue
                    self.assertEqual(old.string, b['name'].getName(old.nameID, old.platformID, old.platEncID, old.langID).string)

    def test_add_bmp_and_astral_glyphs_in_both_outlines(self):
        for cff in (False, True):
            filename, raw = self.make(cff)
            draft = self.draft(raw, filename, '永')
            glyph = draft['glyphs'][0]
            glyph['contours'] = [[['M', 50, 0], ['C', 50, 700, 500, 700, 500, 0], ['L', 50, 0], ['Z']]]
            extra = copy.deepcopy(glyph); extra['char'] = '\U0001F12F'; draft['glyphs'].append(extra)
            result, report = apply_edits(raw, filename, draft)
            font = TTFont(io.BytesIO(result))
            self.assertEqual(len(report['editedGlyphs']), 2)
            self.assertTrue({57, 59}.issubset(font['OS/2'].getUnicodeRanges()), 'New CJK and non-BMP coverage is reflected in OS/2')
            for char in ('永', '\U0001F12F'):
                self.assertIn(ord(char), font.getBestCmap())
                self.assertTrue(read_glyph(result, filename, char)['glyph']['contours'])

    def test_blank_font_to_drawn_font(self):
        raw = blank_font(); draft = self.draft(raw, 'blank.ttf')
        draft['glyphs'][0]['contours'] = [[['M', 50, 0], ['L', 300, 700], ['L', 550, 0], ['Z']]]
        result, _ = apply_edits(raw, 'blank.ttf', draft)
        data = read_glyph(result, 'blank.ttf', 'A')
        self.assertEqual(data['info']['codepoints'], [32, 65])
        self.assertEqual(data['glyph']['contours'][0][0], ['M', 50, 0])

    def test_composite_dependents_are_reported_and_recomputed(self):
        filename, raw = self.make()
        font = TTFont(io.BytesIO(raw)); pen = TTGlyphPen(font.getGlyphSet())
        pen.addComponent('c0041', (1, 0, 0, 1, 20, 30))
        font['glyf']['c0042'] = pen.glyph()
        target = io.BytesIO(); font.save(target); raw = target.getvalue()
        draft = self.draft(raw, filename)
        draft['glyphs'][0]['contours'][0][1][2] += 40
        result, report = apply_edits(raw, filename, draft)
        self.assertEqual(report['dependentGlyphs'], ['c0042'])
        self.assertNotEqual(read_glyph(raw, filename, 'B')['glyph']['contours'], read_glyph(result, filename, 'B')['glyph']['contours'])

    def test_invalid_drafts_and_unsupported_fonts_are_rejected(self):
        filename, raw = self.make(); draft = self.draft(raw, filename)
        mutations = [lambda d: d.update(baseSha256='0' * 64),
                     lambda d: d.update(unitsPerEm=2048),
                     lambda d: d['glyphs'][0].update(glyphName='c0042'),
                     lambda d: d['glyphs'][0]['contours'][0].pop(),
                     lambda d: d['glyphs'][0]['contours'][0][0].__setitem__(1, float('nan')),
                     lambda d: d['glyphs'][0].update(advanceWidth=65536),
                     lambda d: d['glyphs'].append(copy.deepcopy(d['glyphs'][0])),
                     lambda d: d['glyphs'][0].update(contours=[[[], ['Z']]])]
        for mutate in mutations:
            invalid = copy.deepcopy(draft); mutate(invalid)
            with self.assertRaises(ValueError):
                apply_edits(raw, filename, invalid)
        for tag in ('fvar', 'COLR', 'CFF2'):
            font = TTFont(io.BytesIO(raw)); font[tag] = newTable(tag)
            with self.assertRaises(ValueError):
                editable(font)

    def test_handoff_persists_exact_source_and_prepares_without_a_bound_chat(self):
        filename, raw = self.make(); draft = self.draft(raw, filename)
        draft['glyphs'][0]['contours'][0][1][1] += 25
        receipt = handoff(raw, filename, draft, '保留手改端头，再检查字距。', self.root)
        self.assertEqual(receipt['status'], 'prepared')
        folder = Path(receipt['bundlePath'])
        source = json.loads((folder / 'edits.json').read_text())
        self.assertEqual(source['glyphs'], draft['glyphs'])
        self.assertEqual((folder / 'base.ttf').read_bytes(), raw)
        self.assertEqual((folder / 'edited.ttf').read_bytes(), apply_edits(raw, filename, source)[0])
        self.assertIn('scale(1,-1)', (folder / 'U0041.svg').read_text())
        manifest = json.loads((folder / 'manifest.json').read_text())
        for name, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest)
        self.assertIn('保留手改端头', receipt['prompt'])

    def test_handoff_rejects_invalid_source_without_creating_a_package(self):
        filename, raw = self.make(); draft = self.draft(raw, filename)
        invalid = copy.deepcopy(draft); invalid['baseSha256'] = '0' * 64
        with self.assertRaises(ValueError):
            handoff(raw, filename, invalid, '', self.root)
        self.assertFalse((self.root / 'codex-handoffs').exists())
        with self.assertRaises(ValueError):
            handoff(raw, filename, draft, 'x' * 4001, self.root)
        self.assertFalse((self.root / 'codex-handoffs').exists())
        receipt = handoff(raw, filename, draft, '', self.root)
        self.assertIn('暂不进行新的造型修改或扩字', receipt['prompt'])

    def test_handoff_queues_only_to_bound_chat_without_resuming_a_second_writer(self):
        filename, raw = self.make(); draft = self.draft(raw, filename)
        thread_id = '00000000-0000-4000-8000-000000000001'
        queue_id = '00000000-0000-4000-8000-000000000003'
        with patch('serve_editor.subprocess.run', return_value=subprocess.CompletedProcess([], 0, f'Queued message {queue_id} for thread {thread_id}.', '')) as send:
            receipt = handoff(raw, filename, draft, '保留手改节点', self.root, thread_id, '/installed/codex')
        self.assertEqual(receipt['status'], 'queued')
        self.assertEqual(receipt['queuedSubmissionId'], queue_id)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.args[0], ['/installed/codex', 'queue', '--thread', thread_id, '--message', receipt['prompt']])
        self.assertNotIn('--resume', send.call_args.args[0])
        for outcome, expected in [(subprocess.CompletedProcess([], 1, '', 'Connection failed'), 'failed'),
                                  (subprocess.TimeoutExpired('codex', 30), 'unknown')]:
            with patch('serve_editor.subprocess.run') as send:
                if isinstance(outcome, Exception):send.side_effect = outcome
                else:send.return_value = outcome
                result = handoff(raw, filename, draft, '', self.root, thread_id, '/installed/codex')
            self.assertEqual(result['status'], expected)
            self.assertTrue(Path(result['bundlePath'], 'edits.json').is_file())

    def test_local_api_rejects_other_origins_and_symlink_escape(self):
        (self.root / 'index.html').write_text('editor')
        (self.root / 'outside').symlink_to('/etc/hosts')
        server = ThreadingHTTPServer(('127.0.0.1', 0), lambda *a, **kw: EditorHandler(*a, directory=str(self.root), **kw))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        url = f'http://127.0.0.1:{server.server_port}'
        urlopen = build_opener(ProxyHandler({})).open
        for path, headers in [('/api/editor', {'Origin': 'https://example.com'}), ('/outside', {})]:
            with self.assertRaises(HTTPError) as context:
                urlopen(Request(url + path, headers=headers))
            self.assertEqual(context.exception.code, 403)
        req = Request(url + '/api/new-font', data=b'{}', headers={'Content-Type':'application/json', 'X-Hunter-Editor':'2'})
        with urlopen(req) as response:
            self.assertIn('font', json.load(response))
        import base64
        filename, raw = self.make()
        body = {'font': base64.b64encode(raw).decode(), 'filename': filename, 'draft': self.draft(raw, filename),
                'instruction': 'HTTP 接续包验证', 'threadId': '00000000-0000-4000-8000-000000000002'}
        req = Request(url + '/api/handoff', data=json.dumps(body).encode(),
                      headers={'Content-Type':'application/json', 'X-Hunter-Editor':'2'})
        with urlopen(req) as response:
            receipt = json.load(response)
        self.assertEqual(receipt['status'], 'prepared', 'The body cannot choose a conversation')
        self.assertNotIn('threadId', json.loads(Path(receipt['bundlePath'], 'manifest.json').read_text()))
        server.handoff_thread_id = '00000000-0000-4000-8000-000000000001'
        server.codex_binary = '/installed/codex'
        with patch('serve_editor.subprocess.run') as send:
            with urlopen(req) as response:legacy = json.load(response)
        self.assertEqual(legacy['status'], 'prepared')
        send.assert_not_called()
        direct = Request(url + '/api/handoff/send', data=json.dumps(body).encode(),
                         headers={'Content-Type':'application/json', 'X-Hunter-Editor':'2'})
        with patch('serve_editor.subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'Queued', '')) as send:
            with urlopen(direct) as response:receipt = json.load(response)
        self.assertEqual(receipt['threadId'], server.handoff_thread_id)
        self.assertNotIn(body['threadId'], send.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
