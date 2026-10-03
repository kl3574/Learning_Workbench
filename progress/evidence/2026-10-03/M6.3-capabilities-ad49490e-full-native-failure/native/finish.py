import json,hashlib,pathlib,subprocess,re,datetime
base=pathlib.Path('$HOME/.cache/learning-workbench-acceptance')
root=base/'m63-capabilities-full-native-ad49490e-oct03';ev=pathlib.Path(__file__).parent;stage=ev/'native-full'
sha=lambda data:hashlib.sha256(data).hexdigest()
receipt=json.loads((stage/'receipt.json').read_text());log=(stage/'run.log').read_text()
assert sha((stage/'run.log').read_bytes())==receipt['log_sha256']
before=json.loads((stage/'before.json').read_text());after=json.loads((stage/'after.json').read_text())
b={x['path']:x for x in before};a={x['path']:x for x in after};assert b.keys()==a.keys()
changed=[p for p in b if b[p]!=a[p]]
allowed={'docs/ui/m1-after-1440.png','docs/ui/m1-after-1920.png','docs/ui/m1-after-390-agent.png','docs/ui/m1-native-zoom-metrics.json','docs/ui/m1-session-three-way-conflict.png'}
assert set(changed)<=allowed,changed
rows=[]
for p in changed:
 original=subprocess.check_output(['git','show','HEAD:'+p],cwd=root);produced=(root/p).read_bytes()
 assert sha(original)==b[p]['sha256'] and sha(produced)==a[p]['sha256']
 target=ev/'changed-tracked-ui'/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(produced)
 (root/p).write_bytes(original);assert sha((root/p).read_bytes())==b[p]['sha256']
 rows.append({'path':p,'original_sha256':sha(original),'produced_sha256':sha(produced),'restored':True})
status=subprocess.check_output(['git','status','--short'],cwd=root,text=True);assert not status,status
count=re.findall(r'^\s+(\d+) passed \(([^)]*)\)',log,re.M)
result={'source':receipt['head'],'original_capture_unchanged':receipt['unchanged'],'expected_generated_ui_outputs':rows,'other_inputs_unchanged':len(before)-len(changed),'tracked_tree_restored_by_exact_git_bytes':True,'runner_summary':count[-1] if count else None,'native_exit':receipt['exit_code'],'prior60faFAIL_preserved':True,'prior0bFAIL_preserved':True}
(ev/'native-output-preservation.json').write_text(json.dumps(result,indent=2)+'\n')
actual=[]
for name in ['restore-numeric-actual.json','single-publication-actual.json']:
 files=list((stage/'artifacts').rglob(name));assert len(files)==1,(name,len(files))
 f=files[0];j=json.loads(f.read_text())
 actual.append({'path':str(f.relative_to(ev)),'sha256':sha(f.read_bytes()),'top_level_keys':list(j)})
root_result={'source':receipt['head'],'source_inputs':len(before),'native_result':result,'actual_numeric_artifacts':actual,'started_at':receipt['started_at'],'finished_at':receipt['finished_at'],'time_boundary':'Raw UTC timestamps are retained independently of the runner-reported duration; no duration is inferred by subtracting them.','source_push':False}
(ev/'root-terminal-readback.json').write_text(json.dumps(root_result,indent=2)+'\n')
print(json.dumps(root_result,ensure_ascii=False))
