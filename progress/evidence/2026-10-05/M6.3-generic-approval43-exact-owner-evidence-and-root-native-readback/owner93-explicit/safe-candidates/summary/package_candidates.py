"""Copy only the manually reviewed names below; never recurse runtime directories."""
import hashlib, json, os
from pathlib import Path
os.umask(0o077)
out=Path(__file__).parent
cache=out.parent
source=cache/'m63-generic-approval-safe-decline-oct05'
candidate=out/'safe-candidates'
candidate.mkdir(mode=0o700)
entries=[]
def sha(b): return hashlib.sha256(b).hexdigest()
def add(p, name, reason):
    raw=p.read_bytes()
    if p.suffix=='.png': data=raw; transformation='identity PNG bytes'
    else:
        raw.decode('utf-8')
        data=raw.replace(b'<LOCAL_HOME>',b'<LOCAL_HOME>')
        transformation='only <LOCAL_HOME> -> <LOCAL_HOME>' if raw!=data else 'identity UTF-8 bytes (no home prefix present)'
    target=candidate/name; target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data)
    assert target.read_bytes()==data
    entries.append({'raw_path':str(p).replace('<LOCAL_HOME>','<LOCAL_HOME>'),'candidate_path':name,'raw_sha256':sha(raw),'candidate_sha256':sha(data),'raw_bytes':len(raw),'candidate_bytes':len(data),'transformation':transformation,'manual_basis':reason})
for name in ['REPORT.md','FINAL_BINDING.json','QUALIFICATIONS.json','PREFLIGHT_FAILURE.json','FULL_GIT_MANIFESTS.json','GATE_BINDINGS.json','NATIVE_BINDINGS.json','owner-delta.patch','p2-delta.patch','run.py','seal.py','package_candidates.py']:
    add(out/name,'summary/'+name,'Authored fixed source/evidence summary, hashes, paths or replay code; no private runtime material.')
binding=json.loads((out/'FINAL_BINDING.json').read_text())
for name in binding['owner_delta_paths']:
    add(source/name,'source/'+name,'Exact11 owned application/adapter/synthetic-test files; actual fixture credentials are not embedded.')
for stage in ['closure-full-web','closure-strict','closure-build','closure-spec','red-safe-decline-02','green-safe-decline']:
    for name in ['source-before.json','source-after.json','command.json','receipt.json']:
        add(out/stage/name,'gates/'+stage+'/'+name,'Complete fixed Git input metadata/command/result; no runtime data contents.')
    if stage!='red-safe-decline-02':
        add(out/stage/'run.log','gates/'+stage+'/run.log','Manually checked successful synthetic test/static/build log; failure logs deliberately excluded.')
old=cache/'m63-generic-approval-ui-evidence-oct05'
add(old/'ERRATUM_SAFE_DECLINE.json','historical/ERRATUM_SAFE_DECLINE.json','Original9e scope qualification preserved unchanged except optional home prefix.')
for label,dirname,passed,pictures in [
    ('final-positive','m63-generic-approval-native-43c70-oct05',True,['complete-memory-operation-1440.png','complete-memory-operation-390.png','independent-completed-original-ack-1440.png','independent-completed-original-ack-390.png','learner-safe-decline-empty-registry-1440.png','learner-safe-decline-empty-registry-390.png']),
    ('counter-green','m63-generic-approval-safe-decline-native-43c70-oct05',True,['safe-decline-after-actual-403-1440.png','safe-decline-after-actual-403-390.png']),
    ('counter-red','m63-generic-approval-safe-decline-native-red-oct05',False,['safe-decline-after-actual-403-1440.png','safe-decline-after-actual-403-390.png'])]:
    p=cache/dirname
    names=['native.mjs','controlled_api.py','run.py','before.json','terminal-source.json','command.json','run-receipt.json']
    if passed: names+=['after.json','receipt.json','run.log']
    if label!='final-positive': names+=['counter-observation.json']
    if not passed: names+=['failure.json']
    for name in names:
        add(p/name,'native/'+label+'/'+name,'Named inspected harness/receipt/complete Git metadata; cookies/CSRF are runtime reads in code, never values in these files.')
    for name in pictures:
        add(p/name,'native/'+label+'/'+name,'Visually inspected synthetic UI viewport; no credentials/private material; exact original PNG bytes.')
assert len({e['candidate_path'] for e in entries})==len(entries)
manifest={'source_sha':binding['source_sha'],'status':'EXPLICIT_MANUALLY_REVIEWED_CANDIDATES_NOT_PUBLISHED','entries':entries,'excluded':['all raw failed run.log files','private-paths.json','private-fixture.json','cookies and CSRF values','DB/SQLite/WAL/SHM','browser profile/cache','keys/credentials','TMPDIR contents','ZIP/archive contents'],'transformation_policy':'Text: only exact <LOCAL_HOME> -> <LOCAL_HOME>. PNG: identity. No truncation, rewrite or secret-pattern filtering.','review_boundary':'Content candidate review only; root independently decides publication. Prior failure summaries and9e erratum must accompany final fixed claims.'}
(out/'PUBLIC_CANDIDATES.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
for e in entries:
    assert sha((candidate/e['candidate_path']).read_bytes())==e['candidate_sha256']
seal={'source_sha':binding['source_sha'],'candidate_count':len(entries),'png_count':sum(e['candidate_path'].endswith('.png') for e in entries),'readback':'All candidate bytes re-read and hashes checked; all raw files re-read, only declared transformation reproduced.','outer':{n:sha((out/n).read_bytes()) for n in ['PUBLIC_CANDIDATES.json','REPORT.md','FINAL_BINDING.json','FULL_GIT_MANIFESTS.json','GATE_BINDINGS.json','NATIVE_BINDINGS.json','QUALIFICATIONS.json','run.py','seal.py','package_candidates.py']}}
for e in entries:
    p=Path(e['raw_path'].replace('<LOCAL_HOME>','<LOCAL_HOME>')); raw=p.read_bytes()
    assert sha(raw)==e['raw_sha256']
    expected=raw if p.suffix=='.png' else raw.replace(b'<LOCAL_HOME>',b'<LOCAL_HOME>')
    assert expected==(candidate/e['candidate_path']).read_bytes()
(out/'PACKAGE_SEAL.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps(seal,indent=2))
