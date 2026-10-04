"""Separate pure head readback; never repeats the successful git push."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

out=Path(__file__).parent
head='6671dd5c924edbac8ca7f479c4f51d4afec14480'
assert not (out/'PURE_HEAD_READBACK.json').exists()
prior=json.loads((out/'READBACK.json').read_text())
assert prior['git_exit_code']==0
rows={}
for label,path in [('pure-branch','repos/kl3574/Learning_Workbench/branches/feat/M6.3-local-control-bootstrap'),('pure-pr','repos/kl3574/Learning_Workbench/pulls/56')]:
    assert not (out/(label+'-command.json')).exists()
    (out/(label+'-command.json')).write_text(json.dumps({'argv':['gh','api',path],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
    r=subprocess.run(['gh','api',path],capture_output=True)
    (out/(label+'.stdout')).write_bytes(r.stdout);(out/(label+'.stderr')).write_bytes(r.stderr)
    (out/(label+'-receipt.json')).write_text(json.dumps({'exit_code':r.returncode,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
     'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest()},indent=2)+'\n')
    assert r.returncode==0
    rows[label]=json.loads(r.stdout)
b=rows['pure-branch'];p=rows['pure-pr']
record={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expected_head':head,
 'branch_head':b['commit']['sha'],'pr_head':p['head']['sha'],'draft':p['draft'],'state':p['state'],'merged_at':p['merged_at'],
 'prior_immediate_pr_head':prior['pr_head'],'prior_head_mismatch_unique_cause':'NOT_ESTABLISHED',
 'second_git_push':False,'actual_model_calls':0}
record['exact_branch_pr_head_confirmed']=record['branch_head']==record['pr_head']==head and p['draft'] and p['state']=='open' and p['merged_at'] is None
(out/'PURE_HEAD_READBACK.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
