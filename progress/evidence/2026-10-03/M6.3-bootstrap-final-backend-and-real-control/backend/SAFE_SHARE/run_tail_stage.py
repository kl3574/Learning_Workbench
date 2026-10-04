import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path('$HOME/.cache/learning-workbench-acceptance/m63-bootstrap-tail-original-366-oct03')
out=Path(__file__).parent/'stages'/sys.argv[1]
out.mkdir(exist_ok=False)
def inputs():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    blobs={}
    for row in subprocess.check_output(['git','ls-tree','-r','-z',head],cwd=root).split(b'\0'):
        if row:
            meta,name=row.split(b'\t',1); blobs[name.decode()]=meta.split()[2].decode()
    names=set(p.decode() for p in subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=root).split(b'\0') if p)
    entries={}
    for name in sorted(names):
        if name.startswith('progress/'):
            continue
        data=(root/name).read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        entries[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'git_blob':blobs.get(name),'matches_git':blobs.get(name)==blob}
    data=Path(__file__).read_bytes()
    return {'head':head,'scope':'all nonprogress tracked plus nonignored worktree inputs; private runner separately bound','files':entries,'runner_sha256':hashlib.sha256(data).hexdigest()}
def write(name,value):
    (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
before=inputs();write('before.json',before)
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTEST_ADDOPTS':''}
start=time.monotonic()
with (out/'raw.log').open('wb') as log:
    process=subprocess.run(sys.argv[2:],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
after=inputs();write('after.json',after)
write('result.json',{'command':sys.argv[2:],'exit_code':process.returncode,'seconds':time.monotonic()-start,'head':before['head'],'input_count':len(before['files']),'inputs_unchanged':before==after,'all_match_git':all(v['matches_git'] for v in before['files'].values())})
print(json.dumps({'exit_code':process.returncode,'input_count':len(before['files']),'inputs_unchanged':before==after,'stage':out.name}))
raise SystemExit(process.returncode)
