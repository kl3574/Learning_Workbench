from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,subprocess,socket,sys,tempfile,time
base=Path(__file__).resolve().parent;work=base.parent/'m62-grading-submit-race-active';stage=base/sys.argv[1];stage.mkdir(exist_ok=False)
def now():return datetime.now(timezone.utc).isoformat()
def write(name,v):(stage/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sources():
 values=[]
 entries=subprocess.check_output(['git','ls-files','--stage','-z'],cwd=work).split(b'\0')
 entries.append(b'100644 '+'0'.encode()*40+b' 0\ttests/e2e/assessment-submit.spec.ts')
 for entry in entries:
  if not entry:continue
  meta,path=entry.split(b'\t',1);mode,blob,index=meta.decode().split();name=path.decode()
  if name.startswith('progress/'):continue
  f=work/name;data=os.readlink(f).encode() if f.is_symlink() else f.read_bytes();actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  values.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'git_blob_sha1':None if blob=='0'*40 else blob,'git_matches':actual==blob,'git_mode':None if blob=='0'*40 else mode})
 return values
before=sources();write('inputs-before.json',before)
changes=[x['path'] for x in before if not x['git_matches']];assert set(changes)=={'tests/e2e/assessmentTestData.ts','tests/e2e/grading-recovery.spec.ts','tests/e2e/assessment-submit.spec.ts'},changes

for rel in changes:
 target=stage/'source'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((work/rel).read_bytes())
for port in (8765,5173):
 with socket.socket() as sock:
  sock.settimeout(1);assert sock.connect_ex(('127.0.0.1',port))!=0,'Existing global test port; no restart or kill authorized'
env={'PATH':os.environ['PATH'],'HOME':str(Path.home()),'LANG':'C.UTF-8','CI':'1','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':tempfile.mkdtemp(prefix='lw62-race-'),'LEARNING_E2E_DATA_DIR':str(stage/'global-data'),'LEARNING_E2E_OUTPUT_DIR':str(stage/'test-results')}
cmd=['bash','scripts/node.sh','npm','--prefix','apps/web','run','test:e2e','--','assessment-submit.spec.ts','grading-recovery.spec.ts','--retries=0']
started=now();tick=time.monotonic()
with (stage/'test.log').open('wb') as out:p=subprocess.run(cmd,cwd=work,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=180)
finished=now();elapsed=time.monotonic()-tick;after=sources();write('inputs-after.json',after)
log=(stage/'test.log').read_bytes();receipt={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=work).decode().strip(),'command':cmd,'start':started,'finish':finished,'seconds':elapsed,'exit_code':p.returncode,'log_sha256':hashlib.sha256(log).hexdigest(),'source_count':len(before),'source_unchanged_during_run':before==after,'intentional_changed_source':changes,'controlled_request_delay':'explicit gate, no injected response','original_case_timeout_ms':120000,'original_assertions_preserved':True,'playwright_retries':0,'tmpdir':env['TMPDIR'],'scope':'Final helper, existing complete grading-recovery case and new real pending-submission regression. Original result assertions unchanged. Private synthetic workspaces; no provider calls.'};write('receipt.json',receipt)
print(json.dumps(receipt,ensure_ascii=False,indent=2));print(log.decode()[-4000:]);raise SystemExit(p.returncode)
