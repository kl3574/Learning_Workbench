from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,time,os,signal
H=Path(__file__).resolve().parent;R=H.parent/'m62-edit-publication-terminal-active';stage=H/sys.argv[1];stage.mkdir();pool=H/'source-pool';pool.mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def capture():
 names=set(git('ls-files','-z').decode().split('\0'))|set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'));data={}
 for name in sorted(names):
  if not name or name.startswith('progress/'):continue
  p=R/name;raw=os.readlink(p).encode() if p.is_symlink() else p.read_bytes();digest=sha(raw);q=pool/digest
  if not q.exists():q.write_bytes(raw)
  assert q.read_bytes()==raw;data[name]={'bytes':len(raw),'sha256':digest}
 return data
cmd=json.loads(sys.argv[2]);before=capture();dump(stage/'inputs-before.json',before);head=git('rev-parse','HEAD').decode().strip();start=datetime.now(timezone.utc).isoformat();begin=time.monotonic();timeout=False
with (stage/'run.log').open('wb') as log:
 p=subprocess.Popen(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},start_new_session=True)
 try:code=p.wait(timeout=1800)
 except subprocess.TimeoutExpired:
  timeout=True;os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  code=p.returncode
after=capture();dump(stage/'inputs-after.json',after);raw=(stage/'run.log').read_bytes();receipt={'command':cmd,'actual_head':head,'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'seconds':time.monotonic()-begin,'exit_code':code,'timeout':timeout,'input_count_before':len(before),'input_count_after':len(after),'unchanged':before==after,'log_sha256':sha(raw),'log_bytes':len(raw),'driver_sha256':sha(Path(__file__).read_bytes())};dump(stage/'receipt.json',receipt);print(json.dumps(receipt));print(raw.decode(errors='replace')[-5000:]);raise SystemExit(code or (0 if before==after else 1))
