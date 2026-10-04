import datetime, hashlib, json, os, subprocess, tempfile, time
from pathlib import Path
os.umask(0o077)
base=Path(__file__).parent
root=Path(os.environ['SOURCE_TREE'])
head=os.environ['SOURCE_SHA']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==head
tmp=tempfile.mkdtemp(prefix='lwapcounter-',dir='<LOCAL_HOME>/.cache');os.chmod(tmp,0o700)
command=['node',str(base/'native.mjs')]
record={'source_sha':head,'cwd':str(root),'command':command,'TMPDIR':tmp,'boundary':'Private Chrome/loopback HTTP synthetic memory fixture; no model or CLI diagnostic.',
        'harness':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [base/'native.mjs',base/'controlled_api.py',Path(__file__)]},
        'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(base/'command.json').write_text(json.dumps(record,indent=2)+'\n')
env=dict(os.environ,TMPDIR=tmp,PYTHONDONTWRITEBYTECODE='1')
start=time.monotonic()
with (base/'run.log').open('wb') as log: result=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
record.update(exit_code=result.returncode,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,log_sha256=hashlib.sha256((base/'run.log').read_bytes()).hexdigest())
(base/'run-receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2),flush=True)
raise SystemExit(result.returncode)
