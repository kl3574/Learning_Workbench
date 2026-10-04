from pathlib import Path
import json,hashlib,subprocess,sys
root=Path.cwd(); out=Path(sys.argv[1])
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(); base='cc2cc675f91a2794c44267e46687422d5ae50019'
paths=subprocess.check_output(['git','diff','--name-only',base,head,'--',':!progress'],text=True).splitlines()
keep=['services/api/app/application/codex_turn_models.py','services/api/app/application/codex_turn_execution_models.py','services/api/app/application/codex_approval_models.py','services/api/app/application/provider_codex_profile.py','services/api/app/application/provider_codex_execution.py','services/api/app/codex_bootstrap_dto.py','packages/contracts/domain_models.py','migrations/0001_baseline.sql','tests/integration/test_codex_turn_interrupt_http.py','PRODUCT_DESIGN.md']
records={p:{'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest(),'same_as_base':(root/p).read_bytes()==subprocess.check_output(['git','show',base+':'+p])} for p in keep}
coverage=json.loads((root/'packages/contracts/generated/runtime-route-coverage.json').read_text())
registered=coverage['registered_operations']; absent=coverage['not_registered_operations']
assert not set(registered)&set(absent)
value={'base':base,'head':head,'production_head':'1b49cb6870f2b8e89337ddd26da82b5e46391e75','changed_paths':paths,'unchanged_boundaries':records,'registered':len(registered),'declared':len(set(registered)|set(absent)),'unregistered':len(absent),'tool_versions':{'python':'3.12.13','uv':'0.11.21','node':'24.21.0'},'scope':'HTTP control and synthetic local protocol only; no CLI interrupt execution or host resource guarantee'}
old=json.loads(subprocess.check_output(['git','show',base+':packages/contracts/generated/openapi.json']))
new=json.loads((root/'packages/contracts/generated/openapi.json').read_text())
value['openapi']={'prior_paths_unchanged':all(new['paths'][k]==v for k,v in old['paths'].items()),'prior_components_unchanged':all(new['components']['schemas'][k]==v for k,v in old['components']['schemas'].items()),'added_paths':sorted(set(new['paths'])-set(old['paths'])),'added_models':sorted(set(new['components']['schemas'])-set(old['components']['schemas']))}
(out/'SOURCE_BINDING.json').write_text(json.dumps(value,indent=2)+'\n')
print({k:value[k] for k in ('registered','declared','unregistered')}); print('unchanged boundaries',all(v['same_as_base'] for v in records.values()))
