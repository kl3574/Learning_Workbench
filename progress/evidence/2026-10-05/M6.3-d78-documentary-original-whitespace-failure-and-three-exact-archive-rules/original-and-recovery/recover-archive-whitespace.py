from pathlib import Path
import datetime,hashlib,importlib.util,json,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
raw=(O/'original-staged-diff.stdout').read_bytes();receipt=json.loads((O/'original-staged-diff-receipt.json').read_bytes())
assert receipt['exit_code']==2 and receipt['stdout_sha256']==sha(raw)
paths=sorted({x.split(':',1)[0] for x in raw.decode().splitlines() if ': trailing whitespace.' in x})
assert len(paths)==3 and all(p.startswith('progress/evidence/2026-10-05/M6.3-Authoring3d-') for p in paths)
bindings=[]
for p in paths:
 b=(R/p).read_bytes();bindings.append({'path':p,'size':len(b),'sha256':sha(b),'original_whitespace_retained':True})
put('ORIGINAL_DIFF_FAILURE.json',{'tool_chunk':'d3fe58','wrapper_exit_code':1,'actual_git_diff_exit_code':2,'raw_stdout_size':len(raw),'raw_stdout_sha256':sha(raw),'raw_stdout_hex':raw.hex(),
 'original_paths':paths,'classification':'Immutable archived test output/patch context; not production code whitespace failure','no_original_byte_changes':True})
attr=R/'.gitattributes';old=attr.read_bytes();(O/'ATTRIBUTES_BEFORE.raw').write_bytes(old)
addition='\n# Exact original Authoring evidence whitespace; retain bound archived bytes.\n'+'\n'.join(p+' -whitespace' for p in paths)+'\n'
assert all((p+' -whitespace').encode() not in old for p in paths)
attr.write_bytes(old+addition.encode())
put('EXACT_ARCHIVE_RULES.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'paths':bindings,
 'original_attributes_sha256':sha(old),'new_attributes_sha256':sha(attr.read_bytes()),'exact_added_utf8':addition,
 'scope':'Three exact immutable evidence paths only; original archived bytes preserved; no scanner/timeout/test/product runtime change',
 'engineering_identity_limit':'1561 input count unchanged, .gitattributes differs from d78 source anchor; all other nonprogress entries unchanged; current whole gate notprovided'})
sp=importlib.util.spec_from_file_location('helper',B/'m63-412abe-progress-checkpoint-oct05/package-helper-archived.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
evidence=h.package('M6.3-d78-documentary-original-whitespace-failure-and-three-exact-archive-rules',[
 ('original-and-recovery','m63-d78-documentary-publication-oct07',['prepare-stage.py','original-staged-diff-command.json','original-staged-diff-receipt.json','ORIGINAL_DIFF_FAILURE.json','EXACT_ARCHIVE_RULES.json','recover-archive-whitespace.py'])],
 {'scope':'Actual staged original gitdiff2/3immutable evidence paths/four whitespace lines; full804B originalfailure retained as hex',
 'tool_chunk':'d3fe58','actual_gitdiff_exit':2,'root_wrapper_exit':1,'original_bytes_preserved':True,'exact_archive_rules':3,
 'product_runtime_test_scanner_modified':False,'attributes_metadata_changed':True,'current_whole_gate':'NOT_RUN','sourcepush':False,'model_calls':0})
sys.path.insert(0,str(R/'scripts'));from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3');t['evidence_paths'].append(evidence)
s['verification']['m6_3_current_documentary_diff_failure']={'actual_exit_code':2,'evidence':evidence,'repair':'Three exact immutable archive -whitespace rules, no byte trimming/scanner change','attributes_metadata_changed':True,'current_runtime_source_anchor':'d78c4d159a2831f7d5e1721a9a466ec5b3e66421'}
c=t['current_local_checkpoint'];c['documentary_attributes_only']='Three exact new immutable archive whitespace rules; .gitattributes changed, other1560nonprogress inputs exactd78; no fullcombination acceptance borrowed'
s['verification']['m6_3_current_combined1561']=c
save(s)
before=json.loads((O/'SELECTION.json').read_bytes())['files'];extra=git('ls-files','--others','--exclude-standard').decode().splitlines();selection=sorted(set(before+extra+['.gitattributes']))
assert len(extra)==8 and len(selection)==458
put('CORRECTED_SELECTION.json',{'files':selection,'count':len(selection),'original_stage_count':449,'new_exact_archive_rules':3,'new_failure_packet':8,'attributes_path':'.gitattributes'})
def run(n,argv):
 assert not (O/(n+'-command.json')).exists();put(n+'-command.json',{'argv':argv,'cwd':str(R),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 x=subprocess.run(argv,cwd=R,capture_output=True);(O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr)
 put(n+'-receipt.json',{'exit_code':x.returncode,'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 assert x.returncode==0,(n,x.returncode)
run('corrected-stage',['git','add','--',*selection])
run('corrected-staged-diff',['git','diff','--cached','--check'])
run('corrected-publication',['uv','run','--frozen','--no-sync','python','scripts/check_publication.py'])
for e in bindings:assert sha((R/e['path']).read_bytes())==e['sha256']
put('CORRECTED_STAGE_READBACK.json',{'selected_count':458,'original_gitdiff_failure':2,'corrected_gitdiff_exit':0,'staged_publication_exit':0,'three_exact_archive_bytes_unchanged':True,'model_calls':0,'sourcepush':False})
print('Exact458 paths staged; originalfailure preserved; three immutable archives byteexact; correcteddiff/publication0.')
