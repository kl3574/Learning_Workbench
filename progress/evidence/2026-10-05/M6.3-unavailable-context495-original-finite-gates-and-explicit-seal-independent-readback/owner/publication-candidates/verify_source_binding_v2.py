"""Documentary fixed-Git readback; not a product gate or an independent review."""
import hashlib
import json
from pathlib import Path
import subprocess

TREE=Path('$HOME/.cache/learning-workbench-acceptance/m63-production-preparation-closure-oct05')
OUT=Path(__file__).resolve().parent
BASE='6671dd5c924edbac8ca7f479c4f51d4afec14480'
FINAL='495e4daddddb64460326659be5af341085654131'
HEADS=[BASE,'7c1058f977f33b167036830c315b693cfbae2084','de4d12da56100a6b06c065e41881b69ba0ee8127',
 'da7b032720774d36c94281ceaf2cb0e9979a21d0','eef0848b',
 '45a30f4d18c5508f730cace4f838a3b70b86b009',FINAL]
OWNED=[
 'services/api/app/application/codex_turn.py',
 'services/api/app/application/codex_turn_context.py',
 'services/api/app/application/codex_turn_preparation_models.py',
 'services/api/app/application/provider_codex_consents.py',
 'services/api/app/application/provider_codex_ports.py',
 'tests/integration/test_codex_unavailable_preparation_closure.py',
]
def git(*args): return subprocess.check_output(['git','-C',str(TREE),*args])
def put(name,data): (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
blobcache={}
def raw(blob):
 if blob not in blobcache: blobcache[blob]=git('cat-file','blob',blob)
 return blobcache[blob]
def manifest(ref):
 head=git('rev-parse',ref+'^{commit}').decode().strip()
 entries=[]
 for row in git('ls-tree','-r','-z',head).split(b'\0'):
  if not row: continue
  header,pathraw=row.split(b'\t',1); path=pathraw.decode()
  if path.startswith('progress/'): continue
  mode,kind,blob=header.decode().split(); assert kind=='blob'
  body=raw(blob)
  entries.append(dict(path=path,mode=mode,type=kind,blob=blob,size=len(body),sha256=hashlib.sha256(body).hexdigest()))
 return {'head':head,'tree':git('rev-parse',head+'^{tree}').decode().strip(),'count':len(entries),'entries':entries}
maps=[manifest(h) for h in HEADS]
byhead={m['head']:{e['path']:e for e in m['entries']} for m in maps}
old,new=byhead[BASE],byhead[FINAL]
changed=sorted(p for p in set(old)|set(new) if old.get(p)!=new.get(p))
assert changed==sorted(OWNED)
unchanged=[p for p in old if p not in OWNED and old[p]==new[p]]
assert len(unchanged)==1521
assert git('status','--porcelain').decode()==''
assert git('rev-parse','HEAD').decode().strip()==FINAL
assert new['PRODUCT_DESIGN.md']['sha256']=='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
original_test='tests/integration/test_codex_unavailable_preparation_closure.py'
red,green=HEADS[1:3]
assert byhead[red][original_test]==byhead[green][original_test]
first_same=byhead[red][original_test]
prod=[p for p in OWNED if p.startswith('services/')]
source45=byhead[HEADS[-2]]
assert all(source45[p]==new[p] for p in prod)
de4delta=git('diff','--numstat',HEADS[2],FINAL,'--',*prod).decode().strip()
assert de4delta=='3\t2\tservices/api/app/application/codex_turn_context.py'
preserved=[p for p in old if (p in {'PRODUCT_DESIGN.md','migrations/0001_baseline.sql','packages/contracts/domain_models.py'}
 or p.endswith('/codex_turn_models.py') or p.endswith('/codex_turn_execution_models.py')
 or p.endswith('/codex_turn_interrupt_models.py') or p.endswith('/codex_operation_models.py')
 or p.endswith('/codex_artifact_models.py') or p.endswith('/codex_bootstrap_models.py')
 or p.endswith('/provider_codex_models.py') or p.endswith('/codex_turn_dto.py') or p.endswith('/main.py'))]
assert all(old[p]==new[p] for p in preserved)
put('FULL_GIT_INPUTS_V2.json',{'scope':'Git-only fixed full non-progress input maps, not a runtime test','maps':maps,
 'total_bindings':sum(m['count'] for m in maps),'distinct_blobs':len(blobcache)})
put('SOURCE_BINDING_V2.json',{'base':BASE,'final':FINAL,'owned_paths':changed,'final_input_count':len(new),
 'unchanged_old_nonoverlap_inputs':len(unchanged),'source_maps':len(maps),
 'source_bindings':sum(m['count'] for m in maps),'distinct_blobs':len(blobcache),
 'fixed_first_red_green_test_binding':first_same,'first_red_green_full_test_bytes_equal':True,
 'de4_to_final_production_delta':de4delta,'final_production_paths_exact_same_as45':True,
 'preserved_original_types_and_contracts':[new[p] for p in preserved],
 'reviewer':'Implementation owner documentary verification; root independent review remains separate',
 'forbidden_actions':'No CLI/model/network/tool/host security probes or source mutation by this verifier',
 'live_check':'Final worktree clean at this documentary snapshot only'})
print(json.dumps({'final':FINAL,'maps':len(maps),'bindings':sum(m['count'] for m in maps),
 'distinct_blobs':len(blobcache),'unchanged_nonoverlap':len(unchanged),'changed_paths':len(changed)}))
