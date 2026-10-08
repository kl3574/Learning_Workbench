"""Fixed Git input capture and actual local authorized gate receipt; no remote calls."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

TREE=Path('$HOME/.cache/learning-workbench-acceptance/m63-production-preparation-closure-oct05')
ROOT=Path(__file__).resolve().parent
stage=sys.argv[1]
argv=sys.argv[2:]
if not stage.replace('-','').isalnum() or not argv: raise ValueError('Explicit stage and command required')
p=ROOT/stage
p.mkdir(exist_ok=False)
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def git(*args): return subprocess.check_output(['git','-C',str(TREE),*args])
def manifest():
 head=git('rev-parse','HEAD').decode().strip()
 status=git('status','--porcelain','--untracked-files=all').decode()
 if status: raise ValueError('Gate requires a fixed clean tracked/untracked source tree')
 entries=[]
 for row in git('ls-tree','-r','-z',head).split(b'\0'):
  if not row: continue
  header,pathraw=row.split(b'\t',1); path=pathraw.decode()
  if path.startswith('progress/'): continue
  mode,kind,blob=header.decode().split()
  if kind!='blob': raise ValueError('Unexpected source entry')
  original=git('cat-file','blob',blob)
  actual=os.readlink(TREE/path).encode() if mode=='120000' else (TREE/path).read_bytes()
  if actual!=original: raise ValueError('Source differs from fixed Git: '+path)
  entries.append(dict(path=path,mode=mode,type=kind,blob=blob,size=len(original),sha256=hashlib.sha256(original).hexdigest()))
 return {'head':head,'tree':git('rev-parse',head+'^{tree}').decode().strip(),'count':len(entries),'entries':entries}
def put(name,data): (p/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
before=manifest();put('before.json',before)
runner=(ROOT/'run_stage.py').read_bytes()
put('command.json',{'argv':argv,'cwd':str(TREE),'source_head':before['head'],'runner_sha256':hashlib.sha256(runner).hexdigest(),'scope':'Authorized local tests/static only; no real CLI/model/host security probes'})
started=now();tick=time.monotonic()
with (p/'run.log').open('wb') as stream:
 result=subprocess.run(argv,cwd=TREE,stdout=stream,stderr=subprocess.STDOUT,check=False)
finished=now();elapsed=time.monotonic()-tick
try:
 after=manifest();put('after.json',after); exact=before==after
except Exception as error:
 after=None;exact=False;put('after-error.json',{'type':type(error).__name__,'message':str(error)})
log=(p/'run.log').read_bytes()
receipt={'stage':stage,'head':before['head'],'started_at':started,'finished_at':finished,'elapsed_seconds':elapsed,'command_exit_code':result.returncode,'wrapper_exit_code':result.returncode if exact else 1,'before_after_complete_exact':exact,'input_count':before['count'],'log_size':len(log),'log_sha256':hashlib.sha256(log).hexdigest(),'runner_sha256':hashlib.sha256(runner).hexdigest()}
put('receipt.json',receipt)
print(json.dumps(receipt))
raise SystemExit(receipt['wrapper_exit_code'])
