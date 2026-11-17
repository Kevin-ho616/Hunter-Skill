"""Fetch pinned public font fixtures and their licenses; never overwrite a different file."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request


def fetch_sources(directory, ids=None, download=False):
    registry = json.loads((Path(__file__).resolve().parents[1] / 'assets/specialty-sources.json').read_text())
    available = {s['id']: s for s in registry['sources']}
    if ids and not set(ids) <= set(available):
        raise ValueError('Unknown sample source ID.')
    results = []
    for key in ids or available:
        entry = available[key]
        folder = Path(directory) / key
        files = []
        for kind in ['font', 'license', 'metadata']:
            if kind not in entry:
                continue
            spec = entry[kind]
            if Path(spec['file']).name != spec['file'] or not spec['url'].startswith('https://'):
                raise ValueError('Source needs a basename and public HTTPS URL.')
            target = folder / spec['file']
            if target.exists():
                data = target.read_bytes()
            elif not download:
                raise FileNotFoundError(f'{target}; use --download to fetch the pinned public source.')
            else:
                folder.mkdir(parents=True, exist_ok=True)
                request = urllib.request.Request(spec['url'], headers={'User-Agent': 'HunterFontSkill-Samples/1'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    data = response.read()
                if len(data) != spec['bytes'] or hashlib.sha256(data).hexdigest() != spec['sha256']:
                    raise ValueError('Downloaded sample checksum differs: ' + key)
                with tempfile.NamedTemporaryFile(dir=folder, delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(data)
                try:
                    try:
                        target.hardlink_to(temporary)
                    except FileExistsError:
                        if target.read_bytes() != data:
                            raise ValueError('Cache file appeared during download; refusing to overwrite: '+str(target))
                finally:
                    temporary.unlink(missing_ok=True)
            if len(data) != spec['bytes'] or hashlib.sha256(data).hexdigest() != spec['sha256']:
                raise ValueError('Existing sample differs; use a fresh cache directory: ' + str(target))
            files.append({'kind': kind, 'path': str(target.resolve()), 'sha256': spec['sha256']})
        results.append({'id': key, 'commit': entry['commit'], 'files': files})
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--ids', nargs='+')
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    print(json.dumps(fetch_sources(args.directory, args.ids, args.download), ensure_ascii=False, indent=2))
