import hashlib,json,os,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
OUT=Path(__file__).parent
ROOT=OUT.parent/'m62-group-decline-diagnosis-active'
STAGE=OUT/'native-once';STAGE.mkdir(mode=0o700)
def sha(b):return hashlib.sha256(b).hexdigest()
def write(name,data):(STAGE/name).write_text(json.dumps(data,indent=2)+'\n')
def snap(side):
 names=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
 facts={name:{'sha256':sha((ROOT/name).read_bytes()),'bytes':(ROOT/name).stat().st_size} for name in sorted(set(names)) if name and not name.startswith('progress/') and (ROOT/name).is_file()}
 write('inputs-'+side+'.json',facts);return facts
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip();assert head=='1fffd996e9334f7f28dcdeb970430c9aa4052ee3'
changed=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT).decode().splitlines();assert changed==['tests/e2e/authoringRuntime.ts']
for name in ('tests/e2e/authoring-groups.spec.ts','tests/e2e/authoringRuntime.ts'):
 d=STAGE/'source'/name;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes((ROOT/name).read_bytes())
for name in ('observer.ts','playwright.config.ts','package.json'):(STAGE/name).write_bytes((OUT/name).read_bytes())
base_spec=subprocess.check_output(['git','show',head+':tests/e2e/authoring-groups.spec.ts'],cwd=ROOT);assert base_spec==(ROOT/'tests/e2e/authoring-groups.spec.ts').read_bytes()
before=snap('before')
env={key:os.environ[key] for key in ('PATH','HOME','LANG','LC_ALL','TZ','DISPLAY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS') if key in os.environ}
env['LEARNING_GROUP_DECLINE_OBSERVATION']=str(STAGE/'mechanism.json')
cmd=['bash','scripts/node.sh','node','apps/web/node_modules/@playwright/test/cli.js','test','--config',str(OUT/'playwright.config.ts'),'--grep','native lesson group preserves its plan and formulas, then separately declines and executes one exact numeric member']
start=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
write('started.json',{'head':head,'command':cmd,'started_at':start,'original_test_sha256':sha(base_spec),'harness_only_changed_paths':changed,'global_webservers':'not started; original AuthoringRuntime dynamic ports only','max_case_attempts':1,'driver_sha256':sha(Path(__file__).read_bytes())})
print(json.dumps({'state':'RUNNING','started_at':start}),flush=True)
with (STAGE/'run.log').open('wb') as log:p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
after=snap('after');raw=(STAGE/'run.log').read_bytes()
r={'head':head,'command':cmd,'exit_code':p.returncode,'seconds':time.monotonic()-clock,'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'source_count':len(before),'before_after_unchanged':before==after,'harness_only_changed_paths':changed,'log_sha256':sha(raw),'log_bytes':len(raw),'claim':'One targeted observed run of unchanged original case, not rerunning the full gate and not proof of original failure cause if it passes.'}
write('receipt.json',r);print(json.dumps(r),flush=True);raise SystemExit(p.returncode)
