from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path
import subprocess
base=Path(__file__).resolve().parent
repo=base/'fixed'
previous='e0b30f077cc760b8579f81939182f602cd5e992b'
final='4bf176de1cdf0a76cdf0fa965027ec3a5367551f'
changed=subprocess.check_output(['git','diff','--name-only',previous,final],cwd=repo,text=True).splitlines()
assert changed==['tests/integration/test_review_storage_constraints.py']
for p in ['migrations/0017_review_history.sql','docs/adr/0023-review-history-storage.md','tests/integration/test_review_storage_migration.py']:
    assert subprocess.check_output(['git','show',previous+':'+p],cwd=repo)==subprocess.check_output(['git','show',final+':'+p],cwd=repo)
diff=subprocess.check_output(['git','diff',previous,final,'--',changed[0]],cwd=repo)
(base/'final-test-only.diff').write_bytes(diff)
raw=subprocess.check_output(['git','show',final+':'+changed[0]],cwd=repo)
target=base/'snapshots'/'final'/changed[0]
target.parent.mkdir(parents=True,exist_ok=True)
target.write_bytes(raw)
receipt={'reviewed_at':datetime.now(UTC).isoformat(),'previous_head':previous,'final_head':final,'changed_files':changed,
    'final_test_sha256':hashlib.sha256(raw).hexdigest(),'diff_sha256':hashlib.sha256(diff).hexdigest(),
    'migration_adr_other_test_bytes_unchanged':True,'review_result':'PASS read-only test-diff review',
    'actual_test_execution':'Independent 99-case run remains attributed only to e0b30f0. Final 101-case run belongs to implementing parent, not rerun or inferred here.'}
(base/'final-test-only.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
summary=json.loads((base/'summary.json').read_text())
summary['final_test_only_head']=final
summary['final_test_only_review']='PASS; implementation bytes unchanged, test execution not reattributed'
(base/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with (base/'REPORT.md').open('a') as stream:
    stream.write('''
## Final test-only follow-up

Read-only review of `4bf176de1cdf0a76cdf0fa965027ec3a5367551f` against e0b30f0 confirms exactly one changed test file; migration, ADR and migration-test bytes are identical. The permanent relational mutation case now separately targets create event 1, cancel basis 1 and cancel result 2, each with DELETE and UPDATE. The cancel fixture creates only its own command, with distinct basis/result, so the two foreign keys cannot cover for one another. UPDATE moves the selected sequence by 10, avoiding a primary-key collision with the other retained event. No additional finding. The independent 99-case test receipt remains attributed to e0b30f0; the parent's final 101-case run is not claimed as independently executed here. Old-related suites were not rerun by this reviewer.
''')
files=[]
for p in sorted(base.rglob('*')):
    if p.is_file() and not any(part in {'source','fixed'} for part in p.relative_to(base).parts[:1]) and p.name!='MANIFEST.json':
        data=p.read_bytes()
        files.append({'path':str(p.relative_to(base)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(base/'MANIFEST.json').write_text(json.dumps({'files':files},indent=2)+'\n')
for entry in files:
    p=base/entry['path']
    assert p.stat().st_size==entry['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']
for name in ['REPORT.md','summary.json','MANIFEST.json']:
    print(name,hashlib.sha256((base/name).read_bytes()).hexdigest())
print('manifest_files',len(files),'hash_replay PASS')
