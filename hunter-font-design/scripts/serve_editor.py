#!/usr/bin/env python3
"""Serve a proof directory and a local-only, in-memory font editing API."""
import argparse
import base64
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import parse_qs, urlsplit
import uuid
import webbrowser

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen

from glyph_editor import apply_edits, read_glyph, draw
from create_proof import inspect_font


def blank_font():
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    import io
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(['.notdef', 'space'])
    builder.setupCharacterMap({32: 'space'})
    pen = TTGlyphPen(None)
    pen.moveTo((50, 0))
    for p in [(50, 700), (550, 700), (550, 0)]:
        pen.lineTo(p)
    pen.closePath()
    builder.setupGlyf({'.notdef': pen.glyph(), 'space': TTGlyphPen(None).glyph()})
    builder.setupHorizontalMetrics({'.notdef': (600, 50), 'space': (300, 0)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({'familyName': 'Hunter Draw Draft', 'styleName': 'Regular',
                           'uniqueFontIdentifier': 'HunterDrawDraft-1.0',
                           'fullName': 'Hunter Draw Draft Regular', 'psName': 'HunterDrawDraft-Regular',
                           'version': 'Version 1.000; Drawing draft'})
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=850,
                    usWinDescent=250, sCapHeight=700, sxHeight=500)
    builder.setupPost()
    builder.setupMaxp()
    result = io.BytesIO()
    builder.font.save(result)
    return result.getvalue()


def handoff(raw, filename, draft, instruction, directory, thread_id=None, codex_binary=None):
    if not isinstance(instruction, str) or len(instruction) > 4000:
        raise ValueError('后续要求须为 4000 字以内的文字。')
    edited, report = apply_edits(raw, filename, draft)
    source = {key: draft[key] for key in ('format', 'version', 'baseSha256', 'unitsPerEm', 'glyphs')}
    source['sourceFont'] = {'filename': Path(filename).name, 'data': base64.b64encode(raw).decode()}
    source_json = json.dumps(source, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    parent = Path(directory).resolve() / 'codex-handoffs'
    if parent.is_symlink():
        raise ValueError('接续包目录不能是符号链接。')
    parent.mkdir(exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='return-', dir=parent))
    suffix = Path(filename).suffix.lower()
    (folder / ('base' + suffix)).write_bytes(raw)
    (folder / ('edited' + suffix)).write_bytes(edited)
    (folder / 'edits.json').write_text(source_json, encoding='utf-8')
    for glyph in source['glyphs']:
        pen, bounds = SVGPathPen(None), BoundsPen(None)
        draw(glyph, pen)
        draw(glyph, bounds)
        box = bounds.bounds or (0, 0, 0, 0)
        upm = source['unitsPerEm']
        left, right = min(0, box[0]) - upm * .1, max(upm, glyph['advanceWidth'], box[2]) + upm * .1
        bottom, top = min(-upm * .25, box[1]) - upm * .1, max(upm * .9, box[3]) + upm * .1
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left} {-top} {right-left} {top-bottom}"><path transform="scale(1,-1)" fill-rule="nonzero" d="{pen.getCommands()}"/></svg>\n'
        (folder / f'U{ord(glyph["char"]):04X}.svg').write_text(svg, encoding='utf-8')
    chars = '、'.join(glyph['char'] for glyph in source['glyphs'])
    request = instruction.strip() or '请先核验并确认收到这些手改字形，等待我说明下一步要求，暂不进行新的造型修改或扩字。'
    prompt = (f'【字体编辑器手改回传】字形：{chars}\n接续包：{folder}\n'
              f'请先读取 {folder / "edits.json"} 与 {folder / "manifest.json"}，核对原字体和修改文件哈希；'
              '以真实节点和手改结果作为本轮输入，不从截图重新描字。原字体、修改后字体及逐字 SVG 均在接续包中。\n'
              f'用户填写的后续要求：\n{request}')
    (folder / 'request.md').write_text(prompt + '\n', encoding='utf-8')
    manifest = {'version': 1, 'characters': [g['char'] for g in source['glyphs']],
                'baseSha256': report['baseSha256'], 'editedSha256': report['sha256'],
                'sourceOfGeometry': 'manual editor outline data', 'instruction': instruction,
                'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir())},
                'fontReport': report}
    (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    receipt = {'status': 'prepared', 'bundlePath': str(folder), 'prompt': prompt,
               'detail': '接续包已保存，但未绑定对话或未找到本机 Codex 命令。'}
    if thread_id and codex_binary:
        try:
            # Queue to the desktop owner; --resume would compete with its active writer.
            result = subprocess.run([codex_binary, 'queue', '--thread', thread_id, '--message', prompt],
                                    capture_output=True, text=True, timeout=30, cwd=directory)
            receipt['status'] = 'queued' if result.returncode == 0 else 'failed'
            receipt['detail'] = (result.stdout + '\n' + result.stderr).strip()[-2000:]
            match = re.search(r'Queued message ([0-9a-f-]{36})', result.stdout)
            receipt['queuedSubmissionId'] = match.group(1) if match else None
            receipt['threadId'] = thread_id
        except subprocess.TimeoutExpired:
            receipt.update(status='unknown', detail='发送结果未确认。请先查看当前对话，避免重复发送。')
        except OSError as error:
            receipt.update(status='failed', detail=str(error))
    (folder / 'delivery.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return receipt


class EditorHandler(SimpleHTTPRequestHandler):
    def allowed(self, mutation=False):
        expected = f'127.0.0.1:{self.server.server_port}'
        return (self.headers.get('Host') == expected
                and self.headers.get('Origin', 'http://' + expected) == 'http://' + expected
                and (not mutation or self.headers.get('X-Hunter-Editor') == '2'))

    def json(self, status, data):
        raw = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if not self.allowed():
            self.send_error(403)
            return
        if urlsplit(self.path).path == '/api/editor':
            self.json(200, {'version': 2})
        elif urlsplit(self.path).path.startswith('/api/'):
            self.send_error(404)
        else:
            target = Path(self.translate_path(self.path)).resolve()
            if not target.is_relative_to(Path(self.directory).resolve()):
                self.send_error(403)
                return
            super().do_GET()

    def list_directory(self, path):
        self.send_error(403)

    def do_POST(self):
        if not self.allowed(mutation=True):
            self.send_error(403)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 64 * 1024 * 1024:
                raise ValueError('请求超出 64 MB 限制。')
            payload = self.rfile.read(length)
            route = urlsplit(self.path)
            query = parse_qs(route.query)
            if route.path == '/api/new-font':
                raw = blank_font()
                data = {'font': base64.b64encode(raw).decode(),
                        'info': inspect_font(Path('Hunter-Draw-Draft.ttf'), raw)}
            elif route.path == '/api/glyph':
                data = read_glyph(payload, query.get('filename', ['font.ttf'])[0], query.get('char', [''])[0])
            elif route.path == '/api/export':
                body = json.loads(payload)
                raw = base64.b64decode(body['font'], validate=True)
                result, report = apply_edits(raw, body['filename'], body['draft'])
                data = {'font': base64.b64encode(result).decode(), 'report': report}
            elif route.path in ('/api/handoff', '/api/handoff/send'):
                body = json.loads(payload)
                direct = route.path == '/api/handoff/send'
                data = handoff(base64.b64decode(body['font'], validate=True), body['filename'], body['draft'],
                               body.get('instruction', ''), self.directory,
                               getattr(self.server, 'handoff_thread_id', None) if direct else None,
                               getattr(self.server, 'codex_binary', None) if direct else None)
            else:
                self.send_error(404)
                return
            self.json(200, data)
        except Exception as error:
            self.json(400, {'error': str(error) or type(error).__name__})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not (directory / 'index.html').is_file():
        parser.error('A proof directory with index.html is required.')
    server = ThreadingHTTPServer(('127.0.0.1', args.port),
                                 lambda *a, **kw: EditorHandler(*a, directory=str(directory), **kw))
    target_path = directory / 'codex-target.json'
    target = json.loads(target_path.read_text(encoding='utf-8')) if target_path.is_file() else {}
    thread_id = target.get('threadId') or os.environ.get('CODEX_THREAD_ID')
    server.handoff_thread_id = str(uuid.UUID(thread_id)) if thread_id else None
    server.codex_binary = shutil.which('codex') or target.get('codexExecutable')
    url = f'http://127.0.0.1:{server.server_port}/'
    print(json.dumps({'url': url}), flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
