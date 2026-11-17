"""Render actual FreeType glyph pixels at declared ppem, preserving shaping conditions."""
import argparse
import hashlib
from pathlib import Path

import freetype
from PIL import Image, ImageDraw
from font_common import FontData, save_json


def render(font_path,text,size,hinting=True):
    data=FontData(font_path); run=data.shape_run(text)
    if any(not g['gid'] for g in run['glyphs']): raise ValueError('Small-size sample has missing glyphs.')
    if run['direction']!='ltr': raise ValueError('This horizontal pixel sheet expects an LTR sample; use the script-aware gallery for other directions.')
    face=freetype.Face(str(font_path)); face.set_pixel_sizes(0,size)
    image=Image.new('L',(max(1,round(run['advance'][0]*size/data.upm)+30),size*3),255)
    x=12
    for glyph in run['glyphs']:
        flags=freetype.FT_LOAD_RENDER | (0 if hinting else freetype.FT_LOAD_NO_HINTING)
        face.load_glyph(glyph['gid'],flags); slot=face.glyph; bitmap=slot.bitmap
        if bitmap.width and bitmap.rows:
            if bitmap.pixel_mode!=freetype.FT_PIXEL_MODE_GRAY: raise ValueError('Expected grayscale outline raster.')
            raw=bytes(bitmap.buffer); pitch=abs(bitmap.pitch)
            mask=Image.frombytes('L',(bitmap.width,bitmap.rows),b''.join(raw[i*pitch:i*pitch+bitmap.width] for i in range(bitmap.rows)))
            left=round(x+glyph['x_offset']*size/data.upm)+slot.bitmap_left
            top=size*2-slot.bitmap_top-round(glyph['y_offset']*size/data.upm)
            image.paste(0,(left,top),mask)
        x+=glyph['x_advance']*size/data.upm
    return image


def sheet(before,after,out,text='Hnx AV To office aji 01 il',sizes=(8,10,12,14,16,24)):
    out=Path(out)
    if out.exists() or out.with_suffix('.json').exists(): raise ValueError('Use a fresh raster path.')
    rows=[]; records=[]
    for size in sizes:
        a,b=render(before,text,size),render(after,text,size)
        row=Image.new('L',(max(a.width,b.width)+180,max(a.height,b.height)),255)
        ImageDraw.Draw(row).text((8,4),str(size)+' ppem / before | after',fill=0)
        row=Image.new('L',(row.width,row.height*2),255)
        ImageDraw.Draw(row).text((8,4),str(size)+' ppem: before / after',fill=0)
        row.paste(a,(170,0)); row.paste(b,(170,a.height)); rows.append(row)
        records.append({'ppem':size,'before_pixels':hashlib.sha256(a.tobytes()).hexdigest(),'after_pixels':hashlib.sha256(b.tobytes()).hexdigest(),
                        'different':a.tobytes()!=b.tobytes()})
    image=Image.new('L',(max(r.width for r in rows),sum(r.height for r in rows)),255); y=0
    for row in rows: image.paste(row,(0,y)); y+=row.height
    out.parent.mkdir(parents=True,exist_ok=True); image.save(out)
    save_json(out.with_suffix('.json'),{'engine':'FreeType','version':freetype.version(),'text':text,'records':records,
              'inputs':{str(Path(p).resolve()):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [before,after]},
              'scope':'Actual grayscale pixels at ppem. Differences are review evidence, not proof that hinting improved readability.'})
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('before',type=Path); parser.add_argument('after',type=Path); parser.add_argument('out',type=Path)
    args=parser.parse_args(); sheet(args.before,args.after,args.out)
