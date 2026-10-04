import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path(os.environ.get('TURN_TEST_SOURCE', '$HOME/.cache/learning-workbench-acceptance/m63-turn-preparation-owner-oct04'))
evidence=Path(__file__).parent
stage=evidence/'static-final';stage.mkdir(exist_ok=True)
def source():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    entries=subprocess.check_output(['git','ls-files','-s','-z'],cwd=root).split(b'\0')
    rows={}
    for entry in entries:
        if not entry:continue
        meta,name=entry.split(b'\t');name=name.decode()
        if name.startswith('progress/'):continue
        mode,blob,_=meta.decode().split()
        actual=(root/name).read_bytes();expected=subprocess.check_output(['git','cat-file','blob',blob],cwd=root)
        rows[name]={'git_blob':blob,'sha256':hashlib.sha256(actual).hexdigest(),'git_sha256':hashlib.sha256(expected).hexdigest(),'size':len(actual),'equal':actual==expected}
    return {'head':head,'status':subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True),'count':len(rows),'inputs':rows,'all_exact':all(x['equal'] for x in rows.values())}

from datetime import datetime, timezone
before=source();(stage/'before.json').write_text(json.dumps(before,indent=2)+'\n');assert before['all_exact'] and not before['status']
uv=['$HOME/.local/bin/uv','run','--frozen','--no-sync']
node=str(root/'.toolchain/node-v24.21.0-linux-x64/bin/node')
tsc='$HOME/.cache/learning-workbench-acceptance/m63-local-session-bootstrap-ui-oct03/apps/web/node_modules/typescript/bin/tsc'
commands=[('ruff',uv+['ruff','check','services/api/app','tests/integration/test_codex_turn_preparation_http.py','tests/integration/test_codex_turn_review_boundaries.py','tests/integration/test_codex_turn_lifecycle.py','tests/contract/test_api_projection.py','tests/contract/test_codex_bootstrap_routes.py']),('mypy',uv+['mypy','services/api']),('generated',uv+['python','scripts/generate_contracts.py','--check']),('spec',uv+['python','scripts/verify_spec.py']),('types',[node,tsc,'--strict','--noEmit','--target','ES2022','--module','ESNext','--moduleResolution','Bundler','tests/contract/codex_turn_types.ts','packages/contracts/generated/api-client.ts'])]
env=dict(os.environ);env['TMPDIR']=str(evidence/'tmp')
results=[]
for name,args in commands:
 started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
 with (stage/(name+'.log')).open('wb') as out:code=subprocess.call(args,cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT)
 results.append({'name':name,'command':args,'exit_code':code,'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-clock})
after=source();(stage/'after.json').write_text(json.dumps(after,indent=2)+'\n');(stage/'receipt.json').write_text(json.dumps({'head':before['head'],'source_count':before['count'],'before_equals_after':before==after,'commands':results},indent=2)+'\n')
print(json.dumps({'source_equal':before==after,'count':before['count'],'exits':{r['name']:r['exit_code'] for r in results}}))
