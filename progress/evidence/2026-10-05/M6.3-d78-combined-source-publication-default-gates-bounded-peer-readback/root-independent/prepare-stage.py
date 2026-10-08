from pathlib import Path
import datetime,hashlib,importlib.util,json,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02';E=B/'m63-d78-source-publication-independent-oct05'
HEAD='d78c4d159a2831f7d5e1721a9a466ec5b3e66421';PUBLIC='1e7ad7a8656c0dc8373d4181fa3002f385ed1847'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def put(n,v):(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('diff','--cached','--name-only')
m=json.loads((E/'SAFE_REPORT_CANDIDATES.json').read_bytes());assert len(m['entries'])==10
for e in m['entries']:
 raw=(E/e['original_relative_path']).read_bytes();b=(E/'publication-candidates'/e['candidate_path']).read_bytes()
 assert len(raw)==e['original_size'] and sha(raw)==e['original_sha256']
 assert len(b)==e['size'] and sha(b)==e['sha256']
 assert b==(raw if e['transformation']=='identity' else raw.replace(b'$HOME',b'~'))
source=json.loads((E/'SOURCE_PUBLICATION_ALLOWLIST.json').read_bytes());assert source['base']==PUBLIC and source['head']==HEAD and len(source['entries'])==24
changed=git('diff','--name-only',PUBLIC,HEAD,'--','.',':(exclude)progress/**').decode().splitlines()
assert set(changed)=={e['path'] for e in source['entries']}
for e in source['entries']:
 b=git('show',HEAD+':'+e['path']);assert len(b)==e['size'] and sha(b)==e['sha256']
put('SOURCE_PEER_ROOT_ADMISSION.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':HEAD,'public_base':PUBLIC,
 'finite_candidate_count':10,'source_texts_rebound':24,'source_summary':'20added/4modified/0removed;1537oldengineeringunchanged;1561current',
 'manual_read':'Complete owner REPORT.md and delegated peer6662B REPORT.md; production defaults remain emptyproofs/executorNone; prior separate root functional source qualification retained',
 'independence_limit':'Coordinator authored20Broker/interrupt paths, so source publication reading is not independent correctness review; delegated peer only default registration gates; root separate prior actual functional qualification',
 'formal_outgoing_scan':'NOT_RUN; next after documentary commit','current_full_python_native_CI':'NOT_RUN','model_calls':0,'whole_M63_AC21_M7':'NOT_ACCEPTED'})
sp=importlib.util.spec_from_file_location('helper',B/'m63-412abe-progress-checkpoint-oct05/package-helper-archived.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
path=h.package('M6.3-d78-combined-source-publication-default-gates-bounded-peer-readback',[
 ('finite-source-review','m63-d78-source-publication-independent-oct05/publication-candidates',[e['candidate_path'] for e in m['entries']]),
 ('seal','m63-d78-source-publication-independent-oct05',['SAFE_REPORT_CANDIDATES.json']),
 ('root-independent','m63-d78-documentary-publication-oct07',['prepare-stage.py','SOURCE_PEER_ROOT_ADMISSION.json'])],
 {'scope':'Bounded24changedsource publication readiness and delegated defaultgates; formaloutgoing scan separate',
 'source':HEAD,'public_base':PUBLIC,'engineering_inputs':1561,'added':20,'modified':4,'removed':0,
 'owner_independence':'Coordinator selfread20paths; delegated peer only defaultproof/executor gate; root prior functionalqualification separate',
 'tests_run':0,'current_complete_gates':'NOT_RUN','model_calls':0,'remote_write':False,'whole_M63_AC21_M7':'NOT_ACCEPTED'})
sys.path.insert(0,str(R/'scripts'));from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3')
if path not in t['evidence_paths']:t['evidence_paths'].append(path)
s['verification']['m6_3_current1561_source_publication_peer']={'evidence':path,'source':HEAD,'scope':'24changedsource/delegateddefaultgates; no formaloutgoing/newtest/wholeclaim'}
untracked=git('ls-files','--others','--exclude-standard').decode().splitlines();assert len(untracked)==445
s['checkpoint']['working_tree']='Local1561d78 source;445explicit evidencefiles plus4progressdocuments prepared for exact documentary commit;public1e unchanged;originaluserb895clean'
save(s)
docs=['progress/state.json','progress/CURRENT.md','progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md']
assert sorted(git('diff','--name-only').decode().splitlines())==sorted(docs)
prefixes={p.split('/')[3] for p in untracked};assert len(prefixes)==8
assert all(p.startswith('progress/evidence/2026-10-05/') for p in untracked)
selection=docs+sorted(untracked);put('SELECTION.json',{'source':HEAD,'count':len(selection),'files':selection,'prefixes':sorted(prefixes),'scope':'Exact4progressdocuments+8finitepackages445files; no source mutation'})
def run(n,argv):
 put(n+'-command.json',{'argv':argv,'cwd':str(R),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 x=subprocess.run(argv,cwd=R,capture_output=True);(O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr)
 put(n+'-receipt.json',{'exit_code':x.returncode,'stdout_size':len(x.stdout),'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 assert x.returncode==0,(n,x.returncode)
run('stage',['git','add','--',*selection])
run('original-staged-diff',['git','diff','--cached','--check'])
run('staged-publication',['uv','run','--frozen','--no-sync','python','scripts/check_publication.py'])
put('STAGE_READBACK.json',{'source':HEAD,'selected':449,'evidence':445,'documents':4,'staged_diff_exit':0,'staged_publication_exit':0,'sourcepush':False,'whole_M63_AC21_M7':'NOT_ACCEPTED'})
print('Exact449progress/evidence files staged; originaldiff and bounded publication scanner0; no commit/push yet.')
