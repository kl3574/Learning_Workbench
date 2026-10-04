"""Read-only evidence/Git-object verification; never invokes a product or test runner."""
from pathlib import Path, PurePosixPath
import datetime, hashlib, importlib.util, json, re, subprocess
ROOT=Path(__file__).parent
BASE=Path('$HOME/.cache/learning-workbench-acceptance')
E=BASE/'m63-legacy-review-backup-test-evidence-oct04'
STATIC=BASE/'m71-backup-legacy-test-static-review-1843556e-oct04'
REPO=BASE/'m63-bootstrap-full-native-bd3b-oct03'
BD='bd3b9375b41cf9a726260e7497a7302f11c3db04'; FIX='b51de327fe74cdc476a52e061fe2e044072d2267'
def sha(b):return hashlib.sha256(b).hexdigest()
def facts(p):
 b=p.read_bytes();return {'sha256':sha(b),'bytes':len(b)}
def distinct(items):
 d={}
 for k,v in items:
  assert k not in d,'duplicate JSON key';d[k]=v
 return d
def read(p):return json.loads(p.read_text(),object_pairs_hook=distinct)
def path(root,name):
 p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
 assert not set(p.parts)&{'pytest-cache','basetemp','harness-data'}
 assert p.suffix not in {'.db','.sqlite','.sqlite3','.zip','.key','.token'}
 return root/str(p)
def git(*args,stdin=None):return subprocess.check_output(['git',*args],cwd=REPO,input=stdin)
def git_inputs(head):
 entries=[]
 for row in git('ls-tree','-rz',head).split(b'\0'):
  if not row:continue
  info,name=row.split(b'\t');mode,kind,blob=info.decode().split();name=name.decode()
  if name.startswith('progress/'):continue
  assert kind=='blob';entries.append((name,mode,blob))
 stream=git('cat-file','--batch',stdin=''.join(x[2]+'\n' for x in entries).encode());pos=0;answer={}
 for name,mode,blob in entries:
  end=stream.index(b'\n',pos);header=stream[pos:end].decode().split();size=int(header[2]);start=end+1;data=stream[start:start+size];pos=start+size+1
  assert header[:2]==[blob,'blob'] and stream[pos-1:pos]==b'\n'
  answer[name]={'sha256':sha(data),'bytes':len(data),'git_blob':blob,'git_mode':mode,'exact_git_bytes':True}
 assert pos==len(stream) and len(answer)==1381
 return answer
manifest=read(E/'RAW_MANIFEST.json');assert manifest['count']==23==len(manifest['files']) and manifest['head']==FIX
for n,f in manifest['files'].items():assert facts(path(E,n))==f
runner=facts(E/'run_gate.py');inputs={BD:git_inputs(BD),FIX:git_inputs(FIX)}
stages=[]
expected=[('01-original-red',BD,1,1,0),('03-revised-green',FIX,0,0,1),('04-related-regression',FIX,0,0,65),('05-test-ruff',FIX,0,0,None)]
for stage,head,code,failed,passed in expected:
 r=read(E/stage/'receipt.json');before=read(E/stage/'inputs-before.json');after=read(E/stage/'inputs-after.json');log=(E/stage/'output.log').read_text()
 assert before==after and before['head']==head and before['count']==1381 and before['files']==inputs[head]
 assert before['private_inputs']=={'run_gate.py':runner}
 assert r['head']==head and r['phase']==stage and r['exit_code']==code and r['runner']==runner and r['input_count']==1381 and r['inputs_unchanged'] is True
 assert r['log_sha256']==sha((E/stage/'output.log').read_bytes()) and r['command'][:4]==['uv','run','--frozen','--no-sync']
 if passed is not None:
  assert r['command'][4]=='pytest'
  assert re.search(r'collected '+str(failed+passed)+r' items?',log)
  term=str(failed)+' failed' if failed else str(passed)+' passed'
  assert term in log
 else:assert r['command'][4:6]==['ruff','check'] and log.strip()=='All checks passed!'
 tests=[p for p in r['command'] if p.startswith('tests/')]
 if stage=='01-original-red':assert 'session_review_original' in log and '!= None' in log and 'reviewer_session_id' in log
 if stage=='04-related-regression':
  assert len(tests)==7 and '65 passed, 2 warnings in 18.86s' in log
  counts={};current=None
  for line in log.splitlines():
   m=re.match(r'^(tests/\S+\.py)\s+([.FEsx]+)\s+\[',line)
   if m:current=m[1];counts[current]=len(m[2]);continue
   m=re.match(r'^([.FEsx]+)\s+\[',line)
   if m and current:counts[current]+=len(m[1])
  assert set(counts)==set(tests) and sum(counts.values())==65
 else:counts=None
 stages.append({'phase':stage,'head':head,'exit_code':code,'passed':passed,'failed':failed,'all_1381_inputs_exact_fixed_git':True,'saved_before_after_equal':True,'runner_hash_matches':True,'log_hash_matches':True,'test_files':tests,'per_file_counts':counts,'monotonic_seconds_from_receipt':r['duration_seconds'],'started_at':r['started_at'],'finished_at':r['finished_at']})
preflight=read(E/'02-revised-green/preflight-failure.json');assert preflight['state']=='NOT_RUN' and 'before pytest launch' in preflight['cause']
assert not (E/'02-revised-green/output.log').exists() and not (E/'02-revised-green/receipt.json').exists()
p='tests/integration/test_review_storage_migration.py'
assert (E/'original-test-file.py').read_bytes()==git('show',BD+':'+p)
assert (E/'fixed-test-file.py').read_bytes()==git('show',FIX+':'+p)
assert git('diff','--name-only',BD,FIX).decode().splitlines()==[p]
assert (E/'test-only.patch').read_bytes()==git('diff',BD,FIX,'--',p)
scanner_path='progress/evidence/2026-09-28/M6.2-general-draft-fixed-gates/publication_scanner.py'
assert (ROOT/'publication-scanner-pinned.py').read_bytes()==git('show',FIX+':'+scanner_path)
spec=importlib.util.spec_from_file_location('safe_byte_scanner',ROOT/'publication-scanner-pinned.py');scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)
ss=read(E/'SAFE_SHARE.json');assert ss['count']==24==len(ss['entries']) and ss['only_explicit_entries_authorized'] is True
assert {x['raw_path'] for x in ss['entries']}==set(manifest['files'])|{'RAW_MANIFEST.json'}
assert len({x['candidate_path'] for x in ss['entries']})==24
raw_findings=[];safechecks=[];secret_fields={'authorization','cookie','set-cookie','x-csrf-token','csrf_token','one_time_code','access_token','refresh_token','api_key','private_key','raw_response','receipt_json','description_json'}
def no_secret_keys(value):
 if isinstance(value,dict):
  for k,v in value.items():assert k.lower() not in secret_fields;no_secret_keys(v)
 elif isinstance(value,list):
  for v in value:no_secret_keys(v)
def scan_safe(name,b):
 assert not scanner.inspect('progress/evidence/independent-backup/'+name,b)
 assert not re.search(rb'/home/[A-Za-z0-9_.-]+',b)
 if name.endswith('.json'):no_secret_keys(json.loads(b,object_pairs_hook=distinct))
 if name.endswith('.log'):assert not re.search(rb'(?im)^\s*(authorization|cookie|set-cookie|x-csrf-token)\s*:',b)
for entry in ss['entries']:
 n=entry['raw_path'];r=path(E,n);c=path(E,entry['candidate_path']);raw=r.read_bytes();public=c.read_bytes()
 assert entry['candidate_path']=='SAFE_SHARE/'+n and facts(r)==entry['raw'] and facts(c)==entry['candidate']
 assert public==raw.replace(b'$HOME',b'$HOME')
 assert entry['transform']==('unchanged' if public==raw else 'exact local-home prefix to $HOME only')
 scan_safe(n,public)
 for reason in scanner.inspect('progress/evidence/m63-legacy-review-backup-test-evidence-oct04/'+n,raw):raw_findings.append({'path':n,'reason':reason})
 safechecks.append({'path':n,'candidate_sha256':sha(public),'prefix_replacements':raw.count(b'$HOME')})
rawscan=read(E/'RAW_SCAN.json');candidate=read(E/'CANDIDATE_SCAN.json');assert rawscan['status']=='FAIL' and rawscan['findings']==raw_findings and len(raw_findings)==8
assert rawscan['scanner']==candidate['scanner']==facts(ROOT/'publication-scanner-pinned.py')
assert candidate['status']=='PASS' and candidate['findings']==[]
outer=read(E/'PUBLIC_OUTER_ALLOWLIST.json');assert set(outer['files'])=={'SAFE_SHARE.json','RAW_SCAN.json','CANDIDATE_SCAN.json','SHA256SUMS'}
for n,f in outer['files'].items():assert facts(path(E,n))==f;scan_safe(n,(E/n).read_bytes())
for line in (E/'SHA256SUMS').read_text().splitlines():
 digest,n=line.split('  ');assert facts(path(E,n))['sha256']==digest
static=read(STATIC/'RAW_MANIFEST.json');static_safe=read(STATIC/'SAFE_SHARE.json');assert static['count']==16==len(static['files'])==static_safe['count']
for x in static['files']:
 b=path(STATIC,x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256']
for x in static_safe['files']:
 b=path(STATIC,x['path']).read_bytes();out=b.replace(b'$HOME',b'$HOME');assert sha(out)==x['public_sha256'] and len(out)==x['public_bytes']
 assert path(STATIC,'safe-share/'+x['path']).read_bytes()==out
result={'result':'PASS','readback_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Independent static evidence/Git-object readback only. No tests, application/backup/Codex CLI, database, credential, model, network or diagnostic probe invoked. Original evidence unchanged.','source_package':'m63-legacy-review-backup-test-evidence-oct04','source_outer_bindings':{n:facts(E/n) for n in ['REPORT.md','RAW_MANIFEST.json','SAFE_SHARE.json','PUBLIC_OUTER_ALLOWLIST.json','RAW_SCAN.json','CANDIDATE_SCAN.json','SHA256SUMS']},'stages':stages,'preflight':'NOT_RUN: wrong commit rejected before pytest launch; preserved','source_changes':[p],'raw_manifest_verified_count':23,'safe_candidate_verified_count':24,'outer_allowlist_verified_count':4,'copy_scope':'24 candidates plus four explicitly authorized outer files; PUBLIC_OUTER_ALLOWLIST itself is audit authority, not one of its four listed payloads. No broad directory copy.','exact_transforms':safechecks,'raw_scan':'FAIL preserved: eight original files contain the home prefix; the candidate scan is a distinct PASS','static_report_manifest_verified_count':16,'static_report_sha256':facts(STATIC/'REVIEW.md')['sha256'],'static_raw_manifest_sha256':facts(STATIC/'RAW_MANIFEST.json')['sha256'],'limits':{'original_dcf_full_gate':'FAIL: 3683 PASS /1 FAIL /2 ERROR /2 environment SKIP, as carried in source report; full gate not reopened or replaced','two_setup_errors_cause':'UNKNOWN','M7_complete_acceptance':'NOT_RUN','unique_related_tests':65,'single_revised_PASS_included_in_65':True,'installed_dependencies':'not part of 1381 tracked input proof; private runner separately hash-bound','historical_execution_limitation':'saved before/after maps and actual runner/log/receipt bindings were verified; this is not a fresh execution or independent live filesystem capture at the earlier times'}}
(ROOT/'READBACK.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'result':'PASS','raw':23,'safe_candidates':24,'outer':4,'inputs_per_stage':1381,'executed_stages':4,'static_report_files':16}))
