from pathlib import Path
import json,hashlib,importlib.util
O=Path(__file__).resolve().parent;B=O.parent
E=B/'m63-local73ad831-Issue32-PR56-actual-failures-sync-oct05'
def sha(b):return hashlib.sha256(b).hexdigest()
rows=[]
for name in ['identity','issue-before','pr-before','issue-write','issue-after','pr-write','pr-after']:
 c=json.loads((E/(name+'-command.json')).read_bytes());r=json.loads((E/(name+'-receipt.json')).read_bytes())
 raw=(E/(name+'.stdout')).read_bytes();err=(E/(name+'.stderr')).read_bytes()
 assert r['exit_code']==0 and r['stdout_sha256']==sha(raw) and r['stderr_sha256']==sha(err)
 rows.append({'name':name,'command':c,'receipt':r})
i=json.loads((E/'issue-before.stdout').read_bytes());ia=json.loads((E/'issue-after.stdout').read_bytes())
p=json.loads((E/'pr-before.stdout').read_bytes());pa=json.loads((E/'pr-after.stdout').read_bytes())
for key in ['number','title','state','labels','milestone','assignees']:assert i[key]==ia[key]
for key in ['title','draft','state','merged_at','base','head']:assert p[key]==pa[key]
assert pa['draft'] and pa['state']=='open' and pa['merged_at'] is None and pa['head']['sha']=='1e7ad7a8656c0dc8373d4181fa3002f385ed1847'
begin,end='<!-- engineering_progress:start -->','<!-- engineering_progress:end -->'
assert i['body'].split(begin)[0]==ia['body'].split(begin)[0] and i['body'].split(end)[1]==ia['body'].split(end)[1]
assert ia['body']==(E/'issue-body.md').read_text() and pa['body']==(E/'pr-body.md').read_text()
assert sha(ia['body'].encode())=='77fb50ac69ac6fd19e7f05b3e08cf85146dea169fef157f6db9ded800ec29d6d'
assert sha(pa['body'].encode())=='8d518336200def21a099f23299fcb8e96f87cd3fd334f48068aece5b6692de7e'
readback=json.loads((E/'READBACK.json').read_bytes())
assert readback['local_unpushed_head']=='73ad831d5a1617e1ad478fb5371c1ae04b27c299' and readback['snapshot_sequence']==83
(O/'GOVERNANCE_ROOT_ADMISSION.json').write_text(json.dumps({'role':'root independent exact seven original actual commands/stdout/stderr/receipts and guarded body readback; no new remote operation',
 'actual_recorded_utc':readback['recorded_utc'],'commands':rows,'issue_body_sha256':sha(ia['body'].encode()),'pr_body_sha256':sha(pa['body'].encode()),
 'issue_unmanaged_preserved':True,'draft_open_unmerged':True,
 'timing_limit':'Original23:55 snapshot83 pushintegration and complete68Python RUNNING remain immutable; later86/all68terminal reported separately',
 'excluded':'Original full API stdout contains unrelated identity/metadata and is private; only raw byte hash receipts, exact requested body texts and selected verification admitted',
 'current_sourcepush':'NOT_RUN; this is original earlier body sync only','model_calls':0},ensure_ascii=False,indent=2)+'\n')
sp=importlib.util.spec_from_file_location('helper',B/'m63-412abe-progress-checkpoint-oct05/package-helper-archived.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
names=['sync.py','READBACK.json','LOCAL_RECORD_READBACK.json','issue-body.md','pr-body.md']+[n+x for n in ['identity','issue-before','pr-before','issue-write','issue-after','pr-write','pr-after'] for x in ['-command.json','-receipt.json']]
path=h.package('M6.3-original-local73ad-actual-managed-body-sync-and-documentary-commit-readback',[
 ('original-body-sync','m63-local73ad831-Issue32-PR56-actual-failures-sync-oct05',names),
 ('original-stage','m63-interrupt68a-documentary-stage-corrected-oct05',['stage.py','SELECTION.json','READBACK.json','staged-publication-command.json','staged-publication-receipt.json','staged-publication.stdout','staged-publication.stderr']),
 ('original-documentary-commit','m63-interrupt68a-documentary-commit-corrected-oct05',['commit.py','command.json','receipt.json','READBACK.json']),
 ('root-independent','m63-broker6f-progress-checkpoint-oct05',['install-governance.py','GOVERNANCE_ROOT_ADMISSION.json'])],
 {'scope':'Earlier original23:55 body sync and actual416path documentary73ad commit; original statuses notbackdated',
 'public_head_then':'1e7ad7a8656c0dc8373d4181fa3002f385ed1847','local_then':'73ad831d5a1617e1ad478fb5371c1ae04b27c299',
 'actual_body_exact':True,'issue_unmanaged_preserved':True,'PR_draft_open_unmerged':True,'snapshot_then':83,
 'later_terminal':'Recorded separately in terminal86 and complete68 packets','sourcepush_merge_release_deploy':False,'model_calls':0})
(O/'GOVERNANCE_INSTALL_READBACK.json').write_text(json.dumps({'governance_evidence':path},indent=2)+'\n')
print('Archived original actual managed sync and fixed documentary-stage/commit receipts; historical running statuses preserved.')
