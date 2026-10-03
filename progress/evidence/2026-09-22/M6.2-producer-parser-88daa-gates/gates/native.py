from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,signal,socket,subprocess,tempfile,time
base=Path(__file__).resolve().parent;main=base.parent/'m62-active';work=base.parent/'m62-producer-parser-native-active';stage=base/'native';stage.mkdir(exist_ok=False)
def now():return datetime.now(timezone.utc).isoformat()
def write(name,data):(stage/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=main).decode().strip()
assert not work.exists(),'Refusing to overwrite a worktree'
p=subprocess.run(['git','worktree','add','--detach',str(work),head],cwd=main,capture_output=True)
(stage/'setup.stdout').write_bytes(p.stdout);(stage/'setup.stderr').write_bytes(p.stderr);assert p.returncode==0
for name in ['.venv','.toolchain']:(work/name).symlink_to((main/name).resolve(),target_is_directory=True)
modules=work/'apps/web/node_modules';modules.mkdir();linked=[]
for source in sorted((main/'apps/web/node_modules').iterdir()):
 if source.name in {'.vite','.vite-temp','.cache'}:continue
 (modules/source.name).symlink_to(source.resolve(),target_is_directory=source.is_dir());linked.append(source.name)
for name in ['.vite','.vite-temp','.cache']:(modules/name).mkdir()
write('setup.json',{'head':head,'module_entries':linked,'node_modules_caches':'Private .vite/.vite-temp/.cache; installed dependency entries linked read-only by convention, no dependency install.'})
def sources():
 rows=[]
 for entry in subprocess.check_output(['git','ls-files','--stage','-z'],cwd=work).split(b'\0'):
  if not entry:continue
  metadata,path=entry.split(b'\t',1);mode,blob,index=metadata.decode().split();name=path.decode()
  if name.startswith('progress/'):continue
  f=work/name;data=os.readlink(f).encode() if f.is_symlink() else f.read_bytes();actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  rows.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'git_blob_sha1':blob,'git_mode':mode,'git_matches':actual==blob})
 return rows
before=sources();write('inputs-before.json',before);assert all(row['git_matches'] for row in before)
for port in [8765,5173]:
 with socket.socket() as sock:
  sock.settimeout(1);assert sock.connect_ex(('127.0.0.1',port))!=0,'Global test port already used; no process will be killed'
env={'PATH':os.environ['PATH'],'HOME':str(Path.home()),'LANG':'C.UTF-8','CI':'1','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':tempfile.mkdtemp(prefix='lw62-final-'),'LEARNING_E2E_DATA_DIR':str(stage/'global-data'),'LEARNING_E2E_OUTPUT_DIR':str(stage/'test-results')}
cmd=['bash','scripts/node.sh','npm','--prefix','apps/web','run','test:e2e','--','document-imports.spec.ts','authoring.spec.ts','authoring-groups.spec.ts','assessment-submit.spec.ts','grading-recovery.spec.ts','--retries=0']
start=now();tick=time.monotonic();timedout=False
with (stage/'test.log').open('wb') as output:
 process=subprocess.Popen(cmd,cwd=work,env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
 try:exitcode=process.wait(timeout=600)
 except subprocess.TimeoutExpired:
  timedout=True;exitcode=None;os.killpg(process.pid,signal.SIGTERM)
  try:process.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
finish=now();after=sources();write('inputs-after.json',after);log=(stage/'test.log').read_bytes()
receipt={'code_commit':head,'command':cmd,'start':start,'finish':finish,'seconds':time.monotonic()-tick,'exit_code':exitcode,'timeout':timedout,'source_count':len(before),'source_unchanged':before==after,'all_source_matches_git_before':all(x['git_matches'] for x in before),'all_source_matches_git_after':all(x['git_matches'] for x in after),'log_bytes':len(log),'log_sha256':hashlib.sha256(log).hexdigest(),'scope':'10 focused native cases: real PDF/DOCX/scanned PDF imports, single and three group authoring roots, submission ACK and grading recovery; controlled loopback only. Numeric actual environment verdict preserved, not successful sandbox arithmetic. Not the full native suite.','tmpdir':env['TMPDIR']};write('receipt.json',receipt)
print(json.dumps(receipt,indent=2));print(log.decode(errors='replace')[-3500:]);raise SystemExit(0 if exitcode==0 and before==after else 1)
