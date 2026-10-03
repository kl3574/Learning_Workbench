from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
BASE=Path(__file__).resolve().parent
WORK=BASE.parent/'m62-catalog-wiring-active'
name,*command=sys.argv[1:]
assert name and command
stage=BASE/name;stage.mkdir()
def sha(data): return hashlib.sha256(data).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def inputs():
 names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=WORK).split(b'\0')
 result=[]
 for name in sorted(set(names)):
  if not name: continue
  path=name.decode()
  if path.startswith('progress/'): continue
  item=WORK/path
  data=os.readlink(item).encode() if item.is_symlink() else item.read_bytes()
  result.append({'path':path,'bytes':len(data),'sha256':sha(data)})
 return result
def write(name,value): (stage/name).write_text(json.dumps(value,indent=2)+'\n')
before=inputs();write('inputs-before.json',before)
for row in before:
 if row['path'].startswith(('services/api/app/application/draft_candidate','services/api/app/infrastructure/draft_candidate')) or row['path'] in ['services/api/app/infrastructure/import_worker.py','services/api/app/application/authoring_worker.py','services/api/app/application/authoring_group_worker.py','tests/integration/test_draft_candidate_catalog.py','tests/integration/test_draft_candidate_owners.py']:
  source=stage/'source'/row['path'];source.parent.mkdir(parents=True,exist_ok=True);source.write_bytes((WORK/row['path']).read_bytes())
env={key:os.environ[key] for key in ['PATH','HOME']}
env.update(LANG='C.UTF-8',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(BASE/'tmp'),XDG_CACHE_HOME=str(BASE/'tool-cache'))
started=now();begin=time.monotonic()
with (stage/'output.log').open('xb') as log:
 result=subprocess.run(command,cwd=WORK,env=env,stdout=log,stderr=subprocess.STDOUT)
after=inputs();write('inputs-after.json',after)
log=(stage/'output.log').read_bytes()
receipt={'started_at':started,'finished_at':now(),'wall_seconds':time.monotonic()-begin,'argv':command,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),'exit_code':result.returncode,'log_bytes':len(log),'log_sha256':sha(log),'source_count':len(before),'source_unchanged':before==after,'scope':'Only explicit selected command; synthetic loopback fixtures are not vendor proof.'}
write('receipt.json',receipt);print(json.dumps(receipt,indent=2))
