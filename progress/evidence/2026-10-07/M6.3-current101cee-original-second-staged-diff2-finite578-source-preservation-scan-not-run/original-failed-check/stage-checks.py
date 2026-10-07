from pathlib import Path
import datetime,hashlib,json,os,stat,subprocess,sys,time
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02';PIN='101cee47d8e746dddac81fb6e8829069fcabff09'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def cmd(n,argv,cwd=R):
 assert not (O/(n+'-receipt.json')).exists()
 put(n+'-command.json',{'argv':argv,'cwd':str(cwd),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 t=time.monotonic();x=subprocess.run(argv,cwd=cwd,capture_output=True)
 (O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr)
 put(n+'-receipt.json',{'actual_exit':x.returncode,'stdout_bytes':len(x.stdout),'stdout_sha256':sha(x.stdout),'stderr_bytes':len(x.stderr),'stderr_sha256':sha(x.stderr),'elapsed_seconds':time.monotonic()-t,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 return x
assert cmd('01-head',['git','rev-parse','HEAD']).stdout.decode().strip()==PIN
assert cmd('02-user-head',['git','rev-parse','HEAD'],Path('$HOME/Desktop/learning/Learning_Workbench')).stdout.decode().strip()=='b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2'
assert cmd('03-user-status',['git','status','--porcelain=v1','--untracked-files=all'],Path('$HOME/Desktop/learning/Learning_Workbench')).stdout==b''
specsha='b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
assert sha((R/'PRODUCT_DESIGN.md').read_bytes())==sha(Path('$HOME/Desktop/learning/PRODUCT_DESIGN.md').read_bytes())==specsha
x=cmd('04-fixed-tree',['git','ls-tree','-r','-l','-z',PIN]);assert x.returncode==0
rows={}
for z in x.stdout.split(b'\0'):
 if not z:continue
 md,p=z.split(b'\t',1);p=p.decode();mode,kind,blob,size=md.decode().split();
 if p.startswith('progress/'):continue
 f=R/p;st=f.lstat();assert stat.S_ISREG(st.st_mode) and not f.is_symlink();v=f.read_bytes();actualmode='100755' if st.st_mode&0o111 else '100644';actualblob=hashlib.sha1(b'blob '+str(len(v)).encode()+b'\0'+v).hexdigest();equal=(actualmode,actualblob,len(v))==(mode,blob,int(size))
 rows[p]={'fixed_mode':mode,'fixed_type':kind,'fixed_blob':blob,'fixed_bytes':int(size),'live_mode':actualmode,'live_blob':actualblob,'live_bytes':len(v),'live_sha256':sha(v),'exact':equal}
assert len(rows)==1564 and [p for p,v in rows.items() if not v['exact']]==['.gitattributes']
assert rows['.gitattributes']['live_sha256']=='e9b42216d7c6171d3d0e8a13a064a477ce7eeb6e8cb5a0fb31e5169100518a20'
put('NONPROGRESS-ACTUAL-BEFORE-STAGE.json',rows)
x=cmd('05-tracked-differences',['git','diff','--name-only','--no-renames','-z','HEAD']);assert x.returncode==0
u=cmd('06-untracked',['git','ls-files','--others','--exclude-standard','-z']);assert u.returncode==0
names=sorted({p.decode() for p in (x.stdout+u.stdout).split(b'\0') if p});assert names and all(n=='.gitattributes' or n.startswith('progress/') for n in names)
inv=[]
for n in names:
 f=R/n;assert f.is_file() and not f.is_symlink();v=f.read_bytes();inv.append({'path':n,'bytes':len(v),'sha256':sha(v)})
put('EXACT-FINITE-STAGE-INVENTORY.json',{'count':len(inv),'paths':inv,'allowed_source_difference':['.gitattributes'],'other1563_exact':True,'user_checkout_preserved':True})
x=cmd('07-stage',['git','add','--',*names]);assert x.returncode==0
x=cmd('08-staged-paths',['git','diff','--cached','--name-only','--no-renames','-z']);assert x.returncode==0 and sorted(p.decode() for p in x.stdout.split(b'\0') if p)==names
x=cmd('09-original-default-staged-diff',['git','diff','--cached','--check']);print('original_default_staged_diff_exit',x.returncode,flush=True)
if x.returncode:sys.exit(x.returncode)
x=cmd('10-original-all-tracked-publication',['python3','scripts/check_publication.py','--all-tracked']);print('original_all_tracked_publication_exit',x.returncode,flush=True)
if x.returncode:sys.exit(x.returncode)
put('READBACK.json',{'status':'ACTUAL_ORIGINAL_DIFF_AND_PUBLICATION_EXIT0','count':len(names),'source_pin':PIN,'fixed_inputs':1564,'other1563_exact':True,'exact_archive_attrs_sha256':rows['.gitattributes']['live_sha256'],'spec_sha256':specsha,'preserved_original_user_head':'b8952a3ec0cc9c2bbbaf9ed41cbd9a9e1eb81ce2','model_calls':0,'M6_3':'NOT_ACCEPTED','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
print('Finite actual staged paths and original checks complete; no commit/push by this script.')
