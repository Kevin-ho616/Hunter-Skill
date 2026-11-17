#!/usr/bin/env python3
"""Measure a font or a single text image; calibrate pixel readings against a known font."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import statistics
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from font_common import FontData, font_measurements, save_json


def font_report(path):
    face = FontData(path)
    values = font_measurements(face)
    return {'schema_version': 1, 'kind': 'font_measurement',
            'source': {'path': str(face.path), 'sha256': face.info['sha256']},
            'units': 'cap-normalised, cap=700; contrast is a ratio',
            'metrics': {k: {'value': v, 'confidence': 'high' if v is not None else 'unknown',
                            'method': 'outline cuts sampled at 64 segments per curve; exact outline heights'} for k,v in values.items()},
            'notes': ['Read-only; measurements do not set design targets or approve a visual direction.',
                      'Variable fonts are measured at their default instance.']}


def components(image):
    from PIL import ImageOps
    gray = ImageOps.grayscale(image)
    histogram = gray.histogram()
    median, count = 0, 0
    for median, n in enumerate(histogram):
        count += n
        if count >= gray.width*gray.height/2:
            break
    if median < 128:
        gray = ImageOps.invert(gray)
    w, h = gray.size
    mask = gray.point(lambda p: 255 if p < 128 else 0).tobytes()
    seen, groups = bytearray(w*h), []
    for start, ink in enumerate(mask):
        if not ink or seen[start]:
            continue
        stack, points = [start], []
        seen[start] = 1
        while stack:
            index = stack.pop()
            points.append(index)
            x, y = index % w, index // w
            for yy in range(max(0,y-1), min(h,y+2)):
                for xx in range(max(0,x-1), min(w,x+2)):
                    nxt = yy*w+xx
                    if mask[nxt] and not seen[nxt]:
                        seen[nxt] = 1
                        stack.append(nxt)
        groups.append(set(points))
    if not groups:
        raise ValueError('No readable dark-on-light or light-on-dark text.')
    groups = [p for p in groups if len(p) >= max(2, statistics.median(map(len,groups))*.01)]
    boxes = lambda p: (min(i%w for i in p), min(i//w for i in p), max(i%w for i in p)+1, max(i//w for i in p)+1)
    # A disconnected dot/accent joins the larger body directly underneath it.
    merged = []
    for group in sorted(groups, key=len, reverse=True):
        x0,y0,x1,y1 = boxes(group)
        owner = next((p for p in merged if boxes(p)[0] <= (x0+x1)/2 <= boxes(p)[2]
                      and (y1 <= boxes(p)[1] or y0 >= boxes(p)[3])), None)
        if owner is None:
            merged.append(group)
        else:
            owner.update(group)
    return gray, sorted([boxes(p) for p in merged], key=lambda b:b[0])


def pixel_runs(gray, box, position, vertical=False):
    x0,y0,x1,y1 = box
    values = [1-gray.getpixel((round(position),p))/255 for p in range(max(0,y0-1),min(gray.height,y1+1))] if vertical else \
             [1-gray.getpixel((p,round(position)))/255 for p in range(max(0,x0-1),min(gray.width,x1+1))]
    runs, current = [], 0
    for value in values+[0]:
        if value > .02:
            current += value
        elif current:
            # shortcut: isolated coverage below half a pixel is noise; use larger input for subpixel strokes.
            if current >= .5:
                runs.append(current)
            current = 0
    return runs


def image_report(path, text, cap_char='H', xheight_chars='x', stem_chars='n', calibration=None):
    from PIL import Image
    if len(cap_char) != 1 or cap_char.isspace() or not text.strip():
        raise ValueError('Provide nonempty reference text and one real cap anchor character.')
    with Image.open(path) as source:
        rgba = source.convert('RGBA')
        image = Image.new('RGBA', rgba.size, 'white')
        image.alpha_composite(rgba)
        gray, boxes = components(image.convert('RGB'))
    chars = [c for c in text if not c.isspace()]
    if len(chars) != len(boxes):
        raise ValueError(f'{len(boxes)} connected letters, {len(chars)} text characters; crop one line or correct --text. No glyph is invented.')
    labelled = list(zip(chars, boxes))
    flat = [b[3] for c,b in labelled if c in 'HIEFLMNTXZhnmrx']
    baseline = statistics.median(flat or [b[3] for _,b in labelled])
    cap_boxes = [b for c,b in labelled if c == cap_char]
    cap = baseline-min(b[1] for b in cap_boxes) if cap_boxes else None
    xs = [baseline-b[1] for c,b in labelled if c in xheight_chars]
    xh = statistics.mean(xs) if xs else None
    raw = {'cap': cap, 'xh': xh, 'asc': None, 'desc': None, 'n_stem': None,
           'o_side': None, 'o_thin': None, 'contrast': None}
    asc = [baseline-b[1] for c,b in labelled if c in 'bdhkl']
    desc = [baseline-b[3] for c,b in labelled if c in 'pq']
    raw['asc'] = statistics.mean(asc) if asc else None
    raw['desc'] = statistics.mean(desc) if desc else None
    stems = []
    for c,b in labelled:
        if c in stem_chars:
            runs = pixel_runs(gray,b,baseline-(xh or (b[3]-b[1]))/2)
            if runs:
                stems.append(runs[-1] if c == 'd' else runs[0])
        if c == 'o':
            sides = pixel_runs(gray,b,(b[1]+b[3]-1)/2)
            thins = pixel_runs(gray,b,(b[0]+b[2]-1)/2,True)
            raw['o_side'] = statistics.mean(sides) if sides else None
            raw['o_thin'] = min(thins) if thins else None
    raw['n_stem'] = statistics.mean(stems) if stems else None
    if raw['o_side'] and raw['o_thin']:
        raw['contrast'] = raw['o_thin']/raw['o_side']
    scale = 700/cap if cap and cap > 0 else None
    proxy = cap_char != 'H' or not flat
    metrics = {}
    for key, value in raw.items():
        number = value if key == 'contrast' else value*scale if value is not None and scale else None
        confidence = 'unknown' if number is None else 'low' if proxy or (cap or 0)<60 else 'medium'
        if key in ('xh','n_stem') and (xheight_chars != 'x' if key == 'xh' else stem_chars != 'n') and number is not None:
            confidence = 'low'
        metrics[key] = {'value': round(number,4) if number is not None else None, 'confidence': confidence,
                        'method': 'grayscale pixels; explicit anchors/proxies, not reference outlines'}
    notes = ['No per-glyph advances, sidebearings or kerning can be recovered from ordinary logo text.',
             'Pixel precision calibration does not establish the unseen glyph structure or em size.']
    if not cap:
        notes.append(f'No {cap_char}: cap-normalised measurements are unknown; specify a real --cap-char if justified.')
    if proxy:
        notes.append(f'Cap anchor {cap_char!r} or baseline is a proxy; normalised values have low confidence.')
    result = {'schema_version':1, 'kind':'image_measurement',
              'source':{'path':str(Path(path).resolve()),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()},
              'text':text, 'units':'cap-normalised, cap=700; contrast is a ratio', 'cap_px':cap,
              'anchors':{'cap':cap_char,'xheight':xheight_chars,'stem':stem_chars},
              'pixel_values':raw,'metrics':metrics,'notes':notes,'calibration':None}
    if calibration:
        check = json.loads(Path(calibration).read_text())
        if check.get('kind') != 'pixel_calibration' or not isinstance(check.get('cap_px'),(int,float)) or check['cap_px'] <= 0:
            raise ValueError('Not a pixel calibration report.')
        compatible = bool(cap and .8 <= cap/check['cap_px'] <= 1.25)
        result['calibration'] = {'file':str(Path(calibration).resolve()), 'similar_cap_size':compatible,
                                 'observed_errors':check['errors']}
        if not compatible:
            notes.append('Calibration is from another size; rerun at the reference cap height.')
    else:
        notes.append('Pixel reader is uncalibrated for this input; run calibrate before treating numbers as design evidence.')
    return result


def calibrate(path, px, output):
    from PIL import Image, ImageDraw, ImageFont
    face = FontData(path)
    text, ss = 'HnxodnH', 4
    if not all(ord(c) in face.cmap for c in text):
        raise ValueError('Calibration requires the real H, n, x, o and d glyphs.')
    font = ImageFont.truetype(io.BytesIO(face.sfnt_bytes()), round(px*ss))
    box = font.getbbox(text, anchor='ls')
    pad = round(px*.3*ss)
    image = Image.new('L',(box[2]-box[0]+pad*2,box[3]-box[1]+pad*2),255)
    ImageDraw.Draw(image).text((pad-box[0],pad-box[1]),text,font=font,anchor='ls',fill=0)
    image = image.resize((round(image.width/ss),round(image.height/ss)),Image.Resampling.LANCZOS)
    image_path = Path(output).with_suffix('.png')
    if image_path.exists() or Path(output).exists():
        raise FileExistsError('Use a new calibration output path.')
    image_path.parent.mkdir(parents=True,exist_ok=True)
    image.save(image_path)
    observed = image_report(image_path,text)
    expected = font_report(path)
    errors = {key: round(item['value']-expected['metrics'][key]['value'],4)
              for key,item in observed['metrics'].items()
              if item['value'] is not None and expected['metrics'][key]['value'] is not None}
    return {'schema_version':1,'kind':'pixel_calibration','font':face.info,
            'px_per_em':px,'cap_px':observed['cap_px'],'sample_image':image_path.name,
            'profile':'Pillow grayscale, 4x supersampling; one horizontal line',
            'expected':expected['metrics'],'observed':observed['metrics'],'errors':errors,
            'notes':['Errors describe this renderer, font and size, not a universal screenshot accuracy guarantee.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='kind',required=True)
    for kind in ('font','image','calibrate'):
        p = sub.add_parser(kind)
        p.add_argument('source',type=Path)
        p.add_argument('--out',type=Path,required=True)
        if kind == 'image':
            p.add_argument('--text',required=True)
            p.add_argument('--cap-char',default='H')
            p.add_argument('--xheight-chars',default='x')
            p.add_argument('--stem-chars',default='n')
            p.add_argument('--calibration',type=Path)
        if kind == 'calibrate':
            p.add_argument('--px',type=float,default=200)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Output already exists; use a fresh versioned path.')
    if args.kind == 'font':
        result = font_report(args.source)
    elif args.kind == 'image':
        result = image_report(args.source,args.text,args.cap_char,args.xheight_chars,args.stem_chars,args.calibration)
    else:
        if not 8 <= args.px <= 1000:
            parser.error('--px must be between 8 and 1000.')
        result = calibrate(args.source,args.px,args.out)
    save_json(args.out,result)
    print(json.dumps({'report':str(args.out.resolve()),'kind':result['kind']},ensure_ascii=False))


if __name__ == '__main__':
    main()
