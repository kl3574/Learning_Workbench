from pathlib import Path
import hashlib, json, re, subprocess, sys
base=Path('$HOME/.cache/learning-workbench-acceptance')
producer=base/'m63-local-session-bootstrap-ui-evidence-oct03'
root=base/'m62-public-safe-oct02'
head='5d07c43851c84e4e1d8df12d7de52500293c1c3b'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
sys.path.insert(0,str(root/'scripts'))
from check_publication import inspect
raw=json.loads((producer/'RAW_MANIFEST.json').read_text())
safe=json.loads((producer/'SAFE_SHARE.json').read_text())
assert raw['count']==len(raw['files'])==safe['count']==len(safe['files'])==63
for item in raw['files']:
 data=(producer/item['path']).read_bytes()
 assert len(data)==item['bytes'] and sha(data)==item['sha256'],item['path']
for item in safe['files']:
 data=(producer/item['path']).read_bytes()
 public=(producer/'public-candidates'/item['path']).read_bytes()
 assert sha(data)==item['raw_sha256'] and sha(public)==item['public_sha256']
 assert public==data.replace(b'$HOME',b'$HOME')
 assert not inspect('progress/'+item['path'],public),item['path']
before=json.loads((producer/'fixed-5d07/before.json').read_text())
after=json.loads((producer/'fixed-5d07/after.json').read_text())
assert before==after and before['head']==head and before['count']==len(before['inputs'])==1369
assert before['status']=='' and before['all_equal'] is True
tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',head],cwd=root,text=True).splitlines()
tracked=[path for path in tracked if not path.startswith('progress/')]
assert set(tracked)=={item['path'] for item in before['inputs']}
for item in before['inputs']:
 blob=subprocess.check_output(['git','show',head+':'+item['path']],cwd=root)
 assert len(blob)==item['bytes'] and sha(blob)==item['sha256'] and item['git_equal'] is True,item['path']
logs={}
for label in ('20-full-web','21-strict','22-build'):
 receipt=json.loads((producer/('fixed-5d07/'+label+'.json')).read_text())
 assert receipt['head']==head and receipt['exit_code']==0 and receipt['node_version']=='v24.21.0'
 log=(producer/('fixed-5d07/'+label+'.log')).read_bytes()
 text=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',log.decode())
 if label=='20-full-web':
  assert re.search(r'Tests\s+1037 passed',text) and re.search(r'Test Files\s+145 passed',text)
 if label=='22-build':assert '849 modules transformed' in text
 logs[label]={'sha256':sha(log),'exit_code':0}
report={'status':'PASS_SCOPED_INDEPENDENT_READBACK','head':head,'raw_files':63,'explicit_public_files':63,
 'nonprogress_inputs':1369,'before_after_equal':True,'all_git_blobs_independently_checked':True,
 'full_web':'1037 PASS /145 files','strict':'PASS','build':'PASS /849 modules; existing chunk advisory',
 'logs':logs,'runner_source_limit':'Producer stage receipts and complete original before/after maps preserved. No separate producer runner.py saved; no fabricated script binding claimed.',
 'boundary':'Static UI/code and evidence readback only. Backend366 intermediate not accepted, no root execution of UI/CLI/native/model. Original full-gate failures and interrupted tasks remain.',
 'reviewed_ui_paths':['useBootstrap.ts','bootstrapCommands.ts','bootstrapMemory.ts','bootstrapClient.ts','CodexBootstrapPanel.tsx','AuthoringPanel.tsx','Shell.tsx'],
 'review_conclusion':'No additional static UI blocker found in reviewed original actor, explicit replay, late-ACK local reader save, scope fences, literal Shell label and retained dirty/safe predicates. Requires current backend/new native and integrated gate.'}
(Path(__file__).parent/'READBACK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('logs','reviewed_ui_paths')},ensure_ascii=False))
