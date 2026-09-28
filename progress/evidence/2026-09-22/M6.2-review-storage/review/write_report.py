from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path
import subprocess

base=Path(__file__).resolve().parent
paths=['migrations/0017_review_history.sql','tests/integration/test_review_storage_constraints.py','tests/integration/test_review_storage_migration.py','docs/adr/0023-review-history-storage.md']
pins={}
for label in ['source','fixed']:
    tree=base/label
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=tree,text=True).strip()
    inventory={}
    for p in paths:
        data=(tree/p).read_bytes()
        expected=subprocess.check_output(['git','show',head+':'+p],cwd=tree)
        assert data==expected
        target=base/'snapshots'/label/p
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
        inventory[p]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    pins[label]={'head':head,'files':inventory,'git_status':subprocess.check_output(['git','status','--short'],cwd=tree,text=True)}
    assert not pins[label]['git_status']
    assert subprocess.run(['git','diff','--quiet','16f4ae1355c4398a6b419b2fa883ec5211624c3d',head,'--','migrations/0001_baseline.sql','migrations/0016_draft_candidate_identities.sql','packages/contracts'],cwd=tree).returncode==0
spec=(base/'fixed'/'PRODUCT_DESIGN.md').read_bytes()
pins['spec']={'path':'PRODUCT_DESIGN.md','sha256':hashlib.sha256(spec).hexdigest(),'version':'3.0.7'}
(base/'source-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
summary={'reviewed_at':datetime.now(UTC).isoformat(),'initial_head':pins['source']['head'],'fixed_head':pins['fixed']['head'],
    'standards':{'open_findings':0},'spec':{'initial_findings':1,'resolved_findings':1,'open_findings':0},
    'initial_relation_probes':{'accepted_orphans':5,'copy_sanitation_pass':1},
    'fixed_relation_probes':{'rejected_orphans':5,'copy_sanitation_pass':1},
    'fixed_storage_tests':{'passed':99,'failed':0,'duration_seconds':2.44},
    'scope':'forward SQLite schema, migration, tests, short ADR; not Quality runtime or M6.2 completion',
    'not_run':['Quality owner/repository/worker/HTTP (not implemented by this slice)','production provider','numeric execution','M7 restore acceptance','full repository test suite by this reviewer']}
(base/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
report='''# Independent review — M6.2 review storage

Sole specification: PRODUCT_DESIGN.md 3.0.7; exact SHA is in source-pins.json. Applicable rules reviewed: owner boundaries, Job/Draft state and atomic history, exact candidate approval identity, quality levels, forward migrations and online backups, explicit human review endpoint, ReviewReceipt, baseline SQL JSON/permission caveat and M7 backup boundary. The storage candidate and ADR are engineering choices, not additional product specifications.

Initial reviewed source: `4b0296f3334d580f22fd95a9cede5c8edfcf4a77`. Independently rechecked fix: `e0b30f077cc760b8579f81939182f602cd5e992b`. Both are isolated clean detached worktrees. Four changed files match their actual Git blobs; 0001, 0016 and packages/contracts are unchanged from the authorized base `16f4ae1355c4398a6b419b2fa883ec5211624c3d`. The test runner records all 10,113 tracked-file hashes before/after each invocation and verifies no changes; generated caches are outside this inventory.

## Standards

No open finding. The change is a forward owner storage migration with real SQLite tests. It changes no core contract or applied predecessor migration. SQL fixtures are explicitly synthetic and are not described as application owner, human authority, machine execution or publication proof. No repository/worker/HTTP/Provider implementation is claimed. No production data, system permissions, timeout or source files were changed by this review.

## Spec

One initial relational finding is resolved in the reviewed fix. In original 0017 lines 104–117, command event existence was checked only by a BEFORE INSERT trigger. Existing job_events has no ordinary DELETE/UPDATE guard. A retained cancel command therefore survived deletion or renumbering of either referenced event while PRAGMA foreign_key_check returned no error. A create command could also name initial Job revision 1 after that event had been deleted. This was a gap in persistent command revision identity; it was not evidence that a protected production API had accepted a forged human review.

Independent actual SQLite probes at 4b0296f reproduced all five cases: cancel basis=1/result=2, with no create command sharing its event references, then separately DELETE and UPDATE each endpoint; plus create with missing initial event. Original observations and logs are preserved, never relabeled PASS. The fixed migration adds generated per-kind revision columns and composite foreign keys to Jobs events and retained Review revisions. At e0b30f0 the same five isolated probes all rejected the orphaning operations. Both event rows remained and foreign_key_check stayed empty.

No other open finding within this storage slice. Review Job identity binds actual Jobs id/workspace/draft_review kind and the complete immutable catalog source-kind and candidate identity. Revision predecessors bind the same review, adjacent number and exact retained receipt hash. Artifact bindings use actual artifact id/workspace/blob identity; the REPLACE guard covers ordinal primary key and separate artifact uniqueness even with recursive triggers disabled. Command routes bind the actual object, original actor/key/workspace remain append-only, and create/cancel remain representable before any ReviewReceipt exists. SQL validity and opaque owner labels do not authenticate current permissions, canonical hash correctness, event meaning, ACK shape or human decisions; those remain explicit future checked-port responsibilities.

## Actual verification

- e0b30f0: 99 committed storage/migration tests passed in 2.44 seconds; raw pytest output and command receipt retained.
- Independent relation probes: five original accepted orphans; five fixed rejections.
- Nonempty retained review history plus create/cancel commands survived a real online snapshot followed by NULL reviewer_session_id and DELETE local_sessions on the isolated copy; original receipt bytes/history/commands were unchanged and the live synthetic source still retained its session reference. This checks copy sanitation compatibility, not M7 restore acceptance.
- Committed migration tests independently rerun cover legacy receipt/Job byte preservation, empty newly added tables, 16→17 online backup, schema/index/migration-record rollback after deliberate invalid SQL, and the actual backup script's legacy reviewer cleanup.
- Source and test boundaries did not change during verification. SQLite runtime reported 3.53.1.

Quality application repository/worker/HTTP, real human approval, provider execution, numeric execution, publication and M7 restore acceptance were not run or inferred from this schema acceptance. Full-suite/old-related regression results executed by the implementing parent are not represented as this reviewer's own results. This report does not mark M6.2 complete.
'''
(base/'REPORT.md').write_text(report)
files=[]
for p in sorted(base.rglob('*')):
    if p.is_file() and not any(part in {'source','fixed'} for part in p.relative_to(base).parts[:1]) and p.name!='MANIFEST.json':
        data=p.read_bytes()
        files.append({'path':str(p.relative_to(base)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(base/'MANIFEST.json').write_text(json.dumps({'files':files},indent=2)+'\n')
for name in ['REPORT.md','summary.json','source-pins.json','MANIFEST.json']:
    p=base/name
    print(name,hashlib.sha256(p.read_bytes()).hexdigest())
print('manifest_files',len(files))
