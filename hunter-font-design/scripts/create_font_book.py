#!/usr/bin/env python3
"""Create a versioned technical font book from real fonts and the declared project scope."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from font_common import FontData, font_measurements, load_targets, save_json

esc = lambda value: html.escape(str(value),quote=True)


def create_book(paths, target_path, output, report_path=None):
    targets,codes = load_targets(target_path)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('Use a fresh book directory; existing review evidence is preserved.')
    faces = [FontData(p) for p in paths]
    target_hash = hashlib.sha256(Path(target_path).read_bytes()).hexdigest()
    report = json.loads(Path(report_path).read_text()) if report_path else None
    if report:
        if report.get('kind') != 'font_validation' or report.get('targets_sha256') != target_hash:
            raise ValueError('Validation report belongs to another target file; re-run the check.')
        checked = {f['font'].get('sha256') for f in report['fonts']}
        if any(f.info['sha256'] not in checked for f in faces):
            raise ValueError('Validation report is stale for these font bytes.')
    references = []
    for name in targets.get('reference_measurements',[]):
        path = Path(target_path).resolve().parent/name
        data = json.loads(path.read_text())
        if data.get('kind') not in ('font_measurement','image_measurement'):
            raise ValueError(f'Not a measurement report: {path}')
        references.append(data)
    (output/'fonts').mkdir(parents=True)
    pages,css,metadata = [],[],[]

    def page(title,body,style):
        number = len(pages)+1
        pages.append(f'<section class="page" id="p{number:03}" data-title="{esc(title)}"><header>{esc(style)}<span>{number:02}</span></header><main><h1>{esc(title)}</h1>{body}</main></section>')

    def sample(text,index,size=64,extra=''):
        return f'<div class="sample" data-font="f{index}" style="font-family:f{index};font-size:{size}px;{extra}" data-fit="shrink">{esc(text)}</div>'

    for index,face in enumerate(faces):
        info = face.info
        filename = info['sha256'][:16]+face.path.suffix.lower()
        shutil.copy2(face.path,output/'fonts'/filename)
        css.append(f'@font-face{{font-family:f{index};src:url("fonts/{filename}");font-weight:normal;font-style:normal}}')
        missing = [cp for cp in codes if cp not in face.cmap]
        samples = targets.get('shaping',{}).get('samples',[])
        hero = next((s.splitlines()[0] for s in samples if s.strip()), ''.join(chr(cp) for cp in codes if chr(cp).isprintable())[:24])
        name = f'{info["family"]} / {info["style"]}'
        status = report['status'] if report else 'not run'
        facts = [('Version',info['version']),('Glyphs',info['glyphCount']),('Encoded codepoints',len(face.cmap)),
                 ('Requested codepoints',len(codes)),('Missing',len(missing)),('Engineering checks',status),
                 ('Units per em',face.upm),('Outline / container',f'{info["outline"]} / {info["container"]}'),('SHA-256',info['sha256'])]
        body = sample(hero,index,168) + '<table>'+''.join(f'<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>' for k,v in facts)+'</table>'
        body += '<p class="note">Actual font rendering. Engineering results do not certify optical approval, installation or native application compatibility.</p>'
        page(name,body,name)
        measures = font_measurements(face)
        body = '<p>Lengths below are normalised to cap height 700; contrast is a ratio. These are measurements, not new design rules.</p><table><tr><th>Metric</th><th>Actual</th><th>Target</th><th>Tolerance</th></tr>'
        for key,value in measures.items():
            spec = targets.get('metrics',{}).get(key,{})
            body += f'<tr><th>{esc(key)}</th><td>{esc(value if value is not None else "unknown")}</td><td>{esc(spec.get("value","not specified"))}</td><td>{esc(spec.get("tolerance","—"))}</td></tr>'
        body += '</table>'
        if references:
            summaries = [f'{Path(r["source"]["path"]).name}: '+', '.join(f'{k} {v["value"]} ({v["confidence"]})' for k,v in r['metrics'].items() if k in ('xh','n_stem','contrast')) for r in references]
            body += '<p class="note">Reference evidence: '+esc('; '.join(summaries))+'</p>'
        page('Measured proportions',body,name)
        body = ''
        for size in (96,72,48,36,24,18,12):
            body += f'<div class="waterfall"><span>{size} px</span><div data-font="f{index}" data-fit="clip-text" style="font-family:f{index};font-size:{size}px">{esc(hero)}</div></div>'
        page('Size waterfall',body+'<p class="note">Long lines are shortened to the page width; the labelled font size is preserved.</p>',name)
        for offset in range(0,len(codes),192):
            cells = []
            for cp in codes[offset:offset+192]:
                char = chr(cp)
                if cp not in face.cmap:
                    ink = '<span class="missing">missing</span>'
                elif char.isspace() or not char.isprintable():
                    ink = '<span class="note">space / control</span>'
                else:
                    ink = f'<span data-font="f{index}" style="font-family:f{index}" class="glyph">{esc(char)}</span>'
                cells.append(f'<div class="cell">{ink}<small>U+{cp:04X}</small></div>')
            page(f'Character scope {offset//192+1}',f'<p>{len(codes)} explicitly requested codepoints; this is not the entire Unicode repertoire.</p><div class="grid">'+''.join(cells)+'</div>',name)
        pairs = targets.get('shaping',{}).get('pairs',[])
        for offset in range(0,len(pairs),8):
            body = '<div class="pairs">'
            for pair in pairs[offset:offset+8]:
                body += f'<div class="pair"><span>{esc(pair)}</span>{sample(pair,index,54,"font-kerning:none")}{sample(pair,index,54,"font-kerning:normal")}</div>'
            page('Kerning off / on',body+'</div><p class="note">Grey labels identify the pair; columns render kerning off and on. Optical spacing review is still required.</p>',name)
        tags = info['features']
        tests = targets.get('shaping',{}).get('features',[])
        for offset in range(0,max(1,len(tests)),3):
            body = '<p>Tags read from the actual GSUB/GPOS tables. Presence alone does not demonstrate the feature.</p><p class="tags">'+esc(' · '.join(tags) or 'No declared features')+'</p>'
            for test in tests[offset:offset+3]:
                tag,text = test['tag'],test['text']
                body += f'<p>{esc(tag)} off / on</p>'+sample(text,index,38,f"font-feature-settings:'{tag}' 0")+sample(text,index,38,f"font-feature-settings:'{tag}' 1")
            page('OpenType and validation',body+f'<p>Engineering report: {esc(status)}. Language support is not inferred from the presence of a few script characters.</p>',name)
        metadata.append({**info,'book_file':'fonts/'+filename,'alias':f'f{index}','missing_codepoints':missing})
    styles = '''
*{box-sizing:border-box}body{margin:0;background:#ececec;color:#171717;font:18px Arial,sans-serif}.page{width:1600px;height:1000px;background:white;margin:24px auto;position:relative;overflow:hidden;break-after:page}header{position:absolute;left:64px;right:64px;top:28px;color:#777;font-size:16px}header span{float:right}main{position:absolute;left:64px;right:64px;top:86px;bottom:48px}h1{font-size:38px;line-height:1.15;margin:0 0 24px}p{line-height:1.45}.sample{white-space:nowrap;line-height:1.22;margin:12px 0;max-width:100%}table{width:100%;border-collapse:collapse;font-size:17px;table-layout:fixed}th,td{text-align:left;border-bottom:1px solid #ddd;padding:9px 12px;overflow-wrap:anywhere}th{font-weight:normal;color:#666}.note{font-size:14px;color:#666}.waterfall{display:grid;grid-template-columns:90px 1fr;align-items:baseline;margin:12px 0;gap:24px}.waterfall>div{white-space:nowrap;line-height:1.2;min-width:0}.waterfall>span{font-size:14px;color:#777}.grid{display:grid;grid-template-columns:repeat(16,minmax(0,1fr));border-left:1px solid #ddd;border-top:1px solid #ddd}.cell{height:58px;border-right:1px solid #ddd;border-bottom:1px solid #ddd;display:flex;align-items:center;justify-content:center;flex-direction:column}.glyph{font-size:32px;line-height:1.1}.cell small{font-size:9px;color:#888}.missing{color:#b00020;font-size:14px}.pairs{display:grid;gap:8px}.pair{display:grid;grid-template-columns:80px 1fr 1fr;gap:28px;align-items:center;border-bottom:1px solid #ddd;height:82px}.pair .sample{margin:0}.pair>span{font-size:16px;color:#777}.tags{line-height:2;overflow-wrap:anywhere}@page{size:1600px 1000px;margin:0}@media print{body{background:white}.page{margin:0}}
'''
    document = '<!doctype html><meta charset="utf-8"><title>Technical font book</title><style>'+''.join(css)+styles+'</style>'+''.join(pages)
    (output/'index.html').write_text(document,encoding='utf-8')
    save_json(output/'book-info.json',{'schema_version':1,'kind':'font_book','targets_sha256':target_hash,
              'fonts':metadata,'pages':len(pages),'validation_status':report['status'] if report else 'not run',
              'missing_codepoints':sum(len(f['missing_codepoints']) for f in metadata),
              'scope':'Declared encoded characters; unencoded alternates and full optical review remain separate.'})
    return {'html':str(output/'index.html'),'pages':len(pages),'pdf':'not rendered; run render_font_book.cjs'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fonts',nargs='+',type=Path)
    parser.add_argument('--targets',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--report',type=Path)
    args = parser.parse_args()
    print(json.dumps(create_book(args.fonts,args.targets,args.out,args.report),ensure_ascii=False))


if __name__ == '__main__':
    main()
