"""Keep the failed scan, publish only declared symbolic directory prefixes."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

base=Path('$HOME/.cache/learning-workbench-acceptance')
root=base/'m62-public-safe-oct02'
out=Path(__file__).parent
assert not (out/'PREFIX_CORRECTION.json').exists()
sha=lambda b:hashlib.sha256(b).hexdigest()
original=json.loads((out/'staged-publication-scan-receipt.json').read_text())
assert original['exit_code']==1
sys.path.insert(0,str(root/'scripts'))
from progress import read_state,save
from check_publication import inspect
before=(root/'progress/state.json').read_bytes()
(out/'state-before-prefix-correction.private.json').write_bytes(before)
assert b'$RUNNER_HOME' not in before and before.count(b'$HOME')==19
state=json.loads(before.replace(b'$HOME',b'$HOME'))
state['verification']['m6_3_doc486_original_publication_scan_failure']={
    'original_exit_code':1,'scope':'state/CURRENT nineteen local-directory JSON fields; no credential-like field found',
    'correction':'Exact /home prefix converted to symbolic HOME only; original private progress bytes retained separately. Original scanner receipt is unchanged.',
    'original_stdout_sha256':original['stdout_sha256'],'subsequent_check':'SEPARATE_ACTUAL_RECEIPT_REQUIRED',
    'wholeM6_3':'NOT_ACCEPTED'}
save(state)
after=(root/'progress/state.json').read_bytes()
assert not inspect('progress/state.json',after)
(out/'PREFIX_CORRECTION.json').write_text(json.dumps({'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'original_scan_exit_code':1,'before_state_sha256':sha(before),'after_state_sha256':sha(after),
    'replaced_occurrences':19,'change':'Exact personal home prefix only plus a scoped original failure record.',
    'private_original_state_excluded':True,'original_scan_receipt_sha256':sha((out/'staged-publication-scan-receipt.json').read_bytes())},indent=2)+'\n')
namespace={}
exec((base/'m63-412abe-progress-checkpoint-oct05/package-helper-archived.py').read_text(),namespace)
evidence=namespace['package']('M6.3-doc486-original-publication-path-scan-failure-and-symbolic-prefix-correction',
    [('documentary',out.name,['correct-prefix.py','staged-publication-scan-command.json','staged-publication-scan.stdout',
    'staged-publication-scan.stderr','staged-publication-scan-receipt.json','PREFIX_CORRECTION.json'])],
    {'status':'ORIGINAL_BOUNDED_STAGED_SCAN_EXIT1_RETAINED_PERSONAL_DIRECTORY_PREFIX_CORRECTED',
     'source':'4869393654446c1dfcb0da97b9dca5fa7429b36f',
     'boundary':'Original scanner stopped only currentstate/CURRENT personalabsolute paths, nineteen fields, zero credential-like fields; no upload occurred. Exact HOME substitution only; private originalstate retained/excluded. Final stagedscan/M0structure check require separate receipts. Not product test or wholephase acceptance.'})
state=read_state();task=next(t for t in state['tasks'] if t['id']=='M6.3')
task['evidence_paths'].append(evidence)
state['verification']['m6_3_doc486_original_publication_scan_failure']['evidence']=evidence
save(state)
def run(label,argv):
    assert not (out/(label+'-command.json')).exists()
    (out/(label+'-command.json')).write_text(json.dumps({'argv':argv,'cwd':str(root),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
    r=subprocess.run(argv,cwd=root,capture_output=True)
    (out/(label+'.stdout')).write_bytes(r.stdout);(out/(label+'.stderr')).write_bytes(r.stderr)
    (out/(label+'-receipt.json')).write_text(json.dumps({'exit_code':r.returncode,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'stdout_sha256':sha(r.stdout),'stderr_sha256':sha(r.stderr)},indent=2)+'\n')
    assert r.returncode==0,(label,r.returncode)
    return r
run('prefix-corrected-stage',['git','add','--','progress/state.json','progress/CURRENT.md',str(Path(evidence).parent)])
run('prefix-corrected-staged-diff',['git','diff','--cached','--check'])
scan=run('prefix-corrected-staged-publication',['uv','run','--frozen','--no-sync','python','scripts/check_publication.py'])
structure=run('current-M0-structure-only',['uv','run','--frozen','--no-sync','python','scripts/verify_spec.py'])
(out/'FINAL_READBACK.json').write_text(json.dumps({'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'original_whitespace_exit_code':2,'original_publication_scan_exit_code':1,
    'final_staged_diff_exit_code':0,'subsequent_publication_scan_exit_code':0,'M0_structure_only_exit_code':0,
    'evidence':evidence,'source_push':False,'wholeM6_3':'NOT_ACCEPTED'},indent=2)+'\n')
print(scan.stdout.decode().strip());print(structure.stdout.decode().strip())
