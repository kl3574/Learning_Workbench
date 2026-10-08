import datetime,hashlib,importlib.util,json,subprocess
from pathlib import Path
B=Path('$HOME/.cache/learning-workbench-acceptance');R=B/'m62-public-safe-oct02';O=Path(__file__).parent;sha=lambda b:hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('public_package',B/'m62-v313-pushed-progress-sync-oct03/package.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
H='29e864a6157f3bb23c6ced5d1a2f34f77bf3b875';assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==H
assert not subprocess.check_output(['git','status','--porcelain'],cwd=R)
gates=[];maps=[]
for stage,logs in [('static',['ruff','mypy','generated','spec','full-web','strict','build']),('python',['full-python'])]:
 p=B/'m63-combined-dispatch-ui-gates-oct04'/stage
 d=json.loads((p/'GATES.json').read_text());assert d['head']==H and all(e['exit_code']==0 for e in d['gates'])
 before=(p/'before.json').read_bytes();assert before==(p/'after.json').read_bytes();mp=json.loads(before);assert mp['head']==H and mp['count']==1433
 for e in d['gates']:assert sha((p/(e['name']+'.log')).read_bytes())==e['log_sha256']
 tree={}
 for e in subprocess.check_output(['git','ls-tree','-rz',H],cwd=R).split(b'\0'):
  if not e:continue
  meta,path=e.split(b'\t',1)
  if not path.startswith(b'progress/'):tree[path.decode()]=meta.split()[2].decode()
 assert set(tree)==set(mp['files'])
 for name,row in mp['files'].items():
  raw=(R/name).read_bytes();assert row['git_blob']==tree[name] and sha(raw)==row['sha256'] and len(raw)==row['bytes']
  assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==tree[name]
 gates.append((stage,'m63-combined-dispatch-ui-gates-oct04',[stage+'/'+n for n in ['run.py','before.json','after.json','GATES.json']+[n+'.log' for n in logs]]));maps.append({'stage':stage,'head':H,'count':1433,'manifest_sha256':sha(before),'log_sha256':[e['log_sha256'] for e in d['gates']]})
plog=(B/'m63-combined-dispatch-ui-gates-oct04/python/full-python.log').read_text()
assert '4085 passed, 2 skipped, 2 warnings' in plog
N=B/'m63-native-formal-29e864a6-03-oct04/publication-candidates';a=json.loads((N/'allowlist.json').read_text());assert len(a['files'])==29
native=[('native-originals-and-qualified-terminal',str(N.relative_to(B)),[e['path'] for e in a['files']]+['allowlist.json']),('root-independent-readback','m63-native-generic-root-readback-oct04',['readback.py','READBACK.json','generic-git-readback.py','GENERIC_GIT_READBACK.json'])]
sync=[('actual-native-terminal-issue-sync','m63-native-terminal-running-python-Issue32-sync-oct04',['sync.py','issue-body.md','issue-patch.invocation.json','readback.json'])]
for groups in [gates,native,sync]:
 for alias,dirname,names in groups:
  for name in names:
   raw=(B/dirname/name).read_bytes();safe=raw.replace(b'$HOME',b'$HOME').replace(b'$RUNNER_HOME',b'$RUNNER_HOME');assert not m.inspect('progress/'+alias+'/'+name,safe),(dirname,name)
summary={'status':'ROOT_29E_ACTUAL_TERMINAL_GATES_AND_EXPLICIT_CANDIDATES_READBACK_PASS_NOT_INSTALLED','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':H,'maps':maps,'native':'130PASS/makeexit0, original wrapperexit1 preserved, actual5 generatedchanges qualified separately, canonical unchanged','original_failures':'All prior originalFAIL/interruption/root correction preserved, no blanket failure-cause claim','boundary':'Bounded structural/runtime checks only; productionfullproof missing,0modelrequests, numericalENVblocked, physicalBroker/wholeM6.3/AC21/academic acceptance incomplete. No sourcepush by this preparation.'}
(O/'READBACK.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(O/'GROUPS.json').write_text(json.dumps({'gates':gates,'native':native,'sync':sync},indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
