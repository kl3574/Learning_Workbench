from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
ROOT=Path('$HOME/.cache/learning-workbench-acceptance/m63-codex-capabilities-oct03')
OUT=Path(__file__).parent
stage=sys.argv[1];command=sys.argv[2:];dest=OUT/stage;dest.mkdir()
h=lambda raw:hashlib.sha256(raw).hexdigest()
def capture():
 paths=set(subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0'))|set(subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0'))
 return {name:h((ROOT/name).read_bytes()) for name in sorted(paths) if name and not name.startswith('progress/') and (ROOT/name).is_file()}
before=capture();(dest/'before.json').write_text(json.dumps(before,indent=2)+'\n')
changed=set(subprocess.check_output(['git','diff','--name-only','HEAD','-z'],cwd=ROOT).decode().split('\0'))|set(subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0'))
for name in sorted(changed):
 if name and name in before:
  copy=dest/'source'/name;copy.parent.mkdir(parents=True,exist_ok=True);copy.write_bytes((ROOT/name).read_bytes())
tmp=Path('$HOME/.cache/m63-capability-tmp');tmp.mkdir(exist_ok=True)
env=dict(os.environ,TMPDIR=str(tmp),PYTHONDONTWRITEBYTECODE='1')
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (dest/'run.log').open('wb') as log: result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
after=capture();(dest/'after.json').write_text(json.dumps(after,indent=2)+'\n')
receipt={'command':command,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit':result.returncode,'input_count':len(before),'inputs_unchanged':before==after,'before_sha256':h((dest/'before.json').read_bytes()),'after_sha256':h((dest/'after.json').read_bytes()),'log_sha256':h((dest/'run.log').read_bytes())}
(dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));raise SystemExit(result.returncode)
