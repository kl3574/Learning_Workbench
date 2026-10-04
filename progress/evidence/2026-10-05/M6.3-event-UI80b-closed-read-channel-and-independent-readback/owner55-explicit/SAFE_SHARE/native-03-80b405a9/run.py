from pathlib import Path
import subprocess, hashlib, json, time, os
root=Path('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-turn-event-ui-oct05')
out=Path(__file__).parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=root)
head=git('rev-parse','HEAD').decode().strip()
assert head=='80b405a9c859c47bff0d9b74465f1e7370268218'
paths=[p for p in git('ls-files','-z').decode().split('\0') if p and not p.startswith('progress/')]
def inputs():
 result={}
 for path in paths:
  raw=(root/path).read_bytes(); blob=git('show',f'{head}:{path}')
  result[path]={'sha256':sha(raw),'bytes':len(raw),'git_sha256':sha(blob),'git_exact':raw==blob}
 assert all(v['git_exact'] for v in result.values())
 return result
private={name:sha((out/name).read_bytes()) for name in ['run.py','playwright.config.ts','event-reader.spec.ts','package.json','event-harness.tsx']}
assert (root/'apps/web/.local_data/event-harness.tsx').read_bytes()==(out/'event-harness.tsx').read_bytes()
before=inputs();(out/'inputs-before.json').write_text(json.dumps(before,sort_keys=True,indent=2)+'\n')
env={**os.environ,'TMPDIR':'<LOCAL_HOME>/.cache/m63-evt-tmp'}
commands=[('native',['bash','scripts/node.sh','node','apps/web/node_modules/@playwright/test/cli.js','test','--config',str(out/'playwright.config.ts')])]
results=[]
for name,command in commands:
 t=time.monotonic()
 with (out/f'{name}.log').open('wb') as log:r=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
 results.append({'name':name,'command':command,'exit_code':r.returncode,'seconds':time.monotonic()-t,'log_sha256':sha((out/f'{name}.log').read_bytes())})
 (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps(results[-1]),flush=True)
assert (root/'apps/web/.local_data/event-harness.tsx').read_bytes()==(out/'event-harness.tsx').read_bytes()
after=inputs();(out/'inputs-after.json').write_text(json.dumps(after,sort_keys=True,indent=2)+'\n')
receipt={'head':head,'spec_sha256':sha((root/'PRODUCT_DESIGN.md').read_bytes()),'input_count':len(before),'source_equal':before==after,'all_git_exact':True,'git_status':git('status','--porcelain').decode(),'runner_sha256':sha(Path(__file__).read_bytes()),'commands':results,'private_inputs':private,'private_unchanged':all(sha((out/name).read_bytes())==digest for name,digest in private.items())}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
