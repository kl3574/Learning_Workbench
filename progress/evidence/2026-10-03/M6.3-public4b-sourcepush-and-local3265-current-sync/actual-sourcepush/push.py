import datetime,hashlib,json,subprocess
from pathlib import Path
B=Path('$HOME/.cache/learning-workbench-acceptance');R=B/'m62-public-safe-oct02';O=Path(__file__).parent
H='4b5516bd2a78d7b39f9b4a4c321a6d91ad4ca78f';P='69029bc1ab355efdbb6e0fdb8a86204c59cea71a';REPO='kl3574/Learning_Workbench';BR='feat/M6.3-local-control-bootstrap';sha=lambda b:hashlib.sha256(b).hexdigest()
assert not (O/'push.log').exists()
def api(label,path):
 p=subprocess.run(['gh','api','repos/'+REPO+'/'+path],capture_output=True);(O/(label+'.json')).write_bytes(p.stdout);(O/(label+'.stderr')).write_bytes(p.stderr);assert p.returncode==0;return json.loads(p.stdout)
assert subprocess.check_output(['gh','api','user','--jq','.login']).strip()==b'kl3574'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==H and not subprocess.check_output(['git','status','--porcelain'],cwd=R)
remote=subprocess.check_output(['git','remote','get-url','origin'],cwd=R,text=True).strip();assert remote in ['https://github.com/kl3574/Learning_Workbench.git','git@github.com:kl3574/Learning_Workbench.git']
subprocess.run(['git','merge-base','--is-ancestor',P,H],cwd=R,check=True)
a=json.loads((B/'m63-outgoing-publication-audit-4b5516bd-oct04/receipt.json').read_text());assert a['head']==H and a['status']=='PASS_BOUNDED_PUBLICATION_SCANNER' and not a['findings']
pr=api('pr-before','pulls/56');ref=api('ref-before','git/ref/heads/'+BR)
assert pr['draft'] and pr['state']=='open' and pr['merged_at'] is None and pr['head']['sha']==P and ref['object']['sha']==P
assert pr['base']['ref']=='feat/M6.2-candidate-review' and pr['base']['sha']=='e2877101d9c2bda0f793a460db63ef496350c6b4'
command=['git','push','origin','HEAD:refs/heads/'+BR];p=subprocess.run(command,cwd=R,capture_output=True);(O/'push.log').write_bytes(p.stdout+p.stderr)
r={'status':'PUSH_COMMAND_COMPLETED' if p.returncode==0 else 'PUSH_COMMAND_FAILED','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':command,'exit_code':p.returncode,'head':H,'previous_public_head':P,'log_sha256':sha(p.stdout+p.stderr),'boundary':'Authorized normal branch sourcepush only, noforce/noGitHubmerge/release/deploy/model. Actual29e fullgates do not accept isolatednextfeatures.'};(O/'push-result.json').write_text(json.dumps(r,indent=2)+'\n');assert p.returncode==0
ref_after=api('ref-after','git/ref/heads/'+BR);pr_after=api('pr-after','pulls/56')
readback={'status':'SOURCE_PUSH_REMOTE_HEAD_VERIFIED' if ref_after['object']['sha']==pr_after['head']['sha']==H else 'INITIAL_REMOTE_HEAD_READBACK_MISMATCH','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':H,'remote_ref_head':ref_after['object']['sha'],'pr56_head':pr_after['head']['sha'],'pr56_draft':pr_after['draft'],'pr56_state':pr_after['state'],'pr56_merged_at':pr_after['merged_at'],'pr56_body_sha256':sha(pr_after['body'].encode()),'sourcepush_exit':p.returncode,'ci':'NOT_YET_READ','boundary':'Actual sourcepush separately verified; fullgates29e and doc-only4b. No GitHubmerge/release/deploy,0externalmodels.'};(O/'readback.json').write_text(json.dumps(readback,indent=2)+'\n');print(json.dumps(readback));assert ref_after['object']['sha']==pr_after['head']['sha']==H
assert pr_after['draft'] and pr_after['state']=='open' and pr_after['merged_at'] is None
