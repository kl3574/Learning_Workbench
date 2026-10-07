from pathlib import Path
import datetime,hashlib,importlib.util,json,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02'
P=R/'progress/evidence/2026-10-07/M6.3-actual-public079a008-sourcepush-guarded-body-sync-and-two-original-CI-start'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
receipt=json.loads((O/'staged-diff-receipt.json').read_bytes());raw=(O/'staged-diff.stdout').read_bytes();assert receipt['exit_code']==2 and receipt['stdout_sha256']==sha(raw)
paths=['root-readback/package-helper.py','root-readback/v1-package-helper.py']
assert len(raw.decode().splitlines())==2 and all(n in raw.decode() for n in paths)
(O/'commit-local-v1-failed.py').write_bytes((O/'commit-local.py').read_bytes())
manifest=P/'manifest.json';old=manifest.read_bytes();(O/'PUBLIC_MANIFEST_BEFORE_EOF_CONVERSION.json').write_bytes(old);d=json.loads(old);changes=[]
for n in paths:
 f=P/n;b=f.read_bytes();e=next(x for x in d['entries'] if x['file']==n)
 assert sha(b)==e['published_sha256'] and b.endswith(b'\n\n') and not b.endswith(b'\n\n\n')
 safe=b[:-1];f.write_bytes(safe);e['published_sha256']=sha(safe);e['transformation']+='; remove exactly one extra final LF from newauthored helper copy only; private raw unchanged'
 changes.append({'path':str(f.relative_to(R)),'original_candidate_size':len(b),'original_candidate_sha256':sha(b),'new_candidate_size':len(safe),'new_candidate_sha256':sha(safe),'private_raw_sha256':e['raw_sha256'],'conversion':'Exactly remove one terminalLF only; all other bytes preserved'})
manifest.write_text(json.dumps(d,indent=2)+'\n')
put('HELPER_EOF_CONVERSION_READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tool_chunk':'b76bc4','actual_staged_gitdiff_exit':2,'wrapper_exit':1,
 'scope':'Two copies of newlyauthored packagehelper code, not original test logs/runner raw bytes; private raws unchanged, public manifest explicitconversion','changes':changes,
 'original_failure_stdout_sha256':sha(raw),'new_manifest_sha256':sha(manifest.read_bytes()),'no_attributes_runtime_scanner_change':True})
sp=importlib.util.spec_from_file_location('helper',O/'package-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
evidence=h.package('M6.3-public079-localrecord-original-helper-EOF-failure-and-lossless-raw-preservation',[
 ('original-and-correction',O.name,['commit-local-v1-failed.py','staged-diff-command.json','staged-diff-receipt.json','staged-diff.stdout','HELPER_EOF_CONVERSION_READBACK.json','PUBLIC_MANIFEST_BEFORE_EOF_CONVERSION.json','recover-helper-eof.py'])],
 {'scope':'Actual gitdiff2 from2newauthoredhelper-copy extraEOF LF; explicit terminalLFconversion, rawprivate/codebytes unchanged otherwise',
 'actual_gitdiff_failure':2,'root_tool_chunk':'b76bc4','product_runtime_attributes_scanner_changed':False,'original_test_log_bytes_changed':False,'sourcepush':False,'model_calls':0,'whole_M63_AC21_M7':'NOT_ACCEPTED'})
sys.path.insert(0,str(R/'scripts'));from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3');t['evidence_paths'].append(evidence)
t['current_local_checkpoint']['local_current_complete_python']={'source':'079a008cf88b37e4517cb391503a1e7393ccf374','status':'ACTUALLY_RUNNING_ORIGINAL_COMMAND_ONCE_NOT_TERMINAL','owner_agent':'current079_complete_python_oct07',
 'owned_tool_handle':31957,'owned_command_pid':54356,'wrapper_pid':54331,'originals':'m63-public079-complete-python-originals-v2-oct07/complete-python','inputs':1561,'collected':4583,'collected_source':'Owner originallivepytestlog reported4583; terminal notyetavailable','setup':'Actual0/1561exact43.08s; publicdependencytraffic; Nodeactualversionreceipt separate','actual_argv':['uv','run','--frozen','--offline','pytest']}
s['verification']['m6_3_current_combined1561']=t['current_local_checkpoint'];s['verification']['m6_3_public079_complete_python']=t['current_local_checkpoint']['local_current_complete_python']
s['verification']['m6_3_public079_localrecord_EOF_correction']={'evidence':evidence,'original_gitdiff_exit':2,'correction':'Two derivedhelpercopies one terminalLF explicitlyremoved; rawprivate originals retained; no scanner/runtime/attributes modification'}
save(s)
prior=json.loads((O/'SELECTION.json').read_bytes())['files'];extra=git('ls-files','--others','--exclude-standard').decode().splitlines();assert len(extra)==9
selection=sorted(set(prior+extra));assert len(selection)==96
put('CORRECTED_SELECTION.json',{'files':selection,'count':96,'oldpaths':87,'new_failure_packet':9,'all_nonprogress_unchanged':True})
def run(n,argv):
 assert not (O/(n+'-command.json')).exists();put(n+'-command.json',{'argv':argv,'cwd':str(R),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 x=subprocess.run(argv,cwd=R,capture_output=True);(O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr)
 put(n+'-receipt.json',{'exit_code':x.returncode,'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 assert x.returncode==0,(n,x.returncode)
run('corrected-stage',['git','add','--',*selection])
run('corrected-staged-diff',['git','diff','--cached','--check'])
run('corrected-publication',['uv','run','--frozen','--no-sync','python','scripts/check_publication.py'])
assert not git('diff','--name-only') and not git('ls-files','--others','--exclude-standard')
run('corrected-commit',['git','commit','-m','Record actual source publication and original complete gate start'])
new=git('rev-parse','HEAD').decode().strip();assert git('rev-parse','HEAD^').decode().strip()=='079a008cf88b37e4517cb391503a1e7393ccf374' and not git('status','--porcelain')
assert not git('diff','--name-only','079a008cf88b37e4517cb391503a1e7393ccf374',new,'--','.',':(exclude)progress/**')
put('CORRECTED_COMMIT_READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'local_head':new,'public_head':'079a008cf88b37e4517cb391503a1e7393ccf374','paths':96,'all1561_nonprogress_exact_public079':True,
 'original_gitdiff_failure':2,'corrected_diff_publication_commit_exit':0,'current_complete_python':'ACTUALLY_RUNNING_NOT_TERMINAL','sourcepush':False,'whole_M63_AC21_M7':'NOT_ACCEPTED','model_calls':0})
print(json.dumps({'local_head':new,'public_head':'079a008cf88b37e4517cb391503a1e7393ccf374','paths':96,'nonprogress_exact':True,'sourcepush':False}))
