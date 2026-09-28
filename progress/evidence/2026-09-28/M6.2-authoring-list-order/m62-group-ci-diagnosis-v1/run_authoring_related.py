from pathlib import Path
import datetime, hashlib, json, os, subprocess, time
root=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-group-ci-diagnosis-active')
base=Path(__file__).parent

def inputs():
 paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
 return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths if p and not p.startswith('progress/')}

a=inputs(); (base/'authoring-related-green-before.json').write_text(json.dumps(a,indent=2)+'\n')
cmd=['bash','scripts/node.sh','npm','--prefix','apps/web','test','--','src/features/authoring']
started=datetime.datetime.now(datetime.timezone.utc).isoformat(); t=time.monotonic()
env={k:v for k,v in os.environ.items() if k in ['HOME','PATH','LANG','DISPLAY','XDG_RUNTIME_DIR']}
env['CI']='1'
with (base/'authoring-related-green.log').open('wb') as out:
 p=subprocess.run(cmd,cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=180)
z=inputs(); (base/'authoring-related-green-after.json').write_text(json.dumps(z,indent=2)+'\n')
record=dict(command=cmd,started_at=started,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed=time.monotonic()-t,exit_code=p.returncode,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),engineering_inputs=len(a),source_stable=a==z,log_sha256=hashlib.sha256((base/'authoring-related-green.log').read_bytes()).hexdigest(),boundary='Controlled real hook and IndexedDB semantics; synthetic AuthoringPort responses. No historical CI root-cause claim.')
(base/'authoring-related-green-receipt.json').write_text(json.dumps(record,indent=2)+'\n'); print(json.dumps(record)); raise SystemExit(p.returncode)
