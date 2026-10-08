from pathlib import Path
import json,hashlib,datetime,subprocess
O=Path(__file__).resolve().parent;R=O.parent/'m62-public-safe-oct02'
PR='88da38fc07cd1d797e1171943a00159842421ac3';HEAD='1e7ad7a8656c0dc8373d4181fa3002f385ed1847';BASE='e2877101d9c2bda0f793a460db63ef496350c6b4'
def sha(b):return hashlib.sha256(b).hexdigest()
def run(stem,argv):
 assert not (O/(stem+'-command.json')).exists()
 (O/(stem+'-command.json')).write_text(json.dumps({'argv':argv,'cwd':str(R),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Read-only fixed public Git object acquisition; no worktree switch/sourcepush'},indent=2)+'\n')
 x=subprocess.run(argv,cwd=R,capture_output=True);(O/(stem+'.stdout')).write_bytes(x.stdout);(O/(stem+'.stderr')).write_bytes(x.stderr)
 (O/(stem+'-receipt.json')).write_text(json.dumps({'exit_code':x.returncode,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr)},indent=2)+'\n')
 assert x.returncode==0;return x.stdout
old=run('local-before',['git','rev-parse','HEAD']).decode().strip()
run('fetch-fixed-PR-merge',['git','fetch','--no-tags','origin',PR])
parents=run('actual-PR-parents',['git','rev-list','--parents','-n','1',PR]).decode().split();assert parents==[PR,BASE,HEAD]
t1=run('actual-push-tree',['git','rev-parse',HEAD+'^{tree}']).decode().strip();t2=run('actual-PR-tree',['git','rev-parse',PR+'^{tree}']).decode().strip();assert t1==t2
assert run('local-after',['git','rev-parse','HEAD']).decode().strip()==old
(O/'ACTUAL_FIXED_GIT_TREE_READBACK.json').write_text(json.dumps({'scope':'New actual fixedpublicGit tree acquisition; does not rewrite earlier NOT_CAPTURED report','public_head':HEAD,'actual_checkout_push':HEAD,'actual_checkout_PR':PR,'PR_parents':parents[1:],'actual_checkout_trees_equal':True,'actual_tree':t1,'current_local_HEAD_unchanged':old,'CI_beforeafter_working_input_maps':'NOT_CAPTURED','real_model_or_physical_numeric_qualification':False},indent=2)+'\n')
print(json.dumps({'head':HEAD,'PR_checkout':PR,'actual_same_tree':t1,'local_head_unchanged':old}))
