"""Run the specialist sample lab. Results demonstrate tools, not professional design approval."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from fontTools.ttLib import TTFont
from font_common import FontData, save_json
from check_source import check_source
from check_specialties import check_plan
from fetch_specialty_samples import fetch_sources
from render_small_text import sheet


def validate(sources, samples, output):
    fetch_sources(sources)
    output.mkdir(parents=True,exist_ok=False)
    registry=json.loads((Path(__file__).resolve().parents[1]/'assets/specialty-sources.json').read_text())['sources']
    original={s['id']:str(sources/s['id']/s['font']['file']) for s in registry}
    fonts=samples/'fonts'; cases=[]
    def add(id, kind, **options): cases.append(dict(id=id,kind=kind,**options))
    def font(name): return str(fonts/name)
    add('family-ribbi','family',styles=[{'font':font('Skill Lab Serif-'+style+'.ttf'),'style':style,'weight':weight,'italic':italic}
        for style,weight,italic in [('Regular',400,False),('Bold',700,False),('Italic',400,True),('Bold Italic',700,True)]])
    add('rebuilt-ligature','shape',font=font('Skill Lab Serif-Regular.ttf'),text='office',features={'liga':1},compare={'features':{'liga':0}})
    add('rebuilt-kerning','shape',font=font('Skill Lab Serif-Regular.ttf'),text='AV To',features={'kern':1},compare={'features':{'kern':0}})
    add('serbian-locl','shape',font=original['serif-italic'],text='бгдпт',language='sr',script='Cyrl',direction='ltr',compare={'language':'ru'})
    add('canonical-equivalence','shape',font=original['serif'],text='ö',compare_text='o\u0308',compare={},must_change=False)
    add('stacked-mark','shape',font=original['serif'],text='n\u0301\u0308',zero_advance_mark=True)
    for key,text,lang,script,direction in [('arabic','السَّلَامُ عَلَيْكُمْ','ar','Arab','rtl'),
            ('devanagari','हिन्दी क्षि कर्म','hi','Deva','ltr'),('thai','ภาษาไทย น้ำ กิ้','th','Thai','ltr')]:
        add(key+'-shape','shape',font=font(key+'.ttf'),text=text,language=lang,script=script,direction=direction)
        add(key+'-subset','subset',font=font(key+'.ttf'),original=original[key],characters=text,
            runs=[{'text':text,'language':lang,'script':script,'direction':direction}])
    vertical='中文（）「」一二三。'
    add('vertical-replacement','shape',font=font('cjk.otf'),text=vertical,language='zh-Hans',script='Hani',direction='ttb',
        features={'vert':1,'vrt2':1},compare={'features':{'vert':0,'vrt2':0}})
    add('vertical-subset','subset',font=font('cjk.woff2'),original=original['cjk'],characters=vertical,
        runs=[{'text':vertical,'direction':'ttb','script':'Hani','language':'zh-Hans'}])
    for name in ['Roman-VF.ttf','Italic-VF.ttf']:
        add('rebuilt-'+name,'variable',font=font(name),text='AV To office aji',must_vary=True)
    add('multi-axis-optical','variable',font=original['serif'],text='AV To office n\u0301',must_vary=True)
    add('multi-axis-width','variable',font=original['mono'],text='H0il1{}[]',must_vary=True)
    for name,tables in [('colr0',['COLR','CPAL']),('colr1',['COLR','CPAL']),('emoji',['COLR','CPAL']),('bitmap',['sbix'])]:
        add(name,'color',font=font(name+'.ttf'),tables=tables,runs=[{'text':'😀👩‍💻❤️' if name=='emoji' else 'AB'}])
    add('emoji-zwj','shape',font=font('emoji.ttf'),text='👩‍💻',max_glyphs=1)
    add('math-stretch','math',font=original['math'],stretch='()√')
    add('monospace','mono',font=font('mono.woff2'),characters=''.join(map(chr,range(32,127))),texts=['if (a == 1) {','  return x + 0;','}'])
    add('smufl-metadata','smufl',font=original['music'],metadata=str(sources/'music/Bravura.json'),
        glyphs={'gClef':0xe050,'noteheadBlack':0xe0a4,'accidentalSharp':0xe262})
    plan=output/'specialty-plan.json'; save_json(plan,{'schema_version':1,'cases':cases})
    report=check_plan(plan); save_json(output/'specialty-checks.json',report)
    sources_report={}
    for name in ['Roman.designspace','Italic.designspace','OriginalCJK.ufo','OriginalCJK.glyphs']:
        sources_report[name]=check_source(samples/'masters'/name)
    save_json(output/'source-checks.json',sources_report)
    # Exercise a source change through shared components without touching the built fixture.
    from build_specialty_samples import original_cjk
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    a,b=original_cjk(80),original_cjk(88)
    changes={}
    for char in '木林森口':
        name='uni%04X'%ord(char); pa,pb=DecomposingRecordingPen(a),DecomposingRecordingPen(b)
        a[name].draw(pa); b[name].draw(pb); changes[char]=pa.value!=pb.value
    # 口 also uses the global stroke; changing just 木 is the component dependency test.
    b=original_cjk(80); b['uni6728'].clearContours()
    b['uni6728'].copyDataFromGlyph(original_cjk(88)['uni6728'])
    local_changes={}
    for char in '木林森口':
        name='uni%04X'%ord(char); pa,pb=DecomposingRecordingPen(a),DecomposingRecordingPen(b)
        a[name].draw(pa); b[name].draw(pb); local_changes[char]=pa.value!=pb.value
    assert local_changes=={'木':True,'林':True,'森':True,'口':False}, local_changes
    save_json(output/'component-regression.json',{'global_stroke':changes,'wood_only':local_changes})
    commands=[]
    def run(label,args):
        result=subprocess.run(args,capture_output=True,text=True)
        (output/(label+'.log')).write_text(result.stdout+'\n'+result.stderr)
        commands.append({'id':label,'command':list(map(str,args)),'exit_code':result.returncode})
        return result
    hint=samples/'unhinted/Skill Lab Serif-Regular.ttf'; hinted=output/'hinted.ttf'
    result=run('ttfautohint',[sys.executable,'-m','ttfautohint',str(hint),str(hinted)])
    if result.returncode==0:
        hf=TTFont(hinted); hf['head'].flags |= 1<<3; hf.save(hinted)
        before=FontData(hint); after=FontData(hinted)
        assert all(t in hf for t in ['fpgm','prep','cvt '])
        assert any(getattr(hf['glyf'][n],'program',None) and hf['glyf'][n].program.getBytecode() for n in hf.getGlyphOrder())
        assert before.shape_run('AV To office')['glyphs']==after.shape_run('AV To office')['glyphs']
        from check_specialties import outline
        assert all(outline(before,gid)==outline(after,gid) for gid in range(len(before.font.getGlyphOrder())))
        sheet(hint,hinted,output/'hinting-pixels.png')
    for index,path in enumerate([fonts/'Skill Lab Serif-Regular.ttf',fonts/'Skill Lab Serif-Regular.otf',fonts/'Roman-VF.ttf',
                                fonts/'cjk.otf',fonts/'arabic.woff2',fonts/'colr0.ttf',fonts/'colr1.ttf',fonts/'emoji.ttf',fonts/'bitmap.ttf']):
        run('ots-'+str(index),[sys.executable,'-m','ots',str(path),str(output/('sanitized-'+str(index)+'.sfnt'))])
    broken=output/'negative-truncated.ttf'; broken.write_bytes(hint.read_bytes()[:48])
    bad=run('ots-negative',[sys.executable,'-m','ots',str(broken),str(output/'should-not-exist.sfnt')])
    assert bad.returncode!=0, 'OTS accepted deliberately truncated data.'
    family=[str(p) for p in fonts.glob('Skill Lab Serif-*.ttf')]
    run('fontbakery',[sys.executable,'-m','fontbakery','check-universal',*family,'--skip-network','--json',str(output/'fontbakery.json'),'-J','1'])
    import verovio
    toolkit=verovio.toolkit(); toolkit.setOptions({'font':'Bravura','pageWidth':1600,'pageHeight':600,'adjustPageHeight':True})
    mei='''<mei xmlns="http://www.music-encoding.org/ns/mei" meiversion="5.0"><meiHead><fileDesc><titleStmt><title>Skill Lab</title></titleStmt><pubStmt/></fileDesc></meiHead><music><body><mdiv><score><scoreDef meter.count="4" meter.unit="4"><staffGrp><staffDef n="1" lines="5" clef.shape="G" clef.line="2"/></staffGrp></scoreDef><section><measure n="1"><staff n="1"><layer n="1"><note pname="c" oct="4" dur="4"/><note pname="d" oct="4" dur="4"/><note pname="e" oct="4" dur="4"/><note pname="f" oct="4" dur="4"/></layer></staff></measure></section></score></mdiv></body></music></mei>'''
    assert toolkit.loadData(mei); svg=toolkit.renderToSVG(1)
    assert '<svg' in svg and 'note' in svg
    (output/'score.mei').write_text(mei); (output/'score.svg').write_text(svg)
    save_json(output/'tool-runs.json',commands)
    save_json(output/'music-engine.json',{'engine':'Verovio','version':toolkit.getVersion(),'font':'Bravura',
              'scope':'Verovio bundled Bravura engraving data. Downloaded Bravura binary/metadata checked separately.'})
    make_gallery(original,fonts,hinted,output)
    tools_ok=all(c['exit_code']==(1 if c['id']=='ots-negative' else 0) for c in commands)
    summary={'specialty_status':report['status'],'tools_pass':tools_ok,'cases':len(cases),'source_status':{k:v['status'] for k,v in sources_report.items()},
             'commands':commands,'untested':['human language and optical approval','Windows/device/physical print acceptance'],
             'scope':'tool lab, not a font release certificate'}
    save_json(output/'summary.json',summary)
    print(json.dumps({'specialties':report['status'],'out':str(output)},ensure_ascii=False))
    return tools_ok and report['status']=='pass' and all(v['status']=='pass' for v in sources_report.values())


def make_gallery(original,fonts,hinted,out):
    target=out/'gallery'; target.mkdir(); (target/'fonts').mkdir()
    specimens=[('serif',fonts/'Skill Lab Serif-Regular.ttf','AV To office aji. Read a paragraph at actual sizes.','en','ltr'),
        ('italic',fonts/'Skill Lab Serif-Italic.ttf','SaijiH fT VA; curves, serif joins, hanging terminals.','en','ltr'),
        ('script',fonts/'script.ttf','Dancing voices: office AV To aji','en','ltr'),
        ('locl',Path(original['serif-italic']),'бгдпт','sr','ltr'),
        ('arabic',fonts/'arabic.woff2','السَّلَامُ عَلَيْكُمْ','ar','rtl'),
        ('devanagari',fonts/'devanagari.ttf','हिन्दी क्षि कर्म','hi','ltr'),
        ('thai',fonts/'thai.ttf','ภาษาไทย น้ำ กิ้','th','ltr'),
        ('cjk',fonts/'cjk.woff2','中文测试，天地（）「」一二三。123','zh-Hans','ltr'),
        ('original',fonts/'OriginalCJK.ttf','一十口日田中人大小木林森','zh-Hans','ltr'),
        ('mono',fonts/'mono.woff2','if (a == 1) { return x + 0; }','en','ltr'),
        ('variable',fonts/'Roman-VF.ttf','AV To office aji','en','ltr'),
        ('colr0',fonts/'colr0.ttf','AB','en','ltr'),('colr1',fonts/'colr1.ttf','AB','en','ltr'),
        ('emoji',fonts/'emoji.ttf','😀👩‍💻❤️','und','ltr'),('bitmap',fonts/'bitmap.ttf','AB','en','ltr'),
        ('hinted',hinted,'Minimum reading size: Hnx 01 il aji.','en','ltr')]
    styles=[]; blocks=[]; manifest=[]
    import html
    for id,path,text,lang,direction in specimens:
        name=id+path.suffix; shutil.copyfile(path,target/'fonts'/name)
        weight='font-weight:200 900;' if id=='variable' else ''
        styles.append(f'@font-face{{font-family:LabFont-{id};{weight}src:url("fonts/{name}")}}')
        blocks.append(f'<section><h2>{id}</h2><p id="{id}" lang="{lang}" dir="{direction}" style="font-family:LabFont-{id}">{html.escape(text)}</p></section>')
        manifest.append({'id':id,'url':'fonts/'+name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'text':text})
    shutil.copyfile(original['math'],target/'fonts/math.ttf')
    styles.append('@font-face{font-family:mathlab;src:url("fonts/math.ttf")} math{font-family:mathlab;font-size:44px}')
    blocks.append('''<section><h2>MATH</h2><math id="math" display="block"><mrow><mo>(</mo><mfrac><msqrt><mrow><mi>x</mi><mo>+</mo><mn>1</mn></mrow></msqrt><mrow><munderover><mo>∑</mo><mi>i</mi><mi>n</mi></munderover><msup><mi>x</mi><mn>2</mn></msup></mrow></mfrac><mo>)</mo></mrow></math></section>''')
    blocks.append('<section><h2>Vertical</h2><p id="vertical" lang="zh-Hans" style="font-family:LabFont-cjk;writing-mode:vertical-rl;height:460px">中文（）「」一二三。</p></section><section><h2>Engraving</h2><img src="../score.svg" width="900" alt="Verovio Bravura four-note score"></section>')
    blocks.append('<section><h2>Body / reverse / hinting</h2>'+''.join(f'<p style="font-family:LabFont-serif;font-size:{size}px">At {size}px: AV To office aji, minimum reading size, 0123456789.</p>' for size in [8,10,12,14,16,24])+ '<p style="font-family:LabFont-serif;background:#111;color:white">Reverse: AV To office aji 0123456789</p></section>')
    (target/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Font specialist lab</title><style>body{max-width:1000px;margin:40px auto;padding:24px;font-family:system-ui}section{padding:20px 0;border-bottom:1px solid #ddd}h2{font-size:16px}p{font-size:44px;margin:8px 0;overflow-wrap:anywhere}#colr0,#colr1,#emoji{font-size:96px}#bitmap{font-size:32px}'+''.join(styles)+'</style><h1>字体专项工具测试样本</h1><p style="font:16px system-ui">Technical samples only. Language and optical approval remain separate.</p>'+''.join(blocks))
    save_json(target/'manifest.json',manifest)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('sources',type=Path); p.add_argument('samples',type=Path); p.add_argument('out',type=Path)
    a=p.parse_args(); raise SystemExit(not validate(a.sources.resolve(),a.samples.resolve(),a.out.resolve()))
