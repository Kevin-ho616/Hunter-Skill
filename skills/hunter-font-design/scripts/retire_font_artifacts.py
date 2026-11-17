"""Verify a scoped cleanup plan; --apply moves only listed old fonts/ZIPs to a fresh recoverable folder."""
import argparse
import json
from pathlib import Path
import shutil

from package_project import digest, local
from font_common import save_json


def retire(plan_path, destination=None):
    plan_path=Path(plan_path).resolve(); plan=json.loads(plan_path.read_text()); root=plan_path.parent
    if not plan.get('authorization'): raise ValueError('Record the existing user-authorized cleanup scope.')
    preserve=[(root/p).resolve() for p in plan['preserve']]
    dependencies={Path(p).resolve() for p in plan['dependencies']}
    rows=plan['candidates']; paths=[]
    if not rows or len({r['path'] for r in rows})!=len(rows): raise ValueError('Declare unique cleanup candidates.')
    for row in rows:
        path=local(root,row['path'])
        if path.suffix.lower() not in ['.ttf','.otf','.woff','.woff2','.zip']: raise ValueError('Only scoped old font/ZIP artifacts can be retired.')
        if any(path.resolve()==p or path.resolve().is_relative_to(p) for p in preserve) or path.resolve() in dependencies:
            raise ValueError('Protected/current/dependent artifact: '+str(path))
        if digest(path)!=row['sha256']: raise ValueError('Cleanup candidate changed: '+row['path'])
        paths.append(path)
    if destination is None: return {'status':'dry-run','files':rows,'bytes':sum(p.stat().st_size for p in paths)}
    destination=Path(destination).absolute()
    if destination.exists() or not destination.parent.resolve().is_relative_to(root):
        raise ValueError('Use a fresh recoverable folder inside this project.')
    destination.mkdir(); moved=[]
    try:
        for row,path in zip(rows,paths):
            if digest(path)!=row['sha256']: raise ValueError('Candidate changed during cleanup.')
            target=destination/row['path']; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.move(str(path),str(target)); moved.append((path,target))
        save_json(destination/'retired-manifest.json',{'authorization':plan['authorization'],'files':rows,'recovery':'Move each relative path back to the project root.'})
    except Exception:
        for path,target in reversed(moved): shutil.move(str(target),str(path))
        raise
    return {'status':'retired-recoverable','directory':str(destination),'files':len(moved)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('plan',type=Path)
    parser.add_argument('--apply',type=Path,metavar='FRESH_RECOVERY_FOLDER')
    args=parser.parse_args(); print(json.dumps(retire(args.plan,args.apply),ensure_ascii=False))
