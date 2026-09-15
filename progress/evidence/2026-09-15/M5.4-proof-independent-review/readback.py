"""Read-only evidence/file verification; never imports or executes product/tests."""
from pathlib import Path
import json,hashlib,ast
from datetime import datetime,UTC
A=Path(__file__).parent;P=Path('[LOCAL_HOME]/.cache/learning-workbench-acceptance/m54-proof-binding-implementation-v1');R=Path('[LOCAL_HOME]/.cache/learning-workbench-acceptance/m54-active')
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((P/'final-receipt.json').read_text());out={'observed_at':datetime.now(UTC).isoformat(),'tests_executed_by_reviewer':False,'sources':[],'run_records':[],'same_test_functions':[]}
for f in r['owned_sources']:
 p=Path(f['path']);assert h(p)==f['sha256'];out['sources'].append({'path':f['relative_path'],'sha256':h(p),'bytes':p.stat().st_size})
for name in ['PRODUCT_DESIGN.md','docs/adr/0019-provider-proof-bindings.md','services/api/app/main.py','services/api/app/infrastructure/provider_network.py','services/api/app/application/consents.py','services/api/app/application/provider_dispatch.py']:
 p=R/name;out['sources'].append({'path':name,'sha256':h(p),'bytes':p.stat().st_size})
assert h(R/'PRODUCT_DESIGN.md')=='2bfd471933be478a7cac51363a0482a87c81ec113c3e6cbdec88cfd139d43f37'
for x in r['runs']:
 for k in ['receipt','log']:assert h(Path(x[k]['path']))==x[k]['sha256']
 d=json.loads(Path(x['receipt']['path']).read_text());assert d['exit_code']==x['exit_code'];assert d['before']==d['after']
 log=Path(x['log']['path']).read_text();out['run_records'].append({'name':x['name'],'receipt_sha256':x['receipt']['sha256'],'log_sha256':x['log']['sha256'],'exit_code':d['exit_code'],'listed_inputs_count':len(d['before']),'listed_inputs_equal':True,'summaries':[s for s in log.splitlines() if ' passed' in s or ' failed' in s or 'All checks' in s or 'Success:' in s]})
for c in r['red_green_test_binding']:
 seg=[]
 for label in ['red_test_file','green_test_file']:
  p=Path(c[label]['path']);assert h(p)==c[label]['sha256'];s=p.read_text();n=next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name==c['test']);seg.append(ast.get_source_segment(s,n).encode())
 assert seg[0]==seg[1] and hashlib.sha256(seg[0]).hexdigest()==c['test_function_sha256']
 out['same_test_functions'].append({'name':c['test'],'sha256':c['test_function_sha256'],'method':'ast.get_source_segment; excludes decorator and trailing final LF, exactly B declared extraction','equal':True,'entire_file_equal':c['same_entire_test_file']})
f=json.loads((P/'existing-targets-12/receipt.json').read_text());assert all(f['before'][x['path']]==x['sha256'] for x in out['sources'][:7]);out['seven_sources_match_actual_80_pass_scope']=True
out['reviewer_readback_attempt_note']='An earlier inline comparison included the trailing final LF and asserted against B AST segment SHA, failing after all 15 run records and 7 sources had matched. Exact declared AST extraction above now matches all 4 pairs; no product test or source was changed.'
(A/'evidence-readback.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS readonly evidence readback:',len(out['sources']),'files,',len(out['run_records']),'owner runs,',len(out['same_test_functions']),'same-body pairs')
