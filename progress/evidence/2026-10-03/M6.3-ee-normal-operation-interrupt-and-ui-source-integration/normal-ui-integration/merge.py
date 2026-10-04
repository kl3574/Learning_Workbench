import datetime,hashlib,json,subprocess,sys
from pathlib import Path
B=Path('$HOME/.cache/learning-workbench-acceptance');R=B/'m62-public-safe-oct02';O=Path(__file__).parent/ sys.argv[1];O.mkdir(exist_ok=False)
HEAD,BASE,OWNER=sys.argv[2:5];sha=lambda b:hashlib.sha256(b).hexdigest()
def run(args):return subprocess.check_output(['git',*args],cwd=R)
def map_():
 head=run(['rev-parse','HEAD']).decode().strip();files={}
 for item in run(['ls-tree','-rz',head]).split(b'\0'):
  if not item:continue
  meta,name=item.split(b'\t',1);name=name.decode()
  if name.startswith('progress/'):continue
  oid=meta.split()[2].decode();raw=(R/name).read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid
  files[name]={'git_blob':oid,'sha256':sha(raw),'bytes':len(raw)}
 return {'head':head,'count':len(files),'files':files}
assert run(['rev-parse','HEAD']).decode().strip()==HEAD and not run(['status','--porcelain'])
subprocess.run(['git','merge-base','--is-ancestor',BASE,HEAD],cwd=R,check=True)
owner_paths=run(['diff','--name-only',BASE,OWNER]).decode().splitlines();assert all(not p.startswith('progress/') for p in owner_paths)
before=map_();(O/'before.json').write_text(json.dumps(before,indent=2)+'\n')
command=['git','merge','--no-ff',OWNER,'-m','feat(M6.3): integrate reviewed '+sys.argv[1]+' owner'];p=subprocess.run(command,cwd=R,capture_output=True)
(O/'merge.stdout').write_bytes(p.stdout);(O/'merge.stderr').write_bytes(p.stderr);(O/'command.json').write_text(json.dumps({'command':command,'exit_code':p.returncode},indent=2)+'\n');assert p.returncode==0,'Original merge conflict retained; do not retry/overwrite blindly'
after=map_();(O/'after.json').write_text(json.dumps(after,indent=2)+'\n')
for name in owner_paths:assert (R/name).read_bytes()==run(['show',OWNER+':'+name]),name
for name,e in before['files'].items():
 if name not in owner_paths:assert after['files'][name]==e,name
assert not run(['status','--porcelain'])
r={'status':'NORMAL_LOCAL_MERGE_EXACT_OWNER_AND_ALL_OTHER_SOURCE_PRESERVED','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before_head':HEAD,'owner_base':BASE,'owner_head':OWNER,'head':after['head'],'owner_changed_paths':owner_paths,'owner_changed_count':len(owner_paths),'before_count':before['count'],'after_count':after['count'],'all_owner_files_exact':True,'all_preexisting_nonoverlap_byte_exact':True,'sourcepush':False,'boundary':'Actual local merge only, not GitHubmerge/release/deploy. Reviewed authorrelated gates and full29e gates do not replace newcombined gates. User originalcheckout untouched,0modelrequests.'};(O/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
