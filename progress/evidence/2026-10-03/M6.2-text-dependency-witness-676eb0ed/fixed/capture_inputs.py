import hashlib, json, subprocess, sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
paths=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
selected=[p for p in paths if p and (len(Path(p).parts)==1 or Path(p).parts[0] in {'apps','services','packages','tests','scripts','migrations'}) and not Path(p).name.startswith('.env')]
files={}
for name in sorted(selected):
    raw=(root/name).read_bytes()
    assert raw==subprocess.check_output(['git','show','HEAD:'+name],cwd=root), name
    files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
value={'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'scope':'Git tracked apps/services/packages/tests/scripts/migrations plus root files; excludes .env*, .github, docs, progress and other directories, tooling and ignored outputs','files':files,'git_status':subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True)}
assert not value['git_status']
Path(sys.argv[2]).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
print('verified input files:',len(files))
