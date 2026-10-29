"""Create a real centered 3:4 crop and mobile previews; visual review is still required."""

import argparse
import json
from pathlib import Path

from PIL import Image


def crop_cover(source: Path, output: Path):
    with Image.open(source) as image:
        image.load()
        width, height = image.size
        q = min(width // 3, height // 4)
        if q < 1:
            raise ValueError('Image is too small for an integer 3:4 crop')
        crop_width, crop_height = 3 * q, 4 * q
        left, top = (width - crop_width) // 2, (height - crop_height) // 2
        box = (left, top, left + crop_width, top + crop_height)
        center = image.crop(box)
        output.mkdir(parents=True, exist_ok=False)
        center.save(output / '封面-中央3x4.png')
        for name, view in [('完整', image), ('中央3x4', center)]:
            size = (390, max(1, round(view.height * 390 / view.width)))
            view.resize(size, Image.Resampling.LANCZOS).save(output / f'预览-{name}.png')
    report = {'source': str(source.resolve()), 'size': [width, height],
              'crop_box': list(box), 'crop_size': [crop_width, crop_height],
              'preview_width': 390, 'visual_review': 'required'}
    (output / '裁切记录.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path, help='New output directory; never overwrites existing files')
    args = parser.parse_args()
    print(json.dumps(crop_cover(args.source, args.output), ensure_ascii=False))
