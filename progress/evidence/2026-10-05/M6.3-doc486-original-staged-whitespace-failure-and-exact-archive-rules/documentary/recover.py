"""Preserve original archival whitespace and qualify a subsequent check."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

base=Path('$HOME/.cache/learning-workbench-acceptance')
root=base/'m62-public-safe-oct02'
out=Path(__file__).parent
assert not (out/'RECOVERY_READBACK.json').exists()
original=json.loads((out/'READBACK.json').read_text())
assert original['original_staged_diff_exit_code']==2
old=(root/'.gitattributes').read_bytes()
(out/'gitattributes-before.txt').write_bytes(old)
names=[]
for line in (out/'original-staged-diff.stdout').read_text().splitlines():
    if ': trailing whitespace.' in line:
        path=line.rsplit(':',2)[0]
        assert path.startswith('progress/evidence/2026-10-05/')
        if path not in names: names.append(path)
assert len(names)==5
packet='M6.3-doc486-original-staged-whitespace-failure-and-exact-archive-rules'
names.append('progress/evidence/2026-10-05/'+packet+'/documentary/original-staged-diff.stdout')
rules='\n# Exact immutable original evidence patches, CI excerpts and whitespace failure captures.\n'+'\n'.join(p+' -whitespace' for p in names)+'\n'
for p in names:
    assert (p+' -whitespace').encode() not in old
(root/'.gitattributes').write_bytes(old+rules.encode())
sha=lambda b:hashlib.sha256(b).hexdigest()
def run(label,argv):
    assert not (out/(label+'-command.json')).exists()
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out/(label+'-command.json')).write_text(json.dumps({'argv':argv,'cwd':str(root),'started_utc':start},indent=2)+'\n')
    r=subprocess.run(argv,cwd=root,capture_output=True)
    (out/(label+'.stdout')).write_bytes(r.stdout)
    (out/(label+'.stderr')).write_bytes(r.stderr)
    (out/(label+'-receipt.json')).write_text(json.dumps({'exit_code':r.returncode,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'stdout_sha256':sha(r.stdout),'stderr_sha256':sha(r.stderr)},indent=2)+'\n')
    assert r.returncode==0,(label,r.returncode)
    return r
run('stage-exact-attributes',['git','add','--','.gitattributes'])
run('subsequent-staged-diff',['git','diff','--cached','--check'])
(out/'RECOVERY_READBACK.json').write_text(json.dumps({'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'original_exit_code':2,'subsequent_exit_code':0,'exact_archive_rule_paths':names,
    'old_attributes_prefix_unchanged':(root/'.gitattributes').read_bytes().startswith(old),
    'qualification':'Exact reviewed archives only. No production-source whitespace exception. Original failure bytes retained.'},indent=2)+'\n')
namespace={}
exec((base/'m63-412abe-progress-checkpoint-oct05/package-helper-archived.py').read_text(),namespace)
allowed=['stage.py','recover.py','original-staged-diff-command.json','original-staged-diff.stdout','original-staged-diff.stderr',
    'original-staged-diff-receipt.json','READBACK.json','stage-exact-attributes-command.json','stage-exact-attributes.stdout',
    'stage-exact-attributes.stderr','stage-exact-attributes-receipt.json','subsequent-staged-diff-command.json',
    'subsequent-staged-diff.stdout','subsequent-staged-diff.stderr','subsequent-staged-diff-receipt.json','RECOVERY_READBACK.json']
evidence=namespace['package'](packet,[('documentary',out.name,allowed)],{'status':'ORIGINAL_STAGED_WHITESPACE_EXIT2_RETAINED_EXACT_ARCHIVE_RULES_SUBSEQUENT_EXIT0',
    'source':'4869393654446c1dfcb0da97b9dca5fa7429b36f',
    'boundary':'Original464selectedfiles checkexit2 atfive exact evidence archives; all bytes preserved. Six exact archive rules include this copied originalstdout; no global/sourcewhitespace relaxation. Subsequent stagedcheck0 before this new packet/progress update; finalcheck separately required. Not product or wholephase acceptance.'})
sys.path.insert(0,str(root/'scripts'))
from progress import read_state,save
state=read_state(); task=next(t for t in state['tasks'] if t['id']=='M6.3')
task['evidence_paths'].append(evidence)
state['verification']['m6_3_doc486_original_whitespace']={'original_exit_code':2,'subsequent_exit_code':0,
    'exact_archive_paths':names,'evidence':evidence,'wholeM6_3':'NOT_ACCEPTED'}
save(state)
run('stage-final-selected',['git','add','--','.gitattributes','progress/state.json','progress/CURRENT.md','progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md',str(Path(evidence).parent)])
run('final-staged-diff',['git','diff','--cached','--check'])
run('staged-publication-scan',['uv','run','--frozen','--no-sync','python','scripts/check_publication.py'])
run('current-M0-structure-only',['uv','run','--frozen','--no-sync','python','scripts/verify_spec.py'])
(out/'FINAL_READBACK.json').write_text(json.dumps({'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'original_exit_code':2,'final_staged_diff_exit_code':0,'staged_publication_scan_exit_code':0,
    'M0_structure_only_exit_code':0,'evidence':evidence,'source_push':False,'wholeM6_3':'NOT_ACCEPTED'},indent=2)+'\n')
print('Original whitespace failure preserved; exact archive rules, final staged scan and M0 structure-only check passed.')
