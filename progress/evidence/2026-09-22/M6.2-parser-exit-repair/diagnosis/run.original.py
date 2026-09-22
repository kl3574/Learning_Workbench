"""Run one scoped PDF case with real source snapshots and raw process result."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
BASE=Path(__file__).resolve().parent
ROOT=BASE.parent/'m62-pdf-ci-active'
PYTHON='<LOCAL_HOME>/Desktop/learning/Learning_Workbench/.venv/bin/python'
os.umask(0o077)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def snapshot():
 rows=[]
 for n in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0'):
  if not n or n.startswith('progress/'):continue
  p=ROOT/n
  if p.is_file():
   raw=p.read_bytes();rows.append({'path':n,'bytes':len(raw),'sha256':sha(raw)})
 return rows
name=sys.argv[1];out=BASE/name;out.mkdir(mode=0o700,exist_ok=False);temp=out/'tmp';temp.mkdir()
command=[PYTHON,'-m','pytest','-q','tests/integration/test_document_http.py::test_failed_documents_report_safe_failure_and_retain_exact_original_without_formal_content[pdf-pdf_scan_fixture-True]','-p','no:cacheprovider',*sys.argv[2:]]
before=snapshot();write(out/'inputs-before.json',before)
env={**os.environ,'TMPDIR':str(temp),'PYTHONDONTWRITEBYTECODE':'1'}
start=now();clock=time.monotonic()
with (out/'test.log').open('wb') as log:
 try:exit_code=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=False).returncode
 except subprocess.TimeoutExpired:exit_code=124
finish=now();elapsed=time.monotonic()-clock;after=snapshot();write(out/'inputs-after.json',after)
raw=(out/'test.log').read_bytes();receipt={'command':command,'cwd_alias':'m62-pdf-ci-active','started_at':start,'finished_at':finish,'elapsed_seconds':elapsed,'exit_code':exit_code,'runner_timeout_seconds':120,'log_sha256':sha(raw),'log_bytes':len(raw),'source_count':len(before),'source_unchanged':before==after,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'tmpdir_alias':name+'/tmp','scope':'Only the exact original scanned-PDF HTTP test; private synthetic database/processes, no shared HTTP ports, no provider invocation, no assertion or product timeout changes.'}
write(out/'receipt.json',receipt);print(json.dumps(receipt,indent=2),flush=True)
