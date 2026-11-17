"""Package explicitly listed project files and verify every ZIP byte and required evidence hash."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local(root, relative):
    path = root/relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts or not path.is_file():
        raise ValueError('Expected an existing project-relative file: '+relative)
    if any(p.is_symlink() for p in [path,*path.parents] if p != root.parent) or not path.resolve().is_relative_to(root):
        raise ValueError('Symlinks/external dependencies must be resolved explicitly before packaging: '+relative)
    return path


def package(plan_path, output):
    plan_path, output = Path(plan_path).resolve(), Path(output).resolve()
    plan = json.loads(plan_path.read_text()); root=plan_path.parent
    if not isinstance(plan.get('release'),bool): raise ValueError('release must be an explicit boolean.')
    if output.exists(): raise ValueError('Use a fresh ZIP path.')
    rows = plan['files']
    names = [r['path'] for r in rows]
    if not names or len(names)!=len(set(names)) or 'delivery-manifest.json' in names: raise ValueError('Need unique explicit files; delivery-manifest.json is reserved.')
    for row in rows:
        if digest(local(root,row['path'])) != row['sha256']: raise ValueError('Stale file/hash: '+row['path'])
    for required in ['source','font','license','proof']:
        if not any(r.get('role')==required for r in rows): raise ValueError('Missing delivery role: '+required)
    evidence=plan['gates']
    if not evidence: raise ValueError('Declare project completion gates.')
    for gate in evidence:
        if gate['state'] not in ['pass','fail','pending','not_applicable']: raise ValueError('Unknown gate state.')
        if not gate.get('reason'): raise ValueError('Every gate needs its scope/reason.')
        for path in gate.get('evidence',[]):
            if path not in names: raise ValueError('Evidence must be packaged and hashed: '+path)
        if gate['state']=='pass' and not gate.get('evidence'): raise ValueError('Pass needs evidence.')
        for relative, sha in gate.get('subjects',{}).items():
            if not any(r['path']==relative and r['sha256']==sha for r in rows): raise ValueError('Gate subject is stale or absent: '+relative)
    blocked=[g['id'] for g in evidence if g.get('required',True) and g['state'] not in ['pass','not_applicable']]
    if plan.get('release') and blocked: raise ValueError('Release blocked by required gates: '+', '.join(blocked))
    manifest={'schema_version':1,'release':bool(plan.get('release')),'pending_required':blocked,'files':rows,'gates':evidence}
    output.parent.mkdir(parents=True,exist_ok=True)
    try:
        with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
            for row in rows: archive.write(local(root,row['path']),row['path'])
            archive.writestr('delivery-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        with zipfile.ZipFile(output) as archive:
            if archive.testzip() is not None: raise ValueError('ZIP CRC failed.')
            for row in rows:
                if hashlib.sha256(archive.read(row['path'])).hexdigest()!=row['sha256']: raise ValueError('ZIP byte mismatch.')
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {'zip':str(output),'sha256':digest(output),'files':len(rows),'release':manifest['release'],'pending_required':blocked}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('plan',type=Path); parser.add_argument('out',type=Path)
    args=parser.parse_args(); print(json.dumps(package(args.plan,args.out),ensure_ascii=False))
