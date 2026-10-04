"""Read fixed Git objects and named evidence. No runtime directory collection."""
import hashlib, io, json, os, subprocess
from pathlib import Path
out = Path(__file__).parent
cache = out.parent
root = cache / 'm63-generic-approval-safe-decline-oct05'
old = cache / 'm63-generic-approval-ui-evidence-oct05'
head = '43c70d660d98904903bd607a4661b3b95710293e'
baseline = '412abe09c519104d9dbd2b360eed3ff4f897f829'
prior = '9e4ce1bab62d23cef0ef3f3354fa606ee62d090b'
def git(*args): return subprocess.check_output(['git', *args], cwd=root)
def sha(data): return hashlib.sha256(data).hexdigest()
def read(p): return json.loads(p.read_text())
def write(name, value): (out/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
assert git('rev-parse','HEAD').decode().strip() == head and git('status','--porcelain') == b''
stages = [(old, s) for s in ['red-wire','green-wire','red-panel','green-panel','first-strict','expanded-focused','full-web','strict','build','localtask-observation','full-web-02','turnpanel-observation','combined-full-web','combined-strict','combined-build','combined-spec']]
stages += [(out, s) for s in ['red-safe-decline-02','green-safe-decline','fixed-build','final-full-web','final-strict','final-build','final-spec','closure-full-web','closure-strict','closure-build','closure-spec']]
heads = {head, baseline, prior, '8f2c884510aef987b80ae62a018c33c83d89388c'}
bindings = []
for base, stage in stages:
    p=base/stage; r=read(p/'receipt.json'); before=read(p/'source-before.json'); after=read(p/'source-after.json')
    assert before==after and r['before_after_exact'] and before['status']==''
    assert all(v['matches_git'] for v in before['files'])
    assert sha((p/'run.log').read_bytes())==r['log_sha256']
    assert sha((base/'run.py').read_bytes())==r['runner_sha256']
    for path, digest in r['test_sources'].items(): assert sha(git('show',r['source_sha']+':'+path))==digest
    heads.add(r['source_sha'])
    bindings.append({'directory':str(p), 'stage':stage, 'receipt':r, 'files':{n:sha((p/n).read_bytes()) for n in ['receipt.json','source-before.json','source-after.json','command.json','run.log']}})
maps={}; oids=set()
for h in sorted(heads):
    rows=[]
    for row in git('ls-tree','-rz',h).split(b'\0'):
        if not row: continue
        meta,path=row.split(b'\t'); mode,kind,oid=meta.decode().split(); path=path.decode()
        if kind!='blob' or path.startswith('progress/'): continue
        rows.append({'path':path,'mode':mode,'type':kind,'git_blob':oid}); oids.add(oid)
    maps[h]=rows
stream=io.BytesIO(subprocess.check_output(['git','cat-file','--batch'],cwd=root,input=''.join(o+'\n' for o in sorted(oids)).encode()))
objects={}
for expected in sorted(oids):
    oid,kind,size=stream.readline().decode().split(); data=stream.read(int(size))
    assert stream.read(1)==b'\n' and oid==expected and kind=='blob'
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid
    objects[oid]={'sha256':sha(data),'bytes':len(data)}
assert stream.read()==b''
for rows in maps.values():
    for row in rows: row.update(objects[row['git_blob']])
for base,stage in stages:
    snap=read(base/stage/'source-before.json')
    fixed={r['path']:r for r in maps[snap['head']]}
    assert set(fixed)=={r['path'] for r in snap['files']}
    for row in snap['files']:
        for field in ['mode','type','git_blob','bytes','sha256']: assert row[field]==fixed[row['path']][field]
for row in maps[head]:
    p=root/row['path']; data=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes()
    assert sha(data)==row['sha256']
changed=git('diff','--name-only',baseline,head).decode().splitlines()
p2changed=git('diff','--name-only',prior,head).decode().splitlines()
assert len(changed)==11 and len(p2changed)==3
basefiles={r['path']:r for r in maps[baseline]}; final={r['path']:r for r in maps[head]}
preserved=[p for p in basefiles if p not in changed]
assert all(basefiles[p]==final[p] for p in preserved)
native=[]
for label,dirname,expected,passed in [
    ('prior_positive','m63-generic-approval-native-9e4ce-oct05',prior,True),
    ('p2_red','m63-generic-approval-safe-decline-native-red-oct05',prior,False),
    ('p2_green','m63-generic-approval-safe-decline-native-43c70-oct05',head,True),
    ('final_positive','m63-generic-approval-native-43c70-oct05',head,True)]:
    p=cache/dirname; r=read(p/'run-receipt.json'); before=read(p/'before.json'); terminal=read(p/'terminal-source.json')
    assert before==terminal and before['head']==expected and before['count']==len(maps[expected])
    assert (r['exit_code']==0)==passed and sha((p/'run.log').read_bytes())==r['log_sha256']
    for name,digest in r['harness'].items(): assert sha((p/name).read_bytes())==digest
    fixed={f['path']:f for f in maps[expected]}
    assert set(fixed)==set(before['files'])
    for path,row in before['files'].items(): assert all(row[k]==fixed[path][k] for k in ['mode','type','git_blob','bytes','sha256'])
    if passed:
        assert before==read(p/'after.json')
        facts=read(p/'receipt.json')
        for picture in facts['screenshots']: assert sha((p/picture['file']).read_bytes())==picture['sha256']
    else:
        assert not (p/'after.json').exists() and not (p/'receipt.json').exists()
        facts=read(p/'counter-observation.json')
    names=['before.json','terminal-source.json','command.json','run-receipt.json','run.log','native.mjs','controlled_api.py','run.py']
    names += ['after.json','receipt.json'] if passed else ['counter-observation.json','failure.json']
    native.append({'label':label,'directory':str(p),'run':r,'facts':facts,'files':{n:sha((p/n).read_bytes()) for n in names}})
red=cache/'m63-generic-approval-safe-decline-native-red-oct05'
green=cache/'m63-generic-approval-safe-decline-native-43c70-oct05'
assert all((red/n).read_bytes()==(green/n).read_bytes() for n in ['native.mjs','controlled_api.py','run.py'])
assert (out/'red-safe-decline-02/CodexApprovalsPanel.test.tsx').read_bytes()==(out/'green-safe-decline/CodexApprovalsPanel.test.tsx').read_bytes()
write('FULL_GIT_MANIFESTS.json',{'heads':maps,'complete_git_blobs_read':len(objects),'head_count':len(maps),'boundary':'All listed nonprogress tracked Git blobs fully read and SHA1/SHA256 verified; no runtime profile/DB/cache collection.'})
write('GATE_BINDINGS.json',bindings)
write('NATIVE_BINDINGS.json',native)
(out/'owner-delta.patch').write_bytes(git('diff','--binary',baseline,head))
(out/'p2-delta.patch').write_bytes(git('diff','--binary',prior,head))
write('FINAL_BINDING.json',{'source_sha':head,'parent_shas':git('show','-s','--format=%P',head).decode().strip().split(),'review_base':baseline,'p2_base':prior,'source_tree':str(root),'spec_sha256':sha(git('show',head+':PRODUCT_DESIGN.md')),'clean':True,'owner_delta_paths':changed,'p2_delta_paths':p2changed,'complete_nonprogress_inputs':len(maps[head]),'unchanged_base_paths':len(preserved),'owned_tests':40,'full_web_tests':1399,'full_web_files':166,'all_stage_source_pairs':len(stages),'native_runs':len(native),'same_byte_counter_harness':True,'same_byte_component_red_green':True,'original_evidence_unchanged':True,'independent_final_closure':'PENDING_ROOT_REVIEW'})
write('QUALIFICATIONS.json',{'prior':read(old/'QUALIFICATIONS.json'),'prior_erratum':read(old/'ERRATUM_SAFE_DECLINE.json'),'p2':{'finding':'SAFE_DECLINE_BLOCKED_BY_PRIOR_APPROVE_COMMAND','component_red':'29fc: 3 FAIL/19 PASS; actual disabled buttons after saved approve under learner/independent/open_book','same_file_green':'11a: 38 PASS (3 files), same complete component source as29fc','additional_final_cases':'43: saved unknown approve remains unchanged while safe decline is new; reverse negative retains new approve block for unknown prior decline','native_red':'9e actual approve403/pendingr1/prior original retained/decline disabled, exit1','native_green':'43 exact same three harness bytes: actual403/pendingr1/decline enabled; explicit new key/full safe basis; old complete journal unchanged; 1 memory request and zero literal operation','narrow_fix':'Only decline ignores prior approve; new approve and original approve replay admission retain original rules. No backend change.','final_test_file_qualification':'Final43 adds unknown-approve and reverse-negative cases; whole final component file is not claimed byte-equal to29fc. RED29fc and GREEN11a complete files are byte-equal.'},'preflight':read(out/'PREFLIGHT_FAILURE.json'),'native_replay_environment':'Counter run.py expects SOURCE_TREE=run-receipt.cwd and SOURCE_SHA=run-receipt.source_sha. These values were actual environment; raw command receipts store equivalent cwd/source fields but do not separately enumerate both variable names.','publication':'Candidates only, not publication. Raw failure logs stay private; share hashes and fixed summaries. No DB/cookies/fixture/profile/cache/keys/tmp/ZIP.','final_scope':'40 owned Web tests; full1399; structural spec; two bounded native runs on final43, not entire platform or real provider/CLI/host acceptance.'})
print(json.dumps({'source':head,'heads':len(maps),'blobs_fully_read':len(objects),'inputs':len(maps[head]),'preserved':len(preserved),'gate_pairs':len(stages),'native':len(native)}))
