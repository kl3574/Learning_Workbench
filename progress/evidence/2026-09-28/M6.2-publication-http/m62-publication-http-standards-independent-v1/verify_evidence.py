"""Read-only evidence/Git verification; runs no application or product test."""
from pathlib import Path
import hashlib,json,subprocess
OUT=Path(__file__).parent;BASE=OUT.parent
OWNER=BASE/'m62-publication-http-development-v1';ROOT=BASE/'m62-publication-http-active'
COMMIT='833f0a84168638ba5ce421c70cd2f20a71e45e48';BASELINE='dec1d937523f4596da4c39bcc27750d9132c752c'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def save(name,value):(OUT/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
index_raw=(OWNER/'PRIVATE_MANIFEST.json').read_bytes()
assert sha(index_raw)=='330401d9097ca5bc01a9a4183378d141fb41840749f5ac65253897c109665249'
index=json.loads(index_raw);assert len(index['members'])==index['count']==62
for item in index['members']:
 raw=(OWNER/item['path']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
assert {r['path'] for r in index['members']}|{'PRIVATE_MANIFEST.json'}=={p.relative_to(OWNER).as_posix() for p in OWNER.rglob('*') if p.is_file()}
assert sha((OWNER/'REPORT.md').read_bytes())=='f2ee5ef2c99b2a4b4bb8828d7077ac069486496ab897b27d3414147a728bc356'
cache={};stages=[]
for directory in sorted(p for p in OWNER.iterdir() if p.is_dir() and (p/'inputs-before.json').exists()):
 before=json.loads((directory/'inputs-before.json').read_bytes());after=json.loads((directory/'inputs-after.json').read_bytes());assert before==after
 receipt=json.loads((directory/'receipt.json').read_bytes());log=(directory/'test.log').read_bytes()
 assert len(log)==receipt['log_bytes'] and sha(log)==receipt['log_sha256']
 entries={}
 for line in git('ls-tree','-r','-z',receipt['code_commit']).split(b'\0'):
  if not line:continue
  meta,name=line.split(b'\t',1);mode,kind,blob=meta.decode().split()
  assert kind=='blob'
  if not name.startswith(b'progress/'):entries[name.decode()]=(mode,blob)
 assert set(entries)=={row['path'] for row in before} and len(entries)==receipt['source_count']
 for row in before:
  mode,blob=entries[row['path']];assert mode==row['git_mode'] and blob==row['git_blob_sha1']
  if blob not in cache:
   raw=git('cat-file','blob',blob);cache[blob]={'bytes':len(raw),'sha256':sha(raw)}
  assert cache[blob]=={'bytes':row['bytes'],'sha256':row['sha256']}
  assert row['git_matches'] is True
 target=OUT/'owner-execution'/directory.name;target.mkdir(parents=True)
 for name in ['receipt.json','test.log']:(target/name).write_bytes((directory/name).read_bytes())
 stages.append({'stage':directory.name,'commit':receipt['code_commit'],'source_count':len(entries),'actual_git_before_after_verified':True,'exit_code':receipt['exit_code'],'log_sha256':sha(log),'log_bytes':len(log),'original_receipt_sha256':sha((directory/'receipt.json').read_bytes())})
assert len(stages)==10
for item in json.loads((OWNER/'source-pins.json').read_bytes())['http_changed_files']:
 raw=git('show',COMMIT+':'+item['path']);assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
 assert raw==(OWNER/'source'/item['path']).read_bytes()==(OUT/'source'/item['path']).read_bytes()
assert (OWNER/'http-final.diff').read_bytes()==git('diff',BASELINE,COMMIT)==(OUT/'reviewed.diff').read_bytes()
assert (OWNER/'fixture-only-final.diff').read_bytes()==git('diff','966b6c6cf616df816d6c114675c920621ba84573',COMMIT)==(OUT/'833-test-only.diff').read_bytes()
assert git('diff','--name-only','966b6c6cf616df816d6c114675c920621ba84573',COMMIT).decode().splitlines()==['tests/integration/test_draft_publication_http.py']
gen=json.loads((OWNER/'generation/receipt.json').read_bytes());gen_log=(OWNER/'generation/run.log').read_bytes()
assert sha(gen_log)==gen['log_sha256'] and gen['exit_code']==0
assert set(gen['changed_paths'])=={'packages/contracts/generated/'+name for name in ['api-client.ts','api-types.ts','openapi.json','runtime-route-coverage.json']}
for name in ['receipt.json','run.log']:
 target=OUT/'owner-execution/generation'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((OWNER/'generation'/name).read_bytes())
(OUT/'owner-private-manifest.json').write_bytes(index_raw)
assert git('rev-parse','HEAD').decode().strip()==COMMIT and not git('status','--porcelain')
result={'result':'PASS','review_scope':'Eight HTTP adaptation files only; prior authored service is context, not independently re-reviewed','source_commit':COMMIT,'owner_manifest_sha256':sha(index_raw),'owner_manifest_members_verified':62,'stages':stages,'distinct_git_blobs_verified':len(cache),'final_input_count':1023,'generation':'Actual command/exit/four-path/log receipt only; no before/after manifests claimed','fixture_only_delta_verified':True,'product_tests_rerun':False,'source_worktree_clean':True}
save('verification.json',result)
print(json.dumps({'result':'PASS','owner_files':62,'stages':10,'distinct_git_blobs':len(cache),'final_source_count':1023,'product_tests_rerun':False}))
