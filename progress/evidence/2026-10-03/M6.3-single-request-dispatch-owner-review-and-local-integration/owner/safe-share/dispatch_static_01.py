import hashlib,json,os,subprocess,time
from pathlib import Path
root=Path('$HOME/.cache/learning-workbench-acceptance/m63-turn-dispatch-owner-oct04')
e=Path(__file__).parent/'dispatch-static-01';e.mkdir(exist_ok=False)
def source():
 names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0');rows={}
 for n in names:
  if not n or n.startswith('progress/'):continue
  b=(root/n).read_bytes();g=subprocess.check_output(['git','show','HEAD:'+n],cwd=root)
  rows[n]={'sha256':hashlib.sha256(b).hexdigest(),'git_sha256':hashlib.sha256(g).hexdigest(),'size':len(b),'equal':b==g}
 return {'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'status':subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True),'inputs':rows,'count':len(rows),'all_exact':all(r['equal'] for r in rows.values())}
before=source();assert not before['status'] and before['all_exact'];(e/'before.json').write_text(json.dumps(before,indent=2)+'\n')
u=['$HOME/.local/bin/uv','run','--frozen','--no-sync']
commands=[('ruff',u+['ruff','check','services/api','tests/integration/test_codex_turn_consent_http.py','tests/integration/test_codex_turn_dispatch_http.py','tests/security/test_local_boundary.py','tests/contract/test_api_projection.py']),('mypy',u+['mypy','services/api']),('generated',u+['python','scripts/generate_contracts.py','--check']),('spec',u+['python','scripts/verify_spec.py']),('typescript',[str(root/'.toolchain/node-v24.21.0-linux-x64/bin/node'),'$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02/apps/web/node_modules/typescript/bin/tsc','--noEmit','--strict','--skipLibCheck','--target','ES2022','--module','ESNext','--moduleResolution','bundler','--lib','ES2022,DOM',*[str(p) for p in sorted((root/'packages/contracts/generated').glob('*.ts'))]]),('whitespace',['git','diff','--check'])]
results=[];env=dict(os.environ);env['TMPDIR']=str(Path(__file__).parent/'tmp')
for name,args in commands:
 start=time.monotonic()
 with (e/(name+'.log')).open('wb') as out:code=subprocess.call(args,cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT)
 results.append({'name':name,'command':args,'exit_code':code,'seconds':time.monotonic()-start})
after=source();(e/'after.json').write_text(json.dumps(after,indent=2)+'\n');(e/'receipt.json').write_text(json.dumps({'head':before['head'],'results':results,'unchanged':before==after},indent=2)+'\n');print(json.dumps({'results':[(x['name'],x['exit_code']) for x in results],'unchanged':before==after}))
