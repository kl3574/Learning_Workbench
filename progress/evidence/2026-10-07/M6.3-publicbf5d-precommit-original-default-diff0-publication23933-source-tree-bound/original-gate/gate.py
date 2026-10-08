from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def run(n,argv):
 put(n+'-command.json',{'argv':argv,'cwd':str(R),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 t=time.monotonic();x=subprocess.run(argv,cwd=R,capture_output=True);(O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr);put(n+'-receipt.json',{'actual_exit':x.returncode,'stdout_bytes':len(x.stdout),'stdout_sha256':sha(x.stdout),'stderr_bytes':len(x.stderr),'stderr_sha256':sha(x.stderr),'elapsed_seconds':time.monotonic()-t,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});return x
before=run('01-stage-snapshot',['git','write-tree']);assert before.returncode==0
x=run('02-original-default-staged-diff',['git','diff','--cached','--check']);print('default_cached_diff_actual_exit',x.returncode,flush=True)
if x.returncode:sys.exit(x.returncode)
x=run('03-original-all-tracked-publication',['python3','scripts/check_publication.py','--all-tracked']);print('all_tracked_publication_actual_exit',x.returncode,flush=True)
if x.returncode:sys.exit(x.returncode)
after=run('04-final-stage-snapshot',['git','write-tree']);assert after.returncode==0 and after.stdout==before.stdout
put('READBACK.json',{'actual_original_default_diff_exit':0,'actual_original_all_tracked_publication_exit':0,'stage_tree_before_after':before.stdout.decode().strip(),'stage_tree_unchanged':True,'manual_provenance':'Explicit finite root admissions and independent original candidate provenance audits retained; scanner is not sole provenance approval','source_gate_anchor':'101cee47d8e746dddac81fb6e8829069fcabff09','archive_attrs':'11 literal rules; other1563 exact; no runtime source edits','real_model_calls':0,'M6_3':'NOT_ACCEPTED','commit_push':'NOT_RUN_BY_THIS_GATE_SCRIPT'})
print('Original publication gate terminal; stagedtree unchanged.')
