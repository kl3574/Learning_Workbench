from pathlib import Path
import hashlib,json,datetime,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02';P=B/'m63-current101-eleventh-exact-archive-rule-plan-oct07'
def sha(v):return hashlib.sha256(v).hexdigest()
def put(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def cmd(n,argv,cwd=R,inp=None):
 put(n+'-command.json',{'argv':argv,'cwd':str(cwd),'stdin_bytes':len(inp) if inp is not None else None,'stdin_sha256':sha(inp) if inp is not None else None,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 x=subprocess.run(argv,cwd=cwd,input=inp,capture_output=True)
 (O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr)
 put(n+'-receipt.json',{'actual_exit':x.returncode,'stdout_bytes':len(x.stdout),'stdout_sha256':sha(x.stdout),'stderr_bytes':len(x.stderr),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});assert x.returncode==0,(n,x.returncode);return x
plan=json.loads((P/'RULE-PLAN.json').read_bytes());before=(R/'.gitattributes').read_bytes();after=(P/'proposed.gitattributes').read_bytes();assert sha(before)==plan['before_sha256']=='e9b42216d7c6171d3d0e8a13a064a477ce7eeb6e8cb5a0fb31e5169100518a20';assert sha(after)==plan['proposed_sha256']=='1bc2eeba8343bd4b536e98ce2ba6a7b6e244fadbc4e46099ee5c7b7484723990';assert after==before+plan['path'].encode()+b' -whitespace\n'
source=json.loads((B/'m63-current101-final-stage-and-publication-checks-oct07/NONPROGRESS-ACTUAL-BEFORE-STAGE.json').read_bytes())
for n,e in source.items():
 if n=='.gitattributes':continue
 v=(R/n).read_bytes();assert sha(v)==e['live_sha256']
put('APPLY-BEFORE.json',{'attributes_sha256':sha(before),'other1563_sha_exact':True,'tests_already_terminal':'Python4587P2numericENVskip; native133P','apply':'NOT_YET'})
(R/'.gitattributes').write_bytes(after)
put('APPLY-ACTUAL.json',{'changed_paths':['.gitattributes'],'attributes_sha256':sha((R/'.gitattributes').read_bytes()),'prior_prefix_preserved':True,'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actual_file_write':'COMPLETED','test_rerun':False})
old=json.loads((B/'m63-current101-exact-archive-whitespace-apply-oct07/ACTUAL-ATTRIBUTE-READBACK.json').read_bytes())['changed_attribute_paths'];paths=sorted(source)+old+[plan['path']];assert len(paths)==len(set(paths))==1575;inp=b'\0'.join(n.encode() for n in paths)+b'\0';put('EXACT-ATTRIBUTE-INPUTS.json',{'paths':paths,'sha256':sha(inp)})
fixed=cmd('01-fixed-attrs',['git','check-attr','-z','--stdin','whitespace'],B/'m63-integrated-1564-complete-python-source-oct07',inp);live=cmd('02-current-attrs',['git','check-attr','-z','--stdin','whitespace'],R,inp)
def parse(v):
 a=v.split(b'\0');assert a[-1]==b'';a=a[:-1];assert len(a)==len(paths)*3;return {a[i].decode():[a[i+1].decode(),a[i+2].decode()] for i in range(0,len(a),3)}
f=parse(fixed.stdout);l=parse(live.stdout);changed=sorted(n for n in paths if f[n]!=l[n]);assert changed==sorted(old+[plan['path']]);assert all(f[n]==l[n] for n in source) and all(l[n]==['whitespace','unset'] for n in changed)
cmd('03-stage-attrs',['git','add','--','.gitattributes']);cmd('04-original-default-staged-diff',['git','diff','--cached','--check'])
put('READBACK.json',{'actual_apply':'COMPLETED','actual_default_cached_diff_exit':0,'changed_whitespace_paths':changed,'all1564_nonprogress_whitespace_attributes_unchanged':True,'other1563_live_bytes_exact':True,'exact_archive_attrs_sha256':sha(after),'original_two_diff_failures':'RETAINED_EXIT2; no raw log trimming','model_calls':0,'tests_rerun':False,'source_push':False,'M6_3':'NOT_ACCEPTED'})
print('11 exact archive rules; actual attributes and default cached diff verified; no test rerun or push.')
