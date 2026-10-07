from pathlib import Path
import datetime,hashlib,json,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02'
def sha(v):return hashlib.sha256(v).hexdigest()
def put(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def run(n,argv):
 put(n+'-command.json',{'argv':argv,'cwd':str(R),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});x=subprocess.run(argv,cwd=R,capture_output=True);(O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr);put(n+'-receipt.json',{'actual_exit':x.returncode,'stdout_bytes':len(x.stdout),'stdout_sha256':sha(x.stdout),'stderr_bytes':len(x.stderr),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});assert x.returncode==0,(n,x.returncode);return x
orig=B/'m63-current101-reviewed-normal-commit-push-oct07';c=json.loads((orig/'LOCAL-COMMIT-ACTUAL.json').read_bytes());im=json.loads((orig/'IMMEDIATE-READBACK.json').read_bytes());head=c['head'];assert json.loads((orig/'12-normal-push-receipt.json').read_bytes())['actual_exit']==0
ba=json.loads(run('01-branch',['gh','api','repos/kl3574/Learning_Workbench/branches/feat%2FM6.3-local-control-bootstrap']).stdout);pa=json.loads(run('02-pr',['gh','api','repos/kl3574/Learning_Workbench/pulls/56']).stdout);remotecommit=json.loads(run('03-public-commit',['gh','api','repos/kl3574/Learning_Workbench/git/commits/'+head]).stdout);assert ba['commit']['sha']==head and remotecommit['sha']==head and remotecommit['tree']['sha']==c['tree'];assert pa['draft'] and pa['state']=='open' and pa['merged_at'] is None and pa['base']['sha']=='e2877101d9c2bda0f793a460db63ef496350c6b4'
record={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expected_head':head,'branch_head':ba['commit']['sha'],'pr_head':pa['head']['sha'],'remote_tree':remotecommit['tree']['sha'],'local_tree':c['tree'],'draft_open_unmerged':True,'base_unchanged':True,'immediate_original_readback':im,'immediate_PR_head_mismatch_cause':'NOT_ESTABLISHED','actual_normal_commit_push_exit':[0,0],'read_only_continuation':True,'second_push':False,'runtime_input_qualification':'Fixed101 full gates;1563source unchanged/11exact archive attributes; notnewCI result','real_model_calls_by_root':0,'M6_3':'NOT_ACCEPTED','M7':'NOT_UNLOCKED'};put('READBACK.json',record)
assert pa['head']['sha']==head,'PR head still differs; no push/retry command issued'
print('Read-only exact branch/PR/tree confirmed:',head)
ci=json.loads(run('04-new-original-run-list',['gh','api','repos/kl3574/Learning_Workbench/actions/runs?head_sha='+head+'&per_page=20']).stdout)
es=[]
for x in ci['workflow_runs']:
 if x['head_sha']==head:
  es.append({k:x[k] for k in ['id','event','head_sha','status','conclusion','run_attempt','html_url','created_at','updated_at']})
put('FIRST-ACTUAL-CI-SNAPSHOT.json',{'source_head':head,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actual_events':es,'count':len(es),'no_result_counts_inferred':True,'no_rerun_cancel_dispatch':True,'old079_events':'BothterminalFAILretainedseparately','M6_3':'NOT_ACCEPTED'})
print('New actual CI events observed:',[(x['id'],x['event'],x['status'],x['conclusion']) for x in es])
