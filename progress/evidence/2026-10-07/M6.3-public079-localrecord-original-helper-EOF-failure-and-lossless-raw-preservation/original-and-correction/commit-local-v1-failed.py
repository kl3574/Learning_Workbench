from pathlib import Path
import datetime,hashlib,json,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02';HEAD='079a008cf88b37e4517cb391503a1e7393ccf374'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('diff','--cached','--name-only')
snapshot=json.loads((B/'m63-ci-public079a008-observation-oct07/14-SNAPSHOT.json').read_bytes());assert snapshot['source']==HEAD and all(e['status']=='in_progress' for e in snapshot['actual_events'])
assert all(len([j for j in e['jobs'] if j['conclusion']=='success'])==4 for e in snapshot['actual_events'])
sys.path.insert(0,str(R/'scripts'));from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3');c=t['current_local_checkpoint']
original=c['current_public_originalCI'];c['current_public_originalCI']={**original,'snapshot':14,'observed_utc':snapshot['observed_utc'],'status':'BOTH_ACTUAL4SUCCESS2RUNNING; NOT_TERMINAL','original_body_sync_snapshot':3,'actual_events':snapshot['actual_events']}
s['verification']['m6_3_current_public079_original_ci']=c['current_public_originalCI'];s['verification']['m6_3_current_combined1561']=c
s['verification']['ci']='Current079 push37632652743/PR37632662238 attempt1: snapshot14 at14:08:38UTC each4SUCCESS/backend/frontend/spec/publication and2RUNNING/browser/integration. Exacttestcounts pendingoriginalraw independentreadback; entireCI NOT_TERMINAL. Actualbody14:00 usedsnapshot3, preserved. Olderpublic1e twoCIFAIL remain.'
s['checkpoint']['working_tree']='Localrecord of actualpublic079sourcepush/body and83finite evidencefiles+4progressdocs; nextordinary localonly87path commit; no furtherpush while currentoriginalCI running'
save(s)
docs=['progress/state.json','progress/CURRENT.md','progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md'];new=git('ls-files','--others','--exclude-standard').decode().splitlines()
assert len(new)==83 and all(p.startswith('progress/evidence/2026-10-07/') for p in new)
assert set(git('diff','--name-only').decode().splitlines())==set(docs)
selection=docs+sorted(new);put('SELECTION.json',{'files':selection,'count':87,'source':HEAD,'scope':'Localonly actualpublic receipts+4progress documents; no newruntime or remotemutation'})
def run(n,argv):
 assert not (O/(n+'-command.json')).exists();put(n+'-command.json',{'argv':argv,'cwd':str(R),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 x=subprocess.run(argv,cwd=R,capture_output=True);(O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr)
 put(n+'-receipt.json',{'exit_code':x.returncode,'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 assert x.returncode==0,(n,x.returncode)
run('stage',['git','add','--',*selection])
run('staged-diff',['git','diff','--cached','--check'])
run('staged-publication',['uv','run','--frozen','--no-sync','python','scripts/check_publication.py'])
assert not git('diff','--name-only') and not git('ls-files','--others','--exclude-standard')
run('commit',['git','commit','-m','Record actual public branch and original CI start with production Agent gaps'])
local=git('rev-parse','HEAD').decode().strip();assert git('rev-parse','HEAD^').decode().strip()==HEAD and not git('status','--porcelain')
assert not git('diff','--name-only',HEAD,local,'--','.',':(exclude)progress/**')
user=Path('$HOME/Desktop/learning/Learning_Workbench');assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=user).decode().strip()=='b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2' and not subprocess.check_output(['git','status','--porcelain'],cwd=user)
put('COMMIT_READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'local_head':local,'parent_actual_public':HEAD,'paths':87,'engineering1561_all_exact_public079':True,'originaluserb895clean':True,
 'public_head':HEAD,'sourcepush':False,'reason_no_push':'TwooriginalCI stillrunning; do not trigger cancel-in-progress','whole_M63_AC21_M7':'NOT_ACCEPTED','model_calls':0})
print(json.dumps({'local_head':local,'public_head':HEAD,'paths':87,'engineering_all_exact':True,'sourcepush':False}))
