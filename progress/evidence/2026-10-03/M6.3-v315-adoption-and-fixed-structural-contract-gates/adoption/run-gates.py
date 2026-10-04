import datetime,hashlib,json,subprocess,time
from pathlib import Path
O=Path(__file__).parent;R=Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02');H='50ec27381c4e98513bf8aac48128c201e933423f';sha=lambda b:hashlib.sha256(b).hexdigest()
assert not (O/'GATES.json').exists()
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
def state():return subprocess.check_output(['git','status','--porcelain'],cwd=R)
def mapping():
 paths=[p for p in subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0') if p and not p.startswith('progress/')]
 values={p:sha((R/p).read_bytes()) for p in paths}
 for p,digest in values.items():assert sha(subprocess.check_output(['git','show',H+':'+p],cwd=R))==digest,p
 return values
assert head()==H and not state();before=mapping();(O/'before-map.json').write_text(json.dumps(before,indent=2)+'\n')
assert not (O/'pytest-runtime').exists()
commands=[('structural',['uv','run','--frozen','--no-sync','python','scripts/verify_spec.py']),('contracts',['uv','run','--frozen','--no-sync','pytest','tests/unit/test_spec_catalog.py','tests/unit/test_spec_extraction.py','tests/contract/test_api_projection.py','tests/contract/test_codex_bootstrap_dto.py','tests/contract/test_codex_bootstrap_routes.py','-q','--basetemp='+str(O/'pytest-runtime')]),('ruff',['uv','run','--frozen','--no-sync','ruff','check','.']),('web-types',['bash','scripts/node.sh','npm','--prefix','apps/web','run','typecheck'])]
results=[];started=time.monotonic()
for label,argv in commands:
 t=time.monotonic()
 with (O/(label+'.log')).open('wb') as out:r=subprocess.run(argv,cwd=R,stdout=out,stderr=subprocess.STDOUT)
 results.append({'gate':label,'command':argv,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-t,'log_sha256':sha((O/(label+'.log')).read_bytes())})
 print(label,r.returncode,flush=True)
 if r.returncode:break
after=mapping();(O/'after-map.json').write_text(json.dumps(after,indent=2)+'\n');assert before==after and head()==H and not state()
receipt={'status':'SCOPED_V315_STRUCTURAL_CONTRACTS_PASS' if len(results)==len(commands) and all(x['exit_code']==0 for x in results) else 'FAIL_GATE','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':H,'complete_nonprogress_git_files':len(before),'before_after_git_exact':True,'gates':results,'elapsed_seconds':time.monotonic()-started,'boundary':'Only normative extraction/derived catalog, original runtime/DTO contract and TypeScript structural checks. No new Codex turn/Provider/tools/runtime acceptance; v315 actual implementation and production proof not yet complete. Exact4ecc CI receipts remain older source.'}
(O/'GATES.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False),flush=True)
assert receipt['status']=='SCOPED_V315_STRUCTURAL_CONTRACTS_PASS'
