"""Run one bounded isolated test command and preserve exact declared source inputs."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

BASE=Path(__file__).resolve().parent
TREE=BASE.parent/'m62-artifact-owner-active'
PYTHON=Path('<LOCAL_HOME>/Desktop/learning/Learning_Workbench/.venv/bin/python')
name=sys.argv[1]
folder=BASE/name
folder.mkdir(mode=0o700)
files=['services/api/app/application/artifacts.py', 'services/api/app/infrastructure/artifact_repository.py', 'services/api/app/application/imports.py', 'services/api/app/application/jobs.py', 'services/api/app/infrastructure/security.py', 'services/api/app/interfaces/import_http.py']
command=[str(PYTHON),'-m',sys.argv[2],*(['check',*files,'tests/integration/test_artifact_owners.py'] if sys.argv[2]=='ruff' else ['--cache-dir',str(folder/'private-mypy-cache'),*files])]

def sha(data):return hashlib.sha256(data).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def inputs():
    paths=subprocess.check_output(['git','ls-files','-c','-o','--exclude-standard','-z'],cwd=TREE).decode().split('\0')
    result=[]
    for relative in sorted(set(paths)):
        if not relative or relative.startswith('progress/') or not (TREE/relative).is_file():continue
        data=(TREE/relative).read_bytes()
        blob=subprocess.run(['git','rev-parse','--verify','HEAD:'+relative],cwd=TREE,capture_output=True)
        result.append({'path':relative,'bytes':len(data),'sha256':sha(data),'git_blob':blob.stdout.decode().strip() if blob.returncode==0 else None})
    return result
before=inputs();dump(folder/'inputs-before.json',before)
scope=['services/api/app/application/artifacts.py','services/api/app/infrastructure/artifact_repository.py','services/api/app/application/imports.py','services/api/app/application/jobs.py','services/api/app/infrastructure/security.py','services/api/app/interfaces/import_http.py','tests/integration/test_artifact_owners.py']
for relative in scope:
    if (TREE/relative).exists():
        p=folder/'source'/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((TREE/relative).read_bytes())
(folder/'runner.py').write_bytes(Path(__file__).read_bytes())
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
try:
    p=subprocess.run(command,cwd=TREE,env=env,capture_output=True,timeout=300)
    log=p.stdout+p.stderr;code=p.returncode;timed_out=False
except subprocess.TimeoutExpired as e:
    log=(e.stdout or b'')+(e.stderr or b'');code=124;timed_out=True
(folder/'test.log').write_bytes(log)
after=inputs();dump(folder/'inputs-after.json',after)
receipt={'command':command,'cwd_alias':TREE.name,'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-t,'exit_code':code,'timeout':timed_out,'source_count':len(before),'source_unchanged':before==after,'log_bytes':len(log),'log_sha256':sha(log),'runner_sha256':sha((folder/'runner.py').read_bytes()),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=TREE).decode().strip(),'scope':'Declared isolated static check only; no vendor or shared application ports; private fixtures excluded from public artifacts.'}
dump(folder/'receipt.json',receipt)
print(json.dumps(receipt,indent=2))
print('Final log line:',log.decode(errors='replace').splitlines()[-1])
