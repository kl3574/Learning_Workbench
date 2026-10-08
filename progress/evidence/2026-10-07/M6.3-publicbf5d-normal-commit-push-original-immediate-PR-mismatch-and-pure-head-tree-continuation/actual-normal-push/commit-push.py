from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02';PUBLIC='079a008cf88b37e4517cb391503a1e7393ccf374';BASE='e2877101d9c2bda0f793a460db63ef496350c6b4';BRANCH='feat/M6.3-local-control-bootstrap'
def sha(v):return hashlib.sha256(v).hexdigest()
def put(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def run(n,argv):
 assert not (O/(n+'-receipt.json')).exists();put(n+'-command.json',{'argv':argv,'cwd':str(R),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});t=time.monotonic();x=subprocess.run(argv,cwd=R,capture_output=True);(O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr);put(n+'-receipt.json',{'actual_exit':x.returncode,'stdout_bytes':len(x.stdout),'stdout_sha256':sha(x.stdout),'stderr_bytes':len(x.stderr),'stderr_sha256':sha(x.stderr),'elapsed_seconds':time.monotonic()-t,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});assert x.returncode==0,(n,x.returncode);return x
proof=json.loads((B/'m63-current101-final-original-publication-gate-oct07/READBACK.json').read_bytes());assert proof['actual_original_default_diff_exit']==proof['actual_original_all_tracked_publication_exit']==0 and proof['stage_tree_unchanged']
assert run('01-local-head',['git','rev-parse','HEAD']).stdout.decode().strip()=='101cee47d8e746dddac81fb6e8829069fcabff09'
assert run('02-local-branch',['git','branch','--show-current']).stdout.decode().strip()==BRANCH
assert run('03-stage-tree',['git','write-tree']).stdout.decode().strip()==proof['stage_tree_before_after']
assert run('04-origin-url',['git','remote','get-url','origin']).stdout.decode().strip()=='https://github.com/kl3574/Learning_Workbench.git'
assert json.loads(run('05-identity',['gh','api','user']).stdout)['login']=='kl3574'
before=json.loads(run('06-branch-before',['gh','api','repos/kl3574/Learning_Workbench/branches/feat%2FM6.3-local-control-bootstrap']).stdout);p=json.loads(run('07-pr-before',['gh','api','repos/kl3574/Learning_Workbench/pulls/56']).stdout)
assert before['commit']['sha']==p['head']['sha']==PUBLIC and p['draft'] and p['state']=='open' and p['merged_at'] is None and p['base']['sha']==BASE
run('08-ancestry-public',['git','merge-base','--is-ancestor',PUBLIC,'HEAD'])
run('09-normal-local-commit',['git','-c','user.name=Kangxin Liu','-c','user.email=robinliu97@outlook.com','commit','-m','docs: record fixed101 complete gates and exact archive rules'])
head=run('10-committed-head',['git','rev-parse','HEAD']).stdout.decode().strip();tree=run('11-committed-tree',['git','rev-parse','HEAD^{tree}']).stdout.decode().strip();assert tree==proof['stage_tree_before_after']
put('LOCAL-COMMIT-ACTUAL.json',{'head':head,'tree':tree,'parent_anchor':'101cee47d8e746dddac81fb6e8829069fcabff09','actual_commit_exit':0,'publication_original_gate':'actual0/stageexact','source4normalmerges':'90c8/232/8bd/552 already ancestors101','runtime_input_qualification':'Fixed101 complete gates;1563 other sourceinputs unchanged and11 exact archive attributes only','actual_source_push':'NOT_YET','M6_3':'NOT_ACCEPTED'})
run('12-normal-push',['git','push','origin','HEAD:refs/heads/'+BRANCH])
ba=json.loads(run('13-branch-after',['gh','api','repos/kl3574/Learning_Workbench/branches/feat%2FM6.3-local-control-bootstrap']).stdout);pa=json.loads(run('14-pr-after',['gh','api','repos/kl3574/Learning_Workbench/pulls/56']).stdout)
assert ba['commit']['sha']==head;assert pa['draft'] and pa['state']=='open' and pa['merged_at'] is None and pa['base']['sha']==BASE and pa['title']==p['title']
put('IMMEDIATE-READBACK.json',{'local_committed_head':head,'branch_head':ba['commit']['sha'],'pr_head':pa['head']['sha'],'draft_open_unmerged':True,'base_unchanged':True,'exact_heads_match':pa['head']['sha']==head,'second_push':False,'actual_git_push_exit':0})
if pa['head']['sha']!=head:
 print('Normal push0; immediate PR head not yet equal; will use read-only metadata continuation, no second push.',flush=True);sys.exit(3)
put('READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'local_head':head,'public_branch_head':head,'public_draft_PR56_head':head,'tree':tree,'actual_normal_commit_push_exit':[0,0],'draft_open_unmerged':True,'base_sha':BASE,'local_runtime_anchor':'101cee47d8e746dddac81fb6e8829069fcabff09','source4normal_merges_already_included':True,'complete_gates':'Fixed101Python4587P2numericENVskip3warn/native133P20.9m; notnewGitHubCI','new_CI_status':'NOT_OBSERVED_YET','merge_release_deploy':False,'real_model_calls':0,'physical_numeric':'BLOCKED_ENVIRONMENT_NO_FALLBACK','M6_3':'NOT_ACCEPTED','M7':'NOT_UNLOCKED'})
print('Actual normal commit/push and exact branch/draft PR readback:',head)
