"""Check crop geometry, preserved pixels, previews and refusal to overwrite."""

from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from crop_cover import crop_cover


def test_crop_cover():
    with TemporaryDirectory(prefix='miao-cover-test-') as temporary:
        root = Path(temporary)
        cases = [
            ((1080, 1920), [0, 240, 1080, 1680]),
            ((1920, 1080), [555, 0, 1365, 1080]),
            ((1672, 941), [483, 0, 1188, 940]),
        ]
        for index, (size, box) in enumerate(cases):
            source, output = root / f'{index}.png', root / str(index)
            image = Image.linear_gradient('L').resize(size).convert('RGBA')
            image.putpixel((box[0], box[1]), (12, 34, 56, 78))
            image.save(source)
            report = crop_cover(source, output)
            assert report['crop_box'] == box
            assert report['visual_review'] == 'required'
            cropped = output / '封面-中央3x4.png'
            with Image.open(cropped) as actual:
                assert actual.tobytes() == image.crop(box).tobytes()
                assert actual.width * 4 == actual.height * 3
            for name in ['完整', '中央3x4']:
                with Image.open(output / f'预览-{name}.png') as preview:
                    assert preview.width == 390
            before = cropped.read_bytes()
            try:
                crop_cover(source, output)
            except FileExistsError:
                pass
            else:
                raise AssertionError('Existing output directory was overwritten')
            assert cropped.read_bytes() == before
        tiny = root / 'tiny.png'
        Image.new('RGB', (2, 2)).save(tiny)
        try:
            crop_cover(tiny, root / 'tiny-output')
        except ValueError:
            pass
        else:
            raise AssertionError('Image too small for 3:4 was accepted')
        assert not (root / 'tiny-output').exists()


if __name__ == '__main__':
    test_crop_cover()
    print('Crop geometry, pixels, previews, tiny input and no-overwrite checks passed.')
