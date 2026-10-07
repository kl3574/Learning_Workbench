from pathlib import Path
import datetime,hashlib,importlib.util,json,os,stat,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02'
P=B/'m63-six-source-integration-preflight-v3-oct07'
I=B/'m63-review-safe-timing-independent-oct07';IE=B/'m63-review-safe-timing-evidence-oct07'
OLD='7f1669db921fac285226bebeb6a829336b4248b3';PUBLIC='079a008cf88b37e4517cb391503a1e7393ccf374'
SPEC='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def put(n,d):(O/n).parent.mkdir(parents=True,exist_ok=True);(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
env={'PATH':'$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin','LANG':'C.UTF-8'}
def git(*a,cwd=R):return subprocess.run(['git',*a],cwd=cwd,env=env,capture_output=True,check=True).stdout
def tree(h):
 rows={}
 for row in git('ls-tree','-r','-l','-z',h).split(b'\0'):
  if not row:continue
  meta,path=row.split(b'\t',1);mode,kind,oid,size=meta.split();name=path.decode()
  rows[name]={'mode':mode.decode(),'type':kind.decode(),'blob':oid.decode(),'bytes':int(size)}
 return rows
def live(p):
 s=p.lstat();link=stat.S_ISLNK(s.st_mode)
 assert link or stat.S_ISREG(s.st_mode),str(p)
 raw=os.readlink(p).encode() if link else p.read_bytes()
 return {'mode':'120000' if link else '100755' if s.st_mode&stat.S_IXUSR else '100644','type':'blob',
         'blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'bytes':len(raw),'sha256':sha(raw)}
def progress_live():return {str(p.relative_to(R)):live(p) for p in (R/'progress').rglob('*') if p.is_file() or p.is_symlink()}
assert git('rev-parse','HEAD').decode().strip()==OLD
assert git('rev-parse','--show-object-format').decode().strip()=='sha1'
assert sha((R/'PRODUCT_DESIGN.md').read_bytes())==SPEC
before=tree(OLD);public=tree(PUBLIC)
assert {k:v for k,v in before.items() if not k.startswith('progress/')}=={k:v for k,v in public.items() if not k.startswith('progress/')}
status=git('status','--porcelain=v1','--untracked-files=all').decode().splitlines()
assert all(x.startswith(' M progress/') or x.startswith('?? progress/evidence/2026-10-07/') for x in status)
assert all(x[3:] in ['progress/CURRENT.md','progress/state.json'] for x in status if x.startswith(' M '))
assert not git('diff','--cached','--name-only')
user=Path('$HOME/Desktop/learning/Learning_Workbench')
assert git('rev-parse','HEAD',cwd=user).decode().strip()=='b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2'
assert not git('status','--porcelain=v1',cwd=user)
assert sha((P/'10-ROOT-FINITE-PREFLIGHT-MANIFEST.json').read_bytes())=='797df6aead9a75153138995c2b54c40ac63890416e13cc8d203c7741dc77e688'
pm=load(P/'10-ROOT-FINITE-PREFLIGHT-MANIFEST.json')
for e in pm['files']:
 raw=Path(e['path']).read_bytes();assert len(raw)==e['bytes'] and sha(raw)==e['sha256']
assert sha((P/'04-EXPECTED-FINAL-SOURCE-MANIFEST.json').read_bytes())=='0c4a4f401e748eddc77cd983e07863d801fa9e21c5dc7bac111322545dd7ce21'
expected=load(P/'04-EXPECTED-FINAL-SOURCE-MANIFEST.json');assert len(expected['source_files'])==1564
assert sha((I/'REVIEW.json').read_bytes())=='a1bdec158209f960c4ca65ee065809766f5d12e3ce9881749a667b57244af8ab'
review=load(I/'REVIEW.json');assert review['standards']['blocking_findings']==review['spec']['blocking_findings']==0
assert sha((IE/'34-ROOT-FINITE-REVIEW-MANIFEST.json').read_bytes())=='cc4dc54128108a00f1476b2a09439ff324aa703a52bd1b3a6a6742f8cb7e99aa'
im=load(IE/'34-ROOT-FINITE-REVIEW-MANIFEST.json')
for e in im['files']:
 raw=Path(e['path']).read_bytes();assert len(raw)==e['bytes'] and sha(raw)==e['sha256']
put('PRECONDITIONS.json',{'actual_head':OLD,'source_count':1561,'dirty_status':status,'spec_sha256':SPEC,
 'preflight26hashes_exact':True,'review552owner74hashes_exact':True,'review552_axes_blocking':[0,0],
 'user_preserved':'b895clean','source_push':False})
progress=progress_live();put('PROGRESS-BEFORE.json',progress)
for name in ['progress/CURRENT.md','progress/state.json']:
 (O/('before-'+Path(name).name)).write_bytes((R/name).read_bytes())
identity=git('show','-s','--format=%an%x00%ae',OLD).decode().strip().split('\0');assert len(identity)==2
def operation(n,*args):
 argv=['git','-c','user.name='+identity[0],'-c','user.email='+identity[1],*args]
 put(n+'/command.json',{'argv':argv,'cwd':str(R),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'environment':env})
 x=subprocess.run(argv,cwd=R,env=env,capture_output=True)
 (O/n/'stdout.bin').write_bytes(x.stdout);(O/n/'stderr.bin').write_bytes(x.stderr)
 put(n+'/receipt.json',{'actual_exit':x.returncode,'stdout_bytes':len(x.stdout),'stdout_sha256':sha(x.stdout),'stderr_bytes':len(x.stderr),'stderr_sha256':sha(x.stderr),'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 assert x.returncode==0,(n,x.returncode);return x
candidate=[('fixture','90c8cd4ff455a15d6caee9ac296af461f4de65ae',B/'m63-artifact-forward-guard-source-oct07'),
 ('lock','2323558615803830049a02ddfade49450d3fd77e',B/'m63-public079-npm-security-fix-oct07'),
 ('backup','8bd930b6bfcad8b824ca73dd2bd9c475ccf86ab4',B/'m63-backup-closed-grants-oct07'),
 ('review','5520255308ff4824b8fd0b641b1379887742fe33',B/'m63-review-safe-timing-source-oct07')]
merges=[]
for label,commit,path in candidate:
 probe=subprocess.run(['git','cat-file','-e',commit+'^{commit}'],cwd=R,env=env,capture_output=True)
 put('object-presence-'+label+'.json',{'actual_exit':probe.returncode,'meaning':'Localobjectavailabilitylookup only; nonzero triggers exact localfetch, not productFAIL.'})
 if probe.returncode!=0:operation('fetch-local-'+label,'fetch','--no-tags',str(path),commit)
 parent=git('rev-parse','HEAD').decode().strip()
 operation('merge-'+label,'merge','--no-ff',commit,'-m','Merge reviewed M6.3 '+label+' candidate '+commit[:8])
 head=git('rev-parse','HEAD').decode().strip();parents=git('rev-list','--parents','-n','1',head).decode().split()[1:]
 assert parents==[parent,commit] and progress_live()==progress
 merges.append({'label':label,'candidate':commit,'merge':head,'parents':parents})
four_head=git('rev-parse','HEAD').decode().strip();four=tree(four_head)
assert {p for p in four if not p.startswith('progress/')}=={e['path'] for e in expected['source_files']}
for e in expected['source_files']:
 actual=live(R/e['path']);meta=four[e['path']]
 assert all(meta[k]==actual[k]==e[k] for k in ['mode','type','blob','bytes']),e['path']
 assert actual['sha256']==e['sha256'],e['path']
assert {k:v for k,v in four.items() if k.startswith('progress/')}=={k:v for k,v in before.items() if k.startswith('progress/')}
put('FOUR-MERGES-READBACK.json',{'actual_head':four_head,'merges':merges,'all1564_source_matches_expected':True,
 'all_old_progress_Git_equal':True,'all_actual_dirty_and_new_progress_bytes_modes_equal':True,'normal_local_merge_only':True})
rules=[
 'progress/evidence/2026-10-07/M6.3-compatible-source-map-lock232-security-repair-current-web-gates-residual-low-gap/owner-finite/22-frontend-build.stderr',
 'progress/evidence/2026-10-07/M6.3-public079-original-complete-python-terminal-independent-readback/root-finite/SAFE-ORIGINAL-LINES.txt']
attrs=(R/'.gitattributes').read_bytes();(O/'original-gitattributes').write_bytes(attrs)
for path in rules:assert any(line.rstrip(b' \t')!=line for line in (R/path).read_bytes().splitlines())
addition=b'\n# Exact immutable original build warning and pytest source-location whitespace.\n'+''.join(p+' -whitespace\n' for p in rules).encode()
assert all(p.encode() not in attrs for p in rules)
(R/'.gitattributes').write_bytes(attrs+addition)
operation('stage-exact-archive-rules','add','--','.gitattributes')
operation('check-exact-archive-rules','diff','--cached','--check')
operation('commit-exact-archive-rules','commit','-m','Preserve two exact original M6.3 evidence whitespace captures')
head=git('rev-parse','HEAD').decode().strip();final=tree(head)
assert {k:v for k,v in final.items() if k!='.gitattributes'}=={k:v for k,v in four.items() if k!='.gitattributes'}
assert (R/'.gitattributes').read_bytes()==attrs+addition and progress_live()==progress
assert sha((R/'PRODUCT_DESIGN.md').read_bytes())==SPEC
assert git('rev-parse','HEAD',cwd=user).decode().strip()=='b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2' and not git('status','--porcelain=v1',cwd=user)
assert not git('diff','--cached','--name-only')
put('FINAL-SOURCE-METADATA.json',{p:v for p,v in final.items() if not p.startswith('progress/')})
put('READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'previous_head':OLD,'four_merge_head':four_head,'head':head,
 'engineering_input_count':1564,'source_delta_count':6,'archive_only_additional_path':'.gitattributes','archive_only_exact_rules':rules,
 'merges':merges,'all1564_four_merge_source_Git_live_bytes_match_preflight':True,'after_archive_only_other_entries_equal':True,
 'all_old_committed_progress_and_actual_dirty_new_progress_preserved':True,'preserved_progress_files':len(progress),
 'sole_spec_sha256':SPEC,'original_user_b895clean_preserved':True,'public_head_unchanged':PUBLIC,
 'new_full_Python_native_gates':'NOT_RUN_PENDING_FIXED_HEAD','real_model_calls':0,'remote_push_merge_release_deploy':False})
print('Four normal local merges and two exact archive-only rules complete; fixed '+head+';1564inputs; progress/user/spec preserved; no sourcepush.')
