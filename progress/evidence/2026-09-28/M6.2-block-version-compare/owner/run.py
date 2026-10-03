import sys,subprocess,json,hashlib,datetime,time,os
from pathlib import Path
BASE=Path(__file__).parent
TREE=BASE.parent/'m62-block-version-compare-active'
def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def freeze():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=TREE,text=True).strip()
    names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=TREE).decode().split('\0')
    entries=[]
    for name in sorted(set(names)):
        if not name or name.startswith(('progress/','docs/ui/')): continue
        path=TREE/name
        if not path.is_file() or path.is_symlink(): continue
        raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest();dest=BASE/'source-pool'/digest
        dest.parent.mkdir(exist_ok=True)
        if not dest.exists(): dest.write_bytes(raw)
        else: assert dest.read_bytes()==raw
        git=subprocess.run(['git','rev-parse',f'{head}:{name}'],cwd=TREE,capture_output=True,text=True)
        actual=None
        if git.returncode==0: actual=subprocess.check_output(['git','cat-file','blob',git.stdout.strip()],cwd=TREE)
        entries.append(dict(path=name,bytes=len(raw),sha256=digest,git_blob=git.stdout.strip() if git.returncode==0 else None,git_matches=actual==raw))
    return dict(head=head,files=entries)
name=sys.argv[1];cmd=sys.argv[2:];run=BASE/name;run.mkdir(exist_ok=False)
before=freeze();(run/'inputs-before.json').write_text(json.dumps(before,indent=2)+'\n')
start=stamp();clock=time.monotonic()
with (run/'run.log').open('wb') as log:
    process=subprocess.run(cmd,cwd=TREE,stdout=log,stderr=subprocess.STDOUT)
after=freeze();(run/'inputs-after.json').write_text(json.dumps(after,indent=2)+'\n')
receipt=dict(stage=name,argv=cmd,started_at=start,finished_at=stamp(),seconds=time.monotonic()-clock,exit_code=process.returncode,input_count=len(before['files']),inputs_unchanged=before==after,head=before['head'],log_sha256=hashlib.sha256((run/'run.log').read_bytes()).hexdigest(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));print((run/'run.log').read_text()[-8000:]);sys.exit(process.returncode)
